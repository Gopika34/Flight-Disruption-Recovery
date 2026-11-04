"""Simulated flight schedule built from REAL routes (OpenFlights routes.dat).
Times, fares and seats are generated deterministically for today + the next days,
so the data never goes stale and needs no database. Everything is marked simulated."""
import csv
import random
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from app.core.config import DATA_DIR
from app.services.airports import load_airports, nearby_airports, distance_km

IST = timezone(timedelta(hours=5, minutes=30))
CRUISE_KMH = 700


def now_ist():
    return datetime.now(IST)


def estimate_block_minutes(km):
    return int(round((km / CRUISE_KMH * 60 + 30) / 5) * 5)      # flight time + taxi/climb buffer


@lru_cache(maxsize=1)
def _routes():
    codes = set(load_airports())
    seen, out = set(), []
    with open(DATA_DIR / "routes.dat", encoding="utf-8") as f:
        for row in csv.reader(f):
            if len(row) < 9:
                continue
            airline, src, dst, stops = row[0], row[2], row[4], row[7]
            if len(airline) != 2 or airline == r"\N" or stops != "0":
                continue
            if src not in codes or dst not in codes:
                continue
            key = (airline, src, dst)
            if key not in seen:
                seen.add(key)
                out.append(key)
    return out


@lru_cache(maxsize=512)
def _day_flights(origin, destination, day_iso):
    km = distance_km(origin, destination)
    if km is None:
        return []
    day = datetime.fromisoformat(day_iso).replace(tzinfo=IST)
    flights = []
    for airline, src, dst in _routes():
        if src != origin or dst != destination:
            continue
        rng = random.Random(f"{airline}-{src}-{dst}-{day_iso}")     # same inputs, same flights
        hours = sorted(rng.sample(range(5, 23), rng.choice([1, 2, 2, 3])))
        for h in hours:
            dep = day.replace(hour=h, minute=rng.choice([0, 15, 30, 45]))
            arr = dep + timedelta(minutes=estimate_block_minutes(km))
            flights.append({
                "flight_number": f"{airline}{rng.randint(100, 999)}",
                "airline": airline, "origin": src, "destination": dst,
                "departure": dep.isoformat(), "arrival": arr.isoformat(),
                "fare_inr": int((1800 + km * 1.9) * rng.uniform(0.8, 1.5) // 10 * 10),
                "seats_available": rng.choice([0, 0, 2, 5, 9, 14, 20]),
                "simulated": True,
            })
    return flights


def _upcoming(origin, destination, after, days):
    out = []
    for d in range(days + 1):
        day = (after + timedelta(days=d)).date().isoformat()
        for f in _day_flights(origin, destination, day):
            if datetime.fromisoformat(f["departure"]) > after and f["seats_available"] > 0:
                out.append(dict(f))
    return sorted(out, key=lambda f: f["departure"])


def find_alternatives(origin, destination, after=None, days=2, limit=5,
                      exclude_flight=None, nearby_km=150):
    """Direct flights first; if there are few, also try nearby airports at either end."""
    after = after or now_ist()
    options = []
    for f in _upcoming(origin, destination, after, days):
        if f["flight_number"] != exclude_flight:
            f["kind"] = "direct"
            f["note"] = "Same route"
            options.append(f)

    if len(options) < 3:
        for code, km in nearby_airports(origin, nearby_km)[:4]:
            for f in _upcoming(code, destination, after, days)[:1]:
                f["kind"] = "nearby_origin"
                f["note"] = f"Depart from {code}, about {km} km from {origin} (ground transfer needed)"
                options.append(f)
        for code, km in nearby_airports(destination, nearby_km)[:4]:
            for f in _upcoming(origin, code, after, days)[:1]:
                f["kind"] = "nearby_destination"
                f["note"] = f"Land at {code}, about {km} km from {destination} (ground transfer needed)"
                options.append(f)

    return sorted(options, key=lambda f: f["departure"])[:limit]