# server.py
import os
import time
import logging
from typing import AsyncIterator
from ollama import Client as OllamaClient
from contextlib import asynccontextmanager
from fastmcp import FastMCP, Context
from fastmcp.server.lifespan import lifespan
from pymilvus import MilvusClient
from starlette.responses import JSONResponse

# Configuration
MILVUS_URI = os.getenv("MILVUS_URI", "http://localhost:19530")
COLLECTION_NAME = os.getenv("COLLECTION_NAME", "docs")
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://192.168.0.193:11434")
TOP_K = os.getenv("TOP_K", 5)
ADDRESS = os.getenv("ADDRESS", "127.0.0.1")

# Logging


# Globals
milvus_client = None
ollama_client = None

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
  global milvus_client, ollama_client

  try:
    # Startup the connections
    milvus_client = MilvusClient(uri=MILVUS_URI)
    milvus_client.load_collection(COLLECTION_NAME)
    print(f"Connected to Milvus at {MILVUS_URI}") 
    ollama_client = OllamaClient(host=OLLAMA_HOST)
    print(f"Connected to Ollama embedding model at {OLLAMA_HOST}")
    yield
  finally:
    if milvus_client:
      milvus_client.release_collection(COLLECTION_NAME)
      milvus_client.close()

# MCP server setup
mcp_server = FastMCP("RAG-agentic-service", lifespan=app_lifespan)


@mcp_server.tool(
  name = "search_knowledge_base",
  description = "Search the internal vector database for information about the University of Massachusetts Lowell",
  tags = {"rag"},
  meta = {"version": "0.1", "author": "Gurpreet Singh"}
)
async def search_knowledge_base(query: str) -> list[dict]:
    """Searches internal vector database using provided user query"""
    global milvus_client, ollama_client 
     
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
        search_params={"metric__type": "L2"},
        limit=int(TOP_K),
        output_fields=["text", "source_url"],
      )
   
    return [{"text": result.get("entity")["text"], "source_url": result.get("entity")["source_url"]} for result in results[0]]


@mcp_server.custom_route("/health", methods=["GET"])
async def health_check(request):
  global milvus_client, ollama_client 
  if milvus_client is None:
    return JSONResponse({"status": "uninitialized", "message": "Milvus client not connected"}, status_code=503)
  if ollama_client is None:
    return JSONResponse({"status": "uninitialzed", "message": "Ollama client not connected"}, status_code=503)
  try:
    milvus_client.list_collections()
    ollama_client.list()
  except Exception as e:
    return JSONResponse({"status": "error", "message": str(e)}, status_code=503)
  
  return JSONResponse({"status": "healthy"})


if __name__ == "__main__":
    mcp_server.run(transport="streamable-http", host=ADDRESS, port=8000)
  
