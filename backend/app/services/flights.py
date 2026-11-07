"""Live flight schedules/status from AirLabs.

AirLabs free schedules are documented as covering up to 10 hours ahead and
allow a maximum limit of 50 records for free keys. The provider does not return
seat inventory or fares in this endpoint; this module never fabricates either.
"""
from __future__ import annotations

import logging
import threading
import time
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx

from app.core.config import AIRLABS_API_KEY, FLIGHT_API_CACHE_TTL_S, FLIGHT_API_TIMEOUT_S
from app.services.airports import distance_km

logger = logging.getLogger(__name__)
BASE_URL = "https://airlabs.co/api/v9"
IST = timezone(timedelta(hours=5, minutes=30))

# Common Indian airline codes.
# Unknown codes are displayed as their original IATA code.
AIRLINE_NAMES = {
    "AI": "Air India",
    "IX": "Air India Express",
    "6E": "IndiGo",
    "SG": "SpiceJet",
    "QP": "Akasa Air",
    "9I": "Alliance Air",
}

INDIAN_OPERATING_AIRLINES = {
    "AI",  # Air India
    "IX",  # Air India Express
    "6E",  # IndiGo
    "SG",  # SpiceJet
    "QP",  # Akasa Air
    "9I",  # Alliance Air
}

def now_ist():
    return datetime.now(IST)


def estimate_block_minutes(km):
    """Display-only estimate; never use this for legal eligibility."""
    return int(round((km / 700 * 60 + 30) / 5) * 5)
_CACHE: dict[tuple, tuple[float, Any]] = {}
_CACHE_LOCK = threading.Lock()


class FlightDataError(RuntimeError):
    """A safe, user-facing flight provider error (never contains the API key)."""


def _cached(key):
    with _CACHE_LOCK:
        item = _CACHE.get(key)
        if item and item[0] > time.monotonic():
            return item[1]
        if item:
            _CACHE.pop(key, None)
    return None


def _store(key, value):
    with _CACHE_LOCK:
        _CACHE[key] = (time.monotonic() + FLIGHT_API_CACHE_TTL_S, value)
        if len(_CACHE) > 512:
            now = time.monotonic()
            for cache_key in [k for k, v in _CACHE.items() if v[0] <= now]:
                _CACHE.pop(cache_key, None)


def _request(endpoint: str, params: dict[str, Any]):
    if not AIRLABS_API_KEY:
        raise FlightDataError("Live flight data is not configured. Set AIRLABS_API_KEY.")
    request_params = {**params, "api_key": AIRLABS_API_KEY}
    try:
        response = httpx.get(
            f"{BASE_URL}/{endpoint}",
            params=request_params,
            timeout=FLIGHT_API_TIMEOUT_S,
        )
        response.raise_for_status()
        payload = response.json()
    except httpx.TimeoutException as exc:
        raise FlightDataError("AirLabs did not respond before the timeout.") from exc
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 429:
            raise FlightDataError("AirLabs rate limit reached. Try again later.") from exc
        raise FlightDataError(f"AirLabs returned HTTP {exc.response.status_code}.") from exc
    except (httpx.HTTPError, ValueError) as exc:
        raise FlightDataError("Could not read a valid response from AirLabs.") from exc

    if isinstance(payload, dict) and payload.get("error"):
        error = payload["error"]
        code = error.get("code", "provider_error") if isinstance(error, dict) else "provider_error"
        if code in {"month_limit_exceeded", "hour_limit_exceeded", "minute_limit_exceeded"}:
            raise FlightDataError("AirLabs request quota has been reached.")
        if code in {"unknown_api_key", "expired_api_key"}:
            raise FlightDataError("AirLabs API key is invalid or expired.")
        if code == "not_found":
            return None
        raise FlightDataError(f"AirLabs rejected the request ({code}).")
    return payload


def _records(payload):
    if payload is None:
        return []
    if isinstance(payload, dict):
        payload = payload.get("response", payload)
    if isinstance(payload, dict):
        return [payload]
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    return []


def _to_ist(timestamp, utc_fallback, local_fallback):
    if timestamp:
        try:
            return datetime.fromtimestamp(int(timestamp), timezone.utc).astimezone(IST)
        except (TypeError, ValueError, OSError):
            pass
    if utc_fallback:
        try:
            return datetime.strptime(utc_fallback, "%Y-%m-%d %H:%M").replace(tzinfo=timezone.utc).astimezone(IST)
        except (TypeError, ValueError):
            pass
    if local_fallback:
        try:
            # The current route dataset is India-only; AirLabs local airport time is IST.
            return datetime.strptime(local_fallback, "%Y-%m-%d %H:%M").replace(tzinfo=IST)
        except (TypeError, ValueError):
            pass
    return None


# def _normalise_schedule(item):
#     departure = _to_ist(
#         item.get("dep_time_ts"),
#         item.get("dep_time_utc"),
#         item.get("dep_time"),
#     )

#     arrival = _to_ist(
#         item.get("arr_time_ts"),
#         item.get("arr_time_utc"),
#         item.get("arr_time"),
#     )

#     if not departure:
#         return None

#     flight_number = item.get("flight_iata")
#     airline_code = item.get("airline_iata")

#     airline_name = AIRLINE_NAMES.get(
#         airline_code,
#         airline_code or "Unknown airline",
#     )

#     if flight_number:
#         display_name = f"{airline_name} ({flight_number})"
#     else:
#         display_name = airline_name

#     return {
#         "flight_number": flight_number,
#         "airline": airline_code,
#         "airline_code": airline_code,
#         "airline_name": airline_name,
#         "display_name": display_name,

#         "origin": item.get("dep_iata"),
#         "destination": item.get("arr_iata"),

#         "departure": departure.isoformat(),
#         "arrival": arrival.isoformat() if arrival else None,

#         "status": item.get("status") or "unknown",
#         "delay_minutes": item.get("dep_delayed"),
#         "duration_minutes": item.get("duration"),

#         "departure_terminal": item.get("dep_terminal"),
#         "departure_gate": item.get("dep_gate"),
#         "arrival_terminal": item.get("arr_terminal"),
#         "arrival_gate": item.get("arr_gate"),

#         "fare_inr": None,
#         "seats_available": None,
#         "availability_confirmed": False,

#         "simulated": False,
#         "provider": "AirLabs",
#     }
    
def _normalise_schedule(item):
    departure = _to_ist(
        item.get("dep_time_ts"),
        item.get("dep_time_utc"),
        item.get("dep_time"),
    )

    arrival = _to_ist(
        item.get("arr_time_ts"),
        item.get("arr_time_utc"),
        item.get("arr_time"),
    )

    if not departure:
        return None

    # AirLabs codeshare fields identify the operating carrier.
    marketing_code = item.get("airline_iata")
    marketing_flight = item.get("flight_iata")

    operating_code = (
        item.get("cs_airline_iata") or marketing_code
    )
    operating_flight = (
        item.get("cs_flight_iata") or marketing_flight
    )

    airline_name = AIRLINE_NAMES.get(
        operating_code,
        operating_code or "Unknown airline",
    )

    return {
        # Actual operating flight
        "flight_number": operating_flight,
        "airline": operating_code,
        "airline_code": operating_code,
        "airline_name": airline_name,
        "display_name": (
            f"{airline_name} ({operating_flight})"
            if operating_flight else airline_name
        ),

        # Original marketed flight, retained for traceability
        "marketing_airline_code": marketing_code,
        "marketing_flight_number": marketing_flight,

        "origin": item.get("dep_iata"),
        "destination": item.get("arr_iata"),

        "departure": departure.isoformat(),
        "arrival": arrival.isoformat() if arrival else None,

        "status": item.get("status") or "unknown",
        "delay_minutes": item.get("dep_delayed"),
        "duration_minutes": item.get("duration"),

        "departure_terminal": item.get("dep_terminal"),
        "departure_gate": item.get("dep_gate"),
        "arrival_terminal": item.get("arr_terminal"),
        "arrival_gate": item.get("arr_gate"),

        "fare_inr": None,
        "seats_available": None,
        "availability_confirmed": False,

        "simulated": False,
        "provider": "AirLabs",
    }
    
def find_alternatives(origin, destination, after=None, days=0, limit=5, exclude_flight=None, **_ignored):
    """Return live scheduled flights for a route, within AirLabs' 10h horizon.

    `days` is accepted for compatibility with the old simulated provider but is
    deliberately ignored: AirLabs does not promise schedules beyond 10 hours.
    """
    origin, destination = (origin or "").upper(), (destination or "").upper()
    if len(origin) != 3 or len(destination) != 3:
        raise ValueError("origin and destination must be 3-letter IATA codes")
    after = after or datetime.now(IST)
    if after.tzinfo is None:
        after = after.replace(tzinfo=IST)

    cache_key = ("schedules", origin, destination)
    records = _cached(cache_key)
    if records is None:
        payload = _request("schedules", {
            "dep_iata": origin,
            "arr_iata": destination,
            "limit": min(max(int(limit) * 5, 10), 50),
            "_fields": (
                "airline_iata,flight_iata,"
                "cs_airline_iata,cs_flight_iata,cs_flight_number,"
                "dep_iata,arr_iata,"
                "dep_time,dep_time_ts,dep_time_utc,"
                "arr_time,arr_time_ts,arr_time_utc,"
                "status,dep_delayed,duration,"
                "dep_terminal,dep_gate,arr_terminal,arr_gate"
            ),
        })
        records = _records(payload)
        _store(cache_key, records)

    options = []
    seen = set()

    for item in records:
        flight = _normalise_schedule(item)

        if not flight:
            continue

        if (
            flight["origin"] != origin
            or flight["destination"] != destination
        ):
            continue

        if flight["status"] not in {"scheduled", "unknown"}:
            continue

        if datetime.fromisoformat(flight["departure"]) <= after:
            continue

        if exclude_flight and (
            flight["flight_number"] or ""
        ).upper() == exclude_flight.upper():
            continue

        # Restrict to the configured Indian operating carriers.
        if flight["airline_code"] not in INDIAN_OPERATING_AIRLINES:
            continue

        # Prefer the actual operating flight number for deduplication.
        operating_flight = flight.get("flight_number")

        if operating_flight:
            dedupe_key = (
                origin,
                destination,
                operating_flight.upper(),
                flight["departure"],
            )
        else:
            dedupe_key = (
                origin,
                destination,
                flight["departure"],
            )

        if dedupe_key in seen:
            continue

        seen.add(dedupe_key)

        flight["kind"] = "live_schedule"
        flight["note"] = (
            "Live AirLabs schedule. Operating carrier identified where "
            "codeshare data is supplied. Seat inventory and fares are "
            "not supplied by this endpoint."
        )

        options.append(flight)

    return sorted(
        options,
        key=lambda item: item["departure"],
    )[:limit]


def get_flight_status(flight_number: str):
    flight_number = (flight_number or "").strip().upper()
    if not flight_number.isalnum() or not 2 <= len(flight_number) <= 12:
        raise ValueError("flight_number must be an IATA flight number, e.g. AI202")
    cache_key = ("flight", flight_number)
    payload = _cached(cache_key)
    if payload is None:
        payload = _request("flight", {"flight_iata": flight_number})
        _store(cache_key, payload)
    records = _records(payload)
    if not records:
        return None
    result = _normalise_schedule(records[0])
    if result is None:
        item = records[0]
        result = {
            "flight_number": item.get("flight_iata"),
            "airline": item.get("airline_iata"),
            "origin": item.get("dep_iata"),
            "destination": item.get("arr_iata"),
            "status": item.get("status") or "unknown",
            "departure": item.get("dep_time_utc"),
            "arrival": item.get("arr_time_utc"),
            "delay_minutes": item.get("dep_delayed"),
            "simulated": False,
            "provider": "AirLabs",
        }
    result["position"] = {
        "latitude": records[0].get("lat"),
        "longitude": records[0].get("lng"),
        "altitude_m": records[0].get("alt"),
        "speed_kmh": records[0].get("speed"),
        "heading_degrees": records[0].get("dir"),
    }
    result["updated_at_unix"] = records[0].get("updated")
    return result
