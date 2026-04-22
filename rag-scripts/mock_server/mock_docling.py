import requests 
import random
import aiohttp
import asyncio
from contextlib import asynccontextmanager
from aiohttp import web

# Fake Docling Server
async def handle_chunk_request(request):
  """ Mimics /v1/chunk/hybrid/source/async """
  data = await request.json()
  # Check request structure
  if "sources" in data and data["sources"][0]["kind"] == "http":
    return web.json_response({"task_id": random.randint(1000,9999)}) # Match task_id with what's below
  return web.json_response({"error": "Invalid payload"}, status=400)

async def handle_ws_status(request):
  """ Mimics v1/status/ws/{task_id} """
  ws = web.WebSocketResponse()
  await ws.prepare(request)

  # Simulate processing time
  await asyncio.sleep(0.1)
  
  # Send completion signal, task_id must match above
  await ws.send_json({"message": "update", "task": {"task_id": "...", "task_status": "success", "task_type": "..."}, "error": ""})
  await ws.close()
  return ws

async def handle_get_results(request):
  """ Mimics v1/result/{task_id} """
  return web.json_response({
    "chunks": [
      {"text": "Chunk 1 content"},
      {"text": "Chunk 2 content"}
    ]
  })

@asynccontextmanager
async def mock_docling():
  app = web.Application()
  app.router.add_post("/v1/chunk/hybrid/source/async", handle_chunk_request)
  app.router.add_get("/v1/status/ws/{task_id}", handle_ws_status)
  app.router.add_get("/v1/result/{task_id}", handle_get_results)

  runner = web.AppRunner(app)
  await runner.setup()
  site = web.TCPSite(runner, '127.0.0.1', 0)
  await site.start()

  port = site._server.sockets[0].getsockname()[1]
  try:
    yield f"127.0.0.1:{port}"
  finally:
    await runner.cleanup()
