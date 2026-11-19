"""Server-side role and permission checks for FlightGuard."""
from __future__ import annotations
import os
from fastapi import Depends, HTTPException, status
from app.core.auth import Principal, get_current_principal

ROLE_PERMISSIONS = {
    "guest": {"flight:read", "policy:read", "agent:use"},
    "user": {"flight:read", "policy:read", "agent:use", "recovery:use", "session:read", "session:write",
             "connector:github:connect", "connector:github:read", "connector:github:disconnect",
             "mcp:github:list_repositories", "mcp:github:read_repository_file",
             "mcp:github:search_code", "mcp:github:list_issues"},
    "admin": {"*"},
}


def effective_role(principal: Principal) -> str:
    if principal.kind == "guest":
        return "guest"
    admins = {item.strip() for item in os.getenv("ADMIN_USER_IDS", "").split(",") if item.strip()}
    return "admin" if principal.owner_id in admins else "user"


def has_permission(principal: Principal, permission: str) -> bool:
    role = effective_role(principal)
    permissions = ROLE_PERMISSIONS.get(role, set())
    return "*" in permissions or permission in permissions


def require_permission(permission: str):
    def dependency(principal: Principal = Depends(get_current_principal)) -> Principal:
        if not has_permission(principal, permission):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                                detail=f"Permission denied: {permission}")
        return principal
    return dependency


def require_role(*roles: str):
    def dependency(principal: Principal = Depends(get_current_principal)) -> Principal:
        if effective_role(principal) not in roles:
            raise HTTPException(status_code=403, detail="Insufficient role")
        return principal
    return dependency
