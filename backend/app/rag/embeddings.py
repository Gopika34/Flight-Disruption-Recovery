import time
from google import genai
from google.genai import types
from app.core.config import GEMINI_API_KEY, EMBED_MODEL, EMBED_DIMS
from functools import lru_cache

_client = genai.Client(api_key=GEMINI_API_KEY)


def _embed_one(text, task_type, retries=3):
    for attempt in range(retries):
        try:
            result = _client.models.embed_content(
                model=EMBED_MODEL,
                contents=text,
                config=types.EmbedContentConfig(
                    task_type=task_type,
                    output_dimensionality=EMBED_DIMS,
                ),
            )
            return result.embeddings[0].values
        except Exception:
            if attempt == retries - 1:
                raise
            time.sleep(2 * (attempt + 1))     # back off, then retry


def embed_documents(texts):
    return [_embed_one(t, "RETRIEVAL_DOCUMENT") for t in texts]

@lru_cache(maxsize=256)

def embed_query(text):
    return _embed_one(text, "RETRIEVAL_QUERY")