# subreddit-pushshift-semantic-search

Semantic vector search across 40,000+ subreddits from the [Pushshift top-40k dataset](https://www.reddit.com/r/pushshift/comments/1itme1k/separate_dump_files_for_the_top_40k_subreddits/), including pre-pruning for adult / banned / invalid subreddits. Type a natural-language query, hit a button on the backend, and get ranked results in seconds using a Google Sheets UI.

## What this does

The Pushshift dataset is a well-known ~3+ TB archive of Reddit submissions and comments from the top 40,000 subreddits, spanning 2005–2025. This project makes that list of subreddits searchable by meaning, rather than name.

The pipeline has four stages:

1. **Recon & flagging** — Checks every subreddit against Reddit and flags ones that are banned, private, quarantined, NSFW, or no longer exist. Uses a 6-second delay between requests to stay within Reddit's rate limits.

2. **Description generation** — Sends each non-flagged subreddit to OpenAI to get a short, plain-English description. Web search is deliberately disabled — if the LLM doesn't already have latent knowledge about a subreddit, it probably isn't popular enough to warrant inclusion.

3. **Embedding & storage** — Encodes each description into a 1024-dimensional vector using `intfloat/multilingual-e5-large-instruct` and stores everything in a PostgreSQL database with pgvector.

4. **Interactive search** — A Google Sheets spreadsheet acts as the UI. Type a query into a designated cell, trigger the backend, and ranked results appear in the sheet within seconds. Search uses a two-stage pipeline: fast HNSW approximate recall followed by exact cosine-similarity reranking.

## Project structure

```
├── config.py                  # Central configuration (reads from .env)
├── database.py                # PostgreSQL + pgvector connection utilities
├── create_descriptions.py     # Stage 1-2: flag subreddits & generate descriptions via OpenAI
├── lib/
│   ├── embeddings.py          # Embedding model loading & encoding (E5)
│   ├── search.py              # Two-stage vector search (HNSW + rerank)
│   └── sheets.py              # Google Sheets read/write integration
├── scripts/
│   ├── 01_init_db.py          # Create the database schema
│   ├── 02_load_data.py        # Load subreddit data from XLSX into PostgreSQL
│   ├── 03_embed.py            # Generate and store embedding vectors
│   └── 04_search.py           # Interactive search loop (Google Sheets I/O)
├── sql/
│   └── create_tables.sql      # Table and index definitions
├── requirements.txt           # Python dependencies
├── .env.example               # Template for environment variables
└── .gitignore
```

## Prerequisites

- Python 3.10+
- PostgreSQL with the [pgvector](https://github.com/pgvector/pgvector) extension installed
- A Google Cloud service account with access to the Google Sheets API
- An OpenAI API key (only needed for description generation)
- This project was built and tested on Windows. The data-loading scripts (`create_descriptions.py`, `02_load_data.py`) use hardcoded Windows-style file paths that you'll need to adjust if running on Linux or macOS.

## Setup

1. **Clone the repo**

```bash
   git clone https://github.com/alexander-doak/subreddit-pushshift-semantic-search.git
   cd subreddit-pushshift-semantic-search
```

2. **Create a virtual environment and install dependencies**

```bash
   python -m venv venv
   source venv/bin/activate        # Linux/macOS
   venv\Scripts\activate           # Windows
   pip install -r requirements.txt
```

3. **Configure environment variables**

```bash
   cp .env.example .env
```

   Edit `.env` and fill in your database credentials, Google Sheet ID, service account JSON filename, and OpenAI API key.

4. **Set up PostgreSQL**

   Make sure pgvector is installed, then create the database:

```sql
   CREATE DATABASE reddit_vectors;
   \c reddit_vectors
   CREATE EXTENSION IF NOT EXISTS vector;
```

5. **Set up Google Sheets**

   Create a spreadsheet with a sheet named `Results`. Row 1 should contain:
   - A cell with `Input String:` — the cell to its right is where you type your query
   - A cell with `Currently Showing:` — the cell to its right displays the active query
   - Column headers matching the result fields: `subreddit_name`, `subreddit_url`, `comments_size_mb`, `submissions_size_mb`, `banned`, `adult`, `valid`, `description`, `semantic_strength`

   Share the spreadsheet with the email address from your service account JSON.

## Usage

Run the scripts in order:

```bash
# 1. Initialize the database schema
python scripts/01_init_db.py

# 2. Load subreddit data from the XLSX file
python scripts/02_load_data.py

# 3. Generate embeddings
#    A CUDA-capable GPU is strongly recommended — embedding 40k descriptions
#    on CPU can take many hours, while a GPU with CUDA cores brings this down to about an hour.
python scripts/03_embed.py

# 4. Start the interactive search loop
python scripts/04_search.py
```

Step 4 connects to your Google Sheet, reads the query from the input cell, runs the search, and writes results back. It loops so you can update the query and search again without restarting.

## How search works

1. Your query is encoded using the same E5 model used for the descriptions
2. **Stage 1 (HNSW recall):** pgvector's HNSW index pulls back the top 1,000 approximate nearest neighbors
3. **Stage 2 (exact rerank):** Cosine similarity is computed exactly against the query vector, and the top 500 results are returned
4. Results are written to the Google Sheet, ranked by `semantic_strength`

## Data source

The subreddit list comes from the Pushshift top-40k dataset. See [this post](https://www.reddit.com/r/pushshift/comments/1itme1k/separate_dump_files_for_the_top_40k_subreddits/) for background on the dataset.

## License

MIT
