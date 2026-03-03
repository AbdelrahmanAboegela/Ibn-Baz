"""
routes/stats.py
Dashboard stats endpoint.
"""
import sqlite3

from fastapi import APIRouter

from api.models import DashboardStats

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from config import settings
from api.retriever import get_qdrant_client

router = APIRouter(prefix="/api", tags=["Stats"])


@router.get("/stats", response_model=DashboardStats)
async def get_stats():
    """Get dashboard statistics for all content types."""
    # Fatwas from Qdrant
    client = get_qdrant_client()
    try:
        info = client.get_collection(settings.qdrant_collection)
        total_fatwas = info.points_count
    except Exception:
        total_fatwas = 0

    # Other content from SQLite
    try:
        conn = sqlite3.connect(settings.content_db_path)
        articles = conn.execute("SELECT COUNT(*) FROM articles").fetchone()[0]
        books = conn.execute("SELECT COUNT(*) FROM books").fetchone()[0]
        speeches = conn.execute("SELECT COUNT(*) FROM speeches").fetchone()[0]
        discussions = conn.execute("SELECT COUNT(*) FROM discussions").fetchone()[0]
        conn.close()
    except Exception:
        articles = books = speeches = discussions = 0

    # Categories (approximate from Qdrant)
    try:
        from api.retriever import get_all_categories
        categories = await get_all_categories()
        total_categories = len(categories)
    except Exception:
        total_categories = 0

    return DashboardStats(
        total_fatwas=total_fatwas,
        total_articles=articles,
        total_books=books,
        total_speeches=speeches,
        total_discussions=discussions,
        total_categories=total_categories,
    )
