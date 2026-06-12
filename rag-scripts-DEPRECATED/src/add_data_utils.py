import asyncio
import aiohttp
import logging
import httpx
from threading import Event
from tqdm.asyncio import tqdm
from tqdm import tqdm as tstqdm
from aiohttp import ClientSession
from asyncio import Queue as asyncQueue
from asyncio import Semaphore, QueueEmpty
from queue import Queue as tsQueue
from queue import Empty
from ollama import Client
from pymilvus import MilvusClient

logger = logging.getLogger(__name__)


# ----------URL Chunkers----------
async def chunk_url_generator(
    session: ClientSession,
    url: str,
    docling_base_url: str,
    semaphore: Semaphore,
    chunk_pbar: tqdm = None,
):
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
                "table_mode": "accurate",
            },
        }
        async with session.post(
            f"http://{docling_base_url}/v1/chunk/hybrid/source/async", json=payload
        ) as resp:
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
                                results_url = (
                                    f"http://{docling_base_url}/v1/result/{task_id}"
                                )
                                async with session.get(results_url) as results_resp:
                                    final_data = await results_resp.json()
                                    chunks = final_data.get("chunks")
                                    for chunk in chunks:
                                        yield {
                                            "text": chunk.get("text"),
                                            "source_url": url,
                                        }
                                if chunk_pbar:
                                    chunk_pbar.update(1)
                                break
                    elif msg.type in (
                        aiohttp.WSMsgType.CLOSED,
                        aiohttp.WSMsgType.ERROR,
                    ):
                        break
        except Exception as e:
            logger.error(f"Websocket error for task {task_id} | {e}")


async def chunk_url(
    session: ClientSession,
    url: str,
    docling_base_url: str,
    chunk_queue: asyncQueue,
    semaphore: Semaphore,
    pbar: tqdm = None,
):
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
                "table_mode": "accurate",
            },
        }
        post_url = f"http://{docling_base_url}/v1/chunk/hybrid/source/async"
        async with session.post(post_url, json=payload) as resp:
            if resp.status != 200:
                logger.error(f"Failed to submit {url}")
                return
            data = await resp.json()
            task_id = data["task_id"]
            logger.info(f"Successfully submitted {url} to docling")

        poll_url = f"http://{docling_base_url}/v1/status/poll/{task_id}"
        result_url = f"http://{docling_base_url}/v1/result/{task_id}"

        while True:
            try:
                async with session.get(poll_url, params={"wait": 10}) as status_resp:
                    status_resp.raise_for_status()
                    data = await status_resp.json()
                    status = data.get("task_status")

                    if status == "success":
                        async with session.get(result_url) as res_resp:
                            res_resp.raise_for_status()
                            result_data = await res_resp.json()

                            chunks = result_data.get("chunks", [])

                            for chunk in chunks:
                                await chunk_queue.put(
                                    {"text": chunk.get("text"), "source_url": url}
                                )

                            logger.info(f"Poller-Success: {url}")
                            if pbar is not None:
                                pbar.update(1)

                            break

                    elif status == "failure":
                        logger.error(f"Poller-Failure: {task_id} ({url})")
                        break

            except Exception as e:
                logger.error(f"Poller-Error: {task_id} | {e}")


def chunk_url_sync(
    docling_base_url: str, url_queue: tsQueue, chunk_queue: tsQueue, pbar: tstqdm = None
):
    """
    Consumes URLs from the url_queue, produces chunks using docling,
    annotates each chunk with its source url, and inserts them into the chunk_queue.
    Synchronous, designed for multi-threading, not asynchronous time-slice preemption.
    """
    with httpx.Client() as client:
        while True:
            try:
                url = url_queue.get(timeout=1)
            except Empty:
                break
            try:
                payload = {
                    "sources": [{"url": url, "kind": "http"}],
                    "chunking_options": {
                        # "max_tokens": 1024,
                        # "overlap": 102,
                        "merge_peers": False
                    },
                    "convert_options": {
                        "do_table_structures": True,
                        "to_formats": ["md"],
                        "table_mode": "accurate",
                        "ocr_engine": "tesseract",
                    },
                }
                resp = client.post(
                    f"http://{docling_base_url}/v1/chunk/hybrid/source", json=payload
                )
                resp.raise_for_status()

                data = resp.json()
                chunks = data["chunks"]
                for chunk in chunks:
                    chunk_queue.put({"text": chunk.get("text"), "source_url": url})

                if pbar is not None:
                    pbar.update(1)

            except httpx.HTTPStatusError as e:
                logger.error(
                    f"Server error {e.response.status_code} while processing {url}"
                )
            except httpx.RequestError as e:
                logger.error(f"Network error occured while requesting {url}: {e}")
            except Exception as e:
                logger.error(f"Unexpected error: {e}")
            finally:
                url_queue.task_done()


# -----------Embedders-------------
async def embedder(
    client: Client,
    chunk_queue: asyncQueue,
    processed_queue: tsQueue,
    stop_event: asyncio.Event,
    embedding_pbar: tqdm = None,
    batch_size: int = 128,
):
    """
    Asynchronously reads from chunk_queue, batches items for Ollama,
    and pushes to processed_queue.
    Stops when either the stop event is triggered or when the chunk_queue is empty.
    Requires an external asyncio Event object to orchestrate termination.
    Batch first approach, processed_queue contains batches, not individual chunk embeddings.
    """
    while not (chunk_queue.empty() and stop_event.is_set()):
        batch = []
        texts = []
        # Attempt to fill batch
        try:
            # Get at least one item
            try:
                item = await asyncio.wait_for(chunk_queue.get(), timeout=5.0)
                texts.append(item["text"])
                batch.append(item)
            except (asyncio.TimeoutError, QueueEmpty):
                continue

            # Build batch
            while len(batch) < batch_size:
                try:
                    next_item = chunk_queue.get_nowait()
                    texts.append(next_item["text"])
                    batch.append(next_item)
                except QueueEmpty:
                    break

            response = client.embed(model="nomic-embed-text", input=texts)
            vectors = response["embeddings"]
            # Wrap ollama response with metadata into single batch
            # Pre-formatted in column-order format for Milvus
            processed_batch = [
                {
                    "source_url": batch[i]["source_url"],
                    "text": texts[i],
                    "vector": vectors[i],
                }
                for i in range(len(batch))
            ]

            # This is a blocking operation since it's over a thread safe queue
            processed_queue.put(processed_batch)

            if embedding_pbar is not None:
                embedding_pbar.update(len(batch))

        except Exception as e:
            logger.error(f"Embedder Error: {e}")
        finally:
            for _ in range(len(batch)):
                chunk_queue.task_done()


def embedder_sync(
    ollama_base_url: str,
    chunk_queue: tsQueue,
    embedding_queue: tsQueue,
    batch_size: int = 128,
    pbar: tstqdm = None,
):
    client = Client(ollama_base_url)
    while True:
        batch = []
        texts = []
        try:
            try:
                item = chunk_queue.get(timeout=15)
                texts.append(item["text"])
                batch.append(item)
            # Complete thread when the queue is empty
            except Empty:
                return

            # Build a batch
            while len(batch) < batch_size:
                try:
                    item = chunk_queue.get(timeout=5)
                    texts.append(item["text"])
                    batch.append(item)
                except Empty:
                    break
            resp = client.embed("nomic-embed-text", input=texts)
            vectors = resp["embeddings"]
            processed_batch = [
                {
                    "source_url": batch[i]["source_url"],
                    "text": texts[i],
                    "vector": vectors[i],
                }
                for i in range(len(batch))
            ]
            embedding_queue.put(processed_batch)
            if pbar is not None:
                pbar.update(len(batch))
        except Exception as e:
            logger.error(f"Embedder error: {e}")
        finally:
            for _ in range(len(batch)):
                chunk_queue.task_done()


# --- Milvus Worker ---
def milvus_worker(
    processed_queue: tsQueue,
    milvus_host: str,
    milvus_port: str,
    collection_name: str,
    stop_event: Event,
    milvus_pbar: tstqdm = None,
):
    """
    Consumes from processed_queue and inserts into Milvus in batches.
    Exits when queue is empty and stop event is set.
    """
    client_properties = {
        "keep_alive_time_ms": 60000,  # Send a ping every 60 seconds
        "keep_alive_timeout_ms": 20000,  # Wait 20s for ping response
        "keep_alive_permit_without_calls": True,  # Ping even if no data is being sent
        "max_connection_idle_ms": 300000,  # Allow connection to be idle for 5 mins
    }
    client = MilvusClient(
        uri=f"http://{milvus_host}:{milvus_port}", client_properties=client_properties
    )
    try:
        while not stop_event.is_set() or not processed_queue.empty():
            try:
                batch = processed_queue.get(timeout=10)

                try:
                    client.insert(collection_name=collection_name, data=batch)

                    if milvus_pbar is not None:
                        milvus_pbar.update(len(batch))
                    logger.info(f"Inserted {len(batch)} chunks into Milvus")

                except Exception as e:
                    logger.error(f"Milvus Insert Error: {e}")

                finally:
                    # Mark batch as done
                    processed_queue.task_done()
            except Empty:
                # Queue is empty, however the prodcer is not done producing
                continue
    finally:
        client.close()
