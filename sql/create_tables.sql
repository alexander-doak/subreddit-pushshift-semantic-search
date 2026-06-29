-- Main subreddits table
CREATE TABLE IF NOT EXISTS subreddits (
    id                  SERIAL PRIMARY KEY,
    subreddit_name      TEXT NOT NULL,
    url_checked         TEXT,
    final_url           TEXT,
    status_code         INTEGER,
    page_title          TEXT,
    signal_banned       BOOLEAN DEFAULT FALSE,
    signal_private      BOOLEAN DEFAULT FALSE,
    signal_quarantined  BOOLEAN DEFAULT FALSE,
    signal_over18       BOOLEAN DEFAULT FALSE,
    signal_not_found    BOOLEAN DEFAULT FALSE,
    description         TEXT,
    comments_size_mb    DOUBLE PRECISION,
    submissions_size_mb DOUBLE PRECISION,
    embedding           vector(1024),
    created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Fast lookup by name
CREATE INDEX IF NOT EXISTS idx_subreddits_name
    ON subreddits (subreddit_name);

-- HNSW index for approximate nearest neighbor search
-- Only covers rows that have an embedding
CREATE INDEX IF NOT EXISTS idx_subreddits_embedding_hnsw
    ON subreddits
    USING hnsw (embedding vector_cosine_ops)
    WHERE embedding IS NOT NULL;