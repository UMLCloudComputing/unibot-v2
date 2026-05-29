"""title: Milvus RAG Filter Function
author: Gurpreet Singh (with help from Gemini)
date: 2026-03-13
version: 0.1
description: Integration with CI/CD managed Milvus Collection as a knowledge base.
requirements: pymilvus
"""

import os
import traceback
import httpx
from typing import Optional, List
from pymilvus import MilvusClient
from pydantic import BaseModel, Field


class Filter:
    class Valves(BaseModel):
        milvus_uri: str = Field(
            default="http://milvus-cluster-milvus.milvus-cluster.svc.cluster.local:19530",
            description="Milvus URI",
        )
        ollama_uri: str = Field(
            default="http://192.168.0.193:11434", description="Ollama API URI"
        )
        collection_name: str = Field(
            default="docs", description="Specific collection to query"
        )
        embedding_model: str = Field(
            default="nomic-embed-text:latest",
            description="Model used for query embeddings",
        )
        top_k: int = Field(default=5, description="Number of chunks to retrieve")

    def __init__(self):
        self.valves = self.Valves()
        self.client = None

    async def on_startup(self):
        print(f"Connecting to Milvus at {self.valves.MILVUS_URI}...")
        try:
            self.client = MilvusClient(uri=self.valves.milvus_uri)
            self.client.load_collection(self.valves.collection_name)
            print("✅ Successfully connected to Milvus")
        except Exception as e:
            print(f"❌ Failed to initialize Milvus: {e}")

    async def on_shutdown(self):
        try:
            if self.client:
                self.client.release_collection(self.valves.collection_name)
                self.client.close()
                print("✅ Cleaned up Milvus connections.")
        except Exception as e:
            print(f"❌ Error during shutdown: {e}")

    async def get_embedding(self, text: str) -> list[float]:
        """Generates embedding for the user query via Ollama."""
        url = f"{self.valves.ollama_uri}/api/embed"
        payload = {"model": self.valves.embedding_model, "input": text}

        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
            return data["embeddings"][0]

    # async def emit_citations(self, citations_data: List[dict], __emit_citations__: callable):
    #     if __event_emitter__:
    #         for item in citations_data:
    #             await __emit_citations__({
    #                 "type": "citation",
    #                 "data": {
    #                     "document": [item["text"]],
    #                     "metadata": [{"source": item["url"]}],
    #                     "source": {
    #                       "name": f"Source [{item['index']}]",
    #                       "url": item["url"]
    #                     }
    #                 }
    #             })

    async def inlet(
        self,
        body: dict,
        __event_emitter__: Optional[callable] = None,
        __user__: Optional[dict] = None,
    ) -> dict:
        messages = body.get("messages", [])
        if not messages:
            return body

        user_query = messages[-1]["content"]

        if __event_emitter__:
            await __event_emitter__(
                {
                    "type": "status",
                    "data": {
                        "description": "Generating query embedding...",
                        "done": False,
                    },
                }
            )

        try:
            query_vector = await self.get_embedding(user_query)

            self.client = MilvusClient(uri=self.valves.milvus_uri)
            self.client.load_collection(self.valves.collection_name)

            # 4. Search Milvus
            if __event_emitter__:
                await __event_emitter__(
                    {
                        "type": "status",
                        "data": {
                            "description": "Querying Milvus knowledge base...",
                            "done": False,
                        },
                    }
                )

            search_results = self.client.search(
                collection_name=self.valves.collection_name,
                data=[query_vector],
                limit=self.valves.top_k,
                output_fields=["text", "source_url"],
            )

            context_items = []
            citations_data = []
            for i, res in enumerate(search_results[0]):
                text = res["entity"].get("text", "")
                url = res["entity"].get("source_url", "Unknown")
                context_items.append(
                    f"--- SOURCE [{i}] ---\nURL: {url}\nCONTENT: {text}\n"
                )
                if __event_emitter__:
                    await __event_emitter__(
                        {
                            "type": "citation",
                            "data": {
                                "document": [text],
                                "metadata": [{"source": url}],
                                "source": {
                                    "name": f"Source [{i}]",
                                    "url": url,
                                },
                            },
                        }
                    )

                citations_data.append({"index": i, "text": text, "url": url})

            if context_items:
                context_string = "\n\n".join(context_items)

                optimized_prompt = (
                    # f"### CORE DIRECTIVES\n{system_prompt}\n\n"
                    "### REFERENCE CONTEXT\n"
                    f"{context_string}\n\n"
                    "### RAG INSTRUCTIONS\n"
                    "Answer the user query using the REFERENCE CONTEXT. Maintain a professional tone.\n"
                    "Adhere strictly to the CORE DIRECTIVES above.\n\n"
                    "### USER QUERY\n"
                    f"{user_query}"
                )
                body["messages"][-1]["content"] = optimized_prompt

            if __event_emitter__:
                await __event_emitter__(
                    {
                        "type": "status",
                        "data": {
                            "description": "RAG injection complete.",
                            "done": True,
                        },
                    }
                )
        except Exception as e:
            if __event_emitter__:
                await __event_emitter__(
                    {
                        "type": "status",
                        "data": {"description": f"RAG Error: {str(e)}", "done": True},
                    }
                )
            error_detail = traceback.format_exc()
            print(f"❌ Error Message: {e}")
            print(f"DEBUG TRACEBACK:\n{error_detail}")

        self.client.release_collection(self.valves.collection_name)
        self.client.close()
        return body

