#%%
import csv
import json
import re
from pathlib import Path

from PyPDF2 import PdfReader
from docx import Document  # python -m pip install python-docx, not regular docx

from config import (
    EMB_MODEL,
    MAX_CHUNK_TOKENS,
    POLICY_SOURCE_FOLDER,
    VECTOR_DB_CSV,
)
from func import get_embedding, token_count

#%%

supported_extensions = {".pdf", ".docx", ".txt", ".md", ".py"}

# File destinations are intentionally blank in config.py for migration to the GB-10.
source_folder = Path(POLICY_SOURCE_FOLDER) if POLICY_SOURCE_FOLDER else None
csv_file = Path(VECTOR_DB_CSV) if VECTOR_DB_CSV else None

emb_model = EMB_MODEL
max_tokens = MAX_CHUNK_TOKENS

fieldnames = ["file_name", "content", "embedding", "embedding_model", "embedding_dim"]

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

def delete_file_from_vector_db(file_name, vector_db=csv_file):
    """
    Delete every vector database row that came from the given file name.

    Pass either a plain file name like "policy.pdf" or a full path. The function
    compares against only the base file name stored in the CSV's file_name column.
    Returns the number of deleted rows.
    """
    vector_db = require_path(vector_db, "VECTOR_DB_CSV")
    target_file_name = Path(file_name).name

    if not vector_db.exists():
        raise FileNotFoundError(f"Vector database does not exist: {vector_db}")

    with open(vector_db, "r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        existing_fieldnames = reader.fieldnames or fieldnames

    kept_rows = [row for row in rows if row.get("file_name") != target_file_name]
    deleted_count = len(rows) - len(kept_rows)

    with open(vector_db, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=existing_fieldnames)
        writer.writeheader()
        writer.writerows(kept_rows)

    print(f"Deleted {deleted_count} rows for {target_file_name} from {vector_db}")
    return deleted_count

#%%

def insert_file_into_vector_db(
        file_path,
        vector_db=csv_file,
        emb_model=emb_model,
        max_tokens=max_tokens,
        replace_existing=True
        ):
    """
    Read one local file, split it into chunks, embed each chunk, and append those
    chunks to the CSV vector database.

    The CSV records embedding_model and embedding_dim so dimension changes are
    explicit after moving to the GB-10 or switching embedding models.
    """
    file_path = Path(file_path)
    vector_db = require_path(vector_db, "VECTOR_DB_CSV")

    if not file_path.exists():
        raise FileNotFoundError(f"File does not exist: {file_path}")

    if file_path.suffix.lower() not in supported_extensions:
        raise ValueError(
            f"Unsupported file type: {file_path.suffix}. "
            f"Supported types: {sorted(supported_extensions)}"
        )

    vector_db.parent.mkdir(parents=True, exist_ok=True)

    if replace_existing and vector_db.exists():
        delete_file_from_vector_db(file_path.name, vector_db=vector_db)

    print(f"Processing {file_path.name}")

    text = read_original_file(file_path)
    contents = split_content(text, max_tokens=max_tokens, model=emb_model)

    contents = [clean_text(content) for content in contents]
    contents = [content for content in contents if content]

    file_exists = vector_db.exists()
    write_header = (not file_exists) or vector_db.stat().st_size == 0

    with open(vector_db, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)

        if write_header:
            writer.writeheader()

        for content in contents:
            embedding_input = f"File name: {file_path.name}\nContent: {content}"
            embedding = get_embedding(embedding_input, emb_model)

            writer.writerow({
                "file_name": file_path.name,
                "content": content,
                "embedding": json.dumps(embedding),
                "embedding_model": emb_model,
                "embedding_dim": len(embedding)
            })

    print(f"Inserted {len(contents)} chunks for {file_path.name} into {vector_db}")
    return len(contents)

#%%

def build_vector_database(
        source_folder=source_folder,
        vector_db=csv_file,
        emb_model=emb_model,
        max_tokens=max_tokens
        ):
    """
    Rebuild the entire vector database from every supported file in source_folder.
    """
    source_folder = require_path(source_folder, "POLICY_SOURCE_FOLDER")
    vector_db = require_path(vector_db, "VECTOR_DB_CSV")
    vector_db.parent.mkdir(parents=True, exist_ok=True)

    if not source_folder.exists():
        raise FileNotFoundError(f"Source folder does not exist: {source_folder}")

    files = [
        file for file in source_folder.iterdir()
        if file.suffix.lower() in supported_extensions
    ]

    with open(vector_db, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for file in files:
            print(f"Processing {file.name}")

            text = read_original_file(file)
            contents = split_content(text, max_tokens=max_tokens, model=emb_model)

            contents = [clean_text(content) for content in contents]
            contents = [content for content in contents if content]

            for content in contents:
                embedding_input = f"File name: {file.name}\nContent: {content}"
                embedding = get_embedding(embedding_input, emb_model)

                writer.writerow({
                    "file_name": file.name,
                    "content": content,
                    "embedding": json.dumps(embedding),
                    "embedding_model": emb_model,
                    "embedding_dim": len(embedding)
                })

    print(f"Saved vector database to {vector_db}")

#%%

if __name__ == "__main__":
    build_vector_database()

#%%
