from ollama import Client

from config import OLLAMA_API_KEY, OLLAMA_HOST


if not OLLAMA_API_KEY:
    raise RuntimeError(
        "GB10_OLLAMA_API_KEY is not set. "
        "Set it in PowerShell before running the app."
    )


ollama_client = Client(
    host=OLLAMA_HOST,
    headers={
        "X-API-KEY": OLLAMA_API_KEY
    }
)