import os
import httpx
from typing import Optional
from pymilvus import MilvusClient
from pydantic import BaseModel, Field


class Filter:
    class Valves(BaseModel):
        milvus_uri: str = Field(
            default="http://standalone:19530", description="Milvus URI"
        )
        ollama_uri: str = Field(
            default="http://192.168.0.245:11434", description="Ollama API URI"
        )
        collection_name: str = Field(
            default="docs", description="Specific collection to query"
        )
        embedding_model: str = Field(
            default="nomic-embed-text", description="Model used for query embeddings"
        )
        top_k: int = Field(default=5, description="Number of chunks to retrieve")

    def __init__(self):
        self.valves = self.Valves()
        self.client = None

    async def get_embedding(self, text: str) -> list[float]:
        """Generates embedding for the user query via Ollama."""
        url = f"{self.valves.ollama_uri}/api/embed"
        payload = {"model": self.valves.embedding_model, "input": text}

        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
            return data["embeddings"][0]

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

        # 1. Start Status
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
            # 2. Setup Milvus Client
            if not self.client:
                self.client = MilvusClient(uri=self.valves.milvus_uri)

            # 3. Embed the User Query
            query_vector = await self.get_embedding(user_query)

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

            # 5. Process results and construct Augmented Prompt
            context_blocks = []
            for res in search_results[0]:
                text = res["entity"].get("text", "")
                source = res["entity"].get("source_url", "Unknown")
                context_blocks.append(f"--- SOURCE: {source} ---\n{text}")

            if context_blocks:
                context_string = "\n\n".join(context_blocks)

                # Instruction to the LLM
                rag_instruction = (
                    "You are a helpful assistant. Use the following pieces of retrieved context "
                    "to answer the user's question. If the context doesn't contain the answer, "
                    "use your general knowledge but mention that the specific data wasn't found.\n\n"
                    f"CONTEXT:\n{context_string}\n\n"
                    f"USER QUESTION: {user_query}"
                )

                # Replace the last message content with the augmented version
                body["messages"][-1]["content"] = rag_instruction
                status_msg = f"Injected {len(context_blocks)} chunks from Milvus."
            else:
                status_msg = "No relevant context found in Milvus."

            # 6. Final Status
            if __event_emitter__:
                await __event_emitter__(
                    {
                        "type": "status",
                        "data": {"description": status_msg, "done": True},
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
            print(f"RAG Error Details: {e}")

        return body

