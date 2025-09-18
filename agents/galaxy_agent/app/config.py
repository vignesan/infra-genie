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

import os
from dataclasses import dataclass
from typing import Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


@dataclass
class GalaxyConfig:
    """Configuration for Galaxy application."""

    # Google Cloud and AI
    google_cloud_project: str = "qwiklabs-gcp-03-ec92c6095411"
    google_cloud_location: str = "europe-west4"
    google_api_key: Optional[str] = None

    # Azure DevOps
    azure_devops_org: Optional[str] = None
    azure_devops_project: Optional[str] = None
    azure_devops_pat: Optional[str] = None

    # GitHub (for future use)
    github_token: Optional[str] = None

    # General
    max_loop_iterations: int = 10
    default_work_item_type: str = "Task"
    default_pipeline_branch: str = "main"

    def __post_init__(self):
        """Load configuration from environment variables."""
        self.google_api_key = os.environ.get('GOOGLE_API_KEY')
        self.azure_devops_org = os.environ.get('AZURE_DEVOPS_ORG')
        self.azure_devops_project = os.environ.get('AZURE_DEVOPS_PROJECT')
        self.azure_devops_pat = os.environ.get('AZURE_DEVOPS_PAT')
        self.github_token = os.environ.get('GITHUB_TOKEN')

    @property
    def azure_devops_configured(self) -> bool:
        """Check if Azure DevOps is properly configured."""
        return all([
            self.azure_devops_org,
            self.azure_devops_project,
            self.azure_devops_pat
        ])

    @property
    def google_ai_configured(self) -> bool:
        """Check if Google AI is properly configured."""
        return self.google_api_key is not None

    def get_azure_devops_url(self) -> Optional[str]:
        """Get Azure DevOps organization URL."""
        if self.azure_devops_org:
            return f"https://dev.azure.com/{self.azure_devops_org}"
        return None


# Global configuration instance
config = GalaxyConfig()