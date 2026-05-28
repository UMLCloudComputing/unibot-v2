# Orchestrator Service

This service acts as the orchestrator for the unibot-v2 application, providing a REST API endpoint for chat interactions that leverage Retrieval-Augmented Generation (RAG) and remote Model Context Protocol (MCP) tools.

## Overview

The orchestrator service is responsible for:
- Handling incoming chat requests via a FastAPI endpoint (`/v1/chat`)
- Coordinating with a local Ollama model for text generation and embeddings
- Retrieving relevant context from a Milvus vector store
- Fetching and utilizing tools from a remote MCP server
- Combining these components to produce informed, contextual responses

## Project Structure

```
orchestrator/
├── app/
│   ├── api.py          # FastAPI application and endpoint definitions
│   └── ai_stack.py     # UnifiedRemoteAIStack class orchestrating AI components
├── Dockerfile          # Containerization configuration
├── pyproject.toml      # Project metadata and dependencies
├── uv.lock             # Dependency lock file
├── CLAUDE.md           # This file - guidance for Claude Code
├── README.md           # This file - service overview
├── .env                # Environment variables (not tracked)
├── k8s-manifest.yaml   # Kubernetes deployment manifest
└── .venv/              # Python virtual environment (UV managed)
```

## Key Components

### API Layer (`app/api.py`)
- Defines the FastAPI application
- Exposes the `/v1/chat` POST endpoint
- Handles request/response formatting and error handling

### AI Stack (`app/ai_stack.py`)
- Implements `UnifiedRemoteAIStack` class
- Manages connections to:
  - Milvus vector store for document retrieval
  - Ollama for embeddings (`nomic-embed-text`) and language generation (`gpt-oss:latest`)
  - Remote MCP server for tool discovery and execution
- Orchestrates the RAG pipeline: retrieve context → format prompt → invoke LLM with available tools

## Environment Variables

The service requires the following environment variables (typically set in `.env`):

- `MCP_SERVER_BASE_URL`: URL for the remote MCP server (default: `http://localhost:8000/mcp`)
- `MILVUS_BASE_URL`: URL for Milvus vector store (default: `http://localhost:19530`)
- `MILVUS_COLLECTION`: Name of Milvus collection (default: `docs`)
- `OLLAMA_MODEL`: Ollama model to use for chat (default: `gpt-oss:latest`)
- `OLLAMA_BASE_URL`: Base URL for Ollama API (optional, defaults to localhost)

## Installation & Setup

1. Install dependencies using UV:
   ```bash
   uv sync
   ```

2. Ensure required services are running:
   - Milvus vector store
   - Ollama with the specified model
   - Remote MCP server

3. Start the service:
   ```bash
   python app/api.py
   ```
   or using uvicorn directly:
   ```bash
   uvicorn app.api:app --host 0.0.0.0 --port 8001 --reload
   ```

## API Endpoints

### POST `/v1/chat`
Send a chat request to receive a response from the AI system.

**Request Body:**
```json
{
  "message": "Your question here",
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

### GET `/health`
Health check endpoint for Kubernetes liveness/readiness probes.

**Response:**
```json
{
  "status": "healthy"
}
```
or
```json
{
  "status": "unhealthy",
  "reason": "error description"
}
```

## Notes

- The service is designed to work with the unibot-v2 ecosystem, specifically targeting information about the University of Massachusetts Lowell.
- It intentionally avoids answering questions related to academic work (homework, assignments, quizzes, exams).
- If the answer cannot be determined from the available context and tools, the service will state that it does not know the answer.