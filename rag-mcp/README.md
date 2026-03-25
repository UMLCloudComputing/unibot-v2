# RAG MCP Server

An MCP server for making search requests into the Milvus vector database. Enables agentic capabilities for models that support function calling.

## Lifespan
Objects that are initialized during the server's startup and persist until it's end.
- Persistent connection to Milvus through `MilvusClient` object.
- Persistent connection to Ollama through a [Ollama] `Client` object. 

## Tools
- `search_knowledge_base`
  - Embeds user query to a vector and searches Milvus vector database for top `TOP_K` chunks.


## Deployment
- Development
  - Can be run directly using `uv run server.py`. 
  - Run with MCP inspector to test locally. 
  - `npx @modelcontextprotocol/inspector http://localhost:3000`

- Production
  - Build into a container using the provided Dockerfile. 
  - Publish image to a registry and reference in k8s deployments as an image. 
  - Scale by replica count on your deployment manifest and load balance within the cluster using a k8s service.

## Required env variables (production)
- MILVUS_URI
- COLLECTION_NAME
- OLLAMA_HOST
- ADDRESS
- TOP_K
    

