# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Running the Service
```bash
# Start the FastAPI server
python app/api.py

# Or using uvicorn directly
uvicorn app.api:app --host 0.0.0.0 --port 8001 --reload
```

### Environment Setup
The service requires several environment variables (typically set in `.env`):
- `MCP_SERVER_BASE_URL`: URL for the remote MCP server (default: http://localhost:8000/mcp)
- `MILVUS_BASE_URL`: URL for Milvus vector store (default: http://localhost:19530)
- `MILVUS_COLLECTION`: Name of Milvus collection (default: docs)
- `OLLAMA_MODEL`: Ollama model to use (default: gpt-oss:latest)
- `OLLAMA_BASE_URL`: Base URL for Ollama API (optional)

### Dependencies
Dependencies are managed via UV. To install:
```bash
uv sync
```

## Code Architecture

### High-Level Structure
The orchestrator service follows a modular architecture:

1. **API Layer** (`app/api.py`): 
   - FastAPI application exposing REST endpoints
   - `/v1/chat` endpoint handles chat requests with conversation history

2. **AI Stack** (`app/ai_stack.py`):
   - `UnifiedRemoteAIStack` class orchestrates all AI components
   - Integrates Retrieval-Augmented Generation (RAG) with remote MCP tools
   - Uses local Ollama models for embeddings and language generation

3. **Core Components**:
   - **Vector Store**: Milvus for document storage and retrieval
   - **Embeddings**: Ollama's nomic-embed-text for text vectorization
   - **Language Model**: Ollama ChatOllama for text generation
   - **MCP Integration**: MultiServerMCPClient for connecting to remote tools
   - **Prompt Engineering**: Structured prompts with system instructions, chat history, and user questions

### Data Flow
1. User sends chat request to `/v1/chat` endpoint
2. Request processed by `handle_chat_request` in `app/api.py`
3. Delegated to `UnifiedRemoteAIStack.chat()` method
4. Retrieves relevant context from Milvus vector store
5. Fetches available tools from remote MCP server
6. Combines context, tools, and conversation history in LLM prompt
7. Streams response back to user

### Key Design Patterns
- **Dependency Injection**: Services configured via constructor parameters
- **Async/Await**: Fully asynchronous for handling concurrent requests
- **Lazy Initialization**: MCP client and tools fetched on-demand
- **Modular Chains**: LangChain Expression Language (LCEL) for composable pipelines

## Common Tasks

### Adding New MCP Tools
New tools are automatically discovered from the remote MCP server. No code changes needed unless you want to filter or modify tool behavior.

### Modifying Retrieval Parameters
Adjust search parameters in `app/ai_stack.py`:
- Change `search_kwargs={"k": 3}` to retrieve more/less documents
- Modify `_format_docs` method to change context formatting

### Changing System Prompt
Edit the system message in `app/ai_stack.py` lines 124-132 to adjust assistant behavior.

## Testing
Currently no formal test suite exists. Manual testing can be done via:
```bash
curl -X POST http://localhost:8001/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello", "history": []}'
```