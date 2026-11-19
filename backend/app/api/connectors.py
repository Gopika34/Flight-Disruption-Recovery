"""User-scoped connector APIs and GitHub OAuth lifecycle."""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field
from app.core.auth import get_current_principal, Principal
from app.core.authz import require_permission
from app.core.audit import record_audit
from app.core.config import GITHUB_MCP_ENABLED
from app.services.github_connector import get_account, delete_token, get_access_token
from app.services.github_oauth import build_authorization_url, complete_authorization, revoke_access_token
from app.services.github_connector import store_token

router = APIRouter(prefix="/connectors", tags=["Connectors"])

class GitHubConnectRequest(BaseModel):
    personal_access_token: str = Field(..., min_length=1, max_length=500)

@router.post("/github/oauth/start")
def github_oauth_start(principal: Principal = Depends(require_permission("connector:github:connect"))):
    return {"authorization_url": build_authorization_url(principal.owner_id)}

@router.get("/github/oauth/callback")
async def github_oauth_callback(code: str = Query(min_length=1), state: str = Query(min_length=16)):
    account = await complete_authorization(code, state)
    # Frontend can poll connector status after this redirect. Configure the frontend URL explicitly.
    from app.core.config import FRONTEND_URL
    return RedirectResponse(url=f"{FRONTEND_URL.rstrip('/')}/integrations?github_connected=1", status_code=303)

@router.post("/github/connect", status_code=status.HTTP_201_CREATED, deprecated=True)
def github_connect(payload: GitHubConnectRequest,
                   principal: Principal = Depends(require_permission("connector:github:connect"))):
    """Legacy PAT import is disabled by default; OAuth is the supported flow."""
    from app.core.config import ALLOW_GITHUB_PAT_IMPORT
    if not ALLOW_GITHUB_PAT_IMPORT:
        raise HTTPException(status_code=410, detail="PAT import is disabled. Connect GitHub using OAuth instead.")
    try:
        account = store_token(principal, payload.personal_access_token)
        record_audit(owner_id=principal.owner_id, action="connector.connect", resource="github", outcome="success", metadata={"method": "pat"})
        return {"provider": "github", "connected": True, "account": account}
    except ValueError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail="GitHub connection failed") from exc

@router.get("/github/status")
def github_status(principal: Principal = Depends(require_permission("connector:github:read"))):
    account = get_account(principal)
    return {"provider": "github", "connected": bool(account), "account": account}

@router.delete("/github")
async def github_disconnect(principal: Principal = Depends(require_permission("connector:github:disconnect"))):
    token = None
    try:
        token = get_access_token(principal)
    except Exception:
        record_audit(owner_id=principal.owner_id, action="connector.credential_read", resource="github", outcome="failed")
    # Revoke remotely where possible. Local deletion is unconditional so a bad
    # or undecryptable token can never trap the user in a connected state.
    if token:
        try:
            await revoke_access_token(token)
        except Exception:
            record_audit(owner_id=principal.owner_id, action="connector.revoke", resource="github", outcome="failed")
    delete_token(principal)
    record_audit(owner_id=principal.owner_id, action="connector.disconnect", resource="github", outcome="success")
    return {"provider": "github", "connected": False}

@router.get("")
def list_connectors(principal: Principal = Depends(get_current_principal)):
    github = get_account(principal) if principal.kind != "guest" else None
    return {"connectors": [
        {"id": "github", "name": "GitHub", "status": "Connected" if github else "Not connected",
         "available": GITHUB_MCP_ENABLED and principal.kind != "guest", "auth_type": github.get("auth_type") if github else None},
        {"id": "supabase", "name": "Supabase", "status": "Coming soon", "available": False},
        {"id": "gmail", "name": "Gmail", "status": "Coming soon", "available": False},
        {"id": "google_drive", "name": "Google Drive", "status": "Coming soon", "available": False},
        {"id": "notion", "name": "Notion", "status": "Coming soon", "available": False},
        {"id": "slack", "name": "Slack", "status": "Coming soon", "available": False},
        {"id": "linear", "name": "Linear", "status": "Coming soon", "available": False},
    ]}
