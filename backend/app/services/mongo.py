
"""Shared MongoDB connection wrapper used by FlightGuard services."""

from pymongo.database import Database

from app.rag.retriever import (
    get_database as _get_shared_database,
    close_client,
)


def get_database() -> Database:
    """Return the application's shared MongoDB database."""
    return _get_shared_database()


def close_mongo_connection() -> None:
    """Close the shared MongoDB client during application shutdown."""
    close_client()
