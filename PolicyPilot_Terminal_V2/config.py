"""Environment-based configuration for the local document RAG assistant."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")


def _path_from_env(name: str, default: str) -> Path:
    raw_value = os.getenv(name, default).strip()
    path = Path(raw_value).expanduser()
    return path if path.is_absolute() else (BASE_DIR / path).resolve()


def _int_from_env(name: str, default: int, minimum: int = 1) -> int:
    value = int(os.getenv(name, str(default)))
    if value < minimum:
        raise ValueError(f"{name} must be at least {minimum}.")
    return value


@dataclass(frozen=True)
class Settings:
    ollama_base_url: str
    chat_model: str
    embedding_model: str
    guard_model: str | None
    documents_dir: Path
    vector_db_csv: Path
    top_k: int
    max_chunk_chars: int
    chunk_overlap_chars: int
    max_context_chars: int
    context_window: int
    request_timeout_seconds: int
    embed_batch_size: int


def load_settings() -> Settings:
    max_chunk_chars = _int_from_env("MAX_CHUNK_CHARS", 4000, minimum=200)
    overlap = _int_from_env("CHUNK_OVERLAP_CHARS", 400, minimum=0)
    if overlap >= max_chunk_chars:
        raise ValueError("CHUNK_OVERLAP_CHARS must be smaller than MAX_CHUNK_CHARS.")

    guard_model = os.getenv("OLLAMA_GUARD_MODEL", "").strip() or None

    return Settings(
        ollama_base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/"),
        chat_model=os.getenv("OLLAMA_CHAT_MODEL", "llama3.2:3b").strip(),
        embedding_model=os.getenv("OLLAMA_EMBED_MODEL", "embeddinggemma").strip(),
        guard_model=guard_model,
        documents_dir=_path_from_env("DOCUMENTS_DIR", "data/documents"),
        vector_db_csv=_path_from_env("VECTOR_DB_CSV", "data/vector_store/vectors.csv"),
        top_k=_int_from_env("TOP_K", 5),
        max_chunk_chars=max_chunk_chars,
        chunk_overlap_chars=overlap,
        max_context_chars=_int_from_env("MAX_CONTEXT_CHARS", 16000, minimum=1000),
        context_window=_int_from_env("OLLAMA_CONTEXT_WINDOW", 8192, minimum=1024),
        request_timeout_seconds=_int_from_env("OLLAMA_TIMEOUT_SECONDS", 180),
        embed_batch_size=_int_from_env("EMBED_BATCH_SIZE", 16),
    )
