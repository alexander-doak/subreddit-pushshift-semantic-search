"""Configuration for Reddit Subreddit Vector Search."""

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# -- Paths ------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent
DATA_DIR = PROJECT_ROOT / "data"
SQL_DIR = PROJECT_ROOT / "sql"
SERVICE_ACCOUNT_JSON = PROJECT_ROOT / os.getenv(
    "GOOGLE_SERVICE_ACCOUNT_JSON",
    "automated-internal-operational-c31f82e1bf18.json",
)

# -- Database ---------------------------------------------------------------
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_PORT = int(os.getenv("POSTGRES_PORT", "5432"))
POSTGRES_DB = os.getenv("POSTGRES_DB", "reddit_vectors")
POSTGRES_USER = os.getenv("POSTGRES_USER", "reddit_user")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "reddit_secret_pw")

def database_url() -> str:
    return f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"

# -- Google Sheets ----------------------------------------------------------
GOOGLE_SHEET_ID = os.getenv("GOOGLE_SHEET_ID", "")
RESULTS_SHEET_NAME = "Results"

# Marker strings in row 1 -- the INPUT/OUTPUT cells are one column to the right
INPUT_MARKER = "Input String:"
OUTPUT_MARKER = "Currently Showing:"

# -- Embedding Model --------------------------------------------------------
EMBEDDING_MODEL = "intfloat/multilingual-e5-large-instruct"
EMBEDDING_DIMENSION = 1024
MODEL_CACHE_DIR = str(PROJECT_ROOT / "models")

# -- Search Tuning ----------------------------------------------------------
HNSW_RECALL_COUNT = 1000   # How many rows HNSW pulls back (tune down if slow)
FINAL_RESULT_COUNT = 500   # Top N written to Google Sheet

# -- Data Loading -----------------------------------------------------------
SKIP_SENTINEL = "SKIP"     # Value in the XLSX that means "no description"
EMBED_BATCH_SIZE = 64      # Rows per batch during embedding generation