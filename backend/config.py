"""
BinBaz RAG System Configuration
Loads settings from .env and provides typed access via Pydantic Settings.
"""
import os
from pathlib import Path
from pydantic_settings import BaseSettings
from typing import Optional

# Project root
BASE_DIR = Path(__file__).resolve().parent


class Settings(BaseSettings):
    # --- Fanar API Keys ---
    fanar_api_key: str
    fanar_model: str = "Fanar-Sadiq"

    # --- Hugging Face ---
    hf_home: str = str(Path.home() / ".cache" / "huggingface")
    transformers_cache: str = str(Path.home() / ".cache" / "huggingface" / "hub")
    embedding_model: str = "intfloat/multilingual-e5-base"

    # --- Qdrant ---
    qdrant_path: str = str(BASE_DIR / "qdrant_data")
    qdrant_collection: str = "fatwas"

    # --- SQLite ---
    content_db_path: str = str(BASE_DIR / "content.db")

    # --- Data paths ---
    data_dir: str = str(BASE_DIR / "data")
    quran_verses_path: str = str(BASE_DIR / "data" / "quran_verses.json")
    enriched_fatwas_path: str = str(BASE_DIR / "data" / "enriched_fatwas.jsonl")

    # --- Server ---
    api_host: str = "0.0.0.0"
    api_port: int = 8000



    class Config:
        env_file = str(BASE_DIR / ".env")
        env_file_encoding = "utf-8"


# Singleton
settings = Settings()

# Set HF environment variables BEFORE any HF imports
os.environ["HF_HOME"] = settings.hf_home
os.environ["TRANSFORMERS_CACHE"] = settings.transformers_cache
