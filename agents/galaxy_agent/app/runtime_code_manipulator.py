"""
Runtime Code Manipulator: Clone GitHub repos, modify code, and commit back.
"""

import os
import re
import shutil
import tempfile
import subprocess
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from datetime import datetime
import asyncio
import logging
from pathlib import Path
import json


@dataclass
class CodeModification:
    """Represents a code modification operation."""
    file_path: str
    operation: str  # 'replace', 'insert', 'delete', 'append'
    target: str  # What to find/target
    content: str  # New content
    line_number: Optional[int] = None
    description: str = ""


@dataclass
class GitHubRepository:
    """Represents a GitHub repository for manipulation."""
    url: str
    owner: str
    repo: str
    branch: str = "main"
    clone_path: Optional[str] = None
    auth_token: Optional[str] = None


class RuntimeCodeManipulator:
    """Handles runtime code manipulation operations."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.temp_dirs: List[str] = []
        self.modifications_log: List[Dict] = []

    async def clone_repository(self, repo: GitHubRepository) -> str:
        """Clone a GitHub repository to a temporary directory."""
        try:
            # Create temporary directory
            temp_dir = tempfile.mkdtemp(prefix="infragenie_clone_")
            self.temp_dirs.append(temp_dir)

            # Prepare git clone command
            if repo.auth_token:
                # Use token authentication
                clone_url = repo.url.replace('https://', f'https://{repo.auth_token}@')
            else:
                clone_url = repo.url

            # Clone repository
            cmd = ['git', 'clone', '-b', repo.branch, clone_url, temp_dir]
            result = await self._run_command(cmd, cwd=None)

            if result.returncode != 0:
                raise Exception(f"Git clone failed: {result.stderr}")

            repo.clone_path = temp_dir
            self.logger.info(f"Successfully cloned {repo.owner}/{repo.repo} to {temp_dir}")

            # Configure git user for commits
            await self._configure_git_user(temp_dir)

            return temp_dir

        except Exception as e:
            self.logger.error(f"Failed to clone repository: {e}")
            raise

    async def _configure_git_user(self, repo_path: str):
        """Configure git user for commits."""
        try:
            # Set git user for commits (use environment variables if available)
            git_name = os.environ.get('GIT_USER_NAME', 'Infrastructure Genie')
            git_email = os.environ.get('GIT_USER_EMAIL', 'infragenie@example.com')

            await self._run_command(['git', 'config', 'user.name', git_name], cwd=repo_path)
            await self._run_command(['git', 'config', 'user.email', git_email], cwd=repo_path)

        except Exception as e:
            self.logger.warning(f"Failed to configure git user: {e}")

    async def analyze_repository_structure(self, repo_path: str) -> Dict[str, Any]:
        """Analyze repository structure and common patterns."""
        try:
            analysis = {
                "languages": {},
                "frameworks": [],
                "config_files": [],
                "directory_structure": {},
                "file_types": {},
                "key_files": []
            }

            # Walk through repository
            for root, dirs, files in os.walk(repo_path):
                # Skip .git directory
                if '.git' in dirs:
                    dirs.remove('.git')

                rel_path = os.path.relpath(root, repo_path)

                for file in files:
                    file_path = os.path.join(root, file)
                    rel_file_path = os.path.relpath(file_path, repo_path)

                    # Analyze file extensions
                    ext = Path(file).suffix.lower()
                    if ext:
                        analysis["file_types"][ext] = analysis["file_types"].get(ext, 0) + 1

                    # Identify key files
                    if file.lower() in ['readme.md', 'package.json', 'requirements.txt', 'dockerfile', 'docker-compose.yml', 'makefile']:
                        analysis["key_files"].append(rel_file_path)

                    # Identify config files
                    if any(file.lower().endswith(config_ext) for config_ext in ['.json', '.yaml', '.yml', '.toml', '.ini', '.env']):
                        analysis["config_files"].append(rel_file_path)

            # Detect frameworks/languages
            if 'package.json' in [os.path.basename(f) for f in analysis["key_files"]]:
                analysis["frameworks"].append("Node.js")
            if 'requirements.txt' in [os.path.basename(f) for f in analysis["key_files"]]:
                analysis["frameworks"].append("Python")
            if 'Dockerfile' in [os.path.basename(f) for f in analysis["key_files"]]:
                analysis["frameworks"].append("Docker")

            return analysis

        except Exception as e:
            self.logger.error(f"Failed to analyze repository: {e}")
            return {}

    async def find_files_by_pattern(self, repo_path: str, pattern: str, content_pattern: Optional[str] = None) -> List[str]:
        """Find files matching filename or content patterns."""
        matching_files = []

        try:
            for root, dirs, files in os.walk(repo_path):
                if '.git' in dirs:
                    dirs.remove('.git')

                for file in files:
                    file_path = os.path.join(root, file)
                    rel_path = os.path.relpath(file_path, repo_path)

                    # Check filename pattern
                    if re.search(pattern, file, re.IGNORECASE):
                        if content_pattern:
                            # Check content pattern if specified
                            try:
                                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                                    content = f.read()
                                    if re.search(content_pattern, content, re.IGNORECASE):
                                        matching_files.append(rel_path)
                            except Exception:
                                continue
                        else:
                            matching_files.append(rel_path)

            return matching_files

        except Exception as e:
            self.logger.error(f"Failed to find files: {e}")
            return []

    async def read_file_content(self, repo_path: str, file_path: str) -> str:
        """Read content of a specific file."""
        try:
            full_path = os.path.join(repo_path, file_path)
            with open(full_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            self.logger.error(f"Failed to read file {file_path}: {e}")
            raise

    async def apply_modifications(self, repo_path: str, modifications: List[CodeModification]) -> List[str]:
        """Apply a list of code modifications to files."""
        modified_files = []

        for mod in modifications:
            try:
                success = await self._apply_single_modification(repo_path, mod)
                if success:
                    modified_files.append(mod.file_path)

                    # Log modification
                    self.modifications_log.append({
                        "timestamp": datetime.now().isoformat(),
                        "file": mod.file_path,
                        "operation": mod.operation,
                        "description": mod.description
                    })

            except Exception as e:
                self.logger.error(f"Failed to apply modification to {mod.file_path}: {e}")
                continue

        return modified_files

    async def _apply_single_modification(self, repo_path: str, mod: CodeModification) -> bool:
        """Apply a single code modification."""
        try:
            file_path = os.path.join(repo_path, mod.file_path)

            # Read current content
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            original_content = content

            if mod.operation == 'replace':
                content = content.replace(mod.target, mod.content)

            elif mod.operation == 'insert':
                if mod.line_number is not None:
                    lines = content.split('\n')
                    lines.insert(mod.line_number, mod.content)
                    content = '\n'.join(lines)
                else:
                    # Insert after target line
                    content = content.replace(mod.target, mod.target + '\n' + mod.content)

            elif mod.operation == 'delete':
                content = content.replace(mod.target, '')

            elif mod.operation == 'append':
                content += '\n' + mod.content

            elif mod.operation == 'regex_replace':
                content = re.sub(mod.target, mod.content, content, flags=re.MULTILINE)

            # Write modified content back
            if content != original_content:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)

                self.logger.info(f"Applied {mod.operation} modification to {mod.file_path}")
                return True
            else:
                self.logger.warning(f"No changes made to {mod.file_path} - target not found")
                return False

        except Exception as e:
            self.logger.error(f"Failed to apply modification: {e}")
            return False

    async def create_smart_modifications(self, repo_path: str, instruction: str) -> List[CodeModification]:
        """Create smart modifications based on natural language instructions."""
        modifications = []

        # Example intelligent modification patterns
        # This could be enhanced with AI/LLM analysis

        if "update version" in instruction.lower():
            # Find version files and update them
            version_files = await self.find_files_by_pattern(repo_path, r'(package\.json|setup\.py|pyproject\.toml|version\.py)')

            for file_path in version_files:
                if 'package.json' in file_path:
                    content = await self.read_file_content(repo_path, file_path)
                    # Extract current version and increment
                    version_match = re.search(r'"version":\s*"([^"]+)"', content)
                    if version_match:
                        current_version = version_match.group(1)
                        # Simple version increment (could be more sophisticated)
                        parts = current_version.split('.')
                        if len(parts) >= 3:
                            parts[2] = str(int(parts[2]) + 1)
                            new_version = '.'.join(parts)

                            modifications.append(CodeModification(
                                file_path=file_path,
                                operation='replace',
                                target=f'"version": "{current_version}"',
                                content=f'"version": "{new_version}"',
                                description=f"Update version from {current_version} to {new_version}"
                            ))

        elif "add dependency" in instruction.lower():
            # Add dependencies to package files
            dep_match = re.search(r'add dependency\s+([^\s]+)', instruction.lower())
            if dep_match:
                dependency = dep_match.group(1)

                package_files = await self.find_files_by_pattern(repo_path, r'(package\.json|requirements\.txt|pyproject\.toml)')

                for file_path in package_files:
                    if 'requirements.txt' in file_path:
                        modifications.append(CodeModification(
                            file_path=file_path,
                            operation='append',
                            target='',
                            content=dependency,
                            description=f"Add dependency {dependency}"
                        ))

        elif "update config" in instruction.lower():
            # Find and update configuration files
            config_files = await self.find_files_by_pattern(repo_path, r'(config\.|\.env|\.yaml|\.yml|\.json)')

            # This could be enhanced to parse specific config changes from instruction

        return modifications

    async def commit_and_push_changes(self, repo: GitHubRepository, commit_message: str,
                                    modified_files: List[str]) -> bool:
        """Commit and push changes back to repository."""
        try:
            if not repo.clone_path:
                raise Exception("Repository not cloned")

            # Add modified files to git
            for file_path in modified_files:
                await self._run_command(['git', 'add', file_path], cwd=repo.clone_path)

            # Check if there are changes to commit
            status_result = await self._run_command(['git', 'status', '--porcelain'], cwd=repo.clone_path)
            if not status_result.stdout.strip():
                self.logger.info("No changes to commit")
                return True

            # Create commit
            full_commit_message = f"{commit_message}\n\n🤖 Generated by Infrastructure Genie\nModified files: {', '.join(modified_files)}"

            await self._run_command(['git', 'commit', '-m', full_commit_message], cwd=repo.clone_path)

            # Push changes
            if repo.auth_token:
                # Use token for push
                remote_url = f"https://{repo.auth_token}@github.com/{repo.owner}/{repo.repo}.git"
                await self._run_command(['git', 'remote', 'set-url', 'origin', remote_url], cwd=repo.clone_path)

            push_result = await self._run_command(['git', 'push', 'origin', repo.branch], cwd=repo.clone_path)

            if push_result.returncode != 0:
                raise Exception(f"Git push failed: {push_result.stderr}")

            self.logger.info(f"Successfully pushed changes to {repo.owner}/{repo.repo}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to commit and push changes: {e}")
            return False

    async def _run_command(self, cmd: List[str], cwd: Optional[str] = None) -> subprocess.CompletedProcess:
        """Run a shell command asynchronously."""
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=cwd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            stdout, stderr = await process.communicate()

            return subprocess.CompletedProcess(
                args=cmd,
                returncode=process.returncode,
                stdout=stdout.decode('utf-8'),
                stderr=stderr.decode('utf-8')
            )

        except Exception as e:
            self.logger.error(f"Command failed: {' '.join(cmd)} - {e}")
            raise

    async def create_pull_request(self, repo: GitHubRepository, title: str,
                                description: str, branch_name: str) -> Optional[str]:
        """Create a pull request instead of direct push (safer approach)."""
        try:
            if not repo.clone_path:
                raise Exception("Repository not cloned")

            # Create new branch
            await self._run_command(['git', 'checkout', '-b', branch_name], cwd=repo.clone_path)

            # This would require GitHub API integration
            # For now, just return the branch name
            return branch_name

        except Exception as e:
            self.logger.error(f"Failed to create pull request: {e}")
            return None

    def cleanup(self):
        """Clean up temporary directories."""
        for temp_dir in self.temp_dirs:
            try:
                if os.path.exists(temp_dir):
                    shutil.rmtree(temp_dir)
                    self.logger.info(f"Cleaned up temporary directory: {temp_dir}")
            except Exception as e:
                self.logger.warning(f"Failed to cleanup {temp_dir}: {e}")

        self.temp_dirs.clear()

    def get_modifications_log(self) -> List[Dict]:
        """Get log of all modifications made."""
        return self.modifications_log.copy()


# Global instance
code_manipulator = RuntimeCodeManipulator()