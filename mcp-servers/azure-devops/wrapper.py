import os
import json
import subprocess
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse

app = FastAPI()

mcp_process = None

@app.on_event("startup")
def startup_event():
    global mcp_process
    # Start the npx process for the MCP server
    # It will read its config from .azure-devops.json created by entrypoint.sh
    try:
        mcp_process = subprocess.Popen(
            ["npx", "-y", "@wangkanai/devops-mcp"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True, # Use text mode for string communication
            bufsize=1, # Line-buffered
            universal_newlines=True # For cross-platform newline handling
        )
        # Give it a moment to start up, though stdio MCPs often don't print much on startup
        # You might add a small delay here if needed, but it's usually not for stdio.
    except Exception as e:
        print(f"Failed to start MCP process: {e}")
        # In a real app, you might want to exit or mark the app as unhealthy

@app.on_event("shutdown")
def shutdown_event():
    if mcp_process and mcp_process.poll() is None:
        mcp_process.terminate()
        mcp_process.wait(timeout=5) # Give it some time to terminate gracefully

@app.get("/health")
def health_check():
    if mcp_process and mcp_process.poll() is None:
        return {"status": "ok", "mcp_process_running": True}
    return {"status": "error", "mcp_process_running": False, "mcp_exit_code": mcp_process.returncode if mcp_process else "N/A"}

@app.post("/mcp")
def handle_mcp_request(request: Request):
    if not mcp_process or mcp_process.poll() is not None:
        raise HTTPException(status_code=500, detail="MCP server process not running or crashed.")

    try:
        # Read incoming JSON request from HTTP
        mcp_request_json = await request.json()
        mcp_request_str = json.dumps(mcp_request_json) + "\n" # Add newline for stdio

        # Write to MCP process's stdin
        mcp_process.stdin.write(mcp_request_str)
        mcp_process.stdin.flush()

        # Read response from MCP process's stdout
        # This assumes the MCP server responds with a single line of JSON per request
        mcp_response_str = mcp_process.stdout.readline()
        mcp_response_json = json.loads(mcp_response_str)

        return JSONResponse(content=mcp_response_json)

    except json.JSONDecodeError:
        return JSONResponse(status_code=400, content={"error": "Invalid JSON request or response from MCP."})
    except Exception as e:
        # Log stderr from MCP process for debugging
        stderr_output = "N/A"
        if mcp_process.stderr:
            try:
                # Try to read any pending stderr output without blocking indefinitely
                stderr_output = mcp_process.stderr.read()
            except Exception as stderr_e:
                stderr_output = f"Error reading stderr: {stderr_e}"

        print(f"Error communicating with MCP: {e}\nMCP Stderr: {stderr_output}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {e}")
