"""
Live documentation fetcher for diagrams package API reference.
Keeps the knowledge base up-to-date with latest diagrams package documentation.
"""

import asyncio
from typing import Dict, List
from google.adk.tools import google_search
import json
import time


class DiagramsDocsFetcher:
    """Fetches and caches live documentation from diagrams package website."""

    def __init__(self):
        self.base_url = "https://diagrams.mingrammer.com"
        self.cache = {}
        self.cache_expiry = 3600  # 1 hour cache
        self.last_updated = {}

    async def fetch_provider_nodes(self, provider: str) -> Dict:
        """Fetch live documentation for a specific cloud provider."""
        cache_key = f"nodes_{provider}"

        # Check cache
        if (cache_key in self.cache and
            time.time() - self.last_updated.get(cache_key, 0) < self.cache_expiry):
            return self.cache[cache_key]

        try:
            # Use Google Search to find diagrams documentation
            search_query = f"python diagrams package {provider} components site:diagrams.mingrammer.com"

            result = await google_search.invoke(search_query)

            # Parse and structure the result
            nodes_data = self._parse_nodes_response(result, provider)

            # Cache the result
            self.cache[cache_key] = nodes_data
            self.last_updated[cache_key] = time.time()

            return nodes_data

        except Exception as e:
            print(f"Failed to fetch {provider} docs: {e}")
            return self._get_fallback_nodes(provider)

    def _parse_nodes_response(self, response: str, provider: str) -> Dict:
        """Parse the web response into structured node data."""
        # This would parse the HTML/markdown response
        # For now, return a basic structure
        return {
            "provider": provider,
            "categories": {},
            "last_updated": time.time(),
            "source": f"{self.base_url}/docs/nodes/{provider}"
        }

    def _get_fallback_nodes(self, provider: str) -> Dict:
        """Fallback node data if live fetch fails."""
        fallback_data = {
            "aws": {
                "compute": ["EC2", "Lambda", "ECS", "Fargate"],
                "database": ["RDS", "DynamoDB", "ElastiCache", "Redshift"],
                "network": ["ELB", "ALB", "CloudFront", "VPC"],
                "storage": ["S3", "EBS", "EFS"]
            },
            "azure": {
                "compute": ["VirtualMachines", "FunctionApps", "ContainerInstances"],
                "database": ["SQLDatabases", "CosmosDb", "DatabaseForPostgreSQL"],
                "network": ["LoadBalancers", "ApplicationGateway", "VirtualNetworks"],
                "storage": ["StorageAccounts", "BlobStorage"]
            },
            "gcp": {
                "compute": ["ComputeEngine", "CloudFunctions", "GKE"],
                "database": ["SQL", "Firestore", "BigQuery"],
                "network": ["LoadBalancing", "CDN", "VPC"],
                "storage": ["Storage"]
            }
        }

        return {
            "provider": provider,
            "categories": fallback_data.get(provider, {}),
            "last_updated": time.time(),
            "source": "fallback"
        }

    async def get_comprehensive_knowledge_base(self) -> str:
        """Generate comprehensive, up-to-date knowledge base for LLM."""
        providers = ["aws", "azure", "gcp"]
        knowledge_base = "# LIVE DIAGRAMS PACKAGE DOCUMENTATION\n\n"

        for provider in providers:
            nodes_data = await self.fetch_provider_nodes(provider)
            knowledge_base += self._format_provider_docs(provider, nodes_data)

        # Add generic components
        knowledge_base += self._get_generic_components()

        return knowledge_base

    def _format_provider_docs(self, provider: str, nodes_data: Dict) -> str:
        """Format provider documentation for LLM consumption."""
        formatted = f"\n## {provider.upper()} Components:\n"

        categories = nodes_data.get("categories", {})
        for category, components in categories.items():
            formatted += f"\n### {category.title()}:\n"
            for component in components:
                formatted += f"- from diagrams.{provider}.{category} import {component}\n"

        return formatted

    def _get_generic_components(self) -> str:
        """Get generic/on-premise components."""
        return """
## Generic/On-Premise Components:
- from diagrams.onprem.client import Users, Client
- from diagrams.onprem.database import MySQL, PostgreSQL, MongoDB
- from diagrams.onprem.inmemory import Redis, Memcached
- from diagrams.onprem.queue import Kafka, RabbitMQ
- from diagrams.onprem.network import Internet, Nginx

## Basic Syntax:
```python
from diagrams import Diagram, Cluster, Edge

with Diagram("Title", filename="output", show=False, direction="TB"):
    component1 = EC2("Component 1")
    component2 >> component1  # Connection

    with Cluster("Group"):
        services = [EC2(f"Service {i}") for i in range(3)]
```
"""


# Global instance for caching
docs_fetcher = DiagramsDocsFetcher()


async def get_live_diagrams_knowledge() -> str:
    """Get live, up-to-date diagrams package knowledge."""
    return await docs_fetcher.get_comprehensive_knowledge_base()


async def refresh_docs_cache():
    """Manually refresh the documentation cache."""
    docs_fetcher.cache.clear()
    docs_fetcher.last_updated.clear()
    return await get_live_diagrams_knowledge()