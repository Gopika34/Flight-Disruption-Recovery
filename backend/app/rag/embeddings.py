import logging
import random
import time
from functools import lru_cache

from google import genai
from google.genai import types
from app.core.config import (
    EMBED_BATCH_SIZE,
    EMBED_DIMS,
    EMBED_MODEL,
    EMBED_RETRIES,
    GEMINI_API_KEY,
)

logger = logging.getLogger(__name__)


class EmbeddingError(RuntimeError):
    """Embeddings could not be produced or failed validation."""


@lru_cache(maxsize=1)
def _get_client():
    """Create the Gemini client on first use, not at import time."""
    if not GEMINI_API_KEY:
        raise EmbeddingError("GEMINI_API_KEY is not configured.")
    return genai.Client(api_key=GEMINI_API_KEY)


def _sleep_backoff(attempt: int) -> None:
    # 1s, 2s, 4s... plus jitter so parallel retries don't all collide.
    time.sleep((2 ** attempt) + random.uniform(0, 1))


def _embed_batch(texts: list[str], task_type: str) -> list[list[float]]:
    """Embed one batch with retries; validate count and dimensions."""
    last_error = None

    for attempt in range(EMBED_RETRIES):
        try:
            result = _get_client().models.embed_content(
                model=EMBED_MODEL,
                contents=texts,
                config=types.EmbedContentConfig(
                    task_type=task_type,
                    output_dimensionality=EMBED_DIMS,
                ),
            )
            vectors = [list(e.values) for e in (result.embeddings or [])]
            break
        except EmbeddingError:
            raise
        except Exception as error:
            last_error = error
            logger.warning("Embedding attempt %d failed: %s", attempt + 1, type(error).__name__)
            if attempt < EMBED_RETRIES - 1:
                _sleep_backoff(attempt)
    else:
        raise EmbeddingError("Embedding request failed after retries.") from last_error

    if len(vectors) != len(texts):
        raise EmbeddingError(
            f"Expected {len(texts)} embeddings but received {len(vectors)}."
        )

    for index, vector in enumerate(vectors):
        if len(vector) != EMBED_DIMS:
            raise EmbeddingError(
                f"Embedding {index} has {len(vector)} dimensions, expected {EMBED_DIMS}."
            )

    return vectors


def embed_documents(texts, batch_size=None):
    """Embed many texts in batches. Output order always matches input order."""
    texts = list(texts)
    size = batch_size or EMBED_BATCH_SIZE
    if size < 1:
        raise ValueError("batch_size must be at least 1")

    vectors: list[list[float]] = []
    for start in range(0, len(texts), size):
        vectors.extend(_embed_batch(texts[start:start + size], "RETRIEVAL_DOCUMENT"))

    if len(vectors) != len(texts):
        raise EmbeddingError("Embedding count does not match input count.")
    return vectors


@lru_cache(maxsize=256)
def embed_query(text):
    return _embed_batch([text], "RETRIEVAL_QUERY")[0]
