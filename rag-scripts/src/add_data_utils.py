import asyncio
import aiohttp
import logging
from tqdm import tqdm
from aiohttp import ClientSession
from queue import Queue

MAX_CONCURRENT_TASKS = 80
semaphore = asyncio.Semaphore(MAX_CONCURRENT_TASKS)

logger = logging.getLogger(__name__)

# ----------URL Chunkers----------
async def chunk_url_generator(session: ClientSession, url: str, task_registry: dict, docling_base_url: str, chunk_pbar: tqdm = None):
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

      task_registry[task_id] = url
  
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
                  source_url = task_registry.get(task_id)
                  chunks = final_data.get("chunks")
                  for chunk in chunks:
                    yield { 
                      "text": chunk.get("text"),
                      "source_url": source_url
                    }
                  if chunk_pbar:
                    chunk_pbar.update(1)
          elif msg.type in (aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.ERROR):
            break 
    except Exception as e:
      logger.error(f"Websocket error for task {task_id} | {e}")
    finally:
      if task_id in task_registry:
        del task_registry[task_id]

async def chunk_url(session: ClientSession, url: str, task_registry: dict, docling_base_url: str, chunk_queue: Queue, chunk_pbar: tqdm = None):
  """
  Asynchronously requests and adds chunks from docling by url.
  Can either operate as a generator or internally insert to a queue. 
  Toggle generator mode by setting `generator` argument to True.
  Toggle internal queue writes by `chunk_queue` argument to a Queue object.
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

      task_registry[task_id] = url
  
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
                  source_url = task_registry.get(task_id)
                  chunks = final_data.get("chunks")
                  for chunk in chunks:
                    chunk_queue.put({ 
                      "text": chunk.get("text"),
                      "source_url": source_url
                    })
                  if chunk_pbar:
                    chunk_pbar.update(1)
          elif msg.type in (aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.ERROR):
            break 
    except Exception as e:
      logger.error(f"Websocket error for task {task_id} | {e}")
    finally:
      if task_id in task_registry:
        del task_registry[task_id]


# -----------Embedders-------------
async def embedder(chunk_queue: Queue, processed_queue: Queue, embedding_pbar: tqdm):
  
