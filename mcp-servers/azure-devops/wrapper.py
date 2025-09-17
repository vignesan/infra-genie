import os
import json
import subprocess
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse

app = FastAPI()

mcp_process = None

@app.on_event("startup")
async def startup_event():
    print("Wrapper: Startup event triggered.")
    global mcp_process
    try:
        # Ensure the .azure-devops.json is created by the entrypoint.sh
        # The npx command will read this config.
        mcp_process = subprocess.Popen(
            ["npx", "-y", "@wangkanai/devops-mcp"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True, # Use text mode for string communication
            bufsize=1, # Line-buffered
            universal_newlines=True # For cross-platform newline handling
        )
        print(f"Wrapper: MCP process started with PID {mcp_process.pid}")
    except Exception as e:
        print(f"Wrapper: Failed to start MCP process: {e}")
        # In a real app, you might want to exit or mark the app as unhealthy
        raise HTTPException(status_code=500, detail=f"Failed to start MCP process: {e}")

@app.on_event("shutdown")
async def shutdown_event():
    print("Wrapper: Shutdown event triggered.")
    if mcp_process and mcp_process.poll() is None:
        mcp_process.terminate()
        mcp_process.wait(timeout=5) # Give it some time to terminate gracefully
        print("Wrapper: MCP process terminated.")

@app.get("/health")
async def health_check():
    print("Wrapper: Health check requested.")
    if mcp_process and mcp_process.poll() is None:
        return {"status": "ok", "mcp_process_running": True}
    return {"status": "error", "mcp_process_running": False, "mcp_exit_code": mcp_process.returncode if mcp_process else "N/A"}

@app.post("/mcp")
async def handle_mcp_request(request: Request):
    print("Wrapper: MCP request received.")
    if not mcp_process or mcp_process.poll() is not None:
        raise HTTPException(status_code=500, detail="MCP server process not running or crashed.")

    try:
        # Read incoming JSON request from HTTP
        mcp_request_json = await request.json()
        mcp_request_str = json.dumps(mcp_request_json) + "\n" # Add newline for stdio

        # Write to MCP process's stdin
        mcp_process.stdin.write(mcp_request_str)
        mcp_process.stdin.flush()
        print(f"Wrapper: Sent request to MCP: {mcp_request_str.strip()}")

        # Read response from MCP process's stdout
        mcp_response_str = mcp_process.stdout.readline()
        mcp_response_json = json.loads(mcp_response_str)
        print(f"Wrapper: Received response from MCP: {mcp_response_str.strip()}")

        return JSONResponse(content=mcp_response_json)

    except json.JSONDecodeError:
        print("Wrapper: Invalid JSON request or response from MCP.")
        raise HTTPException(status_code=400, detail="Invalid JSON request or response from MCP.")
    except Exception as e:
        stderr_output = "N/A"
        if mcp_process.stderr:
            try:
                stderr_output = mcp_process.stderr.read()
            except Exception as stderr_e:
                stderr_output = f"Error reading stderr: {stderr_e}"

        print(f"Wrapper: Error communicating with MCP: {e}\nMCP Stderr: {stderr_output}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {e}")