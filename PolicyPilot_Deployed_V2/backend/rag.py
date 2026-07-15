"""Local ingestion, retrieval, and answer generation pipeline."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable
from config import Settings, settings
from document_loader import DocumentChunk, list_documents, load_chunks
from ollama_client import OllamaClient
from vector_store import CsvVectorStore, SearchResult, VectorRecord

SYSTEM_PROMPT = """
You are a document-grounded policy assistant.
Use only the supplied source excerpts to answer the question.
Do not use outside knowledge and do not invent requirements, deadlines, approvals, exceptions, contacts, or procedures.
If the excerpts do not clearly support an answer, respond exactly: I do not know based on the provided documents.
When an answer is supported, end each factual paragraph or bullet with one or more source filenames in this format: (Source: filename.pdf).
Keep the answer focused and under 500 words.
""".strip()


@dataclass(frozen=True)
class Citation:
    source_file: str
    quote: str
    score: float


@dataclass(frozen=True)
class AnswerResult:
    answer: str
    citations: list[Citation]


def _client(config: Settings) -> OllamaClient:
    return OllamaClient(config.ollama_base_url, config.ollama_timeout_seconds)


def _batched(values: list[str], size: int = 16) -> Iterable[list[str]]:
    for start in range(0, len(values), size):
        yield values[start : start + size]


def _records_for_chunks(
    chunks: list[DocumentChunk], vectors: list[list[float]], embedding_model: str
) -> list[VectorRecord]:
    if len(chunks) != len(vectors):
        raise ValueError("Ollama returned a different number of embeddings than inputs.")

    return [
        VectorRecord(
            chunk_id=f"{chunk.source_file}::chunk_{chunk.chunk_index:05d}",
            source_file=chunk.source_file,
            chunk_index=chunk.chunk_index,
            text=chunk.text,
            embedding_model=embedding_model,
            embedding=vector,
        )
        for chunk, vector in zip(chunks, vectors)
    ]


def rebuild_index(config: Settings = settings) -> int:
    documents = list_documents(config.documents_dir)
    if not documents:
        raise FileNotFoundError(
            f"No supported documents were found in {config.documents_dir}. "
            "Add a PDF, DOCX, TXT, or Markdown file first."
        )

    chunks: list[DocumentChunk] = []
    for document in documents:
        chunks.extend(
            load_chunks(
                document,
                chunk_size=config.chunk_size_chars,
                overlap=config.chunk_overlap_chars,
            )
        )

    if not chunks:
        raise ValueError("The documents did not contain extractable text.")

    client = _client(config)
    vectors: list[list[float]] = []
    embedding_inputs = [
        f"Source file: {chunk.source_file}\nDocument text: {chunk.text}" for chunk in chunks
    ]
    for batch in _batched(embedding_inputs):
        vectors.extend(client.embed(config.embed_model, batch))

    records = _records_for_chunks(chunks, vectors, config.embed_model)
    CsvVectorStore(config.vector_store_csv).write(records)
    return len(records)


def add_document(path: Path, config: Settings = settings) -> int:
    source_path = path.expanduser().resolve()
    if not source_path.is_file():
        raise FileNotFoundError(f"Document not found: {source_path}")

    destination = config.documents_dir / source_path.name
    config.documents_dir.mkdir(parents=True, exist_ok=True)
    if source_path != destination.resolve():
        destination.write_bytes(source_path.read_bytes())

    return rebuild_index(config)


def remove_document(filename: str, config: Settings = settings) -> int:
    safe_name = Path(filename).name
    target = config.documents_dir / safe_name
    if target.exists():
        target.unlink()
    if list_documents(config.documents_dir):
        return rebuild_index(config)

    config.vector_store_csv.unlink(missing_ok=True)
    return 0


def retrieve(question: str, top_k: int | None = None, config: Settings = settings) -> list[SearchResult]:
    query = question.strip()
    if not query:
        return []

    query_vector = _client(config).embed(config.embed_model, query)[0]
    return CsvVectorStore(config.vector_store_csv).search(
        query_embedding=query_vector,
        embedding_model=config.embed_model,
        top_k=top_k or config.top_k,
        minimum_score=config.min_similarity,
    )


def _build_user_prompt(question: str, results: list[SearchResult], max_chars: int) -> str:
    sections: list[str] = []
    used = 0

    for result in results:
        section = (
            f"SOURCE_FILE: {result.record.source_file}\n"
            f"SIMILARITY: {result.score:.4f}\n"
            f"EXCERPT:\n{result.record.text}"
        )
        if sections and used + len(section) > max_chars:
            break
        sections.append(section)
        used += len(section)

    context = "\n\n---\n\n".join(sections)
    return f"Retrieved excerpts:\n\n{context}\n\nUser question: {question}"


def _quote(text: str, limit: int = 280) -> str:
    compact = re.sub(r"\s+", " ", text).strip()
    return compact[:limit] + ("..." if len(compact) > limit else "")


def answer_question(
    question: str, top_k: int | None = None, config: Settings = settings
) -> AnswerResult:
    question = question.strip()
    if not question:
        return AnswerResult(answer="Please enter a question.", citations=[])

    results = retrieve(question, top_k=top_k, config=config)
    if not results:
        return AnswerResult(
            answer="I do not know based on the provided documents.", citations=[]
        )

    answer = _client(config).chat(
        config.chat_model,
        SYSTEM_PROMPT,
        _build_user_prompt(question, results, config.max_context_chars),
    )

    if "i do not know based on the provided documents" in answer.lower():
        return AnswerResult(answer=answer, citations=[])

    seen: set[tuple[str, int]] = set()
    citations: list[Citation] = []
    for result in results:
        key = (result.record.source_file, result.record.chunk_index)
        if key in seen:
            continue
        seen.add(key)
        citations.append(
            Citation(
                source_file=result.record.source_file,
                quote=_quote(result.record.text),
                score=result.score,
            )
        )

    return AnswerResult(answer=answer, citations=citations)
