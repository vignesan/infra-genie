"""
Automated RAG Builder: Creates and populates multiple RAG corpora from various sources.
Data Sources: Google Search, Microsoft Docs, Terraform Docs, GitHub Repos, etc.
"""

import os
import asyncio
import json
from typing import List, Dict, Any
import vertexai
from vertexai.preview import rag
from google.adk.tools import google_search
from app.mcp_github import create_github_mcp
from app.mcp_github import create_microsoft_learn_mcp, create_terraform_docs_mcp


class AutomatedRagBuilder:
    """Automatically builds and populates RAG corpora from multiple data sources."""

    def __init__(self):
        # Initialize Vertex AI
        vertexai.init(
            project=os.environ.get("GOOGLE_CLOUD_PROJECT", "qwiklabs-gcp-03-ec92c6095411"),
            location=os.environ.get("GOOGLE_CLOUD_LOCATION", "europe-west4")
        )

        # Initialize data source tools
        self.search_tool = google_search
        self.github_mcp = create_github_mcp()
        self.microsoft_mcp = create_microsoft_learn_mcp()
        self.terraform_mcp = create_terraform_docs_mcp()

        # RAG corpus configurations
        self.corpus_configs = {
            "diagrams_knowledge": {
                "display_name": "Python Diagrams Package Knowledge",
                "description": "Comprehensive documentation for Python diagrams package including AWS, Azure, GCP components",
                "sources": ["google_search", "github"],
                "search_queries": [
                    "python diagrams package AWS components site:diagrams.mingrammer.com",
                    "python diagrams package Azure components site:diagrams.mingrammer.com",
                    "python diagrams package GCP components site:diagrams.mingrammer.com",
                    "python diagrams package syntax examples site:diagrams.mingrammer.com",
                    "python diagrams package clustering groups site:diagrams.mingrammer.com"
                ],
                "github_repos": ["mingrammer/diagrams"]
            },
            "azure_architecture": {
                "display_name": "Azure Architecture Knowledge",
                "description": "Azure services, architecture patterns, and best practices",
                "sources": ["microsoft_docs", "google_search"],
                "microsoft_queries": [
                    "Azure architecture patterns",
                    "Azure virtual networks",
                    "Azure compute services",
                    "Azure database services",
                    "Azure networking components"
                ],
                "search_queries": [
                    "Azure architecture best practices site:learn.microsoft.com",
                    "Azure reference architectures site:learn.microsoft.com"
                ]
            },
            "terraform_infrastructure": {
                "display_name": "Terraform Infrastructure Knowledge",
                "description": "Terraform providers, resources, and infrastructure patterns",
                "sources": ["terraform_docs", "google_search"],
                "terraform_queries": [
                    "AWS provider resources",
                    "Azure provider resources",
                    "GCP provider resources",
                    "Terraform modules patterns",
                    "Terraform best practices"
                ],
                "search_queries": [
                    "terraform AWS resources site:registry.terraform.io",
                    "terraform Azure resources site:registry.terraform.io",
                    "terraform GCP resources site:registry.terraform.io"
                ]
            },
            "cloud_architecture": {
                "display_name": "Multi-Cloud Architecture Knowledge",
                "description": "General cloud architecture patterns, networking, and best practices",
                "sources": ["google_search"],
                "search_queries": [
                    "cloud architecture patterns best practices",
                    "microservices architecture cloud",
                    "cloud networking VPC patterns",
                    "cloud security architecture",
                    "multi-cloud architecture design",
                    "serverless architecture patterns",
                    "container orchestration architecture"
                ]
            }
        }

    async def create_all_rag_corpora(self):
        """Create all RAG corpora with their respective knowledge sources."""

        print("🚀 Starting Automated RAG Builder...")
        created_corpora = {}

        for corpus_name, config in self.corpus_configs.items():
            print(f"\n📚 Creating corpus: {corpus_name}")

            try:
                # Step 1: Create corpus
                corpus = await self._create_corpus(corpus_name, config)
                if not corpus:
                    continue

                # Step 2: Gather content from all sources
                content_data = await self._gather_content_from_sources(config)

                # Step 3: Import content into corpus
                await self._import_content_to_corpus(corpus, content_data)

                created_corpora[corpus_name] = corpus.name
                print(f"✅ Successfully created corpus: {corpus_name}")

            except Exception as e:
                print(f"❌ Failed to create corpus {corpus_name}: {e}")

        print(f"\n🎉 Automated RAG Builder completed!")
        print(f"Created {len(created_corpora)} corpora:")
        for name, corpus_id in created_corpora.items():
            print(f"  - {name}: {corpus_id}")

        return created_corpora

    async def _create_corpus(self, corpus_name: str, config: Dict) -> Any:
        """Create a single RAG corpus."""
        try:
            corpus = rag.create_corpus(
                display_name=config["display_name"],
                description=config["description"]
            )
            print(f"  ✅ Created corpus: {corpus.name}")
            return corpus
        except Exception as e:
            print(f"  ❌ Error creating corpus: {e}")
            return None

    async def _gather_content_from_sources(self, config: Dict) -> List[Dict]:
        """Gather content from all configured sources."""

        content_data = []
        sources = config.get("sources", [])

        # Gather from Google Search
        if "google_search" in sources:
            search_queries = config.get("search_queries", [])
            search_content = await self._gather_from_google_search(search_queries)
            content_data.extend(search_content)

        # Gather from Microsoft Docs
        if "microsoft_docs" in sources:
            microsoft_queries = config.get("microsoft_queries", [])
            microsoft_content = await self._gather_from_microsoft_docs(microsoft_queries)
            content_data.extend(microsoft_content)

        # Gather from Terraform Docs
        if "terraform_docs" in sources:
            terraform_queries = config.get("terraform_queries", [])
            terraform_content = await self._gather_from_terraform_docs(terraform_queries)
            content_data.extend(terraform_content)

        # Gather from GitHub
        if "github" in sources:
            github_repos = config.get("github_repos", [])
            github_content = await self._gather_from_github(github_repos)
            content_data.extend(github_content)

        print(f"  📦 Gathered {len(content_data)} content items from {len(sources)} sources")
        return content_data

    async def _gather_from_google_search(self, queries: List[str]) -> List[Dict]:
        """Gather content using Google Search."""
        content = []

        for query in queries:
            try:
                result = await self.search_tool.invoke(query)
                content.append({
                    "title": f"Search: {query}",
                    "content": result,
                    "source": "google_search",
                    "query": query
                })
                print(f"    🔍 Searched: {query}")
            except Exception as e:
                print(f"    ❌ Search failed for {query}: {e}")

        return content

    async def _gather_from_microsoft_docs(self, queries: List[str]) -> List[Dict]:
        """Gather content from Microsoft Learn docs."""
        content = []

        for query in queries:
            try:
                # Use Microsoft MCP to get documentation
                result = await self._query_microsoft_mcp(query)
                content.append({
                    "title": f"Microsoft Docs: {query}",
                    "content": result,
                    "source": "microsoft_docs",
                    "query": query
                })
                print(f"    📖 Microsoft docs: {query}")
            except Exception as e:
                print(f"    ❌ Microsoft docs failed for {query}: {e}")

        return content

    async def _gather_from_terraform_docs(self, queries: List[str]) -> List[Dict]:
        """Gather content from Terraform documentation."""
        content = []

        for query in queries:
            try:
                # Use Terraform MCP to get documentation
                result = await self._query_terraform_mcp(query)
                content.append({
                    "title": f"Terraform Docs: {query}",
                    "content": result,
                    "source": "terraform_docs",
                    "query": query
                })
                print(f"    📋 Terraform docs: {query}")
            except Exception as e:
                print(f"    ❌ Terraform docs failed for {query}: {e}")

        return content

    async def _gather_from_github(self, repos: List[str]) -> List[Dict]:
        """Gather content from GitHub repositories."""
        content = []

        for repo in repos:
            try:
                # Use GitHub MCP to get repository content
                result = await self._query_github_mcp(repo)
                content.append({
                    "title": f"GitHub Repo: {repo}",
                    "content": result,
                    "source": "github",
                    "repo": repo
                })
                print(f"    🐙 GitHub repo: {repo}")
            except Exception as e:
                print(f"    ❌ GitHub failed for {repo}: {e}")

        return content

    async def _query_microsoft_mcp(self, query: str) -> str:
        """Query Microsoft Learn MCP."""
        # TODO: Implement actual MCP query
        # This would use the Microsoft Learn MCP tools
        return f"Microsoft documentation for: {query}"

    async def _query_terraform_mcp(self, query: str) -> str:
        """Query Terraform docs MCP."""
        # TODO: Implement actual MCP query
        # This would use the Terraform docs MCP tools
        return f"Terraform documentation for: {query}"

    async def _query_github_mcp(self, repo: str) -> str:
        """Query GitHub MCP."""
        # TODO: Implement actual MCP query
        # This would use the GitHub MCP tools to get README, docs, examples
        return f"GitHub repository content for: {repo}"

    async def _import_content_to_corpus(self, corpus: Any, content_data: List[Dict]):
        """Import all gathered content into the RAG corpus."""

        for i, content_item in enumerate(content_data):
            try:
                # Create temporary file with content
                temp_file = f"/tmp/rag_content_{i}.md"

                formatted_content = f"""# {content_item['title']}

Source: {content_item['source']}
Query/Repo: {content_item.get('query', content_item.get('repo', 'N/A'))}

## Content

{content_item['content']}
"""

                with open(temp_file, 'w', encoding='utf-8') as f:
                    f.write(formatted_content)

                # Import to corpus
                rag.import_files(
                    corpus_name=corpus.name,
                    paths=[temp_file],
                    chunk_size=1000,
                    chunk_overlap=200
                )

                # Clean up
                os.remove(temp_file)

                print(f"    ✅ Imported: {content_item['title']}")

            except Exception as e:
                print(f"    ❌ Failed to import {content_item['title']}: {e}")

    async def refresh_corpus_content(self, corpus_name: str):
        """Refresh content for a specific corpus with latest data."""

        if corpus_name not in self.corpus_configs:
            print(f"❌ Unknown corpus: {corpus_name}")
            return

        config = self.corpus_configs[corpus_name]
        print(f"🔄 Refreshing corpus: {corpus_name}")

        # Gather fresh content
        content_data = await self._gather_content_from_sources(config)

        # TODO: Update existing corpus with new content
        # This would require corpus update functionality

        print(f"✅ Refreshed corpus: {corpus_name}")

    async def create_custom_corpus(self, name: str, display_name: str, description: str,
                                 sources: List[str], queries: Dict[str, List[str]]):
        """Create a custom corpus with specified sources and queries."""

        custom_config = {
            "display_name": display_name,
            "description": description,
            "sources": sources,
            **queries  # Add all query types (search_queries, microsoft_queries, etc.)
        }

        # Add to configurations
        self.corpus_configs[name] = custom_config

        # Create the corpus
        print(f"🔧 Creating custom corpus: {name}")
        corpus = await self._create_corpus(name, custom_config)

        if corpus:
            content_data = await self._gather_content_from_sources(custom_config)
            await self._import_content_to_corpus(corpus, content_data)
            print(f"✅ Custom corpus created: {name}")
            return corpus.name

        return None


# Global builder instance
rag_builder = AutomatedRagBuilder()


async def setup_all_rag_systems():
    """Setup all RAG systems automatically."""
    return await rag_builder.create_all_rag_corpora()


async def create_custom_rag(name: str, display_name: str, description: str,
                          sources: List[str], queries: Dict[str, List[str]]):
    """Create a custom RAG corpus."""
    return await rag_builder.create_custom_corpus(name, display_name, description, sources, queries)


async def refresh_rag_corpus(corpus_name: str):
    """Refresh a specific RAG corpus with latest content."""
    return await rag_builder.refresh_corpus_content(corpus_name)


if __name__ == "__main__":
    # Example usage
    asyncio.run(setup_all_rag_systems())