import datetime
import os
import uuid
from zoneinfo import ZoneInfo

import google.auth
from google.adk.agents import LoopAgent
from google.adk.agents.callback_context import CallbackContext
from .orchestrator_agent import GalaxyOrchestrator, galaxy_orchestrator # Import the class and instance
from .checker_agent import checker_agent

_, project_id = google.auth.default()
os.environ.setdefault("GOOGLE_CLOUD_PROJECT", "qwiklabs-gcp-03-ec92c6095411")
os.environ.setdefault("GOOGLE_CLOUD_LOCATION", "europe-west4")
os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI", "True")



def set_session(callback_context: CallbackContext):
    """Sets a unique ID and timestamp in the callback context's state.
    This function is called before the main LoopAgent executes.
    """
    callback_context.state["unique_id"] = str(uuid.uuid4())
    callback_context.state["timestamp"] = datetime.datetime.now(
        ZoneInfo("UTC")
    ).isoformat()
    callback_context.state["task_completed"] = False


# Galaxy Main LoopAgent - Coordinates orchestrator and checker agents in a loop
# This follows the ADK pattern where:
# 1. Orchestrator agent handles the main workflow and routes to specialized agents
# 2. Checker agent evaluates completion and controls loop termination
# The process continues until the checker agent determines the task is complete

galaxy_main_loop = LoopAgent(
    name="galaxy_main_loop",
    description="Galaxy main loop that coordinates orchestrator and checker agents for iterative task completion.",
    sub_agents=[
        GalaxyOrchestrator(),
        checker_agent,        # Second, check completion and potentially stop the loop
    ],
    before_agent_callback=set_session,
)

# Set the LoopAgent as the root agent
root_agent = galaxy_main_loop