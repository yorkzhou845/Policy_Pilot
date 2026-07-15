# Policy Pilot Local

Policy Pilot Local is a reusable, document-grounded question-answering template. It ingests local PDF, DOCX, Markdown, and text files; creates embeddings with a locally running Ollama instance; stores document chunks and embeddings in a CSV file; retrieves relevant chunks with cosine similarity; and generates source-grounded answers through an Ollama chat model.

This repository is a sanitized public template. It contains no workplace authentication, institutional branding, internal infrastructure, production data, or proprietary policy documents.

## Architecture

```text
Browser
  -> ASP.NET Core Blazor frontend
  -> local FastAPI backend (127.0.0.1)
  -> CSV vector store + local source documents
  -> local Ollama REST API for embeddings and answer generation
```

### Technology stack

- Frontend: ASP.NET Core Blazor Web App targeting .NET 8
- Backend: Python 3.10+ and FastAPI
- LLM runtime: Ollama running locally
- Embeddings: configurable Ollama embedding model
- Retrieval: cosine similarity implemented in Python
- Vector storage: local CSV file
- Supported source files: `.pdf`, `.docx`, `.txt`, and `.md`

## Prerequisites

Install the following before setup:

1. .NET 8 SDK
2. Python 3.10 or newer
3. Ollama
4. At least one Ollama chat model and one embedding model

Example model setup:

```bash
ollama pull llama3.2:3b
ollama pull embeddinggemma
```

Ollama must be running before ingestion or question answering. Its default local API address is `http://localhost:11434`.

## Repository layout

```text
backend/
  backend_server.py       Local FastAPI service
  config.py               Environment-based configuration
  document_loader.py      File extraction and chunking
  ollama_client.py        Direct calls to the local Ollama REST API
  rag.py                  Retrieval-augmented generation pipeline
  vector_store.py         CSV persistence and cosine search
  manage.py               Command-line ingestion and search utility
  data/documents/         Local source documents
  data/vector_store/      Generated CSV vector store (ignored by Git)
  tests/                  Offline unit tests
frontend/PolicyPilot.Web/
  Components/             Blazor UI
  Services/               Local backend client
SANITIZATION_REPORT.md    Detailed migration and removal report
LICENSE_GUIDANCE.md       Publication and third-party licensing cautions
```

## Backend setup

From the repository root:

### Windows PowerShell

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

### macOS or Linux

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
cp .env.example .env
```

The provided `.env.example` uses local defaults. Edit `.env` when using different model names or directories.

## Configuration

The backend reads these environment variables. Relative paths are resolved from the `backend` directory.

| Variable | Default | Purpose |
|---|---|---|
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Local Ollama API address |
| `OLLAMA_CHAT_MODEL` | `llama3.2:3b` | Model used to generate answers |
| `OLLAMA_EMBED_MODEL` | `embeddinggemma` | Model used for document and query embeddings |
| `POLICY_DOCUMENTS_DIR` | `data/documents` | Directory containing source documents |
| `VECTOR_STORE_CSV` | `data/vector_store/vector_store.csv` | Generated CSV vector store |
| `TOP_K` | `5` | Number of chunks retrieved per question |
| `MIN_SIMILARITY` | `0.20` | Minimum cosine-similarity score |
| `CHUNK_SIZE_CHARS` | `2400` | Approximate chunk size |
| `CHUNK_OVERLAP_CHARS` | `250` | Character overlap between chunks |
| `MAX_CONTEXT_CHARS` | `14000` | Maximum retrieved context sent to the chat model |
| `OLLAMA_TIMEOUT_SECONDS` | `180` | HTTP timeout for local Ollama calls |

The frontend reads:

| Setting | Default | Purpose |
|---|---|---|
| `LocalBackend:BaseUrl` or `LocalBackend__BaseUrl` | `http://127.0.0.1:8000` | Local Python backend address |

`frontend/PolicyPilot.Web/appsettings.json` is safe to commit. Use environment variables or an ignored `appsettings.*.local.json` file for machine-specific overrides.

## Add documents and build the CSV vector store

A fictional `example_policy.md` is included for testing. Replace it locally with your own authorized documents. The `.gitignore` prevents additional files in `backend/data/documents` from being committed.

Build or rebuild the vector store:

```bash
cd backend
python manage.py rebuild
```

The command extracts text, chunks each document, requests embeddings from Ollama, and writes `data/vector_store/vector_store.csv`.

When the embedding model changes, rebuild the CSV. Stored vectors from one embedding model should not be queried with a different model.

Optional maintenance commands:

```bash
python manage.py add /path/to/document.pdf
python manage.py remove document.pdf
python manage.py search "How long are records retained?" --top-k 5
```

## Run the backend

From `backend` with the virtual environment active:

```bash
uvicorn backend_server:app --host 127.0.0.1 --port 8000 --reload
```

Verify it:

```bash
curl http://127.0.0.1:8000/health
```

Rebuild the index through the API when needed:

```bash
curl -X POST http://127.0.0.1:8000/ingest
```

Ask a question directly:

```bash
curl -X POST http://127.0.0.1:8000/answer \
  -H "Content-Type: application/json" \
  -d '{"question":"How long should approved requests be retained?"}'
```

## Run the frontend

Open a second terminal from the repository root:

```bash
dotnet restore frontend/PolicyPilot.Web/PolicyPilot.Web.csproj
dotnet run --project frontend/PolicyPilot.Web/PolicyPilot.Web.csproj
```

Open the local URL shown by `dotnet run`. The frontend expects the Python backend at `http://127.0.0.1:8000` unless overridden.

## Local testing

Backend unit tests do not call Ollama:

```bash
cd backend
python -m unittest discover -s tests -v
```

End-to-end test sequence:

1. Start Ollama.
2. Confirm the configured chat and embedding models are installed.
3. Activate the backend virtual environment.
4. Run `python manage.py rebuild`.
5. Start the backend with Uvicorn.
6. Confirm `/health` reports `vector_store_ready: true`.
7. Send a question to `/answer` and confirm the response contains an answer and retrieved source records.
8. Start the Blazor frontend.
9. Submit a question in the browser and confirm the answer and retrieved sources render.
10. Stop Ollama temporarily and confirm the app returns a clear local-connection error rather than using an external service.

## Generalized or removed workplace features

- Removed institutional SSO and all authentication packages and pages.
- Removed institutional header, footer, colors, templates, domains, and branding.
- Removed hard-coded remote server addresses, API keys, secrets, and user-specific paths.
- Replaced the remote vector-retrieval service with local CSV cosine search.
- Replaced remote Ollama access with the local Ollama REST API.
- Removed Chroma, SQLite vector extensions, internal packages, deployment service files, and server-specific instructions.
- Removed proprietary documents and included one fictional example document.
- Removed generated binaries, IDE state, cached files, and duplicate backend copies.
- Simplified the UI and removed the organization-specific campus selector.

See `SANITIZATION_REPORT.md` for the detailed removal and replacement list.

## Files that must not be committed

Do not commit:

- `.env` or other machine-specific configuration files
- Real workplace or customer documents
- `backend/data/vector_store/vector_store.csv`
- Logs, uploaded files, cached data, model files, virtual environments, build output, or IDE metadata
- Any screenshots or documentation containing internal branding or infrastructure

The generated CSV contains document text and embeddings. Treat it as sensitive whenever the indexed source documents are sensitive.

## Known limitations

- CSV retrieval loads vectors into memory for each search. It is appropriate for a portfolio project or modest document collection, not a large production corpus.
- PDF extraction quality depends on whether the PDF contains usable text. Scanned PDFs require a separate OCR step, which is not included.
- The application has no user authentication because it is intended for local development. Keep the backend bound to `127.0.0.1` unless you add appropriate deployment controls.
- Answer quality depends on the selected models, document quality, chunking settings, and retrieval threshold.
- Retrieved-source cards show the chunks selected by similarity. They are evidence supplied to the model, not an independent guarantee that every generated statement is correct.

## Licensing and publication

No known employer-owned assets or internal packages are intentionally included in this sanitized version. No project-wide open-source license has been selected automatically. Confirm that you have the right to publish the remaining original code, then choose a license appropriate for your intended use. Dependencies remain governed by their own licenses. See `LICENSE_GUIDANCE.md`.
