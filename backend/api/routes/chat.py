"""
routes/chat.py
RAG chatbot endpoint with SSE streaming support.
"""
import json
import time

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from api.models import ChatRequest, ChatResponse
from api.rag_pipeline import run_rag_pipeline, run_rag_pipeline_stream

router = APIRouter(prefix="/api/chat", tags=["Chat"])


@router.post("", response_model=ChatResponse)
async def chat(req: ChatRequest):
    """RAG query → structured JSON response with citations."""
    response = await run_rag_pipeline(req.query, top_k=req.top_k)
    return response


@router.post("/stream")
async def chat_stream(req: ChatRequest):
    """RAG query → Server-Sent Events streaming response."""

    async def event_stream():
        # Send initial "thinking" event
        yield f"data: {json.dumps({'type': 'status', 'content': 'جاري البحث في الفتاوى...'}, ensure_ascii=False)}\n\n"

        try:
            # Stream events directly from the true streaming pipeline
            async for event in run_rag_pipeline_stream(req.query, top_k=req.top_k):
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

            # Done
            yield f"data: {json.dumps({'type': 'done'})}\n\n"

        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'content': str(e)}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
