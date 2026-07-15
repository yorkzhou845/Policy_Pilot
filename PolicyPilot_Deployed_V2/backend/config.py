"""Environment-based configuration for the local Policy Pilot backend."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")


def _resolve_path(value: str, default: str) -> Path:
    path = Path(value or default).expanduser()
    if not path.is_absolute():
        path = BASE_DIR / path
    return path.resolve()


def _get_int(name: str, default: int, minimum: int = 1) -> int:
    value = int(os.getenv(name, str(default)))
    if value < minimum:
        raise ValueError(f"{name} must be at least {minimum}.")
    return value


def _get_float(name: str, default: float) -> float:
    return float(os.getenv(name, str(default)))


@dataclass(frozen=True)
class Settings:
    ollama_base_url: str
    chat_model: str
    embed_model: str
    ollama_timeout_seconds: int
    documents_dir: Path
    vector_store_csv: Path
    top_k: int
    min_similarity: float
    chunk_size_chars: int
    chunk_overlap_chars: int
    max_context_chars: int


def load_settings() -> Settings:
    base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")
    chat_model = os.getenv("OLLAMA_CHAT_MODEL", "llama3.2:3b").strip()
    embed_model = os.getenv("OLLAMA_EMBED_MODEL", "embeddinggemma").strip()

    if not base_url:
        raise ValueError("OLLAMA_BASE_URL cannot be empty.")
    if not chat_model:
        raise ValueError("OLLAMA_CHAT_MODEL cannot be empty.")
    if not embed_model:
        raise ValueError("OLLAMA_EMBED_MODEL cannot be empty.")

    chunk_size = _get_int("CHUNK_SIZE_CHARS", 2400, 200)
    overlap = _get_int("CHUNK_OVERLAP_CHARS", 250, 0)
    if overlap >= chunk_size:
        raise ValueError("CHUNK_OVERLAP_CHARS must be smaller than CHUNK_SIZE_CHARS.")

    min_similarity = _get_float("MIN_SIMILARITY", 0.20)
    if not -1.0 <= min_similarity <= 1.0:
        raise ValueError("MIN_SIMILARITY must be between -1.0 and 1.0.")

    return Settings(
        ollama_base_url=base_url,
        chat_model=chat_model,
        embed_model=embed_model,
        ollama_timeout_seconds=_get_int("OLLAMA_TIMEOUT_SECONDS", 180, 1),
        documents_dir=_resolve_path(os.getenv("POLICY_DOCUMENTS_DIR", ""), "data/documents"),
        vector_store_csv=_resolve_path(os.getenv("VECTOR_STORE_CSV", ""), "data/vector_store/vector_store.csv"),
        top_k=_get_int("TOP_K", 5, 1),
        min_similarity=min_similarity,
        chunk_size_chars=chunk_size,
        chunk_overlap_chars=overlap,
        max_context_chars=_get_int("MAX_CONTEXT_CHARS", 14000, 1000),
    )


settings = load_settings()
