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

from google.adk.agents import Agent
from .tools.loop_condition_tool import check_loop_condition


# This agent is responsible for checking task completion and controlling loop termination
# It evaluates whether the current task has been completed successfully and decides
# whether the LoopAgent should continue or terminate
checker_agent = Agent(
    name="galaxy_checker_agent",
    model="gemini-2.5-flash",
    instruction=(
        "You are the Galaxy Checker Agent - responsible for evaluating task completion and controlling loop flow. "
        "Your role is to determine if the current task has been completed successfully and whether the loop should continue. "
        "\n\nYour responsibilities:\n"
        "1. Review the current state and results from previous agents\n"
        "2. Determine if the task objectives have been met\n"
        "3. Call the check_task_completion_and_escalate tool to evaluate loop termination\n"
        "4. Provide clear feedback on task status and next steps\n"
        "\nAlways be thorough in your evaluation but decisive in your conclusions."
    ),
    tools=[check_loop_condition],
    output_key="checker_output",
)