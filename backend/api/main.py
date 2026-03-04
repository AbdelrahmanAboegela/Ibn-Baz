"""
main.py
FastAPI application assembly.
Run with: uvicorn api.main:app --reload --port 8000
"""
import sys
from pathlib import Path

# Ensure parent is in path for config
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from api.routes import fatwas, content, chat, stats

# ──────────────────────────────── App ────────────────────────────────

app = FastAPI(
    title="مكتبة الشيخ ابن باز — API",
    description="API for Sheikh Ibn Baz's fatwas, articles, books, speeches, and RAG chatbot.",
    version="1.0.0",
)

# ──────────────────────────────── CORS ────────────────────────────────

# ──────────────────────────────── Middleware ────────────────────────────────

app.add_middleware(GZipMiddleware, minimum_size=1000)  # compress responses > 1 KB

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # dev: allow all origins (lock down before production)
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ──────────────────────────────── Routes ────────────────────────────────

app.include_router(fatwas.router)
app.include_router(content.router)
app.include_router(chat.router)
app.include_router(stats.router)


# ──────────────────────────────── Health ────────────────────────────────

@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "ibn-baz-rag"}


# ──────────────────────────────── Root ────────────────────────────────

@app.get("/")
async def root():
    return {
        "name": "مكتبة الشيخ ابن باز",
        "version": "1.0.0",
        "endpoints": {
            "fatwas": "/api/fatwas",
            "articles": "/api/articles",
            "books": "/api/books",
            "speeches": "/api/speeches",
            "discussions": "/api/discussions",
            "chat": "/api/chat",
            "stats": "/api/stats",
            "health": "/health",
        },
    }
