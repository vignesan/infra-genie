"""
Complete RAG system for diagrams package documentation.
Google Search → RAG Storage → RAG Retrieval → LLM Code Generation
"""

import os
from google.adk.tools import google_search
from google.adk.tools.retrieval.vertex_ai_rag_retrieval import VertexAiRagRetrieval
from vertexai.preview import rag
import vertexai

# Initialize Vertex AI
vertexai.init(
    project=os.environ.get("GOOGLE_CLOUD_PROJECT", "qwiklabs-gcp-03-ec92c6095411"),
    location=os.environ.get("GOOGLE_CLOUD_LOCATION", "europe-west4")
)


class DiagramsRagSystem:
    """Complete RAG system for diagrams package knowledge."""

    def __init__(self):
        self.corpus_name = "diagrams-documentation-corpus"
        self.search_tool = google_search
        self.rag_retrieval = None
        self._setup_rag_retrieval()

    def _setup_rag_retrieval(self):
        """Set up RAG retrieval tool."""
        try:
            # Create RAG retrieval tool
            self.rag_retrieval = VertexAiRagRetrieval(
                name='retrieve_diagrams_docs',
                description='Retrieve diagrams package documentation and examples',
                rag_resources=[
                    rag.RagResource(
                        rag_corpus=self.corpus_name  # This corpus needs to be created
                    )
                ],
                similarity_top_k=10,
                vector_distance_threshold=0.3
            )
        except Exception as e:
            print(f"RAG setup failed: {e}")
            self.rag_retrieval = None

    async def fetch_and_store_docs(self):
        """Fetch live documentation and store in RAG corpus."""
        try:
            # Fetch documentation for each provider
            providers = ["aws", "azure", "gcp"]
            docs_content = []

            for provider in providers:
                search_query = f"python diagrams package {provider} components site:diagrams.mingrammer.com"

                content = await self.search_tool.invoke(search_query)

                docs_content.append({
                    "provider": provider,
                    "search_query": search_query,
                    "content": content
                })

            # Store in RAG corpus (this would require corpus creation)
            await self._store_in_rag_corpus(docs_content)

            return docs_content

        except Exception as e:
            print(f"Failed to fetch and store docs: {e}")
            return []

    async def _store_in_rag_corpus(self, docs_content):
        """Store fetched documentation in RAG corpus."""
        # TODO: Implement corpus creation and document import
        # This requires setting up Vertex AI RAG corpus first
        pass

    async def retrieve_diagrams_knowledge(self, query: str) -> str:
        """Retrieve relevant diagrams knowledge from RAG."""
        if not self.rag_retrieval:
            return self._get_fallback_knowledge()

        try:
            # Use RAG to retrieve relevant documentation
            result = await self.rag_retrieval.run_async(query)
            return result if result else self._get_fallback_knowledge()
        except Exception as e:
            print(f"RAG retrieval failed: {e}")
            return self._get_fallback_knowledge()

    def _get_fallback_knowledge(self) -> str:
        """Fallback knowledge if RAG is not available."""
        return """
DIAGRAMS PACKAGE REFERENCE (FALLBACK):

## AWS Components:
- from diagrams.aws.compute import EC2, Lambda, ECS, Fargate
- from diagrams.aws.database import RDS, DynamoDB, ElastiCache
- from diagrams.aws.network import ELB, ALB, CloudFront, VPC
- from diagrams.aws.storage import S3, EBS, EFS

## Azure Components:
- from diagrams.azure.compute import VirtualMachines, FunctionApps, ContainerInstances
- from diagrams.azure.database import SQLDatabases, CosmosDb, DatabaseForPostgreSQL
- from diagrams.azure.network import LoadBalancers, ApplicationGateway, VirtualNetworks
- from diagrams.azure.storage import StorageAccounts, BlobStorage

## GCP Components:
- from diagrams.gcp.compute import ComputeEngine, CloudFunctions, GKE
- from diagrams.gcp.database import SQL, Firestore, BigQuery
- from diagrams.gcp.network import LoadBalancing, CDN, VPC
- from diagrams.gcp.storage import Storage

## Basic Syntax:
```python
from diagrams import Diagram, Cluster, Edge

with Diagram("Architecture", filename="generated_diagram", show=False, direction="TB"):
    component1 = EC2("Web Server")
    component2 = RDS("Database")
    component1 >> component2
```
"""


# Global RAG system instance
diagrams_rag = DiagramsRagSystem()


async def get_diagrams_knowledge_from_rag(architecture_query: str) -> str:
    """Get diagrams knowledge using RAG system."""
    return await diagrams_rag.retrieve_diagrams_knowledge(architecture_query)


async def refresh_diagrams_knowledge():
    """Refresh the RAG knowledge base with latest documentation."""
    return await diagrams_rag.fetch_and_store_docs()