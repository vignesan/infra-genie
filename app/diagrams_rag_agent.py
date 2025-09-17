"""
Diagrams RAG Agent: Uses RAG to access diagrams package documentation and examples.
Auto-initializes RAG systems at runtime.
"""

from google.adk.agents import Agent
from google.adk.tools.retrieval.vertex_ai_rag_retrieval import VertexAiRagRetrieval
from google.adk.code_executors import BuiltInCodeExecutor
from vertexai.preview import rag
from .runtime_rag_bootstrap import get_rag_corpus_id, initialize_rag_at_startup
from .diagram_generator_tool import generate_diagram_with_code
import os
import asyncio

# Set up environment
os.environ.setdefault("GOOGLE_CLOUD_PROJECT", "qwiklabs-gcp-03-ec92c6095411")
os.environ.setdefault("GOOGLE_CLOUD_LOCATION", "europe-west2")

# Create RAG tool for diagrams documentation - Auto-initialized at runtime
async def _setup_diagrams_rag():
    """Setup RAG with runtime initialization."""
    try:
        # Get or create diagrams knowledge corpus
        corpus_id = await get_rag_corpus_id("diagrams_knowledge")

        if corpus_id:
            diagrams_rag = VertexAiRagRetrieval(
                name='retrieve_diagrams_docs',
                description='Retrieve diagrams package documentation and examples',
                rag_resources=[
                    rag.RagResource(rag_corpus=corpus_id)
                ],
                similarity_top_k=5,
                vector_distance_threshold=0.5
            )
            print(f"✅ RAG initialized with corpus: {corpus_id}")
            return diagrams_rag
        else:
            print("⚠️ RAG corpus not available, using fallback mode")
            return None
    except Exception as e:
        print(f"⚠️ RAG setup failed, using fallback mode: {e}")
        return None

# Initialize RAG synchronously (will auto-bootstrap if needed)
diagrams_rag = None

def _sync_setup_rag():
    """Synchronous RAG setup for module initialization."""
    global diagrams_rag
    try:
        # Try to run async setup
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        diagrams_rag = loop.run_until_complete(_setup_diagrams_rag())
        loop.close()
    except Exception as e:
        print(f"⚠️ Sync RAG setup failed: {e}")
        diagrams_rag = None

# Setup RAG at module load
_sync_setup_rag()

# Create code executor
code_executor = BuiltInCodeExecutor()

# Create specialized diagrams agent with RAG knowledge
if diagrams_rag:
    diagrams_expert_agent = Agent(
        name="diagrams_expert",
        model="gemini-2.5-flash",
        instruction="""You are a Python diagrams package expert with code execution capabilities. Use RAG to access diagrams documentation and examples.

        Your task:
        1. Use RAG to find relevant diagrams package examples and syntax
        2. Generate accurate Python diagrams code for technical architecture
        3. EXECUTE the generated Python code using your code_executor to create actual diagram images
        4. Focus on AWS, Azure, GCP cloud provider components

        IMPORTANT: When you receive diagram_code from tools, ALWAYS execute it immediately using your code_executor. The code will generate a PNG file that you can reference.

        Always include proper imports, use show=False, and save with filename='generated_diagram'.

        Example code structure:
        ```python
        from diagrams import Diagram
        from diagrams.aws.compute import EC2
        from diagrams.aws.database import RDS

        with Diagram("Architecture", show=False, filename="generated_diagram"):
            web = EC2("Web Server")
            db = RDS("Database")
            web >> db
        ```""",
        code_executor=code_executor,
        output_key="diagrams_result"
    )
else:
    # Fallback agent without RAG
    diagrams_expert_agent = Agent(
        name="diagrams_expert",
        model="gemini-2.5-flash",
        instruction="""You are a Python diagrams package expert with code execution capabilities. Use RAG to access diagrams documentation and examples.

        Your task:
        1. Use RAG to find relevant diagrams package examples and syntax
        2. Generate accurate Python diagrams code for technical architecture
        3. EXECUTE the generated Python code using your code_executor to create actual diagram images
        4. Focus on AWS, Azure, GCP cloud provider components

        IMPORTANT: When you receive diagram_code from tools, ALWAYS execute it immediately using your code_executor. The code will generate a PNG file that you can reference.

        Always include proper imports, use show=False, and save with filename='generated_diagram'.

        Example code structure:
        ```python
        from diagrams import Diagram
        from diagrams.aws.compute import EC2
        from diagrams.aws.database import RDS

        with Diagram("Architecture", show=False, filename="generated_diagram"):
            web = EC2("Web Server")
            db = RDS("Database")
            web >> db
        ```""",
        code_executor=code_executor,
        output_key="diagrams_result"
    )