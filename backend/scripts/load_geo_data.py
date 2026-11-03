import csv
from pymongo import MongoClient, ReplaceOne
from app.core.config import BASE_DIR, MONGO_URI, MONGO_DB
from app.services.geo import haversine_km

DATA = BASE_DIR / "data"


def clean(value):
    """OpenFlights writes 'empty' as \\N."""
    return None if value in (r"\N", "") else value


def load_airports(country="India"):
    airports = []
    with open(DATA / "airports.dat", encoding="utf-8") as f:
        for row in csv.reader(f):
            if len(row) < 14 or row[3] != country or row[12] != "airport":
                continue
            iata = clean(row[4])
            if not iata:
                continue
            airports.append({
                "iata": iata, "name": row[1], "city": clean(row[2]),
                "country": row[3], "lat": float(row[6]), "lon": float(row[7]),
                "tz": clean(row[11]), "source": "OpenFlights",
            })
    return airports


def load_routes(iata_codes):
    routes = {}
    with open(DATA / "routes.dat", encoding="utf-8") as f:
        for row in csv.reader(f):
            if len(row) < 9:
                continue
            airline, src, dst, stops = clean(row[0]), row[2], row[4], row[7]
            if airline and stops == "0" and src in iata_codes and dst in iata_codes:
                routes[(airline, src, dst)] = {
                    "airline": airline, "origin": src, "destination": dst,
                    "source": "OpenFlights",
                }
    return list(routes.values())


airports = load_airports()
codes = {a["iata"] for a in airports}
routes = load_routes(codes)
print(f"Indian airports: {len(airports)} | direct domestic routes: {len(routes)}")

db = MongoClient(MONGO_URI)[MONGO_DB]
db["airports"].bulk_write(
    [ReplaceOne({"iata": a["iata"]}, a, upsert=True) for a in airports])
db["routes"].bulk_write(
    [ReplaceOne({"airline": r["airline"], "origin": r["origin"], "destination": r["destination"]},
                r, upsert=True) for r in routes])
print("Saved to Atlas: airports, routes")

# Sanity checks
by_code = {a["iata"]: a for a in airports}
maa, dl = by_code["MAA"], by_code["DEL"]
print(f"MAA: {maa['name']} ({maa['city']})")
print(f"MAA to DEL distance: {haversine_km(maa['lat'], maa['lon'], dl['lat'], dl['lon']):.0f} km")
airlines = sorted({r["airline"] for r in routes if r["origin"] == "MAA" and r["destination"] == "DEL"})
print("Airlines on MAA to DEL in this dataset:", airlines or "none")