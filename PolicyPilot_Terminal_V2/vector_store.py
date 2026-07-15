"""CSV-backed embedding storage and cosine-similarity retrieval."""

from __future__ import annotations

import csv
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from documents import TextChunk, chunk_sections, iter_document_files, read_document
from ollama_client import OllamaClient

FIELDNAMES = [
    "source",
    "location",
    "chunk_index",
    "content",
    "embedding_model",
    "embedding_dim",
    "embedding",
]


@dataclass(frozen=True)
class VectorRecord:
    source: str
    location: str
    chunk_index: int
    content: str
    embedding_model: str
    embedding: list[float]


@dataclass(frozen=True)
class SearchResult:
    record: VectorRecord
    similarity: float


def _cosine_similarity(left: list[float], right: list[float]) -> float:
    if len(left) != len(right) or not left:
        return -1.0
    dot_product = sum(a * b for a, b in zip(left, right))
    left_norm = math.sqrt(sum(value * value for value in left))
    right_norm = math.sqrt(sum(value * value for value in right))
    if left_norm == 0 or right_norm == 0:
        return -1.0
    return dot_product / (left_norm * right_norm)


def load_records(csv_path: Path) -> list[VectorRecord]:
    if not csv_path.exists():
        return []

    records: list[VectorRecord] = []
    with csv_path.open("r", newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        missing = set(FIELDNAMES) - set(reader.fieldnames or [])
        if missing:
            raise ValueError(
                f"Vector CSV is missing required columns: {', '.join(sorted(missing))}"
            )

        for row in reader:
            embedding = json.loads(row["embedding"])
            records.append(
                VectorRecord(
                    source=row["source"],
                    location=row["location"],
                    chunk_index=int(row["chunk_index"]),
                    content=row["content"],
                    embedding_model=row["embedding_model"],
                    embedding=[float(value) for value in embedding],
                )
            )
    return records


def write_records(csv_path: Path, records: Iterable[VectorRecord]) -> None:
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = csv_path.with_suffix(csv_path.suffix + ".tmp")

    with temporary_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDNAMES)
        writer.writeheader()
        for record in records:
            writer.writerow(
                {
                    "source": record.source,
                    "location": record.location,
                    "chunk_index": record.chunk_index,
                    "content": record.content,
                    "embedding_model": record.embedding_model,
                    "embedding_dim": len(record.embedding),
                    "embedding": json.dumps(record.embedding, separators=(",", ":")),
                }
            )

    temporary_path.replace(csv_path)


def _embed_chunks(
    chunks: list[TextChunk],
    client: OllamaClient,
    embedding_model: str,
    batch_size: int,
) -> list[VectorRecord]:
    records: list[VectorRecord] = []

    for start in range(0, len(chunks), batch_size):
        batch = chunks[start : start + batch_size]
        inputs = [f"Source: {chunk.source}\n{chunk.content}" for chunk in batch]
        embeddings = client.embed(inputs, embedding_model)
        if len(embeddings) != len(batch):
            raise ValueError("Ollama returned a different number of embeddings than requested.")

        for chunk, embedding in zip(batch, embeddings):
            records.append(
                VectorRecord(
                    source=chunk.source,
                    location=chunk.location,
                    chunk_index=chunk.chunk_index,
                    content=chunk.content,
                    embedding_model=embedding_model,
                    embedding=[float(value) for value in embedding],
                )
            )

    return records


def build_index(
    documents_dir: Path,
    csv_path: Path,
    client: OllamaClient,
    embedding_model: str,
    max_chunk_chars: int,
    overlap_chars: int,
    batch_size: int,
) -> tuple[int, int]:
    files = iter_document_files(documents_dir)
    all_chunks: list[TextChunk] = []

    for path in files:
        source = path.relative_to(documents_dir).as_posix()
        sections = read_document(path, source)
        all_chunks.extend(chunk_sections(sections, max_chunk_chars, overlap_chars))

    records = _embed_chunks(all_chunks, client, embedding_model, batch_size)
    write_records(csv_path, records)
    return len(files), len(records)


def add_or_replace_document(
    path: Path,
    csv_path: Path,
    client: OllamaClient,
    embedding_model: str,
    max_chunk_chars: int,
    overlap_chars: int,
    batch_size: int,
) -> int:
    if not path.exists() or not path.is_file():
        raise FileNotFoundError(f"Document does not exist: {path}")

    source = path.name
    sections = read_document(path, source)
    chunks = chunk_sections(sections, max_chunk_chars, overlap_chars)
    new_records = _embed_chunks(chunks, client, embedding_model, batch_size)
    existing_records = [record for record in load_records(csv_path) if record.source != source]
    write_records(csv_path, [*existing_records, *new_records])
    return len(new_records)


def remove_source(csv_path: Path, source: str) -> int:
    records = load_records(csv_path)
    kept = [record for record in records if record.source != source]
    removed = len(records) - len(kept)
    write_records(csv_path, kept)
    return removed


def search(
    csv_path: Path,
    query_embedding: list[float],
    embedding_model: str,
    top_k: int,
) -> list[SearchResult]:
    records = load_records(csv_path)
    if not records:
        raise ValueError("The vector CSV is empty or missing. Run the ingest command first.")

    compatible = [
        record
        for record in records
        if record.embedding_model == embedding_model
        and len(record.embedding) == len(query_embedding)
    ]
    if not compatible:
        raise ValueError(
            "No embeddings in the CSV match the configured embedding model. "
            "Rebuild the index after changing OLLAMA_EMBED_MODEL."
        )

    results = [
        SearchResult(record, _cosine_similarity(query_embedding, record.embedding))
        for record in compatible
    ]
    results.sort(key=lambda item: item.similarity, reverse=True)
    return results[:top_k]
