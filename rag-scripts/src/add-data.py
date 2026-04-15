import threading
import time
import argparse
import os
import logging
import httpx
import ollama
from dotenv import load_dotenv
from concurrent.futures import ThreadPoolExecutor
from pymilvus import connections, FieldSchema, CollectionSchema, DataType, Collection, utility, MilvusClient
from queue import Queue, Empty
from tqdm import tqdm

load_dotenv()

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

url_queue = Queue()
chunk_queue = Queue()
processed_queue = Queue()
poll_executor = ThreadPoolExecutor(max_workers=100)

# --- Logging Setup ---
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(threadName)s - %(message)s',
    handlers=[logging.FileHandler(LOG_OUTPUT_PATH + "rag-sync-manager.log")]
)


def setup_milvus(is_worker=False):
    # Establish the global connection alias if it doesn't exist
    try:
        connections.connect("default", host=MILVUS_HOST, port=MILVUS_PORT)
    except Exception as e:
        logging.error(f"Milvus Connection Error: {e}")
        return None

    if not is_worker:
        # --- MAIN THREAD ONLY: Schema Management ---
        if not utility.has_collection(COLLECTION_NAME):
            fields = [
                FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
                FieldSchema(name="source_url", dtype=DataType.VARCHAR, max_length=512),
                FieldSchema(name="text", dtype=DataType.VARCHAR, max_length=65535),
                FieldSchema(name="vector", dtype=DataType.FLOAT_VECTOR, dim=DIMENSION)
            ]
            schema = CollectionSchema(fields, "Document chunks")
            collection = Collection(COLLECTION_NAME, schema)
            
            # Create Index
            index_params = {"metric_type": "L2", "index_type": "IVF_FLAT", "params": {"nlist": 128}}
            collection.create_index(field_name="vector", index_params=index_params)
        else:
            collection = Collection(COLLECTION_NAME)
        
        # Ensure collection is loaded into memory for all threads
        collection.load()
        return collection
    else:
        # --- WORKER THREADS: Just grab the reference ---
        collection = Collection(COLLECTION_NAME)
        return collection


def single_task_poller(task_id, original_url, pbar):
    logging.info(f"Poller-Start: {task_id} for {original_url}")
    with httpx.Client(timeout=30) as client:
        while True:
            try:
                status_resp = client.get(f"{DOCLING_BASE_URL}/v1/status/poll/{task_id}")
                status_resp.raise_for_status()
                status = status_resp.json().get("task_status")

                if status == "success":
                    res_resp = client.get(f"{DOCLING_BASE_URL}/v1/result/{task_id}")
                    res_resp.raise_for_status()
                    result_data = res_resp.json()

                    results = result_data.get("results", [])
                    chunks = results[0].get("chunks", []) if results else result_data.get("chunks", [])
                    
                    for chunk in chunks:
                        chunk_queue.put({
                            "text": chunk.get("text"),
                            "source_url": original_url,
                        })
                    
                    logging.info(f"Poller-Success: {original_url}")
                    pbar.update(1)
                    break 

                elif status == "failure":
                    logging.error(f"Poller-Failure: {task_id} ({original_url})")
                    pbar.update(1)
                    break

                time.sleep(2) 
            except Exception as e:
                logging.error(f"Poller-Error: {task_id} | {e}")
                time.sleep(5)

def docling_worker(submit_pbar, poll_pbar):
    with httpx.Client(timeout=30) as client:
        while True:
            url = url_queue.get()
            if url is None:
                url_queue.task_done()
                break
            try:
                payload = {
                    "sources": [{"url": url, "kind": "http"}],
                    "chunker_options": {"max_tokens": 512, "overlap": 30},
                    "convert_options": {
                        "do_table_structure": True,
                        "to_formats": ["md"],
                        "table_mode": "accurate"
                    }
                }             
                response = client.post(f"{DOCLING_BASE_URL}/v1/chunk/hybrid/source/async", json=payload)
                response.raise_for_status()
                task_id = response.json().get("task_id")   

                poll_executor.submit(single_task_poller, task_id, url, poll_pbar)
                submit_pbar.update(1)
            except Exception as e:
                logging.error(f"Submission Error {url}: {e}")
                submit_pbar.update(1)
            finally:
                url_queue.task_done()

def embedding_worker(embedding_pbar):
    """
    Reads from chunk_queue, batches items for Ollama, 
    and pushes to processed_queue.
    """
    client = ollama.Client(host=OLLAMA_BASE_URL)
    while True:
        batch = []
        sentinel_found = False
        # Attempt to fill a batch
        try:
            # Get at least one item (blocking)
            first_item = chunk_queue.get(timeout=5)
            if first_item is None:
                chunk_queue.task_done()
                return 

            batch.append(first_item)

            # Try to get more items until BATCH_SIZE is reached (non-blocking)
            while len(batch) < BATCH_SIZE:
                try:
                    next_item = chunk_queue.get_nowait()
                    if next_item is None:
                        # Put it back so other threads/loops see the sentinel
                        chunk_queue.put(None)
                        sentinel_found = True
                        break
                    batch.append(next_item)
                except Empty:
                    break
        except Empty:
            # If nothing arrived in 5 seconds, check if we are totally done
            continue
        if batch:
            try:
                texts = [item["text"] for item in batch]
                # Batch embedding call (Order-preserving)
                response = client.embed(model="nomic-embed-text", input=texts)
                vectors = response["embeddings"]
                if len(vectors) == len(batch): 
                    for i, vector in enumerate(vectors):
                        processed_queue.put({
                            "text": batch[i]["text"],
                            "source_url": batch[i]["source_url"],
                            "vector": vector
                        })
            
                embedding_pbar.update(len(batch))
            
            except Exception as e:
                logging.error(f"Batch Embedding Error: {e}")
            finally:
                for _ in range(len(batch)):
                    chunk_queue.task_done()
        if sentinel_found:
            return

def milvus_worker(milvus_pbar):
    """
    Consumes from processed_queue and inserts into Milvus in batches.
    """
    collection = setup_milvus(is_worker=True)
    
    while True:
        batch = []
        try:
            # Greedy batching from processed_queue
            item = processed_queue.get(timeout=10)
            if item is None:
                processed_queue.task_done()
                break
            batch.append(item)
            
            while len(batch) < 50: # Milvus likes larger batches
                try:
                    next_item = processed_queue.get_nowait()
                    if next_item is None:
                        processed_queue.put(None)
                        break
                    batch.append(next_item)
                except Empty:
                    break
        except Empty:
            continue

        if batch:
            try:
                # Prepare data in column-format for Milvus
                data = [
                    [item["source_url"] for item in batch],
                    [item["text"] for item in batch],
                    [item["vector"] for item in batch]
                ]
                collection.insert(data)
                milvus_pbar.update(len(batch))
            except Exception as e:
                logging.error(f"Milvus Insert Error: {e}")
            finally:
                for _ in range(len(batch)):
                    processed_queue.task_done()


if __name__ == "__main__":
    print("[INIT] Setting up Milvus Connection...")
    setup_milvus(is_worker=False)

    with open(OP_FILES_PATH + "to_add.txt", "r") as f:
        urls = [line.strip() for line in f if line.strip()]

    total_docs = len(urls)

    # Initialize Progress Bars
    # Since total chunks is unknown, embedding_pbar and milvus_pbar start with total=None
    submit_pbar = tqdm(total=total_docs, desc="[1/4] Submitting to Docling", unit="doc", position=0)
    poll_pbar = tqdm(total=total_docs, desc="[2/4] Polling Docling Tasks", unit="doc", position=1)
    embedding_pbar = tqdm(total=None, desc="[3/4] Generating Embeddings", unit="chunk", position=2)
    milvus_pbar = tqdm(total=None, desc="[4/4] Inserting into Milvus", unit="chunk", position=3)

    # Adjust as needed
    num_submitters=40
    num_embedders=30
    num_inserters=30

    for i in range(num_inserters):
        threading.Thread(target=milvus_worker, args=(milvus_pbar,), name="Inserter-{i}", daemon=True).start()

    # Start Embedding Workers
    for i in range(num_embedders):
        threading.Thread(target=embedding_worker, args=(embedding_pbar,), name=f"Embedder-{i}", daemon=True).start()

    # Start Submitter Workers
    submit_threads = []
    for i in range(num_submitters):
        t = threading.Thread(target=docling_worker, args=(submit_pbar, poll_pbar), name=f"Submitter-{i}", daemon=True)
        t.start()
        submit_threads.append(t)

    # Load URLs
    for url in urls:
        url_queue.put(url)
    
    # Wait for Submission stage
    url_queue.join()
    for _ in range(num_submitters): url_queue.put(None)
    for t in submit_threads: t.join()
    submit_pbar.close()

    # Wait for Polling stage
    poll_executor.shutdown(wait=True)
    poll_pbar.close()

    # Send sentinel to Embedders and wait
    for _ in range(num_embedders): chunk_queue.put(None)
    chunk_queue.join()
    embedding_pbar.close()

    # Send sentinel to Inserters and wait
    for _ in range(num_inserters): processed_queue.put(None)
    processed_queue.join()
    milvus_pbar.close()

    # Finished
    print(f"\n[FINISH] Pipeline complete") 
    print(f"Total processed results in queue: {processed_queue.qsize()}")
    print("Check database for processed chunks and logs for errors")
