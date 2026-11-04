"""Indian airports from OpenFlights, read once from data/airports.dat."""
import csv
from functools import lru_cache
from app.core.config import DATA_DIR
from app.services.geo import haversine_km


@lru_cache(maxsize=1)
def load_airports():
    airports = {}
    with open(DATA_DIR / "airports.dat", encoding="utf-8") as f:
        for row in csv.reader(f):
            if len(row) < 14 or row[3] != "India" or row[12] != "airport":
                continue
            iata = row[4]
            if iata in ("", r"\N"):
                continue
            airports[iata] = {"iata": iata, "name": row[1], "city": row[2],
                              "lat": float(row[6]), "lon": float(row[7])}
    return airports


def get_airport(iata):
    return load_airports().get((iata or "").upper())


def distance_km(a, b):
    pa, pb = get_airport(a), get_airport(b)
    if not pa or not pb:
        return None
    return haversine_km(pa["lat"], pa["lon"], pb["lat"], pb["lon"])


def nearby_airports(iata, radius_km=150):
    """[(code, km)] of other Indian airports within radius, closest first."""
    here = get_airport(iata)
    if not here:
        return []
    found = []
    for code, a in load_airports().items():
        if code == here["iata"]:
            continue
        km = haversine_km(here["lat"], here["lon"], a["lat"], a["lon"])
        if km <= radius_km:
            found.append((code, round(km)))
    return sorted(found, key=lambda x: x[1])