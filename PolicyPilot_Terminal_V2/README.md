# Local Policy RAG Assistant

A terminal-based Retrieval-Augmented Generation (RAG) template that indexes local documents, creates embeddings through a locally running Ollama API, stores embeddings in a CSV file, retrieves relevant chunks with cosine similarity, and asks a local Ollama chat model to answer with source citations.

The public version is organization-neutral. It contains no workplace documents, credentials, server addresses, workplace authentication integration, production data, generated embeddings, or company branding.

## Architecture

```text
Local documents (PDF, DOCX, TXT, MD)
        |
        v
Document parser and chunker
        |
        v
Ollama /api/embed
        |
        v
Local CSV vector store
        |
        v
Cosine-similarity retrieval
        |
        v
Ollama /api/chat
        |
        v
Terminal answer with retrieved sources
```

This repository has no separate web frontend or remote backend. `main.py` is the terminal interface, and the locally running Ollama process supplies the model API.

## Technology Stack

- Python 3.10 or newer
- Ollama running on the same computer by default
- `pypdf` for text extraction from searchable PDFs
- `python-docx` for DOCX extraction
- `python-dotenv` for local environment configuration
- Python standard-library CSV, JSON, HTTP, and math modules

## Project Structure

```text
.
├── config.py                 # Environment-based settings
├── documents.py              # File parsing and text chunking
├── main.py                   # Command-line interface
├── ollama_client.py          # Local Ollama REST client
├── rag.py                    # Prompt assembly and answer generation
├── vector_store.py           # CSV storage and cosine retrieval
├── .env.example              # Safe example configuration
├── .gitignore                # Excludes local data, secrets, and generated files
├── requirements.txt          # Runtime dependencies
├── requirements-dev.txt      # Test dependencies
├── examples/
│   └── sample_policy.txt     # Fictional test document
├── data/
│   ├── documents/            # Your local documents; ignored by Git
│   └── vector_store/         # Generated CSV; ignored by Git
└── tests/                    # Unit tests that do not require Ollama
```

## Prerequisites

1. Install Python 3.10 or newer.
2. Install Ollama locally and ensure its service is running.
3. Pull one chat model and one embedding model. The example configuration uses:

```bash
ollama pull llama3.2:3b
ollama pull embeddinggemma
```

Model availability, hardware requirements, and license terms vary. Replace these model names with local models appropriate for your computer and intended use.

## Installation

### Windows PowerShell

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

### macOS or Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
cp .env.example .env
```

## Configuration

Edit `.env`. Do not commit it.

| Variable | Purpose | Example |
|---|---|---|
| `OLLAMA_BASE_URL` | Local Ollama service address | `http://localhost:11434` |
| `OLLAMA_CHAT_MODEL` | Locally installed generation model | `llama3.2:3b` |
| `OLLAMA_EMBED_MODEL` | Locally installed embedding model | `embeddinggemma` |
| `OLLAMA_GUARD_MODEL` | Optional safety model; blank disables it | blank |
| `DOCUMENTS_DIR` | Directory containing authorized source documents | `data/documents` |
| `VECTOR_DB_CSV` | Generated local CSV vector store | `data/vector_store/vectors.csv` |
| `TOP_K` | Number of chunks retrieved per question | `5` |
| `MAX_CHUNK_CHARS` | Approximate maximum characters per chunk | `4000` |
| `CHUNK_OVERLAP_CHARS` | Repeated characters between adjacent chunks | `400` |
| `MAX_CONTEXT_CHARS` | Maximum retrieved text sent to the chat model | `16000` |
| `OLLAMA_CONTEXT_WINDOW` | Requested chat-model context window | `8192` |
| `EMBED_BATCH_SIZE` | Documents chunks embedded per API request | `16` |
| `OLLAMA_TIMEOUT_SECONDS` | Local API request timeout | `180` |

A standard local Ollama installation does not require an API key. This project intentionally contains no API-key field for local use. Do not change `OLLAMA_BASE_URL` to a workplace or cloud endpoint unless you have separately reviewed authentication, confidentiality, and licensing requirements.

## Local Setup and Test

1. Copy the fictional example document into the ignored document directory:

```bash
cp examples/sample_policy.txt data/documents/
```

On PowerShell:

```powershell
Copy-Item examples\sample_policy.txt data\documents\
```

2. Confirm Ollama and the configured models are available:

```bash
python main.py check
```

3. Build the CSV vector store:

```bash
python main.py ingest
```

4. Ask one question:

```bash
python main.py ask "How long is the standard equipment checkout period?"
```

5. Start an interactive terminal session:

```bash
python main.py chat
```

Type `exit`, `quit`, or `bye` to stop.

## Index Maintenance

Rebuild the full index after changing documents or the embedding model:

```bash
python main.py ingest
```

Add or replace one document by filename:

```bash
python main.py add path/to/document.pdf
```

Remove a stored source using its exact source name:

```bash
python main.py remove document.pdf
```

When the full index is built from nested directories, the source name is stored as a relative path such as `department/document.pdf`.

## Automated Tests

The unit tests use a fake embedding client and do not require Ollama:

```bash
python -m pip install -r requirements-dev.txt
pytest
```

A successful unit-test run verifies chunking, CSV creation, embedding serialization, and retrieval. The manual steps above provide the local Ollama integration test.

## Supported Documents

- Searchable PDF
- DOCX
- UTF-8 text
- Markdown

Scanned or image-only PDFs require OCR before ingestion. OCR is intentionally not included.

## Public-Version Changes

The public template was rewritten to remove or generalize:

- Organization names, slogans, branding, and organization-specific assistant prompts
- Personal names and workstation-specific paths
- Hardware- and server-specific deployment instructions
- External-server assumptions and remote connectivity
- Internal authentication and identity-provider integration
- Organization policy filenames, documents, datasets, and generated vectors
- XML citation formatting intended for a separate private user interface
- Large machine-specific model defaults

The core workflow remains: local document ingestion, Ollama embeddings, CSV storage, similarity retrieval, Ollama answer generation, and source attribution.

## Files That Must Not Be Committed

The included `.gitignore` excludes:

- `.env` and other local environment files
- Virtual environments and Python caches
- Documents placed under `data/documents/`
- Generated vector CSV files under `data/vector_store/`
- Logs, local output, databases, IDE settings, and ZIP archives

Before every public push, review `git status` and scan the complete repository, including hidden files and Git history. `.gitignore` prevents future additions but does not remove sensitive material already committed in history.

## Known Limitations

- CSV retrieval loads the full index into memory and is intended for small or moderate collections.
- The project has no OCR, reranker, web interface, user authentication, access control, or multi-user isolation.
- PDF extraction quality depends on the PDF's embedded text structure.
- Citation wording is generated by the model; the CLI also prints the retrieved sources deterministically.
- Files with the same basename can replace one another when added individually.
- Changing the embedding model requires rebuilding the entire CSV.
- Local model output can still be incomplete or incorrect; verify answers against the source documents.

## Licensing and Redistribution

No project license is included. Permission to publish workplace-derived code does not automatically establish the right to grant broad reuse rights. Add an open-source license only after confirming that you own or are authorized to license every part of the rewritten project.

This repository does not bundle Ollama, model weights, or Python dependencies. Those components have separate licenses and terms. Review the licenses for Ollama, each selected model, and each dependency before commercial use or redistribution. Do not add workplace logos, templates, documents, or other assets unless you have explicit redistribution rights.

See `THIRD_PARTY_NOTICES.md` and `SANITIZATION_REPORT.md` for the review summary.
