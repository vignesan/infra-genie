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

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .webhook_handler import webhook_router
from .config import config
from .agent import root_agent

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Startup
    logger.info("🚀 Galaxy Automation Server starting up...")
    logger.info(f"Azure DevOps configured: {config.azure_devops_configured}")
    logger.info(f"Google AI configured: {config.google_ai_configured}")

    yield

    # Shutdown
    logger.info("🔄 Galaxy Automation Server shutting down...")


# Create FastAPI application
app = FastAPI(
    title="Galaxy Automation Server",
    description="Multi-Agent System for Code, DevOps, and Workflow Automation",
    version="0.1.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include webhook router
app.include_router(webhook_router)


@app.get("/")
async def root():
    """Root endpoint with system information."""
    return {
        "message": "Galaxy Automation Server is running",
        "version": "0.1.0",
        "features": {
            "azure_devops_integration": config.azure_devops_configured,
            "google_ai_integration": config.google_ai_configured,
            "webhook_automation": True,
            "github_integration": True,
            "pipeline_monitoring": True
        },
        "endpoints": {
            "webhooks": "/webhook/",
            "azure_devops_webhook": "/webhook/azure-devops/workitem",
            "test_webhook": "/webhook/azure-devops/test",
            "health": "/health"
        }
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    try:
        # Check system health
        health_status = {
            "status": "healthy",
            "timestamp": "2025-01-18T12:00:00Z",
            "services": {
                "azure_devops": "configured" if config.azure_devops_configured else "not_configured",
                "google_ai": "configured" if config.google_ai_configured else "not_configured",
                "webhook_handler": "active",
                "github_client": "active"
            },
            "configuration": {
                "azure_devops_org": config.azure_devops_org or "not_set",
                "azure_devops_project": config.azure_devops_project or "not_set",
                "max_loop_iterations": config.max_loop_iterations
            }
        }

        return health_status

    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=500, detail=f"Health check failed: {str(e)}")


@app.get("/agent/info")
async def agent_info():
    """Get information about the Galaxy agent system."""
    try:
        return {
            "root_agent": {
                "name": root_agent.name,
                "type": type(root_agent).__name__,
                "description": getattr(root_agent, 'description', 'No description available'),
                "sub_agents": [agent.name for agent in getattr(root_agent, 'sub_agents', [])]
            },
            "capabilities": [
                "Automated workflow orchestration",
                "Azure DevOps work item management",
                "GitHub repository operations",
                "Pipeline monitoring and retry logic",
                "Code modification and analysis",
                "Webhook-driven automation"
            ]
        }

    except Exception as e:
        logger.error(f"Failed to get agent info: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/manual/trigger-workflow")
async def manual_trigger_workflow(
    work_item_id: int,
    approval_comment: str = "manually approved - proceed with implementation"
):
    """Manually trigger a workflow for testing purposes."""
    try:
        from .webhook_handler import webhook_handler, WorkItemCommentEvent
        from datetime import datetime

        # Create a test event
        event = WorkItemCommentEvent(
            work_item_id=work_item_id,
            comment_text=approval_comment,
            commented_by="Manual Trigger",
            comment_date=datetime.now().isoformat(),
            work_item_title=f"Manual Test Work Item #{work_item_id}",
            work_item_description="This is a manually triggered test workflow",
            work_item_state="Active",
            work_item_type="Task",
            project="test-project",
            organization="test-org"
        )

        result = await webhook_handler.process_work_item_comment(event)
        return result

    except Exception as e:
        logger.error(f"Manual workflow trigger failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler."""
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "detail": str(exc)}
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8080,
        reload=True,
        log_level="info"
    )