from datetime import datetime, timedelta, timezone

import pytest

from app.services import flights

IST = timezone(timedelta(hours=5, minutes=30))


def _schedule(dep, status="scheduled", number="AI202", delay=0):
    departure = datetime.now(timezone.utc) + timedelta(hours=2)
    return {
        "flight_iata": number, "airline_iata": "AI", "dep_iata": "MAA", "arr_iata": "DEL",
        "dep_time_ts": int(departure.timestamp()), "arr_time_ts": int((departure + timedelta(hours=3)).timestamp()),
        "status": status, "dep_delayed": delay, "duration": 180,
    }


def test_live_alternatives_normalise_schedule_and_never_invent_fares(monkeypatch):
    monkeypatch.setattr(flights, "AIRLABS_API_KEY", "test-key")
    monkeypatch.setattr(flights, "_request", lambda endpoint, params: [_schedule(None)])
    flights._CACHE.clear()
    result = flights.find_alternatives("MAA", "DEL", after=datetime.now(IST), limit=3)
    assert len(result) == 1
    assert result[0]["provider"] == "AirLabs"
    assert result[0]["simulated"] is False
    assert result[0]["fare_inr"] is None
    assert result[0]["seats_available"] is None
    assert result[0]["availability_confirmed"] is False


def test_live_alternatives_exclude_cancelled_and_original_flight(monkeypatch):
    monkeypatch.setattr(flights, "AIRLABS_API_KEY", "test-key")
    monkeypatch.setattr(flights, "_request", lambda endpoint, params: [
        _schedule(None, status="cancelled", number="AI201"),
        _schedule(None, status="scheduled", number="AI202"),
    ])
    flights._CACHE.clear()
    result = flights.find_alternatives("MAA", "DEL", after=datetime.now(IST), exclude_flight="AI202")
    assert result == []


def test_live_provider_requires_api_key(monkeypatch):
    monkeypatch.setattr(flights, "AIRLABS_API_KEY", None)
    flights._CACHE.clear()
    with pytest.raises(flights.FlightDataError, match="AIRLABS_API_KEY"):
        flights.find_alternatives("MAA", "DEL")


def test_invalid_flight_number_rejected():
    with pytest.raises(ValueError):
        flights.get_flight_status("AI-202")


def test_flight_status_normalises_provider_response(monkeypatch):
    monkeypatch.setattr(flights, "AIRLABS_API_KEY", "test-key")
    flights._CACHE.clear()
    departure = datetime.now(timezone.utc) + timedelta(hours=1)
    payload = {"response": {
        "flight_iata": "AI202", "airline_iata": "AI", "dep_iata": "MAA", "arr_iata": "DEL",
        "dep_time_ts": int(departure.timestamp()), "status": "en-route",
        "lat": 13.0, "lng": 80.0, "alt": 9000, "updated": 123456,
    }}
    monkeypatch.setattr(flights, "_request", lambda endpoint, params: payload)
    result = flights.get_flight_status("ai202")
    assert result["flight_number"] == "AI202"
    assert result["status"] == "en-route"
    assert result["position"]["latitude"] == 13.0
    assert result["simulated"] is False


def test_airlabs_quota_error_is_reported_without_exposing_key(monkeypatch):
    monkeypatch.setattr(flights, "AIRLABS_API_KEY", "secret-test-key")
    monkeypatch.setattr(flights.httpx, "get", lambda *a, **k: _FakeResponse({
        "error": {"code": "month_limit_exceeded", "message": "quota"}
    }))
    with pytest.raises(flights.FlightDataError, match="quota") as exc:
        flights._request("schedules", {"dep_iata": "MAA", "arr_iata": "DEL"})
    assert "secret-test-key" not in str(exc.value)


class _FakeResponse:
    def __init__(self, payload, status=200):
        self._payload = payload
        self.status_code = status

    def raise_for_status(self):
        if self.status_code >= 400:
            raise flights.httpx.HTTPStatusError("error", request=None, response=self)

    def json(self):
        return self._payload
