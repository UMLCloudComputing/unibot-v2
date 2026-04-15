import pytest
import asyncio
import aiohttp
import time
from queue import Queue
from mock_server import mock_docling
from src import chunk_url, chunk_url_generator
from unittest.mock import MagicMock

# Tests
@pytest.mark.asyncio
async def test_mock_docling_contract():
  """Verifies the mock server follows the expected Docling API protocol."""
  async with mock_docling() as base_url:
    async with aiohttp.ClientSession() as session:
        
      # 1. Test the Async Submission (POST)
      submit_url = f"http://{base_url}/v1/chunk/hybrid/source/async"
      payload = {"sources": [{"url": "http://test.com", "kind": "http"}]}
      
      async with session.post(submit_url, json=payload) as resp:
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

@pytest.mark.asyncio
async def test_chunk_url_behavior_success():
  async with mock_docling() as base_url:
    # Setup global-like objects
    test_url = "https://example.com/doc.pdf"
    task_registry = {}
    chunk_queue = Queue()
    mock_pbar = MagicMock()

    async with aiohttp.ClientSession() as session:
      await chunk_url(session, test_url, task_registry, base_url, chunk_queue, mock_pbar)

  # Assertions
  assert chunk_queue.qsize() == 2, "Should have two chunks in queue"
  first_chunk = chunk_queue.queue[0]
  assert first_chunk["text"] == "Chunk 1 content"
  assert first_chunk["source_url"] == test_url, "Metadata annotation failed"
  assert len(task_registry) == 0, "Registry was not cleaned up"
  assert mock_pbar.update.called, "Progress bar updates are not being called"
  assert mock_pbar.update.call_count == 1,  "Progress bar not updated to the correct count"

@pytest.mark.asyncio
async def test_chunk_url_generator_behavior_success():
  async with mock_docling() as base_url:
    # Setup global like objects
    test_url = "https://exmaple.com/doc.pdf"
    chunk_queue = Queue()
    task_registry = {}
    mock_pbar = MagicMock()

    async with aiohttp.ClientSession() as session:
      async for chunk in chunk_url_generator(session, test_url, task_registry, base_url, mock_pbar):
        chunk_queue.put(chunk)

  # Assertions
  assert chunk_queue.qsize() == 2, "Should have two chunks in queue"
  first_chunk = chunk_queue.queue[0]
  assert first_chunk["text"] == "Chunk 1 content"
  assert first_chunk["source_url"] == test_url, "Metadata annotation failed"
  assert len(task_registry) == 0, "Registry was not cleaned up"
  assert mock_pbar.update.called, "Progress bar updates are not being called"
  assert mock_pbar.update.call_count == 1,  "Progress bar not updated to the correct count"

@pytest.mark.asyncio
async def test_chunk_url_high_volume_throughput():
  async with mock_docling() as base_url:
    # Setup Params
    NUM_URLS = 20000
    TIME_THRESHOLD_SECONDS = 60.0
    task_registry = {}
    chunk_queue = Queue()
    mock_pbar = MagicMock()
  
    start_time = time.perf_counter()
   
    async with aiohttp.ClientSession() as session:
      tasks = [chunk_url(session, f"http://url-{i}.com", base_url, task_registry, chunk_queue, False, mock_pbar) for i in range(NUM_URLS)]

      await asyncio.gather(*tasks)

  end_time = time.perf_counter()
  total_duration = end_time - start_time
  throughput = NUM_URLS / total_duration
  assert total_duration < TIME_THRESHOLD_SECONDS, f"Throughput too low! {throughput:.2f} URL/s"
  assert chunk_queue.qsize() == (NUM_URLS * 2), "Chunk count mismatch"
  assert len(task_registry) == 0, "Registry was not cleaned up"
  assert mock_pbar.update.called, "Progress bar updates are not being called"
  assert mock_pbar.update.call_count == NUM_URLS,  "Progress bar not updated to the correct count"
@pytest.mark.asyncio
async def test_chunk_url_generator_high_volume_throughput():
  async with mock_docling() as base_url:
    # Setup Params
    NUM_URLS = 20000
    TIME_THRESHOLD_SECONDS = 60.0
    task_registry = {}
    chunk_queue = Queue()
    mock_pbar = MagicMock()
  
    start_time = time.perf_counter()
   
    async with aiohttp.ClientSession() as session:
      async def consume_generator(url):
        async for chunk in chunk_url_generator(session, url, task_registry, base_url, mock_pbar):
          chunk_queue.put(chunk)
      tasks = [consume_generator(f"http://url-{i}.com") for i in range(NUM_URLS)]
      await asyncio.gather(*tasks)

  end_time = time.perf_counter()
  total_duration = end_time - start_time
  throughput = NUM_URLS / total_duration
  assert total_duration < TIME_THRESHOLD_SECONDS, f"Throughput too low! {throughput:.2f} URL/s"
  assert chunk_queue.qsize() == (NUM_URLS * 2), "Chunk count mismatch"
  assert len(task_registry) == 0, "Registry was not cleaned up"
  assert mock_pbar.update.called, "Progress bar updates are not being called"
  assert mock_pbar.update.call_count == NUM_URLS,  "Progress bar not updated to the correct count"





