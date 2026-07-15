"""CSV vector storage and cosine-similarity retrieval."""

from __future__ import annotations

import csv
import json
import math
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

CSV_FIELDS = [
    "chunk_id",
    "source_file",
    "chunk_index",
    "text",
    "embedding_model",
    "embedding_dim",
    "embedding_json",
]


@dataclass(frozen=True)
class VectorRecord:
    chunk_id: str
    source_file: str
    chunk_index: int
    text: str
    embedding_model: str
    embedding: list[float]


@dataclass(frozen=True)
class SearchResult:
    record: VectorRecord
    score: float


def cosine_similarity(left: list[float], right: list[float]) -> float:
    if len(left) != len(right):
        raise ValueError(f"Embedding dimension mismatch: {len(left)} != {len(right)}")

    dot = math.fsum(a * b for a, b in zip(left, right))
    left_norm = math.sqrt(math.fsum(value * value for value in left))
    right_norm = math.sqrt(math.fsum(value * value for value in right))
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return dot / (left_norm * right_norm)


class CsvVectorStore:
    def __init__(self, path: Path) -> None:
        self.path = path

    def exists(self) -> bool:
        return self.path.is_file() and self.path.stat().st_size > 0

    def load(self) -> list[VectorRecord]:
        if not self.exists():
            return []

        records: list[VectorRecord] = []
        with self.path.open("r", encoding="utf-8", newline="") as file:
            reader = csv.DictReader(file)
            missing = set(CSV_FIELDS) - set(reader.fieldnames or [])
            if missing:
                raise ValueError(f"Vector CSV is missing columns: {', '.join(sorted(missing))}")

            for row in reader:
                embedding = json.loads(row["embedding_json"])
                records.append(
                    VectorRecord(
                        chunk_id=row["chunk_id"],
                        source_file=row["source_file"],
                        chunk_index=int(row["chunk_index"]),
                        text=row["text"],
                        embedding_model=row["embedding_model"],
                        embedding=[float(value) for value in embedding],
                    )
                )
        return records

    def write(self, records: Iterable[VectorRecord]) -> None:
        records = list(records)
        self.path.parent.mkdir(parents=True, exist_ok=True)

        descriptor, temporary_name = tempfile.mkstemp(
            prefix=f"{self.path.stem}.", suffix=".tmp", dir=self.path.parent
        )
        os.close(descriptor)
        temporary_path = Path(temporary_name)

        try:
            with temporary_path.open("w", encoding="utf-8", newline="") as file:
                writer = csv.DictWriter(file, fieldnames=CSV_FIELDS)
                writer.writeheader()
                for record in records:
                    writer.writerow(
                        {
                            "chunk_id": record.chunk_id,
                            "source_file": record.source_file,
                            "chunk_index": record.chunk_index,
                            "text": record.text,
                            "embedding_model": record.embedding_model,
                            "embedding_dim": len(record.embedding),
                            "embedding_json": json.dumps(record.embedding, separators=(",", ":")),
                        }
                    )
            temporary_path.replace(self.path)
        finally:
            temporary_path.unlink(missing_ok=True)

    def search(
        self,
        query_embedding: list[float],
        embedding_model: str,
        top_k: int,
        minimum_score: float,
    ) -> list[SearchResult]:
        compatible = [
            record
            for record in self.load()
            if record.embedding_model == embedding_model
            and len(record.embedding) == len(query_embedding)
        ]

        if not compatible:
            raise ValueError(
                "The vector store is empty or was built with a different embedding model. "
                "Run `python manage.py rebuild`."
            )

        results = [
            SearchResult(record=record, score=cosine_similarity(query_embedding, record.embedding))
            for record in compatible
        ]
        results.sort(key=lambda item: item.score, reverse=True)
        return [result for result in results[:top_k] if result.score >= minimum_score]
