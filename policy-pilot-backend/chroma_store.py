from pathlib import Path

import chromadb

from config import CHROMA_COLLECTION_NAME, CHROMA_DB_DIR


def get_chroma_client():
    """
    Create a local persistent Chroma client.

    This stores the Chroma database files on your Windows machine in CHROMA_DB_DIR.
    It does not send your vector database to Pinecone or Chroma Cloud.
    """
    if not CHROMA_DB_DIR:
        raise ValueError("CHROMA_DB_DIR is blank. Fill it in config.py before running the app.")

    chroma_path = Path(CHROMA_DB_DIR)
    chroma_path.mkdir(parents=True, exist_ok=True)

    return chromadb.PersistentClient(path=str(chroma_path))


def get_chroma_collection(reset=False):
    """
    Return the local Chroma collection used by the RAG pipeline.

    embedding_function=None is intentional because this project already creates
    embeddings with Ollama through get_embedding(...). Therefore every add/query
    call must pass embeddings/query_embeddings explicitly.
    """
    if not CHROMA_COLLECTION_NAME:
        raise ValueError("CHROMA_COLLECTION_NAME is blank. Fill it in config.py.")

    client = get_chroma_client()

    if reset:
        try:
            client.delete_collection(name=CHROMA_COLLECTION_NAME)
        except Exception:
            # Collection may not exist yet. That is fine for a rebuild.
            pass

    # Current Chroma versions use configuration={"hnsw": {"space": "cosine"}}.
    # The fallback keeps this project usable with older Chroma versions.
    try:
        return client.get_or_create_collection(
            name=CHROMA_COLLECTION_NAME,
            embedding_function=None,
            configuration={"hnsw": {"space": "cosine"}},
        )
    except TypeError:
        return client.get_or_create_collection(
            name=CHROMA_COLLECTION_NAME,
            embedding_function=None,
            metadata={"hnsw:space": "cosine"},
        )
