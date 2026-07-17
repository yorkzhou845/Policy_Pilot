"""
backend_server.py

Runs the Policy Pilot Python backend as a small HTTP service on the GB10 server.
The Blazor app should call this service instead of starting Python locally.

Endpoints:
  GET  /health
  POST /answer   body: {"question": "...", "runtimeContext": {...}}
  POST /ingest   no-op compatibility endpoint
"""

import os
from typing import Any, Dict, Optional

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel

from main import get_answer


class AnswerRequest(BaseModel):
    question: str
    runtimeContext: Optional[Dict[str, Any]] = None


app = FastAPI(title="Policy Pilot GB10 Backend")


def _check_api_key(x_api_key: Optional[str]) -> None:
    expected = os.getenv("POLICY_PILOT_BACKEND_API_KEY", "").strip()

    # If no key is configured, the backend allows requests. Use this only for
    # initial testing or when the firewall restricts access to the web server.
    if not expected:
        return

    if not x_api_key or x_api_key.strip() != expected:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")


@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok"}


@app.post("/answer")
def answer(request: AnswerRequest, x_api_key: Optional[str] = Header(default=None)) -> Dict[str, str]:
    _check_api_key(x_api_key)

    question = (request.question or "").strip()
    if not question:
        return {"answer": "Please enter a policy question."}

    try:
        response = get_answer(question, runtime_context=request.runtimeContext or {})
        return {"answer": response}
    except Exception as exc:
        return {"error": str(exc)}


@app.post("/ingest")
def ingest(x_api_key: Optional[str] = Header(default=None)) -> Dict[str, str]:
    _check_api_key(x_api_key)

    return {
        "status": "ok",
        "message": "Local ingestion skipped. The GB10 backend uses the existing remote retrieval database.",
    }
