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
    # --- Groq API Keys (rotate to avoid rate limits) ---
    groq_api_key: str
    groq_api_key_2: Optional[str] = None
    groq_api_key_3: Optional[str] = None
    groq_api_key_4: Optional[str] = None
    groq_api_key_5: Optional[str] = None
    groq_model: str = "llama-3.3-70b-versatile"

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

    @property
    def all_groq_keys(self) -> list[str]:
        """All available Groq keys for rotation."""
        keys = [self.groq_api_key]
        for attr in [self.groq_api_key_2, self.groq_api_key_3,
                     self.groq_api_key_4, self.groq_api_key_5]:
            if attr:
                keys.append(attr)
        return keys

    class Config:
        env_file = str(BASE_DIR / ".env")
        env_file_encoding = "utf-8"


# Singleton
settings = Settings()

# Set HF environment variables BEFORE any HF imports
os.environ["HF_HOME"] = settings.hf_home
os.environ["TRANSFORMERS_CACHE"] = settings.transformers_cache
