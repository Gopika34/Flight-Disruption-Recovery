"""Owner-scoped conversation session endpoints."""
from fastapi import APIRouter, Depends, HTTPException
from app.core.auth import Principal
from app.core.authz import require_permission
from app.core.audit import record_audit
from app.services.sessions import load_session, delete_session

router = APIRouter(prefix="/sessions", tags=["Sessions"])

@router.get("/{session_id}")
def get_owned_session(session_id: str, principal: Principal = Depends(require_permission("session:read"))):
    data = load_session(session_id, principal.owner_id)
    # A non-existent session and a foreign session are both hidden from the caller.
    from app.services.sessions import _sessions
    exists = _sessions().find_one({"_id": session_id, "owner_id": principal.owner_id}, {"_id": 1})
    if not exists:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"session_id": session_id, **data}

@router.delete("/{session_id}")
def remove_owned_session(session_id: str, principal: Principal = Depends(require_permission("session:write"))):
    deleted = delete_session(session_id, principal.owner_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Session not found")
    record_audit(owner_id=principal.owner_id, action="session.delete", resource="session", outcome="success")
    return {"deleted": True, "session_id": session_id}
