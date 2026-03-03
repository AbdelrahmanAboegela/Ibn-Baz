"""
routes/fatwas.py
Fatwa endpoints: list, search, detail, related.
"""
import math
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from api.models import FatwaBrief, FatwaFull, PaginatedResponse, QuranCitation, RelatedFatwa
from api.retriever import (
    get_all_categories,
    get_fatwa_by_id,
    get_related_fatwas,
    scroll_fatwas,
    search_fatwas,
)

router = APIRouter(prefix="/api/fatwas", tags=["Fatwas"])


@router.get("", response_model=PaginatedResponse)
async def list_fatwas(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    category: Optional[str] = None,
    search: Optional[str] = None,
):
    """List fatwas with pagination, optional category filter or search."""
    if search:
        # Use vector search
        results = await search_fatwas(search, top_k=per_page, category=category)
        items = [
            FatwaBrief(
                fatwa_id=r["fatwa_id"],
                title=r.get("title", ""),
                question=r.get("question", ""),
                answer_preview=r.get("answer", "")[:300],
                categories=r.get("categories", []),
                source_ref=r.get("source_ref", ""),
                has_audio=bool(r.get("audio_url")),
            ).model_dump()
            for r in results
        ]
        return PaginatedResponse(
            items=items,
            total=len(items),
            page=1,
            per_page=per_page,
            total_pages=1,
        )

    # Paginated scroll
    raw_items, total = await scroll_fatwas(page, per_page, category)
    items = [
        FatwaBrief(
            fatwa_id=r["fatwa_id"],
            title=r.get("title", ""),
            question=r.get("question", ""),
            answer_preview=r.get("answer", "")[:300],
            categories=r.get("categories", []),
            source_ref=r.get("source_ref", ""),
            has_audio=bool(r.get("audio_url")),
        ).model_dump()
        for r in raw_items
    ]
    return PaginatedResponse(
        items=items,
        total=total,
        page=page,
        per_page=per_page,
        total_pages=math.ceil(total / per_page) if total > 0 else 0,
    )


@router.get("/categories", response_model=list[str])
async def list_categories():
    """Get all distinct fatwa categories."""
    return await get_all_categories()


@router.get("/{fatwa_id}", response_model=FatwaFull)
async def get_fatwa(fatwa_id: int):
    """Get full fatwa detail by ID."""
    fatwa = await get_fatwa_by_id(fatwa_id)
    if not fatwa:
        raise HTTPException(status_code=404, detail="فتوى غير موجودة")

    return FatwaFull(
        fatwa_id=fatwa["fatwa_id"],
        title=fatwa.get("title", ""),
        question=fatwa.get("question", ""),
        answer=fatwa.get("answer", ""),
        answer_direct=fatwa.get("answer_direct", ""),
        source_ref=fatwa.get("source_ref", ""),
        url=fatwa.get("url", ""),
        categories=fatwa.get("categories", []),
        related_ids=fatwa.get("related_ids", []),
        audio_url=fatwa.get("audio_url", ""),
        quran_citations=[
            QuranCitation(**c) for c in fatwa.get("quran_citations", [])
        ],
    )


@router.get("/{fatwa_id}/related", response_model=list[RelatedFatwa])
async def get_fatwa_related(fatwa_id: int):
    """Get related fatwas for a given fatwa."""
    related = await get_related_fatwas(fatwa_id)
    return [RelatedFatwa(**r) for r in related]
