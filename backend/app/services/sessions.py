"""MongoDB-backed passenger sessions with strict per-principal ownership."""
from datetime import datetime, timedelta, timezone
from functools import lru_cache

from pymongo import ASCENDING
from pymongo.errors import PyMongoError
from fastapi import HTTPException

from app.core.config import SESSION_TTL_DAYS
from app.rag.retriever import get_database

COLLECTION = "passenger_sessions"


@lru_cache(maxsize=1)
def _sessions():
    collection = get_database()[COLLECTION]
    collection.create_index([("expires_at", ASCENDING)], expireAfterSeconds=0)
    collection.create_index([("owner_id", ASCENDING), ("updated_at", -1)])
    return collection


def _assert_owner(session_id: str, owner_id: str) -> None:
    existing = _sessions().find_one({"_id": session_id}, {"owner_id": 1})
    if existing and existing.get("owner_id") != owner_id:
        raise HTTPException(status_code=404, detail="Session not found")


def _upsert_filter(session_id: str, owner_id: str) -> dict:
    _assert_owner(session_id, owner_id)
    return {"_id": session_id, "owner_id": owner_id}


def load_facts(session_id: str, owner_id: str = "legacy_unowned") -> dict:
    try:
        _assert_owner(session_id, owner_id)
        doc = _sessions().find_one({"_id": session_id, "owner_id": owner_id}, {"facts": 1})
        return (doc or {}).get("facts", {})
    except HTTPException:
        raise
    except PyMongoError as exc:
        raise RuntimeError("Could not load the passenger session from MongoDB.") from exc


def save_facts(session_id: str, facts: dict, owner_id: str = "legacy_unowned") -> None:
    now = datetime.now(timezone.utc)
    try:
        _sessions().update_one(
            _upsert_filter(session_id, owner_id),
            {"$set": {"facts": facts, "updated_at": now,
                      "expires_at": now + timedelta(days=SESSION_TTL_DAYS)},
             "$setOnInsert": {"created_at": now, "owner_id": owner_id}},
            upsert=True,
        )
    except (PyMongoError, HTTPException) as exc:
        if isinstance(exc, HTTPException):
            raise
        raise RuntimeError("Could not save the passenger session to MongoDB.") from exc


def load_messages(session_id: str, owner_id: str = "legacy_unowned") -> list[dict]:
    try:
        _assert_owner(session_id, owner_id)
        doc = _sessions().find_one({"_id": session_id, "owner_id": owner_id}, {"messages": 1})
        return (doc or {}).get("messages", [])
    except PyMongoError as exc:
        raise RuntimeError("Could not load session messages from MongoDB.") from exc


def save_messages(session_id: str, messages: list[dict], owner_id: str = "legacy_unowned") -> None:
    now = datetime.now(timezone.utc)
    try:
        _sessions().update_one(
            _upsert_filter(session_id, owner_id),
            {"$set": {"messages": messages, "updated_at": now,
                      "expires_at": now + timedelta(days=SESSION_TTL_DAYS)},
             "$setOnInsert": {"created_at": now, "owner_id": owner_id}},
            upsert=True,
        )
    except (PyMongoError, HTTPException) as exc:
        if isinstance(exc, HTTPException):
            raise
        raise RuntimeError("Could not save session messages to MongoDB.") from exc


def append_message(session_id: str, message: dict, owner_id: str = "legacy_unowned") -> None:
    now = datetime.now(timezone.utc)
    try:
        _sessions().update_one(
            _upsert_filter(session_id, owner_id),
            {"$push": {"messages": message},
             "$set": {"updated_at": now, "expires_at": now + timedelta(days=SESSION_TTL_DAYS)},
             "$setOnInsert": {"created_at": now, "facts": {}, "owner_id": owner_id}},
            upsert=True,
        )
    except (PyMongoError, HTTPException) as exc:
        if isinstance(exc, HTTPException):
            raise
        raise RuntimeError("Could not append message to session in MongoDB.") from exc


def load_session(session_id: str, owner_id: str = "legacy_unowned") -> dict:
    try:
        doc = _sessions().find_one({"_id": session_id, "owner_id": owner_id})
        if not doc:
            return {"facts": {}, "messages": []}
        return {"facts": doc.get("facts", {}), "messages": doc.get("messages", [])}
    except PyMongoError as exc:
        raise RuntimeError("Could not load session from MongoDB.") from exc


def close_session_cache() -> None:
    _sessions.cache_clear()


def delete_session(session_id: str, owner_id: str) -> bool:
    """Delete only a session owned by the supplied principal."""
    try:
        result = _sessions().delete_one({"_id": session_id, "owner_id": owner_id})
        return result.deleted_count == 1
    except PyMongoError as exc:
        raise RuntimeError("Could not delete session from MongoDB.") from exc
