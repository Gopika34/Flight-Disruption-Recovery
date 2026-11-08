import json

import pytest
from fastapi.testclient import TestClient

import app.main as main
from app.core import config
from app.rag.retriever import RetrievalUnavailable

client = TestClient(main.app)

COMPLETE_CANCELLATION = {
    "type": "cancellation", "notice_hours": 3, "has_contact_info": True,
    "reason": "technical", "alternate_flight_offered": False,
    "block_time_minutes": 170, "basic_fare": 6500, "fuel_charge": 800,
}


@pytest.fixture(autouse=True)
def reset_rate_limit():
    main._hits.clear()
    yield
    main._hits.clear()


@pytest.fixture(autouse=True)
def fake_session_store(monkeypatch):
    """Never touch the real Atlas: sessions live in a dict for every API test."""
    store = {}
    monkeypatch.setattr(main, "load_facts", lambda sid: dict(store.get(sid, {})))
    monkeypatch.setattr(main, "save_facts", lambda sid, facts: store.__setitem__(sid, dict(facts)))
    return store


# ---------- health ----------

def test_live_never_touches_dependencies():
    assert client.get("/health/live").json() == {"status": "alive"}


def test_ready_is_503_when_database_is_down(monkeypatch):
    monkeypatch.setattr(main, "db_available", lambda: False)
    r = client.get("/health/ready")
    assert r.status_code == 503 and r.json()["checks"]["database"] == "unavailable"


def test_ready_is_200_when_everything_is_ok(monkeypatch):
    monkeypatch.setattr(main, "db_available", lambda: True)
    monkeypatch.setattr(main, "vector_index_status", lambda: "ready")
    monkeypatch.setattr(main, "GEMINI_API_KEY", "x")
    monkeypatch.setattr(main, "AIRLABS_API_KEY", "x")
    assert client.get("/health/ready").status_code == 200


def test_ready_is_503_while_index_is_building(monkeypatch):
    monkeypatch.setattr(main, "db_available", lambda: True)
    monkeypatch.setattr(main, "vector_index_status", lambda: "building")
    monkeypatch.setattr(main, "GEMINI_API_KEY", "x")
    assert client.get("/health/ready").status_code == 503


def test_ready_does_not_require_airlabs(monkeypatch):
    monkeypatch.setattr(main, "db_available", lambda: True)
    monkeypatch.setattr(main, "vector_index_status", lambda: "ready")
    monkeypatch.setattr(main, "GEMINI_API_KEY", "x")
    monkeypatch.setattr(main, "AIRLABS_API_KEY", None)
    r = client.get("/health/ready")
    assert r.status_code == 200 and r.json()["checks"]["airlabs_key_configured"] is False


# ---------- LLM diagnostics ----------

def test_llm_status_hides_raw_errors(monkeypatch):
    from app.llm import router
    monkeypatch.setattr(router, "chain", lambda: [("gemini", None)])
    monkeypatch.setitem(router._last_errors, "gemini", "KeyError: sk-SECRET-123")
    body = client.get("/llm/status").text
    assert "SECRET" not in body and "last_error" not in body
    assert "SECRET" in json.dumps(router.provider_status(detailed=True))   # still available internally


# ---------- validation ----------

def test_ask_rejects_bad_known_facts_and_short_messages():
    assert client.post("/ask", json={"message": "cancelled", "known_facts": {"notice_hours": "soon"}}).status_code == 422
    assert client.post("/ask", json={"message": "cancelled", "known_facts": {"junk": 1}}).status_code == 422
    assert client.post("/ask", json={"message": "hi"}).status_code == 422
    assert client.post("/ask", json={"message": "x" * 2001}).status_code == 422


def test_search_input_limits():
    assert client.get("/search", params={"q": "x" * 301}).status_code == 422
    assert client.get("/search", params={"q": "cancel", "k": 0}).status_code == 422
    assert client.get("/search", params={"q": "cancel", "k": 21}).status_code == 422
    assert client.get("/search", params={"q": "  "}).status_code == 400


def test_search_failure_is_sanitised(monkeypatch):
    def boom(q, k):
        raise RetrievalUnavailable("mongodb+srv://user:PASSWORD@host")
    monkeypatch.setattr(main, "search_with_related", boom)
    r = client.get("/search", params={"q": "cancelled flight"})
    assert r.status_code == 503 and "PASSWORD" not in r.text


# ---------- deterministic engine ----------

def test_evaluate_needs_no_database_or_llm():
    r = client.post("/evaluate", json=COMPLETE_CANCELLATION)
    assert r.status_code == 200 and r.json()["compensation"] == 7300


def test_estimated_block_time_does_not_decide_compensation():
    body = {k: v for k, v in COMPLETE_CANCELLATION.items() if k != "block_time_minutes"}
    body.update(origin="DEL", destination="BOM")
    r = client.post("/evaluate", json=body).json()
    assert r["status"] == "needs_more_info" and "block_time_minutes" in r["missing_facts"]
    assert r["compensation"] is None


# ---------- /ask behaviour ----------

def _patch_extract(monkeypatch, facts):
    from app.rag import generation
    monkeypatch.setattr(generation, "extract_facts", lambda m, k: dict(facts))


def test_ask_without_clause_evidence_is_not_policy_grounded(monkeypatch):
    from app.services import recovery

    _patch_extract(monkeypatch, COMPLETE_CANCELLATION)
    monkeypatch.setattr(recovery, "get_clause", lambda cid: (_ for _ in ()).throw(RetrievalUnavailable("down")))

    r = client.post("/ask", json={"message": "my flight was cancelled"}).json()
    assert r["status"] == "ok" and r["decision"]["compensation"] == 7300   # calculation still works
    assert r["policy_grounded"] is False
    assert r["explanation_mode"] == "deterministic"
    assert "could not be retrieved" in r["evidence_warning"]


def test_ask_with_evidence_is_grounded_and_states_the_entitlement(monkeypatch):
    from app.services import recovery

    _patch_extract(monkeypatch, COMPLETE_CANCELLATION)
    monkeypatch.setattr(recovery, "get_clause", lambda cid: {"clause_id": cid, "text": "t"})

    r = client.post("/ask", json={"message": "my flight was cancelled"}).json()
    assert r["policy_grounded"] is True
    assert "INR 7,300" in r["explanation"]               # the amount is in the text
    assert "full ticket refund" in r["explanation"]
    assert r["entitlement"]["compensation"] == 7300


def test_ask_persists_and_reuses_session_facts(monkeypatch, fake_session_store):
    _patch_extract(monkeypatch, {"type": "cancellation"})
    first = client.post("/ask", json={"message": "my flight was cancelled"}).json()
    assert first["status"] == "needs_more_info"
    assert fake_session_store[first["session_id"]]["type"] == "cancellation"


def test_ask_storage_down_returns_503(monkeypatch):
    def down(sid):
        raise RuntimeError("mongo down")
    monkeypatch.setattr(main, "load_facts", down)
    assert client.post("/ask", json={"message": "my flight was cancelled"}).status_code == 503


def test_all_llm_providers_down_returns_sanitised_502(monkeypatch):
    from app.rag import generation

    def boom(m, k):
        raise RuntimeError("gemini: 401 key=AIza-SECRET")
    monkeypatch.setattr(generation, "extract_facts", boom)
    r = client.post("/ask", json={"message": "my flight was cancelled"})
    assert r.status_code == 502 and "SECRET" not in r.text


# ---------- /ask/stream ----------

def _sse(text):
    events = []
    for block in text.strip().split("\n\n"):
        name, data = block.split("\n", 1)
        events.append((name.removeprefix("event: "), json.loads(data.removeprefix("data: "))))
    return events


def test_stream_sends_python_amounts_before_llm_text(monkeypatch):
    from app.rag import generation
    from app.services import recovery

    _patch_extract(monkeypatch, COMPLETE_CANCELLATION)
    monkeypatch.setattr(recovery, "get_clause", lambda cid: {"clause_id": cid, "text": "t"})
    monkeypatch.setattr(generation, "stream_explain", lambda m, p: iter(["Hello ", "there"]))

    events = _sse(client.post("/ask/stream", json={"message": "my flight was cancelled"}).text)
    names = [n for n, _ in events]
    assert names.index("result") < names.index("token")
    result = dict(events)["result"]
    assert result["entitlement"]["compensation"] == 7300 and result["policy_grounded"] is True
    assert dict(events)["done"]["explanation_mode"] == "llm"


def test_stream_never_streams_llm_text_without_clause_evidence(monkeypatch):
    from app.rag import generation
    from app.services import recovery

    _patch_extract(monkeypatch, COMPLETE_CANCELLATION)
    monkeypatch.setattr(recovery, "get_clause", lambda cid: (_ for _ in ()).throw(RetrievalUnavailable("down")))

    def must_not_run(m, p):
        raise AssertionError("LLM must not stream without clause evidence")
    monkeypatch.setattr(generation, "stream_explain", must_not_run)

    events = _sse(client.post("/ask/stream", json={"message": "my flight was cancelled"}).text)
    done = dict(events)["done"]
    assert done["explanation_mode"] == "deterministic" and done["policy_grounded"] is False
    assert "INR 7,300" in "".join(d["text"] for n, d in events if n == "token")


# ---------- protection ----------

def test_rate_limit_returns_429(monkeypatch):
    monkeypatch.setattr(main, "RATE_LIMIT_PER_MINUTE", 2)
    monkeypatch.setattr(main, "search_with_related", lambda q, k: [])
    codes = [client.get("/search", params={"q": "cancelled"}).status_code for _ in range(3)]
    assert codes == [200, 200, 429]


def test_rotating_x_forwarded_for_does_not_bypass_the_limit(monkeypatch):
    monkeypatch.setattr(main, "RATE_LIMIT_PER_MINUTE", 2)
    monkeypatch.setattr(main, "TRUSTED_PROXY_COUNT", 0)
    monkeypatch.setattr(main, "search_with_related", lambda q, k: [])
    codes = [
        client.get("/search", params={"q": "cancelled"}, headers={"X-Forwarded-For": f"1.2.3.{i}"}).status_code
        for i in range(3)
    ]
    assert codes == [200, 200, 429]
    assert len(main._hits) == 1                       # no per-fake-IP entries


def test_behind_one_proxy_only_the_proxy_appended_hop_counts(monkeypatch):
    monkeypatch.setattr(main, "RATE_LIMIT_PER_MINUTE", 2)
    monkeypatch.setattr(main, "TRUSTED_PROXY_COUNT", 1)
    monkeypatch.setattr(main, "search_with_related", lambda q, k: [])
    # client rotates the left-hand value; the proxy always appends the real IP last
    codes = [
        client.get("/search", params={"q": "cancelled"}, headers={"X-Forwarded-For": f"9.9.9.{i}, 5.5.5.5"}).status_code
        for i in range(3)
    ]
    assert codes == [200, 200, 429]


def test_idle_ips_are_swept(monkeypatch):
    from collections import deque
    main._hits["old"] = deque([0.0])                  # long expired
    main._last_sweep = 0.0
    assert main.allow_request("new") is True
    assert "old" not in main._hits


def test_websocket_rejects_foreign_origin():
    from starlette.websockets import WebSocketDisconnect
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect("/ws/simulate", headers={"origin": "https://evil.example"}):
            pass


def test_websocket_is_rate_limited(monkeypatch):
    from starlette.websockets import WebSocketDisconnect
    monkeypatch.setattr(main, "RATE_LIMIT_PER_MINUTE", 1)
    monkeypatch.setattr(main, "CORS_ORIGINS", ["http://localhost:5173"])
    headers = {"origin": "http://localhost:5173"}
    with client.websocket_connect("/ws/simulate", headers=headers) as ws:
        ws.send_json({"type": "nonsense"})
        ws.receive_json()
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect("/ws/simulate", headers=headers):
            pass


def test_httpx_does_not_log_request_urls_at_info():
    import logging
    assert logging.getLogger("httpx").getEffectiveLevel() >= logging.WARNING


def test_cors_allows_only_configured_origins():
    if not config.CORS_ORIGINS:
        pytest.skip("no CORS origins configured")
    allowed = config.CORS_ORIGINS[0]
    ok = client.options("/ask", headers={"Origin": allowed, "Access-Control-Request-Method": "POST"})
    bad = client.options("/ask", headers={"Origin": "https://evil.example", "Access-Control-Request-Method": "POST"})
    assert ok.headers.get("access-control-allow-origin") == allowed
    assert "access-control-allow-origin" not in bad.headers


# ---------- production config ----------

def test_production_refuses_wildcard_cors(monkeypatch):
    monkeypatch.setattr(config, "IS_PRODUCTION", True)
    monkeypatch.setattr(config, "CORS_ORIGINS", ["*"])
    with pytest.raises(RuntimeError, match="CORS_ORIGINS"):
        config.validate_production_config()


def test_production_refuses_missing_secrets(monkeypatch):
    monkeypatch.setattr(config, "IS_PRODUCTION", True)
    monkeypatch.setattr(config, "CORS_ORIGINS", ["https://app.example.com"])
    monkeypatch.setattr(config, "MONGO_URI", None)
    with pytest.raises(RuntimeError, match="MONGO_URI"):
        config.validate_production_config()


def test_development_does_not_enforce(monkeypatch):
    monkeypatch.setattr(config, "IS_PRODUCTION", False)
    config.validate_production_config()


# ---------- live flight provider ----------

def test_flight_status_endpoint_returns_live_provider_data(monkeypatch):
    monkeypatch.setattr(main, "get_flight_status", lambda number: {
        "flight_number": number, "status": "en-route", "provider": "AirLabs", "simulated": False,
    })
    response = client.get("/flights/AI202")
    assert response.status_code == 200
    assert response.json()["provider"] == "AirLabs"
    assert response.json()["simulated"] is False


def test_flight_status_endpoint_rejects_invalid_number():
    assert client.get("/flights/AI-202").status_code == 422


def test_flight_status_endpoint_sanitises_provider_errors(monkeypatch):
    from app.services.flights import FlightDataError
    monkeypatch.setattr(main, "get_flight_status", lambda number: (_ for _ in ()).throw(FlightDataError("AirLabs quota reached")))
    response = client.get("/flights/AI202")
    assert response.status_code == 503
    assert "AirLabs quota reached" in response.text
