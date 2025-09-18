import os
import subprocess
import asyncio
from google.adk.tools import FunctionTool
from google.adk.agents.invocation_context import InvocationContext
from google.adk.tools.tool_context import ToolContext
from github import Github

async def _run_shell_command_wrapper(command: str, directory: str, tool_context: ToolContext) -> dict:
    """Wrapper to run shell commands and handle potential errors."""
    try:
        # Run command asynchronously using subprocess
        process = await asyncio.create_subprocess_shell(
            command,
            cwd=directory,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )

        stdout, stderr = await process.communicate()

        result = {
            "stdout": stdout.decode() if stdout else "",
            "stderr": stderr.decode() if stderr else "",
            "returncode": process.returncode
        }

        if process.returncode != 0:
            full_error = f"Command failed: {command}\nReturn code: {process.returncode}\nStderr: {result['stderr']}"
            tool_context.state["git_operation_error"] = full_error
            return {"status": "error", "message": full_error}

        return {"status": "success", "stdout": result["stdout"], "stderr": result["stderr"]}

    except Exception as e:
        error_message = f"Command execution failed: {command}\nException: {str(e)}"
        tool_context.state["git_operation_error"] = error_message
        return {"status": "error", "message": error_message}

async def git_clone_repo(
    repo_url: str,
    branch: str,
    local_path: str,
    tool_context: ToolContext
) -> dict:
    """Clones a Git repository into a specified local path.

    Args:
        repo_url (str): The URL of the Git repository to clone.
        branch (str): The branch to checkout after cloning.
        local_path (str): The local directory path where the repository should be cloned.
        tool_context (ToolContext): The tool context object.

    Returns:
        dict: A dictionary indicating the status and any output/error.
    """
    # Ensure the parent directory exists
    parent_dir = os.path.dirname(local_path)
    if parent_dir and not os.path.exists(parent_dir):
        os.makedirs(parent_dir)

    # Handle authentication for cloning
    pat = tool_context.state.get("GALAXY_GITHUB_PAT")
    if pat and "github.com" in repo_url:
        # Inject PAT into the URL for cloning
        # Example: https://<PAT>@github.com/owner/repo.git
        parsed_url = repo_url.replace("https://", f"https://{pat}@")
    else:
        parsed_url = repo_url

    command = f"git clone --branch {branch} {parsed_url} {local_path}"
    return await _run_shell_command_wrapper(command, ".", tool_context)

async def git_checkout_new_branch(
    local_path: str,
    branch_name: str,
    tool_context: ToolContext
) -> dict:
    """Checks out a new Git branch.

    Args:
        local_path (str): The local directory path of the cloned repository.
        branch_name (str): The name of the new branch to create and checkout.
        tool_context (ToolContext): The tool context object.

    Returns:
        dict: A dictionary indicating the status and any output/error.
    """
    command = f"git checkout -b {branch_name}"
    return await _run_shell_command_wrapper(command, local_path, tool_context)

async def git_add_all(
    local_path: str,
    tool_context: ToolContext
) -> dict:
    """Stages all changes in the Git repository.

    Args:
        local_path (str): The local directory path of the cloned repository.
        tool_context (ToolContext): The tool context object.

    Returns:
        dict: A dictionary indicating the status and any output/error.
    """
    command = "git add ."
    return await _run_shell_command_wrapper(command, local_path, tool_context)

async def git_commit_changes(
    local_path: str,
    commit_message: str,
    tool_context: ToolContext
) -> dict:
    """Commits staged changes to the Git repository.

    Args:
        local_path (str): The local directory path of the cloned repository.
        commit_message (str): The commit message.
        tool_context (ToolContext): The tool context object.

    Returns:
        dict: A dictionary indicating the status and any output/error.
    """
    command = f"git commit -m \"{commit_message}\""
    return await _run_shell_command_wrapper(command, local_path, tool_context)

async def git_push_branch(
    local_path: str,
    branch_name: str,
    tool_context: ToolContext
) -> dict:
    """Pushes the current branch to the remote repository.

    Args:
        local_path (str): The local directory path of the cloned repository.
        branch_name (str): The name of the branch to push.
        tool_context (ToolContext): The tool context object.

    Returns:
        dict: A dictionary indicating the status and any output/error.
    """
    command = f"git push --set-upstream origin {branch_name}"
    return await _run_shell_command_wrapper(command, local_path, tool_context)

# Instantiate FunctionTools
git_clone_tool = FunctionTool(git_clone_repo)
git_checkout_new_branch_tool = FunctionTool(git_checkout_new_branch)
git_add_all_tool = FunctionTool(git_add_all)
git_commit_changes_tool = FunctionTool(git_commit_changes)
git_push_branch_tool = FunctionTool(git_push_branch)

async def github_create_pull_request(
    repo_owner: str,
    repo_name: str,
    head_branch: str,
    base_branch: str,
    title: str,
    body: str,
    tool_context: ToolContext
) -> dict:
    """Creates a Pull Request on GitHub.

    Args:
        repo_owner (str): The owner of the repository (e.g., 'octocat').
        repo_name (str): The name of the repository (e.g., 'Spoon-Knife').
        head_branch (str): The name of the branch where your changes are implemented (e.g., 'new-feature').
        base_branch (str): The name of the branch you want to merge your changes into (e.g., 'main').
        title (str): The title of the pull request.
        body (str): The body of the pull request.
        tool_context (ToolContext): The tool context object.

    Returns:
        dict: A dictionary indicating the status and any output/error, including the PR URL if successful.
    """
    pat = tool_context.state.get("GALAXY_GITHUB_PAT")
    if not pat:
        return {"status": "error", "message": "GitHub PAT not found in session state."}

    try:
        g = Github(pat)
        user = g.get_user(repo_owner)
        repo = user.get_repo(repo_name)
        
        pr = repo.create_pull(
            title=title,
            body=body,
            head=head_branch,
            base=base_branch
        )
        return {"status": "success", "pr_url": pr.html_url, "pr_number": pr.number}
    except Exception as e:
        tool_context.state["github_pr_error"] = str(e)
        return {"status": "error", "message": f"Failed to create pull request: {e}"}

github_create_pull_request_tool = FunctionTool(github_create_pull_request)

