"""
retriever.py
Qdrant hybrid search: dense (e5-base) retrieval + payload filtering.
Handles fatwa lookup, search, and graph expansion via related_ids.
"""
import sys
from pathlib import Path
from typing import Optional

from qdrant_client import QdrantClient
from qdrant_client.models import (
    FieldCondition,
    Filter,
    MatchValue,
)
from sentence_transformers import SentenceTransformer

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import settings

# Module-level singletons (initialized lazily)
_client: Optional[QdrantClient] = None
_embed_model: Optional[SentenceTransformer] = None


def get_qdrant_client() -> QdrantClient:
    """Get or create Qdrant client (local file mode)."""
    global _client
    if _client is None:
        _client = QdrantClient(path=settings.qdrant_path)
    return _client


def get_embed_model() -> SentenceTransformer:
    """Get or create embedding model (cached from HF)."""
    global _embed_model
    if _embed_model is None:
        _embed_model = SentenceTransformer(
            settings.embedding_model,
            cache_folder=settings.transformers_cache,
        )
    return _embed_model


def embed_query(query: str) -> list[float]:
    """Embed a user query using e5 format."""
    model = get_embed_model()
    # multilingual-e5 expects "query: " prefix for queries
    embedding = model.encode(f"query: {query}")
    return embedding.tolist()


async def search_fatwas(
    query: str,
    top_k: int = 5,
    category: Optional[str] = None,
) -> list[dict]:
    """
    Hybrid search: dense vector similarity + optional category filter.
    Returns list of fatwa payloads with scores.
    """
    client = get_qdrant_client()
    query_vector = embed_query(query)

    # Build filter
    search_filter = None
    if category:
        search_filter = Filter(
            must=[
                FieldCondition(
                    key="categories",
                    match=MatchValue(value=category),
                )
            ]
        )

    results = client.query_points(
        collection_name=settings.qdrant_collection,
        query=query_vector,
        using="dense",
        query_filter=search_filter,
        limit=top_k,
        with_payload=True,
    )

    fatwas = []
    for hit in results.points:
        payload = hit.payload or {}
        payload["_score"] = hit.score
        fatwas.append(payload)

    return fatwas


async def get_fatwa_by_id(fatwa_id: int) -> Optional[dict]:
    """Fetch a single fatwa by ID from Qdrant."""
    client = get_qdrant_client()
    try:
        points = client.retrieve(
            collection_name=settings.qdrant_collection,
            ids=[fatwa_id],
            with_payload=True,
        )
        if points:
            return points[0].payload
    except Exception:
        pass
    return None


async def get_fatwas_by_ids(fatwa_ids: list[int]) -> list[dict]:
    """Fetch multiple fatwas by their IDs."""
    if not fatwa_ids:
        return []

    client = get_qdrant_client()
    try:
        points = client.retrieve(
            collection_name=settings.qdrant_collection,
            ids=fatwa_ids,
            with_payload=True,
        )
        return [p.payload for p in points if p.payload]
    except Exception:
        return []


async def get_related_fatwas(fatwa_id: int) -> list[dict]:
    """Get related fatwas via the related_ids field (graph expansion)."""
    fatwa = await get_fatwa_by_id(fatwa_id)
    if not fatwa:
        return []

    related_ids = fatwa.get("related_ids", [])
    if not related_ids:
        return []

    related = await get_fatwas_by_ids(related_ids)
    return [
        {"fatwa_id": r["fatwa_id"], "title": r.get("title", "")}
        for r in related
    ]


async def scroll_fatwas(
    page: int = 1,
    per_page: int = 20,
    category: Optional[str] = None,
) -> tuple[list[dict], int]:
    """
    Paginated fatwa listing with optional category filter.
    Returns (items, total_count).
    """
    client = get_qdrant_client()

    # Build filter
    scroll_filter = None
    if category:
        scroll_filter = Filter(
            must=[
                FieldCondition(
                    key="categories",
                    match=MatchValue(value=category),
                )
            ]
        )

    # Get total count
    collection_info = client.get_collection(settings.qdrant_collection)
    total = collection_info.points_count

    # Scroll with offset
    offset = (page - 1) * per_page
    points, _ = client.scroll(
        collection_name=settings.qdrant_collection,
        scroll_filter=scroll_filter,
        limit=per_page,
        offset=offset if offset > 0 else None,
        with_payload=True,
    )

    items = [p.payload for p in points if p.payload]
    return items, total


async def get_all_categories() -> list[str]:
    """Get distinct categories from all fatwas."""
    client = get_qdrant_client()
    categories = set()

    # Scroll through all points to collect categories
    offset = None
    while True:
        points, next_offset = client.scroll(
            collection_name=settings.qdrant_collection,
            limit=1000,
            offset=offset,
            with_payload=["categories"],
        )
        for p in points:
            if p.payload and "categories" in p.payload:
                for cat in p.payload["categories"]:
                    categories.add(cat)

        if next_offset is None:
            break
        offset = next_offset

    return sorted(categories)
