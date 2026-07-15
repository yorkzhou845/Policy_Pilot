"""Command-line utilities for the local CSV vector store."""

from __future__ import annotations

import argparse
from pathlib import Path

from config import settings
from rag import add_document, rebuild_index, remove_document, retrieve


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Manage the local Policy Pilot vector store.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("rebuild", help="Rebuild the CSV index from the documents directory.")

    add_parser = subparsers.add_parser("add", help="Copy a document into the documents directory and rebuild.")
    add_parser.add_argument("path", type=Path)

    remove_parser = subparsers.add_parser("remove", help="Remove a document by filename and rebuild.")
    remove_parser.add_argument("filename")

    search_parser = subparsers.add_parser("search", help="Run retrieval without generating an answer.")
    search_parser.add_argument("query")
    search_parser.add_argument("--top-k", type=int, default=None)

    return parser


def main() -> int:
    args = build_parser().parse_args()

    if args.command == "rebuild":
        count = rebuild_index(settings)
        print(f"Indexed {count} chunks into {settings.vector_store_csv}")
        return 0

    if args.command == "add":
        count = add_document(args.path, settings)
        print(f"Document added. The rebuilt index contains {count} chunks.")
        return 0

    if args.command == "remove":
        count = remove_document(args.filename, settings)
        print(f"Document removed. The rebuilt index contains {count} chunks.")
        return 0

    if args.command == "search":
        results = retrieve(args.query, top_k=args.top_k, config=settings)
        if not results:
            print("No chunks met the similarity threshold.")
            return 0
        for index, result in enumerate(results, start=1):
            preview = " ".join(result.record.text.split())[:240]
            print(
                f"{index}. score={result.score:.4f} "
                f"source={result.record.source_file} chunk={result.record.chunk_index}\n"
                f"   {preview}"
            )
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
