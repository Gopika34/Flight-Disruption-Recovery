import logging
from functools import lru_cache

from pymongo import MongoClient
from pymongo.errors import PyMongoError

from app.core.config import MONGO_DB, MONGO_TIMEOUT_MS, MONGO_URI
from app.rag.embeddings import EmbeddingError, embed_query

logger = logging.getLogger(__name__)

INDEX_NAME = "policy_vector_index"
COLLECTION = "policy_chunks"

MAX_K = 20
MAX_TOTAL = 50


class RetrievalUnavailable(RuntimeError):
    """The policy store or embedding service could not be used.

    Different from 'no relevant clauses found', which is an empty list.
    """


@lru_cache(maxsize=1)
def _get_client():
    """One pooled MongoDB client, created on first use (not at import)."""
    if not MONGO_URI or not MONGO_DB:
        raise RetrievalUnavailable("MongoDB is not configured (MONGO_URI / MONGO_DB).")
    return MongoClient(MONGO_URI, serverSelectionTimeoutMS=MONGO_TIMEOUT_MS)


def get_database():
    """Return the configured database using the shared pooled Mongo client."""
    return _get_client()[MONGO_DB]


def _collection():
    return get_database()[COLLECTION]


def close_client() -> None:
    """Close the pooled client (call on app shutdown)."""
    if _get_client.cache_info().currsize:
        _get_client().close()
        _get_client.cache_clear()


def db_available() -> bool:
    try:
        _get_client().admin.command("ping")
        return True
    except (PyMongoError, RetrievalUnavailable):
        return False


def vector_index_status() -> str:
    """'ready' | 'building' | 'missing' | 'unavailable'."""
    try:
        for index in _collection().list_search_indexes(INDEX_NAME):
            if index.get("queryable"):
                return "ready"
            return "building"
        return "missing"
    except (PyMongoError, RetrievalUnavailable):
        return "unavailable"


# Map user language to the corresponding CAR section.
TOPIC_SECTIONS = {
    "cancellation": {
        "section": "Cancellation of Flight",
        "keywords": ("cancel", "cancell"),
    },
    "delay": {
        "section": "Delays in Flight",
        "keywords": ("delay", "delayed"),
    },
    "denied_boarding": {
        "section": "Denied Boarding",
        "keywords": ("denied boarding", "overbook"),
    },
    "downgrading": {
        "section": "Downgrading",
        "keywords": ("downgrad",),
    },
}


# Clauses that legally or operationally support one another.
RELATED = {
    "3.2.2": ["3.2.1"],
    "3.3.1": ["3.3.2"],
    "3.3.2": ["3.3.1", "3.3.3", "3.3.4", "3.3.5"],
    "3.3.4": ["3.3.2", "3.3.5"],
    "3.4.1": ["3.4.4", "3.8.1"],
    "3.4.2": ["3.4.4"],
    "3.4.3": ["3.4.4", "3.8.1"],
}


def identify_topics(query):
    """Identify policy topics explicitly mentioned in the query."""
    q = query.lower()

    return [
        topic
        for topic, details in TOPIC_SECTIONS.items()
        if any(keyword in q for keyword in details["keywords"])
    ]


def filter_by_topic(hits, query):
    """
    Keep vector results belonging to the identified policy topic.

    Relevant definitions are retained when their text mentions
    the topic. Unknown or ambiguous queries are not filtered.
    """
    topics = identify_topics(query)

    if not topics:
        return hits

    allowed_sections = {TOPIC_SECTIONS[topic]["section"] for topic in topics}

    topic_keywords = tuple(
        keyword
        for topic in topics
        for keyword in TOPIC_SECTIONS[topic]["keywords"]
    )

    filtered = []

    for hit in hits:
        section = hit.get("section_title", "")

        if section in allowed_sections:
            filtered.append(hit)

        elif section == "Definitions":
            text = hit.get("text", "").lower()

            if any(keyword in text for keyword in topic_keywords):
                filtered.append(hit)

    return filtered


def _check_int(name, value, low, high):
    if not isinstance(value, int) or isinstance(value, bool) or not low <= value <= high:
        raise ValueError(f"{name} must be an integer between {low} and {high}")


def search_policy(query, k=4):
    """Retrieve the top-k policy clauses using MongoDB vector search.

    Returns [] when nothing matches. Raises RetrievalUnavailable when
    retrieval itself failed (DB down, embeddings down, index missing).
    """
    _check_int("k", k, 1, MAX_K)

    try:
        vector = embed_query(query)
    except EmbeddingError as error:
        raise RetrievalUnavailable("Embedding service unavailable.") from error

    pipeline = [
        {
            "$vectorSearch": {
                "index": INDEX_NAME,
                "path": "embedding",
                "queryVector": vector,
                "numCandidates": max(50, k * 10),
                "limit": k,
            }
        },
        {
            "$project": {
                "_id": 0,
                "clause_id": 1,
                "section_title": 1,
                "page_start": 1,
                "page_end": 1,
                "text": 1,
                "document_id": 1,
                "document_title": 1,
                "issuing_authority": 1,
                "document_version": 1,
                "publication_date": 1,
                "effective_date": 1,
                "content_hash": 1,
                "verified": 1,
                "score": {"$meta": "vectorSearchScore"},
            }
        },
    ]

    try:
        return list(_collection().aggregate(pipeline))
    except PyMongoError as error:
        # An unavailable DB and a missing index both end up here.
        status = vector_index_status()
        if status in ("missing", "building"):
            raise RetrievalUnavailable(f"Vector index is {status}.") from error
        raise RetrievalUnavailable("Policy database unavailable.") from error


def get_clause(clause_id):
    """Retrieve one exact clause without its embedding.

    Returns None if the clause does not exist.
    Raises RetrievalUnavailable if the database could not be queried.
    """
    try:
        return _collection().find_one(
            {"clause_id": clause_id},
            {"_id": 0, "embedding": 0},
        )
    except PyMongoError as error:
        raise RetrievalUnavailable("Policy database unavailable.") from error


def search_with_related(query, k=4, max_total=8):
    """
    Retrieve relevant vector matches, then expand their related clauses.

    Related expansion only starts from vector results that survive
    topic filtering.
    """
    _check_int("k", k, 1, MAX_K)
    _check_int("max_total", max_total, 1, MAX_TOTAL)

    hits = search_policy(query, k)

    # Step 1: Filter unrelated vector results.
    hits = filter_by_topic(hits, query)

    # Step 2: Mark the retrieval source.
    for hit in hits:
        hit["retrieved_by"] = "vector"

    # Step 3: Collect related clauses only from retained results.
    have = {hit["clause_id"] for hit in hits}

    extra_ids = []

    for hit in hits:
        for related_id in RELATED.get(hit["clause_id"], []):
            if related_id not in have and related_id not in extra_ids:
                extra_ids.append(related_id)

    # Step 4: Fetch related clauses, avoiding duplicates.
    for related_id in extra_ids:
        if len(hits) >= max_total:
            break

        clause = get_clause(related_id)

        if clause:
            clause["score"] = None
            clause["retrieved_by"] = "related"
            hits.append(clause)

    return hits[:max_total]
