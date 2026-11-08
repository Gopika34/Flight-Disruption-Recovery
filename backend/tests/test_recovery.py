import pytest

from app.rag.retriever import RetrievalUnavailable
from app.services import recovery


def test_estimated_block_time_is_never_used_as_a_fact():
    facts, notes = recovery.enrich_facts({"type": "cancellation", "origin": "DEL", "destination": "BOM"})
    assert "block_time_minutes" not in facts
    assert any("NOT used for eligibility" in n for n in notes)


def test_supplied_block_time_is_untouched():
    facts, notes = recovery.enrich_facts(
        {"origin": "DEL", "destination": "BOM", "block_time_minutes": 130})
    assert facts["block_time_minutes"] == 130
    assert not any("Estimated flight time" in n for n in notes)


def test_domestic_is_inferred_for_two_indian_airports_and_stated():
    facts, notes = recovery.enrich_facts({"origin": "DEL", "destination": "BOM"})
    assert facts["domestic"] is True
    assert any("treated as domestic" in n for n in notes)


def test_flight_info_is_display_only():
    info = recovery.flight_info({"origin": "DEL", "destination": "BOM"})
    assert info["estimated_block_time_minutes"] > 0
    assert recovery.flight_info({"origin": "DEL"}) is None


def _patch_clauses(monkeypatch, available):
    def fake(cid):
        if available is None:
            raise RetrievalUnavailable("down")
        return {"clause_id": cid, "text": "t"} if cid in available else None
    monkeypatch.setattr(recovery, "get_clause", fake)


def test_evidence_ok(monkeypatch):
    _patch_clauses(monkeypatch, {"3.3.1", "3.3.2"})
    clauses, ev = recovery.fetch_clauses(["3.3.1", "3.3.2(a)"])
    assert ev["status"] == "ok" and len(clauses) == 2


def test_evidence_partial_when_a_clause_does_not_exist(monkeypatch):
    _patch_clauses(monkeypatch, {"3.3.1"})
    clauses, ev = recovery.fetch_clauses(["3.3.1", "3.3.2"])
    assert ev == {"status": "partial", "missing_clause_ids": ["3.3.2"]}


def test_evidence_unavailable_when_database_is_down(monkeypatch):
    _patch_clauses(monkeypatch, None)
    clauses, ev = recovery.fetch_clauses(["3.3.1"])
    assert clauses == [] and ev["status"] == "unavailable"


def test_recovery_reports_live_flight_provider_not_configured(monkeypatch):
    monkeypatch.setattr(recovery, "AIRLABS_API_KEY", None)
    monkeypatch.setattr(recovery, "get_clause", lambda cid: {"clause_id": cid, "text": "policy"})
    plan = recovery.plan_recovery({
        "type": "cancellation", "notice_hours": 30,
        "acceptable_alternative_or_refund_provided": True,
        "origin": "MAA", "destination": "DEL",
    })
    assert plan["flight_data"]["status"] == "not_configured"
    assert plan["alternatives"] == []


def test_recovery_uses_live_schedules_and_marks_no_seat_or_fare_claim(monkeypatch):
    monkeypatch.setattr(recovery, "AIRLABS_API_KEY", "test-key")
    monkeypatch.setattr(recovery, "find_alternatives", lambda *a, **k: [{
        "flight_number": "AI202", "provider": "AirLabs", "simulated": False,
        "fare_inr": None, "seats_available": None, "availability_confirmed": False,
        "departure": "2026-11-07T20:00:00+05:30",
    }])
    monkeypatch.setattr(recovery, "get_clause", lambda cid: {"clause_id": cid, "text": "policy"})
    plan = recovery.plan_recovery({
        "type": "cancellation", "notice_hours": 30,
        "acceptable_alternative_or_refund_provided": True,
        "origin": "MAA", "destination": "DEL",
    })
    assert plan["flight_data"]["status"] == "live_data"
    assert plan["flight_data"]["result_count"] == 1
    assert plan["alternatives"][0]["availability_confirmed"] is False


def test_hotel_obligation_never_creates_fake_hotel_or_price(monkeypatch):
    monkeypatch.setattr(recovery, "get_clause", lambda cid: {"clause_id": cid, "text": "policy"})
    plan = recovery.plan_recovery({
        "type": "delay", "domestic": True, "block_time_minutes": 120,
        "delay_minutes": 1500, "total_delay_from_published_minutes": 1500,
        "checked_in_on_time": True, "scheduled_departure": "12:00",
        "revised_departure_communicated_more_than_24h": False, "reason": "technical",
    })
    assert plan["decision"]["hotel"] is True
    assert plan["stay"]["provider_status"] == "not_integrated"
    assert plan["stay"]["hotel_options"] == []
    assert plan["stay"]["cab_estimate_inr"] is None
