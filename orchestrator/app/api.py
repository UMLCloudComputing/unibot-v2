import os
import logging
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional

from ai_stack import AutonomousStack, MCPServer
from langchain_core.messages import HumanMessage, AIMessage

MCP_SERVER_1 = os.getenv("MCP_SERVER_1", "http://localhost:8000/mcp")
MCP_SERVER_2 = os.getenv("MCP_SERVER_2", "http://localhost:8001/mcp")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "gpt-oss:latest")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL")

app = FastAPI(title="unibot-v2 orchestrator (RAG + Remote MCP)")

server_1 = MCP_SERVER_1.split(",")
mcp_server_1: MCPServer = {"name": server_1[0], "url": server_1[1], "api_key": ""}

server_2 = MCP_SERVER_2.split(",")
mcp_server_2: MCPServer = {"name": server_2[0], "url": server_2[1], "api_key": ""}

# Instantiate the refactored network configuration stack
ai_coordinator = AutonomousStack(
    mcp_servers=[mcp_server_1, mcp_server_2],
    ollama_base_url=OLLAMA_BASE_URL,
    ollama_model=OLLAMA_MODEL,
)


# Maintain public client API request schema contract
class ChatMessageSchema(BaseModel):
    role: str  # "user" or "assitant"
    content: str  # Actual text content string


class ChatRequest(BaseModel):
    message: str  # New incoming user query
    # Optional hsitory tracking
    history: Optional[List[ChatMessageSchema]] = []


@app.post("/v1/chat")
async def handle_chat_request(payload: ChatRequest):
    try:
        formatted_history = []
        for msg in payload.history:
            if msg.role == "user":
                formatted_history.append(HumanMessage(content=msg.content))
            elif msg.role == "assistant":
                formatted_history.append(AIMessage(content=msg.content))

        output_text = await ai_coordinator.chat(
            user_message=payload.message, chat_history=formatted_history
        )
        return {"status": "success", "response": output_text}

    except Exception as e:
        logging.error(f"Error handling agent pipeline call: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health_check():
    """Health check endpoint for Kubernetes liveness/readiness probes."""
    try:
        # Check if the AI coordinator is initialized
        if ai_coordinator is None:
            return {"status": "unhealthy", "reason": "AI coordinator not initialized"}

        # Basic health check - we could add more sophisticated checks here
        # For now, if the app is running and this endpoint responds, consider it healthy
        return {"status": "healthy"}
    except Exception as e:
        return {"status": "unhealthy", "reason": str(e)}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8001)
