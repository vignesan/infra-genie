# Infrastructure Genie: Technical Overview

This document provides a comprehensive technical overview of the Infrastructure Genie application, detailing its architecture, core concepts, features, technical stack, deployment strategies, and future enhancements.

## 1. Introduction: Defining the Infrastructure Genie

The **Infrastructure Genie** is an intelligent multi-agent system built with Google's Agent Development Kit (ADK). It automates complex technical tasks across infrastructure, tools, and coding using Generative AI (GenAI). Designed for scalable, secure, and efficient technical problem-solving and automation, it orchestrates workflows, answers technical queries, and automates DevOps processes.

## 2. Core Concepts

The Infrastructure Genie is built upon the foundational principles and primitives of the Google ADK, enabling modular, composable, and observable agent-based solutions.

*   **ADK (Agent Development Kit):** A framework for building, orchestrating, and deploying AI agents.
*   **Agents:** The core intelligent units. The system uses various specialized `LlmAgent`s (LLM-driven) and `SequentialAgent`s (workflow orchestration).
*   **Tools:** Callable functions or classes that provide external capabilities to agents (e.g., interacting with APIs, executing shell commands, performing searches).
*   **RAG (Retrieval Augmented Generation):** A technique used by agents to retrieve information from external knowledge bases (like documentation, codebases, web search) to ground their responses and code generation, reducing hallucinations.

## 3. Architecture

The Infrastructure Genie employs a modular, scalable, and intelligent agent-based architecture, with a central orchestrator delegating tasks to specialized sub-agents.

### 3.1 High-Level Overview

The system processes user prompts or webhook triggers through a FastAPI application. An ADK Runner then orchestrates the `root_agent` (Infrastructure Genie), which intelligently delegates tasks to various specialized sub-agents. These sub-agents interact with external tools and APIs, with the entire system deployed on Google Cloud Run.

```
[User Prompt (Current)]
       |
       V
[Webhook (Enhancement)]
       |
       V
[FastAPI App (Entrypoint)]
       |
       V
   [ADK Runner]
       |
       V
[root_agent (Infrastructure Genie)]
       |
       V
[Specialized Sub-Agents (GitHub, Microsoft, Terraform, Search, Diagrams, Code Gen)]
       |
       V
[External Tools/APIs (GitHub, Azure DevOps, Google Search, Cloud APIs)]
       |
       V
[Cloud Run (Deployment Platform)]
```
*(Image Placeholder: A simple block diagram illustrating the flow from input to deployment, similar to the text above.)*

### 3.2 Detailed Agent Breakdown

The `Infrastructure Genie` comprises a `root_agent` that orchestrates several specialized sub-agents, each designed for a specific technical domain.

1.  **`github_sub_agent` (`github_specialist`)**:
    *   **Purpose**: Extracts information from GitHub repositories using `create_github_mcp()`.
    *   **Focus**: Repository architecture, tech stack, deployment configurations for diagram generation.
    *   **Output**: `github_info` in session state.

2.  **`microsoft_sub_agent` (`microsoft_specialist`)**:
    *   **Purpose**: Retrieves information from Microsoft Learn documentation using `create_microsoft_learn_mcp()`.
    *   **Focus**: Azure service details, architecture patterns, component relationships, configurations, and best practices for diagram generation.
    *   **Output**: `microsoft_info` in session state.

3.  **`terraform_sub_agent` (`terraform_specialist`)**:
    *   **Purpose**: Works with Terraform documentation and generates infrastructure-as-code using `create_terraform_docs_mcp()`.
    *   **Focus**: Generating Terraform resource blocks, configurations, and providers; explicitly generates code, not diagrams.
    *   **Output**: `terraform_info` in session state.

4.  **`search_sub_agent` (`search_specialist`)**:
    *   **Purpose**: A general technical search specialist using `google_search`.
    *   **Focus**: General technical knowledge, best practices, and architecture patterns when other specialists lack specific information.
    *   **Output**: `search_info` in session state.

5.  **`image_generation_sub_agent` (`image_generation_specialist`)**:
    *   **Purpose**: Generates technical images/diagrams using an AI-driven approach via `generate_technical_image`.
    *   **Focus**: Analyzing context (GitHub, Microsoft, search info) to identify cloud providers, services, architecture patterns, and data flows, then generating Python diagrams code.
    *   **Output**: `image_result` (status) in session state.

6.  **`diagrams_expert_agent` (`diagrams_expert`)**:
    *   **Purpose**: A RAG-powered diagram specialist with code generation capabilities, preferred for diagram requests.
    *   **Focus**: Uses RAG knowledge to generate accurate Python code for professional technical diagrams.

7.  **`code_generator_agent` (`code_generator_specialist`)**:
    *   **Purpose**: Creates complete applications, APIs, and infrastructure code.
    *   **Focus**: Uses GitHub examples, Microsoft docs, and Terraform resources for code generation.

8.  **`root_agent` (`infrastructure_genie`)**:
    *   **Purpose**: The main orchestrator for the entire `infrastructure-genie` application. It coordinates and delegates tasks to the specialized sub-agents based on the user's request.
    *   **Instruction**: Provides a comprehensive overview of its capabilities (diagrams, code generation, research) and defines a clear priority order for delegating tasks to its specialized tools/sub-agents.
    *   **Tools**: Uses `AgentTool` to wrap all the specialized sub-agents, allowing the `root_agent` (an `LlmAgent`) to call them as tools.

### 3.3 Data Flow

The system's data flow is orchestrated through the ADK's `Session` and `State` mechanisms. User prompts or webhook payloads initiate a session. The `root_agent` processes the input, leveraging its specialized sub-agents and their tools. Intermediate results and contextual information are stored and shared via the `session.state`, enabling a coherent multi-turn interaction and complex task execution.

## 4. Key Features

*   **Intelligent RAG (Retrieval Augmented Generation):** Accesses and synthesizes information from diverse sources (e.g., documentation, codebases) to inform agent decisions.
*   **Diagram Generation:** Automates the creation of technical diagrams based on infrastructure descriptions or code analysis.
*   **Code Compliance & Guardrails:** Integrates with compliance APIs to ensure generated or modified code adheres to predefined standards.
*   **Automated Code Modification & CI/CD:** Handles end-to-end code changes, Git operations, Pull Request creation, and CI/CD pipeline management triggered by external events.
*   **Comprehensive Technical Knowledge:** Answers queries and provides solutions across infrastructure, tools, and coding domains.

## 5. Technical Stack

The Infrastructure Genie is built using a robust and modern cloud-native technical stack:

*   **Framework:** Google ADK (Python)
*   **LLM:** Google Gemini (Flash/Pro)
*   **Web Framework:** FastAPI
*   **Dependency Management:** `uv` (for fast, reproducible builds)
*   **Tools:** Custom `FunctionTool`s for Git, GitHub API, Azure DevOps API, MCPs (Model Context Protocols).
*   **Cloud Services:** Google Cloud Run, Google Cloud Build, Google Secret Manager.

## 6. Deployment

This project uses Google Cloud for deployment, leveraging serverless and automated CI/CD practices.

### 6.1 Local Development

For local development and testing, you can run the application directly:

1.  **Prerequisites:** Ensure Python 3.11, `uv`, `gcloud` CLI, Docker, and Git are installed.
2.  **Clone Repository:** `git clone https://github.com/your-repo/infrastructure-genie.git && cd infrastructure-genie`
3.  **Install Dependencies:** `uv sync`
4.  **Environment Variables:** Set common variables (e.g., `GOOGLE_CLOUD_PROJECT`, `GOOGLE_API_KEY`) in a `.env` file at the project root.
5.  **Run Application:** `uv run app.server:app --host 0.0.0.0 --port 8080`

### 6.2 Cloud Deployment

The main `infrastructure-genie` agent is deployed to Google Cloud Run, with CI/CD managed by Google Cloud Build.

*   **Containerization:** Docker is used to create reproducible application images.
*   **CI/CD Pipeline:** Defined in `.cloudbuild/staging.yaml` (and `deploy-to-prod.yaml`), automating the build, test, and deployment process.
*   **Deployment Target:** Google Cloud Run provides a fully managed, scalable, and cost-effective serverless environment.
*   **Security:** Sensitive environment variables (like PATs and API keys) are securely managed using Google Secret Manager and referenced in Cloud Build configurations.

*(Image Placeholder: A DevOps pipeline diagram showing source code -> Cloud Build -> Docker Image -> Cloud Run deployment.)*

## 7. Usage

To interact with the `Infrastructure Genie` agent, you can send prompts to its FastAPI endpoint.

1.  **Local Interaction:** If running locally, send POST requests to `http://localhost:8080/run` with your prompts.
2.  **Deployed Interaction:** If deployed to Cloud Run, send POST requests to your service URL (e.g., `https://your-service-url.run.app/run`).

Example Request (using `curl`):

```bash
curl -X POST "http://localhost:8080/run" \
     -H "Content-Type: application/json" \
     -d '{
           "user_id": "test_user",
           "session_id": "test_session",
           "new_message": {
             "parts": [
               {"text": "Generate a simple Python FastAPI application that returns 'Hello World'."}
             ]
           }
         }'
```

## 8. Future Enhancements

The vision for Infrastructure Genie extends towards fully autonomous, intelligent technical problem-solving and automation.

*   **Automated Request Fulfillment from Ticketing Systems:**
    *   Users submit requests (e.g., new feature, bug fix) in Azure Boards, Jira, or ServiceNow.
    *   Engineers approve requests with a specific comment (e.g., "Genie: Approved").
    *   Webhooks send request details to the agent.
    *   Agent automatically writes/modifies code, runs pipelines, creates PRs, and updates the ticket.
*   Integration with more cloud providers (AWS, Azure).
*   Advanced error recovery and self-healing capabilities.
*   Natural language interface for complex technical problem-solving.
*   Broader range of automated DevOps tasks.
