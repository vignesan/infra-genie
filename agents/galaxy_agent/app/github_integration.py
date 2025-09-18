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

import os
import tempfile
import shutil
import subprocess
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime
import asyncio
import logging

from github import Github
from github.Repository import Repository
from github.PullRequest import PullRequest
import git

logger = logging.getLogger(__name__)


@dataclass
class GitHubConfig:
    """Configuration for GitHub integration."""
    token: str
    default_branch: str = "main"


@dataclass
class CodeChange:
    """Represents a code change to be made."""
    file_path: str
    change_type: str  # 'create', 'update', 'delete'
    content: str
    description: str


class GitHubClient:
    """GitHub integration client for repository operations."""

    def __init__(self, token: str = None):
        self.token = token or os.environ.get('GITHUB_TOKEN')
        if not self.token:
            raise ValueError("GitHub token not provided")

        self.github = Github(self.token)
        self.temp_dirs: List[str] = []

    async def clone_repository(self, repo_url: str, branch: str = "main") -> str:
        """Clone a GitHub repository to a temporary directory."""
        try:
            # Create temporary directory
            temp_dir = tempfile.mkdtemp(prefix="galaxy_clone_")
            self.temp_dirs.append(temp_dir)

            # Add token to URL for authentication
            if repo_url.startswith("https://github.com/"):
                auth_url = repo_url.replace("https://", f"https://{self.token}@")
            else:
                auth_url = repo_url

            # Clone repository
            cmd = ["git", "clone", "-b", branch, auth_url, temp_dir]
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            stdout, stderr = await process.communicate()

            if process.returncode != 0:
                raise Exception(f"Git clone failed: {stderr.decode()}")

            # Configure git user
            await self._configure_git_user(temp_dir)

            logger.info(f"Successfully cloned {repo_url} to {temp_dir}")
            return temp_dir

        except Exception as e:
            logger.error(f"Failed to clone repository: {e}")
            raise

    async def _configure_git_user(self, repo_path: str):
        """Configure git user for commits."""
        try:
            git_name = os.environ.get('GIT_USER_NAME', 'Galaxy Bot')
            git_email = os.environ.get('GIT_USER_EMAIL', 'galaxy-bot@example.com')

            await self._run_git_command(['config', 'user.name', git_name], cwd=repo_path)
            await self._run_git_command(['config', 'user.email', git_email], cwd=repo_path)

        except Exception as e:
            logger.warning(f"Failed to configure git user: {e}")

    async def _run_git_command(self, cmd: List[str], cwd: str) -> str:
        """Run a git command and return output."""
        full_cmd = ['git'] + cmd
        process = await asyncio.create_subprocess_exec(
            *full_cmd,
            cwd=cwd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            raise Exception(f"Git command failed: {stderr.decode()}")

        return stdout.decode()

    async def create_branch(self, repo_path: str, branch_name: str, base_branch: str = "main") -> Dict[str, Any]:
        """Create a new branch from base branch."""
        try:
            # Ensure we're on the base branch
            await self._run_git_command(['checkout', base_branch], cwd=repo_path)

            # Pull latest changes
            await self._run_git_command(['pull', 'origin', base_branch], cwd=repo_path)

            # Create and checkout new branch
            await self._run_git_command(['checkout', '-b', branch_name], cwd=repo_path)

            return {
                "status": "success",
                "branch_name": branch_name,
                "base_branch": base_branch,
                "message": f"Branch '{branch_name}' created from '{base_branch}'"
            }

        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "message": f"Failed to create branch '{branch_name}'"
            }

    async def apply_code_changes(self, repo_path: str, changes: List[CodeChange]) -> Dict[str, Any]:
        """Apply code changes to the repository."""
        try:
            modified_files = []

            for change in changes:
                file_path = os.path.join(repo_path, change.file_path)

                if change.change_type == 'create' or change.change_type == 'update':
                    # Create directory if it doesn't exist
                    os.makedirs(os.path.dirname(file_path), exist_ok=True)

                    # Write content to file
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(change.content)

                    modified_files.append(change.file_path)
                    logger.info(f"Applied {change.change_type} to {change.file_path}")

                elif change.change_type == 'delete':
                    if os.path.exists(file_path):
                        os.remove(file_path)
                        modified_files.append(change.file_path)
                        logger.info(f"Deleted {change.file_path}")

            return {
                "status": "success",
                "modified_files": modified_files,
                "message": f"Applied {len(changes)} code changes"
            }

        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "message": "Failed to apply code changes"
            }

    async def commit_and_push_changes(
        self,
        repo_path: str,
        commit_message: str,
        branch_name: str,
        modified_files: List[str] = None
    ) -> Dict[str, Any]:
        """Commit and push changes to the remote repository."""
        try:
            # Add modified files or all changes
            if modified_files:
                for file in modified_files:
                    await self._run_git_command(['add', file], cwd=repo_path)
            else:
                await self._run_git_command(['add', '.'], cwd=repo_path)

            # Check if there are changes to commit
            status_output = await self._run_git_command(['status', '--porcelain'], cwd=repo_path)
            if not status_output.strip():
                return {
                    "status": "no_changes",
                    "message": "No changes to commit"
                }

            # Create commit
            full_commit_message = f"{commit_message}\n\n🤖 Generated by Galaxy Automation\nTimestamp: {datetime.now().isoformat()}"
            await self._run_git_command(['commit', '-m', full_commit_message], cwd=repo_path)

            # Push to remote
            await self._run_git_command(['push', 'origin', branch_name], cwd=repo_path)

            return {
                "status": "success",
                "commit_message": commit_message,
                "branch_name": branch_name,
                "message": f"Changes committed and pushed to '{branch_name}'"
            }

        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "message": "Failed to commit and push changes"
            }

    async def create_pull_request(
        self,
        repo_owner: str,
        repo_name: str,
        source_branch: str,
        target_branch: str,
        title: str,
        description: str
    ) -> Dict[str, Any]:
        """Create a pull request."""
        try:
            repo = self.github.get_repo(f"{repo_owner}/{repo_name}")

            # Create pull request
            pr = repo.create_pull(
                title=title,
                body=description,
                head=source_branch,
                base=target_branch
            )

            return {
                "status": "success",
                "pr_number": pr.number,
                "pr_url": pr.html_url,
                "title": title,
                "source_branch": source_branch,
                "target_branch": target_branch,
                "message": f"Pull request #{pr.number} created successfully"
            }

        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "message": f"Failed to create pull request: {str(e)}"
            }

    async def get_repository_info(self, repo_url: str) -> Dict[str, Any]:
        """Extract repository information from URL."""
        try:
            # Parse GitHub URL
            if repo_url.startswith("https://github.com/"):
                parts = repo_url.replace("https://github.com/", "").rstrip("/").split("/")
                if len(parts) >= 2:
                    return {
                        "owner": parts[0],
                        "name": parts[1].replace(".git", ""),
                        "full_name": f"{parts[0]}/{parts[1].replace('.git', '')}"
                    }

            raise ValueError(f"Invalid GitHub URL format: {repo_url}")

        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "message": "Failed to parse repository URL"
            }

    def cleanup(self):
        """Clean up temporary directories."""
        for temp_dir in self.temp_dirs:
            try:
                if os.path.exists(temp_dir):
                    shutil.rmtree(temp_dir)
                    logger.info(f"Cleaned up temporary directory: {temp_dir}")
            except Exception as e:
                logger.warning(f"Failed to cleanup {temp_dir}: {e}")

        self.temp_dirs.clear()


# Global GitHub client instance
github_client = GitHubClient()