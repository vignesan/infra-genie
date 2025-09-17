# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Infrastructure Genie Application Package
Auto-initializes RAG systems at startup for seamless operation.
"""

import asyncio
import logging
from .runtime_rag_bootstrap import initialize_rag_at_startup

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Application metadata
__version__ = "0.1.0"
__app_name__ = "Infrastructure Genie"

def initialize_app():
    """Initialize the Infrastructure Genie application."""
    logger.info(f"🚀 Starting {__app_name__} v{__version__}")

    # Schedule RAG initialization for when async context is available
    try:
        # Note: RAG initialization will happen automatically via runtime_rag_bootstrap
        logger.info("📚 RAG systems will auto-initialize on first use")
    except Exception as e:
        logger.warning(f"⚠️ RAG initialization setup failed: {e}")

# Auto-initialize when package is imported
try:
    initialize_app()
except Exception as e:
    logger.warning(f"⚠️ App initialization deferred: {e}")

# Import main agent after initialization (now uses RAG-enabled agents)
from .agent import root_agent

logger.info("📦 Infrastructure Genie package loaded")

__all__ = ["root_agent"]
