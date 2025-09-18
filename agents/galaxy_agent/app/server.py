import os
from fastapi import FastAPI, Request, HTTPException
from google.adk.cli.fast_api import get_fast_api_app
from .agent import root_agent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types as genai_types

# AGENT_DIR should point to the directory containing agent.py
# If server.py is in agents/galaxy_agent/app/, then AGENT_DIR is also agents/galaxy_agent/app/
AGENT_DIR = os.path.dirname(os.path.abspath(__file__))

app: FastAPI = get_fast_api_app(
    agents_dir=AGENT_DIR,
    web=True, # Enable web UI for local testing/direct access
    # For deployment, you'd typically configure session_service_uri, artifact_service_uri etc.
    # based on environment variables or cloud services.
)

app.title = "Galaxy App"
app.description = "API for the Galaxy application"

# Placeholder for the main agent's run function
# In a real scenario, this would trigger the agent's workflow
async def trigger_galaxy_agent_workflow(work_item_id: str, comment_text: str, commented_by: str):
    print(f"Received webhook for Work Item {work_item_id}: '{comment_text}' by {commented_by}")

    session_service = InMemorySessionService()
    session = await session_service.create_session(app_name="galaxy-app", user_id=commented_by, session_id=f"wi-{work_item_id}")

    # Get GitHub PAT from environment variable and store in session state
    github_pat = os.getenv("GALAXY_GITHUB_PAT")
    if github_pat:
        session.state["GALAXY_GITHUB_PAT"] = github_pat
    else:
        print("Warning: GALAXY_GITHUB_PAT environment variable not set. Git operations may fail.")

    runner = Runner(agent=root_agent, app_name="galaxy-app", session_service=session_service)

    # The initial message to the agent will include the work item ID and the comment.
    # The agent's instruction will guide it on how to process this.
    initial_message_text = f"Work item {work_item_id} commented by {commented_by}: {comment_text}"

    async for event in runner.run_async(
        user_id=commented_by,
        session_id=f"wi-{work_item_id}",
        new_message=genai_types.Content(parts=[genai_types.Part.from_text(text=initial_message_text)])
    ):
        if event.is_final_response():
            print(f"Agent final response for Work Item {work_item_id}: {event.content.text}")
        elif event.content and event.content.parts:
            for part in event.content.parts:
                if part.text:
                    print(f"Agent intermediate response for Work Item {work_item_id}: {part.text}")

@app.post("/webhook/azure-devops")
async def azure_devops_webhook(request: Request):
    try:
        payload = await request.json()
        event_type = payload.get("eventType")

        if event_type == "workitem.commented":
            work_item_id = payload.get("resource", {}).get("workItemId")
            comment_text = payload.get("resource", {}).get("comment", {}).get("text")
            commented_by = payload.get("resource", {}).get("comment", {}).get("createdBy", {}).get("uniqueName")

            if not work_item_id or not comment_text:
                raise HTTPException(status_code=400, detail="Missing work item ID or comment text in payload.")

            # Trigger your ADK agent workflow here
            await trigger_galaxy_agent_workflow(str(work_item_id), comment_text, commented_by)

            return {"status": "success", "message": "Webhook received and processed."}
        else:
            return {"status": 200, "message": f"Event type {event_type} not handled."}

    except Exception as e:
        print(f"Error processing webhook: {e}")
        raise HTTPException(status_code=500, detail=f"Error processing webhook: {e}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)