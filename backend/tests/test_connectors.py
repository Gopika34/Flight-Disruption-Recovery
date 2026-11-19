
# backend/tests/test_connectors.py

import mongomock
import pytest

from cryptography.fernet import Fernet
from fastapi.testclient import TestClient

from app.main import app
from app.core.auth import get_current_principal, Principal
from app.services import github_connector
from app.core import config


@pytest.fixture(autouse=True)
def setup_test_environment(monkeypatch):
    # Give the test a valid encryption key.
    monkeypatch.setattr(
        config,
        "GITHUB_TOKEN_ENCRYPTION_KEY",
        Fernet.generate_key().decode(),
    )
    monkeypatch.setattr(config, "ALLOW_GITHUB_PAT_IMPORT", True, raising=False)

    # Use an in-memory MongoDB mock.
    mongo_client = mongomock.MongoClient()
    test_db = mongo_client["test_fligh_rag"]

    monkeypatch.setattr(
        github_connector,
        "get_database",
        lambda: test_db,
    )

    # Use a predictable authenticated test user.
    app.dependency_overrides[get_current_principal] = lambda: Principal(
        owner_id="test_user_1",
        kind="test",
    )

    yield

    app.dependency_overrides.clear()
    mongo_client.close()


@pytest.fixture
def client():
    return TestClient(app)


def github_success(*args, **kwargs):
    class Response:
        status_code = 200

        def json(self):
            return {
                "login": "testuser",
                "avatar_url": "https://example.com/avatar.png",
            }

    return Response()


def github_unauthorized(*args, **kwargs):
    class Response:
        status_code = 401

    return Response()


def test_github_connect_success(client, monkeypatch):
    monkeypatch.setattr(
        "app.services.github_connector.httpx.get",
        github_success,
    )

    response = client.post(
        "/connectors/github/connect",
        json={"personal_access_token": "test-pat"},
    )

    assert response.status_code == 201

    data = response.json()

    assert data["provider"] == "github"
    assert data["connected"] is True
    assert data["account"]["login"] == "testuser"

    # Make sure the raw PAT was not returned.
    assert "test-pat" not in response.text


def test_github_connect_invalid_pat(client, monkeypatch):
    monkeypatch.setattr(
        "app.services.github_connector.httpx.get",
        github_unauthorized,
    )

    response = client.post(
        "/connectors/github/connect",
        json={"personal_access_token": "bad-pat"},
    )

    assert response.status_code == 401
    assert "Invalid or expired" in response.json()["detail"]


def test_github_status_not_connected(client):
    response = client.get("/connectors/github/status")

    assert response.status_code == 200
    assert response.json()["connected"] is False


def test_github_disconnect(client, monkeypatch):
    monkeypatch.setattr(
        "app.services.github_connector.httpx.get",
        github_success,
    )

    connect_response = client.post(
        "/connectors/github/connect",
        json={"personal_access_token": "test-pat"},
    )

    assert connect_response.status_code == 201

    disconnect_response = client.delete("/connectors/github")

    assert disconnect_response.status_code == 200
    assert disconnect_response.json()["connected"] is False

    status_response = client.get("/connectors/github/status")

    assert status_response.status_code == 200
    assert status_response.json()["connected"] is False


def test_connector_catalog(client):
    response = client.get("/connectors")

    assert response.status_code == 200

    connector_ids = [
        item["id"]
        for item in response.json()["connectors"]
    ]

    assert "github" in connector_ids
    assert "supabase" in connector_ids


def test_pat_is_encrypted_in_database(client, monkeypatch):
    monkeypatch.setattr(
        "app.services.github_connector.httpx.get",
        github_success,
    )

    client.post(
        "/connectors/github/connect",
        json={"personal_access_token": "my-secret-pat"},
    )

    document = github_connector._col().find_one(
        {"owner_id": "test_user_1"}
    )

    assert document is not None
    assert document["encrypted_pat"] != "my-secret-pat"
    assert github_connector.get_pat(
        Principal(owner_id="test_user_1", kind="test")
    ) == "my-secret-pat"


@pytest.fixture
def test_principal_override():
    """Temporarily override authentication without deleting other overrides."""

    from app.core.auth import get_current_principal, Principal
    from app.main import app

    previous_override = app.dependency_overrides.get(
        get_current_principal
    )

    def _test_principal():
        return Principal(
            owner_id="test_user_1",
            kind="test",
        )

    app.dependency_overrides[get_current_principal] = _test_principal

    yield

    # Restore the previous override instead of clearing everything.
    if previous_override is None:
        app.dependency_overrides.pop(get_current_principal, None)
    else:
        app.dependency_overrides[get_current_principal] = previous_override
