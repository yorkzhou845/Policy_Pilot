"""Text extraction and simple overlapping chunk creation."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from docx import Document
from pypdf import PdfReader

SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".txt", ".md"}


@dataclass(frozen=True)
class DocumentChunk:
    source_file: str
    chunk_index: int
    text: str


def list_documents(folder: Path) -> list[Path]:
    if not folder.exists():
        return []

    return sorted(
        path
        for path in folder.rglob("*")
        if path.is_file()
        and path.suffix.lower() in SUPPORTED_EXTENSIONS
        and not path.name.startswith(".")
        and path.name.lower() != "readme.md"
    )


def extract_text(path: Path) -> str:
    suffix = path.suffix.lower()

    if suffix == ".pdf":
        reader = PdfReader(str(path))
        return "\n\n".join((page.extract_text() or "").strip() for page in reader.pages)

    if suffix == ".docx":
        document = Document(str(path))
        return "\n\n".join(paragraph.text.strip() for paragraph in document.paragraphs)

    if suffix in {".txt", ".md"}:
        return path.read_text(encoding="utf-8", errors="replace")

    raise ValueError(f"Unsupported document type: {path.suffix}")


def normalize_text(text: str) -> str:
    text = text.replace("\x00", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n[ \t]+", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def chunk_text(text: str, chunk_size: int, overlap: int) -> list[str]:
    text = normalize_text(text)
    if not text:
        return []

    paragraphs = [part.strip() for part in text.split("\n\n") if part.strip()]
    chunks: list[str] = []
    current = ""

    def emit(value: str) -> None:
        cleaned = value.strip()
        if cleaned:
            chunks.append(cleaned)

    for paragraph in paragraphs:
        if len(paragraph) > chunk_size:
            if current:
                emit(current)
                current = ""
            step = max(1, chunk_size - overlap)
            for start in range(0, len(paragraph), step):
                emit(paragraph[start : start + chunk_size])
            continue

        candidate = paragraph if not current else f"{current}\n\n{paragraph}"
        if len(candidate) <= chunk_size:
            current = candidate
            continue

        emit(current)
        prefix = current[-overlap:] if overlap else ""
        current = f"{prefix}\n\n{paragraph}".strip()

    emit(current)
    return chunks


def load_chunks(path: Path, chunk_size: int, overlap: int) -> list[DocumentChunk]:
    chunks = chunk_text(extract_text(path), chunk_size=chunk_size, overlap=overlap)
    return [
        DocumentChunk(source_file=path.name, chunk_index=index, text=text)
        for index, text in enumerate(chunks)
    ]
