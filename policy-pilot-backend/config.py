"""
config.py

GB-10 / GB10 configuration for the Policy_Pilot_P2 Blazor app.

The Blazor UI still calls the Python backend through backend_bridge.py.
The local Chroma DB path is no longer used for active retrieval because GB10
already hosts the vector database behind /retrieve-context.
"""

import os
from pathlib import Path


# -----------------------------
# Project-relative locations
# -----------------------------

def _default_content_root():
    # This file lives in: <project>/App_Data/GB10_Chroma/config.py
    return Path(__file__).resolve().parents[2]


CONTENT_ROOT = Path(
    os.getenv("POLICY_PILOT_CONTENT_ROOT")
    or _default_content_root()
)

# Kept for compatibility with the older local-ingestion files. The active app
# no longer reads local policy files for retrieval.
POLICY_SOURCE_FOLDER = os.getenv(
    "POLICY_SOURCE_FOLDER",
    str(CONTENT_ROOT / "wwwroot" / "Data"),
)

# Kept for compatibility only. Active retrieval now uses DB10_RETRIEVE_CONTEXT_URL.
CHROMA_DB_DIR = os.getenv(
    "CHROMA_DB_DIR",
    str(CONTENT_ROOT / "App_Data" / "chroma_db"),
)

CHROMA_COLLECTION_NAME = os.getenv("CHROMA_COLLECTION_NAME", "ttu_policies")

NEW_POLICIES_FOLDER = os.getenv(
    "NEW_POLICIES_FOLDER",
    str(CONTENT_ROOT / "App_Data" / "New_Policies"),
)

VECTOR_DB_CSV = os.getenv(
    "VECTOR_DB_CSV",
    str(CONTENT_ROOT / "App_Data" / "Vector_db" / "vector_db.csv"),
)


# -----------------------------
# GB-10 Ollama settings
# -----------------------------

OLLAMA_HOST = os.getenv("GB10_OLLAMA_HOST", "http://66.230.43.54/ollama")
OLLAMA_API_KEY = os.getenv("GB10_OLLAMA_API_KEY")

GUARD_MODEL = os.getenv("GB10_GUARD_MODEL", "llama-guard3:8b")
GEN_MODEL = os.getenv("GB10_GEN_MODEL", "llama3.1:8b")

# Kept for compatibility/debugging. Active retrieval no longer embeds the query
# locally because GB10 does retrieval.
EMB_MODEL = os.getenv("GB10_EMB_MODEL", "embeddinggemma:300m")


# -----------------------------
# Remote GB10 retrieval settings
# -----------------------------

RETRIEVE_CONTEXT_URL = os.getenv(
    "DB10_RETRIEVE_CONTEXT_URL",
    "http://66.230.43.54:8085/retrieve-context",
)

# Your current curl example does not need this, but this keeps the app ready if
# the retrieval endpoint later requires an API key.
RETRIEVE_CONTEXT_API_KEY = os.getenv("DB10_RETRIEVE_CONTEXT_API_KEY", "")


# -----------------------------
# Context / generation settings
# -----------------------------

GEN_CONTEXT_WINDOW = int(os.getenv("GB10_GEN_CONTEXT_WINDOW", "32768"))
GEN_TOKEN_MAX = int(os.getenv("GB10_GEN_TOKEN_MAX", str(GEN_CONTEXT_WINDOW - 1500)))
K = int(os.getenv("GB10_TOP_K", "8"))

expected_dim = os.getenv("GB10_EXPECTED_EMBEDDING_DIM")
EXPECTED_EMBEDDING_DIM = int(expected_dim) if expected_dim else None

MAX_CHUNK_TOKENS = int(os.getenv("GB10_MAX_CHUNK_TOKENS", "1500"))
