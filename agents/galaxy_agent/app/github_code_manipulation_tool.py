"""
GitHub Code Manipulation Tool: Agent tool for runtime code modification.
"""

import os
import json
from typing import Dict, Any, List
from google.adk.tools import Tool
from app.runtime_code_manipulator import code_manipulator, GitHubRepository, CodeModification


class GitHubCodeManipulationTool(Tool):
    """Tool for manipulating GitHub repositories at runtime."""

    def __init__(self):
        super().__init__(
            name="github_code_manipulator",
            description=(
                "Clone GitHub repositories, analyze code structure, make targeted modifications, "
                "and commit changes back. Supports operations like version updates, dependency additions, "
                "configuration changes, and code refactoring. Provide repository URL and modification instructions."
            ),
            input_schema={
                "type": "object",
                "properties": {
                    "repository_url": {
                        "type": "string",
                        "description": "GitHub repository URL (https://github.com/owner/repo)"
                    },
                    "operation": {
                        "type": "string",
                        "enum": ["analyze", "modify", "smart_modify"],
                        "description": "Operation to perform: analyze (inspect repo), modify (apply specific changes), smart_modify (AI-guided changes)"
                    },
                    "modifications": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "file_path": {"type": "string"},
                                "operation": {"type": "string", "enum": ["replace", "insert", "delete", "append", "regex_replace"]},
                                "target": {"type": "string"},
                                "content": {"type": "string"},
                                "line_number": {"type": "integer"},
                                "description": {"type": "string"}
                            },
                            "required": ["file_path", "operation", "target", "content"]
                        },
                        "description": "List of specific modifications to apply"
                    },
                    "instruction": {
                        "type": "string",
                        "description": "Natural language instruction for smart modifications (e.g., 'update version to 2.1.0', 'add dependency requests')"
                    },
                    "commit_message": {
                        "type": "string",
                        "description": "Commit message for changes"
                    },
                    "branch": {
                        "type": "string",
                        "default": "main",
                        "description": "Git branch to work with"
                    },
                    "create_pr": {
                        "type": "boolean",
                        "default": False,
                        "description": "Create pull request instead of direct push (safer)"
                    },
                    "dry_run": {
                        "type": "boolean",
                        "default": False,
                        "description": "Preview changes without committing"
                    }
                },
                "required": ["repository_url", "operation"]
            }
        )

    async def run_async(self, *, args: Dict[str, Any], tool_context) -> Dict[str, Any]:
        """Execute GitHub code manipulation."""

        try:
            repository_url = args["repository_url"]
            operation = args["operation"]
            branch = args.get("branch", "main")
            dry_run = args.get("dry_run", False)

            # Parse repository URL
            repo = self._parse_repository_url(repository_url, branch)

            # Add authentication if available
            github_token = os.environ.get('GITHUB_TOKEN')
            if github_token:
                repo.auth_token = github_token

            # Clone repository
            print(f"🔄 Cloning repository {repo.owner}/{repo.repo}...")
            clone_path = await code_manipulator.clone_repository(repo)

            result = {
                "repository": f"{repo.owner}/{repo.repo}",
                "branch": branch,
                "clone_path": clone_path,
                "operation": operation,
                "dry_run": dry_run
            }

            if operation == "analyze":
                # Analyze repository structure
                print("🔍 Analyzing repository structure...")
                analysis = await code_manipulator.analyze_repository_structure(clone_path)
                result["analysis"] = analysis
                result["status"] = "success"

            elif operation == "modify":
                # Apply specific modifications
                modifications_data = args.get("modifications", [])
                if not modifications_data:
                    raise ValueError("No modifications specified")

                modifications = [
                    CodeModification(**mod_data) for mod_data in modifications_data
                ]

                print(f"📝 Applying {len(modifications)} modifications...")
                modified_files = await code_manipulator.apply_modifications(clone_path, modifications)

                result["modified_files"] = modified_files
                result["modifications_applied"] = len(modifications)

                if not dry_run and modified_files:
                    commit_message = args.get("commit_message", "Update code via Infrastructure Genie")
                    success = await code_manipulator.commit_and_push_changes(repo, commit_message, modified_files)
                    result["committed"] = success

                result["status"] = "success" if modified_files else "no_changes"

            elif operation == "smart_modify":
                # AI-guided modifications
                instruction = args.get("instruction", "")
                if not instruction:
                    raise ValueError("No instruction provided for smart modification")

                print(f"🧠 Creating smart modifications based on: {instruction}")
                modifications = await code_manipulator.create_smart_modifications(clone_path, instruction)

                if modifications:
                    modified_files = await code_manipulator.apply_modifications(clone_path, modifications)
                    result["modifications_created"] = len(modifications)
                    result["modified_files"] = modified_files

                    if not dry_run and modified_files:
                        commit_message = args.get("commit_message", f"Smart update: {instruction}")
                        success = await code_manipulator.commit_and_push_changes(repo, commit_message, modified_files)
                        result["committed"] = success

                    result["status"] = "success"
                else:
                    result["status"] = "no_modifications_needed"
                    result["message"] = "No applicable modifications found for the given instruction"

            # Add modification log
            result["modifications_log"] = code_manipulator.get_modifications_log()

            return result

        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "operation": operation
            }

        finally:
            # Cleanup temporary files (optional - might want to keep for debugging)
            if not dry_run:
                code_manipulator.cleanup()

    def _parse_repository_url(self, url: str, branch: str) -> GitHubRepository:
        """Parse GitHub repository URL into components."""
        import re

        # Handle different GitHub URL formats
        patterns = [
            r'https://github\.com/([^/]+)/([^/]+?)(?:\.git)?/?$',
            r'git@github\.com:([^/]+)/([^/]+?)(?:\.git)?$'
        ]

        for pattern in patterns:
            match = re.match(pattern, url.strip())
            if match:
                owner, repo_name = match.groups()
                # Remove .git suffix if present
                if repo_name.endswith('.git'):
                    repo_name = repo_name[:-4]

                return GitHubRepository(
                    url=f"https://github.com/{owner}/{repo_name}.git",
                    owner=owner,
                    repo=repo_name,
                    branch=branch
                )

        raise ValueError(f"Invalid GitHub repository URL: {url}")


# Tool instance
github_code_tool = GitHubCodeManipulationTool()