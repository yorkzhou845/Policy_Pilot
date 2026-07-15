"""Small REST client for a locally running Ollama instance."""

from __future__ import annotations

import json
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class OllamaError(RuntimeError):
    """Raised when the local Ollama API cannot complete a request."""


class OllamaClient:
    def __init__(self, base_url: str, timeout_seconds: int = 180) -> None:
        normalized = base_url.rstrip("/")
        if normalized.endswith("/api"):
            normalized = normalized[:-4]
        self.base_url = normalized
        self.timeout_seconds = timeout_seconds

    def _request(
        self,
        method: str,
        path: str,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        body = None if payload is None else json.dumps(payload).encode("utf-8")
        request = Request(
            f"{self.base_url}{path}",
            data=body,
            method=method,
            headers={"Content-Type": "application/json"},
        )

        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                return json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise OllamaError(f"Ollama returned HTTP {exc.code}: {detail}") from exc
        except URLError as exc:
            raise OllamaError(
                f"Could not reach Ollama at {self.base_url}. "
                "Confirm that Ollama is installed and running locally."
            ) from exc
        except (json.JSONDecodeError, KeyError, TypeError) as exc:
            raise OllamaError("Ollama returned an unexpected response.") from exc

    def list_models(self) -> list[str]:
        response = self._request("GET", "/api/tags")
        models = response.get("models", [])
        return [str(item.get("name", "")) for item in models if item.get("name")]

    def embed(self, texts: str | list[str], model: str) -> list[list[float]]:
        response = self._request(
            "POST",
            "/api/embed",
            {"model": model, "input": texts},
        )
        embeddings = response.get("embeddings")
        if not isinstance(embeddings, list) or not embeddings:
            raise OllamaError("Ollama did not return any embeddings.")
        return embeddings

    def chat(
        self,
        model: str,
        messages: list[dict[str, str]],
        *,
        context_window: int = 8192,
        temperature: float = 0.0,
    ) -> str:
        response = self._request(
            "POST",
            "/api/chat",
            {
                "model": model,
                "messages": messages,
                "stream": False,
                "options": {
                    "temperature": temperature,
                    "num_ctx": context_window,
                },
            },
        )
        message = response.get("message", {})
        content = message.get("content") if isinstance(message, dict) else None
        if not isinstance(content, str) or not content.strip():
            raise OllamaError("Ollama did not return a chat response.")
        return content.strip()
