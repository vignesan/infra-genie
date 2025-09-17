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
from app.compliance_guardrails import guardrails, GuardrailAction
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

    async def run_async(self, *, args, tool_context):
        """Run the agent with guardrails and store output in RAG."""
        result = None
        try:
            # Extract query for validation
            query = str(args.get('query', args))

            # 🛡️ BEFORE CALLBACK: Input validation
            print(f"🛡️ Validating input for {self.specialist_name}...")
            is_valid, input_violations = await guardrails.validate_input(
                query=query,
                context={"specialist": self.specialist_name, "args": args}
            )

            if not is_valid:
                blocked_violations = [v for v in input_violations if v.action == GuardrailAction.BLOCK]
                if blocked_violations:
                    violation_messages = [v.message for v in blocked_violations]
                    return {
                        "error": "Input blocked by compliance guardrails",
                        "violations": violation_messages,
                        "specialist": self.specialist_name
                    }

            # Run the original agent if input validation passed
            result = await super().run_async(args=args, tool_context=tool_context)

            # Extract the output text from the result
            output_text = self._extract_output_text(result)

            # 🛡️ AFTER CALLBACK: Output validation and sanitization
            print(f"🛡️ Validating output from {self.specialist_name}...")
            sanitized_output, output_violations = await guardrails.validate_output(
                output=output_text,
                specialist_name=self.specialist_name,
                context={"query": query}
            )

            # Update result with sanitized output if needed
            if sanitized_output != output_text:
                print(f"⚠️ Output sanitized for {self.specialist_name}")
                result = self._update_result_with_sanitized_output(result, sanitized_output)

            # Store in RAG asynchronously (store sanitized version)
            asyncio.create_task(
                store_specialist_output(
                    specialist_name=self.specialist_name,
                    query=query,
                    output=sanitized_output,
                    context={
                        "agent_name": self.specialist_name,
                        "guardrails_violations": len(input_violations + output_violations),
                        "compliance_checked": True
                    }
                )
            )

            # Add compliance metadata to result
            if hasattr(result, '__dict__'):
                result.compliance_info = {
                    "input_violations": len(input_violations),
                    "output_violations": len(output_violations),
                    "sanitized": sanitized_output != output_text
                }

            return result

        except Exception as e:
            print(f"❌ Error in RAG-enabled agent {self.specialist_name}: {e}")
            # Return result if we have it, otherwise return error info
            return result if result is not None else {"error": str(e)}

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

    def _update_result_with_sanitized_output(self, result, sanitized_output: str):
        """Update result object with sanitized output."""
        if isinstance(result, dict):
            if "output" in result:
                result["output"] = sanitized_output
            elif "content" in result:
                result["content"] = sanitized_output
            elif "message" in result:
                result["message"] = sanitized_output
            else:
                result["sanitized_output"] = sanitized_output
        elif hasattr(result, 'content'):
            if hasattr(result.content, 'parts'):
                # Update the first text part
                for part in result.content.parts:
                    if hasattr(part, 'text'):
                        part.text = sanitized_output
                        break
            else:
                result.content = sanitized_output
        return result


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
    instruction="Infrastructure Genie - Smart workflow orchestrator. Choose appropriate specialists based on user requests. SPECIALIST USAGE: 1) For Terraform/infrastructure code questions: use terraform_specialist, 2) For Azure documentation: use microsoft_specialist, 3) For GitHub repository info: use github_specialist, 4) For general cloud questions: use search_specialist, 5) For diagram/visualization requests: FIRST try diagrams_expert (RAG-powered with code generation), then image_generation_specialist if needed. Only generate diagrams when explicitly requested or when user asks for architecture visualization. Respond directly to infrastructure questions without automatically creating diagrams.",
    tools=[github_tool, microsoft_tool, terraform_tool, search_tool, diagrams_tool, image_tool],
)