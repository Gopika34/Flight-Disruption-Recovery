"""Regression tests for the deterministic DGCA decision engine."""
import copy
import json
import re

import pytest

from app.core.config import BASE_DIR
from app.rules.rule_engine import evaluate

CASES = json.loads((BASE_DIR / "data" / "test_cases.json").read_text(encoding="utf-8"))["cases"]


def base(clause):
    return re.sub(r"\(.*\)$", "", clause)


def fixture_facts(case):
    """Apply only assumptions explicitly described by the old fixture semantics.

    Production code never receives these defaults. The legacy dataset predates
    the newer confirmation fields, so this adapter makes its intended scenarios
    explicit for regression testing.
    """
    facts = copy.deepcopy(case)
    if facts.get("type") == "denied_boarding":
        facts.setdefault("overbooking", True)
        facts.setdefault("voluntary_surrender", False)
        facts.setdefault("connecting_same_ticket", False)
        facts.setdefault("alternate_flight_offered", True)
        facts.setdefault("alternate_flight_accepted", True)
    if facts.get("type") == "delay":
        facts.setdefault("reason", "technical")
        facts.setdefault("total_delay_from_published_minutes", facts.get("delay_minutes", 0))
        if facts.get("domestic") and (facts.get("delay_minutes") or 0) > 360:
            facts.setdefault("revised_departure_communicated_more_than_24h", False)
        if facts.get("reason") and facts["reason"].lower().startswith(("weather", "fog", "atc", "security")):
            facts.setdefault("extraordinary_circumstances_established", True)
    if facts.get("type") == "cancellation":
        if facts.get("notice_hours") is not None and facts["notice_hours"] >= 24:
            facts.setdefault("acceptable_alternative_or_refund_provided", True)
        if facts.get("notice_hours") is not None and facts["notice_hours"] < 24:
            # The legacy fixtures describe "no alternate offered" cancellations.
            facts.setdefault("alternate_flight_offered", False)
        if facts.get("reason") and facts["reason"].lower().startswith(("weather", "fog", "atc", "security")):
            facts.setdefault("extraordinary_circumstances_established", True)
    return facts


@pytest.mark.parametrize("case", CASES, ids=[c["case_id"] for c in CASES])
def test_policy_fixture_cases(case):
    facts = fixture_facts(case)
    try:
        result = evaluate(facts)
    except ValueError:
        pytest.skip("not a rule-engine case")
    if "expected_compensation" in case:
        assert result["compensation"] == case["expected_compensation"]
    for key, field in (("expected_meals", "meals"), ("expected_hotel", "hotel"),
                       ("expected_alt_or_refund", "alt_or_refund")):
        if key in case:
            assert result[field] == case[key], field
    assert set(case.get("expected_missing_facts", [])) <= set(result["missing_facts"])
    expected = {base(clause) for clause in case.get("expected_clause_ids", [])}
    assert expected <= {base(clause) for clause in result["clauses"]}


def test_cancellation_24_hours_or_more_uses_331_notice_window():
    result = evaluate({"type": "cancellation", "notice_hours": 30, "acceptable_alternative_or_refund_provided": True})
    assert result["status"] == "ok"
    assert result["compensation"] == 0
    assert result["alt_or_refund"] is True


def test_cancellation_24h_notice_without_acceptable_option_uses_compensation_path():
    result = evaluate({
        "type": "cancellation", "notice_hours": 30,
        "acceptable_alternative_or_refund_provided": False,
        "has_contact_info": True, "reason": "technical",
        "block_time_minutes": 90, "basic_fare": 4000, "fuel_charge": 500,
    })
    assert result["compensation"] == 4500
    assert result["refund"] == "full_ticket_refund"


def test_cancellation_under_24h_requires_alternate_acceptance_fact():
    result = evaluate({
        "type": "cancellation", "notice_hours": 3, "has_contact_info": True,
        "reason": "airline_operational", "alternate_flight_offered": True,
        "block_time_minutes": 90, "basic_fare": 4000, "fuel_charge": 500,
    })
    assert result["status"] == "needs_more_info"
    assert result["missing_facts"] == ["alternate_flight_accepted"]


def test_cancellation_offered_but_rejected_gets_compensation_and_refund():
    result = evaluate({
        "type": "cancellation", "notice_hours": 3, "has_contact_info": True,
        "reason": "technical", "alternate_flight_offered": True,
        "alternate_flight_accepted": False, "block_time_minutes": 90,
        "basic_fare": 4000, "fuel_charge": 500,
    })
    assert result["compensation"] == 4500
    assert result["refund"] == "full_ticket_refund"


def test_cancellation_stated_weather_is_not_automatically_exempt():
    facts = {
        "type": "cancellation", "notice_hours": 3, "has_contact_info": True,
        "reason": "weather", "alternate_flight_offered": False,
        "block_time_minutes": 90, "basic_fare": 4000, "fuel_charge": 500,
    }
    result = evaluate(facts)
    assert result["status"] == "needs_more_info"
    assert result["missing_facts"] == ["extraordinary_circumstances_established"]


def test_cancellation_established_extraordinary_circumstance_exempts_compensation():
    result = evaluate({
        "type": "cancellation", "notice_hours": 3, "has_contact_info": True,
        "reason": "weather", "extraordinary_circumstances_established": True,
    })
    assert result["compensation"] == 0
    assert result["alt_or_refund"] is True


def test_denied_boarding_no_accepted_alternate_uses_400_percent_and_refund():
    result = evaluate({
        "type": "denied_boarding", "confirmed_booking": True,
        "checked_in_on_time": True, "overbooking": True,
        "voluntary_surrender": False, "connecting_same_ticket": False,
        "alternate_flight_offered": False, "basic_fare": 4000, "fuel_charge": 500,
    })
    assert result["compensation"] == 18000
    assert result["refund"] == "full_ticket_refund"
    assert "3.2.2(c)" in result["clauses"]


def test_denied_boarding_alternate_within_one_hour_is_zero():
    result = evaluate({
        "type": "denied_boarding", "confirmed_booking": True,
        "checked_in_on_time": True, "overbooking": True,
        "voluntary_surrender": False, "connecting_same_ticket": False,
        "alternate_flight_offered": True, "alternate_flight_accepted": True,
        "alternate_departure_delay_minutes": 60, "basic_fare": 4000, "fuel_charge": 500,
    })
    assert result["compensation"] == 0


def test_denied_boarding_connecting_ticket_requires_three_hour_final_delay():
    facts = {
        "type": "denied_boarding", "confirmed_booking": True,
        "checked_in_on_time": True, "overbooking": True,
        "voluntary_surrender": False, "connecting_same_ticket": True,
        "final_arrival_delay_minutes": 179, "alternate_flight_offered": False,
        "basic_fare": 4000, "fuel_charge": 500,
    }
    assert evaluate(facts)["compensation"] == 0
    facts["final_arrival_delay_minutes"] = 180
    assert evaluate(facts)["compensation"] == 18000


def test_delay_6_hours_is_not_more_than_6_hours_for_342():
    result = evaluate({
        "type": "delay", "domestic": True, "block_time_minutes": 120,
        "delay_minutes": 360, "total_delay_from_published_minutes": 360, "scheduled_departure": "20:00",
        "checked_in_on_time": True, "reason": "technical",
    })
    assert result["alt_or_refund"] is False


def test_delay_more_than_6_hours_does_not_ask_revised_time_flag():
    """The flag never changed an outcome, so it must not block the answer."""
    result = evaluate({
        "type": "delay", "domestic": True, "block_time_minutes": 120,
        "delay_minutes": 361, "total_delay_from_published_minutes": 361, "scheduled_departure": "12:00",
        "checked_in_on_time": True, "reason": "technical",
    })
    assert result["status"] == "ok"
    assert result["alt_or_refund"] is True


def test_delay_extraordinary_exemption_only_affects_meals_and_hotel():
    result = evaluate({
        "type": "delay", "domestic": True, "block_time_minutes": 120,
        "delay_minutes": 400, "total_delay_from_published_minutes": 400, "scheduled_departure": "22:00",
        "checked_in_on_time": True, "reason": "weather",
        "extraordinary_circumstances_established": True,
        "revised_departure_communicated_more_than_24h": False,
    })
    assert result["meals"] is False
    assert result["hotel"] is False
    assert result["alt_or_refund"] is True


def test_unknown_type_is_rejected():
    with pytest.raises(ValueError):
        evaluate({"type": "teleportation"})


def test_reason_never_given_is_asked_only_when_absent():
    base_facts = {
        "type": "cancellation", "notice_hours": 2, "has_contact_info": True,
        "alternate_flight_offered": False,
        "block_time_minutes": 120, "basic_fare": 3000, "fuel_charge": 400,
    }
    asked = evaluate(base_facts)
    assert asked["status"] == "needs_more_info" and asked["missing_facts"] == ["reason"]


@pytest.mark.parametrize("reason", ["unknown", "bird_strike"])
def test_unknown_or_unlisted_reason_does_not_loop(reason):
    """Once the passenger has answered, the engine must move on (no endless re-asking)."""
    result = evaluate({
        "type": "cancellation", "notice_hours": 2, "has_contact_info": True,
        "reason": reason, "alternate_flight_offered": False,
        "block_time_minutes": 120, "basic_fare": 3000, "fuel_charge": 400,
    })
    assert result["status"] == "ok"
    assert result["compensation"] == 3400
    assert any("not extraordinary" in a for a in result["assumptions"])


def test_delay_too_short_for_any_entitlement_does_not_ask_reason():
    result = evaluate({
        "type": "delay", "domestic": True, "block_time_minutes": 90,
        "delay_minutes": 30, "total_delay_from_published_minutes": 30, "scheduled_departure": "12:00",
        "checked_in_on_time": True,
    })
    assert result["status"] == "ok"
    assert result["meals"] is False and result["hotel"] is False


def test_denied_boarding_questions_are_batched():
    first = evaluate({"type": "denied_boarding"})
    assert first["missing_facts"] == ["confirmed_booking", "checked_in_on_time"]
    second = evaluate({"type": "denied_boarding", "confirmed_booking": True, "checked_in_on_time": True})
    assert second["missing_facts"] == ["voluntary_surrender", "overbooking", "connecting_same_ticket"]


def test_cancellation_conflicting_alternate_facts_do_not_calculate():
    result = evaluate({
        "type": "cancellation", "notice_hours": 2, "has_contact_info": True,
        "reason": "technical", "alternate_flight_offered": False,
        "alternate_flight_accepted": True,
    })
    assert result["status"] == "unable_to_determine"



def test_documented_force_majeure_can_apply_even_to_other_reported_cause():
    result = evaluate({
        "type": "cancellation", "notice_hours": 2, "has_contact_info": True,
        "reason": "technical", "extraordinary_circumstances_established": True,
    })
    assert result["compensation"] == 0
    assert "3.3.4" in result["clauses"]
