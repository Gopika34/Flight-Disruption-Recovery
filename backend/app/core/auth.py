"""Authentication for Clerk users and signed anonymous guest sessions.

Clerk owns credentials/OAuth. This API only verifies Clerk session JWTs.
Guest tokens are short-lived, signed by this backend, and receive a separate
owner namespace so guests cannot access another guest's MongoDB sessions.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from uuid import uuid4

import jwt
from fastapi import APIRouter, Depends, HTTPException, Request, status
from jwt import PyJWKClient

from app.core import config as C

router = APIRouter(prefix="/auth", tags=["Authentication"])


@dataclass(frozen=True)
class Principal:
    owner_id: str
    kind: str  # "clerk", "guest", or "test"

    @property
    def role(self) -> str:
        from app.core.authz import effective_role
        return effective_role(self)


@lru_cache(maxsize=1)
def _jwks_client() -> PyJWKClient:
    if not C.CLERK_JWKS_URL:
        raise RuntimeError("CLERK_JWKS_URL is not configured")
    return PyJWKClient(C.CLERK_JWKS_URL, cache_keys=True, lifespan=3600)


def _unauthorized(detail: str = "A valid session token is required") -> HTTPException:
    return HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail,
                         headers={"WWW-Authenticate": "Bearer"})


def create_guest_token() -> tuple[str, str, int]:
    if not C.GUEST_TOKEN_SECRET or len(C.GUEST_TOKEN_SECRET) < 32:
        raise RuntimeError("GUEST_TOKEN_SECRET must contain at least 32 characters")
    guest_id = f"guest_{uuid4().hex}"
    expires = datetime.now(timezone.utc) + timedelta(hours=C.GUEST_TOKEN_TTL_HOURS)
    payload = {
        "sub": guest_id,
        "typ": "guest",
        "iat": datetime.now(timezone.utc),
        "exp": expires,
        "iss": C.GUEST_TOKEN_ISSUER,
    }
    token = jwt.encode(payload, C.GUEST_TOKEN_SECRET, algorithm="HS256")
    return token, guest_id, C.GUEST_TOKEN_TTL_HOURS * 3600


@router.post("/guest")
def issue_guest_session():
    """Create a limited anonymous identity. No passenger details are required."""
    if not C.ENABLE_GUEST_MODE:
        raise HTTPException(status_code=404, detail="Guest access is disabled")
    try:
        token, guest_id, expires_in = create_guest_token()
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail="Guest access is not configured") from exc
    return {"access_token": token, "token_type": "bearer", "expires_in": expires_in,
            "user": {"id": guest_id, "type": "guest"}}


def _verify_guest(token: str) -> Principal | None:
    if not C.GUEST_TOKEN_SECRET:
        return None
    try:
        claims = jwt.decode(
            token, C.GUEST_TOKEN_SECRET, algorithms=["HS256"],
            issuer=C.GUEST_TOKEN_ISSUER, options={"require": ["exp", "iat", "sub", "typ"]},
        )
        if claims.get("typ") != "guest" or not str(claims.get("sub", "")).startswith("guest_"):
            return None
        return Principal(owner_id=str(claims["sub"]), kind="guest")
    except jwt.PyJWTError:
        return None


def _verify_clerk(token: str) -> Principal:
    if not C.CLERK_ISSUER_URL or not C.CLERK_JWKS_URL:
        raise _unauthorized("Clerk authentication is not configured")
    try:
        signing_key = _jwks_client().get_signing_key_from_jwt(token)
        claims = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            issuer=C.CLERK_ISSUER_URL.rstrip("/"),
            options={"require": ["exp", "iat", "sub"]},
        )
        # Reject tokens minted for an unexpected frontend origin.
        azp = claims.get("azp")
        if C.AUTHORIZED_PARTIES and azp not in C.AUTHORIZED_PARTIES:
            raise _unauthorized("Token was issued for an untrusted application")
        subject = claims.get("sub")
        if not isinstance(subject, str) or not subject.startswith("user_"):
            raise _unauthorized()
        return Principal(owner_id=subject, kind="clerk")
    except HTTPException:
        raise
    except Exception as exc:
        raise _unauthorized("Invalid or expired Clerk session") from exc


def get_current_principal(request: Request) -> Principal:
    authorization = request.headers.get("authorization", "")
    if not authorization.startswith("Bearer "):
        # Unit tests may use the test environment without provisioning auth.
        if C.ENVIRONMENT == "test":
            return Principal(owner_id="test_user", kind="test")
        raise _unauthorized()
    token = authorization[7:].strip()
    if not token:
        raise _unauthorized()
    guest = _verify_guest(token)
    if guest:
        return guest
    return _verify_clerk(token)


def get_optional_principal(request: Request) -> Principal | None:
    """Authenticate when a bearer token exists; otherwise return None."""
    authorization = request.headers.get("authorization", "")
    if not authorization.startswith("Bearer "):
        return None
    try:
        return get_current_principal(request)
    except HTTPException:
        return None
