import pytest
import app.main as main
import app.services.sessions as sessions_mod
import app.services.claims as claims_mod
import app.llm.router as router_mod


@pytest.fixture(autouse=True)
def reset_rate_limit():
    """Reset rate limiting hit counter before and after every test."""
    main._hits.clear()
    yield
    main._hits.clear()


@pytest.fixture(autouse=True)
def fake_session_store(monkeypatch):
    """
    In-memory session store for tests so no test attempts
    to reach external MongoDB Atlas in offline or sandbox test runs.
    """
    store = {}

    def _load_facts(sid):
        return dict(store.get(sid, {}).get("facts", {}))

    def _save_facts(sid, facts):
        store.setdefault(sid, {})["facts"] = dict(facts)

    def _load_messages(sid):
        return list(store.get(sid, {}).get("messages", []))

    def _save_messages(sid, msgs):
        store.setdefault(sid, {})["messages"] = list(msgs)

    def _append_message(sid, msg):
        store.setdefault(sid, {}).setdefault("messages", []).append(dict(msg))

    def _load_session(sid):
        sess = store.get(sid, {})
        return {
            "facts": dict(sess.get("facts", {})),
            "messages": list(sess.get("messages", [])),
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


@pytest.fixture(autouse=True)
def mock_llm_for_unit_tests(monkeypatch):
    """Mock external LLM network completion during unit tests."""
    def _mock_complete(*args, **kwargs):
        return (
            "FORMAL STATUTORY GRIEVANCE NOTICE\n\n"
            "Demand for statutory compensation under DGCA CAR Section 3, Series M, Part IV.\n"
            "Flight: 6E204 | PNR: XYZ987"
        )

    monkeypatch.setattr(claims_mod, "complete", _mock_complete)
    monkeypatch.setattr(router_mod, "complete", _mock_complete)
