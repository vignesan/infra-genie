import os
import google.auth
from google.adk.agents import Agent
from google.adk.tools import AgentTool
from google.adk.tools import google_search
from app.mcp_github import create_github_mcp, create_microsoft_learn_mcp, create_terraform_docs_mcp
from app.image_generation_tool import generate_technical_image
from app.diagrams_rag_agent import diagrams_expert_agent
from app.intelligent_code_generator import code_generator_agent


_, project_id = google.auth.default()
os.environ.setdefault("GOOGLE_CLOUD_PROJECT", "qwiklabs-gcp-03-ec92c6095411")
os.environ.setdefault("GOOGLE_CLOUD_LOCATION", "europe-west4")
os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI", "True")



# Create specialized sub-agents for each MCP domain
github_sub_agent = Agent(
    name="github_specialist",
    model="gemini-2.5-flash",
    instruction=(
        "GitHub specialist with comprehensive MCP tools for repository operations. "
        "You can perform ALL GitHub operations including:\n"
        "- Repository analysis and file operations\n"
        "- Branch creation and management\n"
        "- File reading, writing, and modification\n"
        "- Commit operations and pull requests\n"
        "- Issue and release management\n\n"
        "For file modification workflows:\n"
        "1. Read current file content from specified repository/branch\n"
        "2. Create new branch if requested\n"
        "3. Update files with provided content\n"
        "4. Commit changes with meaningful messages\n"
        "5. Create pull requests if requested\n\n"
        "Always provide detailed operation results and any errors encountered. "
        "Use GitHub tools immediately when requested."
    ),
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
code_generator_tool = AgentTool(agent=code_generator_agent)

root_agent = Agent(
    name="infrastructure_genie",
    model="gemini-2.5-flash",
    instruction=(
        "Infrastructure Genie - Smart workflow orchestrator with comprehensive capabilities.\n\n"
        "CAPABILITIES:\n"
        "1) DIAGRAMS: Generate technical diagrams using diagrams_expert (preferred) or image_generation_specialist\n"
        "2) CODE GENERATION: Create complete applications, APIs, infrastructure code using code_generator_specialist\n"
        "3) GITHUB WORKFLOWS: Use enhanced_github_specialist for advanced repository operations\n"
        "4) RESEARCH: Use GitHub, Microsoft Learn, Terraform docs, and web search specialists\n\n"
        "GITHUB FILE MODIFICATION WORKFLOW:\n"
        "For requests to modify files in GitHub repositories, follow this EXACT sequence:\n"
        "1. Use github_specialist to fetch the current file from the specified repository and branch\n"
        "2. Use code_generator_specialist to modify the file content with the requested changes\n"
        "3. Use github_specialist to create a new branch and commit the modified file\n"
        "4. Optionally use github_specialist to create a pull request\n\n"
        "PRIORITY ORDER:\n"
        "- For diagrams → diagrams_expert first\n"
        "- For GitHub file modifications → github_specialist → code_generator_specialist → github_specialist\n"
        "- For code generation → code_generator_specialist\n"
        "- For infrastructure → terraform_specialist\n"
        "- For Azure/Microsoft → microsoft_specialist\n"
        "- For GitHub repositories → github_specialist\n"
        "- For general research → search_specialist"
    ),
    tools=[
        github_tool,
        microsoft_tool,
        terraform_tool,
        search_tool,
        diagrams_tool,
        image_tool,
        code_generator_tool
    ],
)