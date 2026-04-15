import threading
import time
import logging
import ollama
import asyncio
import aiohttp
from dotenv import load_dotenv
from concurrent.futures import ThreadPoolExecutor
from aiohttp import ClientSession
from queue import Queue
from tqdm import tqdm
from add_data_utils import chunk_url

# Configuration
OP_FILES_PATH = os.getenv("OP_FILES_PATH")
DOCLING_BASE_URL = os.getenv("DOCLING_BASE_URL")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL")

BATCH_SIZE = 32  # Optimized for Ollama throughput
DIMENSION = 768
MILVUS_HOST=os.getenv("MILVUS_HOST")
MILVUS_PORT=os.getenv("MILVUS_PORT")
COLLECTION_NAME=os.getenv("COLLECTION_NAME")
LOG_OUTPUT_PATH = os.getenv("LOG_OUTPUT_PATH", "logs/")

# --- Logging Setup ---
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler(LOG_OUTPUT_PATH + "add_data_v2.log")]
)

if __name__ == "__main__":
  logging.info("add_data_v2 script started")
  chunk_queue = Queue()
  embedded_queue = Queue()
  task_registry = {} # Keep track of task_id to source_url mapping
    
  # Read urls
  with open(OP_FILES_PATH + "to_add.txt", "r") as f:
    urls = [line.strip() for line in f if line.strip()]
  
  total_docs = len(urls)

  chunk_pbar = tqdm(total=total_docs, desc="[1/3] Chunking with Docling", unit="url", position=0) 
  embedding_pbar = tqdm(total=None, desc="[2/3] Generating Embeddings", unit="chunk", position=1)
  milvus_pbar = tqdm(total=None, desc="[3/3] Inserting into Milvus", unit="chunk", position=2)
  async with aiohttp.ClientSession():
   tasks = [chunk_url(session, url, task_registry, chunk_queue, DOCLING_BASE_URL, chunk_pbar) for url in urls]
     


