import os
import logging
from pydantic import BaseModel
from typing import List, Optional

# Prometheus
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

# FastAPI
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import PlainTextResponse

from ai_stack import AutonomousStack, REQUEST_COUNT
from langchain_core.messages import HumanMessage, AIMessage

MODEL_NAME = os.getenv("MODEL_NAME", "gemma4:12b")
MODEL_ENDPOINT_BASE_URL = os.getenv("MODEL_ENDPOINT_BASE_URL")

app = FastAPI(title="unibot-v2 orchestrator")


# Instantiate the refactored network configuration stack
ai_coordinator = AutonomousStack(
    model_endpoint_base_url=MODEL_ENDPOINT_BASE_URL,
    model_name=MODEL_NAME,
)


# Maintain public client API request schema contract
class ChatMessageSchema(BaseModel):
    role: str  # "user" or "assistant"
    content: str  # Actual text content string


class ChatRequest(BaseModel):
    message: str  # New incoming user query
    # Optional history tracking
    history: Optional[List[ChatMessageSchema]] = []


@app.middleware("http")
async def monitor_requests(request: Request, call_next):
    endpoint = request.url.path

    # Do not track Prometheus scraping activity
    if endpoint == "/metrics":
        return await call_next(request)

    try:
        response = await call_next(request)
        status_code = response.status_code
        return response
    except Exception as e:
        status_code = 500
        raise e
    finally:
        # Increment total counter dynamically per endpoint and HTTP status
        REQUEST_COUNT.labels(endpoint=endpoint, status_code=status_code).inc()


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
        # Extract content from AIMessage and format response as expected by client
        response_content = output_text.content if hasattr(output_text, 'content') else str(output_text)
        return {"status": "success", "response": {"content": response_content}}

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


@app.get("/metrics", response_class=PlainTextResponse)
async def metrics():
    """
    Exposes all internal metrics to Prometheus scraping agents
    """
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8001)
