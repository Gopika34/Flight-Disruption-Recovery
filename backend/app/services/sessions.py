"""MongoDB-backed passenger conversation sessions."""
from datetime import datetime, timedelta, timezone
from functools import lru_cache

from pymongo import ASCENDING
from pymongo.errors import PyMongoError

from app.core.config import MONGO_DB, SESSION_TTL_DAYS
from app.rag.retriever import get_database

COLLECTION = "passenger_sessions"


@lru_cache(maxsize=1)
def _sessions():
    collection = get_database()[COLLECTION]
    # MongoDB automatically removes expired sessions. This index is created once
    # per process and is safe to call again on subsequent application starts.
    collection.create_index([("expires_at", ASCENDING)], expireAfterSeconds=0)
    return collection


def load_facts(session_id: str) -> dict:
    try:
        doc = _sessions().find_one({"_id": session_id}, {"facts": 1})
        return (doc or {}).get("facts", {})
    except PyMongoError as exc:
        raise RuntimeError("Could not load the passenger session from MongoDB.") from exc


def save_facts(session_id: str, facts: dict) -> None:
    now = datetime.now(timezone.utc)
    try:
        _sessions().update_one(
            {"_id": session_id},
            {
                "$set": {
                    "facts": facts,
                    "updated_at": now,
                    "expires_at": now + timedelta(days=SESSION_TTL_DAYS),
                },
                "$setOnInsert": {"created_at": now},
            },
            upsert=True,
        )
    except PyMongoError as exc:
        raise RuntimeError("Could not save the passenger session to MongoDB.") from exc


def close_session_cache() -> None:
    _sessions.cache_clear()