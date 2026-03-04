"""
routes/content.py
Non-fatwa content endpoints: articles, books, speeches, discussions.
All served from SQLite.
"""
import json
import math
import sqlite3
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from api.models import (
    ArticleBrief,
    BookItem,
    DiscussionBrief,
    PaginatedResponse,
    SpeechBrief,
)

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from config import settings

router = APIRouter(prefix="/api", tags=["Content"])


def get_db() -> sqlite3.Connection:
    """Open SQLite with WAL mode for fast concurrent reads."""
    conn = sqlite3.connect(str(settings.content_db_path), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    # WAL mode: much faster concurrent reads, no blocking writes
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA cache_size=10000")   # ~40 MB page cache
    conn.execute("PRAGMA temp_store=MEMORY")
    return conn


# ──────────────────────────────── Articles ────────────────────────────────

@router.get("/articles", response_model=PaginatedResponse)
async def list_articles(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    category: Optional[str] = None,
):
    conn = get_db()
    offset = (page - 1) * per_page

    if category:
        rows = conn.execute(
            "SELECT * FROM articles WHERE categories LIKE ? ORDER BY id DESC LIMIT ? OFFSET ?",
            (f'%{category}%', per_page, offset),
        ).fetchall()
        total = conn.execute(
            "SELECT COUNT(*) FROM articles WHERE categories LIKE ?",
            (f'%{category}%',),
        ).fetchone()[0]
    else:
        rows = conn.execute(
            "SELECT * FROM articles ORDER BY id DESC LIMIT ? OFFSET ?",
            (per_page, offset),
        ).fetchall()
        total = conn.execute("SELECT COUNT(*) FROM articles").fetchone()[0]

    conn.close()

    items = [
        ArticleBrief(
            id=r["id"],
            title=r["title"] or "",
            text_preview=(r["text"] or "")[:300],
            categories=json.loads(r["categories"]) if r["categories"] else [],
            date=r["date"] or "",
            source_ref=r["source_ref"] or "",
        ).model_dump()
        for r in rows
    ]

    return PaginatedResponse(
        items=items,
        total=total,
        page=page,
        per_page=per_page,
        total_pages=math.ceil(total / per_page) if total > 0 else 0,
    )


# ──────────────────────────────── Books ────────────────────────────────

@router.get("/books", response_model=list[BookItem])
async def list_books():
    conn = get_db()
    rows = conn.execute("SELECT * FROM books ORDER BY id").fetchall()
    conn.close()

    return [
        BookItem(
            id=r["id"],
            title=r["title"] or "",
            url=r["url"] or "",
            pdf_url=r["pdf_url"] or "",
        )
        for r in rows
    ]


# ──────────────────────────────── Speeches ────────────────────────────────

@router.get("/speeches", response_model=PaginatedResponse)
async def list_speeches(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
):
    conn = get_db()
    offset = (page - 1) * per_page

    rows = conn.execute(
        "SELECT * FROM speeches ORDER BY id DESC LIMIT ? OFFSET ?",
        (per_page, offset),
    ).fetchall()
    total = conn.execute("SELECT COUNT(*) FROM speeches").fetchone()[0]
    conn.close()

    items = [
        SpeechBrief(
            id=r["id"],
            title=r["title"] or "",
            text_preview=(r["text"] or "")[:300],
            categories=json.loads(r["categories"]) if r["categories"] else [],
            date=r["date"] or "",
        ).model_dump()
        for r in rows
    ]

    return PaginatedResponse(
        items=items,
        total=total,
        page=page,
        per_page=per_page,
        total_pages=math.ceil(total / per_page) if total > 0 else 0,
    )


# ──────────────────────────────── Discussions ────────────────────────────────

@router.get("/discussions", response_model=PaginatedResponse)
async def list_discussions(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
):
    conn = get_db()
    offset = (page - 1) * per_page

    rows = conn.execute(
        "SELECT * FROM discussions ORDER BY id DESC LIMIT ? OFFSET ?",
        (per_page, offset),
    ).fetchall()
    total = conn.execute("SELECT COUNT(*) FROM discussions").fetchone()[0]
    conn.close()

    items = [
        DiscussionBrief(
            id=r["id"],
            title=r["title"] or "",
            text_preview=(r["text"] or "")[:300],
            categories=json.loads(r["categories"]) if r["categories"] else [],
        ).model_dump()
        for r in rows
    ]

    return PaginatedResponse(
        items=items,
        total=total,
        page=page,
        per_page=per_page,
        total_pages=math.ceil(total / per_page) if total > 0 else 0,
    )


# ──────────────────────────────── Detail endpoints ────────────────────────────────

@router.get("/articles/{article_id}")
async def get_article(article_id: int):
    conn = get_db()
    row = conn.execute("SELECT * FROM articles WHERE id = ?", (article_id,)).fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="Article not found")
    return {**dict(row), "categories": json.loads(row["categories"]) if row["categories"] else []}


@router.get("/books/{book_id}")
async def get_book(book_id: int):
    conn = get_db()
    row = conn.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="Book not found")
    return dict(row)


@router.get("/speeches/{speech_id}")
async def get_speech(speech_id: int):
    conn = get_db()
    row = conn.execute("SELECT * FROM speeches WHERE id = ?", (speech_id,)).fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="Speech not found")
    return {**dict(row), "categories": json.loads(row["categories"]) if row["categories"] else []}


@router.get("/discussions/{discussion_id}")
async def get_discussion(discussion_id: int):
    conn = get_db()
    row = conn.execute("SELECT * FROM discussions WHERE id = ?", (discussion_id,)).fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="Discussion not found")
    return {**dict(row), "categories": json.loads(row["categories"]) if row["categories"] else []}
