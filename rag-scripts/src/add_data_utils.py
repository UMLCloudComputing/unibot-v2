import asyncio
import aiohttp
import logging
from tqdm.asyncio import tqdm
from aiohttp import ClientSession
from asyncio import Queue as asyncQueue
from asyncio import Semaphore, QueueEmpty
from queue import Queue as tsQueue
from ollama import AsyncClient
from pymilvus import connections, FieldSchema, CollectionSchema, DataType, Collection, utility, MilvusClient

logger = logging.getLogger(__name__)

# ----------URL Chunkers----------
async def chunk_url_generator(session: ClientSession, url: str, 
                              docling_base_url: str, semaphore: Semaphore, chunk_pbar: tqdm = None):
  """
  Asynchronously requests and yields chunks from docling by url.
  Follows generator pattern.
  """
  async with semaphore:
    payload = {
      "sources": [{"url": url, "kind": "http"}],
      "chunker_options": {"max_tokens": 512, "overlap": 30},
      "convert_options": {
        "do_table_structures": True,
        "to_formats": ["md"],
        "table_mode": "accurate"
      }
    }
    async with session.post(f"http://{docling_base_url}/v1/chunk/hybrid/source/async", json=payload) as resp:
      if resp.status != 200:
        logger.error(f"Failed to submit {url}") 
        return 
      data = await resp.json()
      task_id = data["task_id"]

  
    ws_url = f"ws://{docling_base_url}/v1/status/ws/{task_id}"
  
    try:
      async with session.ws_connect(ws_url) as ws:
        async for msg in ws:
          if msg.type == aiohttp.WSMsgType.TEXT:
            status_update = msg.json()
            if status_update["message"] == "update": 
              if status_update["task"]["task_status"] in ("success"):
                results_url = f"http://{docling_base_url}/v1/result/{task_id}"
                async with session.get(results_url) as results_resp:
                  final_data = await results_resp.json()
                  chunks = final_data.get("chunks")
                  for chunk in chunks:
                    yield { 
                      "text": chunk.get("text"),
                      "source_url": url
                    }
                  if chunk_pbar:
                    chunk_pbar.update(1)
          elif msg.type in (aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.ERROR):
            break 
    except Exception as e:
      logger.error(f"Websocket error for task {task_id} | {e}")

async def chunk_url(session: ClientSession, url: str, 
                    docling_base_url: str, chunk_queue: asyncQueue, semaphore: Semaphore, chunk_pbar: tqdm = None) :
  """
  Asynchronously requests and adds chunks from docling by url.
  """
  async with semaphore:
    payload = {
      "sources": [{"url": url, "kind": "http"}],
      "chunker_options": {"max_tokens": 512, "overlap": 30},
      "convert_options": {
        "do_table_structures": True,
        "to_formats": ["md"],
        "table_mode": "accurate"
      }
    }
    async with session.post(f"http://{docling_base_url}/v1/chunk/hybrid/source/async", json=payload) as resp:
      if resp.status != 200:
        logger.error(f"Failed to submit {url}") 
        return 
      data = await resp.json()
      task_id = data["task_id"]

  
    ws_url = f"ws://{docling_base_url}/v1/status/ws/{task_id}"
  
    try:
      async with session.ws_connect(ws_url) as ws:
        async for msg in ws:
          if msg.type == aiohttp.WSMsgType.TEXT:
            status_update = msg.json()
            if status_update["message"] == "update": 
              if status_update["task"]["task_status"] in ("success"):
                results_url = f"http://{docling_base_url}/v1/result/{task_id}"
                async with session.get(results_url) as results_resp:
                  final_data = await results_resp.json()
                  chunks = final_data.get("chunks")
                  for chunk in chunks:
                    await chunk_queue.put({ 
                      "text": chunk.get("text"),
                      "source_url": url
                    })
                  if chunk_pbar:
                    chunk_pbar.update(1)
          elif msg.type in (aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.ERROR):
            break 
    except Exception as e:
      logger.error(f"Websocket error for task {task_id} | {e}")

# -----------Embedders-------------
async def embedder(client: AsyncClient, chunk_queue: asyncQueue, 
                   processed_queue: tsQueue, stop_event: asyncio.Event,
                   embedding_pbar: tqdm = None, batch_size: int = 32):
    """
        Asynchronously reads from chunk_queue, batches items for Ollama,
        and pushes to processed_queue. 
        Stops when either the stop event is triggered or when the chunk_queue is empty.
        Requires an external asyncio Event object to orchestrate termination.
        Batch first approach, processed_queue contains batches, not individual chunk embeddings. 
    """
    loop = asyncio.get_running_loop()
    while not(stop_event.is_set() and chunk_queue.empty()):
        batch = []
        # Attempt to fill batch
        try:
            # Get at least one item
            try:
                item = await asyncio.wait_for(chunk_queue.get(), timeout=1.0)
                batch.append(item)
            except (asyncio.TimeoutError, QueueEmpty):
                continue
            
            # Build batch
            while len(batch) < batch_size:
                try:
                    next_item = chunk_queue.get_nowait()
                    batch.append(next_item)
                except QueueEmpty:
                    break

            texts = [item["text"] for item in batch]
            response = await client.embed(model="nomic-embed-text", input=texts)
            vectors = response["embeddings"]
            # Wrap ollama response with metadata into single batch
            # Pre-formatted in column-order format for Milvus
            processed_batch = [
                {
                    "source_url": batch[i]['source_url'],
                    "text": texts[i],
                    "vector": vectors[i]
                }
                for i in range(len(batch))
            ]
            # Allows for non-blocking behavior to operate with thread safe queue
            await loop.run_in_executor(
                None, processed_queue.put, processed_batch
            )
            if embedding_pbar:
                embedding_pbar.update(len(batch))
                
        except Exception as e:
            logger.error(f"Embedder Error: {e}")
        finally:
            for _ in range(len(batch)):
                chunk_queue.task_done()

# --- Milvus Worker ---
def milvus_worker(processed_queue: tsQueue, milvus_host: str, milvus_port: str, 
                  collection_name: str, milvus_pbar: tqdm = None):
    """
    Consumes from processed_queue and inserts into Milvus in batches.
    Exits only when a None sentinel is recieved.
    """
    client = MilvusClient(uri=f"http://{milvus_host}:{milvus_port}")
    try:
        while True:
            batch = processed_queue.get()
            if batch is None:
                logger.info("Milvus worker received shutdown signal")
                break

            try:
                client.insert(collection_name=collection_name, data=batch)
                
                if milvus_pbar:
                    milvus_pbar.update(len(batch))

            except Exception as e:
                logger.error(f"Milvus Insert Error: {e}")

            finally:
                # Mark batch as done
                processed_queue.task_done()
    finally:
        client.close()
