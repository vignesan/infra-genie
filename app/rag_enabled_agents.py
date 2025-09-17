"""
RAG-Enabled Agents: Wrapper agents that automatically store their outputs in RAG corpora.
"""

import asyncio
from google.adk.agents import Agent
from google.adk.tools import AgentTool
from google.adk.tools import google_search
from app.mcp_github import create_github_mcp, create_microsoft_learn_mcp, create_terraform_docs_mcp
from app.image_generation_tool import generate_technical_image
from app.diagrams_rag_agent import diagrams_expert_agent
from app.rag_storage_system import store_specialist_output
import os
import google.auth


# Set up environment
_, project_id = google.auth.default()
os.environ.setdefault("GOOGLE_CLOUD_PROJECT", "qwiklabs-gcp-03-ec92c6095411")
os.environ.setdefault("GOOGLE_CLOUD_LOCATION", "europe-west4")
os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI", "True")


class RagEnabledAgentTool(AgentTool):
    """AgentTool wrapper that automatically stores outputs in RAG."""

    def __init__(self, agent: Agent, specialist_name: str):
        super().__init__(agent=agent)
        self.specialist_name = specialist_name

    async def __call__(self, query: str, invocation_context=None):
        """Run the agent and store output in RAG."""
        try:
            # Run the original agent
            result = await super().__call__(query, invocation_context)

            # Extract the output text from the result
            output_text = self._extract_output_text(result)

            # Store in RAG asynchronously (don't block the main flow)
            asyncio.create_task(
                store_specialist_output(
                    specialist_name=self.specialist_name,
                    query=query,
                    output=output_text,
                    context={"agent_name": self.specialist_name}
                )
            )

            return result

        except Exception as e:
            print(f"❌ Error in RAG-enabled agent {self.specialist_name}: {e}")
            return result  # Return original result even if RAG storage fails

    def _extract_output_text(self, result) -> str:
        """Extract text output from agent result."""
        if isinstance(result, dict):
            if "output" in result:
                return str(result["output"])
            elif "content" in result:
                return str(result["content"])
            elif "message" in result:
                return str(result["message"])
            else:
                return str(result)
        elif hasattr(result, 'content'):
            if hasattr(result.content, 'parts'):
                return ' '.join([part.text for part in result.content.parts if hasattr(part, 'text')])
            else:
                return str(result.content)
        else:
            return str(result)


# Create the base specialist agents
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

# Create RAG-enabled wrappers
github_tool = RagEnabledAgentTool(agent=github_sub_agent, specialist_name="github_specialist")
microsoft_tool = RagEnabledAgentTool(agent=microsoft_sub_agent, specialist_name="microsoft_specialist")
terraform_tool = RagEnabledAgentTool(agent=terraform_sub_agent, specialist_name="terraform_specialist")
search_tool = RagEnabledAgentTool(agent=search_sub_agent, specialist_name="search_specialist")
image_tool = RagEnabledAgentTool(agent=image_generation_sub_agent, specialist_name="image_generation_specialist")
diagrams_tool = RagEnabledAgentTool(agent=diagrams_expert_agent, specialist_name="diagrams_expert")

# Create the root agent with RAG-enabled tools
root_agent = Agent(
    name="infrastructure_genie",
    model="gemini-2.5-flash",
    instruction="Infrastructure Genie - Smart workflow orchestrator. ALWAYS generate diagrams! DIAGRAM PRIORITY: 1) For diagram requests, FIRST try diagrams_expert (RAG-powered diagram specialist with code generation). 2) ONLY if diagrams_expert lacks info or fails, gather context from specialists: Azure=microsoft_specialist, GCP/AWS=search_specialist, GitHub=github_specialist. 3) LAST RESORT: use image_generation_specialist (pure AI generation). The diagrams_expert is PREFERRED because it uses RAG knowledge, generates accurate Python code, and creates professional technical diagrams. Use image_generation_specialist only when programmatic approach fails.",
    tools=[github_tool, microsoft_tool, terraform_tool, search_tool, diagrams_tool, image_tool],
)