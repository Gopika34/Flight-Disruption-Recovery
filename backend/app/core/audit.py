
"""Best-effort security audit logging.

Never persist OAuth tokens, secrets, or raw tool arguments.
"""

from datetime import datetime, timezone
import logging

logger = logging.getLogger(__name__)

COLLECTION = "security_audit_logs"


def record_audit(
    *,
    owner_id: str,
    action: str,
    resource: str,
    outcome: str,
    metadata: dict | None = None,
) -> None:
    """Record a security event without breaking the main request."""

    event = {
        "owner_id": owner_id,
        "action": action,
        "resource": resource,
        "outcome": outcome,
        "metadata": metadata or {},
        "created_at": datetime.now(timezone.utc),
    }

    try:
        # Lazy import prevents module-level circular dependencies.
        from app.rag.retriever import get_database

        db = get_database()
        db[COLLECTION].insert_one(event)

    except Exception:
        logger.exception(
            "Audit write failed: action=%s resource=%s",
            action,
            resource,
        )
