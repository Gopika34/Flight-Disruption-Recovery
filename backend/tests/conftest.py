
import pytest

import app.main as main
import app.services.sessions as sessions_mod
import app.llm.router as router_mod

from app.core.auth import get_current_principal, Principal


# --------------------------------------------------
# GLOBAL TEST AUTHENTICATION
# --------------------------------------------------

def _test_principal():
    return Principal(owner_id="test_user", kind="test")


main.app.dependency_overrides[get_current_principal] = _test_principal


# --------------------------------------------------
# RATE LIMIT RESET
# --------------------------------------------------

@pytest.fixture(autouse=True)
def reset_rate_limit():
    """Reset rate limiting hit counter before and after every test."""
    main._hits.clear()
    main._user_limiter._hits.clear()
    yield
    main._hits.clear()
    main._user_limiter._hits.clear()


# --------------------------------------------------
# IN-MEMORY SESSION STORE
# --------------------------------------------------

@pytest.fixture(autouse=True)
def fake_session_store(monkeypatch):
    """
    In-memory session store for tests.

    Prevents tests from reaching external MongoDB.
    """
    store = {}

    def _load_facts(sid, owner_id=None):
        return dict(store.get(sid, {}).get("facts", {}))

    def _save_facts(sid, facts, owner_id=None):
        store.setdefault(sid, {})["facts"] = dict(facts)

    def _load_messages(sid, owner_id=None):
        return list(store.get(sid, {}).get("messages", []))

    def _save_messages(sid, msgs, owner_id=None):
        store.setdefault(sid, {})["messages"] = list(msgs)

    def _append_message(sid, msg, owner_id=None):
        store.setdefault(sid, {}).setdefault("messages", []).append(dict(msg))

    def _load_session(sid, owner_id=None):
        session = store.get(sid, {})
        return {
            "facts": dict(session.get("facts", {})),
            "messages": list(session.get("messages", [])),
        }

    monkeypatch.setattr(main, "load_facts", _load_facts)
    monkeypatch.setattr(main, "save_facts", _save_facts)

    monkeypatch.setattr(sessions_mod, "load_facts", _load_facts)
    monkeypatch.setattr(sessions_mod, "save_facts", _save_facts)
    monkeypatch.setattr(sessions_mod, "load_messages", _load_messages)
    monkeypatch.setattr(sessions_mod, "save_messages", _save_messages)
    monkeypatch.setattr(sessions_mod, "append_message", _append_message)
    monkeypatch.setattr(sessions_mod, "load_session", _load_session)

    return store


# --------------------------------------------------
# MOCK EXTERNAL LLM CALLS
# --------------------------------------------------

@pytest.fixture(autouse=True)
def mock_llm_for_unit_tests(monkeypatch, request):
    """
    Mock external LLM completion for API/unit tests.

    Do NOT mock router.complete in test_llm_router.py.
    Those tests must exercise the real provider fallback logic.
    """

    if request.node.path.name == "test_llm_router.py":
        return

    def _mock_complete(*args, **kwargs):
        return (
            "FORMAL STATUTORY GRIEVANCE NOTICE\n\n"
            "Demand for statutory compensation under DGCA CAR "
            "Section 3, Series M, Part IV.\n"
            "Flight: 6E204 | PNR: XYZ987"
        )

    monkeypatch.setattr(router_mod, "complete", _mock_complete)
