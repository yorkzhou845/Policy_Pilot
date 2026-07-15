# Sanitization Report

## Scope Reviewed

The complete uploaded archive was inventoried and searched, including source files, documentation, comments, configuration, and hidden-file paths. The archive contained six visible files and no embedded documents, generated databases, environment files, Git metadata, build output, or hidden files.

## Significant Changes

- Replaced institution-specific wording with a generic document-grounded assistant prompt.
- Removed personal identifiers, slogans, hardware names, migration notes, and machine-specific path examples.
- Removed all external-server assumptions; Ollama defaults to the local loopback service.
- Replaced hard-coded Python configuration with environment variables loaded from `.env`.
- Added `.env.example` and excluded `.env` through `.gitignore`.
- Replaced the Ollama Python package dependency with a small standard-library REST client for `/api/embed`, `/api/chat`, and `/api/tags`.
- Replaced the pandas/NumPy retrieval path with standard-library CSV parsing and cosine similarity.
- Replaced the original scripts with a single CLI supporting `check`, `ingest`, `add`, `remove`, `ask`, and `chat`.
- Limited document ingestion to PDF, DOCX, TXT, and Markdown. Python source-code ingestion was removed to reduce accidental indexing of proprietary source code.
- Replaced private XML citation conventions with generic source-and-location citations plus a deterministic retrieved-source list.
- Added a fictional sample document, dependency files, unit tests, third-party notices, and comprehensive setup instructions.
- Added Git exclusions for local documents, generated vector stores, environments, caches, logs, databases, archives, and IDE files.

## Original Files Removed or Replaced

Removed from the public structure:

- `chunking.py` — replaced by `documents.py` and `vector_store.py`
- `func.py` — replaced by `ollama_client.py`, `vector_store.py`, and `rag.py`
- `manage.py` — replaced by `main.py add` and `main.py remove`
- Original `README.md` — fully replaced

Rewritten rather than retained:

- `config.py`
- `main.py`

No source documents, databases, logs, uploads, or caches were present in the submitted archive, so none required deletion.

## Configuration Values to Review

Copy `.env.example` to `.env`, then review:

- `OLLAMA_BASE_URL`
- `OLLAMA_CHAT_MODEL`
- `OLLAMA_EMBED_MODEL`
- `OLLAMA_GUARD_MODEL`
- `DOCUMENTS_DIR`
- `VECTOR_DB_CSV`
- Retrieval, chunking, context-window, batch-size, and timeout values

The default local Ollama configuration requires no API key. Do not commit `.env`.

## Remaining Concerns

- No project license is included because publication permission does not necessarily include authority to grant reuse rights.
- Model licenses are separate from the Ollama software license and must be reviewed individually.
- Any documents added by a user may contain confidential information; the ignored data directories should remain untracked.
- A public repository should also be checked for sensitive Git history before publishing. This archive did not include a `.git` directory, so prior repository history could not be reviewed or rewritten here.
- This template has no authentication, authorization, OCR, or multi-user protections and should not be treated as a production deployment without additional design work.
