import asyncio
from types import SimpleNamespace

import pytest

from app.llm import agent as agent_module


def test_intent_workflows_expose_only_their_allowlisted_tools():
    assert {tool.name for tool in agent_module.tools_for_intent("entitlement")} == {
        "evaluate_disruption", "search_dgca_policy"
    }
    assert {tool.name for tool in agent_module.tools_for_intent("flight_status")} == {
        "get_live_flight_status"
    }
    assert {tool.name for tool in agent_module.tools_for_intent("rebooking")} == {
        "search_alternative_flights", "get_live_flight_status", "evaluate_disruption"
    }
    assert {tool.name for tool in agent_module.tools_for_intent("claims")} == {
        "prepare_passenger_claim_package", "evaluate_disruption", "search_dgca_policy"
    }


def test_unknown_intent_uses_safe_general_allowlist():
    names = {tool.name for tool in agent_module.tools_for_intent("not-a-route")}
    assert names == {"search_dgca_policy", "get_live_flight_status", "evaluate_disruption"}
    assert "prepare_passenger_claim_package" not in names
    assert "search_alternative_flights" not in names


def test_merge_known_facts_validates_and_persists_owner_scoped_facts(monkeypatch):
    calls = {}
    monkeypatch.setattr(agent_module, "load_facts", lambda session_id, owner_id: {"origin": "DEL"})
    monkeypatch.setattr(
        agent_module,
        "save_facts",
        lambda session_id, facts, owner_id: calls.update(session=session_id, facts=facts, owner=owner_id),
    )

    facts = agent_module._merge_known_facts(
        "session-1", "guest_123", {"destination": "maa", "delay_minutes": 240}
    )

    assert facts == {"origin": "DEL", "destination": "MAA", "delay_minutes": 240}
    assert calls == {
        "session": "session-1",
        "facts": facts,
        "owner": "guest_123",
    }


def test_merge_known_facts_rejects_unknown_or_invalid_fields(monkeypatch):
    monkeypatch.setattr(agent_module, "load_facts", lambda *_: {})
    with pytest.raises(Exception):
        agent_module._merge_known_facts("session-1", "user_123", {"pnr": "ABC123"})
    with pytest.raises(Exception):
        agent_module._merge_known_facts("session-1", "user_123", {"delay_minutes": -5})


def test_run_agent_uses_route_specific_agent_and_includes_known_facts(monkeypatch):
    captured = {}

    class FakeAgent:
        def invoke(self, payload):
            captured["messages"] = payload["messages"]
            return {"messages": [SimpleNamespace(content="A grounded response", type="ai")]}

    monkeypatch.setattr(agent_module, "create_flight_agent", lambda intent: captured.update(intent=intent) or FakeAgent())
    monkeypatch.setattr(agent_module, "_merge_known_facts", lambda *_: {"type": "delay", "delay_minutes": 240})
    monkeypatch.setattr(agent_module, "load_messages", lambda *_: [])

    answer = agent_module.run_agent(
        "How much compensation am I entitled to?",
        session_id=None,
        owner_id="guest_123",
        known_facts={"type": "delay", "delay_minutes": 240},
    )

    assert answer == "A grounded response"
    assert captured["intent"] == "entitlement"
    system_text = captured["messages"][0].content
    assert '"delay_minutes": 240' in system_text
    assert "Use only tools available in this workflow" in system_text


def test_stream_agent_emits_real_lifecycle_events_and_persists_messages(monkeypatch):
    saved = {}

    class FakeAgent:
        async def astream_events(self, _payload, version):
            assert version == "v2"
            yield {"event": "on_chat_model_stream", "data": {"chunk": SimpleNamespace(tool_call_chunks=[], content="Hello ")}}
            yield {"event": "on_tool_start", "name": "search_dgca_policy", "run_id": "run-safe-id", "data": {"input": {"query": "private details"}}}
            yield {"event": "on_tool_end", "name": "search_dgca_policy", "data": {"output": "policy result"}}
            yield {"event": "on_chain_end", "data": {"output": {"messages": [SimpleNamespace(content="Hello from FlightGuard", type="ai")]}}}

    monkeypatch.setattr(agent_module, "create_flight_agent", lambda intent: FakeAgent())
    monkeypatch.setattr(agent_module, "_merge_known_facts", lambda *_: {"type": "cancellation"})
    monkeypatch.setattr(agent_module, "load_messages", lambda *_: [])
    monkeypatch.setattr(agent_module, "save_messages", lambda sid, messages, owner: saved.update(session=sid, messages=messages, owner=owner))

    async def collect_events():
        return [event async for event in agent_module.stream_agent_events(
            "DGCA cancellation rights", session_id="session-1", owner_id="guest_123"
        )]

    events = asyncio.run(collect_events())

    names = [name for name, _ in events]
    assert "route" in names and "token" in names and "tool_start" in names and "tool_end" in names and "done" in names
    tool_start_payload = next(data for name, data in events if name == "tool_start")
    assert "input" not in tool_start_payload  # tool arguments are never sent to the browser
    assert saved["session"] == "session-1"
    assert saved["owner"] == "guest_123"
    assert saved["messages"][0]["content"] == "Hello from FlightGuard"
