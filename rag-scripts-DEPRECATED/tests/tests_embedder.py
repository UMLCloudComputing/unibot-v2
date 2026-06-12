import pytest
import asyncio
import aiohttp
import time
from ollama import Client
from asyncio import Queue as asyncQueue
from concurrent.futures import ThreadPoolExecutor
from queue import Queue as tsQueue
from mock_server import mock_ollama_client, mock_docling, mock_ollama_server
from unittest.mock import MagicMock
from src import embedder, embedder_sync, chunk_url
from src.add_data_utils import chunk_url_sync

MAX_CONCURRENT_TASKS = 80


# Tests
@pytest.mark.asyncio
async def test_mock_ollama_client_contract():
    """Verifies the mock async ollama client follows the expected Ollama API protocol."""
    client = mock_ollama_client()
    response1 = client.embed("nomic-embed-text", input="Dummy Text")
    response2 = client.embed("nomic-embed-text", input=["Dummy", "Text"])
    assert len(response1["embeddings"][0]) == 768, "Incorrect dimension for embedding"
    assert response1["model"] == "nomic-embed-text", (
        "Response has incorrect model metadata"
    )
    assert type(response2["embeddings"][0]) is list, (
        "Batched processing returns invalid embedding type"
    )
    assert len(response2["embeddings"]) == 2, (
        "Incorrect number of embeddings returned in batched process"
    )
    assert response2["model"] == "nomic-embed-text", (
        "Batched response has incorrect model metadata"
    )
    assert len(response2["embeddings"][0]) == 768, (
        "Batched response embedding has incorrect dimension"
    )


@pytest.mark.asyncio
async def test_embedder_success():
    client = mock_ollama_client()
    chunk_queue = asyncQueue()
    processed_queue = tsQueue()
    embedding_pbar = MagicMock()
    stop_event = asyncio.Event()

    BATCH_SIZE = 3
    NUM_CHUNKS = 3
    for i in range(NUM_CHUNKS):
        await chunk_queue.put(
            {"text": f"Chunk {i}", "source_url": f"http://example.com/site{i}"}
        )

    stop_event.set()

    await embedder(
        client, chunk_queue, processed_queue, stop_event, embedding_pbar, BATCH_SIZE
    )

    assert processed_queue.qsize() == 1, "Processed queue has incorrect batch count"
    batch = processed_queue.queue[0]
    assert len(batch[0]) == 3, "Batch should have three keys (source_url, text, vector)"
    assert batch[0]["source_url"] == "http://example.com/site0", (
        "source_url column mismatch"
    )
    assert batch[0]["text"] == "Chunk 0", "text column mismatch"
    assert len(batch[0]["vector"]) == 768, "Vector dimension mismatch"
    assert embedding_pbar.update.called, "Embedding progress bar updates not called"

    # Based on the batch size interval, since there are 3 chunks and the batch size is 3, the update happens only once
    # # of updates = int(# chunks / batch_size)
    # Adjust accordingly
    assert embedding_pbar.update.call_count == int(NUM_CHUNKS / BATCH_SIZE), (
        "Embedding progress bar updated wrong amount"
    )


@pytest.mark.asyncio
async def test_embedder_concurrency():
    client = mock_ollama_client()
    chunk_queue = asyncQueue()
    processed_queue = tsQueue()
    embedding_pbar = MagicMock()
    stop_event = asyncio.Event()

    NUM_CHUNKS = 1000
    NUM_WORKERS = 10
    BATCH_SIZE = 50
    for i in range(NUM_CHUNKS):
        await chunk_queue.put(
            {"text": f"Chunk {i}", "source_url": f"https://example.com/{i}"}
        )

    stop_event.set()

    embedder_tasks = [
        asyncio.create_task(
            embedder(
                client,
                chunk_queue,
                processed_queue,
                stop_event,
                embedding_pbar,
                BATCH_SIZE,
            ),
            name=f"Worker-{i}",
        )
        for i in range(NUM_WORKERS)
    ]

    await asyncio.gather(*embedder_tasks)
    batch = processed_queue.queue[0]
    assert len(batch) == BATCH_SIZE, "Incorrect number of source_url values in batch"
    assert processed_queue.qsize() >= int(NUM_CHUNKS / BATCH_SIZE), (
        "Incorrect number of batches produced"
    )
    assert embedding_pbar.update.call_count == int(NUM_CHUNKS / BATCH_SIZE), (
        "Incorrect number of batch updates to progress bar"
    )


@pytest.mark.asyncio
async def test_embedder_live_producer():
    # Setup Params
    NUM_URLS = 100
    BATCH_SIZE = 10
    NUM_WORKERS = 5
    MAX_CONCURRENT_TASKS = 20

    chunk_pbar = MagicMock()
    chunk_queue = asyncQueue()
    processed_queue = tsQueue()
    semaphore = asyncio.Semaphore(MAX_CONCURRENT_TASKS)

    client = mock_ollama_client()
    stop_event = asyncio.Event()
    embedding_pbar = MagicMock()

    async with mock_docling() as base_url:
        async with aiohttp.ClientSession() as session:
            chunker_tasks = [
                chunk_url(
                    session,
                    f"http://url-{i}.com",
                    base_url,
                    chunk_queue,
                    semaphore,
                    chunk_pbar,
                )
                for i in range(NUM_URLS)
            ]

            embedder_tasks = [
                embedder(
                    client,
                    chunk_queue,
                    processed_queue,
                    stop_event,
                    embedding_pbar,
                    BATCH_SIZE,
                )
                for _ in range(NUM_WORKERS)
            ]
            await asyncio.gather(*chunker_tasks)
            stop_event.set()
            await asyncio.gather(*embedder_tasks)

    assert type(processed_queue.queue[0]) is list, "Processed batch is not a list"


@pytest.mark.limit_memory("512 MB")
@pytest.mark.asyncio
async def test_embedder_live_producer_throughput():
    # Setup Params
    NUM_URLS = 20000
    BATCH_SIZE = 50
    NUM_WORKERS = 10
    MAX_CONCURRENT_TASKS = 80

    TIME_THRESHOLD_SECONDS = 120

    chunk_pbar = MagicMock()
    chunk_queue = asyncQueue()
    processed_queue = tsQueue()
    semaphore = asyncio.Semaphore(MAX_CONCURRENT_TASKS)

    client = mock_ollama_client()
    stop_event = asyncio.Event()
    embedding_pbar = MagicMock()

    async with mock_docling() as base_url:
        start_time = time.perf_counter()

        async with aiohttp.ClientSession() as session:
            chunker_tasks = [
                chunk_url(
                    session,
                    f"http://url-{i}.com",
                    base_url,
                    chunk_queue,
                    semaphore,
                    chunk_pbar,
                )
                for i in range(NUM_URLS)
            ]

            embedder_tasks = [
                asyncio.create_task(
                    embedder(
                        client,
                        chunk_queue,
                        processed_queue,
                        stop_event,
                        embedding_pbar,
                        BATCH_SIZE,
                    ),
                    name=f"Worker-{i}",
                )
                for i in range(NUM_WORKERS)
            ]
            await asyncio.gather(*chunker_tasks)
            stop_event.set()
            await asyncio.gather(*embedder_tasks)

    end_time = time.perf_counter()
    total_duration = end_time - start_time
    throughput = NUM_URLS / total_duration

    assert total_duration < TIME_THRESHOLD_SECONDS, (
        f"Throughput too low! {throughput:2f} URLs/s\nBenchmark througput should be {NUM_URLS / TIME_THRESHOLD_SECONDS} URLs/s."
    )


#
# @pytest.mark.asyncio
# async def test_embedder_concurrency_live_server():
#     client = Client("http://192.168.0.193:11434")
#     chunk_queue = asyncQueue()
#     processed_queue = tsQueue()
#     embedding_pbar = MagicMock()
#     stop_event = asyncio.Event()
#
#     NUM_CHUNKS = 1000
#     NUM_WORKERS = 10
#     BATCH_SIZE = 50
#     for i in range(NUM_CHUNKS):
#         await chunk_queue.put({"text": f"Chunk {i}", "source_url": f"https://example.com/{i}"})
#
#     stop_event.set()
#
#     embedder_tasks = [
#         asyncio.create_task(
#             embedder(client, chunk_queue,
#                         processed_queue, stop_event,
#                         embedding_pbar, BATCH_SIZE),
#             name = f"Worker-{i}"
#         )
#         for i in range(NUM_WORKERS)
#     ]
#
#     await asyncio.gather(*embedder_tasks)
#     batch = processed_queue.queue[0]
#     assert len(batch) == BATCH_SIZE, "Incorrect batch size of response"
#     assert processed_queue.qsize() >= int(NUM_CHUNKS / BATCH_SIZE), "Incorrect number of batches produced"
#     assert embedding_pbar.update.call_count == int(NUM_CHUNKS / BATCH_SIZE), "Incorrect number of updates to progress bar"
#
#


@pytest.mark.asyncio
async def test_mock_ollama_server_contract():
    async with mock_ollama_server() as ollama_base_url:
        client = Client(f"http://{ollama_base_url}")

        # Must be run in a thread
        # ollama Client uses httpx internally
        # httpx causes a blocking network I/O operation which can't be run on the same thread
        def call_embed():
            return client.embed("nomic-embed-text", input="dummy text")

        loop = asyncio.get_running_loop()
        with ThreadPoolExecutor() as pool:
            response = await loop.run_in_executor(pool, call_embed)

    assert response["model"] == "nomic-embed-text", (
        "Incorrect embedding model in response"
    )
    assert len(response["embeddings"]) == 1, "Incorrect number of response embeddings"
    assert len(response["embeddings"][0]) == 3, "Incorrect embedding dimension"


@pytest.mark.asyncio
async def test_embedder_sync_success():
    NUM_CHUNKS = 5
    chunk_queue = tsQueue()
    for i in range(NUM_CHUNKS):
        chunk_queue.put({"source_url": f"http://example-{i}.com", "text": f"text-{i}"})
    embedding_queue = tsQueue()
    mock_pbar = MagicMock()

    async with mock_ollama_server() as ollama_base_url:
        loop = asyncio.get_running_loop()
        with ThreadPoolExecutor() as pool:
            await loop.run_in_executor(
                pool,
                embedder_sync,
                ollama_base_url,
                chunk_queue,
                embedding_queue,
                NUM_CHUNKS,
                mock_pbar,
            )
    batch = embedding_queue.queue[0]
    assert embedding_queue.qsize() == 1, (
        "Incorrect number of batches in embedding response"
    )
    assert len(batch) == NUM_CHUNKS, "Batch contains incorrect number of embeddings"
    assert batch[0]["source_url"] == "http://example-0.com", (
        "Incorrect source_url for first embedding"
    )
    assert batch[0]["text"] == "text-0", "Incorrect text for first embedding"
    assert len(batch[0]["vector"]) == 3, (
        "Incorrect embedding dimension for first embedding"
    )
