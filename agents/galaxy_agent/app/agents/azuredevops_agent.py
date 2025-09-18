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

import asyncio
from google.adk.agents import Agent
from ..azure_devops_client import AzureDevOpsClient

class AzureDevOpsAgent(Agent):
    def __init__(self, org_url: str, project: str, pat: str):
        super().__init__(
            name="galaxy_azuredevops_agent",
            model="gemini-2.5-flash",
            instruction=(
                "You are the Galaxy Azure DevOps Agent - specialized in Azure DevOps operations and CI/CD management. "
                "Your expertise includes work item management, pipeline automation, and build monitoring. "
                "\n\nAvailable tools:\n"
                "- create_work_item: Create work items (Task, Bug, User Story, etc.)\n"
                "- update_work_item: Update existing work items\n"
                "- query_work_items: Query and search work items\n"
                "- add_work_item_comment: Add comments to work items\n"
                "- trigger_pipeline: Trigger build pipelines\n"
                "- get_pipeline_status: Get pipeline status and output for reiteration\n"
                "- list_pipelines: List available pipelines\n"
                "\nUse these tools to manage Azure DevOps workflows, track work items, and automate CI/CD processes. "
                "You can monitor pipeline outputs and use the results for iterative improvements."
            ),
            tools=[
                self.create_work_item, self.update_work_item, self.query_work_items, self.add_work_item_comment,
                self.trigger_pipeline, self.get_pipeline_status, self.list_pipelines
            ],
        )
        self.client = AzureDevOpsClient(org_url, project, pat)

    def create_work_item(self, work_item_type: str, title: str, description: str = "", assigned_to: str = "", state: str = "New", priority: int = 2) -> str:
        """Create a new Azure DevOps work item."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(
            self.client.create_work_item(
                work_item_type=work_item_type,
                title=title,
                description=description,
                assigned_to=assigned_to,
                state=state,
                priority=priority
            )
        )
        loop.close()
        if result["status"] == "success":
            return f"✅ Work Item Created:\n📋 ID: {result['work_item_id']}\n📝 Title: {result['title']}\n🔄 State: {result['state']}\n🔗 URL: {result.get('url', 'N/A')}"
        else:
            return f"❌ Failed to create work item: {result.get('message', 'Unknown error')}"

    def update_work_item(self, work_item_id: int, title: str = "", description: str = "", assigned_to: str = "", state: str = "", priority: int = None) -> str:
        """Update an existing Azure DevOps work item."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        kwargs = {}
        if title: kwargs['title'] = title
        if description: kwargs['description'] = description
        if assigned_to: kwargs['assigned_to'] = assigned_to
        if state: kwargs['state'] = state
        if priority is not None: kwargs['priority'] = priority
        result = loop.run_until_complete(
            self.client.update_work_item(work_item_id, **kwargs)
        )
        loop.close()
        if result["status"] == "success":
            return f"✅ Work Item Updated:\n📋 ID: {result['work_item_id']}\n📝 Title: {result['title']}\n🔄 State: {result['state']}\n🔗 URL: {result.get('url', 'N/A')}"
        else:
            return f"❌ Failed to update work item: {result.get('message', 'Unknown error')}"

    def query_work_items(self, work_item_type: str = "", state: str = "", assigned_to: str = "", max_results: int = 20) -> str:
        """Query Azure DevOps work items."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(
            self.client.query_work_items(
                work_item_type=work_item_type or None,
                state=state or None,
                assigned_to=assigned_to or None,
                max_results=max_results
            )
        )
        loop.close()
        if result["status"] == "success":
            work_items = result["work_items"]
            if not work_items:
                return "📋 No work items found matching the criteria"
            response = f"📋 Found {result['count']} work items:\n\n"
            for wi in work_items[:10]:  # Show first 10
                response += f"🔹 #{wi['id']} - {wi['title']}\n   State: {wi['state']} | Type: {wi['type']}\n   Assigned: {wi['assigned_to']}\n\n"
            if len(work_items) > 10:
                response += f"... and {len(work_items) - 10} more items"
            return response
        else:
            return f"❌ Failed to query work items: {result.get('message', 'Unknown error')}"

    def add_work_item_comment(self, work_item_id: int, comment_text: str) -> str:
        """Add a comment to an Azure DevOps work item."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(
            self.client.add_work_item_comment(work_item_id, comment_text)
        )
        loop.close()
        if result["status"] == "success":
            return f"✅ Comment Added:\n📋 Work Item: #{work_item_id}\n💬 Comment: {comment_text}\n📅 Added: {result.get('added_date', 'N/A')}"
        else:
            return f"❌ Failed to add comment: {result.get('message', 'Unknown error')}"

    def trigger_pipeline(self, pipeline_id: int, branch: str = "main", parameters: str = "") -> str:
        """Trigger an Azure DevOps pipeline."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        params = {}
        if parameters:
            for param in parameters.split(","):
                if "=" in param:
                    key, value = param.split("=", 1)
                    params[key.strip()] = value.strip()
        result = loop.run_until_complete(
            self.client.trigger_pipeline(pipeline_id, branch, params or None)
        )
        loop.close()
        if result["status"] == "success":
            return f"🚀 Pipeline Triggered:\n🔧 Pipeline ID: {pipeline_id}\n📋 Build ID: {result['build_id']}\n🔢 Build Number: {result['build_number']}\n🌿 Branch: {branch}\n📅 Queue Time: {result.get('queue_time', 'N/A')}\n🔗 URL: {result.get('url', 'N/A')}"
        else:
            return f"❌ Failed to trigger pipeline: {result.get('message', 'Unknown error')}"

    def get_pipeline_status(self, build_id: int) -> str:
        """Get the status and output of a pipeline build."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(
            self.client.get_pipeline_status(build_id)
        )
        loop.close()
        if result["status"] == "success":
            response = f"📊 Pipeline Status:\n🔧 Build ID: {build_id}\n🔢 Build Number: {result['build_number']}\n📊 Status: {result['pipeline_status']}\n🎯 Result: {result.get('result', 'In Progress')}\n⏱️ Duration: {result.get('duration', 'N/A')}\n🔗 URL: {result.get('url', 'N/A')}"
            if result.get('logs'):
                response += f"\n\n📝 Recent Logs ({len(result['logs'])} entries):"
                for log in result['logs'][:3]:  # Show first 3
                    if 'content' in log:
                        response += f"\n🔹 {log.get('type', 'Log')}: {log['content'][:200]}..."
                    else:
                        response += f"\n🔹 {log.get('message', 'Log entry')}"
            return response
        else:
            return f"❌ Failed to get pipeline status: {result.get('message', 'Unknown error')}"

    def list_pipelines(self) -> str:
        """List available Azure DevOps pipelines."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(
            self.client.list_pipelines()
        )
        loop.close()
        if result["status"] == "success":
            pipelines = result["pipelines"]
            if not pipelines:
                return "📋 No pipelines found in the project"
            response = f"📋 Available Pipelines ({result['count']} total):\n\n"
            for pipeline in pipelines[:10]:  # Show first 10
                response += f"🔧 #{pipeline['id']} - {pipeline['name']}\n   Path: {pipeline.get('path', 'N/A')}\n   Status: {pipeline.get('queue_status', 'N/A')}\n\n"
            if len(pipelines) > 10:
                response += f"... and {len(pipelines) - 10} more items"
            return response
        else:
            return f"❌ Failed to list pipelines: {result.get('message', 'Unknown error')}"

# Instantiate the agent (will be replaced by instantiation in orchestrator_agent.py)
azuredevops_agent = AzureDevOpsAgent(
    org_url=os.getenv("GALAXY_ADO_ORG_URL"),
    project=os.getenv("GALAXY_ADO_PROJECT"),
    pat=os.getenv("GALAXY_ADO_PAT"),
)
