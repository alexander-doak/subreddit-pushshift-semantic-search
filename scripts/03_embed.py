"""Generate embeddings for all subreddit descriptions and store in the database."""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import config
import database

# Add lib/ to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "lib"))
import embeddings


def get_rows_needing_embeddings(cur):
    """Fetch rows that have a description but no embedding yet."""
    cur.execute("""
        SELECT id, description
        FROM subreddits
        WHERE description IS NOT NULL
          AND embedding IS NULL
        ORDER BY id;
    """)
    return cur.fetchall()


def update_embeddings(cur, row_ids, vectors):
    """Write embedding vectors back to the database."""
    for row_id, vec in zip(row_ids, vectors):
        cur.execute(
            "UPDATE subreddits SET embedding = %s WHERE id = %s;",
            (vec.tolist(), row_id),
        )


def main():
    print("=" * 60)
    print("EMBEDDING GENERATOR")
    print("=" * 60)
    print()

    # Check how many rows need embeddings
    with database.get_cursor() as cur:
        rows = get_rows_needing_embeddings(cur)

    total = len(rows)
    if total == 0:
        print("All rows with descriptions already have embeddings. Nothing to do.")
        return

    print(f"Found {total:,} rows needing embeddings.")
    print(f"Model: {config.EMBEDDING_MODEL}")
    print(f"Batch size: {config.EMBED_BATCH_SIZE}")
    print()

    # Estimate time on CPU
    est_minutes = total / 50  # rough: ~50 rows/min on CPU with this model
    print(f"Estimated time on CPU: {est_minutes:.0f} - {est_minutes * 1.5:.0f} minutes")
    print("(This is a rough estimate. Actual time depends on description length.)")
    print()
    input("Press ENTER to start embedding (or Ctrl+C to abort) ... ")
    print()

    # Load model (this itself takes a moment)
    embeddings.get_model()
    print()

    # Process in batches
    batch_size = config.EMBED_BATCH_SIZE
    total_start = time.time()
    processed = 0

    for i in range(0, total, batch_size):
        batch_rows = rows[i : i + batch_size]
        batch_ids = [r["id"] for r in batch_rows]
        batch_texts = [r["description"] for r in batch_rows]

        batch_start = time.time()
        vectors = embeddings.encode_passages(batch_texts, show_progress=False)
        batch_elapsed = time.time() - batch_start

        # Write to DB
        with database.get_cursor() as cur:
            update_embeddings(cur, batch_ids, vectors)

        processed += len(batch_rows)
        elapsed_total = time.time() - total_start
        rate = processed / elapsed_total
        remaining = (total - processed) / rate if rate > 0 else 0

        print(
            f"  Embedded {processed:,} / {total:,} "
            f"({batch_elapsed:.1f}s batch, "
            f"{rate:.1f} rows/s, "
            f"~{remaining:.0f}s remaining)"
        )

    total_elapsed = time.time() - total_start
    print()
    print(f"Embedding complete. {processed:,} rows in {total_elapsed:.1f}s "
          f"({processed / total_elapsed:.1f} rows/s)")

    # Verify
    with database.get_cursor() as cur:
        cur.execute("SELECT COUNT(*) AS cnt FROM subreddits WHERE embedding IS NOT NULL;")
        count = cur.fetchone()["cnt"]
    print(f"Verification: {count:,} rows now have embeddings.")


if __name__ == "__main__":
    main()