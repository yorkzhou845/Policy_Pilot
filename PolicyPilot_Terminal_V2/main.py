"""Command-line interface for the local CSV-backed RAG assistant."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from config import load_settings
from ollama_client import OllamaClient, OllamaError
from rag import answer_question
from vector_store import add_or_replace_document, build_index, remove_source


def _create_client() -> tuple[object, OllamaClient]:
    settings = load_settings()
    client = OllamaClient(settings.ollama_base_url, settings.request_timeout_seconds)
    return settings, client


def command_check() -> None:
    settings, client = _create_client()
    models = client.list_models()
    configured = [settings.chat_model, settings.embedding_model]
    if settings.guard_model:
        configured.append(settings.guard_model)

    print(f"Ollama reachable at: {settings.ollama_base_url}")
    print("Configured models:")
    for model in configured:
        available = model in models or (
            ":" not in model
            and any(installed.split(":", 1)[0] == model for installed in models)
        )
        status = "available" if available else "not found"
        print(f"- {model}: {status}")


def command_ingest() -> None:
    settings, client = _create_client()
    settings.documents_dir.mkdir(parents=True, exist_ok=True)
    file_count, chunk_count = build_index(
        settings.documents_dir,
        settings.vector_db_csv,
        client,
        settings.embedding_model,
        settings.max_chunk_chars,
        settings.chunk_overlap_chars,
        settings.embed_batch_size,
    )
    print(f"Indexed {file_count} document(s) into {chunk_count} chunk(s).")
    print(f"CSV vector store: {settings.vector_db_csv}")


def command_add(file_path: str) -> None:
    settings, client = _create_client()
    count = add_or_replace_document(
        Path(file_path).expanduser().resolve(),
        settings.vector_db_csv,
        client,
        settings.embedding_model,
        settings.max_chunk_chars,
        settings.chunk_overlap_chars,
        settings.embed_batch_size,
    )
    print(f"Added or replaced {count} chunk(s) for {Path(file_path).name}.")


def command_remove(source: str) -> None:
    settings, _ = _create_client()
    removed = remove_source(settings.vector_db_csv, source)
    print(f"Removed {removed} chunk(s) for source: {source}")


def _ask(question: str) -> None:
    settings, client = _create_client()
    result = answer_question(
        question,
        csv_path=settings.vector_db_csv,
        client=client,
        chat_model=settings.chat_model,
        embedding_model=settings.embedding_model,
        guard_model=settings.guard_model,
        top_k=settings.top_k,
        max_context_chars=settings.max_context_chars,
        context_window=settings.context_window,
    )
    print(result.text)
    if result.sources:
        print("\nRetrieved sources:")
        for source in result.sources:
            print(f"- {source}")


def command_chat() -> None:
    print("Local document assistant. Type 'exit' to stop.")
    while True:
        try:
            question = input("\nQuestion: ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if question.lower() in {"exit", "quit", "bye"}:
            break
        if question:
            _ask(question)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Local Ollama RAG assistant with a CSV vector store."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("check", help="Check Ollama and configured model availability.")
    subparsers.add_parser("ingest", help="Rebuild the CSV index from DOCUMENTS_DIR.")

    add_parser = subparsers.add_parser("add", help="Add or replace one document in the CSV.")
    add_parser.add_argument("file", help="Path to a PDF, DOCX, TXT, or Markdown file.")

    remove_parser = subparsers.add_parser("remove", help="Remove one stored source name.")
    remove_parser.add_argument("source", help="Exact source name stored in the CSV.")

    ask_parser = subparsers.add_parser("ask", help="Ask one question and exit.")
    ask_parser.add_argument("question", help="Question to answer from indexed documents.")

    subparsers.add_parser("chat", help="Start an interactive terminal session.")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        if args.command == "check":
            command_check()
        elif args.command == "ingest":
            command_ingest()
        elif args.command == "add":
            command_add(args.file)
        elif args.command == "remove":
            command_remove(args.source)
        elif args.command == "ask":
            _ask(args.question)
        elif args.command == "chat":
            command_chat()
        return 0
    except (OllamaError, FileNotFoundError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
