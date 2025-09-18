# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import asyncio
import uuid
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum

from .azure_devops_client import azure_devops_client
from .github_integration import github_client, CodeChange
from .standalone_code_modifier import code_modifier
from .config import config

logger = logging.getLogger(__name__)


class WorkflowStatus(Enum):
    """Workflow execution status."""
    PENDING = "pending"
    ANALYZING = "analyzing"
    CODING = "coding"
    TESTING = "testing"
    RETRYING = "retrying"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class WorkflowState:
    """Represents the state of an automated workflow."""
    workflow_id: str
    work_item_id: int
    status: WorkflowStatus
    created_at: str
    updated_at: str

    # Work item data
    work_item_title: str
    work_item_description: str
    approval_comment: str

    # Repository data
    repo_url: Optional[str] = None
    branch_name: Optional[str] = None
    local_repo_path: Optional[str] = None

    # Code changes
    code_changes: List[Dict] = None

    # Pipeline data
    pipeline_id: Optional[int] = None
    build_id: Optional[int] = None

    # Retry tracking
    retry_count: int = 0
    max_retries: int = 3
    last_error: Optional[str] = None

    # Results
    pr_url: Optional[str] = None
    success: bool = False


class WorkflowOrchestrator:
    """Orchestrates end-to-end automated workflows for approved work items."""

    def __init__(self):
        self.active_workflows: Dict[str, WorkflowState] = {}
        self.max_concurrent_workflows = 5

    async def start_workflow(
        self,
        work_item_id: int,
        approval_comment: str,
        work_item_data: Dict[str, Any]
    ) -> str:
        """Start an automated workflow for an approved work item."""
        try:
            # Create workflow state
            workflow_id = str(uuid.uuid4())
            workflow_state = WorkflowState(
                workflow_id=workflow_id,
                work_item_id=work_item_id,
                status=WorkflowStatus.PENDING,
                created_at=datetime.now().isoformat(),
                updated_at=datetime.now().isoformat(),
                work_item_title=work_item_data.get("title", ""),
                work_item_description=work_item_data.get("description", ""),
                approval_comment=approval_comment,
                code_changes=[]
            )

            self.active_workflows[workflow_id] = workflow_state

            # Start workflow execution in background
            asyncio.create_task(self._execute_workflow(workflow_state))

            logger.info(f"Started workflow {workflow_id} for work item #{work_item_id}")
            return workflow_id

        except Exception as e:
            logger.error(f"Failed to start workflow: {e}")
            raise

    async def _execute_workflow(self, state: WorkflowState):
        """Execute the complete automated workflow."""
        try:
            await self._update_status(state, WorkflowStatus.ANALYZING)

            # Step 1: Analyze requirements and determine if code changes are needed
            analysis_result = await self._analyze_requirements(state)
            if not analysis_result["needs_code_changes"]:
                await self._complete_workflow(state, success=True, message="No code changes required")
                return

            # Step 2: Extract repository information
            repo_info = await self._extract_repository_info(state)
            if not repo_info["success"]:
                await self._complete_workflow(state, success=False, error="Failed to identify repository")
                return

            state.repo_url = repo_info["repo_url"]

            # Step 3: Start implementation loop with retries
            await self._implementation_loop(state)

        except Exception as e:
            logger.error(f"Workflow {state.workflow_id} failed: {e}")
            await self._complete_workflow(state, success=False, error=str(e))

    async def _analyze_requirements(self, state: WorkflowState) -> Dict[str, Any]:
        """Analyze work item requirements and approval comment to understand what needs to be done."""
        try:
            # Combine work item description and approval comment
            combined_text = f"""
            Work Item: {state.work_item_title}
            Description: {state.work_item_description}
            Approval Comment: {state.approval_comment}
            """

            # Use LLM to analyze requirements
            analysis_prompt = f"""
            Analyze this work item and approval comment to determine:
            1. Does this require code changes? (yes/no)
            2. What type of changes are needed? (new feature, bug fix, refactoring, etc.)
            3. Which files or components might be affected?
            4. What is the repository URL if mentioned?

            Text to analyze:
            {combined_text}

            Respond in JSON format:
            {{
                "needs_code_changes": true/false,
                "change_type": "feature|bugfix|refactor|other",
                "affected_components": ["list", "of", "components"],
                "repository_url": "url if found",
                "implementation_plan": "brief plan of what to implement"
            }}
            """

            # Get analysis from code modifier (using LLM)
            if code_modifier.model:
                response = await code_modifier.model.generate_content_async(analysis_prompt)

                # Parse JSON response
                import json
                import re
                json_match = re.search(r'\{.*\}', response.text, re.DOTALL)
                if json_match:
                    analysis = json.loads(json_match.group())
                else:
                    # Fallback analysis
                    analysis = {
                        "needs_code_changes": True,
                        "change_type": "feature",
                        "affected_components": [],
                        "repository_url": None,
                        "implementation_plan": "Implement based on work item description"
                    }
            else:
                # Fallback when no LLM available
                analysis = {
                    "needs_code_changes": True,
                    "change_type": "feature",
                    "affected_components": [],
                    "repository_url": None,
                    "implementation_plan": "Manual implementation required"
                }

            await azure_devops_client.add_work_item_comment(
                state.work_item_id,
                f"📋 Requirements Analysis:\n- Change Type: {analysis['change_type']}\n- Implementation Plan: {analysis['implementation_plan']}"
            )

            return analysis

        except Exception as e:
            logger.error(f"Requirements analysis failed: {e}")
            return {"needs_code_changes": False, "error": str(e)}

    async def _extract_repository_info(self, state: WorkflowState) -> Dict[str, Any]:
        """Extract repository information from work item or comments."""
        try:
            # Look for repository URLs in work item description or comments
            text_to_search = f"{state.work_item_description} {state.approval_comment}"

            # Common repository URL patterns
            import re
            github_pattern = r'https://github\.com/[\w-]+/[\w-]+(?:\.git)?'
            azure_repos_pattern = r'https://dev\.azure\.com/[\w-]+/[\w-]+/_git/[\w-]+'

            github_match = re.search(github_pattern, text_to_search)
            azure_match = re.search(azure_repos_pattern, text_to_search)

            if github_match:
                return {
                    "success": True,
                    "repo_url": github_match.group(),
                    "repo_type": "github"
                }
            elif azure_match:
                return {
                    "success": True,
                    "repo_url": azure_match.group(),
                    "repo_type": "azure_repos"
                }
            else:
                # Try to get from environment or configuration
                default_repo = os.environ.get('DEFAULT_REPO_URL')
                if default_repo:
                    return {
                        "success": True,
                        "repo_url": default_repo,
                        "repo_type": "github"
                    }
                else:
                    return {
                        "success": False,
                        "error": "No repository URL found in work item or configuration"
                    }

        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _implementation_loop(self, state: WorkflowState):
        """Main implementation loop with retries for failures."""
        while state.retry_count <= state.max_retries:
            try:
                await self._update_status(state, WorkflowStatus.CODING)

                # Step 1: Clone repository and create branch
                clone_result = await self._clone_and_create_branch(state)
                if not clone_result["success"]:
                    raise Exception(clone_result["error"])

                # Step 2: Generate and apply code changes
                changes_result = await self._generate_code_changes(state)
                if not changes_result["success"]:
                    raise Exception(changes_result["error"])

                # Step 3: Commit and push changes
                commit_result = await self._commit_and_push_changes(state)
                if not commit_result["success"]:
                    raise Exception(commit_result["error"])

                # Step 4: Create pull request
                pr_result = await self._create_pull_request(state)
                if not pr_result["success"]:
                    raise Exception(pr_result["error"])

                state.pr_url = pr_result["pr_url"]

                # Step 5: Trigger pipeline
                await self._update_status(state, WorkflowStatus.TESTING)
                pipeline_result = await self._trigger_and_monitor_pipeline(state)

                if pipeline_result["success"]:
                    await self._complete_workflow(state, success=True, message="Implementation completed successfully")
                    return
                else:
                    # Pipeline failed, retry if possible
                    state.retry_count += 1
                    state.last_error = pipeline_result["error"]

                    if state.retry_count <= state.max_retries:
                        await self._update_status(state, WorkflowStatus.RETRYING)
                        await azure_devops_client.add_work_item_comment(
                            state.work_item_id,
                            f"⚠️ Pipeline failed (attempt {state.retry_count}/{state.max_retries + 1}). Retrying with fixes...\nError: {pipeline_result['error']}"
                        )
                        # Continue to next iteration
                    else:
                        raise Exception(f"Pipeline failed after {state.max_retries + 1} attempts: {pipeline_result['error']}")

            except Exception as e:
                state.retry_count += 1
                state.last_error = str(e)

                if state.retry_count <= state.max_retries:
                    await azure_devops_client.add_work_item_comment(
                        state.work_item_id,
                        f"❌ Implementation failed (attempt {state.retry_count}/{state.max_retries + 1}): {str(e)}\nRetrying..."
                    )
                    await asyncio.sleep(30)  # Wait before retry
                else:
                    await self._complete_workflow(state, success=False, error=str(e))
                    return

    async def _clone_and_create_branch(self, state: WorkflowState) -> Dict[str, Any]:
        """Clone repository and create a new branch for changes."""
        try:
            # Clone repository
            repo_path = await github_client.clone_repository(state.repo_url)
            state.local_repo_path = repo_path

            # Create branch name
            branch_name = f"galaxy/workitem-{state.work_item_id}-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
            state.branch_name = branch_name

            # Create branch
            branch_result = await github_client.create_branch(repo_path, branch_name)

            return branch_result

        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _generate_code_changes(self, state: WorkflowState) -> Dict[str, Any]:
        """Generate code changes based on requirements."""
        try:
            # Use code modifier to generate changes
            instruction = f"""
            Work Item: {state.work_item_title}
            Description: {state.work_item_description}
            Approval: {state.approval_comment}

            Generate the necessary code changes to implement this requirement.
            """

            # For now, create a simple example change
            # In a real implementation, this would use LLM to generate actual code
            changes = [
                CodeChange(
                    file_path="README.md",
                    change_type="update",
                    content=f"# Updated by Galaxy Automation\n\nWork Item: {state.work_item_title}\nImplemented: {datetime.now().isoformat()}\n",
                    description=f"Updated for work item #{state.work_item_id}"
                )
            ]

            # Apply changes to repository
            apply_result = await github_client.apply_code_changes(state.local_repo_path, changes)

            if apply_result["status"] == "success":
                state.code_changes = [asdict(change) for change in changes]
                return {"success": True, "changes": len(changes)}
            else:
                return {"success": False, "error": apply_result["message"]}

        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _commit_and_push_changes(self, state: WorkflowState) -> Dict[str, Any]:
        """Commit and push changes to remote repository."""
        try:
            commit_message = f"Implement work item #{state.work_item_id}: {state.work_item_title}"

            result = await github_client.commit_and_push_changes(
                state.local_repo_path,
                commit_message,
                state.branch_name
            )

            return {"success": result["status"] == "success", "error": result.get("message", "")}

        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _create_pull_request(self, state: WorkflowState) -> Dict[str, Any]:
        """Create a pull request for the changes."""
        try:
            repo_info = await github_client.get_repository_info(state.repo_url)

            if "error" in repo_info:
                return {"success": False, "error": repo_info["error"]}

            title = f"Work Item #{state.work_item_id}: {state.work_item_title}"
            description = f"""
## Automated Implementation

**Work Item**: #{state.work_item_id}
**Title**: {state.work_item_title}
**Description**: {state.work_item_description}

**Approval Comment**: {state.approval_comment}

**Changes Made**:
{chr(10).join([f"- {change['description']}" for change in state.code_changes])}

---
🤖 This PR was automatically generated by Galaxy Automation
"""

            pr_result = await github_client.create_pull_request(
                repo_info["owner"],
                repo_info["name"],
                state.branch_name,
                "main",
                title,
                description
            )

            if pr_result["status"] == "success":
                await azure_devops_client.add_work_item_comment(
                    state.work_item_id,
                    f"🔄 Pull Request Created: {pr_result['pr_url']}"
                )
                return {"success": True, "pr_url": pr_result["pr_url"]}
            else:
                return {"success": False, "error": pr_result["message"]}

        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _trigger_and_monitor_pipeline(self, state: WorkflowState) -> Dict[str, Any]:
        """Trigger pipeline and monitor its execution."""
        try:
            # Get pipeline ID from environment or work item
            pipeline_id = int(os.environ.get('DEFAULT_PIPELINE_ID', '1'))
            state.pipeline_id = pipeline_id

            # Trigger pipeline
            trigger_result = await azure_devops_client.trigger_pipeline(
                pipeline_id,
                state.branch_name
            )

            if trigger_result["status"] != "success":
                return {"success": False, "error": trigger_result["message"]}

            state.build_id = trigger_result["build_id"]

            # Monitor pipeline execution
            return await self._monitor_pipeline_execution(state)

        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _monitor_pipeline_execution(self, state: WorkflowState) -> Dict[str, Any]:
        """Monitor pipeline execution and return result."""
        try:
            max_wait_time = 1800  # 30 minutes
            wait_interval = 30  # 30 seconds
            elapsed_time = 0

            while elapsed_time < max_wait_time:
                status_result = await azure_devops_client.get_pipeline_status(state.build_id)

                if status_result["status"] == "success":
                    pipeline_status = status_result["pipeline_status"]

                    if pipeline_status in ["completed", "succeeded"]:
                        await azure_devops_client.add_work_item_comment(
                            state.work_item_id,
                            f"✅ Pipeline completed successfully!\nBuild: {state.build_id}\nDuration: {status_result.get('duration', 'N/A')}"
                        )
                        return {"success": True, "message": "Pipeline completed successfully"}

                    elif pipeline_status in ["failed", "canceled"]:
                        error_logs = status_result.get("logs", [])
                        error_summary = self._extract_error_summary(error_logs)

                        await azure_devops_client.add_work_item_comment(
                            state.work_item_id,
                            f"❌ Pipeline failed!\nBuild: {state.build_id}\nError: {error_summary}"
                        )
                        return {"success": False, "error": error_summary}

                    # Pipeline still running
                    await asyncio.sleep(wait_interval)
                    elapsed_time += wait_interval
                else:
                    return {"success": False, "error": "Failed to get pipeline status"}

            # Timeout
            return {"success": False, "error": "Pipeline monitoring timeout"}

        except Exception as e:
            return {"success": False, "error": str(e)}

    def _extract_error_summary(self, logs: List[Dict]) -> str:
        """Extract error summary from pipeline logs."""
        try:
            error_keywords = ["error", "failed", "exception", "critical"]
            errors = []

            for log in logs:
                content = log.get("content", "").lower()
                for keyword in error_keywords:
                    if keyword in content:
                        # Extract the line with error
                        lines = content.split('\n')
                        for line in lines:
                            if keyword in line:
                                errors.append(line.strip()[:200])  # Limit length
                                break

            return "; ".join(errors[:3]) if errors else "Unknown pipeline error"

        except Exception:
            return "Error details not available"

    async def _update_status(self, state: WorkflowState, status: WorkflowStatus):
        """Update workflow status."""
        state.status = status
        state.updated_at = datetime.now().isoformat()
        logger.info(f"Workflow {state.workflow_id} status: {status.value}")

    async def _complete_workflow(self, state: WorkflowState, success: bool, message: str = "", error: str = ""):
        """Complete workflow and clean up."""
        try:
            state.success = success
            state.status = WorkflowStatus.COMPLETED if success else WorkflowStatus.FAILED
            state.updated_at = datetime.now().isoformat()

            # Clean up temporary files
            if state.local_repo_path:
                github_client.cleanup()

            # Remove from active workflows
            if state.workflow_id in self.active_workflows:
                del self.active_workflows[state.workflow_id]

            # Add final comment
            final_message = message or error or "Workflow completed"

            if success:
                comment = f"🎉 **Workflow Completed Successfully!**\n\n{final_message}"
                if state.pr_url:
                    comment += f"\n\n**Pull Request**: {state.pr_url}"
            else:
                comment = f"❌ **Workflow Failed**\n\n{final_message}"
                if state.retry_count > state.max_retries:
                    comment += f"\n\n**Suggestions**:\n- Review the error details\n- Check repository configuration\n- Verify pipeline settings\n- Consider manual implementation"

            await azure_devops_client.add_work_item_comment(state.work_item_id, comment)

            logger.info(f"Workflow {state.workflow_id} completed with success={success}")

        except Exception as e:
            logger.error(f"Error completing workflow: {e}")

# Global orchestrator instance
workflow_orchestrator = WorkflowOrchestrator()