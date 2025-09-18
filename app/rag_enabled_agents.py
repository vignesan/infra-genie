import os
import google.auth
from google.adk.agents import Agent
from google.adk.tools import AgentTool
from google.adk.tools import google_search
from app.mcp_github import create_github_mcp, create_microsoft_learn_mcp, create_terraform_docs_mcp
from app.image_generation_tool import generate_technical_image
from app.diagrams_rag_agent import diagrams_expert_agent
from google.adk.a2a import RemoteA2aAgent


_, project_id = google.auth.default()
os.environ.setdefault("GOOGLE_CLOUD_PROJECT", "qwiklabs-gcp-03-ec92c6095411")
os.environ.setdefault("GOOGLE_CLOUD_LOCATION", "europe-west4")
os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI", "True")

# Get Galaxy App URL from environment variable
GALAXY_APP_URL = os.getenv("GALAXY_APP_URL")

# Define the remote Galaxy App agent
remote_galaxy_app = None
if GALAXY_APP_URL:
    remote_galaxy_app = RemoteA2aAgent(
        name="galaxy_app_service",
        description="The remote Galaxy application service for various tasks.",
        agent_card=GALAXY_APP_URL
    )

# Create specialized sub-agents for each MCP domain
github_sub_agent = Agent(
    name="github_specialist",
    model="gemini-2.5-flash",
    instruction="GitHub specialist with MCP tools. Use GitHub tools immediately. Extract repository architecture details, tech stack, deployment configs for diagram generation. Provide your response under 'github_info' key with essential info only.",
    tools=[create_github_mcp()],
    output_key="github_info",
)

microsoft_sub_agent = Agent(
    name="microsoft_specialist",
    model="gemini-2.5-flash",
    instruction="Microsoft Learn specialist with MCP tools. Use Microsoft Learn tools immediately. Extract Azure service details, architecture patterns, component relationships for diagram generation. Focus on Azure services, configs, best practices. Provide your response under 'microsoft_info' key with essential Azure/Microsoft info only.",
    tools=[create_microsoft_learn_mcp()],
    output_key="microsoft_info",
)

terraform_sub_agent = Agent(
    name="terraform_specialist",
    model="gemini-2.5-flash",
    instruction="Terraform specialist with MCP tools. Use Terraform docs tools immediately. Generate infrastructure-as-code, NOT diagrams. For Azure resources, reference microsoft_info input for context. Focus on Terraform resource blocks, configurations, providers. Provide your response under 'terraform_info' key with essential resource config only.",
    tools=[create_terraform_docs_mcp()],
    output_key="terraform_info",
)

search_sub_agent = Agent(
    name="search_specialist",
    model="gemini-2.5-flash",
    instruction="Technical search specialist with Google Search. Search technical topics only. Focus on general technical knowledge, best practices, architecture patterns when other specialists lack specific info. Provide your response under 'search_info' key with essential findings only.",
    tools=[google_search],
    output_key="search_info",
)

image_generation_sub_agent = Agent(
    name="image_generation_specialist",
    model="gemini-2.5-flash",
    instruction="Image generation specialist. ONLY use relevant context provided (github_info, microsoft_info, search_info - NOT terraform_info as it's for code). Analyze architecture context to identify: 1) Cloud providers, 2) Services/components, 3) Architecture patterns, 4) Data flows. Use intelligent RAG+WebFetch system to get diagrams package knowledge, generate Python diagrams code, execute with code executor. Provide your response under 'image_result' key with status only.",
    tools=[generate_technical_image],
    output_key="image_result",
)

# Wrap sub-agents as tools using AgentTool
github_tool = AgentTool(agent=github_sub_agent)
microsoft_tool = AgentTool(agent=microsoft_sub_agent)
terraform_tool = AgentTool(agent=terraform_sub_agent)
search_tool = AgentTool(agent=search_sub_agent)
image_tool = AgentTool(agent=image_generation_sub_agent)
diagrams_tool = AgentTool(agent=diagrams_expert_agent)

root_agent = Agent(
    name="infrastructure_genie",
    model="gemini-2.5-flash",
    instruction="Infrastructure Genie - Smart workflow orchestrator. ALWAYS generate diagrams! DIAGRAM PRIORITY: 1) For diagram requests, FIRST try diagrams_expert (RAG-powered diagram specialist with code generation). 2) ONLY if diagrams_expert lacks info or fails, gather context from specialists: Azure=microsoft_specialist, GCP/AWS=search_specialist, GitHub=github_specialist. 3) LAST RESORT: use image_generation_specialist (pure AI generation). The diagrams_expert is PREFERRED because it uses RAG knowledge, generates accurate Python code, and creates professional technical diagrams. Use image_generation_specialist only when programmatic approach fails.",
    tools=[
        github_tool, 
        microsoft_tool, 
        terraform_tool, 
        search_tool, 
        diagrams_tool, 
        image_tool
    ] + ([AgentTool(agent=remote_galaxy_app)] if remote_galaxy_app else []),
)