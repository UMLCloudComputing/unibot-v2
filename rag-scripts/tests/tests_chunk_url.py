from concurrent.futures import ThreadPoolExecutor
import pytest
import asyncio
import aiohttp
import time
from asyncio import Queue
from queue import Queue as tsQueue
from mock_server.mock_docling import mock_docling
from src.add_data_utils import chunk_url, chunk_url_generator, chunk_url_sync
from unittest.mock import MagicMock

MAX_CONCURRENT_TASKS = 80


# Tests
@pytest.mark.asyncio
async def test_mock_docling_contract():
    """Verifies the mock server follows the expected Docling API protocol."""
    async with mock_docling() as base_url:
        async with aiohttp.ClientSession() as session:
            # 1. Test the Async Submission (POST)
            payload = {"sources": [{"url": "http://test.com", "kind": "http"}]}

            async with session.post(
                f"http://{base_url}/v1/chunk/hybrid/source/async", json=payload
            ) as resp:
                assert resp.status == 200
                data = await resp.json()
                assert "task_id" in data
                task_id = data["task_id"]

            # 2. Test the WebSocket Status (WS)
            ws_url = f"ws://{base_url}/v1/status/ws/{task_id}"
            async with session.ws_connect(ws_url) as ws:
                msg = await ws.receive()
                status_data = msg.json().get("task")
                # Ensure it uses the exact key your code expects
                assert status_data.get("task_status") == "success"

            # 3. Test the Results Fetch (GET)
            results_url = f"http://{base_url}/v1/result/{task_id}"
            async with session.get(results_url) as resp:
                assert resp.status == 200
                results = await resp.json()
                assert "chunks" in results
                assert len(results["chunks"]) > 0

            # 4. Test the Sync Submission (POST)
            async with session.post(
                f"http://{base_url}/v1/chunk/hybrid/source", json=payload
            ) as resp:
                assert resp.status == 200
                data = await resp.json()
                assert "chunks" in data, "Missing chunks key in response"
                assert len(data.get("chunks")) > 0, (
                    "Incorrect number of chunks in response"
                )
                assert data["chunks"][0]["text"], (
                    "Missing text key in individual chunk from response"
                )

            # 5. Test the task status poll (GET)
            async with session.get(
                f"http://{base_url}/v1/status/poll/{task_id}"
            ) as resp:
                assert resp.status == 200
                data = await resp.json()
                assert data["task_status"] == "success", (
                    "Invalid task status in response"
                )
                assert data["task_type"] == "chunk", "Invalid task type in response"
                assert int(data["task_id"]) == task_id, (
                    "task id does not match in response"
                )


@pytest.mark.asyncio
async def test_chunk_url_behavior_success():
    semaphore = asyncio.Semaphore(MAX_CONCURRENT_TASKS)
    async with mock_docling() as base_url:
        # Setup global-like objects
        test_url = "https://example.com/doc.pdf"
        chunk_queue = Queue()  # Asyncio Queue, not thread safe
        mock_pbar = MagicMock()

        async with aiohttp.ClientSession() as session:
            await chunk_url(
                session, test_url, base_url, chunk_queue, semaphore, mock_pbar
            )

    # Assertions
    assert chunk_queue.qsize() == 2, "Should have two chunks in queue"
    first_chunk = chunk_queue._queue[0]
    assert first_chunk["text"] == "Chunk 1 content"
    assert first_chunk["source_url"] == test_url, "Metadata annotation failed"
    assert mock_pbar.update.called, "Progress bar updates are not being called"
    assert mock_pbar.update.call_count == 1, (
        "Progress bar not updated to the correct count"
    )


@pytest.mark.asyncio
async def test_chunk_url_generator_behavior_success():
    semaphore = asyncio.Semaphore(MAX_CONCURRENT_TASKS)
    async with mock_docling() as base_url:
        # Setup global like objects
        test_url = "https://example.com/doc.pdf"
        chunk_queue = Queue()  # Asyncio Queue, not thread safe
        mock_pbar = MagicMock()

        async with aiohttp.ClientSession() as session:
            async for chunk in chunk_url_generator(
                session, test_url, base_url, semaphore, mock_pbar
            ):
                await chunk_queue.put(chunk)

    # Assertions
    assert chunk_queue.qsize() == 2, "Should have two chunks in queue"
    first_chunk = chunk_queue._queue[0]
    assert first_chunk["text"] == "Chunk 1 content"
    assert first_chunk["source_url"] == test_url, "Metadata annotation failed"
    assert mock_pbar.update.called, "Progress bar updates are not being called"
    assert mock_pbar.update.call_count == 1, (
        "Progress bar not updated to the correct count"
    )


@pytest.mark.asyncio
async def test_chunk_url_high_volume_throughput():
    semaphore = asyncio.Semaphore(MAX_CONCURRENT_TASKS)
    async with mock_docling() as base_url:
        # Setup Params
        NUM_URLS = 20000
        TIME_THRESHOLD_SECONDS = 60.0
        chunk_queue = Queue()  # Asyncio Queue, not thread safe
        mock_pbar = MagicMock()

        start_time = time.perf_counter()

        async with aiohttp.ClientSession() as session:
            tasks = [
                chunk_url(
                    session,
                    f"http://url-{i}.com",
                    base_url,
                    chunk_queue,
                    semaphore,
                    mock_pbar,
                )
                for i in range(NUM_URLS)
            ]

            _ = await asyncio.gather(*tasks)

    end_time = time.perf_counter()
    total_duration = end_time - start_time
    throughput = NUM_URLS / total_duration
    assert total_duration < TIME_THRESHOLD_SECONDS, (
        f"Throughput too low! {throughput:.2f} URL/s"
    )
    assert chunk_queue.qsize() == (NUM_URLS * 2), "Chunk count mismatch"
    assert mock_pbar.update.called, "Progress bar updates are not being called"
    assert mock_pbar.update.call_count == NUM_URLS, (
        "Progress bar not updated to the correct count"
    )


@pytest.mark.asyncio
async def test_chunk_url_generator_high_volume_throughput():
    semaphore = asyncio.Semaphore(MAX_CONCURRENT_TASKS)
    async with mock_docling() as base_url:
        # Setup Params
        NUM_URLS = 20000
        TIME_THRESHOLD_SECONDS = 60.0
        chunk_queue = Queue()  # Asyncio Queue, not thread safe
        mock_pbar = MagicMock()

        start_time = time.perf_counter()

        async with aiohttp.ClientSession() as session:

            async def consume_generator(url):
                async for chunk in chunk_url_generator(
                    session, url, base_url, semaphore, mock_pbar
                ):
                    await chunk_queue.put(chunk)

            tasks = [consume_generator(f"http://url-{i}.com") for i in range(NUM_URLS)]
            await asyncio.gather(*tasks)

    end_time = time.perf_counter()
    total_duration = end_time - start_time
    throughput = NUM_URLS / total_duration
    assert total_duration < TIME_THRESHOLD_SECONDS, (
        f"Throughput too low! {throughput:.2f} URL/s"
    )
    assert chunk_queue.qsize() == (NUM_URLS * 2), "Chunk count mismatch"
    assert mock_pbar.update.called, "Progress bar updates are not being called"
    assert mock_pbar.update.call_count == NUM_URLS, (
        "Progress bar not updated to the correct count"
    )


@pytest.mark.asyncio
async def test_chunk_url_sync_success():
    url_queue = tsQueue()
    chunk_queue = tsQueue()
    mock_pbar = MagicMock()
    NUM_URLS = 3
    for i in range(NUM_URLS):
        url_queue.put(f"http://example-{i}.com")

    async with mock_docling() as base_url:
        # Run in a thread to avoid blocking the main event loop
        loop = asyncio.get_running_loop()
        with ThreadPoolExecutor() as pool:
            await loop.run_in_executor(
                pool, chunk_url_sync, base_url, url_queue, chunk_queue, mock_pbar
            )

    assert chunk_queue.qsize() == NUM_URLS, "Incorrect number of chunks returned"
    assert mock_pbar.update.call_count == NUM_URLS, (
        "Progress bar has incorrect number of updates"
    )


@pytest.mark.asyncio
async def test_chunk_url_sync_high_volume_throughput():
    NUM_URLS = 20000
    NUM_THREADS = 5
    TIME_THRESHOLD_SECONDS = 60.0
    url_queue = tsQueue()
    chunk_queue = tsQueue()
    mock_pbar = MagicMock()
    for i in range(NUM_URLS):
        url_queue.put(f"http://example-{i}.com")

    async with mock_docling() as base_url:
        # Run in a thread to avoid blocking the main event loop
        loop = asyncio.get_running_loop()

        start_time = time.perf_counter()

        with ThreadPoolExecutor() as pool:
            tasks = [
                loop.run_in_executor(
                    pool, chunk_url_sync, base_url, url_queue, chunk_queue, mock_pbar
                )
                for _ in range(NUM_THREADS)
            ]

            await asyncio.gather(*tasks)

        end_time = time.perf_counter()

    total_duration = end_time - start_time
    throughput = NUM_URLS / total_duration
    assert total_duration < TIME_THRESHOLD_SECONDS, (
        f"Throughput too low! {throughput:.2f} URL/s"
    )
    assert chunk_queue.qsize() == NUM_URLS, "Chunk count mismatch"
    assert mock_pbar.update.called, "Progress bar updates are not being called"
    assert mock_pbar.update.call_count == NUM_URLS, (
        "Progress bar not updated to the correct count"
    )
