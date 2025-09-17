"""
Intelligent Knowledge System: LLM decides when to use RAG vs WebFetch based on knowledge gaps.
"""

from google.adk.tools import ToolContext, google_search
from google.adk.tools.retrieval.vertex_ai_rag_retrieval import VertexAiRagRetrieval
from google import genai
from google.genai import types
import os


class IntelligentKnowledgeSystem:
    """Smart system that lets LLM decide when to use RAG vs WebFetch."""

    def __init__(self):
        self.search_tool = google_search
        self.rag_retrieval = self._setup_rag()
        self.client = self._setup_genai_client()

    def _setup_genai_client(self):
        """Set up Gemini client."""
        import google.auth
        _, project_id = google.auth.default()
        os.environ.setdefault("GOOGLE_CLOUD_PROJECT", "qwiklabs-gcp-03-ec92c6095411")
        os.environ.setdefault("GOOGLE_CLOUD_LOCATION", "europe-west4")
        os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI", "True")

        return genai.Client(vertexai=True)

    def _setup_rag(self):
        """Set up RAG retrieval if available."""
        try:
            from vertexai.preview import rag
            return VertexAiRagRetrieval(
                name='retrieve_diagrams_docs',
                description='Retrieve diagrams package documentation',
                rag_resources=[
                    rag.RagResource(rag_corpus="diagrams-docs-corpus")
                ],
                similarity_top_k=5,
                vector_distance_threshold=0.4
            )
        except Exception as e:
            print(f"RAG not available: {e}")
            return None

    async def get_intelligent_knowledge(self, architecture_description: str, context: str = "") -> str:
        """
        Intelligent knowledge retrieval with LLM decision making.
        """

        # Step 1: LLM evaluates what it needs to know
        knowledge_assessment = await self._assess_knowledge_needs(architecture_description, context)

        # Step 2: Try RAG first if available
        rag_knowledge = ""
        if self.rag_retrieval and knowledge_assessment.get("use_rag", True):
            rag_knowledge = await self._get_rag_knowledge(knowledge_assessment["rag_query"])

        # Step 3: LLM decides if RAG knowledge is sufficient
        knowledge_gap = await self._evaluate_knowledge_gap(
            architecture_description,
            rag_knowledge,
            knowledge_assessment
        )

        # Step 4: Use WebFetch if needed
        web_knowledge = ""
        if knowledge_gap.get("need_web_fetch", False):
            web_knowledge = await self._get_web_knowledge(knowledge_gap["web_queries"])

            # Add new knowledge to RAG for future use
            if self.rag_retrieval and web_knowledge:
                await self._add_to_rag(web_knowledge)

        # Step 5: Combine all knowledge sources
        final_knowledge = await self._combine_knowledge(
            rag_knowledge,
            web_knowledge,
            knowledge_assessment
        )

        return final_knowledge

    async def _assess_knowledge_needs(self, architecture_description: str, context: str) -> dict:
        """LLM assesses what knowledge is needed for the architecture."""

        assessment_prompt = f"""
Analyze this architecture request and determine what diagrams package knowledge is needed.

Architecture: {architecture_description}
Context: {context}

Evaluate:
1. What cloud providers are mentioned? (AWS, Azure, GCP)
2. What specific services/components are needed?
3. What diagram patterns are required?
4. Do you need to search for specific diagrams package syntax?

Return JSON with:
{{
    "cloud_providers": ["aws", "azure", "gcp"],
    "services_needed": ["compute", "database", "network"],
    "specific_components": ["EC2", "RDS", "VirtualMachines"],
    "diagram_patterns": ["web-tier", "microservices", "data-pipeline"],
    "use_rag": true,
    "rag_query": "AWS EC2 RDS VirtualMachines diagrams package syntax",
    "confidence_level": "high|medium|low"
}}
"""

        try:
            response = self.client.models.generate_content(
                model="gemini-2.5-flash",
                contents=[assessment_prompt],
                config=types.GenerateContentConfig(
                    temperature=0.1,
                    max_output_tokens=500
                )
            )

            # Parse JSON response
            import json
            result = json.loads(response.text.strip())
            return result

        except Exception as e:
            print(f"Assessment failed: {e}")
            return {
                "cloud_providers": ["aws"],
                "use_rag": True,
                "rag_query": architecture_description,
                "confidence_level": "low"
            }

    async def _get_rag_knowledge(self, query: str) -> str:
        """Get knowledge from RAG system."""
        try:
            if self.rag_retrieval:
                return await self.rag_retrieval.retrieve(query)
            return ""
        except Exception as e:
            print(f"RAG retrieval failed: {e}")
            return ""

    async def _evaluate_knowledge_gap(self, architecture_description: str, rag_knowledge: str, assessment: dict) -> dict:
        """LLM evaluates if RAG knowledge is sufficient or if WebFetch is needed."""

        gap_evaluation_prompt = f"""
Architecture Request: {architecture_description}
RAG Knowledge Retrieved: {rag_knowledge}
Original Assessment: {assessment}

Evaluate if the RAG knowledge is sufficient to generate accurate Python diagrams code.

Check for:
1. Are all required cloud provider imports available?
2. Are specific component classes mentioned?
3. Is the syntax for connections and clusters clear?
4. Are there any missing components or services?

Return JSON:
{{
    "knowledge_sufficient": true/false,
    "need_web_fetch": true/false,
    "missing_knowledge": ["specific missing items"],
    "web_queries": ["diagrams.aws.compute components", "Azure VirtualMachines syntax"],
    "confidence_score": 0.8
}}
"""

        try:
            response = self.client.models.generate_content(
                model="gemini-2.5-flash",
                contents=[gap_evaluation_prompt],
                config=types.GenerateContentConfig(
                    temperature=0.1,
                    max_output_tokens=400
                )
            )

            import json
            result = json.loads(response.text.strip())
            return result

        except Exception as e:
            print(f"Gap evaluation failed: {e}")
            return {"need_web_fetch": False, "knowledge_sufficient": True}

    async def _get_web_knowledge(self, web_queries: list) -> str:
        """Fetch additional knowledge from web sources using Google Search."""
        web_knowledge = ""

        for query in web_queries[:3]:  # Limit to 3 queries
            try:
                # Search for diagrams package documentation
                search_query = f"python diagrams package {query} site:diagrams.mingrammer.com"

                result = await self.search_tool.invoke(search_query)

                web_knowledge += f"\n\n## {query}:\n{result}"

            except Exception as e:
                print(f"Search failed for {query}: {e}")

        return web_knowledge

    def _determine_best_url(self, query: str) -> str:
        """Determine the best URL to fetch information for a query."""
        query_lower = query.lower()

        if "aws" in query_lower:
            return "https://diagrams.mingrammer.com/docs/nodes/aws"
        elif "azure" in query_lower:
            return "https://diagrams.mingrammer.com/docs/nodes/azure"
        elif "gcp" in query_lower or "google" in query_lower:
            return "https://diagrams.mingrammer.com/docs/nodes/gcp"
        else:
            return "https://diagrams.mingrammer.com/docs/getting-started/installation"

    async def _add_to_rag(self, new_knowledge: str):
        """Add newly fetched knowledge to RAG corpus for future use."""
        # TODO: Implement RAG corpus update
        # This would store the new knowledge for future retrieval
        pass

    async def _combine_knowledge(self, rag_knowledge: str, web_knowledge: str, assessment: dict) -> str:
        """Combine RAG and web knowledge into comprehensive knowledge base."""

        combine_prompt = f"""
Combine and organize this knowledge for Python diagrams code generation:

RAG Knowledge:
{rag_knowledge}

Web Knowledge:
{web_knowledge}

Original Request Context:
{assessment}

Create a comprehensive, well-organized knowledge base with:
1. All relevant import statements
2. Available components for each cloud provider
3. Syntax examples for connections and clusters
4. Best practices for the specific architecture pattern

Format as clear documentation for code generation.
"""

        try:
            response = self.client.models.generate_content(
                model="gemini-2.5-flash",
                contents=[combine_prompt],
                config=types.GenerateContentConfig(
                    temperature=0.1,
                    max_output_tokens=1500
                )
            )

            return response.text

        except Exception as e:
            print(f"Knowledge combination failed: {e}")
            # Return combined raw knowledge as fallback
            return f"{rag_knowledge}\n\n{web_knowledge}"


# Global intelligent system instance
intelligent_knowledge = IntelligentKnowledgeSystem()


async def get_smart_diagrams_knowledge(architecture_description: str, context: str = "") -> str:
    """Get intelligent, context-aware diagrams knowledge."""
    return await intelligent_knowledge.get_intelligent_knowledge(architecture_description, context)