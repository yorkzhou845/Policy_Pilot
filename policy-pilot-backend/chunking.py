#%%
import re
import uuid
from pathlib import Path

from PyPDF2 import PdfReader
from docx import Document  # python -m pip install python-docx, not regular docx

from config import (
    EMB_MODEL,
    MAX_CHUNK_TOKENS,
    POLICY_SOURCE_FOLDER,
)
from chroma_store import get_chroma_collection
from func import get_embedding, token_count

#%%

supported_extensions = {".pdf", ".docx", ".txt", ".md", ".py"}

source_folder = Path(POLICY_SOURCE_FOLDER) if POLICY_SOURCE_FOLDER else None

emb_model = EMB_MODEL
max_tokens = MAX_CHUNK_TOKENS

#%%

def require_path(path_value, setting_name):
    if path_value is None:
        raise ValueError(f"{setting_name} is blank. Fill it in config.py before running this script.")

    return Path(path_value)


def read_word(file):
    doc = Document(file)
    text = []

    for paragraph in doc.paragraphs:
        text.append(paragraph.text)

    return text


def read_pdf(file):
    reader = PdfReader(file)
    text = []

    for page in reader.pages:
        text.append(page.extract_text())

    return text


def read_text_file(file):
    with open(file, "r", encoding="utf-8", errors="ignore") as f:
        return [f.read()]


def read_original_file(file):
    file = Path(file)
    extension = file.suffix.lower()

    if extension == ".pdf":
        return read_pdf(file)

    if extension == ".docx":
        return read_word(file)

    if extension in {".txt", ".md", ".py"}:
        return read_text_file(file)

    return []


def halved_by_delimiter(string, delimiter="\n", model=None):
    chunks = string.split(delimiter)

    if len(chunks) == 1:
        return [string, ""]

    halfway = token_count(string, model) // 2

    best_index = 1
    best_diff = halfway

    for i in range(1, len(chunks)):
        left = delimiter.join(chunks[:i])
        left_tokens = token_count(left, model)
        diff = abs(halfway - left_tokens)

        if diff < best_diff:
            best_diff = diff
            best_index = i

    left = delimiter.join(chunks[:best_index])
    right = delimiter.join(chunks[best_index:])

    return [left, right]


def truncated_string(string, max_tokens=800):
    approx_chars = max_tokens * 4
    return string[:approx_chars]


def split_string(string, max_tokens=800, model=None, max_recursion=5):
    num_tokens = token_count(string, model)

    if num_tokens <= max_tokens:
        return [string]

    if max_recursion == 0:
        return [truncated_string(string, max_tokens)]

    for delimiter in ["\n\n", "\n", ". ", " "]:
        left, right = halved_by_delimiter(string, delimiter, model)

        if left and right:
            results = []

            results.extend(
                split_string(
                    left,
                    max_tokens=max_tokens,
                    model=model,
                    max_recursion=max_recursion - 1
                )
            )

            results.extend(
                split_string(
                    right,
                    max_tokens=max_tokens,
                    model=model,
                    max_recursion=max_recursion - 1
                )
            )

            return results

    return [truncated_string(string, max_tokens)]


def split_content(text, max_tokens, model=None):
    contents = []

    for txt in text:
        if txt:
            contents.extend(split_string(txt, max_tokens=max_tokens, model=model))

    print(f"{len(text)} sections split into {len(contents)} chunks.")
    return contents


def clean_text(text):
    text = re.sub(r"\n", " ", text)
    text = re.sub(r"\r", " ", text)
    text = re.sub(r"\[|\]", "", text)
    text = re.sub(r"\s+", " ", text)
    text = text.strip()

    return text

#%%

def delete_file_from_vector_db(file_name, vector_db=None):
    """
    Delete every Chroma record that came from the given file name.

    vector_db is kept in the signature for compatibility with the old CSV code.
    Chroma uses CHROMA_DB_DIR and CHROMA_COLLECTION_NAME from config.py.
    """
    target_file_name = Path(file_name).name
    collection = get_chroma_collection()

    existing = collection.get(
        where={"file_name": target_file_name},
        include=["metadatas"],
    )

    ids_to_delete = existing.get("ids", [])
    deleted_count = len(ids_to_delete)

    if ids_to_delete:
        collection.delete(ids=ids_to_delete)

    print(f"Deleted {deleted_count} chunks for {target_file_name} from ChromaDB")
    return deleted_count

#%%

def insert_file_into_vector_db(
        file_path,
        vector_db=None,
        emb_model=emb_model,
        max_tokens=max_tokens,
        replace_existing=True
        ):
    """
    Read one local file, split it into chunks, embed each chunk with Ollama,
    and insert those chunks into local ChromaDB.
    """
    file_path = Path(file_path)

    if not file_path.exists():
        raise FileNotFoundError(f"File does not exist: {file_path}")

    if file_path.suffix.lower() not in supported_extensions:
        raise ValueError(
            f"Unsupported file type: {file_path.suffix}. "
            f"Supported types: {sorted(supported_extensions)}"
        )

    collection = get_chroma_collection()

    if replace_existing:
        delete_file_from_vector_db(file_path.name)

    print(f"Processing {file_path.name}")

    text = read_original_file(file_path)
    contents = split_content(text, max_tokens=max_tokens, model=emb_model)

    contents = [clean_text(content) for content in contents]
    contents = [content for content in contents if content]

    if not contents:
        print(f"No usable text chunks found for {file_path.name}")
        return 0

    ids = []
    documents = []
    embeddings = []
    metadatas = []

    for chunk_index, content in enumerate(contents):
        embedding_input = f"File name: {file_path.name}\nContent: {content}"
        embedding = get_embedding(embedding_input, emb_model)

        ids.append(f"{file_path.name}::chunk_{chunk_index:04d}::{uuid.uuid4().hex}")
        documents.append(content)
        embeddings.append(embedding)
        metadatas.append({
            "file_name": file_path.name,
            "chunk_index": chunk_index,
            "embedding_model": emb_model,
            "embedding_dim": len(embedding),
        })

    collection.add(
        ids=ids,
        documents=documents,
        embeddings=embeddings,
        metadatas=metadatas,
    )

    print(f"Inserted {len(contents)} chunks for {file_path.name} into ChromaDB")
    return len(contents)

#%%

def build_vector_database(
        source_folder=source_folder,
        vector_db=None,
        emb_model=emb_model,
        max_tokens=max_tokens
        ):
    """
    Rebuild the entire ChromaDB collection from every supported file in source_folder.
    """
    source_folder = require_path(source_folder, "POLICY_SOURCE_FOLDER")

    if not source_folder.exists():
        raise FileNotFoundError(f"Source folder does not exist: {source_folder}")

    files = [
        file for file in source_folder.iterdir()
        if file.suffix.lower() in supported_extensions
    ]

    # Reset the collection so a rebuild does not leave stale chunks from old files.
    get_chroma_collection(reset=True)

    total_chunks = 0

    for file in files:
        rows_added = insert_file_into_vector_db(
            file_path=file,
            emb_model=emb_model,
            max_tokens=max_tokens,
            replace_existing=False,
        )
        total_chunks += rows_added

    print(f"Saved {total_chunks} chunks to local ChromaDB")

#%%

if __name__ == "__main__":
    build_vector_database()

#%%
