"""
Runtime RAG Bootstrap: Automatically creates and initializes RAG systems at ADK startup.
This ensures RAG corpora are available when agents start running.
"""

import asyncio
import os
from typing import Dict, Optional
import vertexai
from vertexai.preview import rag
from .automated_rag_builder import rag_builder
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RuntimeRagBootstrap:
    """Bootstrap RAG systems at runtime during ADK initialization."""

    def __init__(self):
        self.initialized = False
        self.available_corpora = {}
        self.bootstrap_complete = False

    async def bootstrap_rag_systems(self) -> Dict[str, str]:
        """Bootstrap all RAG systems at runtime."""

        if self.bootstrap_complete:
            logger.info("🔄 RAG systems already bootstrapped")
            return self.available_corpora

        logger.info("🚀 Starting Runtime RAG Bootstrap...")

        try:
            # Initialize Vertex AI
            vertexai.init(
                project=os.environ.get("GOOGLE_CLOUD_PROJECT", "qwiklabs-gcp-03-ec92c6095411"),
                location=os.environ.get("GOOGLE_CLOUD_LOCATION", "europe-west4")
            )

            # Step 1: Check existing corpora
            existing_corpora = await self._check_existing_corpora()

            # Step 2: Create missing corpora
            created_corpora = await self._create_missing_corpora(existing_corpora)

            # Step 3: Update available corpora
            self.available_corpora.update(existing_corpora)
            self.available_corpora.update(created_corpora)

            self.bootstrap_complete = True

            logger.info(f"✅ RAG Bootstrap complete! Available corpora: {len(self.available_corpora)}")
            for name, corpus_id in self.available_corpora.items():
                logger.info(f"  📚 {name}: {corpus_id}")

            return self.available_corpora

        except Exception as e:
            logger.error(f"❌ RAG Bootstrap failed: {e}")
            # Continue with empty corpora - agents can still work without RAG
            return {}

    async def _check_existing_corpora(self) -> Dict[str, str]:
        """Check which RAG corpora already exist."""

        existing = {}

        try:
            # List all existing corpora
            corpora = rag.list_corpora()

            # Map our configurations to existing corpora
            for corpus_name, config in rag_builder.corpus_configs.items():
                display_name = config["display_name"]

                for corpus in corpora:
                    if corpus.display_name == display_name:
                        existing[corpus_name] = corpus.name
                        logger.info(f"  ✅ Found existing corpus: {corpus_name}")
                        break

        except Exception as e:
            logger.warning(f"⚠️ Could not list existing corpora: {e}")

        return existing

    async def _create_missing_corpora(self, existing_corpora: Dict[str, str]) -> Dict[str, str]:
        """Create any missing RAG corpora."""

        created = {}
        missing_corpora = [
            name for name in rag_builder.corpus_configs.keys()
            if name not in existing_corpora
        ]

        if not missing_corpora:
            logger.info("📋 All RAG corpora already exist")
            return created

        logger.info(f"🔧 Creating {len(missing_corpora)} missing RAG corpora...")

        # Create corpora in background (don't block agent startup)
        for corpus_name in missing_corpora:
            try:
                # Create corpus quickly with minimal content
                corpus_id = await self._quick_create_corpus(corpus_name)
                if corpus_id:
                    created[corpus_name] = corpus_id
                    logger.info(f"  ✅ Created: {corpus_name}")

                    # Schedule background population (don't wait)
                    asyncio.create_task(self._populate_corpus_background(corpus_name, corpus_id))

            except Exception as e:
                logger.warning(f"  ⚠️ Failed to create {corpus_name}: {e}")

        return created

    async def _quick_create_corpus(self, corpus_name: str) -> Optional[str]:
        """Quickly create a corpus with minimal setup."""

        config = rag_builder.corpus_configs[corpus_name]

        try:
            # Create the corpus
            corpus = rag.create_corpus(
                display_name=config["display_name"],
                description=config["description"]
            )

            # Add a minimal seed document so corpus is not empty
            seed_content = self._generate_seed_content(corpus_name, config)
            await self._add_seed_content(corpus, seed_content)

            return corpus.name

        except Exception as e:
            logger.error(f"Failed to quick-create corpus {corpus_name}: {e}")
            return None

    def _generate_seed_content(self, corpus_name: str, config: Dict) -> str:
        """Generate seed content for immediate corpus functionality."""

        seed_templates = {
            "diagrams_knowledge": """
# Python Diagrams Package Seed Knowledge

## Basic Usage
```python
from diagrams import Diagram, Cluster, Edge
from diagrams.aws.compute import EC2
from diagrams.azure.compute import VirtualMachines
from diagrams.gcp.compute import ComputeEngine

with Diagram("Architecture", show=False):
    ec2 = EC2("AWS Instance")
    vm = VirtualMachines("Azure VM")
    gce = ComputeEngine("GCP Instance")
```

## Common Imports
- AWS: from diagrams.aws.compute import EC2, Lambda
- Azure: from diagrams.azure.compute import VirtualMachines
- GCP: from diagrams.gcp.compute import ComputeEngine
""",

            "azure_architecture": """
# Azure Architecture Seed Knowledge

## Core Services
- Virtual Machines: Compute instances
- Virtual Networks: Networking infrastructure
- Load Balancers: Traffic distribution
- Storage Accounts: Data storage

## Basic Patterns
- Web tier: Load Balancer + VMs
- Database tier: SQL Database + backup
- Network security: NSGs + Firewall
""",

            "terraform_infrastructure": """
# Terraform Infrastructure Seed Knowledge

## Providers
- aws: AWS resources
- azurerm: Azure resources
- google: GCP resources

## Common Resources
- aws_instance: EC2 instances
- azurerm_virtual_machine: Azure VMs
- google_compute_instance: GCP instances
""",

            "cloud_architecture": """
# Cloud Architecture Seed Knowledge

## Common Patterns
- 3-tier architecture: Web + App + Database
- Microservices: Containerized services
- Serverless: Functions + managed services
- Multi-cloud: Resources across providers
"""
        }

        return seed_templates.get(corpus_name, f"# {config['display_name']}\n\nInitial seed content for {corpus_name}")

    async def _add_seed_content(self, corpus: any, content: str):
        """Add seed content to corpus."""

        try:
            # Create temporary file
            temp_file = "/tmp/seed_content.md"
            with open(temp_file, 'w', encoding='utf-8') as f:
                f.write(content)

            # Import to corpus
            rag.import_files(
                corpus_name=corpus.name,
                paths=[temp_file],
                chunk_size=500,
                chunk_overlap=100
            )

            # Clean up
            os.remove(temp_file)

        except Exception as e:
            logger.warning(f"Failed to add seed content: {e}")

    async def _populate_corpus_background(self, corpus_name: str, corpus_id: str):
        """Populate corpus with full content in background."""

        logger.info(f"🔄 Background population started for: {corpus_name}")

        try:
            # Use the full automated RAG builder for comprehensive content
            config = rag_builder.corpus_configs[corpus_name]
            content_data = await rag_builder._gather_content_from_sources(config)

            # Find the corpus object
            corpora = rag.list_corpora()
            target_corpus = None
            for corpus in corpora:
                if corpus.name == corpus_id:
                    target_corpus = corpus
                    break

            if target_corpus and content_data:
                await rag_builder._import_content_to_corpus(target_corpus, content_data)
                logger.info(f"✅ Background population complete for: {corpus_name}")
            else:
                logger.warning(f"⚠️ Could not populate {corpus_name}: corpus not found or no content")

        except Exception as e:
            logger.error(f"❌ Background population failed for {corpus_name}: {e}")

    def get_corpus_id(self, corpus_name: str) -> Optional[str]:
        """Get corpus ID for a specific corpus name."""
        return self.available_corpora.get(corpus_name)

    def is_bootstrap_complete(self) -> bool:
        """Check if bootstrap is complete."""
        return self.bootstrap_complete

    async def ensure_corpus_ready(self, corpus_name: str) -> Optional[str]:
        """Ensure a specific corpus is ready for use."""

        if not self.bootstrap_complete:
            await self.bootstrap_rag_systems()

        return self.get_corpus_id(corpus_name)


# Global bootstrap instance
runtime_bootstrap = RuntimeRagBootstrap()


async def initialize_rag_at_startup():
    """Initialize RAG systems at ADK startup."""
    return await runtime_bootstrap.bootstrap_rag_systems()


async def get_rag_corpus_id(corpus_name: str) -> Optional[str]:
    """Get RAG corpus ID, creating if necessary."""
    return await runtime_bootstrap.ensure_corpus_ready(corpus_name)


def is_rag_ready() -> bool:
    """Check if RAG systems are ready."""
    return runtime_bootstrap.is_bootstrap_complete()


# Auto-initialize when module is imported (for ADK runtime)
async def _auto_initialize():
    """Auto-initialize RAG systems when this module is imported."""
    try:
        await initialize_rag_at_startup()
    except Exception as e:
        logger.warning(f"Auto-initialization failed: {e}")


# Run auto-initialization when module loads
import atexit

def _cleanup():
    """Cleanup function."""
    pass

atexit.register(_cleanup)

# Schedule auto-initialization
_initialization_task = None

def _schedule_auto_init():
    """Schedule auto-initialization."""
    global _initialization_task
    if _initialization_task is None:
        loop = None
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            # No event loop running
            pass

        if loop and loop.is_running():
            _initialization_task = asyncio.create_task(_auto_initialize())

# Call scheduling
_schedule_auto_init()