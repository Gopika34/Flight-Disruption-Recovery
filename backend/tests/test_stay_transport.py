import pytest
from fastapi.testclient import TestClient

import app.main as main
from app.schemas.capabilities import EmergencyStayRequest
from app.services.stay_transport import search_emergency_stay_and_transport

client = TestClient(main.app)


def test_duty_of_care_triggers():
    # 1. Overnight delay -> mandatory duty of care
    req_overnight = EmergencyStayRequest(
        airport_code="DEL",
        delay_hours=7.0,
        is_overnight=True,
        airline_name="IndiGo",
    )
    res_1 = search_emergency_stay_and_transport(req_overnight)
    assert res_1.duty_of_care_mandated is True
    assert "3.4.3" in res_1.statutory_clause
    assert "MANDATORY" in res_1.airline_liability_statement
    assert "IndiGo" in res_1.counter_demand_script

    # 2. Daytime short delay -> duty of care hotel not mandated
    req_short = EmergencyStayRequest(
        airport_code="BOM",
        delay_hours=3.0,
        is_overnight=False,
        airline_name="Air India",
    )
    res_2 = search_emergency_stay_and_transport(req_short)
    assert res_2.duty_of_care_mandated is False
    assert "not mandated" in res_2.airline_liability_statement


def test_hotel_and_transport_options():
    req = EmergencyStayRequest(
        airport_code="DEL",
        delay_hours=8.0,
        is_overnight=True,
    )
    res = search_emergency_stay_and_transport(req)
    assert len(res.hotels) >= 2
    assert res.hotels[0].distance_km > 0
    assert res.hotels[0].price_per_night_inr > 0

    assert len(res.transport) >= 2
    # First should be shuttle or prepaid cab
    assert any("Shuttle" in t.mode for t in res.transport)
    assert any("Taxi" in t.mode or "Cab" in t.mode for t in res.transport)


def test_api_stay_transport_endpoints():
    payload = {
        "airport_code": "BOM",
        "delay_hours": 9.0,
        "is_overnight": True,
        "airline_name": "SpiceJet",
    }
    resp = client.post("/api/v1/stay-transport/evaluate", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["airport_code"] == "BOM"
    assert data["duty_of_care_mandated"] is True
    assert len(data["hotels"]) > 0
    assert "SpiceJet" in data["counter_demand_script"]


def test_api_stay_transport_stream():
    payload = {
        "airport_code": "BLR",
        "delay_hours": 6.5,
        "is_overnight": True,
    }
    with client.stream("POST", "/api/v1/stay-transport/stream", json=payload) as r:
        assert r.status_code == 200
        content = r.read().decode("utf-8")
        assert "event: duty_of_care" in content
        assert "event: hotels" in content
        assert "event: transport" in content
        assert "event: counter_script" in content
        assert "event: done" in content
