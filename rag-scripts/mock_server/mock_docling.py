import requests
import random
import aiohttp
import asyncio
from contextlib import asynccontextmanager
from aiohttp import web


# Fake Docling Server
async def handle_async_chunk_request(request):
    """Mimics /v1/chunk/hybrid/source/async"""
    data = await request.json()
    # Check request structure
    if "sources" in data and data["sources"][0]["kind"] == "http":
        return web.json_response(
            {"task_id": random.randint(1000, 9999)}
        )  # Match task_id with what's below
    return web.json_response({"error": "Invalid payload"}, status=402)


async def handle_ws_status(request):
    """Mimics v1/status/ws/{task_id}"""
    ws = web.WebSocketResponse()
    await ws.prepare(request)

    # Simulate processing time
    await asyncio.sleep(0.1)

    # Send completion signal, task_id must match above
    await ws.send_json(
        {
            "message": "update",
            "task": {"task_id": "...", "task_status": "success", "task_type": "..."},
            "error": "",
        }
    )
    await ws.close()
    return ws


async def handle_chunk_request(request):
    """Mimics /v1/chunk/hybrid/source"""
    data = await request.json()
    response = []
    if "sources" in data and data["sources"][0]["kind"] == "http":
        for item in data["sources"]:
            response.append(
                {
                    "filename": item["url"],
                    "chunk_index": 0,
                    "text": "dummy text",
                    "raw_text": None,
                    "num_tokens": 10,
                    "headings": ["dummy heading"],
                    "captions": None,
                    "doc_items": ["#/texts/1", "#/texts/2"],
                    "page_numbers": [],
                    "metadata": {
                        "origin": {
                            "mimetype": "text/html",
                            "binary_hash": random.randint(1000, 9999),
                            "filename": item["url"],
                            "uri": None,
                        }
                    },
                }
            )
        return web.json_response({"chunks": response})
    else:
        return web.json_response({"error": "Invalid payload"}, status=402)


async def handle_task_status_poll(request):
    """Mimics v1/status/poll/{task_id}"""
    task_id = request.match_info.get("task_id")
    if task_id:
        return web.json_response(
            {"task_id": task_id, "task_type": "chunk", "task_status": "success"},
            status=200,
        )
    else:
        return web.json_response({"error": "Invalid payload"}, status=402)


async def handle_get_results(request):
    """Mimics v1/result/{task_id}"""
    return web.json_response(
        {"chunks": [{"text": "Chunk 1 content"}, {"text": "Chunk 2 content"}]},
        status=200,
    )


@asynccontextmanager
async def mock_docling():
    app = web.Application()
    app.router.add_post("/v1/chunk/hybrid/source/async", handle_async_chunk_request)
    app.router.add_get("/v1/status/ws/{task_id}", handle_ws_status)
    app.router.add_get("/v1/result/{task_id}", handle_get_results)
    app.router.add_post("/v1/chunk/hybrid/source", handle_chunk_request)
    app.router.add_get("/v1/status/poll/{task_id}", handle_task_status_poll)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "127.0.0.1", 0)
    await site.start()

    port = site._server.sockets[0].getsockname()[1]
    try:
        yield f"127.0.0.1:{port}"
    finally:
        await runner.cleanup()
