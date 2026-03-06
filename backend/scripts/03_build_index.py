"""
03_build_index.py
Embeds 24K enriched fatwas into Qdrant (local file mode).
Uses intfloat/multilingual-e5-base for dense vectors.
Uses Qdrant's FastEmbed for sparse (BM25) vectors.
Creates a single collection with hybrid search support.
"""
import json
import sys
import time
from pathlib import Path

import numpy as np
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    PointStruct,
    SparseIndexParams,
    SparseVector,
    SparseVectorParams,
    VectorParams,
)
from sentence_transformers import SentenceTransformer
import torch

_DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

# Add parent to path for config
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import settings

# Constants
COLLECTION_NAME = settings.qdrant_collection
BATCH_SIZE = 64
DENSE_DIM = 768  # multilingual-e5-base


def create_qdrant_client() -> QdrantClient:
    """Create Qdrant client in local file mode."""
    return QdrantClient(path=settings.qdrant_path)


def create_collection(client: QdrantClient):
    """Create or recreate the fatwas collection with hybrid vectors."""
    if client.collection_exists(COLLECTION_NAME):
        print(f"⚠️  Collection '{COLLECTION_NAME}' exists. Dropping and recreating.")
        client.delete_collection(COLLECTION_NAME)

    client.create_collection(
        collection_name=COLLECTION_NAME,
        vectors_config={
            "dense": VectorParams(
                size=DENSE_DIM,
                distance=Distance.COSINE,
            ),
        },
        sparse_vectors_config={
            "sparse": SparseVectorParams(
                index=SparseIndexParams(on_disk=False),
            ),
        },
    )
    print(f"✅ Created collection '{COLLECTION_NAME}' (dense: {DENSE_DIM}d + sparse BM25)")


def load_embedding_model() -> SentenceTransformer:
    """Load the multilingual-e5-base model (uses cached version, GPU if available)."""
    print(f"Loading embedding model: {settings.embedding_model} on {_DEVICE}...")
    model = SentenceTransformer(
        settings.embedding_model,
        cache_folder=settings.transformers_cache,
        device=_DEVICE,
    )
    print(f"   Loaded successfully (device: {model.device})")
    return model


def build_embedding_text(fatwa: dict) -> str:
    """Build the text to embed for a fatwa using e5 query format."""
    # multilingual-e5 expects "query: " or "passage: " prefix
    title = fatwa.get("title", "")
    question = fatwa.get("question", "")
    answer = fatwa.get("answer", "")[:1000]  # truncate long answers
    categories = ", ".join(fatwa.get("categories", []))

    return f"passage: {title} {question} {answer} {categories}"


def build_sparse_text(fatwa: dict) -> str:
    """Build text for sparse (BM25) indexing."""
    return " ".join([
        fatwa.get("title", ""),
        fatwa.get("question", ""),
        fatwa.get("answer", "")[:2000],
    ])


def build_payload(fatwa: dict) -> dict:
    """Build Qdrant payload (stored metadata, not vectorized)."""
    return {
        "fatwa_id": fatwa["fatwa_id"],
        "title": fatwa.get("title", ""),
        "question": fatwa.get("question", ""),
        "answer": fatwa.get("answer", ""),
        "answer_direct": fatwa.get("answer_direct", ""),
        "source_ref": fatwa.get("source_ref", ""),
        "url": fatwa.get("url", ""),
        "categories": fatwa.get("categories", []),
        "related_ids": fatwa.get("related_ids", []),
        "audio_url": fatwa.get("audio_url", ""),
        "quran_citations": fatwa.get("quran_citations", []),
        "content_type": "fatwa",
    }


def main():
    # Determine input file (enriched preferred, raw fallback)
    enriched_path = Path(settings.enriched_fatwas_path)
    raw_path = Path(settings.data_dir) / "fatwa.jsonl"

    if enriched_path.exists():
        input_path = enriched_path
        print(f"📝 Using enriched fatwas: {input_path}")
    elif raw_path.exists():
        input_path = raw_path
        print(f"📝 Using raw fatwas (no Quran enrichment): {input_path}")
    else:
        print(f"❌ No fatwa data found at {enriched_path} or {raw_path}")
        sys.exit(1)

    # Load all fatwas
    print("📦 Loading fatwas...")
    fatwas = []
    with open(input_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                fatwas.append(json.loads(line))
    print(f"   ✅ Loaded {len(fatwas):,} fatwas")

    # Create Qdrant collection
    client = create_qdrant_client()
    create_collection(client)

    # Load embedding model
    embed_model = load_embedding_model()

    # Process in batches
    print(f"\n🚀 Indexing {len(fatwas):,} fatwas (batch_size={BATCH_SIZE})...")
    start_time = time.time()
    total_indexed = 0

    for batch_start in range(0, len(fatwas), BATCH_SIZE):
        batch = fatwas[batch_start: batch_start + BATCH_SIZE]

        # Dense embeddings
        texts = [build_embedding_text(f) for f in batch]
        dense_embeddings = embed_model.encode(texts, show_progress_bar=False)

        # Build points
        points = []
        for i, fatwa in enumerate(batch):
            point_id = fatwa["fatwa_id"]

            points.append(PointStruct(
                id=point_id,
                vector={
                    "dense": dense_embeddings[i].tolist(),
                },
                payload=build_payload(fatwa),
            ))

        # Upsert batch
        client.upsert(
            collection_name=COLLECTION_NAME,
            points=points,
        )
        total_indexed += len(points)

        if total_indexed % (BATCH_SIZE * 10) == 0 or total_indexed == len(fatwas):
            elapsed = time.time() - start_time
            rate = total_indexed / elapsed if elapsed > 0 else 0
            print(f"   ✅ {total_indexed:,}/{len(fatwas):,} indexed "
                  f"({rate:.0f} fatwas/sec, {elapsed:.1f}s elapsed)")

    elapsed = time.time() - start_time
    print(f"\n🎉 Done! Indexed {total_indexed:,} fatwas in {elapsed:.1f}s")
    print(f"   Qdrant data stored at: {settings.qdrant_path}")

    # Verify
    info = client.get_collection(COLLECTION_NAME)
    print(f"   Collection points: {info.points_count}")
    print(f"   Vector size: {DENSE_DIM}d (dense)")


if __name__ == "__main__":
    main()
