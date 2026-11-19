# backend/app/services/mongo.py

import os
from functools import lru_cache

from pymongo import MongoClient
from pymongo.database import Database
from app.rag.retriever import get_database

@lru_cache(maxsize=1)
def get_mongo_client() -> MongoClient:
    mongo_uri = os.getenv("MONGODB_URI")

    if not mongo_uri:
        raise RuntimeError("MONGODB_URI is not configured")

    return MongoClient(
        mongo_uri,
        serverSelectionTimeoutMS=5000,
    )


def get_database() -> Database:
    return _get_shared_database()


def close_mongo_connection() -> None:
    if get_mongo_client.cache_info().currsize:
        get_mongo_client().close()
        get_mongo_client.cache_clear()
