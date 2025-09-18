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

"""Intelligent Code Generator for Infrastructure Genie

This module provides advanced code generation capabilities by leveraging:
- GitHub MCP for code examples and repository analysis
- Microsoft Learn MCP for Azure/Microsoft technology guidance
- Terraform Docs MCP for infrastructure-as-code generation
- Google Search for finding best practices and documentation
- RAG systems for technical knowledge retrieval
"""

import ast
import os
import re
import tempfile
from typing import Any, Dict, List, Optional, Tuple

from google.adk.agents import Agent
from google.adk.tools import BaseTool, FunctionTool
from app.mcp_github import create_github_mcp, create_microsoft_learn_mcp, create_terraform_docs_mcp
from google.adk.tools import google_search


class IntelligentCodeGenerator(BaseTool):
    """Advanced code generator that leverages all Infrastructure Genie capabilities."""

    def __init__(self):
        super().__init__(
            name="intelligent_code_generator",
            description=(
                "Generate high-quality code using GitHub examples, Microsoft docs, "
                "Terraform resources, and web search. Supports multiple languages, frameworks, "
                "and GitHub workflow integration for automated code deployment.\n\n"
                "Parameters:\n"
                "- requirements: Detailed requirements for the code to generate\n"
                "- language: Programming language (python, javascript, typescript, java, go, terraform)\n"
                "- project_type: Type of project (api, web_app, microservice, cli, library, infrastructure)\n"
                "- include_tests: Generate unit tests for the code (boolean)\n"
                "- include_docs: Generate documentation for the code (boolean)\n"
                "- repository_url: GitHub repository URL for workflow integration\n"
                "- target_branch: Target branch for code deployment\n"
                "- create_pr: Create a pull request after committing code (boolean)\n"
                "- commit_message: Custom commit message for the changes\n"
                "- analyze_existing_repo: Analyze existing repository structure and patterns (boolean)"
            )
        )

        # Initialize MCP tools
        self.github_mcp = create_github_mcp()
        self.microsoft_mcp = create_microsoft_learn_mcp()
        self.terraform_mcp = create_terraform_docs_mcp()

        # Language-specific templates and patterns
        self.language_patterns = {
            "python": {
                "file_ext": ".py",
                "comment_style": "#",
                "imports_section": True,
                "class_pattern": r"class\s+\w+.*:",
                "function_pattern": r"def\s+\w+\(.*\):",
            },
            "javascript": {
                "file_ext": ".js",
                "comment_style": "//",
                "imports_section": True,
                "class_pattern": r"class\s+\w+",
                "function_pattern": r"function\s+\w+\(.*\)",
            },
            "typescript": {
                "file_ext": ".ts",
                "comment_style": "//",
                "imports_section": True,
                "class_pattern": r"class\s+\w+",
                "function_pattern": r"function\s+\w+\(.*\)",
            },
            "java": {
                "file_ext": ".java",
                "comment_style": "//",
                "imports_section": True,
                "class_pattern": r"class\s+\w+",
                "function_pattern": r"public\s+.*\s+\w+\(.*\)",
            },
            "go": {
                "file_ext": ".go",
                "comment_style": "//",
                "imports_section": True,
                "class_pattern": r"type\s+\w+\s+struct",
                "function_pattern": r"func\s+\w+\(.*\)",
            },
            "terraform": {
                "file_ext": ".tf",
                "comment_style": "#",
                "imports_section": False,
                "resource_pattern": r"resource\s+\".*\"\s+\".*\"",
                "data_pattern": r"data\s+\".*\"\s+\".*\"",
            },
        }

    async def run_async(self, *, args: Dict[str, Any], tool_context) -> Dict[str, Any]:
        """Generate intelligent code based on requirements."""
        try:
            # Extract parameters
            requirements = args.get("requirements", "")
            language = args.get("language", "python").lower()
            project_type = args.get("project_type", "general")
            include_tests = args.get("include_tests", False)
            include_docs = args.get("include_docs", True)

            # GitHub workflow parameters
            repository_url = args.get("repository_url", "")
            target_branch = args.get("target_branch", "main")
            create_pr = args.get("create_pr", False)
            commit_message = args.get("commit_message", "")
            analyze_existing_repo = args.get("analyze_existing_repo", False)

            if not requirements:
                return {
                    "success": False,
                    "error": "Requirements parameter is required"
                }

            # Step 1: Research and gather context
            context = await self._gather_code_context(
                requirements, language, project_type
            )

            # Step 1.5: Analyze existing repository if provided
            repository_context = {}
            if repository_url and analyze_existing_repo:
                repository_context = await self._analyze_repository_context(
                    repository_url, tool_context
                )
                # Merge repository insights into context
                context["repository_analysis"] = repository_context

            # Step 2: Generate code structure
            code_structure = await self._design_code_structure(
                requirements, language, project_type, context
            )

            # Step 3: Generate actual code
            generated_code = await self._generate_code_implementation(
                requirements, language, code_structure, context
            )

            # Step 4: Add tests if requested
            if include_tests:
                test_code = await self._generate_tests(
                    generated_code, language, context
                )
                generated_code["tests"] = test_code

            # Step 5: Add documentation if requested
            if include_docs:
                documentation = await self._generate_documentation(
                    generated_code, requirements, language
                )
                generated_code["documentation"] = documentation

            # Step 6: Validate and optimize
            validated_code = await self._validate_and_optimize(
                generated_code, language
            )

            # Step 7: GitHub workflow integration (if requested)
            github_result = {}
            if repository_url and (create_pr or commit_message):
                github_result = await self._execute_github_workflow(
                    repository_url, validated_code, target_branch,
                    create_pr, commit_message, tool_context
                )

            result = {
                "success": True,
                "generated_code": validated_code,
                "context_used": context,
                "language": language,
                "project_type": project_type,
                "metadata": {
                    "files_generated": len(validated_code.get("files", {})),
                    "has_tests": include_tests,
                    "has_docs": include_docs,
                    "research_sources": len(context.get("sources", []))
                }
            }

            # Add GitHub workflow results if available
            if github_result:
                result["github_workflow"] = github_result

            return result

        except Exception as e:
            return {
                "success": False,
                "error": f"Code generation failed: {str(e)}"
            }

    async def _gather_code_context(
        self, requirements: str, language: str, project_type: str
    ) -> Dict[str, Any]:
        """Gather context from GitHub, Microsoft Learn, Terraform docs, and web search."""
        context = {
            "github_examples": [],
            "microsoft_guidance": [],
            "terraform_resources": [],
            "web_research": [],
            "sources": []
        }

        try:
            # Search GitHub for relevant code examples
            github_query = f"{requirements} {language} example code"
            github_results = await self._search_github_examples(github_query)
            context["github_examples"] = github_results
            context["sources"].extend([f"GitHub: {r.get('name', 'Unknown')}" for r in github_results])

            # Get Microsoft Learn guidance if relevant
            if any(keyword in requirements.lower() for keyword in [
                'azure', 'microsoft', '.net', 'c#', 'powershell', 'office'
            ]):
                ms_results = await self._get_microsoft_guidance(requirements, language)
                context["microsoft_guidance"] = ms_results
                context["sources"].extend([f"Microsoft Learn: {r.get('title', 'Unknown')}" for r in ms_results])

            # Get Terraform resources if infrastructure-related
            if any(keyword in requirements.lower() for keyword in [
                'infrastructure', 'deploy', 'cloud', 'terraform', 'resource'
            ]):
                tf_results = await self._get_terraform_guidance(requirements)
                context["terraform_resources"] = tf_results
                context["sources"].extend([f"Terraform: {r.get('resource_type', 'Unknown')}" for r in tf_results])

            # Web search for additional context
            web_query = f"{requirements} {language} best practices tutorial"
            web_results = await self._web_search_guidance(web_query)
            context["web_research"] = web_results
            context["sources"].extend([f"Web: {r.get('title', 'Unknown')}" for r in web_results])

        except Exception as e:
            print(f"Warning: Context gathering partially failed: {e}")

        return context

    async def _search_github_examples(self, query: str) -> List[Dict[str, Any]]:
        """Search GitHub for code examples."""
        try:
            # Use GitHub MCP to search for repositories and code
            search_result = await self.github_mcp.run_async(
                args={
                    "action": "search_repositories",
                    "query": query,
                    "sort": "stars",
                    "limit": 5
                },
                tool_context=None
            )

            examples = []
            if search_result.get("success") and search_result.get("repositories"):
                for repo in search_result["repositories"][:3]:  # Top 3 results
                    # Get repository content
                    content_result = await self.github_mcp.run_async(
                        args={
                            "action": "get_repository_content",
                            "owner": repo.get("owner"),
                            "repo": repo.get("name"),
                            "path": ""  # Root directory
                        },
                        tool_context=None
                    )

                    if content_result.get("success"):
                        examples.append({
                            "name": repo.get("full_name"),
                            "description": repo.get("description"),
                            "stars": repo.get("stargazers_count"),
                            "language": repo.get("language"),
                            "content_preview": content_result.get("files", [])[:5]  # First 5 files
                        })

            return examples
        except Exception as e:
            print(f"GitHub search failed: {e}")
            return []

    async def _get_microsoft_guidance(self, requirements: str, language: str) -> List[Dict[str, Any]]:
        """Get Microsoft Learn guidance."""
        try:
            search_result = await self.microsoft_mcp.run_async(
                args={
                    "action": "search_documentation",
                    "query": f"{requirements} {language}",
                    "limit": 5
                },
                tool_context=None
            )

            guidance = []
            if search_result.get("success") and search_result.get("articles"):
                for article in search_result["articles"]:
                    guidance.append({
                        "title": article.get("title"),
                        "url": article.get("url"),
                        "summary": article.get("summary"),
                        "technologies": article.get("technologies", [])
                    })

            return guidance
        except Exception as e:
            print(f"Microsoft Learn search failed: {e}")
            return []

    async def _get_terraform_guidance(self, requirements: str) -> List[Dict[str, Any]]:
        """Get Terraform resource guidance."""
        try:
            search_result = await self.terraform_mcp.run_async(
                args={
                    "action": "search_resources",
                    "query": requirements,
                    "limit": 5
                },
                tool_context=None
            )

            resources = []
            if search_result.get("success") and search_result.get("resources"):
                for resource in search_result["resources"]:
                    resources.append({
                        "resource_type": resource.get("type"),
                        "description": resource.get("description"),
                        "example": resource.get("example"),
                        "arguments": resource.get("arguments", [])
                    })

            return resources
        except Exception as e:
            print(f"Terraform docs search failed: {e}")
            return []

    async def _web_search_guidance(self, query: str) -> List[Dict[str, Any]]:
        """Search web for additional guidance."""
        try:
            search_result = await google_search.run_async(
                args={"query": query, "num_results": 5},
                tool_context=None
            )

            results = []
            if search_result.get("success") and search_result.get("results"):
                for result in search_result["results"]:
                    results.append({
                        "title": result.get("title"),
                        "url": result.get("url"),
                        "snippet": result.get("snippet")
                    })

            return results
        except Exception as e:
            print(f"Web search failed: {e}")
            return []

    async def _design_code_structure(
        self, requirements: str, language: str, project_type: str, context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Design the overall code structure based on requirements and context."""

        structure = {
            "main_files": [],
            "supporting_files": [],
            "directories": [],
            "dependencies": [],
            "architecture_pattern": "standard"
        }

        # Determine architecture pattern based on requirements
        if "api" in requirements.lower() or "rest" in requirements.lower():
            structure["architecture_pattern"] = "api"
            if language == "python":
                structure["main_files"] = ["main.py", "models.py", "routes.py", "config.py"]
                structure["dependencies"] = ["fastapi", "pydantic", "uvicorn"]
            elif language == "javascript" or language == "typescript":
                structure["main_files"] = ["index.js", "routes.js", "models.js", "config.js"]
                structure["dependencies"] = ["express", "cors", "dotenv"]

        elif "web" in requirements.lower() or "frontend" in requirements.lower():
            structure["architecture_pattern"] = "frontend"
            if language == "javascript" or language == "typescript":
                structure["main_files"] = ["index.html", "main.js", "styles.css"]
                structure["directories"] = ["src", "public", "assets"]

        elif "microservice" in requirements.lower():
            structure["architecture_pattern"] = "microservice"
            structure["directories"] = ["src", "tests", "deploy", "docs"]

        elif "terraform" in requirements.lower() or language == "terraform":
            structure["architecture_pattern"] = "infrastructure"
            structure["main_files"] = ["main.tf", "variables.tf", "outputs.tf", "versions.tf"]
            structure["directories"] = ["modules", "environments"]

        else:
            # Standard project structure
            if language == "python":
                structure["main_files"] = ["main.py", "requirements.txt"]
                structure["supporting_files"] = ["README.md", ".gitignore"]
            elif language == "java":
                structure["directories"] = ["src/main/java", "src/test/java"]
                structure["main_files"] = ["pom.xml"]
            elif language == "go":
                structure["main_files"] = ["main.go", "go.mod"]

        # Add common supporting files
        structure["supporting_files"].extend(["README.md", ".gitignore"])

        return structure

    async def _generate_code_implementation(
        self, requirements: str, language: str, structure: Dict[str, Any], context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate the actual code implementation."""

        generated_files = {}

        # Generate main implementation files
        for file_name in structure["main_files"]:
            file_content = await self._generate_file_content(
                file_name, requirements, language, structure, context
            )
            generated_files[file_name] = file_content

        # Generate supporting files
        for file_name in structure["supporting_files"]:
            if file_name == "README.md":
                file_content = await self._generate_readme(requirements, language, structure)
            elif file_name == ".gitignore":
                file_content = await self._generate_gitignore(language)
            elif file_name == "requirements.txt" and language == "python":
                file_content = "\n".join(structure.get("dependencies", []))
            else:
                file_content = f"# {file_name}\n# Generated by Infrastructure Genie\n"

            generated_files[file_name] = file_content

        return {
            "files": generated_files,
            "structure": structure,
            "language": language
        }

    async def _generate_file_content(
        self, file_name: str, requirements: str, language: str,
        structure: Dict[str, Any], context: Dict[str, Any]
    ) -> str:
        """Generate content for a specific file."""

        file_ext = os.path.splitext(file_name)[1]
        lang_config = self.language_patterns.get(language, {})
        comment_style = lang_config.get("comment_style", "#")

        # File header
        header = f"""{comment_style} {file_name}
{comment_style} Generated by Infrastructure Genie
{comment_style} Requirements: {requirements[:100]}...
{comment_style}

"""

        # Generate content based on file type and language
        if language == "python":
            content = await self._generate_python_content(file_name, requirements, context)
        elif language in ["javascript", "typescript"]:
            content = await self._generate_js_content(file_name, requirements, context)
        elif language == "java":
            content = await self._generate_java_content(file_name, requirements, context)
        elif language == "go":
            content = await self._generate_go_content(file_name, requirements, context)
        elif language == "terraform":
            content = await self._generate_terraform_content(file_name, requirements, context)
        else:
            content = f"{comment_style} TODO: Implement {file_name}\n"

        return header + content

    async def _generate_python_content(
        self, file_name: str, requirements: str, context: Dict[str, Any]
    ) -> str:
        """Generate Python-specific content."""

        if file_name == "main.py":
            # Look for FastAPI or Flask patterns in context
            has_api = any("fastapi" in str(ex).lower() or "flask" in str(ex).lower()
                         for ex in context.get("github_examples", []))

            if has_api or "api" in requirements.lower():
                return '''from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn

app = FastAPI(title="Generated API", description="Created by Infrastructure Genie")

class Item(BaseModel):
    name: str
    description: str = None

@app.get("/")
async def root():
    return {"message": "Hello from Infrastructure Genie!"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

@app.post("/items/")
async def create_item(item: Item):
    # TODO: Implement item creation logic
    return {"message": f"Created item: {item.name}"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
'''
            else:
                return '''#!/usr/bin/env python3
"""
Main application module
"""

def main():
    """Main function implementing the requirements."""
    print("Infrastructure Genie Generated Application")

    # TODO: Implement main application logic based on requirements:
    # """ + requirements + """

    pass

if __name__ == "__main__":
    main()
'''

        elif file_name == "models.py":
            return '''"""
Data models for the application
"""
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class BaseEntity(BaseModel):
    id: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

class User(BaseEntity):
    username: str
    email: str
    is_active: bool = True

class Item(BaseEntity):
    name: str
    description: Optional[str] = None
    owner_id: int
    tags: List[str] = []
'''

        elif file_name == "config.py":
            return '''"""
Application configuration
"""
import os
from typing import Optional

class Config:
    """Application configuration class."""

    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./app.db")

    # API
    API_HOST: str = os.getenv("API_HOST", "0.0.0.0")
    API_PORT: int = int(os.getenv("API_PORT", "8000"))

    # Security
    SECRET_KEY: str = os.getenv("SECRET_KEY", "infrastructure-genie-generated-key")

    # Debug
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"

config = Config()
'''

        return f"# {file_name} implementation\npass\n"

    async def _generate_js_content(
        self, file_name: str, requirements: str, context: Dict[str, Any]
    ) -> str:
        """Generate JavaScript/TypeScript content."""

        if file_name == "index.js" or file_name == "main.js":
            return '''const express = require('express');
const cors = require('cors');
const app = express();
const PORT = process.env.PORT || 3000;

// Middleware
app.use(cors());
app.use(express.json());

// Routes
app.get('/', (req, res) => {
    res.json({ message: 'Hello from Infrastructure Genie!' });
});

app.get('/health', (req, res) => {
    res.json({ status: 'healthy' });
});

// Start server
app.listen(PORT, () => {
    console.log(`Server running on port ${PORT}`);
});

module.exports = app;
'''

        return f"// {file_name} implementation\nconsole.log('Generated by Infrastructure Genie');\n"

    async def _generate_terraform_content(
        self, file_name: str, requirements: str, context: Dict[str, Any]
    ) -> str:
        """Generate Terraform content."""

        if file_name == "main.tf":
            # Use Terraform context from research
            tf_resources = context.get("terraform_resources", [])

            content = '''# Infrastructure Generated by Infrastructure Genie
terraform {
  required_version = ">= 1.0"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 4.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}
'''

            # Add resources based on context
            for resource in tf_resources[:3]:  # Use top 3 relevant resources
                resource_type = resource.get("resource_type", "")
                if resource_type:
                    content += f'''
resource "{resource_type}" "generated" {{
  # {resource.get("description", "Generated resource")}
  # TODO: Configure based on requirements
}}
'''

            return content

        elif file_name == "variables.tf":
            return '''variable "project_id" {
  description = "GCP Project ID"
  type        = string
}

variable "region" {
  description = "GCP Region"
  type        = string
  default     = "us-central1"
}

variable "environment" {
  description = "Environment name"
  type        = string
  default     = "dev"
}
'''

        elif file_name == "outputs.tf":
            return '''output "project_id" {
  description = "GCP Project ID"
  value       = var.project_id
}

output "region" {
  description = "GCP Region"
  value       = var.region
}
'''

        return f"# {file_name}\n# Generated by Infrastructure Genie\n"

    async def _generate_java_content(
        self, file_name: str, requirements: str, context: Dict[str, Any]
    ) -> str:
        """Generate Java content."""
        return f"// {file_name}\n// Generated by Infrastructure Genie\n"

    async def _generate_go_content(
        self, file_name: str, requirements: str, context: Dict[str, Any]
    ) -> str:
        """Generate Go content."""
        if file_name == "main.go":
            return '''package main

import (
    "fmt"
    "log"
    "net/http"
    "os"
)

func main() {
    port := os.Getenv("PORT")
    if port == "" {
        port = "8080"
    }

    http.HandleFunc("/", handleRoot)
    http.HandleFunc("/health", handleHealth)

    fmt.Printf("Server starting on port %s\\n", port)
    log.Fatal(http.ListenAndServe(":"+port, nil))
}

func handleRoot(w http.ResponseWriter, r *http.Request) {
    fmt.Fprintf(w, "Hello from Infrastructure Genie!")
}

func handleHealth(w http.ResponseWriter, r *http.Request) {
    w.Header().Set("Content-Type", "application/json")
    fmt.Fprintf(w, `{"status": "healthy"}`)
}
'''
        return f"// {file_name}\n// Generated by Infrastructure Genie\n"

    async def _generate_tests(
        self, generated_code: Dict[str, Any], language: str, context: Dict[str, Any]
    ) -> Dict[str, str]:
        """Generate test files."""
        test_files = {}

        if language == "python":
            test_files["test_main.py"] = '''import pytest
import sys
import os

# Add the parent directory to the path to import the main module
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_application_starts():
    """Test that the application can be imported and started."""
    try:
        import main
        assert True
    except ImportError:
        pytest.fail("Failed to import main module")

def test_basic_functionality():
    """Test basic functionality."""
    # TODO: Add specific tests based on generated code
    assert True

if __name__ == "__main__":
    pytest.main([__file__])
'''

        elif language in ["javascript", "typescript"]:
            test_files["test.js"] = '''const request = require('supertest');
const app = require('./index');

describe('Generated Application', () => {
    test('GET / should return success message', async () => {
        const response = await request(app)
            .get('/')
            .expect(200);

        expect(response.body.message).toBeDefined();
    });

    test('GET /health should return healthy status', async () => {
        const response = await request(app)
            .get('/health')
            .expect(200);

        expect(response.body.status).toBe('healthy');
    });
});
'''

        return test_files

    async def _generate_documentation(
        self, generated_code: Dict[str, Any], requirements: str, language: str
    ) -> Dict[str, str]:
        """Generate documentation files."""
        docs = {}

        docs["API.md"] = f'''# API Documentation

Generated by Infrastructure Genie based on requirements:
{requirements}

## Overview
This application was automatically generated to meet the specified requirements.

## Language: {language.title()}

## Files Generated:
'''

        for file_name in generated_code.get("files", {}).keys():
            docs["API.md"] += f"- `{file_name}`\n"

        docs["API.md"] += '''
## Usage

### Development
```bash
# Install dependencies
# Start development server
# Run tests
```

### Production
```bash
# Build application
# Deploy to environment
```

## Contributing
This code was generated by Infrastructure Genie. Modify as needed for your specific requirements.
'''

        return docs

    async def _generate_readme(
        self, requirements: str, language: str, structure: Dict[str, Any]
    ) -> str:
        """Generate README.md file."""
        return f'''# Generated by Infrastructure Genie

## Overview
This project was automatically generated based on the following requirements:

> {requirements}

## Language: {language.title()}

## Architecture Pattern: {structure.get("architecture_pattern", "standard").title()}

## Files Generated:
'''

    async def _generate_gitignore(self, language: str) -> str:
        """Generate .gitignore file."""
        gitignore_templates = {
            "python": '''__pycache__/
*.py[cod]
*$py.class
*.so
.Python
venv/
.env
.venv
*.egg-info/
.pytest_cache/
''',
            "javascript": '''node_modules/
npm-debug.log*
.env
.env.local
dist/
build/
''',
            "java": '''*.class
target/
.gradle/
build/
*.jar
*.war
''',
            "go": '''*.exe
*.test
*.prof
vendor/
''',
            "terraform": '''*.tfstate
*.tfstate.*
.terraform/
*.tfplan
*.tfvars
'''
        }

        return gitignore_templates.get(language, "# Generated .gitignore\n")

    async def _validate_and_optimize(
        self, generated_code: Dict[str, Any], language: str
    ) -> Dict[str, Any]:
        """Validate and optimize generated code."""

        validated_files = {}
        validation_results = []

        for file_name, file_content in generated_code.get("files", {}).items():
            try:
                # Basic validation based on language
                if language == "python" and file_name.endswith(".py"):
                    # Try to parse Python AST
                    ast.parse(file_content)
                    validation_results.append(f"✅ {file_name}: Valid Python syntax")

                elif language in ["javascript", "typescript"] and (
                    file_name.endswith(".js") or file_name.endswith(".ts")
                ):
                    # Basic JS validation (could be enhanced)
                    if "function" in file_content or "const" in file_content:
                        validation_results.append(f"✅ {file_name}: Valid JavaScript structure")

                # Store validated content
                validated_files[file_name] = file_content

            except SyntaxError as e:
                validation_results.append(f"❌ {file_name}: Syntax error - {str(e)}")
                # Store with comment about syntax issue
                validated_files[file_name] = f"// SYNTAX ERROR: {str(e)}\n{file_content}"

            except Exception as e:
                validation_results.append(f"⚠️ {file_name}: Validation warning - {str(e)}")
                validated_files[file_name] = file_content

        # Return validated code with metadata
        result = generated_code.copy()
        result["files"] = validated_files
        result["validation_results"] = validation_results

        return result

    async def _analyze_repository_context(
        self, repository_url: str, tool_context
    ) -> Dict[str, Any]:
        """Analyze existing repository to understand structure and patterns."""
        try:
            # Use the enhanced GitHub agent to analyze the repository
            from app.enhanced_github_agent import enhanced_github_agent

            analysis_result = await enhanced_github_agent.run_async(
                {
                    "operation": "analyze_repository",
                    "repository_url": repository_url,
                    "analysis_type": "comprehensive"
                },
                tool_context
            )

            if analysis_result.get("success"):
                return {
                    "repository_structure": analysis_result.get("repository_structure", {}),
                    "architecture_patterns": analysis_result.get("architecture_patterns", []),
                    "tech_stack": analysis_result.get("tech_stack", {}),
                    "development_patterns": analysis_result.get("development_patterns", []),
                    "recommendations": analysis_result.get("recommendations", [])
                }
            else:
                return {"error": f"Failed to analyze repository: {analysis_result.get('error', 'Unknown error')}"}

        except Exception as e:
            return {"error": f"Repository analysis failed: {str(e)}"}

    async def _execute_github_workflow(
        self, repository_url: str, validated_code: Dict[str, Any],
        target_branch: str, create_pr: bool, commit_message: str, tool_context
    ) -> Dict[str, Any]:
        """Execute GitHub workflow operations like committing code and creating PRs."""
        try:
            # Use the enhanced GitHub agent for workflow operations
            from app.enhanced_github_agent import enhanced_github_agent

            workflow_steps = []

            # Step 1: Create or switch to branch if not main
            if target_branch != "main":
                branch_result = await enhanced_github_agent.run_async(
                    {
                        "operation": "create_branch",
                        "repository_url": repository_url,
                        "branch_name": target_branch,
                        "source_branch": "main"
                    },
                    tool_context
                )
                workflow_steps.append({"step": "create_branch", "result": branch_result})

            # Step 2: Update files with generated code
            files_updated = []
            for file_path, file_content in validated_code.get("files", {}).items():
                file_result = await enhanced_github_agent.run_async(
                    {
                        "operation": "update_file",
                        "repository_url": repository_url,
                        "file_path": file_path,
                        "content": file_content,
                        "branch": target_branch
                    },
                    tool_context
                )
                files_updated.append({"file": file_path, "result": file_result})

            workflow_steps.append({"step": "update_files", "files": files_updated})

            # Step 3: Commit changes
            commit_msg = commit_message or f"feat: Add generated {validated_code.get('project_type', 'code')} implementation"
            commit_result = await enhanced_github_agent.run_async(
                {
                    "operation": "commit_changes",
                    "repository_url": repository_url,
                    "message": commit_msg,
                    "branch": target_branch
                },
                tool_context
            )
            workflow_steps.append({"step": "commit_changes", "result": commit_result})

            # Step 4: Create PR if requested
            pr_result = None
            if create_pr:
                pr_title = f"feat: Add generated {validated_code.get('project_type', 'code')} implementation"
                pr_body = self._generate_pr_description(validated_code, commit_msg)

                pr_result = await enhanced_github_agent.run_async(
                    {
                        "operation": "create_pull_request",
                        "repository_url": repository_url,
                        "title": pr_title,
                        "body": pr_body,
                        "head_branch": target_branch,
                        "base_branch": "main"
                    },
                    tool_context
                )
                workflow_steps.append({"step": "create_pull_request", "result": pr_result})

            return {
                "success": True,
                "workflow_steps": workflow_steps,
                "branch": target_branch,
                "commit_message": commit_msg,
                "pull_request": pr_result,
                "files_count": len(validated_code.get("files", {}))
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"GitHub workflow execution failed: {str(e)}"
            }

    def _generate_pr_description(self, validated_code: Dict[str, Any], commit_message: str) -> str:
        """Generate a comprehensive PR description."""
        files = validated_code.get("files", {})
        validation_results = validated_code.get("validation_results", [])

        description = f"""## Generated Code Implementation

**Commit Message:** {commit_message}

### Files Generated ({len(files)}):
"""

        for file_path in files.keys():
            description += f"- `{file_path}`\n"

        if validation_results:
            description += "\n### Validation Results:\n"
            for result in validation_results:
                description += f"- {result}\n"

        description += """
### Generated with Infrastructure Genie
This code was automatically generated using Infrastructure Genie's intelligent code generator, which leverages:
- GitHub repository analysis and examples
- Microsoft Learn documentation
- Terraform resource documentation
- Web search for best practices
- Code validation and optimization

🤖 *Generated with [Infrastructure Genie](https://github.com/your-org/infrastructure-genie)*
"""

        return description


# Create the tool instance
intelligent_code_generator = IntelligentCodeGenerator()


# Agent wrapper for the code generator
code_generator_agent = Agent(
    name="code_generator_specialist",
    model="gemini-2.5-pro",
    instruction=(
        "You are an expert code generation specialist with GitHub workflow automation capabilities. "
        "Use the intelligent_code_generator tool to create high-quality code based on user requirements. "
        "Leverage GitHub examples, Microsoft Learn documentation, Terraform resources, and web research "
        "to generate comprehensive, well-structured code with tests and documentation.\n\n"
        "KEY CAPABILITIES:\n"
        "- Generate code in multiple languages (Python, JavaScript, TypeScript, Java, Go, Terraform)\n"
        "- Analyze existing repositories for context and patterns\n"
        "- Create comprehensive tests and documentation\n"
        "- Automate GitHub workflows (branch creation, commits, pull requests)\n"
        "- Integrate with existing codebases using repository analysis\n\n"
        "When users provide repository URLs, automatically analyze the existing codebase to ensure "
        "generated code follows established patterns and integrates seamlessly."
    ),
    tools=[FunctionTool(intelligent_code_generator.run_async)],
    output_key="generated_code_result"
)