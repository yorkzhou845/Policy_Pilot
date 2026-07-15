"""Local FastAPI service used by the Blazor frontend."""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from config import settings
from rag import answer_question, rebuild_index
from vector_store import CsvVectorStore

app = FastAPI(title="Policy Pilot Local Backend", version="1.0.0")


class AnswerRequest(BaseModel):
    question: str = Field(min_length=1, max_length=4000)
    top_k: int | None = Field(default=None, ge=1, le=20)


class CitationResponse(BaseModel):
    source_file: str
    quote: str
    score: float


class AnswerResponse(BaseModel):
    answer: str
    citations: list[CitationResponse]


@app.get("/health")
def health() -> dict[str, Any]:
    store = CsvVectorStore(settings.vector_store_csv)
    return {
        "status": "ok",
        "vector_store_ready": store.exists(),
        "chat_model": settings.chat_model,
        "embedding_model": settings.embed_model,
    }


@app.post("/ingest")
def ingest() -> dict[str, Any]:
    try:
        count = rebuild_index(settings)
        return {"status": "ok", "chunks_indexed": count}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/answer", response_model=AnswerResponse)
def answer(request: AnswerRequest) -> AnswerResponse:
    try:
        result = answer_question(request.question, top_k=request.top_k, config=settings)
        return AnswerResponse(
            answer=result.answer,
            citations=[
                CitationResponse(
                    source_file=citation.source_file,
                    quote=citation.quote,
                    score=citation.score,
                )
                for citation in result.citations
            ],
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
