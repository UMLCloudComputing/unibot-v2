import requests
import random
import aiohttp
import asyncio
from contextlib import asynccontextmanager
from ollama import AsyncClient
from aiohttp import web

class mock_ollama_async_client(AsyncClient):
    async def embed(self, model, input, **kwargs):
        """ Mimics v1/embed/{input} """
        inputs = input if isinstance(input, list) else [input]
        embeddings = [[0.01] * 768 for _ in inputs]
        return {"embeddings": embeddings, "model": model}
