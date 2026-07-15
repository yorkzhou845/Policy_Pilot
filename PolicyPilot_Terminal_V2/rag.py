"""Retrieval-augmented answer generation."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ollama_client import OllamaClient
from vector_store import SearchResult, search

SYSTEM_PROMPT = """
You are a document-grounded assistant.
Use only the retrieved excerpts supplied in the user message.
Do not use outside knowledge or invent requirements, dates, exceptions, contacts, or procedures.
If the excerpts do not support an answer, state that the answer is not available in the indexed documents.
Cite factual statements with the supplied source and location, for example: [Source: handbook.pdf, page 2].
Keep the response direct and clearly distinguish supported facts from uncertainty.
""".strip()


@dataclass(frozen=True)
class RagAnswer:
    text: str
    sources: list[str]


def _guard_allows(text: str, client: OllamaClient, guard_model: str | None) -> bool:
    if not guard_model:
        return True

    response = client.chat(
        guard_model,
        [{"role": "user", "content": text}],
        context_window=4096,
        temperature=0.0,
    )
    first_line = response.splitlines()[0].strip().lower() if response else ""
    return first_line == "safe"


def _build_context(results: list[SearchResult], max_context_chars: int) -> str:
    sections: list[str] = []
    used_chars = 0

    for result in results:
        record = result.record
        block = (
            f"SOURCE: {record.source}\n"
            f"LOCATION: {record.location}\n"
            f"EXCERPT:\n{record.content}\n"
        )
        if sections and used_chars + len(block) > max_context_chars:
            break
        sections.append(block)
        used_chars += len(block)

    return "\n---\n".join(sections)


def answer_question(
    question: str,
    *,
    csv_path: Path,
    client: OllamaClient,
    chat_model: str,
    embedding_model: str,
    guard_model: str | None,
    top_k: int,
    max_context_chars: int,
    context_window: int,
) -> RagAnswer:
    question = question.strip()
    if not question:
        raise ValueError("Question cannot be blank.")

    if not _guard_allows(question, client, guard_model):
        return RagAnswer("The configured safety model blocked this request.", [])

    question_embedding = client.embed(question, embedding_model)[0]
    results = search(csv_path, question_embedding, embedding_model, top_k)
    context = _build_context(results, max_context_chars)

    user_prompt = f"""
Retrieved excerpts:

{context}

Question:
{question}

Answer only from the retrieved excerpts. Include source-and-location citations for supported claims.
""".strip()

    answer = client.chat(
        chat_model,
        [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        context_window=context_window,
        temperature=0.0,
    )

    if not _guard_allows(answer, client, guard_model):
        return RagAnswer("The configured safety model blocked the generated response.", [])

    sources: list[str] = []
    for result in results:
        label = f"{result.record.source} ({result.record.location})"
        if label not in sources:
            sources.append(label)

    return RagAnswer(answer, sources)
