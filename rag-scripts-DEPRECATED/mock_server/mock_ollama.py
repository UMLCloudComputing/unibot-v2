from contextlib import asynccontextmanager
import random
from ollama import Client
from aiohttp import web


class mock_ollama_client(Client):
    def embed(self, model, input, **kwargs):
        """Mimics v1/embed/{input}"""
        inputs = input if isinstance(input, list) else [input]
        embeddings = [[0.01] * 768 for _ in inputs]
        return {"embeddings": embeddings, "model": model}


async def handle_embed(request):
    data = await request.json()
    inputs = data.get("input", [])
    if isinstance(inputs, str):
        inputs = [inputs]

    embeddings = [[0.1, 0.2, 0.3] for _ in inputs]

    return web.json_response(
        {
            "model": data.get("model", "unknown"),
            "embeddings": embeddings,
            "total_duration": 100,
            "load_duration": 50,
            "prompt_eval_count": 10,
        }
    )


@asynccontextmanager
async def mock_ollama_server():
    app = web.Application()
    app.router.add_post("/api/embed", handle_embed)
    app.router.add_post("/v1/embed", handle_embed)
    runner = web.AppRunner(app)

    await runner.setup()
    site = web.TCPSite(runner, "127.0.0.1", 0)
    await site.start()

    port = site._server.sockets[0].getsockname()[1]
    try:
        yield f"127.0.0.1:{port}"
    finally:
        await runner.cleanup()
