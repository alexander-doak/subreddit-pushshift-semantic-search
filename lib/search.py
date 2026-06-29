"""Two-stage vector search: HNSW recall then exact cosine rerank."""

import numpy as np
import config
import database


def hnsw_search(query_vector, top_n=None):
    """Stage 1: Approximate nearest neighbor search via HNSW index.

    Args:
        query_vector: numpy array of shape (EMBEDDING_DIMENSION,)
        top_n: Number of candidates to retrieve. Defaults to config value.

    Returns:
        List of dicts with row data and approximate distance.
    """
    if top_n is None:
        top_n = config.HNSW_RECALL_COUNT

    with database.get_cursor() as cur:
        # Set the HNSW search scope
        cur.execute(f"SET hnsw.ef_search = {top_n};")

        cur.execute("""
            SELECT
                id,
                subreddit_name,
                final_url,
                comments_size_mb,
                submissions_size_mb,
                signal_banned,
                signal_over18,
                signal_not_found,
                signal_private,
                signal_quarantined,
                description,
                embedding,
                embedding <=> %s::vector AS distance
            FROM subreddits
            WHERE embedding IS NOT NULL
            ORDER BY embedding <=> %s::vector
            LIMIT %s;
        """, (query_vector.tolist(), query_vector.tolist(), top_n))

        return cur.fetchall()


def cosine_similarity(vec_a, vec_b):
    """Compute cosine similarity between two vectors.

    Assumes both vectors are already normalized (which they are from our encoder).
    For normalized vectors, cosine similarity = dot product.
    """
    return float(np.dot(vec_a, vec_b))


def rerank_results(candidates, query_vector):
    """Stage 2: Exact cosine similarity rerank of HNSW candidates.

    Args:
        candidates: List of row dicts from hnsw_search (must include 'embedding').
        query_vector: numpy array of shape (EMBEDDING_DIMENSION,)

    Returns:
        List of dicts sorted by semantic_strength (highest first),
        limited to FINAL_RESULT_COUNT. Each dict has the output columns
        plus semantic_strength. The embedding field is removed.
    """
    scored = []
    for row in candidates:
        emb = row["embedding"]
        if emb is None:
            continue

        # pgvector returns the vector as a numpy array via register_vector
        if not isinstance(emb, np.ndarray):
            emb = np.array(emb, dtype=np.float32)

        similarity = cosine_similarity(query_vector, emb)

        scored.append({
            "subreddit_name": row["subreddit_name"],
            "subreddit_url": row["final_url"] or "",
            "comments_size_mb": row["comments_size_mb"],
            "submissions_size_mb": row["submissions_size_mb"],
            "banned": row["signal_banned"],
            "adult": row["signal_over18"],
            "valid": not (row["signal_banned"] or row["signal_private"]
                         or row["signal_quarantined"] or row["signal_over18"]
                         or row["signal_not_found"]),
            "description": row["description"] or "",
            "semantic_strength": round(similarity, 6),
        })

    # Sort by semantic_strength descending
    scored.sort(key=lambda x: x["semantic_strength"], reverse=True)

    return scored[:config.FINAL_RESULT_COUNT]


def search(query_vector):
    """Full two-stage search pipeline.

    Args:
        query_vector: numpy array of shape (EMBEDDING_DIMENSION,)

    Returns:
        List of result dicts sorted by semantic_strength, top N.
    """
    print(f"  Stage 1: HNSW search for top {config.HNSW_RECALL_COUNT} candidates ...")
    candidates = hnsw_search(query_vector)
    print(f"  Got {len(candidates)} candidates.")

    print(f"  Stage 2: Exact cosine rerank ...")
    results = rerank_results(candidates, query_vector)
    print(f"  Returning top {len(results)} results.")

    return results