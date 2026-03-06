"""
rag_pipeline.py
Orchestrates the full RAG flow: Query → Retrieve → Expand Graph → Assemble → Generate.
"""
import time

from typing import AsyncGenerator
from api.retriever import search_fatwas, get_related_fatwas, get_fatwas_by_ids
from api.generator import generate, generate_stream, RetrievalContext
from api.models import (
    ChatResponse,
    CitedFatwa,
    QuranCitation,
    RAGResponse,
    RelatedFatwa,
)


async def run_rag_pipeline(query: str, top_k: int = 5) -> ChatResponse:
    """
    Full RAG pipeline:
    1. Retrieve top-k fatwas from Qdrant (dense search)
    2. Expand graph: fetch related fatwa titles via related_ids
    3. Collect Quran citations from retrieved fatwas
    4. Assemble context and run PydanticAI generator
    5. Build structured ChatResponse
    """
    start_time = time.time()

    # ── Step 1: Retrieve ──
    retrieved = await search_fatwas(query, top_k=top_k)

    if not retrieved:
        return ChatResponse(
            answer="لم أجد فتاوى مرتبطة بسؤالك. يرجى إعادة صياغة السؤال.",
            confidence=0.0,
            query_time_ms=(time.time() - start_time) * 1000,
        )

    # ── Step 2: Graph expansion ──
    related_titles = []
    all_related_ids = set()
    for fatwa in retrieved:
        for rid in fatwa.get("related_ids", []):
            all_related_ids.add(rid)

    # Exclude already-retrieved IDs
    retrieved_ids = {f["fatwa_id"] for f in retrieved}
    expand_ids = list(all_related_ids - retrieved_ids)[:10]

    if expand_ids:
        related_fatwas = await get_fatwas_by_ids(expand_ids)
        related_titles = [r.get("title", "") for r in related_fatwas if r.get("title")]

    # ── Step 3: Collect Quran citations ──
    quran_citations = []
    seen_refs = set()
    for fatwa in retrieved:
        for citation in fatwa.get("quran_citations", []):
            ref = citation.get("reference", "")
            if ref and ref not in seen_refs:
                seen_refs.add(ref)
                quran_citations.append(citation)

    # ── Step 4: Assemble context and generate ──
    ctx = RetrievalContext(
        user_query=query,
        primary_fatwas=retrieved,
        related_titles=related_titles,
        quran_citations=quran_citations,
    )

    try:
        rag_response: RAGResponse = await generate(ctx)
    except Exception as e:
        # Fallback: return best retrieved fatwa as-is
        best = retrieved[0]
        return ChatResponse(
            answer=f"خطأ في التوليد. إليك أقرب فتوى:\n\n{best.get('answer', '')[:2000]}",
            confidence=0.3,
            cited_fatwas=[
                CitedFatwa(
                    fatwa_id=best["fatwa_id"],
                    title=best.get("title", ""),
                    source_ref=best.get("source_ref", ""),
                    url=best.get("url", ""),
                    relevance_score=best.get("_score", 0.0),
                )
            ],
            query_time_ms=(time.time() - start_time) * 1000,
        )

    # ── Step 5: Build response ──
    cited_fatwas = []
    for fatwa in retrieved:
        fid = fatwa["fatwa_id"]
        cited_fatwas.append(
            CitedFatwa(
                fatwa_id=fid,
                title=fatwa.get("title", ""),
                source_ref=fatwa.get("source_ref", ""),
                url=fatwa.get("url", ""),
                relevance_score=fatwa.get("_score", 0.0),
            )
        )

    quran_models = [QuranCitation(**c) for c in quran_citations]

    related_models = [
        RelatedFatwa(fatwa_id=rid, title=title)
        for rid, title in zip(expand_ids, related_titles)
        if title
    ]

    return ChatResponse(
        answer=rag_response.answer,
        confidence=rag_response.confidence,
        cited_fatwas=cited_fatwas,
        quran_citations=quran_models,
        related_fatwas=related_models,
        query_time_ms=(time.time() - start_time) * 1000,
    )


async def run_rag_pipeline_stream(query: str, top_k: int = 5) -> AsyncGenerator[dict, None]:
    """
    Streaming RAG pipeline:
    Yields chunks of text in real-time, then yields metadata at the end.
    """
    start_time = time.time()

    # Step 1: Retrieve
    retrieved = await search_fatwas(query, top_k=top_k)

    if not retrieved:
        yield {
            "type": "metadata",
            "content": ChatResponse(
                answer="لم أجد فتاوى مرتبطة بسؤالك. يرجى إعادة صياغة السؤال.",
                confidence=0.0,
                query_time_ms=(time.time() - start_time) * 1000,
            ).model_dump()
        }
        return

    # Step 2: Graph expansion
    related_titles = []
    all_related_ids = set()
    for fatwa in retrieved:
        for rid in fatwa.get("related_ids", []):
            all_related_ids.add(rid)

    retrieved_ids = {f["fatwa_id"] for f in retrieved}
    expand_ids = list(all_related_ids - retrieved_ids)[:10]

    if expand_ids:
        related_fatwas = await get_fatwas_by_ids(expand_ids)
        related_titles = [r.get("title", "") for r in related_fatwas if r.get("title")]

    # Step 3: Collect Quran citations
    quran_citations = []
    seen_refs = set()
    for fatwa in retrieved:
        for citation in fatwa.get("quran_citations", []):
            ref = citation.get("reference", "")
            if ref and ref not in seen_refs:
                seen_refs.add(ref)
                quran_citations.append(citation)

    # Step 4: Assemble context
    ctx = RetrievalContext(
        user_query=query,
        primary_fatwas=retrieved,
        related_titles=related_titles,
        quran_citations=quran_citations,
    )

    full_answer = ""
    try:
        async for chunk in generate_stream(ctx):
            if chunk:
                full_answer += chunk
                yield {"type": "chunk", "content": chunk}
    except Exception as e:
        yield {"type": "error", "content": str(e)}
        return

    # Optional: sanitize full answer 
    from api.generator import _sanitize
    full_answer = _sanitize(full_answer)

    # Step 5: Build metadata response
    cited_fatwas = []
    for fatwa in retrieved:
        fid = fatwa["fatwa_id"]
        cited_fatwas.append(
            CitedFatwa(
                fatwa_id=fid,
                title=fatwa.get("title", ""),
                source_ref=fatwa.get("source_ref", ""),
                url=fatwa.get("url", ""),
                relevance_score=fatwa.get("_score", 0.0),
            )
        )

    quran_models = [QuranCitation(**c) for c in quran_citations]

    related_models = [
        RelatedFatwa(fatwa_id=rid, title=title)
        for rid, title in zip(expand_ids, related_titles)
        if title
    ]

    top_score = ctx.primary_fatwas[0].get("_score", 0.7) if ctx.primary_fatwas else 0.5
    confidence = min(round(float(top_score), 2), 1.0)

    response = ChatResponse(
        answer=full_answer,
        confidence=confidence,
        cited_fatwas=cited_fatwas,
        quran_citations=quran_models,
        related_fatwas=related_models,
        query_time_ms=(time.time() - start_time) * 1000,
    )

    yield {"type": "metadata", "content": response.model_dump()}
