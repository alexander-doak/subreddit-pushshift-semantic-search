"""Embedding model loading and encoding utilities."""

import time
import numpy as np
from sentence_transformers import SentenceTransformer
import config


_model = None


def get_model():
    """Load the embedding model (cached after first call)."""
    global _model
    if _model is None:
        print(f"Loading embedding model: {config.EMBEDDING_MODEL}")
        print(f"Cache directory: {config.MODEL_CACHE_DIR}")
        start = time.time()
        _model = SentenceTransformer(
            config.EMBEDDING_MODEL,
            cache_folder=config.MODEL_CACHE_DIR,
        )
        device = _model.device
        elapsed = time.time() - start
        print(f"Model loaded on {device} in {elapsed:.1f}s")
    return _model


def encode_passages(texts, batch_size=None, show_progress=True):
    """Encode document texts (descriptions) into normalized embedding vectors.

    Prepends 'passage: ' to each text per the E5 model convention.

    Args:
        texts: List of description strings to encode.
        batch_size: Batch size for encoding. Defaults to config value.
        show_progress: Show a progress bar.

    Returns:
        numpy array of shape (len(texts), EMBEDDING_DIMENSION)
    """
    if batch_size is None:
        batch_size = config.EMBED_BATCH_SIZE

    prefixed = [f"passage: {t}" for t in texts]

    model = get_model()
    vecs = model.encode(
        prefixed,
        batch_size=batch_size,
        show_progress_bar=show_progress,
        normalize_embeddings=True,
    )
    return np.array(vecs, dtype=np.float32)


def encode_query(text):
    """Encode a search query into a normalized embedding vector.

    Prepends 'query: ' per the E5 model convention.

    Args:
        text: The search query string.

    Returns:
        numpy array of shape (EMBEDDING_DIMENSION,)
    """
    model = get_model()
    vec = model.encode(
        f"query: {text}",
        normalize_embeddings=True,
    )
    return np.array(vec, dtype=np.float32)