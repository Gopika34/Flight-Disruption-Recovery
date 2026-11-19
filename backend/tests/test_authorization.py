import pytest
from app.core.auth import Principal
from app.core.authz import effective_role, has_permission
from app.core.rate_limiter import SlidingWindowLimiter


def test_guest_is_limited():
    guest = Principal(owner_id="guest_123", kind="guest")
    assert effective_role(guest) == "guest"
    assert has_permission(guest, "agent:use")
    assert not has_permission(guest, "connector:github:connect")
    assert not has_permission(guest, "mcp:github:list_repositories")


def test_admin_is_configured_only_by_server_environment(monkeypatch):
    monkeypatch.setenv("ADMIN_USER_IDS", "user_admin_1")
    admin = Principal(owner_id="user_admin_1", kind="clerk")
    ordinary = Principal(owner_id="user_2", kind="clerk")
    assert effective_role(admin) == "admin"
    assert has_permission(admin, "anything:dangerous")
    assert effective_role(ordinary) == "user"
    assert not has_permission(ordinary, "anything:dangerous")


def test_rate_limiter_limits_identity_independently():
    limiter = SlidingWindowLimiter(limit=2, window_seconds=60)
    assert limiter.allow("user:a")
    assert limiter.allow("user:a")
    assert not limiter.allow("user:a")
    assert limiter.allow("user:b")
