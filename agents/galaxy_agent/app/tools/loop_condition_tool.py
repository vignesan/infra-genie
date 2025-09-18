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

from google.adk.tools import ToolContext, FunctionTool


def check_task_completion_and_escalate(tool_context: ToolContext) -> dict:
    """Checks if the current task is completed and escalates to terminate the loop if needed."""

    # Increment loop iteration count
    current_loop_count = tool_context.state.get("loop_iteration", 0)
    current_loop_count += 1
    tool_context.state["loop_iteration"] = current_loop_count

    # Define maximum iterations for safety
    max_iterations = 10

    # Get task completion status from state
    task_completed = tool_context.state.get("task_completed", False)
    task_result = tool_context.state.get("task_result", "")

    response_message = f"Loop iteration {current_loop_count}: Task completed = {task_completed}. "

    # Check if task is completed OR maximum iterations reached
    if task_completed:
        print("  Task completed successfully. Setting escalate=True to stop the LoopAgent.")
        tool_context.actions.escalate = True
        response_message += "Task completed, stopping loop."
    elif current_loop_count >= max_iterations:
        print(f"  Max iterations ({max_iterations}) reached. Setting escalate=True to stop the LoopAgent.")
        tool_context.actions.escalate = True
        response_message += "Max iterations reached, stopping loop."
    else:
        print("  Task not completed and max iterations not reached. Loop will continue.")
        response_message += "Loop continues."

    return {
        "status": "Evaluated task completion",
        "message": response_message,
        "iteration": current_loop_count,
        "task_result": task_result
    }


def complete_task_tool(tool_context: ToolContext) -> dict:
    """Mark the current task as completed."""
    tool_context.state["task_completed"] = True
    tool_context.state["task_result"] = "Task successfully completed"

    return {"status": "Task marked as completed"}


# Create the function tools
check_loop_condition = FunctionTool(func=check_task_completion_and_escalate)
complete_task = FunctionTool(func=complete_task_tool)