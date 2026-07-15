"""
config.py

GB-10 configuration for Policy Pilot P1 V2.

Fill in the blank path strings after moving this project to the new device.
The code intentionally does not hardcode York's old Windows paths.
"""

# -----------------------------
# Local file destinations
# -----------------------------

# Folder containing source policy files, such as PDFs, DOCX files, TXT files, etc.
POLICY_SOURCE_FOLDER = r""

# CSV vector database file. Example: r"C:\\Path\\To\\VectorDB\\vector_database.csv"
VECTOR_DB_CSV = r""

# Optional folder for policies you want to append later.
NEW_POLICIES_FOLDER = r""


# -----------------------------
# GB-10 model choices
# -----------------------------

# Safety classifier
GUARD_MODEL = "llama-guard3:8b"

# Stronger generation model for the GB-10 machine
GEN_MODEL = "llama3.3:70b"

# Local embedding model through Ollama
EMB_MODEL = "embeddinggemma:300m"


# -----------------------------
# Context / retrieval settings
# -----------------------------

# llama3.3:70b supports a large context window, but 32768 is a practical default.
# You can raise this later if the GB-10 runs it comfortably.
GEN_CONTEXT_WINDOW = 32768

# Approximate prompt budget. Leaves room for the model answer.
GEN_TOKEN_MAX = GEN_CONTEXT_WINDOW - 1500

# Number of retrieved policy chunks to pass into the generation prompt.
K = 8

# Leave as None unless you intentionally want to enforce a specific embedding size.
# The code records and checks the actual dimension at runtime.
EXPECTED_EMBEDDING_DIM = None

# Chunk size used when building the vector DB.
MAX_CHUNK_TOKENS = 1500
