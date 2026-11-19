"""GitHub App user-authorization code flow with state and PKCE S256."""
from __future__ import annotations
import secrets
import hashlib
import base64
from datetime import datetime, timedelta, timezone
import httpx
from fastapi import HTTPException
from app.core import config as C
from app.core.audit import record_audit
from app.services.mongo import get_database
from app.services.github_connector import store_oauth_token

STATES = "github_oauth_states"

def _state_collection():
    col = get_database()[STATES]
    col.create_index("state", unique=True)
    col.create_index("expires_at", expireAfterSeconds=0)
    return col

def build_authorization_url(owner_id: str) -> str:
    if not C.GITHUB_OAUTH_CLIENT_ID or not C.GITHUB_OAUTH_REDIRECT_URI:
        raise HTTPException(status_code=503, detail="GitHub OAuth is not configured")
    state = secrets.token_urlsafe(32)
    verifier = secrets.token_urlsafe(64)
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip("=")
    now = datetime.now(timezone.utc)
    _state_collection().insert_one({"state": state, "code_verifier": verifier, "owner_id": owner_id,
                                     "created_at": now,
                                     "expires_at": now + timedelta(minutes=10)})
    from urllib.parse import urlencode
    params = {"client_id": C.GITHUB_OAUTH_CLIENT_ID,
              "redirect_uri": C.GITHUB_OAUTH_REDIRECT_URI,
              "scope": C.GITHUB_OAUTH_SCOPES,
              "state": state,
              "code_challenge": challenge,
              "code_challenge_method": "S256"}
    return "https://github.com/login/oauth/authorize?" + urlencode(params)

async def complete_authorization(code: str, state: str) -> dict:
    if not C.GITHUB_OAUTH_CLIENT_ID or not C.GITHUB_OAUTH_CLIENT_SECRET:
        raise HTTPException(status_code=503, detail="GitHub OAuth is not configured")
    record = _state_collection().find_one_and_delete({"state": state})
    expires_at = record.get("expires_at") if record else None
    if expires_at and expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if not record or not expires_at or expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="Invalid or expired OAuth state")
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            token_response = await client.post(
                "https://github.com/login/oauth/access_token",
                headers={"Accept": "application/json"},
                data={"client_id": C.GITHUB_OAUTH_CLIENT_ID,
                      "client_secret": C.GITHUB_OAUTH_CLIENT_SECRET,
                      "code": code, "redirect_uri": C.GITHUB_OAUTH_REDIRECT_URI,
                      "code_verifier": record["code_verifier"]},
            )
            token_response.raise_for_status()
            token_data = token_response.json()
            access_token = token_data.get("access_token")
            if not access_token:
                raise HTTPException(status_code=400, detail="GitHub did not return an access token")
            user_response = await client.get(
                "https://api.github.com/user",
                headers={"Authorization": f"Bearer {access_token}",
                         "Accept": "application/vnd.github+json",
                         "X-GitHub-Api-Version": "2022-11-28"},
            )
            user_response.raise_for_status()
            user = user_response.json()
    except HTTPException:
        raise
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail="GitHub OAuth exchange failed") from exc
    owner_id = record["owner_id"]
    account = {"login": user.get("login"), "avatar_url": user.get("avatar_url"),
               "html_url": user.get("html_url")}
    store_oauth_token(owner_id, access_token, account, token_data.get("scope", ""),
                      refresh_token=token_data.get("refresh_token"),
                      expires_in=token_data.get("expires_in"),
                      refresh_token_expires_in=token_data.get("refresh_token_expires_in"))
    record_audit(owner_id=owner_id, action="connector.connect", resource="github", outcome="success")
    return account

async def revoke_access_token(access_token: str) -> bool:
    """Revoke a classic GitHub OAuth App grant when credentials are configured."""
    if not C.GITHUB_OAUTH_CLIENT_ID or not C.GITHUB_OAUTH_CLIENT_SECRET:
        return False
    async with httpx.AsyncClient(timeout=10.0, auth=(C.GITHUB_OAUTH_CLIENT_ID, C.GITHUB_OAUTH_CLIENT_SECRET)) as client:
        response = await client.delete(
            f"https://api.github.com/applications/{C.GITHUB_OAUTH_CLIENT_ID}/grant",
            json={"access_token": access_token},
            headers={"Accept": "application/vnd.github+json"},
        )
    return response.status_code in {204, 404}
