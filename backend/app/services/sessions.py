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


def load_messages(session_id: str) -> list[dict]:
    """Retrieve full conversation messages for a session."""
    try:
        doc = _sessions().find_one({"_id": session_id}, {"messages": 1})
        return (doc or {}).get("messages", [])
    except PyMongoError as exc:
        raise RuntimeError("Could not load session messages from MongoDB.") from exc


def save_messages(session_id: str, messages: list[dict]) -> None:
    """Save full conversation messages for a session."""
    now = datetime.now(timezone.utc)
    try:
        _sessions().update_one(
            {"_id": session_id},
            {
                "$set": {
                    "messages": messages,
                    "updated_at": now,
                    "expires_at": now + timedelta(days=SESSION_TTL_DAYS),
                },
                "$setOnInsert": {"created_at": now},
            },
            upsert=True,
        )
    except PyMongoError as exc:
        raise RuntimeError("Could not save session messages to MongoDB.") from exc


def append_message(session_id: str, message: dict) -> None:
    """Atomically append a single message to a session's history."""
    now = datetime.now(timezone.utc)
    try:
        _sessions().update_one(
            {"_id": session_id},
            {
                "$push": {"messages": message},
                "$set": {
                    "updated_at": now,
                    "expires_at": now + timedelta(days=SESSION_TTL_DAYS),
                },
                "$setOnInsert": {"created_at": now, "facts": {}},
            },
            upsert=True,
        )
    except PyMongoError as exc:
        raise RuntimeError("Could not append message to session in MongoDB.") from exc


def load_session(session_id: str) -> dict:
    """Retrieve both facts and message history for a session."""
    try:
        doc = _sessions().find_one({"_id": session_id})
        if not doc:
            return {"facts": {}, "messages": []}
        return {
            "facts": doc.get("facts", {}),
            "messages": doc.get("messages", []),
        }
    except PyMongoError as exc:
        raise RuntimeError("Could not load session from MongoDB.") from exc


def close_session_cache() -> None:
    _sessions.cache_clear()