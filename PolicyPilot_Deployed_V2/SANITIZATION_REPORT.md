# Sanitization Report

## Scope

The complete uploaded archive was reviewed, including source code, configuration, documentation, duplicated backend files, build output, Visual Studio metadata, JavaScript assets, and hidden directories.

## Significant changes

1. Replaced remote infrastructure with a local-only architecture.
   - The Python backend now calls Ollama at a configurable local URL.
   - Query embeddings are generated locally.
   - Retrieval uses cosine similarity against a local CSV file.
   - The Blazor frontend calls a local FastAPI service.

2. Removed secrets and identifying infrastructure.
   - Removed embedded authentication credentials and backend API keys.
   - Removed public and private remote IP addresses, internal domains, internal URLs, server names, usernames, and user-specific filesystem paths.
   - Removed internal repository, deployment, and service configuration references.

3. Removed workplace-only authentication and branding.
   - Removed the internal SSO package, authentication handlers, login/logout pages, and authentication notes.
   - Removed the institutional template package, remote header/footer fragments, branded styles, external institutional assets, and location-specific content.

4. Replaced the data layer.
   - Removed Chroma and SQLite vector-database dependencies.
   - Added a transparent CSV schema containing chunk metadata, text, and JSON-encoded embeddings.
   - Added atomic CSV writes and an offline cosine-similarity search implementation.

5. Simplified the application.
   - Replaced the complex chat component set with a small Blazor page and typed HTTP client.
   - Removed unused ingestion abstractions, guard-model logic, remote adapters, compatibility shims, and duplicate code.
   - Removed vendored PDF/Markdown viewers and signed generated JavaScript assets.

6. Added public-template documentation and safeguards.
   - Added root `README.md`, `.env.example`, `appsettings.example.json`, `.gitignore`, unit tests, licensing guidance, and this report.
   - Added a fictional example document for end-to-end testing.
   - Configured Git to ignore real local documents and generated CSV data.

## Original files and directories removed

The sanitized project was rebuilt into a new clean directory. The following original items were intentionally not carried forward:

- `frontend/.vs/` and all Visual Studio caches and user state
- `frontend/Policy Pilot P2/bin/`
- `frontend/Policy Pilot P2/obj/`
- `frontend/Policy Pilot P2/Policy Pilot P2.csproj.user`
- `frontend/Changes summary.txt`
- `frontend/Policy Pilot P2/AUTHENTICATION_DEMO_PATTERN_NOTES.md`
- `frontend/Policy Pilot P2/HscAuthOptions.cs`
- `frontend/Policy Pilot P2/WebConstants.cs`
- `frontend/Policy Pilot P2/Pages/Account/`
- `frontend/Policy Pilot P2/Pages/ExternalLogIn.cshtml`
- `frontend/Policy Pilot P2/Pages/ExternalLogIn.cshtml.cs`
- `frontend/Policy Pilot P2/Components/Layout/RedirectToLogin.razor`
- `frontend/Policy Pilot P2/Components/Pages/AccessDenied.razor`
- `frontend/Policy Pilot P2/Components/Pages/LogOut.razor`
- `frontend/Policy Pilot P2/Components/Documents.razor`
- Original remote-backend HTTP service adapter
- `frontend/Policy Pilot P2/Services/Ingestion/`
- `frontend/Policy Pilot P2/Services/IngestedChunk.cs`
- `frontend/Policy Pilot P2/Services/SemanticSearch.cs`
- Original duplicated Python backend stored under the frontend data directory
- Original institutional `appsettings.json` and `launchSettings.json`
- Original branded layout, authentication routes, and company-specific chat prompt
- `frontend/Policy Pilot P2/wwwroot/lib/` vendored browser libraries and document viewers
- Original `frontend/Policy Pilot P2/wwwroot/app.js` containing a generated signature block
- `backend/chroma_store.py`
- Original remote versions of `backend/config.py`, `backend/func.py`, `backend/main.py`, `backend/backend_bridge.py`, and `backend/backend_server.py`
- Original deployment-focused backend README content and server service examples

## New configuration values to review

These values are safe defaults but should be reviewed for each machine:

- `OLLAMA_BASE_URL`
- `OLLAMA_CHAT_MODEL`
- `OLLAMA_EMBED_MODEL`
- `POLICY_DOCUMENTS_DIR`
- `VECTOR_STORE_CSV`
- `TOP_K`
- `MIN_SIMILARITY`
- `CHUNK_SIZE_CHARS`
- `CHUNK_OVERLAP_CHARS`
- `MAX_CONTEXT_CHARS`
- `OLLAMA_TIMEOUT_SECONDS`
- `LocalBackend__BaseUrl`

## Remaining concerns

1. Credentials found in the original archive should be treated as exposed. Revoke or rotate them even though they were removed from this sanitized copy.
2. Do not copy the old Git history into the public repository. Create a new repository from the sanitized folder, or use a history-rewriting tool and verify every historical commit.
3. Confirm employer authorization covers the remaining general architecture and code, not only the absence of secrets.
4. Review the licenses of all Python and .NET dependencies before public release. Dependencies are not relicensed by this repository.
5. Confirm that every document added for demonstrations is synthetic, public-domain, or otherwise authorized for redistribution.
6. The local backend has no authentication. Keep it on the loopback interface for development.
7. The generated CSV stores source text as well as embeddings and must be protected like the documents from which it was generated.
