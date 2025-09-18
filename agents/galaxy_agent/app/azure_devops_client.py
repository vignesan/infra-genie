import os
import base64
import httpx # Using httpx for async requests
import json

class AzureDevOpsClient:
    def __init__(self, org_url: str, project: str, pat: str):
        self.org_url = org_url.rstrip('/') # Ensure no trailing slash
        self.project = project
        self.pat = pat
        self.headers = {
            "Authorization": f"Basic {base64.b64encode(f':{self.pat}'.encode()).decode()}",
            "Content-Type": "application/json",
        }
        self.base_api_url = f"{self.org_url}/{self.project}/_apis"

    async def _call_api(self, method: str, endpoint: str, data: dict = None, params: dict = None):
        url = f"{self.base_api_url}/{endpoint}"
        async with httpx.AsyncClient() as client:
            try:
                response = await client.request(method, url, json=data, params=params, headers=self.headers)
                response.raise_for_status() # Raise an exception for 4xx or 5xx responses
                return {"status": "success", "data": response.json()}
            except httpx.HTTPStatusError as e:
                return {"status": "error", "message": f"API error: {e.response.status_code} - {e.response.text}"}
            except httpx.RequestError as e:
                return {"status": "error", "message": f"Request error: {e}"}
            except Exception as e:
                return {"status": "error", "message": f"An unexpected error occurred: {e}"}

    async def create_work_item(self, work_item_type: str, title: str, description: str = "", assigned_to: str = "", state: str = "New", priority: int = 2):
        # Placeholder for actual API call
        return {"status": "success", "work_item_id": 123, "title": title, "state": state, "url": "http://example.com"}

    async def update_work_item(self, work_item_id: int, **kwargs):
        # Placeholder for actual API call
        return {"status": "success", "work_item_id": work_item_id, "title": "Updated", "state": "Active", "url": "http://example.com"}

    async def query_work_items(self, work_item_type: str = None, state: str = None, assigned_to: str = None, max_results: int = 20):
        # Placeholder for actual API call
        return {"status": "success", "count": 0, "work_items": []}

    async def add_work_item_comment(self, work_item_id: int, comment_text: str):
        # Placeholder for actual API call
        return {"status": "success", "work_item_id": work_item_id, "added_date": "today"}

    async def trigger_pipeline(self, pipeline_id: int, branch: str = "main", parameters: dict = None):
        # Placeholder for actual API call
        return {"status": "success", "build_id": 456, "build_number": "20250917.1", "url": "http://example.com"}

    async def get_pipeline_status(self, build_id: int):
        # Placeholder for actual API call
        return {"status": "success", "build_number": "20250917.1", "pipeline_status": "completed", "result": "succeeded"}

    async def list_pipelines(self):
        # Placeholder for actual API call
        return {"status": "success", "count": 0, "pipelines": []}
