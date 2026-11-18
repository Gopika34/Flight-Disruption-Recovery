import pytest
from fastapi.testclient import TestClient

import app.main as main
from app.schemas.capabilities import ClaimPackageRequest
from app.services.claims import (
    AIRLINE_REGISTRY,
    build_claim_package,
    generate_claim_timeline,
    generate_evidence_checklist,
    get_airline_contact,
)

client = TestClient(main.app)


@pytest.fixture(autouse=True)
def mock_llm_complete(monkeypatch):
    """Avoid slow network LLM retries during fast unit testing."""
    import app.services.claims as claims_svc
    monkeypatch.setattr(
        claims_svc,
        "complete",
        lambda *args, **kwargs: (
            "FORMAL STATUTORY GRIEVANCE NOTICE\n\n"
            "To: Airline Nodal Officer\n"
            "Demand for statutory compensation under DGCA CAR Section 3.\n"
            "Flight: 6E204 | PNR: XYZ987"
        ),
    )


def test_airline_contact_lookup():
    indigo = get_airline_contact("6E204")
    assert indigo.airline_code == "6E"
    assert "goindigo" in indigo.nodal_officer_email

    airindia = get_airline_contact("AI504")
    assert airindia.airline_code == "AI"
    assert "airindia" in airindia.nodal_officer_email

    generic = get_airline_contact("XX999")
    assert generic.airline_code == "GEN"


def test_timeline_milestones_order():
    timeline = generate_claim_timeline()
    assert len(timeline) == 5
    assert timeline[0].day_marker == "Day 0"
    assert timeline[1].day_marker == "Day 1"
    assert timeline[2].day_marker == "Day 30"
    assert "AirSewa" in timeline[3].title


def test_evidence_checklist_disruptions():
    cancellation_list = generate_evidence_checklist("cancellation")
    assert any(item.id == "written_certificate" for item in cancellation_list)
    assert not any(item.id == "checkin_reporting_proof" for item in cancellation_list)

    denied_boarding_list = generate_evidence_checklist("denied_boarding")
    assert any(item.id == "checkin_reporting_proof" for item in denied_boarding_list)


def test_build_claim_package_deterministic():
    req = ClaimPackageRequest(
        passenger_name="Rahul Sharma",
        pnr="XYZ987",
        flight_number="6E204",
        out_of_pocket_expenses_inr=1500.0,
        scenario_facts={
            "type": "cancellation",
            "notice_hours": 3,
            "has_contact_info": True,
            "reason": "technical",
            "alternate_flight_offered": True,
            "alternate_flight_accepted": False,
            "block_time_minutes": 150,
            "basic_fare": 6000,
            "fuel_charge": 800,
        },
    )
    res = build_claim_package(req)
    assert res.pnr == "XYZ987"
    assert res.disruption_type == "cancellation"
    assert res.statutory_compensation_inr > 0
    assert "6E204" in res.formal_grievance_notice
    assert res.airline.airline_code == "6E"


def test_api_claims_endpoints():
    r = client.get("/api/v1/claims/airlines")
    assert r.status_code == 200
    airlines = r.json()
    assert len(airlines) >= 5

    payload = {
        "passenger_name": "Priya Patel",
        "pnr": "DEF456",
        "flight_number": "AI504",
        "out_of_pocket_expenses_inr": 800.0,
        "scenario_facts": {
            "type": "cancellation",
            "notice_hours": 3,
            "has_contact_info": True,
            "reason": "technical",
            "alternate_flight_offered": True,
            "alternate_flight_accepted": False,
            "block_time_minutes": 90,
            "basic_fare": 4500,
            "fuel_charge": 500,
        },
    }
    resp = client.post("/api/v1/claims/generate", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["pnr"] == "DEF456"
    assert data["airline"]["airline_name"] == "Air India"
    assert len(data["timeline"]) == 5
    assert len(data["evidence_checklist"]) >= 5


def test_api_claims_stream():
    payload = {
        "passenger_name": "Amit Kumar",
        "pnr": "GHI789",
        "flight_number": "6E101",
        "out_of_pocket_expenses_inr": 0.0,
        "scenario_facts": {
            "type": "cancellation",
            "notice_hours": 3,
            "has_contact_info": True,
            "reason": "technical",
            "alternate_flight_offered": True,
            "alternate_flight_accepted": False,
            "block_time_minutes": 90,
            "basic_fare": 4000,
            "fuel_charge": 500,
        },
    }
    with client.stream("POST", "/api/v1/claims/stream", json=payload) as r:
        assert r.status_code == 200
        content = r.read().decode("utf-8")
        assert "event: session" in content
        assert "event: timeline" in content
        assert "event: checklist" in content
        assert "event: done" in content
