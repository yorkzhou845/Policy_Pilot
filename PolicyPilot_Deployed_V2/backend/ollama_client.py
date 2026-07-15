"""Small REST client for a locally running Ollama instance."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any, Iterable


class OllamaError(RuntimeError):
    """Raised when the local Ollama API cannot complete a request."""


class OllamaClient:
    def __init__(self, base_url: str, timeout_seconds: int = 180) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds

    def _post(self, endpoint: str, payload: dict[str, Any]) -> dict[str, Any]:
        request = urllib.request.Request(
            url=f"{self.base_url}{endpoint}",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json", "Accept": "application/json"},
            method="POST",
        )

        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                raw = response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise OllamaError(f"Ollama returned HTTP {exc.code}: {detail[:500]}") from exc
        except urllib.error.URLError as exc:
            raise OllamaError(
                f"Could not connect to Ollama at {self.base_url}. "
                "Start Ollama and verify OLLAMA_BASE_URL."
            ) from exc

        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise OllamaError("Ollama returned an invalid JSON response.") from exc

        if isinstance(data, dict) and data.get("error"):
            raise OllamaError(str(data["error"]))
        return data

    def embed(self, model: str, inputs: str | Iterable[str]) -> list[list[float]]:
        input_value = inputs if isinstance(inputs, str) else list(inputs)
        data = self._post("/api/embed", {"model": model, "input": input_value})
        embeddings = data.get("embeddings")
        if not isinstance(embeddings, list) or not embeddings:
            raise OllamaError("Ollama did not return embeddings.")
        return [[float(value) for value in vector] for vector in embeddings]

    def chat(self, model: str, system_prompt: str, user_prompt: str) -> str:
        data = self._post(
            "/api/chat",
            {
                "model": model,
                "stream": False,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "options": {"temperature": 0.2},
            },
        )
        message = data.get("message")
        content = message.get("content") if isinstance(message, dict) else None
        if not isinstance(content, str) or not content.strip():
            raise OllamaError("Ollama returned an empty chat response.")
        return content.strip()
