# Streamlit RAG Application

A Streamlit-based client application that connects to an existing MCP server for Retrieval-Augmented Generation (RAG) functionality. This application provides a user-friendly interface for querying a knowledge base powered by Milvus vector database.

## Features

- Clean, intuitive chat interface for querying the knowledge base
- Real-time health checking of the MCP server connection
- Configurable connection settings via sidebar
- Display of search results with source attribution
- Responsive design suitable for both desktop and tablet use
- Built with uv package manager for fast, reliable dependency management

## Architecture

This application follows the client-server model:
- **Streamlit App**: Acts as the client UI
- **MCP Server**: Provides the RAG functionality (already deployed in the system)
- **Milvus Database**: Stores the vectorized knowledge base
- **Ollama**: Provides embedding model for query vectorization

## Local Development

### Prerequisites

- Python 3.11+
- [uv](https://github.com/astral-sh/uv) (Astral's Python package installer)
- Running MCP server (accessible via network)

### Installation

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd streamlit-app
   ```

2. Install dependencies using uv:
   ```bash
   uv sync
   ```

3. Run the application:
   ```bash
   uv run streamlit run streamlit_app.py
   ```

4. Access the application at `http://localhost:8501`

### Configuration

The application can be configured via:
- Environment variables:
  - `MCP_SERVER_URL`: URL of the MCP server (default: `http://localhost:8000`)
  - `COLLECTION_NAME`: Milvus collection name (default: `docs`)
  - `TOP_K`: Number of search results to return (default: `5`)

- Sidebar in the Streamlit UI for runtime configuration changes

## Deployment

### Docker

Build and run the Docker container:

```bash
# Build the image
docker build -t streamlit-rag:latest .

# Run the container
docker run -p 8501:8501 \
  -e MCP_SERVER_URL="http://your-mcp-server:8000" \
  -e COLLECTION_NAME="docs" \
  -e TOP_K="5" \
  streamlit-rag:latest
```

### Kubernetes

The application includes Kubernetes manifests for deployment:

```bash
# Apply the deployment
kubectl apply -f kubernetes-deployment.yaml
```

#### Required Secrets

Create a secret named `streamlit-rag-secrets` with the following keys:
- `mcp-server-url`: Base64 encoded URL of the MCP server
- `collection-name`: Base64 encoded Milvus collection name (optional)
- `top-k`: Base64 encoded number of results (optional)

Example:
```bash
kubectl create secret generic streamlit-rag-secrets \
  --from-literal=mcp-server-url="http://mcp-service.mcp.svc.cluster.local:8000" \
  --from-literal=collection-name="docs" \
  --from-literal=top-k="5"
```

### ArgoCD Integration

The application is configured for deployment via ArgoCD:

1. The ArgoCD application manifest is located at `argocd/apps/streamlit-rag.yaml`
2. It pulls from the `streamlit-app` directory in this repository
3. Deploys to the `streamlit-rag` namespace
4. Automatically syncs and self-heals

## Usage

1. Ensure the MCP server is running and accessible
2. Optionally configure the MCP server URL in the sidebar
3. Click "Check MCP Health" to verify connectivity
4. Enter your question in the chat input
5. View the results displayed below the chat
6. Use the sidebar to adjust search settings or clear chat history

## MCP Server Communication

This application communicates with the MCP server using the standard MCP over HTTP protocol:
- Calls the `search_umass_lowell_knowledge_base` tool
- Sends JSON-RPC 2.0 formatted requests
- Expects results in the format: `[{"text": "...", "source_url": "..."}, ...]`

## Troubleshooting

### Connection Issues
- Verify the MCP server is running and accessible from the Streamlit pod/container
- Check the health endpoint: `http://mcp-server-url/health`
- Ensure network policies allow traffic between Streamlit and MCP server

### No Results
- Verify the Milvus collection has data
- Check that the embedding model is working correctly
- Ensure the MCP server can successfully query the vector database

### Performance
- Adjust replica count in the deployment based on expected load
- Monitor resource usage and adjust requests/limits accordingly
- Consider enabling caching if queries are repetitive

## Security Considerations

- The application does not authenticate users by design - consider deploying behind an auth proxy
- Secrets are managed via Kubernetes Secrets
- All communication with the MCP server is over HTTP (consider TLS for production)
- Input is sanitized by Streamlit's markdown rendering

## Maintenance

- Regularly update dependencies: `uv lock --upgrade && uv sync`
- Monitor logs for errors in both Streamlit and MCP server components
- Keep the base container image updated for security patches