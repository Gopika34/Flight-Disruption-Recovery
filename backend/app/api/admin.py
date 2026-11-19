"""Minimal admin-only audit inspection endpoint."""
from fastapi import APIRouter, Depends, Query
from app.core.auth import Principal
from app.core.authz import require_role
from app.rag.retriever import get_database

router = APIRouter(prefix="/admin", tags=["Administration"])

@router.get("/audit")
def list_audit_logs(limit: int = Query(50, ge=1, le=200),
                   principal: Principal = Depends(require_role("admin"))):
    cursor = get_database()["security_audit_logs"].find({}, {"_id": 0}).sort("created_at", -1).limit(limit)
    return {"events": list(cursor)}
