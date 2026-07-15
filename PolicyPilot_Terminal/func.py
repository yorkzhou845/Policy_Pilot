#%%
import json

import numpy as np
import ollama
import pandas as pd

from config import EXPECTED_EMBEDDING_DIM

#%%

def get_embedding(text, emb_model="embeddinggemma:300m"):
    response = ollama.embed(
        model=emb_model,
        input=text
    )

    embedding = response.embeddings[0]

    if EXPECTED_EMBEDDING_DIM is not None and len(embedding) != EXPECTED_EMBEDDING_DIM:
        raise ValueError(
            f"Embedding dimension mismatch. "
            f"Expected {EXPECTED_EMBEDDING_DIM}, got {len(embedding)}. "
            f"Check your embedding model or rebuild the vector database."
        )

    return embedding


def cos_sim(question, answer):
    q = np.array(question, dtype=float)
    a = np.array(answer, dtype=float)

    if len(q) != len(a):
        return -1

    if np.linalg.norm(q) == 0 or np.linalg.norm(a) == 0:
        return -1

    cosine = float(np.dot(q, a) / (np.linalg.norm(q) * np.linalg.norm(a)))
    return cosine


def parse_embedding(value):
    """
    CSV stores embeddings as JSON strings.
    Convert the string back into a list of floats.
    """
    if isinstance(value, list):
        return value

    if isinstance(value, np.ndarray):
        return value.tolist()

    try:
        return json.loads(value)
    except Exception as exc:
        raise ValueError(f"Could not parse embedding from vector database: {value}") from exc


def build_retrieved_chunk_text(row):
    """
    Return a chunk in a format the generation prompt can cite.
    The old code only passed raw content, even though the prompt required filenames.
    """
    file_name = str(row.get("file_name", "unknown_source"))
    content = str(row.get("content", ""))

    citation_quote = " ".join(content.split())[:300]

    return f"""
SOURCE_FILE: {file_name}
POLICY_CHUNK:
{content}
CITATION_XML_TO_COPY:
<citation filename='{file_name}'>{citation_quote}</citation>
""".strip()


def get_topk_chunk(user_vector, vector_db, k):
    if vector_db is None:
        raise ValueError(
            "Vector database path is blank. Fill VECTOR_DB_CSV in config.py before running the app."
        )

    df = pd.read_csv(vector_db)

    if "embedding" not in df.columns:
        raise ValueError("Vector database is missing the required 'embedding' column.")

    user_dim = len(user_vector)

    df["embedding"] = df["embedding"].apply(parse_embedding)
    df["embedding_dim_actual"] = df["embedding"].apply(len)

    compatible_df = df[df["embedding_dim_actual"] == user_dim].copy()

    if compatible_df.empty:
        stored_dims = sorted(df["embedding_dim_actual"].dropna().unique().tolist())
        raise ValueError(
            f"No compatible embeddings found in the vector database. "
            f"Question embedding dimension is {user_dim}; stored dimensions are {stored_dims}. "
            f"Rebuild the vector database with the current embedding model."
        )

    compatible_df["embedding"] = compatible_df["embedding"].apply(np.array)

    # Compare each document chunk embedding against the user's question vector.
    compatible_df["similarity"] = compatible_df["embedding"].apply(
        lambda x: cos_sim(x, user_vector)
    )

    # Sort from most similar to least similar.
    compatible_df = compatible_df.sort_values("similarity", ascending=False)

    # Return the top k chunks, including source file names and citation tags.
    top_rows = compatible_df.head(k)
    chunks = [build_retrieved_chunk_text(row) for _, row in top_rows.iterrows()]

    return chunks


def token_count(text, model=None):
    """
    Approximate token count.

    This keeps the code model-agnostic for local Ollama models. The approximation
    is conservative enough for chunking/prompt budgeting in this project.
    """
    if text is None:
        return 0

    return max(1, len(str(text)) // 4)


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
