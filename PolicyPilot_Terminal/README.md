# Terminal Policy Pilot

Terminal Policy Pilot is a command-line Retrieval-Augmented Generation (RAG) assistant for Texas Tech University Health Sciences Center operating policy documents. It reads local policy files, splits them into searchable text chunks, embeds those chunks with a local Ollama embedding model, stores the results in a CSV vector database, retrieves the most relevant chunks for a user question, and uses a local Ollama chat model to produce a policy-grounded answer with source filenames and XML citation tags.

This version is configured for migration to a GB-10 machine. The local file paths are intentionally blank in `config.py` so they can be filled in after the project is moved to the target device.

## Project Contents

```text
Terminal Policy Pilot/
├── chunking.py   # Builds and updates the CSV vector database from policy files
├── config.py     # Central configuration for paths, models, retrieval, and context limits
├── func.py       # Embedding, cosine similarity, CSV parsing, retrieval, and prompt assembly helpers
├── main.py       # Interactive terminal chatbot loop and safety/generation logic
└── manage.py     # Interactive append/delete utility for maintaining the local vector database
```

## High-Level Workflow

1. Configure local paths and model names in `config.py`.
2. Place source policy documents in the configured policy source folder.
3. Run `chunking.py` to build a CSV vector database.
4. Run `main.py` to ask policy questions in the terminal.
5. The app embeds the user question, retrieves the most similar policy chunks, sends only those chunks to the generation model, and returns a cited answer.
6. Use `manage.py` when you need to append a new file or delete an existing file from the vector database without rebuilding everything.

## Main Purpose

The code is designed to answer policy questions using only retrieved policy excerpts. It explicitly instructs the model not to use outside knowledge and not to guess. Every answer paragraph or bullet that contains policy information is required to include a source filename such as:

```text
(Source: op0101.pdf)
```

The answer is also required to end with XML citation tags in this format:

```xml
<citation filename='actual_filename.pdf'>exact short quote</citation>
```

These citation tags are intended to support clickable document links in a larger UI or downstream integration.

## File-by-File Explanation

### `config.py`

`config.py` stores all project-level settings.

#### Local file path settings

```python
POLICY_SOURCE_FOLDER = r""
VECTOR_DB_CSV = r""
NEW_POLICIES_FOLDER = r""
```

These values are blank by design. Before running the project on the GB-10 or another machine, fill them in with real local paths.

Example:

```python
POLICY_SOURCE_FOLDER = r"C:\\PolicyPilot\\Policies"
VECTOR_DB_CSV = r"C:\\PolicyPilot\\VectorDB\\vector_database.csv"
NEW_POLICIES_FOLDER = r"C:\\PolicyPilot\\NewPolicies"
```

`POLICY_SOURCE_FOLDER` should point to the folder containing the policy documents to ingest. `VECTOR_DB_CSV` should point to the CSV file where embeddings and chunks will be stored. `NEW_POLICIES_FOLDER` is defined as an optional location for policies that may be appended later, but it is not currently used directly by the code.

#### Model settings

```python
GUARD_MODEL = "llama-guard3:8b"
GEN_MODEL = "llama3.3:70b"
EMB_MODEL = "embeddinggemma:300m"
```

The code uses three Ollama models:

- `GUARD_MODEL`: classifies user prompts and model answers as safe or unsafe.
- `GEN_MODEL`: generates the final policy answer.
- `EMB_MODEL`: creates embeddings for policy chunks and user questions.

These model names assume the required Ollama models are already installed on the machine running the code.

#### Retrieval and context settings

```python
GEN_CONTEXT_WINDOW = 32768
GEN_TOKEN_MAX = GEN_CONTEXT_WINDOW - 1500
K = 8
EXPECTED_EMBEDDING_DIM = None
MAX_CHUNK_TOKENS = 1500
```

- `GEN_CONTEXT_WINDOW` controls the Ollama context window passed to the generation model.
- `GEN_TOKEN_MAX` is the approximate prompt budget before leaving room for the answer.
- `K` controls how many retrieved policy chunks are passed into the answer prompt.
- `EXPECTED_EMBEDDING_DIM` can optionally enforce a specific embedding vector size.
- `MAX_CHUNK_TOKENS` controls the approximate maximum chunk size used during ingestion.

### `chunking.py`

`chunking.py` is responsible for reading source files, splitting them into chunks, cleaning the text, embedding each chunk, and writing the results to the CSV vector database.

#### Supported file types

```python
supported_extensions = {".pdf", ".docx", ".txt", ".md", ".py"}
```

The code can ingest:

- PDF files through `PyPDF2.PdfReader`
- Word documents through `python-docx`
- Plain text files
- Markdown files
- Python files

#### Key functions

##### `require_path(path_value, setting_name)`

Validates that a required path setting is not blank. If a path is missing, the function raises a clear error telling the user to fill in the relevant value in `config.py`.

##### `read_word(file)`

Reads a `.docx` file and returns the document paragraphs as a list of strings.

##### `read_pdf(file)`

Reads a PDF file with `PyPDF2` and returns extracted page text as a list of strings. Each page becomes one initial text section before chunking.

##### `read_text_file(file)`

Reads a text-like file with UTF-8 encoding and returns the full file contents as a one-item list.

##### `read_original_file(file)`

Dispatches the file to the correct reader based on extension.

##### `split_string(string, max_tokens=800, model=None, max_recursion=5)`

Recursively splits long text into smaller chunks. It tries to split by increasingly smaller delimiters:

1. Double newline
2. Single newline
3. Sentence boundary `. `
4. Space

If the recursion limit is reached, it truncates the text using an approximate character count.

##### `split_content(text, max_tokens, model=None)`

Applies `split_string()` to each text section extracted from the original file. It prints how many original sections became how many final chunks.

##### `clean_text(text)`

Normalizes text by removing newlines, carriage returns, square brackets, extra spacing, and leading/trailing whitespace.

##### `delete_file_from_vector_db(file_name, vector_db=csv_file)`

Deletes every CSV row whose `file_name` column matches the provided file name. It accepts either a plain filename or a full path and compares only against the base filename.

##### `insert_file_into_vector_db(...)`

Adds a single file to the vector database. It can optionally delete the file's existing rows before inserting the new rows.

Important behavior:

- Validates that the file exists.
- Rejects unsupported file extensions.
- Reads, splits, and cleans the file text.
- Embeds each chunk using the configured embedding model.
- Writes rows to the CSV database.
- Stores the embedding model name and embedding dimension for each row.

##### `build_vector_database(...)`

Rebuilds the entire vector database from every supported file in `POLICY_SOURCE_FOLDER`. When run directly with:

```bash
python chunking.py
```

this function is called automatically.

#### Vector database CSV schema

The CSV contains these columns:

```text
file_name,content,embedding,embedding_model,embedding_dim
```

- `file_name`: source file name, such as `op0101.pdf`
- `content`: cleaned policy chunk text
- `embedding`: JSON-serialized embedding vector
- `embedding_model`: model used to create the embedding
- `embedding_dim`: length of the embedding vector

### `func.py`

`func.py` contains the retrieval and prompt-construction utilities.

#### Key functions

##### `get_embedding(text, emb_model="embeddinggemma:300m")`

Calls Ollama's embedding API and returns the first embedding vector. If `EXPECTED_EMBEDDING_DIM` is set in `config.py`, the function checks that the returned vector has the expected length.

##### `cos_sim(question, answer)`

Computes cosine similarity between two embedding vectors. It returns `-1` if the vectors have different lengths or if either vector has zero norm.

##### `parse_embedding(value)`

Converts an embedding stored as a JSON string in the CSV back into a Python list of floats.

##### `build_retrieved_chunk_text(row)`

Formats a retrieved CSV row into a prompt-ready block containing:

- `SOURCE_FILE`
- `POLICY_CHUNK`
- `CITATION_XML_TO_COPY`

Example output structure:

```text
SOURCE_FILE: op0101.pdf
POLICY_CHUNK:
[retrieved policy text]
CITATION_XML_TO_COPY:
<citation filename='op0101.pdf'>short quote</citation>
```

The citation quote is built from the first 300 characters of the cleaned chunk text.

##### `get_topk_chunk(user_vector, vector_db, k)`

Loads the CSV vector database, parses the stored embeddings, filters rows to only those with the same dimension as the user question embedding, computes cosine similarity, sorts chunks from most similar to least similar, and returns the top `k` chunks formatted by `build_retrieved_chunk_text()`.

This dimension filtering is important because embeddings generated by different models may have different vector lengths. If no compatible embeddings are found, the function raises an error explaining that the vector database should be rebuilt with the current embedding model.

##### `token_count(text, model=None)`

Approximates token count as `len(text) // 4`. This is a lightweight estimate used for chunking and prompt budgeting instead of an exact tokenizer.

##### `set_user_prompt(...)`

Builds the final user prompt sent to the generation model. It starts with the answer instructions, appends retrieved chunks until the approximate token budget is reached, and ends with the user's question.

### `main.py`

`main.py` is the terminal chatbot entry point.

It loads configuration values, defines the system prompt and user instructions, runs safety checks, retrieves relevant chunks, generates an answer, checks the answer safety, and prints the result.

#### System behavior

The system prompt tells the model:

- It is a policy assistant for Texas Tech University Health Sciences Center operating policies.
- It must answer only from retrieved policy excerpts.
- It must not use outside knowledge.
- It must not guess.
- It must include source filenames.
- It must include XML citation tags.
- If the retrieved content is insufficient, it should say: `I do not know based on the provided policy content.`

#### `safe(prompt, guard_model=guard_model)`

Calls the configured guard model through Ollama and parses the returned safety label.

Expected safe response:

```text
safe
```

Expected unsafe response:

```text
unsafe
S1,S6
```

If unsafe, the function maps the returned category codes to human-readable descriptions using `guard_rail_dic`.

The code includes safety descriptions for categories S1 through S13, covering areas such as violent crimes, non-violent crimes, privacy, intellectual property, hate, self-harm, sexual content, and election misinformation.

#### `get_answer(...)`

The main answer pipeline:

1. Verifies that `VECTOR_DB_CSV` is configured.
2. Runs the user question through the guard model.
3. Embeds the user question.
4. Retrieves the top `K` most similar policy chunks.
5. Builds the final RAG prompt.
6. Calls the generation model with temperature `0` and the configured context window.
7. Runs the generated answer through the guard model.
8. Returns the answer only if the safety check passes.

#### Terminal loop

At the bottom of `main.py`, the code runs an infinite terminal loop:

```python
while True:
    question = input("How can I help you? To exit type 'bye' ")

    if question.strip().lower() == "bye":
        print("Have a great day! Wreck 'Em, Red Raiders!")
        break

    answer = get_answer(question)

    print(f">>> {answer}\n")
```

Run it with:

```bash
python main.py
```

Type `bye` to exit.

### `manage.py`

`manage.py` is an interactive helper script for maintaining the local CSV vector database.

Run it with:

```bash
python manage.py
```

It supports three commands:

```text
append
```

Prompts for a full file path and appends that file's chunks to the CSV vector database.

```text
delete
```

Prompts for a filename or full path and removes matching rows from the CSV vector database.

```text
end
```

Stops the script.

Important detail: `append` calls `insert_file_into_vector_db(..., replace_existing=False)`, so it does not remove old rows for the same file before inserting. If the same file is appended repeatedly, duplicate rows may be created.

## Dependencies

This project depends on the following Python packages:

```text
ollama
numpy
pandas
PyPDF2
python-docx
```

Install them with:

```bash
python -m pip install ollama numpy pandas PyPDF2 python-docx
```

Do not install the unrelated package named `docx`; the code imports `Document` from `python-docx`.

## Ollama Model Requirements

The code assumes Ollama is installed and that the configured models are available locally.

Default models from `config.py`:

```text
llama-guard3:8b
llama3.3:70b
embeddinggemma:300m
```

Typical setup commands:

```bash
ollama pull llama-guard3:8b
ollama pull llama3.3:70b
ollama pull embeddinggemma:300m
```

The generation model `llama3.3:70b` is large and is intended for the GB-10 machine. If running on a weaker local machine, choose a smaller generation model in `config.py`.

## Setup Instructions

### 1. Install Python dependencies

```bash
python -m pip install ollama numpy pandas PyPDF2 python-docx
```

### 2. Install and start Ollama

Make sure Ollama is installed and running on the machine.

### 3. Pull the required Ollama models

```bash
ollama pull llama-guard3:8b
ollama pull llama3.3:70b
ollama pull embeddinggemma:300m
```

### 4. Fill in `config.py`

Set at least these two values:

```python
POLICY_SOURCE_FOLDER = r"C:\\Path\\To\\PolicyDocuments"
VECTOR_DB_CSV = r"C:\\Path\\To\\VectorDB\\vector_database.csv"
```

### 5. Build the vector database

```bash
python chunking.py
```

This reads all supported files in `POLICY_SOURCE_FOLDER`, chunks them, embeds them, and saves them to `VECTOR_DB_CSV`.

### 6. Run the terminal assistant

```bash
python main.py
```

Ask a policy question at the prompt. Type `bye` to exit.

## Example Use

```text
How can I help you? To exit type 'bye' What is the travel reimbursement policy?
>>> Answer:
[Policy-grounded answer with source filenames]

Sources used:
- example_policy.pdf

<citation filename='example_policy.pdf'>exact short quote</citation>
```

## Maintaining the Vector Database

### Rebuild everything

Use this when the full source policy folder has changed or when the embedding model changes:

```bash
python chunking.py
```

### Append or delete one file interactively

```bash
python manage.py
```

Then type:

```text
append
```

or:

```text
delete
```

or:

```text
end
```

## Important Design Details

### Local-first design

The project uses local Ollama models instead of cloud APIs. This keeps the RAG pipeline self-contained on the machine where Ollama and the model files are installed.

### CSV vector store

The vector database is a CSV file rather than Chroma, Pinecone, SQLite, or another dedicated vector database. This makes the implementation simple and portable, but it may become slow as the number of policy chunks grows.

### Embedding dimension safety

The code records `embedding_dim` for every chunk and filters retrieved rows to only those matching the current question embedding size. This prevents cosine similarity errors when the database contains embeddings generated by a different model.

### Citation-first prompt format

Retrieved chunks are passed to the generation model with explicit `SOURCE_FILE` and `CITATION_XML_TO_COPY` fields. The answer prompt tells the model to copy those XML citation lines rather than inventing new citation tags.

### Guardrails before and after generation

The code checks both the user question and the generated answer with `llama-guard3:8b`. If either is classified as unsafe, the app returns an unsafe-category message instead of continuing normally.

## Known Limitations and Notes

1. `config.py` has blank paths by default. The project will not run until `POLICY_SOURCE_FOLDER` and `VECTOR_DB_CSV` are filled in.
2. There is no `requirements.txt` file in the uploaded code. Dependencies must be installed manually unless one is added later.
3. `main.py` starts its interactive loop at import time because the loop is not inside an `if __name__ == "__main__":` block. This is fine for direct terminal use, but it makes importing `main.py` from another module inconvenient.
4. `PyPDF2` text extraction can return incomplete or empty text for scanned PDFs or image-based PDFs. OCR is not included.
5. The token counting function is approximate. It estimates tokens using character length divided by four.
6. The CSV vector database is easy to inspect but not optimized for very large document collections.
7. `manage.py` append mode does not remove existing rows for the same file, so repeated appends can create duplicates.
8. The safety classifier depends on the guard model returning labels in the expected `safe` or `unsafe` format.
9. The answer quality depends heavily on the quality of the retrieved chunks and the clarity of the source policy documents.
10. The code assumes the Ollama Python client can reach a running Ollama service.

## Troubleshooting

### `VECTOR_DB_CSV is blank`

Fill in `VECTOR_DB_CSV` in `config.py` with a real file path.

### `POLICY_SOURCE_FOLDER is blank`

Fill in `POLICY_SOURCE_FOLDER` in `config.py` with the folder containing source policy files.

### `No compatible embeddings found`

The question embedding dimension does not match the embeddings stored in the CSV. This usually means the embedding model changed. Rebuild the vector database with:

```bash
python chunking.py
```

### `ModuleNotFoundError: No module named 'docx'`

Install `python-docx`:

```bash
python -m pip install python-docx
```

### Ollama model errors

Make sure Ollama is installed, running, and has the configured models pulled locally:

```bash
ollama list
```

If a model is missing, pull it:

```bash
ollama pull model-name
```

### Poor or missing PDF text

If the PDF is scanned or image-based, `PyPDF2` may not extract useful text. Convert the PDF to searchable text first or add an OCR step before ingestion.

## Recommended Future Improvements

- Add a `requirements.txt` file.
- Move the terminal loop in `main.py` under `if __name__ == "__main__":`.
- Add structured logging instead of print statements.
- Add duplicate detection when appending files through `manage.py`.
- Add a command-line argument interface for build, append, delete, and chat modes.
- Add OCR support for scanned PDFs.
- Consider replacing the CSV vector store with SQLite, Chroma, or another vector database if the document set becomes large.
- Add automated tests for chunking, embedding parsing, retrieval, and prompt construction.
- Add clearer error handling around Ollama connection failures and malformed guard responses.

## Quick Command Reference

Install dependencies:

```bash
python -m pip install ollama numpy pandas PyPDF2 python-docx
```

Build vector database:

```bash
python chunking.py
```

Run chatbot:

```bash
python main.py
```

Maintain vector database:

```bash
python manage.py
```

Exit chatbot:

```text
bye
```
