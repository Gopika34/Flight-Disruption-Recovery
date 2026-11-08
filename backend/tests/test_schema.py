import pytest
from pydantic import ValidationError
from app.schemas.scenario import AskIn, Scenario, sanitize_facts


def test_new_rule_facts_are_accepted():
    facts = Scenario(
        alternate_flight_offered=True, alternate_flight_accepted=False,
        acceptable_alternative_or_refund_provided=True,
        overbooking=True, voluntary_surrender=False,
        connecting_same_ticket=False,
        extraordinary_circumstances_established=False,
    ).facts()
    assert facts["alternate_flight_accepted"] is False
    assert facts["acceptable_alternative_or_refund_provided"] is True
    assert facts["overbooking"] is True


def test_codes_and_reason_are_normalised():
    facts = Scenario(origin=" del ", destination="bom", flight_number=" 6e201 ", reason="Airline Operational").facts()
    assert facts == {"origin": "DEL", "destination": "BOM", "flight_number": "6E201", "reason": "airline_operational"}


@pytest.mark.parametrize("bad", [
    {"notice_hours": "soon"}, {"made_up_key": 1}, {"origin": "DELHI"},
    {"scheduled_departure": "25:99"}, {"block_time_minutes": 0},
    {"basic_fare": -5}, {"final_arrival_delay_minutes": -1},
])
def test_invalid_scenarios_are_rejected(bad):
    with pytest.raises(ValidationError):
        Scenario(**bad)


def test_ask_validates_known_facts():
    assert AskIn(message="hello there", known_facts={"reason": "weather"}).known_facts == {"reason": "weather"}
    for bad in ({"notice_hours": "unknown"}, {"nope": 1}, "not a dict"):
        with pytest.raises(ValidationError):
            AskIn(message="hello there", known_facts=bad)


def test_blank_message_is_rejected():
    with pytest.raises(ValidationError):
        AskIn(message="   ")


def test_sanitize_drops_only_bad_values():
    clean, rejected = sanitize_facts({
        "type": "cancellation", "reason": "weather", "notice_hours": "unknown",
        "block_time_minutes": "2h", "junk": 1, "basic_fare": None,
    })
    assert clean == {"type": "cancellation", "reason": "weather"}
    assert set(rejected) == {"notice_hours", "block_time_minutes", "junk"}
