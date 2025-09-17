import os
from google.adk.tools.mcp_tool import MCPToolset, StreamableHTTPConnectionParams

def create_github_mcp():
    return MCPToolset(
        connection_params=StreamableHTTPConnectionParams(
            url="https://api.githubcopilot.com/mcp/",
            headers={
                "Authorization": f"Bearer {os.getenv('GITHUB_PERSONAL_ACCESS_TOKEN')}",
            }
        )
    )

def create_microsoft_learn_mcp():
    """Create Microsoft Learn MCP toolset using Streamable HTTP"""
    return MCPToolset(
        connection_params=StreamableHTTPConnectionParams(
            url="https://learn.microsoft.com/api/mcp",
            headers={}  # No authentication required - public endpoint
        )
    )

def create_terraform_docs_mcp():
    """Create Terraform Docs MCP toolset using Streamable HTTP"""
    return MCPToolset(
        connection_params=StreamableHTTPConnectionParams(
            url="http://localhost:8080/mcp",
            headers={}  # No authentication required - public endpoint
        )
    )





