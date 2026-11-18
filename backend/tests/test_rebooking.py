import pytest
from fastapi.testclient import TestClient

import app.main as main
from app.schemas.capabilities import RebookingSearchRequest, RebookingSelectRequest
from app.services.rebooking import (
    process_rebooking_selection,
    search_flight_offers,
)

client = TestClient(main.app)


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
    assert first_offer.price_inr is not None
    assert first_offer.price_inr > 0
    assert "DGCA" in first_offer.dgca_compensation_impact or "Statutory" in first_offer.dgca_compensation_impact


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

    # 3. Select WITH explicit confirmation -> issues voucher
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
    assert res_2.voucher_id is not None
    assert "REBOOK-VOUCHER" in res_2.voucher_id
    assert "PNR123" in res_2.agent_presentation_instructions


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
    assert handoff_data["voucher_id"] is not None


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
