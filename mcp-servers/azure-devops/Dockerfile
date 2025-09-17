FROM node:20-slim AS mcp_builder

WORKDIR /usr/src/app
# Install the MCP server globally
RUN npm install -g @wangkanai/devops-mcp

# Stage 2: Build the Python wrapper application
FROM python:3.11-slim-buster AS python_wrapper

# Install FastAPI and Uvicorn
RUN pip install --no-cache-dir fastapi uvicorn --break-system-packages

WORKDIR /usr/src/app

# Copy the entrypoint script and wrapper
COPY entrypoint.sh .
COPY wrapper.py .
RUN chmod +x entrypoint.sh

# Copy the npx executable and the installed MCP package from the mcp_builder stage
COPY --from=mcp_builder /usr/local/bin/npx /usr/local/bin/npx
COPY --from=mcp_builder /usr/local/lib/node_modules/@wangkanai/devops-mcp /usr/local/lib/node_modules/@wangkanai/devops-mcp

# Set the entrypoint
ENTRYPOINT ["./entrypoint.sh"]

# The command to run the wrapper, which will then manage the npx process
CMD ["uvicorn", "wrapper:app", "--host", "0.0.0.0", "--port", "8080"]