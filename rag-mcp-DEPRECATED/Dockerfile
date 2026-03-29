# Use a lightweight Python image
FROM ghcr.io/astral-sh/uv:debian-slim 

# Set working directory
WORKDIR /app

# Install system dependencies (needed for some vector math libs)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
# Note: You'll need mcp[fastapi], pymilvus, sentence-transformers, uvicorn
COPY pyproject.toml .
RUN uv sync

# Copy the server code
COPY server.py .

# Expose the port for K8s service routing
EXPOSE 8000

# Set environment variables
# ENV MILVUS_URI="http://milvus-cluster-milvus.milvus-cluster.svc.cluster.local:19530"
# ENV COLLECTION_NAME="docs"
# ENV OLLAMA_HOST="http://192.168.0.193:11434"
# ENV TOP_K=5
# ENV ADDRESS="0.0.0.0"

# Run the server using Uvicorn
CMD ["uv", "run", "server.py"]
