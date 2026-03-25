# server.py
import os
import time
from typing import AsyncIterator
from ollama import Client
from contextlib import asynccontextmanager
from fastmcp import FastMCP, Context
from fastmcp.server.lifespan import lifespan
from pymilvus import MilvusClient
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware import Middleware
# Configuration
MILVUS_URI = os.getenv("MILVUS_URI", "http://localhost:19530")
COLLECTION_NAME = os.getenv("COLLECTION_NAME", "docs")
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://192.168.0.193:11434")
TOP_K = os.getenv("TOP_K", 5)
ADDRESS = os.getenv("ADDRESS", "127.0.0.1")

@asynccontextmanager
async def timeit(label: str):
  now = time.monotonic()
  try:
    yield
  finally:
    print(f"DEBUG: {label} took {time.monotonic() - now:4f}s")


# Persistent connection lifecycle
@lifespan
async def app_lifespan(app: FastMCP) -> AsyncIterator[dict]:
  # Startup the connections
  milvus = MilvusClient(uri=MILVUS_URI)
  milvus.load_collection(COLLECTION_NAME)
  print(f"Connected to Milvus at {MILVUS_URI}") 
  ollama = Client(host=OLLAMA_HOST)
  print("Connected to Ollama embedding model")

  try:
    yield {"milvus": milvus, "ollama": ollama}
  finally:
    milvus.release_collection(COLLECTION_NAME)
    milvus.close()
    

# MCP server setup
mcp_server = FastMCP("RAG-agentic-service", lifespan=app_lifespan)

@mcp_server.tool()
async def search_knowledge_base(query: str, ctx: Context):
    """Searches internal vector database using provided user query"""
    resources = ctx.lifespan_context
    milvus_client: MilvusClient = resources["milvus"] 
    ollama_client: Client = resources["ollama"]

     
    async with timeit("Ollama Embedding"):
      embeddings = ollama_client.embed(
        model = "nomic-embed-text",
        input = query
      )
      vector = embeddings["embeddings"][0]

  
    async with timeit("Milvus Search"):
      results = milvus_client.search(
        collection_name = COLLECTION_NAME,
        data=[vector],
        limit=TOP_K,
        output_fields=["text", "source_url"],
      )
   
    return {"results": results}

if __name__ == "__main__":
    mcp_server.run(transport="streamable-http", host=ADDRESS, port=8000)
  
