import jwt
from fastapi.testclient import TestClient

import app.main as main
from app.core import auth
from app.core import config as C

client = TestClient(main.app)


def test_guest_token_is_signed_and_has_separate_identity(monkeypatch):
    monkeypatch.setattr(C, "GUEST_TOKEN_SECRET", "x" * 48)
    token, guest_id, expires_in = auth.create_guest_token()
    principal = auth._verify_guest(token)
    assert principal is not None
    assert principal.owner_id == guest_id
    assert principal.kind == "guest"
    assert expires_in == C.GUEST_TOKEN_TTL_HOURS * 3600


def test_guest_endpoint_returns_bearer_token(monkeypatch):
    monkeypatch.setattr(C, "GUEST_TOKEN_SECRET", "x" * 48)
    response = client.post("/api/auth/guest")
    assert response.status_code == 200
    data = response.json()
    assert data["token_type"] == "bearer"
    assert data["user"]["type"] == "guest"
    assert auth._verify_guest(data["access_token"]).owner_id == data["user"]["id"]


def test_tampered_guest_token_is_rejected(monkeypatch):
    monkeypatch.setattr(C, "GUEST_TOKEN_SECRET", "x" * 48)
    token, _, _ = auth.create_guest_token()
    tampered = token[:-2] + "ab"
    assert auth._verify_guest(tampered) is None
