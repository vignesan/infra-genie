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

"""Enhanced GitHub Agent for Infrastructure Genie

This module provides comprehensive GitHub workflow management including:
- Repository operations (create, clone, fork, analyze)
- Branch management (create, switch, merge, delete)
- File operations (read, write, update, delete)
- Commit and push operations with intelligent messaging
- Pull request management (create, review, merge)
- Issue tracking and release management
- Repository analysis and pattern detection
"""

import asyncio
import base64
import json
import os
import re
import tempfile
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from google.adk.agents import Agent
from google.adk.tools import BaseTool, FunctionTool
from app.mcp_github import create_github_mcp


class GitHubWorkflowManager(BaseTool):
    """Comprehensive GitHub workflow management tool."""

    def __init__(self):
        super().__init__(
            name="github_workflow_manager",
            description=(
                "Complete GitHub workflow management including repository operations, "
                "branch management, file operations, commits, pull requests, and releases."
            )
        )
        self.github_mcp = create_github_mcp()

    async def run_async(self, *, args: Dict[str, Any], tool_context) -> Dict[str, Any]:
        """Execute GitHub workflow operations."""
        try:
            operation = args.get("operation", "")
            if not operation:
                return {"success": False, "error": "Operation parameter is required"}

            # Route to specific operation handlers
            if operation == "analyze_repository":
                return await self._analyze_repository(args)
            elif operation == "create_repository":
                return await self._create_repository(args)
            elif operation == "clone_repository":
                return await self._clone_repository(args)
            elif operation == "create_branch":
                return await self._create_branch(args)
            elif operation == "switch_branch":
                return await self._switch_branch(args)
            elif operation == "read_file":
                return await self._read_file(args)
            elif operation == "write_file":
                return await self._write_file(args)
            elif operation == "update_file":
                return await self._update_file(args)
            elif operation == "delete_file":
                return await self._delete_file(args)
            elif operation == "commit_changes":
                return await self._commit_changes(args)
            elif operation == "push_changes":
                return await self._push_changes(args)
            elif operation == "create_pull_request":
                return await self._create_pull_request(args)
            elif operation == "merge_pull_request":
                return await self._merge_pull_request(args)
            elif operation == "create_issue":
                return await self._create_issue(args)
            elif operation == "create_release":
                return await self._create_release(args)
            elif operation == "list_repositories":
                return await self._list_repositories(args)
            elif operation == "get_repository_info":
                return await self._get_repository_info(args)
            elif operation == "list_branches":
                return await self._list_branches(args)
            elif operation == "list_commits":
                return await self._list_commits(args)
            elif operation == "get_pull_requests":
                return await self._get_pull_requests(args)
            else:
                return {"success": False, "error": f"Unknown operation: {operation}"}

        except Exception as e:
            return {"success": False, "error": f"GitHub operation failed: {str(e)}"}

    async def _analyze_repository(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze repository structure, patterns, and development workflow."""
        owner = args.get("owner", "")
        repo = args.get("repo", "")

        if not owner or not repo:
            return {"success": False, "error": "Owner and repo parameters are required"}

        try:
            # Get repository information
            repo_info = await self.github_mcp.run_async(
                args={"action": "get_repository", "owner": owner, "repo": repo},
                tool_context=None
            )

            # Get repository structure
            content_info = await self.github_mcp.run_async(
                args={"action": "get_repository_content", "owner": owner, "repo": repo, "path": ""},
                tool_context=None
            )

            # Get branches
            branches_info = await self.github_mcp.run_async(
                args={"action": "list_branches", "owner": owner, "repo": repo},
                tool_context=None
            )

            # Get recent commits for pattern analysis
            commits_info = await self.github_mcp.run_async(
                args={"action": "list_commits", "owner": owner, "repo": repo, "limit": 50},
                tool_context=None
            )

            # Analyze the structure
            analysis = await self._perform_repository_analysis(
                repo_info, content_info, branches_info, commits_info
            )

            return {
                "success": True,
                "repository_analysis": analysis,
                "raw_data": {
                    "repository": repo_info.get("repository", {}),
                    "structure": content_info.get("files", []),
                    "branches": branches_info.get("branches", []),
                    "recent_commits": commits_info.get("commits", [])
                }
            }

        except Exception as e:
            return {"success": False, "error": f"Repository analysis failed: {str(e)}"}

    async def _perform_repository_analysis(
        self, repo_info: Dict, content_info: Dict, branches_info: Dict, commits_info: Dict
    ) -> Dict[str, Any]:
        """Perform intelligent analysis of repository patterns."""

        analysis = {
            "project_type": "unknown",
            "primary_language": "unknown",
            "framework": "unknown",
            "architecture_pattern": "unknown",
            "development_workflow": {},
            "file_structure": {},
            "commit_patterns": {},
            "branch_strategy": "unknown",
            "ci_cd_setup": False,
            "testing_setup": False,
            "documentation_quality": "unknown",
            "code_quality_tools": [],
            "dependencies": [],
            "recommendations": []
        }

        try:
            # Basic repository info
            repo_data = repo_info.get("repository", {})
            analysis["primary_language"] = repo_data.get("language", "unknown")
            analysis["description"] = repo_data.get("description", "")
            analysis["is_fork"] = repo_data.get("fork", False)

            # Analyze file structure
            files = content_info.get("files", [])
            file_analysis = self._analyze_file_structure(files)
            analysis.update(file_analysis)

            # Analyze branches
            branches = branches_info.get("branches", [])
            analysis["branch_strategy"] = self._analyze_branch_strategy(branches)

            # Analyze commit patterns
            commits = commits_info.get("commits", [])
            analysis["commit_patterns"] = self._analyze_commit_patterns(commits)

            # Development workflow analysis
            analysis["development_workflow"] = self._analyze_development_workflow(files, commits)

            # Generate recommendations
            analysis["recommendations"] = self._generate_recommendations(analysis)

        except Exception as e:
            analysis["analysis_error"] = str(e)

        return analysis

    def _analyze_file_structure(self, files: List[Dict]) -> Dict[str, Any]:
        """Analyze repository file structure to determine project type and patterns."""
        analysis = {
            "project_type": "unknown",
            "framework": "unknown",
            "architecture_pattern": "standard",
            "ci_cd_setup": False,
            "testing_setup": False,
            "documentation_quality": "basic",
            "code_quality_tools": [],
            "dependencies": []
        }

        file_names = [f.get("name", "") for f in files]
        file_paths = [f.get("path", "") for f in files]

        # Project type detection
        if any(f in file_names for f in ["package.json", "yarn.lock", "npm-shrinkwrap.json"]):
            analysis["project_type"] = "javascript/nodejs"
            if "next.config.js" in file_names:
                analysis["framework"] = "next.js"
            elif "angular.json" in file_names:
                analysis["framework"] = "angular"
            elif "vue.config.js" in file_names:
                analysis["framework"] = "vue.js"
            elif any("react" in f.lower() for f in file_names):
                analysis["framework"] = "react"
            elif "express" in str(files).lower():
                analysis["framework"] = "express"

        elif any(f in file_names for f in ["requirements.txt", "pyproject.toml", "setup.py", "Pipfile"]):
            analysis["project_type"] = "python"
            if "manage.py" in file_names:
                analysis["framework"] = "django"
            elif "app.py" in file_names or "main.py" in file_names:
                if "fastapi" in str(files).lower():
                    analysis["framework"] = "fastapi"
                elif "flask" in str(files).lower():
                    analysis["framework"] = "flask"

        elif any(f in file_names for f in ["pom.xml", "build.gradle", "build.gradle.kts"]):
            analysis["project_type"] = "java"
            if "spring" in str(files).lower():
                analysis["framework"] = "spring"

        elif any(f in file_names for f in ["go.mod", "go.sum"]):
            analysis["project_type"] = "go"

        elif any(f in file_names for f in ["Cargo.toml", "Cargo.lock"]):
            analysis["project_type"] = "rust"

        elif any(f.endswith(".tf") for f in file_names):
            analysis["project_type"] = "terraform"

        elif "Dockerfile" in file_names:
            analysis["project_type"] = "containerized"

        # Architecture pattern detection
        if any("microservice" in f.lower() for f in file_paths):
            analysis["architecture_pattern"] = "microservices"
        elif any(d in file_paths for d in ["src/", "lib/", "pkg/"]):
            analysis["architecture_pattern"] = "modular"
        elif any(d in file_paths for d in ["controllers/", "models/", "views/"]):
            analysis["architecture_pattern"] = "mvc"

        # CI/CD detection
        ci_files = [".github/workflows/", ".gitlab-ci.yml", "azure-pipelines.yml",
                   "Jenkinsfile", ".circleci/", ".travis.yml"]
        analysis["ci_cd_setup"] = any(ci in f for f in file_paths for ci in ci_files)

        # Testing setup detection
        test_indicators = ["test/", "tests/", "__tests__/", "spec/", "*.test.*", "*.spec.*"]
        analysis["testing_setup"] = any(indicator in f for f in file_paths for indicator in test_indicators)

        # Documentation quality
        doc_files = [f for f in file_names if f.lower() in ["readme.md", "readme.rst", "readme.txt"]]
        if doc_files:
            analysis["documentation_quality"] = "good" if len(doc_files) >= 1 else "basic"

        # Code quality tools
        quality_files = [".eslintrc", ".prettierrc", "pylint.cfg", "mypy.ini", ".editorconfig"]
        analysis["code_quality_tools"] = [f for f in quality_files if any(f in name for name in file_names)]

        return analysis

    def _analyze_branch_strategy(self, branches: List[Dict]) -> str:
        """Analyze branching strategy used in the repository."""
        branch_names = [b.get("name", "") for b in branches]

        if len(branches) <= 2:
            return "simple"

        # Git Flow indicators
        if any(b.startswith("feature/") or b.startswith("hotfix/") or b.startswith("release/")
               for b in branch_names):
            return "git-flow"

        # GitHub Flow indicators
        if "main" in branch_names or "master" in branch_names:
            feature_branches = [b for b in branch_names if "/" in b]
            if len(feature_branches) > 0:
                return "github-flow"

        return "custom"

    def _analyze_commit_patterns(self, commits: List[Dict]) -> Dict[str, Any]:
        """Analyze commit message patterns and development activity."""
        if not commits:
            return {"pattern": "unknown", "frequency": "low", "conventions": []}

        messages = [c.get("message", "") for c in commits]

        # Conventional commit detection
        conventional_pattern = r"^(feat|fix|docs|style|refactor|test|chore)(\(.+\))?: .+"
        conventional_commits = sum(1 for msg in messages if re.match(conventional_pattern, msg))

        patterns = {
            "conventional_commits_percentage": (conventional_commits / len(messages)) * 100,
            "average_message_length": sum(len(msg) for msg in messages) / len(messages),
            "common_prefixes": self._find_common_prefixes(messages),
            "commit_frequency": self._calculate_commit_frequency(commits)
        }

        return patterns

    def _find_common_prefixes(self, messages: List[str]) -> List[str]:
        """Find common prefixes in commit messages."""
        prefixes = {}
        for msg in messages:
            words = msg.split()
            if words:
                first_word = words[0].lower().rstrip(":")
                prefixes[first_word] = prefixes.get(first_word, 0) + 1

        # Return prefixes used in at least 10% of commits
        threshold = len(messages) * 0.1
        return [prefix for prefix, count in prefixes.items() if count >= threshold]

    def _calculate_commit_frequency(self, commits: List[Dict]) -> str:
        """Calculate commit frequency."""
        if len(commits) < 10:
            return "low"

        # This is a simplified calculation
        # In a real implementation, you'd analyze commit timestamps
        if len(commits) > 30:
            return "high"
        elif len(commits) > 15:
            return "medium"
        else:
            return "low"

    def _analyze_development_workflow(self, files: List[Dict], commits: List[Dict]) -> Dict[str, Any]:
        """Analyze development workflow patterns."""
        workflow = {
            "uses_pull_requests": False,
            "code_review_required": False,
            "automated_testing": False,
            "deployment_automation": False,
            "release_process": "unknown"
        }

        file_names = [f.get("name", "") for f in files]

        # Check for GitHub Actions or other CI/CD
        if any(".github/workflows/" in f.get("path", "") for f in files):
            workflow["automated_testing"] = True
            workflow["deployment_automation"] = True

        # Check for code review indicators (this would need PR data in reality)
        if len(commits) > 5:  # Heuristic: active repos likely use PRs
            workflow["uses_pull_requests"] = True

        return workflow

    def _generate_recommendations(self, analysis: Dict[str, Any]) -> List[str]:
        """Generate recommendations based on repository analysis."""
        recommendations = []

        if not analysis.get("ci_cd_setup"):
            recommendations.append("Consider setting up CI/CD workflows for automated testing and deployment")

        if not analysis.get("testing_setup"):
            recommendations.append("Add automated testing to improve code quality and reliability")

        if analysis.get("documentation_quality") == "basic":
            recommendations.append("Enhance documentation with API docs, contribution guidelines, and examples")

        if analysis.get("commit_patterns", {}).get("conventional_commits_percentage", 0) < 50:
            recommendations.append("Consider adopting conventional commit messages for better change tracking")

        if analysis.get("branch_strategy") == "simple" and analysis.get("commit_patterns", {}).get("commit_frequency") == "high":
            recommendations.append("Consider implementing a branching strategy like GitHub Flow for better collaboration")

        if not analysis.get("code_quality_tools"):
            recommendations.append("Add code quality tools like linters and formatters")

        return recommendations

    async def _create_repository(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new repository."""
        repo_name = args.get("name", "")
        description = args.get("description", "")
        private = args.get("private", False)

        return await self.github_mcp.run_async(
            args={
                "action": "create_repository",
                "name": repo_name,
                "description": description,
                "private": private
            },
            tool_context=None
        )

    async def _clone_repository(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Clone a repository."""
        owner = args.get("owner", "")
        repo = args.get("repo", "")

        return await self.github_mcp.run_async(
            args={"action": "clone_repository", "owner": owner, "repo": repo},
            tool_context=None
        )

    async def _create_branch(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new branch."""
        owner = args.get("owner", "")
        repo = args.get("repo", "")
        branch_name = args.get("branch_name", "")
        source_branch = args.get("source_branch", "main")

        return await self.github_mcp.run_async(
            args={
                "action": "create_branch",
                "owner": owner,
                "repo": repo,
                "branch_name": branch_name,
                "source_branch": source_branch
            },
            tool_context=None
        )

    async def _switch_branch(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Switch to a different branch."""
        owner = args.get("owner", "")
        repo = args.get("repo", "")
        branch_name = args.get("branch_name", "")

        return await self.github_mcp.run_async(
            args={
                "action": "switch_branch",
                "owner": owner,
                "repo": repo,
                "branch_name": branch_name
            },
            tool_context=None
        )

    async def _read_file(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Read a file from the repository."""
        owner = args.get("owner", "")
        repo = args.get("repo", "")
        path = args.get("path", "")
        branch = args.get("branch", "main")

        return await self.github_mcp.run_async(
            args={
                "action": "get_file_content",
                "owner": owner,
                "repo": repo,
                "path": path,
                "branch": branch
            },
            tool_context=None
        )

    async def _write_file(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Write a new file to the repository."""
        owner = args.get("owner", "")
        repo = args.get("repo", "")
        path = args.get("path", "")
        content = args.get("content", "")
        message = args.get("commit_message", f"Add {path}")
        branch = args.get("branch", "main")

        return await self.github_mcp.run_async(
            args={
                "action": "create_file",
                "owner": owner,
                "repo": repo,
                "path": path,
                "content": content,
                "message": message,
                "branch": branch
            },
            tool_context=None
        )

    async def _update_file(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Update an existing file in the repository."""
        owner = args.get("owner", "")
        repo = args.get("repo", "")
        path = args.get("path", "")
        content = args.get("content", "")
        message = args.get("commit_message", f"Update {path}")
        branch = args.get("branch", "main")

        return await self.github_mcp.run_async(
            args={
                "action": "update_file",
                "owner": owner,
                "repo": repo,
                "path": path,
                "content": content,
                "message": message,
                "branch": branch
            },
            tool_context=None
        )

    async def _delete_file(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Delete a file from the repository."""
        owner = args.get("owner", "")
        repo = args.get("repo", "")
        path = args.get("path", "")
        message = args.get("commit_message", f"Delete {path}")
        branch = args.get("branch", "main")

        return await self.github_mcp.run_async(
            args={
                "action": "delete_file",
                "owner": owner,
                "repo": repo,
                "path": path,
                "message": message,
                "branch": branch
            },
            tool_context=None
        )

    async def _commit_changes(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Commit changes with an intelligent commit message."""
        owner = args.get("owner", "")
        repo = args.get("repo", "")
        message = args.get("message", "")
        files = args.get("files", [])
        branch = args.get("branch", "main")

        # Generate intelligent commit message if not provided
        if not message:
            message = self._generate_commit_message(files)

        return await self.github_mcp.run_async(
            args={
                "action": "commit_changes",
                "owner": owner,
                "repo": repo,
                "message": message,
                "files": files,
                "branch": branch
            },
            tool_context=None
        )

    def _generate_commit_message(self, files: List[Dict[str, Any]]) -> str:
        """Generate an intelligent commit message based on file changes."""
        if not files:
            return "Update repository"

        added_files = [f for f in files if f.get("status") == "added"]
        modified_files = [f for f in files if f.get("status") == "modified"]
        deleted_files = [f for f in files if f.get("status") == "deleted"]

        actions = []
        if added_files:
            if len(added_files) == 1:
                actions.append(f"add {added_files[0].get('path', 'file')}")
            else:
                actions.append(f"add {len(added_files)} files")

        if modified_files:
            if len(modified_files) == 1:
                actions.append(f"update {modified_files[0].get('path', 'file')}")
            else:
                actions.append(f"update {len(modified_files)} files")

        if deleted_files:
            if len(deleted_files) == 1:
                actions.append(f"remove {deleted_files[0].get('path', 'file')}")
            else:
                actions.append(f"remove {len(deleted_files)} files")

        if len(actions) == 1:
            return actions[0].capitalize()
        elif len(actions) == 2:
            return f"{actions[0].capitalize()} and {actions[1]}"
        else:
            return f"{actions[0].capitalize()}, {', '.join(actions[1:-1])}, and {actions[-1]}"

    async def _push_changes(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Push changes to the remote repository."""
        owner = args.get("owner", "")
        repo = args.get("repo", "")
        branch = args.get("branch", "main")

        return await self.github_mcp.run_async(
            args={
                "action": "push_changes",
                "owner": owner,
                "repo": repo,
                "branch": branch
            },
            tool_context=None
        )

    async def _create_pull_request(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Create a pull request with intelligent description."""
        owner = args.get("owner", "")
        repo = args.get("repo", "")
        title = args.get("title", "")
        head_branch = args.get("head_branch", "")
        base_branch = args.get("base_branch", "main")
        description = args.get("description", "")

        # Generate intelligent PR description if not provided
        if not description:
            description = await self._generate_pr_description(owner, repo, head_branch, base_branch)

        return await self.github_mcp.run_async(
            args={
                "action": "create_pull_request",
                "owner": owner,
                "repo": repo,
                "title": title,
                "head": head_branch,
                "base": base_branch,
                "body": description
            },
            tool_context=None
        )

    async def _generate_pr_description(self, owner: str, repo: str, head_branch: str, base_branch: str) -> str:
        """Generate an intelligent pull request description."""
        try:
            # Get commits in the branch
            commits_result = await self.github_mcp.run_async(
                args={
                    "action": "compare_branches",
                    "owner": owner,
                    "repo": repo,
                    "base": base_branch,
                    "head": head_branch
                },
                tool_context=None
            )

            if commits_result.get("success"):
                commits = commits_result.get("commits", [])
                files = commits_result.get("files", [])

                description = "## Changes\n\n"

                # Summarize commits
                if commits:
                    description += "### Commits\n"
                    for commit in commits[-5:]:  # Last 5 commits
                        message = commit.get("message", "").split("\n")[0]  # First line only
                        description += f"- {message}\n"
                    description += "\n"

                # Summarize file changes
                if files:
                    description += "### Files Changed\n"
                    for file in files[:10]:  # First 10 files
                        status = file.get("status", "modified")
                        filename = file.get("filename", "")
                        description += f"- {status.capitalize()}: `{filename}`\n"
                    if len(files) > 10:
                        description += f"- ... and {len(files) - 10} more files\n"

                description += "\n---\n*This PR description was generated automatically by Infrastructure Genie*"
                return description

        except Exception as e:
            print(f"Failed to generate PR description: {e}")

        return "Please review the changes in this pull request."

    async def _merge_pull_request(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Merge a pull request."""
        owner = args.get("owner", "")
        repo = args.get("repo", "")
        pr_number = args.get("pr_number", 0)
        merge_method = args.get("merge_method", "merge")  # merge, squash, rebase

        return await self.github_mcp.run_async(
            args={
                "action": "merge_pull_request",
                "owner": owner,
                "repo": repo,
                "pull_number": pr_number,
                "merge_method": merge_method
            },
            tool_context=None
        )

    async def _create_issue(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new issue."""
        owner = args.get("owner", "")
        repo = args.get("repo", "")
        title = args.get("title", "")
        body = args.get("body", "")
        labels = args.get("labels", [])

        return await self.github_mcp.run_async(
            args={
                "action": "create_issue",
                "owner": owner,
                "repo": repo,
                "title": title,
                "body": body,
                "labels": labels
            },
            tool_context=None
        )

    async def _create_release(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new release."""
        owner = args.get("owner", "")
        repo = args.get("repo", "")
        tag_name = args.get("tag_name", "")
        name = args.get("name", "")
        body = args.get("body", "")
        draft = args.get("draft", False)
        prerelease = args.get("prerelease", False)

        return await self.github_mcp.run_async(
            args={
                "action": "create_release",
                "owner": owner,
                "repo": repo,
                "tag_name": tag_name,
                "name": name,
                "body": body,
                "draft": draft,
                "prerelease": prerelease
            },
            tool_context=None
        )

    async def _list_repositories(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """List repositories for a user or organization."""
        owner = args.get("owner", "")
        type_filter = args.get("type", "all")  # all, owner, public, private

        return await self.github_mcp.run_async(
            args={
                "action": "list_repositories",
                "owner": owner,
                "type": type_filter
            },
            tool_context=None
        )

    async def _get_repository_info(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Get detailed repository information."""
        owner = args.get("owner", "")
        repo = args.get("repo", "")

        return await self.github_mcp.run_async(
            args={"action": "get_repository", "owner": owner, "repo": repo},
            tool_context=None
        )

    async def _list_branches(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """List all branches in a repository."""
        owner = args.get("owner", "")
        repo = args.get("repo", "")

        return await self.github_mcp.run_async(
            args={"action": "list_branches", "owner": owner, "repo": repo},
            tool_context=None
        )

    async def _list_commits(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """List commits in a repository."""
        owner = args.get("owner", "")
        repo = args.get("repo", "")
        branch = args.get("branch", "main")
        limit = args.get("limit", 30)

        return await self.github_mcp.run_async(
            args={
                "action": "list_commits",
                "owner": owner,
                "repo": repo,
                "sha": branch,
                "per_page": limit
            },
            tool_context=None
        )

    async def _get_pull_requests(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Get pull requests for a repository."""
        owner = args.get("owner", "")
        repo = args.get("repo", "")
        state = args.get("state", "open")  # open, closed, all

        return await self.github_mcp.run_async(
            args={
                "action": "list_pull_requests",
                "owner": owner,
                "repo": repo,
                "state": state
            },
            tool_context=None
        )


# Create the tool instance
github_workflow_manager = GitHubWorkflowManager()


# Enhanced GitHub agent with full DevOps workflow capabilities
enhanced_github_agent = Agent(
    name="enhanced_github_specialist",
    model="gemini-2.5-pro",
    instruction=(
        "You are an expert GitHub DevOps specialist with comprehensive repository management capabilities. "
        "You can perform ALL GitHub operations including repository analysis, branch management, "
        "file operations, commits, pull requests, issues, and releases. "

        "KEY CAPABILITIES:\n"
        "1. REPOSITORY ANALYSIS: Analyze codebases, detect patterns, frameworks, and architecture\n"
        "2. WORKFLOW MANAGEMENT: Create branches, manage files, commit with intelligent messages\n"
        "3. COLLABORATION: Create PRs with detailed descriptions, manage issues and releases\n"
        "4. INTEGRATION: Work seamlessly with code generation and other development tools\n"

        "INTELLIGENT FEATURES:\n"
        "- Auto-generate commit messages based on file changes\n"
        "- Create detailed PR descriptions with change summaries\n"
        "- Analyze repository structure and provide recommendations\n"
        "- Detect development patterns and suggest improvements\n"

        "Always provide detailed feedback about operations performed and any recommendations "
        "for improving the development workflow."
    ),
    tools=[FunctionTool(github_workflow_manager.run_async)],
    output_key="github_workflow_result"
)