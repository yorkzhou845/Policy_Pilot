#%%
import json
import urllib.error
import urllib.request

from config import (
    EXPECTED_EMBEDDING_DIM,
    RETRIEVE_CONTEXT_API_KEY,
    RETRIEVE_CONTEXT_URL,
)
from ollama_client import ollama_client


#%%

def get_embedding(text, emb_model="embeddinggemma:300m"):
    """
    Kept for compatibility/debugging only.

    The active app no longer needs to create a local query embedding because
    retrieval is now handled by GB10's /retrieve-context endpoint.
    """
    response = ollama_client.embed(
        model=emb_model,
        input=text
    )

    embedding = response.embeddings[0]

    if EXPECTED_EMBEDDING_DIM is not None and len(embedding) != EXPECTED_EMBEDDING_DIM:
        raise ValueError(
            f"Embedding dimension mismatch. "
            f"Expected {EXPECTED_EMBEDDING_DIM}, got {len(embedding)}."
        )

    return embedding


def token_count(text, model=None):
    """
    Approximate token count.

    This keeps the code model-agnostic for local/remote Ollama models. The
    approximation is conservative enough for prompt budgeting in this project.
    """
    if text is None:
        return 0

    return max(1, len(str(text)) // 4)


def _post_json(url, payload, headers=None, timeout=60):
    """
    Small stdlib JSON POST helper so the app does not require requests.
    Equivalent to:
      curl -X POST <url> -H "Content-Type: application/json" -d '{...}'
    """
    body = json.dumps(payload).encode("utf-8")

    request_headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    if headers:
        request_headers.update(headers)

    request = urllib.request.Request(
        url=url,
        data=body,
        headers=request_headers,
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        error_body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(
            f"GB10 retrieval request failed with HTTP {exc.code}: {error_body}"
        ) from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(
            f"Could not connect to GB10 retrieval endpoint at {url}: {exc.reason}"
        ) from exc

    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            f"GB10 retrieval endpoint returned non-JSON output: {raw[:1000]}"
        ) from exc


def extract_matches_from_remote_response(data):
    """
    The current GB10 response shape is:
      {"matches": [{"source": "op5602.pdf", "text": "..."}]}

    The fallbacks make the parser tolerant if the endpoint later uses names
    like results/chunks/documents/context instead of matches.
    """
    if isinstance(data, list):
        return data

    if not isinstance(data, dict):
        return [str(data)]

    for key in ["matches", "results", "chunks", "documents", "context", "data"]:
        value = data.get(key)
        if isinstance(value, list):
            return value

    return [data]


def normalize_remote_match(item, index):
    """
    Convert one retrieved GB10 match into the internal text block expected by
    the existing generation prompt.
    """
    fallback_source = f"remote_chunk_{index + 1}"

    if isinstance(item, str):
        source = fallback_source
        text = item
    elif isinstance(item, dict):
        metadata = item.get("metadata") or {}

        source = (
            item.get("source")
            or item.get("file_name")
            or item.get("filename")
            or item.get("source_file")
            or metadata.get("source")
            or metadata.get("file_name")
            or metadata.get("filename")
            or fallback_source
        )

        text = (
            item.get("text")
            or item.get("content")
            or item.get("document")
            or item.get("chunk")
            or item.get("page_content")
            or ""
        )

        if not text:
            text = json.dumps(item, ensure_ascii=False)
    else:
        source = fallback_source
        text = str(item)

    source = str(source).strip() or fallback_source
    text = str(text).strip()

    citation_quote = " ".join(text.split())[:300]

    return f"""
SOURCE_FILE: {source}
POLICY_CHUNK:
{text}
CITATION_XML_TO_COPY:
<citation filename='{source}'>{citation_quote}</citation>
""".strip()


def retrieve_context_chunks(user_query, k=8):#ask GB10 to retreve top k
    """
    Retrieve top-k context chunks from GB10's preloaded vector database.

    This replaces local Chroma lookup. It is equivalent to this command:
      curl -X POST http://66.230.43.54:8085/retrieve-context \
        -H "Content-Type: application/json" \
        -d "{\"user_query\": \"...\", \"n_results\": 2}"
    """
    headers = {}

    if RETRIEVE_CONTEXT_API_KEY:
        headers["X-API-KEY"] = RETRIEVE_CONTEXT_API_KEY

    payload = {
        "user_query": user_query,
        "n_results": int(k),
    }

    data = _post_json(
        url=RETRIEVE_CONTEXT_URL,
        payload=payload,
        headers=headers,
        timeout=60,
    )

    matches = extract_matches_from_remote_response(data)

    chunks = [
        normalize_remote_match(item, index)
        for index, item in enumerate(matches)
    ]

    if not chunks:
        raise RuntimeError("GB10 retrieval returned no context chunks.")

    return chunks


def set_user_prompt(
        chunks,
        user_question,
        user_instruction,
        gen_model,
        max_gen_token
        ):
    message = user_instruction + "\n\nRetrieved policy chunks:"

    for string in chunks:
        next_section = "\n\n'''\n" + string + "\n'''"

        if token_count(message + next_section, gen_model) > max_gen_token:
            break
        else:
            message += next_section

    user_prompt = message + "\n\nAnswer this user's question: " + user_question

    return user_prompt

# %%
