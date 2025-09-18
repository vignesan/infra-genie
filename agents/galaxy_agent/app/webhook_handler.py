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
import json
import logging
from typing import Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime

from fastapi import APIRouter, Request, HTTPException, BackgroundTasks
from .azure_devops_client import azure_devops_client
from .github_integration import github_client
from .workflow_orchestrator import WorkflowOrchestrator

logger = logging.getLogger(__name__)

# Router for webhook endpoints
webhook_router = APIRouter(prefix="/webhook", tags=["webhooks"])


@dataclass
class WorkItemCommentEvent:
    """Represents a work item comment event from Azure DevOps webhook."""
    work_item_id: int
    comment_text: str
    commented_by: str
    comment_date: str
    work_item_title: str
    work_item_description: str
    work_item_state: str
    work_item_type: str
    project: str
    organization: str


class WebhookHandler:
    """Handles Azure DevOps webhooks and orchestrates automated workflows."""

    def __init__(self):
        self.workflow_orchestrator = WorkflowOrchestrator()
        self.active_workflows: Dict[int, str] = {}  # work_item_id -> workflow_id

    async def process_work_item_comment(self, event: WorkItemCommentEvent) -> Dict[str, Any]:
        """Process work item comment and trigger automated workflow if approved."""
        try:
            logger.info(f"Processing comment on work item #{event.work_item_id}: {event.comment_text}")

            # Check if comment indicates approval
            if not self._is_approval_comment(event.comment_text):
                logger.info(f"Comment does not indicate approval, skipping automation")
                return {"status": "skipped", "reason": "Not an approval comment"}

            # Check if workflow is already running for this work item
            if event.work_item_id in self.active_workflows:
                logger.info(f"Workflow already active for work item #{event.work_item_id}")
                return {"status": "skipped", "reason": "Workflow already active"}

            # Start automated workflow
            workflow_id = await self.workflow_orchestrator.start_workflow(
                work_item_id=event.work_item_id,
                approval_comment=event.comment_text,
                work_item_data={
                    "title": event.work_item_title,
                    "description": event.work_item_description,
                    "state": event.work_item_state,
                    "type": event.work_item_type
                }
            )

            self.active_workflows[event.work_item_id] = workflow_id

            # Add initial comment to work item
            await azure_devops_client.add_work_item_comment(
                event.work_item_id,
                f"🤖 Automated workflow started (ID: {workflow_id}). Processing approval and analyzing requirements..."
            )

            return {
                "status": "success",
                "workflow_id": workflow_id,
                "message": f"Automated workflow started for work item #{event.work_item_id}"
            }

        except Exception as e:
            logger.error(f"Error processing work item comment: {e}")
            return {"status": "error", "error": str(e)}

    def _is_approval_comment(self, comment_text: str) -> bool:
        """Check if comment indicates approval to proceed with automation."""
        approval_keywords = [
            "approved", "approve", "go ahead", "proceed", "implement",
            "start work", "begin implementation", "ready to proceed",
            "good to go", "lgtm", "looks good to me"
        ]

        comment_lower = comment_text.lower()
        return any(keyword in comment_lower for keyword in approval_keywords)

    async def complete_workflow(self, work_item_id: int, workflow_id: str, result: Dict[str, Any]):
        """Complete workflow and clean up tracking."""
        try:
            if work_item_id in self.active_workflows:
                del self.active_workflows[work_item_id]

            # Add final comment based on result
            if result.get("status") == "success":
                comment = f"✅ Workflow completed successfully!\n\n{result.get('summary', '')}"
            else:
                comment = f"❌ Workflow failed after maximum retries.\n\nError: {result.get('error', 'Unknown error')}\n\nSuggested solutions:\n{result.get('suggestions', 'Manual intervention required')}"

            await azure_devops_client.add_work_item_comment(work_item_id, comment)

            logger.info(f"Workflow {workflow_id} completed for work item #{work_item_id}")

        except Exception as e:
            logger.error(f"Error completing workflow: {e}")


# Global webhook handler instance
webhook_handler = WebhookHandler()


@webhook_router.post("/azure-devops/workitem")
async def azure_devops_workitem_webhook(
    request: Request,
    background_tasks: BackgroundTasks
):
    """Handle Azure DevOps work item webhook events."""
    try:
        # Parse webhook payload
        payload = await request.json()

        # Log the event for debugging
        logger.info(f"Received Azure DevOps webhook: {payload.get('eventType', 'unknown')}")

        # Check if it's a work item comment event
        event_type = payload.get("eventType", "")
        if event_type != "workitem.commented":
            return {"status": "ignored", "reason": f"Event type '{event_type}' not handled"}

        # Extract work item comment data
        resource = payload.get("resource", {})
        fields = resource.get("fields", {})

        # Get the latest comment from history
        history = fields.get("System.History", {})
        if not history or not history.get("newValue"):
            return {"status": "ignored", "reason": "No comment text found"}

        # Create event object
        event = WorkItemCommentEvent(
            work_item_id=resource.get("id", 0),
            comment_text=history.get("newValue", ""),
            commented_by=fields.get("System.ChangedBy", {}).get("newValue", {}).get("displayName", "Unknown"),
            comment_date=fields.get("System.ChangedDate", {}).get("newValue", ""),
            work_item_title=fields.get("System.Title", {}).get("newValue", ""),
            work_item_description=fields.get("System.Description", {}).get("newValue", ""),
            work_item_state=fields.get("System.State", {}).get("newValue", ""),
            work_item_type=fields.get("System.WorkItemType", {}).get("newValue", ""),
            project=payload.get("resourceContainers", {}).get("project", {}).get("id", ""),
            organization=payload.get("resourceContainers", {}).get("account", {}).get("id", "")
        )

        # Process the event in background
        background_tasks.add_task(webhook_handler.process_work_item_comment, event)

        return {
            "status": "accepted",
            "message": f"Work item comment event queued for processing",
            "work_item_id": event.work_item_id
        }

    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")
    except Exception as e:
        logger.error(f"Error processing webhook: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@webhook_router.get("/azure-devops/test")
async def test_azure_devops_webhook():
    """Test endpoint to verify webhook configuration."""
    return {
        "status": "ok",
        "message": "Azure DevOps webhook endpoint is active",
        "timestamp": datetime.now().isoformat(),
        "active_workflows": len(webhook_handler.active_workflows)
    }


@webhook_router.post("/azure-devops/test-approval")
async def test_approval_workflow(
    work_item_id: int,
    comment_text: str = "approved - please proceed with implementation"
):
    """Test endpoint to simulate an approval comment and trigger workflow."""
    try:
        event = WorkItemCommentEvent(
            work_item_id=work_item_id,
            comment_text=comment_text,
            commented_by="Test User",
            comment_date=datetime.now().isoformat(),
            work_item_title="Test Work Item",
            work_item_description="Test description for workflow testing",
            work_item_state="Active",
            work_item_type="Task",
            project="test-project",
            organization="test-org"
        )

        result = await webhook_handler.process_work_item_comment(event)
        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))