"""
backend_bridge.py

Thin JSON bridge used by the Blazor app. It calls the Python GB-10 / GB10
logic without changing the Blazor UI.
"""

import argparse
import json
import os
import sys


def _json_print(payload):
    print(json.dumps(payload, ensure_ascii=False))


def answer_mode(content_root):
    if content_root:
        os.environ["POLICY_PILOT_CONTENT_ROOT"] = content_root

    raw_input = sys.stdin.read().strip()
    payload = json.loads(raw_input) if raw_input else {}
    question = str(payload.get("question", "")).strip()
    runtime_context = payload.get("runtimeContext") or payload.get("runtime_context") or {}

    if not question:
        _json_print({"answer": "Please enter a policy question."})
        return 0

    from main import get_answer

    answer = get_answer(question, runtime_context=runtime_context)
    _json_print({"answer": answer})
    return 0


def ingest_mode(content_root):
    if content_root:
        os.environ["POLICY_PILOT_CONTENT_ROOT"] = content_root

    # GB10 already has the vector database preloaded. The Blazor app keeps this
    # mode so `dotnet run -- --ingest` does not crash, but it no longer builds a
    # local App_Data/chroma_db database.
    print(
        "Local ingestion skipped. The app uses the remote GB10 /retrieve-context vector database.",
        file=sys.stderr,
    )

    _json_print({
        "status": "ok",
        "message": "Local ingestion skipped. Remote GB10 vector database is used."
    })
    return 0


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["answer", "ingest"], required=True)
    parser.add_argument("--content-root", default="")
    args = parser.parse_args()

    try:
        if args.mode == "answer":
            return answer_mode(args.content_root)
        if args.mode == "ingest":
            return ingest_mode(args.content_root)
        raise ValueError(f"Unsupported mode: {args.mode}")
    except Exception as exc:
        _json_print({"error": str(exc)})
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
