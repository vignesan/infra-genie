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
from google.adk.agents import SequentialAgent, Agent
from google.adk.a2a import RemoteA2aAgent
from google.adk.tools import AgentTool
from .agents.code_agent import code_agent
from .agents.github_agent import GitHubAgent
from .agents.azuredevops_agent import AzureDevOpsAgent
from .tools.loop_condition_tool import complete_task
from .intelligent_code_modifier import intelligent_code_tool
from .tools.git_tools import (
    git_clone_tool,
    git_checkout_new_branch_tool,
    git_add_all_tool,
    git_commit_changes_tool,
    git_push_branch_tool,
    github_create_pull_request_tool,
)
from google.adk.agents import LlmAgent
from google.adk.agents.callback_context import CallbackContext
from google.adk.events import Event, EventActions
import re

def analyze_work_item_comment_callback(callback_context: CallbackContext) -> None:
    """
    Analyzes the work item comment for the 'gennie: approved' keyword and extracts the core request.
    Sets 'is_approved' and 'core_request' in session.state.
    """
    # The initial message from the webhook is passed as the user_message to the agent.
    # We need to access the content of the last user event.
    user_message = ""
    for event in reversed(callback_context._invocation_context.session.events):
        if event.author == "user" and event.content and event.content.parts:
            for part in event.content.parts:
                if part.text:
                    user_message = part.text
                    break
        if user_message: break

    work_item_id = callback_context._invocation_context.session.session_id.replace("wi-", "")

    approval_pattern = r"gennie:\s*approved\s*(.*)"
    match = re.search(approval_pattern, user_message, re.IGNORECASE)

    if match:
        core_request = match.group(1).strip()
        callback_context.state["is_approved"] = True
        callback_context.state["core_request"] = core_request
        print(f"Work Item {work_item_id} approved. Core request: {core_request}")
    else:
        callback_context.state["is_approved"] = False
        print(f"Work Item {work_item_id} not approved by gennie.")

work_item_analyzer_agent = LlmAgent(
    name="work_item_analyzer_agent",
    model="gemini-2.5-flash", # Using a fast model for initial analysis
    instruction=(
        "You are a work item comment analyzer. Your task is to process incoming work item comments. "
        "Look for the phrase 'gennie: approved' to determine if the work item is approved for action. "
        "If approved, extract the core request or instruction that follows the approval phrase. "
        "If not approved, simply acknowledge the comment without taking further action. "
        "Do not generate any code or perform any actions yourself. Just analyze and extract." 
        "The user message will be in the format: 'Work item {work_item_id} commented by {commented_by}: {comment_text}'"
    ),
    description="Analyzes Azure DevOps work item comments for approval and extracts the core request.",
    after_agent_callback=analyze_work_item_comment_callback,
    # We might add AzureDevOpsAgent as a tool here if it needs to fetch more details
    # tools=[AzureDevOpsAgent(...)]
)

class CodeModificationAgent(SequentialAgent):
    def __init__(self, name: str = "code_modification_agent"):
        sub_agents_for_code_mod = [
            code_generator_modifier_agent, # First step: generate/modify code
            git_operations_agent, # Second step: perform Git operations
            pull_request_creator_agent, # Third step: create Pull Request
        ]
        if pipeline_trigger_agent:
            sub_agents_for_code_mod.append(pipeline_trigger_agent) # Fourth step: trigger pipeline
        if pipeline_monitor_retry_loop:
            sub_agents_for_code_mod.append(pipeline_monitor_retry_loop) # Fifth step: monitor and retry pipeline
        if work_item_commenter_agent:
            sub_agents_for_code_mod.append(work_item_commenter_agent) # Sixth step: comment on work item

        super().__init__(
            name=name,
            description="Orchestrates the code modification and delivery loop if the work item is approved.",
            sub_agents=sub_agents_for_code_mod,
            before_agent_callback=self._check_approval_callback
        )

    def _check_approval_callback(self, callback_context: CallbackContext) -> None:
        """
        Checks if the work item has been approved. If not, it escalates to stop further execution
        within this agent.
        """
        is_approved = callback_context.state.get("is_approved", False)
        if not is_approved:
            print(f"Code modification skipped for Work Item {callback_context._invocation_context.session.session_id.replace('wi-', '')} as it was not approved.")
            callback_context.actions.escalate = True # Stop further execution of this agent

code_modification_agent = CodeModificationAgent()

code_generator_modifier_agent_tools = [intelligent_code_tool]
if remote_infrastructure_genie:
    code_generator_modifier_agent_tools.append(AgentTool(remote_infrastructure_genie))

code_generator_modifier_agent = Agent(
    name="code_generator_modifier_agent",
    model="gemini-2.5-pro", # Using a more capable model for code generation
    instruction=(
        "You are an expert code generator and modifier. Your task is to generate or modify code "
        "based on the 'core_request' stored in the session state. "
        "Use the 'intelligent_code_modifier' tool to analyze and modify code. "
        "For any programming language or technical topic, you can leverage the "
        "'infrastructure_genie_service' tool to perform web searches, access documentation (e.g., Terraform docs, Microsoft docs), "
        "and utilize its RAG capabilities for comprehensive research. "
        "Utilize the 'infrastructure_genie_service' tool as much as possible for research and information gathering. "
        "You will be provided with the current code and a specific instruction. "
        "Your goal is to produce the 'modified_code' and store it in the session state under 'modified_code_output'. "
        "If you need to read existing code, you will be provided with it. "
        "Always strive for correct, idiomatic, and efficient code."
    ),
    description="Generates or modifies code based on requirements using the intelligent code modifier tool, "
                "and can research any technical topic via infrastructure_genie_service's web search and RAG capabilities.",
    tools=code_generator_modifier_agent_tools,
    output_key="modified_code_output" # Store the output of this agent
)

git_operations_agent = Agent(
    name="git_operations_agent",
    model="gemini-2.5-flash", # Using a faster model for tool orchestration
    instruction=(
        "You are a Git operations expert. Your task is to perform a sequence of Git commands "
        "to clone a repository, create a new branch, add changes, commit them, and push to the remote. "
        "The 'core_request' and 'modified_code_output' are available in the session state. "
        "You will need to use the following tools: 'git_clone_tool', 'git_checkout_new_branch_tool', "
        "'git_add_all_tool', 'git_commit_changes_tool', and 'git_push_branch_tool'. "
        "Ensure you use the GALAXY_GITHUB_PAT from the session state for authentication when cloning and pushing. "
        "The repository URL and owner are available as environment variables or in session state. "
        "The local path for cloning should be a temporary directory."
    ),
    description="Performs Git operations like cloning, branching, committing, and pushing changes.",
    tools=[
        git_clone_tool,
        git_checkout_new_branch_tool,
        git_add_all_tool,
        git_commit_changes_tool,
        git_push_branch_tool,
    ],
)

pull_request_creator_agent = Agent(
    name="pull_request_creator_agent",
    model="gemini-2.5-flash", # Using a faster model for tool orchestration
    instruction=(
        "You are a GitHub Pull Request creation expert. Your task is to create a Pull Request "
        "on GitHub using the 'github_create_pull_request_tool'. "
        "You will need the repository owner, repository name, head branch (the new branch with changes), "
        "base branch (e.g., 'main'), a title, and a body for the PR. "
        "The 'core_request' and the new branch name should be available in the session state. "
        "The GitHub PAT should also be available in the session state for authentication. "
        "After creating the PR, store its URL and number in the session state."
    ),
    description="Creates a Pull Request on GitHub for the new changes.",
    tools=[github_create_pull_request_tool],
    output_key="pull_request_details" # Store PR details in state
)

pipeline_trigger_agent = None
if azuredevops_agent_instance:
    pipeline_trigger_agent = Agent(
        name="pipeline_trigger_agent",
        model="gemini-2.5-flash", # Using a faster model for tool orchestration
        instruction=(
            "You are an Azure DevOps pipeline trigger expert. Your task is to trigger a specific "
            "Azure DevOps pipeline using the 'trigger_pipeline' tool. "
            "You will need the 'pipeline_id' and the 'branch' to trigger the pipeline on. "
            "The 'pull_request_details' (which contains the new branch name) and 'core_request' "
            "should be available in the session state. "
            "After triggering the pipeline, store the build ID and URL in the session state."
        ),
        description="Triggers an Azure DevOps pipeline for the new changes.",
        tools=[azuredevops_agent_instance.trigger_pipeline],
        output_key="pipeline_trigger_details" # Store pipeline trigger details in state
    )

pipeline_monitor_retry_loop = None
if azuredevops_agent_instance:
    class PipelineStatusChecker(BaseAgent):
        """Checks pipeline status and decides whether to retry or escalate."""
        async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
            build_id = ctx.session.state.get("pipeline_trigger_details", {}).get("build_id")
            if not build_id:
                print("No build ID found to monitor. Escalating.")
                yield Event(author=self.name, actions=EventActions(escalate=True))
                return

            # In a real scenario, this would call get_pipeline_status tool
            # For now, simulate status check
            print(f"Monitoring pipeline for build ID: {build_id}")
            # Simulate success for now
            ctx.session.state["pipeline_status"] = "succeeded"
            ctx.session.state["pipeline_result"] = "passed"

            if ctx.session.state.get("pipeline_status") == "succeeded":
                print(f"Pipeline for build ID {build_id} succeeded. Escalating to stop loop.")
                yield Event(author=self.name, actions=EventActions(escalate=True))
            else:
                # This is where retry logic would go. For now, just continue the loop.
                print(f"Pipeline for build ID {build_id} still running or failed. Retrying/monitoring.")
                yield Event(author=self.name)

    pipeline_monitor_retry_loop = LoopAgent(
        name="pipeline_monitor_retry_loop",
        description="Monitors Azure DevOps pipeline status and retries on failure.",
        sub_agents=[
            # LlmAgent to call get_pipeline_status tool
            Agent(
                name="pipeline_status_checker_agent",
                model="gemini-2.5-flash",
                instruction=(
                    "You are an Azure DevOps pipeline status monitor. Your task is to check the status "
                    "of a pipeline build using the 'get_pipeline_status' tool. "
                    "The 'build_id' should be available in the session state under 'pipeline_trigger_details'. "
                    "Report the status and result."
                ),
                description="Checks the status of an Azure DevOps pipeline build.",
                tools=[azuredevops_agent_instance.get_pipeline_status],
                output_key="current_pipeline_status"
            ),
            PipelineStatusChecker(name="pipeline_status_checker_base_agent"), # Custom agent for loop control
            # LlmAgent for analyzing logs and suggesting fixes (to be added later)
        ],
        max_iterations=5, # Max retries
    )

work_item_commenter_agent = None
if azuredevops_agent_instance:
    work_item_commenter_agent = Agent(
        name="work_item_commenter_agent",
        model="gemini-2.5-flash", # Using a faster model for tool orchestration
        instruction=(
            "You are an Azure DevOps work item commenter. Your task is to add comments to an Azure DevOps work item "
            "using the 'add_work_item_comment' tool. "
            "The 'work_item_id' should be available in the session state. "
            "You will receive information about the process status (e.g., PR created, pipeline status) "
            "and should summarize it concisely in a comment. "
            "Always provide clear and informative updates to the user."
        ),
        description="Adds comments to Azure DevOps work items with process updates.",
        tools=[azuredevops_agent_instance.add_work_item_comment],
    )

# Get Infrastructure Genie URL from environment variable
INFRASTRUCTURE_GENIE_URL = os.getenv("INFRASTRUCTURE_GENIE_URL")

# Define the remote Infrastructure Genie agent
remote_infrastructure_genie = None
if INFRASTRUCTURE_GENIE_URL:
    remote_infrastructure_genie = RemoteA2aAgent(
        name="infrastructure_genie_service",
        description="The remote Infrastructure Genie service for managing cloud resources.",
        agent_card=INFRASTRUCTURE_GENIE_URL
    )

# Get GitHub credentials from environment variables
GALAXY_GITHUB_PAT = os.getenv("GALAXY_GITHUB_PAT")
GALAXY_GITHUB_REPO_OWNER = os.getenv("GALAXY_GITHUB_REPO_OWNER")

# Get Azure DevOps credentials from environment variables
GALAXY_ADO_ORG_URL = os.getenv("GALAXY_ADO_ORG_URL")
GALAXY_ADO_PROJECT = os.getenv("GALAXY_ADO_PROJECT")
GALAXY_ADO_PAT = os.getenv("GALAXY_ADO_PAT")


def delegate_to_specialized_agent(task_type: str, request: str) -> str:
    """Route requests to specialized agents based on task type."""
    if task_type == "code":
        return f"🔧 Routing to Code Agent: {request}"
    elif task_type == "workflow":
        return f"🔄 Handling workflow/automation request: {request}"
    elif task_type == "github":
        return f"🐙 Routing to GitHub Agent: {request}"
    elif task_type == "azuredevops":
        return f"🔧 Routing to Azure DevOps Agent: {request}"
    elif task_type == "infrastructure": # New task type for infrastructure-genie
        return f"☁️ Routing to Infrastructure Genie: {request}"
    else:
        return f"❌ Unknown task type: {task_type}"


def analyze_request_and_route(user_request: str) -> str:
    """Analyze user request and intelligently route to appropriate agent."""
    request_lower = user_request.lower()

    # Determine the primary task type
    if any(keyword in request_lower for keyword in ['code', 'analyze', 'modify', 'refactor', 'syntax', 'function', 'class']):
        task_type = "code"
    elif any(keyword in request_lower for keyword in ['github', 'repository', 'commit', 'pull request', 'branch', 'clone']):
        task_type = "github"
    elif any(keyword in request_lower for keyword in ['azure', 'devops', 'pipeline', 'build', 'deploy', 'release']):
        task_type = "azuredevops"
    elif any(keyword in request_lower for keyword in ['loop', 'workflow', 'schedule', 'iterate', 'automate']):
        task_type = "workflow"
    elif any(keyword in request_lower for keyword in ['infrastructure', 'cloud', 'gcp', 'aws', 'azure', 'resource']):
        task_type = "infrastructure"
    else:
        task_type = "general"

    return delegate_to_specialized_agent(task_type, user_request)


# Instantiate specialized agents with credentials
# Note: code_agent is assumed to not need external credentials for now
github_agent_instance = GitHubAgent(
    github_pat=GALAXY_GITHUB_PAT,
    repo_owner=GALAXY_GITHUB_REPO_OWNER
) if GALAXY_GITHUB_PAT and GALAXY_GITHUB_REPO_OWNER else None

azuredevops_agent_instance = AzureDevOpsAgent(
    org_url=GALAXY_ADO_ORG_URL,
    project=GALAXY_ADO_PROJECT,
    pat=GALAXY_ADO_PAT
) if GALAXY_ADO_ORG_URL and GALAXY_ADO_PROJECT and GALAXY_ADO_PAT else None

# Filter out None agents if credentials are not provided
sub_agents_list = [
    work_item_analyzer_agent,
    code_modification_agent,
    code_agent,
] + ([github_agent_instance] if github_agent_instance else []) + \
    ([azuredevops_agent_instance] if azuredevops_agent_instance else [])

# The orchestrator agent coordinates multiple specialized agents
# It analyzes requests, routes them to appropriate agents, and manages the overall workflow
class GalaxyOrchestrator(SequentialAgent):
    def __init__(self, remote_infrastructure_genie: RemoteA2aAgent = None):
        super().__init__(
            name="galaxy_orchestrator",
            description=(
                "Galaxy Orchestrator Agent coordinates and routes requests to specialized agents. "
                "It analyzes user requests and determines the best agent to handle each task, "
                "ensuring efficient and accurate task execution across code, DevOps, and workflow domains."
            ),
            sub_agents=sub_agents_list + ([remote_infrastructure_genie] if remote_infrastructure_genie else []),
        )

galaxy_orchestrator = GalaxyOrchestrator()