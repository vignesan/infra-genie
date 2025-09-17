"""
LLM-generated diagram tool: Uses LLM to write Python diagrams code and executes with ADK code executor.
"""

from google.adk.tools import ToolContext
from google.adk.code_executors import BuiltInCodeExecutor
from google import genai
from google.genai import types
from .intelligent_knowledge_system import get_smart_diagrams_knowledge
from .diagrams_rag_system import get_diagrams_knowledge_from_rag
from .live_docs_fetcher import get_live_diagrams_knowledge
import os


# Set up Vertex AI environment
import google.auth
_, project_id = google.auth.default()
os.environ.setdefault("GOOGLE_CLOUD_PROJECT", "qwiklabs-gcp-03-ec92c6095411")
os.environ.setdefault("GOOGLE_CLOUD_LOCATION", "europe-west4")
os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI", "True")

# Configure the genai client
client = genai.Client(vertexai=True)

# Initialize code executor
code_executor = BuiltInCodeExecutor()


async def generate_diagram_with_code(architecture_description: str, tool_context: ToolContext):
    """
    Generate technical diagrams using LLM-generated Python diagrams code.
    Returns both the generated code and instructions for the agent to execute it.
    """
    try:
        # Use intelligent knowledge system to get diagrams information
        print("🔍 Getting intelligent diagrams knowledge...")
        smart_knowledge = await get_smart_diagrams_knowledge(architecture_description)

        # Generate Python diagrams code using the knowledge
        print("🐍 Generating Python diagrams code...")
        diagram_code = await generate_diagram_code_with_llm(architecture_description, smart_knowledge)

        # Return the code with clear instructions for agent execution
        return {
            "status": "success",
            "message": f"Python diagrams code generated for: {architecture_description}",
            "diagram_code": diagram_code,
            "execution_instructions": "Execute this Python code using your code_executor to generate the diagram image. The code will create a file named 'generated_diagram.png'.",
            "method": "code_generation"
        }

    except Exception as e:
        return {
            "status": "error",
            "message": f"Diagram code generation failed: {str(e)}"
        }


async def generate_diagram_code_with_llm(description: str) -> str:
    """Use LLM to generate Python diagrams code based on architecture description."""

    # Step 1: Try RAG first for existing knowledge
    rag_knowledge = await get_diagrams_knowledge_from_rag(description)

    # Step 2: If RAG knowledge insufficient, use intelligent system (RAG + WebFetch)
    if not rag_knowledge or len(rag_knowledge.strip()) < 100:
        print("RAG knowledge insufficient, using intelligent system...")
        smart_knowledge = await get_smart_diagrams_knowledge(description)

        # Step 3: Add new knowledge to RAG for future use
        # TODO: Store smart_knowledge in RAG corpus

    else:
        print("Using RAG knowledge for diagram generation...")
        smart_knowledge = rag_knowledge

    # Step 4: Fallback to live docs if all else fails
    if not smart_knowledge or len(smart_knowledge.strip()) < 50:
        print("Using live docs fallback...")
        smart_knowledge = await get_live_diagrams_knowledge()

    prompt = f"""
{smart_knowledge}

Generate Python code using the 'diagrams' package to create a technical architecture diagram.

Architecture Description: {description}

Requirements:
1. Use appropriate cloud provider components from the reference above
2. Create logical clusters for grouping
3. Use proper connections with >> operator
4. Set filename="generated_diagram" and show=False
5. Direction should be "TB" or "LR" based on complexity

Generate ONLY the Python code, no explanations:
"""

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[prompt],
            config=types.GenerateContentConfig(
                temperature=0.1,
                max_output_tokens=1000
            )
        )

        # Extract code from response
        generated_code = response.text

        # Clean up the code (remove markdown formatting if present)
        if "```python" in generated_code:
            generated_code = generated_code.split("```python")[1].split("```")[0]
        elif "```" in generated_code:
            generated_code = generated_code.split("```")[1].split("```")[0]

        return generated_code.strip()

    except Exception as e:
        # Fallback to basic template if LLM fails
        return create_fallback_diagram_code(description)


def create_fallback_diagram_code(description: str) -> str:
    """Fallback diagram code if LLM generation fails."""
    return '''
from diagrams import Diagram, Cluster, Edge
from diagrams.aws.compute import EC2
from diagrams.aws.database import RDS
from diagrams.onprem.client import Users

with Diagram("Architecture", filename="generated_diagram", show=False, direction="TB"):
    users = Users("Users")

    with Cluster("Cloud Infrastructure"):
        web = EC2("Application")
        db = RDS("Database")

        users >> web >> db
'''


