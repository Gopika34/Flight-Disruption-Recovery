"""Per-user encrypted GitHub OAuth credential storage (legacy PATs remain readable)."""
from typing import Optional
from datetime import datetime, timedelta, timezone
import httpx
from app.core.auth import Principal
from app.core.crypto import encrypt, decrypt
from app.services.mongo import get_database

_COLLECTION = "github_credentials"

def _col():
    collection = get_database()[_COLLECTION]
    collection.create_index("owner_id", unique=True)
    return collection

def _validate_token(token: str) -> dict:
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json",
               "X-GitHub-Api-Version": "2022-11-28"}
    try:
        response = httpx.get("https://api.github.com/user", headers=headers, timeout=10.0)
    except httpx.RequestError as exc:
        raise RuntimeError("Could not reach GitHub") from exc
    if response.status_code == 401:
        raise ValueError("Invalid or expired GitHub access token")
    if response.status_code != 200:
        raise RuntimeError(f"GitHub validation failed: {response.status_code}")
    account = response.json()
    return {"login": account.get("login"), "avatar_url": account.get("avatar_url"),
            "html_url": account.get("html_url")}

def store_token(principal: Principal, pat: str) -> dict:
    """Legacy PAT import. Prefer the OAuth authorization-code flow."""
    account = _validate_token(pat)
    _col().replace_one({"owner_id": principal.owner_id}, {
        "owner_id": principal.owner_id, "encrypted_pat": encrypt(pat),
        "account": account, "auth_type": "pat", "updated_at": datetime.now(timezone.utc),
    }, upsert=True)
    return account

def store_oauth_token(owner_id: str, access_token: str, account: dict, scope: str = "",
                      refresh_token: str | None = None, expires_in: int | None = None,
                      refresh_token_expires_in: int | None = None) -> None:
    now = datetime.now(timezone.utc)
    document = {
        "owner_id": owner_id, "encrypted_access_token": encrypt(access_token),
        "account": account, "auth_type": "oauth", "scope": scope,
        "updated_at": now,
        "access_token_expires_at": now + timedelta(seconds=int(expires_in)) if expires_in else None,
        "refresh_token_expires_at": now + timedelta(seconds=int(refresh_token_expires_in)) if refresh_token_expires_in else None,
    }
    if refresh_token:
        document["encrypted_refresh_token"] = encrypt(refresh_token)
    _col().replace_one({"owner_id": owner_id}, document, upsert=True)

def get_account(principal: Principal) -> Optional[dict]:
    document = _col().find_one({"owner_id": principal.owner_id}, {"account": 1, "auth_type": 1})
    if not document:
        return None
    return {**(document.get("account") or {}), "auth_type": document.get("auth_type", "pat")}

def get_access_token(principal: Principal) -> Optional[str]:
    document = _col().find_one({"owner_id": principal.owner_id})
    if not document:
        return None
    encrypted = document.get("encrypted_access_token") or document.get("encrypted_pat")
    return decrypt(encrypted) if encrypted else None

def get_pat(principal: Principal) -> Optional[str]:
    """Deprecated alias retained for compatibility."""
    return get_access_token(principal)

def delete_token(principal: Principal) -> None:
    _col().delete_one({"owner_id": principal.owner_id})


async def get_access_token_async(principal: Principal) -> Optional[str]:
    """Return a usable OAuth token, refreshing it when GitHub issued an expiring token."""
    document = _col().find_one({"owner_id": principal.owner_id})
    if not document:
        return None
    token = get_access_token(principal)
    expires_at = document.get("access_token_expires_at")
    now = datetime.now(timezone.utc)
    if expires_at and expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if not expires_at or expires_at > now + timedelta(seconds=60):
        return token
    encrypted_refresh = document.get("encrypted_refresh_token")
    refresh_expires = document.get("refresh_token_expires_at")
    if refresh_expires and refresh_expires.tzinfo is None:
        refresh_expires = refresh_expires.replace(tzinfo=timezone.utc)
    if not encrypted_refresh or (refresh_expires and refresh_expires <= now):
        raise ValueError("GitHub access token expired; disconnect and reconnect GitHub")
    from app.core import config as C
    if not C.GITHUB_OAUTH_CLIENT_ID or not C.GITHUB_OAUTH_CLIENT_SECRET:
        raise RuntimeError("GitHub OAuth refresh is not configured")
    refresh_token = decrypt(encrypted_refresh)
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(
                "https://github.com/login/oauth/access_token",
                headers={"Accept": "application/json"},
                data={"client_id": C.GITHUB_OAUTH_CLIENT_ID,
                      "client_secret": C.GITHUB_OAUTH_CLIENT_SECRET,
                      "grant_type": "refresh_token",
                      "refresh_token": refresh_token},
            )
            response.raise_for_status()
            data = response.json()
    except httpx.HTTPError as exc:
        raise RuntimeError("Could not refresh GitHub access token") from exc
    new_access = data.get("access_token")
    if not new_access:
        raise RuntimeError("GitHub did not return a refreshed access token")
    now = datetime.now(timezone.utc)
    update = {
        "encrypted_access_token": encrypt(new_access),
        "access_token_expires_at": now + timedelta(seconds=int(data.get("expires_in", 0))) if data.get("expires_in") else None,
        "updated_at": now,
    }
    if data.get("refresh_token"):
        update["encrypted_refresh_token"] = encrypt(data["refresh_token"])
    if data.get("refresh_token_expires_in"):
        update["refresh_token_expires_at"] = now + timedelta(seconds=int(data["refresh_token_expires_in"]))
    _col().update_one({"owner_id": principal.owner_id}, {"$set": update})
    return new_access
