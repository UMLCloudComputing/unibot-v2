# Orchestrator Service Usage and Design

This document provides detailed usage instructions and design information for the unibot-v2 orchestrator service component.

## Overview

The orchestrator service is the central AI processing component of the unibot-v2 system. It acts as a REST API endpoint that receives chat requests, processes them using a combination of local language models (via Ollama), remote MCP (Model Context Protocol) tools, and vector store retrieval (from Milvus), then returns informed, contextual responses.

## Key Features

### Core Functionality

- **REST API Endpoint**: Exposes `/v1/chat` POST endpoint for chat interactions and `/health` GET endpoint for monitoring
- **Autonomous AI Agent**: Uses LangGraph to create an autonomous agent that can dynamically choose between using MCP tools or providing direct LLM responses
- **MCP Tool Integration**: Connects to remote MCP servers to discover and execute tools dynamically
- **Specialized Assistant**: Configured to specialize in University of Massachusetts Lowell information while refusing to answer academic work-related questions

### Technical Implementation

- Built with FastAPI for high-performance async web framework
- Uses LangGraph for orchestrating AI workflows
- Integrates with Ollama for local language model inference
- Connects to remote MCP servers via `langchain-mcp-adapters`
- Employs Ollama's nomic-embed-text for text vectorization
- Fully asynchronous architecture for handling concurrent requests
- Structured logging with configurable log levels

## System Architecture

### Component Diagram

```
[Discord Bot / Streamlit UI / External Client]
             ↓ (HTTP POST to /v1/chat)
[Orchestrator Service (FastAPI)]
             ↓
[LangGraph Orchestrator] ←→ [Ollama LLM] + [Milvus Vector Store] + [Remote MCP Tools]
             ↓
[Response] ← (returns as JSON) [Orchestrator Service] ← (sends to) [Discord Bot / Streamlit UI / External Client]
```

### Data Flow

1. Client (Discord bot, Streamlit UI, or external service) sends POST request to `/v1/chat` with:
   - `message`: The user's query
   - `history`: Optional conversation history (array of role/content objects)
2. Orchestrator's `handle_chat_request` function:
   - Converts history to LangChain message format
   - Delegates to `UnifiedRemoteAIStack.chat()` method
3. AI Stack processing:
   - Initializes MCP client and LangGraph on first request (lazy initialization)
   - Retrieves conversation history and user message
   - Constructs prompt with system instructions specialized for UMass Lowell
   - LLM autonomously decides whether to use MCP tools or provide direct response
   - If tools are selected:
     - Executes tools via MCP client
     - Incorporates tool results into context
     - May iterate multiple times based on tool results
   - Retrieves relevant context from Milvus vector store (RAG)
   - Generates final response using Ollama LLM
4. Returns JSON response with status and response text
5. Updates conversation history in client (Discord bot/Streamlit) via Redis

### Session Management (Client-Side)

Note: The orchestrator itself is stateless and does not manage conversation sessions. Session history is managed by client applications:

- **Discord Bot**: Uses Redis with key format `session:{user_id}`, stores last 10 exchanges with 1-hour TTL
- **Streamlit UI**: Manages session state internally

### Error Handling

The orchestrator implements multiple layers of error handling:

1. **API Level**:
   - HTTP exception handling with appropriate status codes
   - Validation of request payloads via Pydantic models
   - Detailed error logging for debugging
2. **AI Processing Level**:
   - Exception catching during graph execution
   - Graceful degradation when individual components fail
   - Health check endpoint for Kubernetes monitoring
3. **External Dependencies**:
   - Timeout handling for MCP tool execution (120 seconds)
   - Timeout handling for Ollama requests
   - Connection error handling for Milvus and MCP servers

## Usage Instructions

### Prerequisites

Before running the orchestrator service, ensure you have:

1. Access to a running Ollama instance with the specified model
2. Access to one or more remote MCP servers
3. Access to a Milvus vector store instance
4. Python 3.9+ installed (or Docker for containerized deployment)

### Environment Configuration

Create a `.env` file in the orchestrator directory with the following variables:

| Variable | Description | Default Value |
|----------|-------------|---------------|
| `MCP_SERVER_1` | First MCP server configuration (NAME,URL) - e.g., `uml-now-mcp,http://localhost:8000/mcp` | `http://localhost:8000/mcp` |
| `MCP_SERVER_2` | Second MCP server configuration (NAME,URL) - e.g., `uml-search-mcp,http://localhost:8001/mcp` | `http://localhost:8001/mcp` |
| `OLLAMA_MODEL` | Ollama model to use for chat | `gpt-oss:latest` |
| `OLLAMA_BASE_URL` | Base URL for Ollama API (optional) | (defaults to localhost) |
| `OLLAMA_HOST` | Alternative Ollama host (used in docker-compose) | `http://192.168.1.207:11434` |

Note: The orchestrator also supports `MILVUS_BASE_URL` and `MILVUS_COLLECTION` environment variables (from previous versions), though the current implementation focuses on MCP tools and Ollama.

### Running the Service

#### Local Development

1. Install dependencies:

   ```bash
   uv sync
   ```

2. Ensure required services are running:
   - Ollama with the specified model
   - Remote MCP server(s)
3. Start the service:

   ```bash
   python app/api.py
   # or
   uv run app/api.py
   # or using uvicorn directly:
   uvicorn app.api:app --host 0.0.0.0 --port 8001 --reload
   ```

#### Docker Container

1. Build the image:

   ```bash
   docker build -t unibot-v2-orchestrator .
   ```

2. Run the container:

   ```bash
   docker run --env-file .env -p 8001:8001 unibot-v2-orchestrator
   ```

#### Docker Compose (from project root)

```bash
docker-compose up
```

#### Kubernetes Deployment

1. Apply the manifests:

   ```bash
   kubectl apply -f k8s/k8s-manifest.yaml
   ```

2. The Kubernetes deployment includes:
   - Namespace: `api-orchestrator`
   - ConfigMap `api-orchestrator-config` with environment variables
   - Deployment with 2 replicas
   - Service exposing the API on port 8001
   - Resource requests/limits:
     - Requests: 512Mi memory, 250m CPU
     - Limits: 1Gi memory, 500m CPU
   - Liveness and readiness probes on `/health` endpoint

### API Endpoints

#### POST `/v1/chat`

Send a chat request to receive a response from the AI system.

**Request Body:**

```json
{
  "message": "Your question about UMass Lowell here",
  "history": [
    {"role": "user", "content": "Previous user message"},
    {"role": "assistant", "content": "Previous assistant response"}
  ]
}
```

**Response:**

```json
{
  "status": "success",
  "response": "AI-generated response text"
}
```

#### GET `/health`

Health check endpoint for Kubernetes liveness/readiness probes.

**Response (healthy):**

```json
{
  "status": "healthy"
}
```

**Response (unhealthy):**

```json
{
  "status": "unhealthy",
  "reason": "error description"
}
```

## Design Considerations

### Intentionally Limited Scope

The orchestrator focuses exclusively on:

- Processing chat requests via REST API
- Providing AI-powered responses using LLMs, vector stores, and MCP tools
- Maintaining stateless operation for horizontal scalability

It does not:

- Manage user sessions or conversation history (handled by clients)
- Provide administrative or monitoring endpoints beyond basic health checks
- Implement complex authentication or authorization mechanisms

### Extensibility Points

1. **Adding New MCP Servers**: Modify the `MCP_SERVER_1` and `MCP_SERVER_2` environment variables or update the ConfigMap in Kubernetes
2. **Modifying LLM Parameters**: Adjust Ollama parameters in `app/ai_stack.py` (temperature, top_p, top_k)
3. **Changing System Prompt**: Edit the system message in `app/ai_stack.py` lines 104-110
4. **Updating Dependencies**: Edit `pyproject.toml` and run:

   ```bash
   uv lock
   uv sync
   ```

### Deployment Considerations

- **Resource Usage**: Designed for moderate resource consumption (suitable for small to medium VMs or containers)
- **Scaling**: Horizontally scalable due to stateless nature; multiple instances can be deployed behind a load balancer
- **Security**:
  - No sensitive data stored persistently (stateless)
  - MCP server API keys can be passed through environment variables
  - Communication with external services should use internal network endpoints in production
  - Consider adding authentication middleware for production deployments

## Relationship to Other Components

### Discord Bot and Streamlit UI

The orchestrator service acts as the AI backend for both the Discord bot and Streamlit UI clients:

- Transforms client requests into orchestrator-compatible format
- Processes requests through its AI stack
- Returns standardized JSON responses
- Clients are responsible for managing user-specific state (conversation history)

### Kubernetes Deployment

When deployed via Kubernetes:

- Runs in the `api-orchestrator` namespace
- Uses ConfigMap `api-orchestrator-config` for environment variables
- Configured with resource requests/limits as specified above
- Includes liveness and readiness probes on `/health` endpoint
- Exposes service internally as `api-orchestrator-svc:8001`

### External MCP Servers

The orchestrator connects to remote MCP servers to:

- Discover available tools dynamically
- Execute tools as needed during AI processing
- Incorporate tool results into the LLM's decision-making process
- Currently supports up to two MCP servers via `MCP_SERVER_1` and `MCP_SERVER_2` variables

## Maintenance and Troubleshooting

### Logging

The orchestrator outputs structured logs with configurable levels:

- Default level is DEBUG (as set in `ai_stack.py`)
- Can be adjusted by modifying the `logging.basicConfig()` call
- Logs include timestamps, logger names, and message content

### Common Issues

1. **Service Not Starting**:
   - Verify all required environment variables are set
   - Check that Ollama, MCP servers, and Milvus are accessible
   - Look for import errors in logs (missing dependencies)

2. **No Response or Errors to Chat Requests**:
   - Check orchestrator logs for error details
   - Verify MCP server connectivity and tool availability
   - Ensure Ollama is running with the correct model
   - Look for timeout errors in logs

3. **Health Check Failures**:
   - Verify the `/health` endpoint is accessible
   - Check if AI coordinator initialized successfully
   - Look for initialization errors in logs

### Health Checks

The orchestrator exposes a `/health` endpoint that:

- Returns `{"status": "healthy"}` when the service is operational
- Returns `{"status": "unhealthy", "reason": "..."}` when issues are detected
- Used by Kubernetes for liveness and readiness probes
- Performs basic initialization checks (verifies AI coordinator is not None)

## Future Enhancements

Potential areas for future development include:

- Adding support for more than two MCP servers
- Implementing configurable retrieval parameters (top-k, similarity thresholds)
- Adding metrics export (Prometheus-compatible)
- Implementing request/response caching for frequent queries
- Adding authentication and authorization middleware
- Implementing circuit breaker patterns for external service failures
- Adding support for different LLM providers (not just Ollama)
- Implementing more sophisticated conversation summarization for history management
