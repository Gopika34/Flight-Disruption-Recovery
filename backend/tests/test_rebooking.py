import pytest
from fastapi.testclient import TestClient

import app.main as main
from app.schemas.capabilities import RebookingSearchRequest, RebookingSelectRequest
from app.services.rebooking import (
    process_rebooking_selection,
    search_flight_offers,
)

client = TestClient(main.app)


@pytest.fixture(autouse=True)
def fake_airlabs_schedule(monkeypatch):
    import app.services.rebooking as service
    monkeypatch.setattr(service, "AIRLABS_API_KEY", "test-key")
    from datetime import timedelta
    now = service.now_ist()
    departure = now + timedelta(hours=2)
    arrival = departure + timedelta(hours=2)
    monkeypatch.setattr(service, "find_alternatives", lambda *args, **kwargs: [
        {"flight_number": "6E512", "departure": departure.isoformat(),
         "arrival": arrival.isoformat(), "aircraft": "A320neo", "airline": "IndiGo"}
    ])


def test_search_flight_offers():
    req = RebookingSearchRequest(
        origin="DEL",
        destination="BOM",
        disrupted_flight_number="6E204",
        max_wait_hours=12.0,
    )
    res = search_flight_offers(req)
    assert res.origin == "DEL"
    assert res.destination == "BOM"
    assert res.offers_count > 0
    first_offer = res.offers[0]
    assert first_offer.origin == "DEL"
    assert first_offer.destination == "BOM"
    assert first_offer.price_inr is None
    assert first_offer.data_source == "airlabs_schedule"
    assert first_offer.price_status == "not_provided_by_schedule_provider"
    assert first_offer.availability_status == "schedule_only_not_seat_confirmed"


def test_rebooking_selection_progression():
    # 1. Search to get an offer
    search_req = RebookingSearchRequest(
        origin="BOM",
        destination="BLR",
        disrupted_flight_number="AI504",
    )
    search_res = search_flight_offers(search_req)
    offer = search_res.offers[0]

    # 2. Select without explicit confirmation -> must require confirmation
    select_req_1 = RebookingSelectRequest(
        pnr="PNR123",
        passenger_name="Sita Devi",
        selected_offer_id=offer.offer_id,
        disrupted_flight_number="AI504",
        explicit_confirmation=False,
    )
    res_1 = process_rebooking_selection(select_req_1)
    assert res_1.status == "quote_ready"
    assert res_1.confirmation_required is True
    assert res_1.voucher_id is None

    # 3. Explicit confirmation only authorizes airline handoff; no voucher is issued.
    select_req_2 = RebookingSelectRequest(
        pnr="PNR123",
        passenger_name="Sita Devi",
        selected_offer_id=offer.offer_id,
        disrupted_flight_number="AI504",
        explicit_confirmation=True,
    )
    res_2 = process_rebooking_selection(select_req_2)
    assert res_2.status == "handoff_ready"
    assert res_2.confirmation_required is False
    assert res_2.voucher_id is None
    assert "has not booked" in res_2.agent_presentation_instructions


def test_api_rebooking_endpoints():
    search_payload = {
        "origin": "DEL",
        "destination": "BLR",
        "disrupted_flight_number": "6E101",
        "max_wait_hours": 24.0,
    }
    resp = client.post("/api/v1/rebooking/search", json=search_payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["origin"] == "DEL"
    assert len(data["offers"]) > 0

    chosen_offer = data["offers"][0]
    select_payload = {
        "pnr": "CONF99",
        "passenger_name": "Karan Mehra",
        "selected_offer_id": chosen_offer["offer_id"],
        "disrupted_flight_number": "6E101",
        "explicit_confirmation": True,
    }
    select_resp = client.post("/api/v1/rebooking/select", json=select_payload)
    assert select_resp.status_code == 200
    handoff_data = select_resp.json()
    assert handoff_data["status"] == "handoff_ready"
    assert handoff_data["voucher_id"] is None


def test_api_rebooking_stream():
    search_payload = {
        "origin": "DEL",
        "destination": "BOM",
        "disrupted_flight_number": "6E204",
    }
    with client.stream("POST", "/api/v1/rebooking/stream", json=search_payload) as r:
        assert r.status_code == 200
        content = r.read().decode("utf-8")
        assert "event: status" in content
        assert "event: offers" in content
        assert "event: rights" in content
        assert "event: done" in content


def test_unknown_offer_is_rejected():
    req = RebookingSelectRequest(
        pnr="PNR123", passenger_name="Sita Devi", selected_offer_id="NOT-REAL",
        disrupted_flight_number="AI504", explicit_confirmation=True,
    )
    with pytest.raises(ValueError, match="unknown or expired"):
        process_rebooking_selection(req)


def test_empty_provider_result_does_not_create_demo_flights(monkeypatch):
    import app.services.rebooking as service
    monkeypatch.setattr(service, "find_alternatives", lambda *args, **kwargs: [])
    req = RebookingSearchRequest(
        origin="MAA", destination="DEL", disrupted_flight_number="6E204"
    )
    result = search_flight_offers(req)
    assert result.offers == []
    assert result.offers_count == 0
