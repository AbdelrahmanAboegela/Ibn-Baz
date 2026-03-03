"""
routes/chat.py
RAG chatbot endpoint with SSE streaming support.
"""
import json
import time

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from api.models import ChatRequest, ChatResponse
from api.rag_pipeline import run_rag_pipeline

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
        yield f"data: {json.dumps({'type': 'status', 'content': 'جاري البحث...'}, ensure_ascii=False)}\n\n"

        try:
            # Run the full pipeline
            response = await run_rag_pipeline(req.query, top_k=req.top_k)

            # Stream the answer in chunks for a natural feel
            answer = response.answer
            chunk_size = 50
            for i in range(0, len(answer), chunk_size):
                chunk = answer[i:i + chunk_size]
                yield f"data: {json.dumps({'type': 'chunk', 'content': chunk}, ensure_ascii=False)}\n\n"

            # Send metadata
            yield f"data: {json.dumps({'type': 'metadata', 'content': response.model_dump()}, ensure_ascii=False)}\n\n"

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
