"""
routes/content.py
Non-fatwa content endpoints: articles, books, speeches, discussions, audios.
All served from SQLite.
"""
import json
import math
import re
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
from api.hadith_resolver import extract_citations as _extract_hadith


def extract_hadith_refs(text: str) -> list[dict]:
    """Extract hadith citations from raw Arabic text, serialised as dicts."""
    if not text:
        return []
    return [c.model_dump() for c in _extract_hadith(text)]

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


# ── Load Quran verse data once at startup ─────────────────────────────────────────────────
_QURAN_DATA: dict = {}
try:
    _qpath = Path(__file__).parent.parent.parent / "backend" / "data" / "quran_verses.json"
    if not _qpath.exists():
        _qpath = Path(settings.data_dir) / "quran_verses.json"
    if _qpath.exists():
        with open(_qpath, encoding="utf-8") as _f:
            _QURAN_DATA = json.load(_f)
except Exception:
    pass

_Q_SURAH_NAME_TO_NUM: dict[str, str] = _QURAN_DATA.get("surah_name_to_number", {})
_Q_VERSES: dict = _QURAN_DATA.get("verses", {})


def _lookup_verse(ref: str) -> str:
    """Resolve 'البقرة:43' or 'البقرة: 43' to actual verse text from quran_verses.json."""
    if ":" not in ref:
        return ""
    parts = ref.split(":")
    surah_part = parts[0].strip()
    ayah_part  = parts[-1].strip().split("-")[0].strip()  # handle ranges like 43-44
    surah_num  = str(_Q_SURAH_NAME_TO_NUM.get(surah_part, ""))
    if not surah_num:
        return ""
    return _Q_VERSES.get(surah_num, {}).get(ayah_part, "")


# ── Quran citation extractor ─────────────────────────────────────────────────
# Islamic texts use: {verse text} optionally followed by [SurahName:N] or (SurahName:N)
_Q_VERSE = re.compile(
    r'\{([^{}]{10,400}?)\}'                              # { verse text }
    r'(?:\s*(?:\[([^\]]{3,60}?)\]|\(([^)]{3,60}?)\)))?',  # optional [ref] or (ref)
    re.DOTALL,
)
# Match plain [SurahName:N] references in Arabic text (common in scraped content)
_Q_REF_ONLY = re.compile(
    r'\[([\u0600-\u06FF]{2,20}\s*:\s*\d{1,3}(?:\s*-\s*\d{1,3})?)\]'
)


def extract_quran_refs(text: str) -> list[dict]:
    """Extract Quran citations from raw Arabic text (up to 12)."""
    if not text:
        return []
    seen, citations = set(), []

    # Pattern 1: {verse text} + optional reference
    for m in _Q_VERSE.finditer(text):
        verse = m.group(1).strip()
        ref   = (m.group(2) or m.group(3) or "").strip()
        key   = verse[:40]
        if key not in seen:
            seen.add(key)
            citations.append({"verified_text": verse, "reference": ref,
                              "surah_name": "", "quran_url": ""})
        if len(citations) >= 12:
            break

    # Pattern 2: standalone [SurahName:AyahNum] — look up verse text from quran_verses.json
    for m in _Q_REF_ONLY.finditer(text):
        ref = m.group(1).strip()
        key = ref
        if key in seen:
            continue
        seen.add(key)
        verse_text = _lookup_verse(ref)  # populated from quran_verses.json
        citations.append({"verified_text": verse_text, "reference": ref,
                          "surah_name": "", "quran_url": ""})
        if len(citations) >= 12:
            break

    return citations


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
    text = row["text"] or ""
    return {
        **dict(row),
        "categories": json.loads(row["categories"]) if row["categories"] else [],
        "quran_citations": extract_quran_refs(text),
        "hadith_citations": extract_hadith_refs(text),
    }


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
    text = row["text"] or ""
    return {
        **dict(row),
        "categories": json.loads(row["categories"]) if row["categories"] else [],
        "quran_citations": extract_quran_refs(text),
        "hadith_citations": extract_hadith_refs(text),
    }


@router.get("/discussions/{discussion_id}")
async def get_discussion(discussion_id: int):
    conn = get_db()
    row = conn.execute("SELECT * FROM discussions WHERE id = ?", (discussion_id,)).fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="Discussion not found")
    text = row["text"] or ""
    return {
        **dict(row),
        "categories": json.loads(row["categories"]) if row["categories"] else [],
        "quran_citations": extract_quran_refs(text),
        "hadith_citations": extract_hadith_refs(text),
    }


# ──────────────────────────────── Audios ────────────────────────────────

@router.get("/audios", response_model=PaginatedResponse)
async def list_audios(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
):
    conn = get_db()
    offset = (page - 1) * per_page
    # Show items with audio_url first, then those without
    rows = conn.execute(
        """SELECT * FROM audios
           ORDER BY CASE WHEN audio_url != '' THEN 0 ELSE 1 END, id
           LIMIT ? OFFSET ?""",
        (per_page, offset),
    ).fetchall()
    total = conn.execute("SELECT COUNT(*) FROM audios").fetchone()[0]
    conn.close()

    items = [
        {
            "id": r["id"],
            "title": r["title"] or "",
            "transcript_preview": (r["transcript"] or "")[:300],
            "audio_url": r["audio_url"] or "",
            "has_audio": bool(r["audio_url"]),
            "categories": json.loads(r["categories"]) if r["categories"] else [],
        }
        for r in rows
    ]

    return PaginatedResponse(
        items=items,
        total=total,
        page=page,
        per_page=per_page,
        total_pages=math.ceil(total / per_page) if total > 0 else 0,
    )


@router.get("/audios/{audio_id}")
async def get_audio(audio_id: int):
    conn = get_db()
    row = conn.execute("SELECT * FROM audios WHERE id = ?", (audio_id,)).fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="Audio not found")
    text = row["transcript"] or ""
    return {
        **dict(row),
        "has_audio": bool(row["audio_url"]),
        "categories": json.loads(row["categories"]) if row["categories"] else [],
        "qa_pairs": json.loads(row["qa_pairs"]) if row["qa_pairs"] else [],
        "quran_citations": extract_quran_refs(text),
        "hadith_citations": extract_hadith_refs(text),
    }

