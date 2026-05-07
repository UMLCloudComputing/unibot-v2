import threading
import logging
import ollama
import os
import asyncio
import aiohttp
from dotenv import load_dotenv
from concurrent.futures import ThreadPoolExecutor
from asyncio import Queue as asyncQueue
from queue import Queue as tsQueue
from tqdm.asyncio import tqdm
from pymilvus import MilvusClient, DataType

from add_data_utils import chunk_url, embedder, milvus_worker

_ = load_dotenv()

# Configuration
OP_FILES_PATH = os.getenv("OP_FILES_PATH", "data/")
DOCLING_BASE_URL = os.getenv("DOCLING_BASE_URL", "")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "")

BATCH_SIZE = 32  # Optimized for Ollama throughput
DIMENSION = 768
MILVUS_HOST=os.getenv("MILVUS_HOST")
MILVUS_PORT=os.getenv("MILVUS_PORT", 19530)
COLLECTION_NAME=os.getenv("COLLECTION_NAME", "docs")
LOG_OUTPUT_PATH = os.getenv("LOG_OUTPUT_PATH", "logs/")
NUM_WORKERS = int(os.getenv("NUM_WORKERS", 15))
MAX_CONCURRENT_TASKS = 20

# --- Logging Setup ---
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler(LOG_OUTPUT_PATH + "add_data_v2.log")]
)

async def add_data(chunk_queue: asyncQueue, processed_queue: tsQueue):
    with open(OP_FILES_PATH + "to_add.txt", "r") as f:
            urls = [line.strip() for line in f if line.strip()]

    total_docs = len(urls)

    chunk_pbar = tqdm(total=total_docs, desc="[1/3] Chunking with Docling", unit="url", position=0) 
    embedding_pbar = tqdm(total=None, desc="[2/3] Generating Embeddings", unit="chunk", position=1)
    milvus_pbar = tqdm(total=None, desc="[3/3] Inserting into Milvus", unit="chunk", position=2)

    client = ollama.Client(OLLAMA_BASE_URL)
    stop_event = asyncio.Event()
    semaphore = asyncio.Semaphore(MAX_CONCURRENT_TASKS)
     
    # Tells remote Milvus DB to load collection to query node
    setup_milvus() 

    milvus_executor = ThreadPoolExecutor(max_workers=NUM_WORKERS)

    for _ in range(NUM_WORKERS):
        milvus_executor.submit(milvus_worker, processed_queue, MILVUS_HOST, MILVUS_PORT, COLLECTION_NAME, stop_event, milvus_pbar)


    async with aiohttp.ClientSession() as session:
        
        embedder_tasks = [embedder(client, chunk_queue, processed_queue, stop_event, 
                embedding_pbar, BATCH_SIZE)
                for _ in range(NUM_WORKERS)]

        chunker_tasks = [chunk_url(session, url, DOCLING_BASE_URL, 
                chunk_queue, semaphore, chunk_pbar) 
                for url in urls]

        await asyncio.gather(*chunker_tasks)
        chunk_pbar.close()
        stop_event.set()

        await asyncio.gather(*embedder_tasks)
        embedding_pbar.close()

        for _ in range(NUM_WORKERS):
            processed_queue.put(None)

        await asyncio.gather(*milvus_futures)

    milvus_executor.shutdown(wait=True)
    milvus_pbar.close()


def setup_milvus(host = MILVUS_HOST, port = MILVUS_PORT, collection_name = COLLECTION_NAME, dimension = DIMENSION):
    """
    Main Thread: Ensures collection exists, is indexed, and is loaded into memory.
    """
    client = MilvusClient(uri=f"http://{host}:{port}")

    if not client.has_collection(collection_name):
        schema = client.create_schema(auto_id=True, enable_dynamic_field=False)
        
        schema.add_field(field_name="id", datatype=DataType.INT64, is_primary=True)
        schema.add_field(field_name="source_url", datatype=DataType.VARCHAR, max_length=512)
        schema.add_field(field_name="text", datatype=DataType.VARCHAR, max_length=65535)
        schema.add_field(field_name="vector", datatype=DataType.FLOAT_VECTOR, dim=dimension)

        index_params = client.prepare_index_params()
        index_params.add_index(
            field_name="vector",
            metric_type="L2",
            index_type="IVF_FLAT",
            params={"nlist": 128}
        )

        client.create_collection(
            collection_name=collection_name,
            schema=schema,
            index_params=index_params
        )
        print(f"Collection {collection_name} created.")

    client.load_collection(collection_name)
    client.close() # Close management connection

if __name__ == "__main__":
    logging.info("add_data_v2 script started")
    chunk_queue = asyncQueue()
    processed_queue = tsQueue()
    asyncio.run(add_data(chunk_queue, processed_queue))


