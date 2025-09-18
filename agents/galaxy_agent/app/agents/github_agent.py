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
from google.adk.agents import Agent
from google.adk.tools import FunctionTool

# Placeholder for run_shell_command, as it's not directly available here
# In a real scenario, you'd import it or pass it in.
# For now, these functions will just return strings indicating what they would do.

class GitHubAgent(Agent):
    def __init__(self, github_pat: str = None, repo_owner: str = None):
        # Store credentials as class attributes before calling super().__init__
        self._github_pat = github_pat
        self._repo_owner = repo_owner

        super().__init__(
            name="galaxy_github_agent",
            model="gemini-2.5-flash",
            instruction=(
                "You are the Galaxy GitHub Agent - specialized in GitHub repository operations and version control. "
                "Your expertise includes repository management, branching, commits, pull requests, and issue tracking. "
                "\n\nAvailable tools:\n"
                "- clone_repository: Clone GitHub repositories\n"
                "- create_branch: Create new branches\n"
                "- commit_changes: Commit changes to repository\n"
                "- create_pull_request: Create pull requests\n"
                "- manage_issues: Create and manage GitHub issues\n"
                "- push_changes: Push committed changes to remote\n"
                "\nUse these tools to manage GitHub workflows and collaborate effectively on code projects."
            ),
            tools=[
                FunctionTool(self.clone_repository),
                FunctionTool(self.create_branch),
                FunctionTool(self.commit_changes),
                FunctionTool(self.create_pull_request),
                FunctionTool(self.manage_issues),
                FunctionTool(self.push_changes),
            ],
        )

    def clone_repository(self, repo_url: str, branch: str = "main") -> str:
        """Clone a GitHub repository.
        Requires GITHUB_PAT to be set as an environment variable for git commands.
        """
        # Example of how to use run_shell_command if available
        # os.environ["GITHUB_TOKEN"] = self._github_pat # Set token for git
        # result = run_shell_command(f"git clone {repo_url} -b {branch}")
        return f"Cloning repository: {repo_url} (branch: {branch})\n📋 Repository cloned successfully to local environment." # Placeholder

    def create_branch(self, branch_name: str, base_branch: str = "main") -> str:
        """Create a new branch."""
        return f"Created new branch '{branch_name}' from '{base_branch}'" # Placeholder

    def commit_changes(self, message: str, files: str = "") -> str:
        """Commit changes to repository."""
        file_list = files.split(",") if files else ["all modified files"]
        return f"Committed changes:\n📝 Message: {message}\n📁 Files: {', '.join(file_list)}" # Placeholder

    def create_pull_request(self, title: str, description: str, source_branch: str, target_branch: str = "main") -> str:
        """Create a pull request."""
        return f"Pull request created:\n🔄 Title: {title}\n📄 Description: {description}\n🌿 From: {source_branch} → {target_branch}" # Placeholder

    def manage_issues(self, action: str, issue_title: str = "", issue_body: str = "") -> str:
        """Manage GitHub issues."""
        if action == "create":
            return f"Issue created:\n📋 Title: {issue_title}\n📝 Body: {issue_body}"
        elif action == "list":
            return "📋 Listing open issues..."
        else:
            return f"Issue action '{action}' completed"

    def push_changes(self, branch: str = "main") -> str:
        """Pushes committed changes to remote.
        Requires GITHUB_PAT to be configured for the git client.
        """
        # Example: run_shell_command(f"git push origin {branch}")
        return f"Changes pushed to branch {branch}." # Placeholder

# Instantiate the agent (will be replaced by instantiation in orchestrator_agent.py)
github_agent = GitHubAgent()
