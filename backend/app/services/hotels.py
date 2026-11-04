"""Simulated hotels and cab prices (clearly marked simulated). Swap for a real API later."""
import random
from app.services.airports import get_airport

OLD_NAMES = {"Madras": "Chennai", "Bombay": "Mumbai", "Calcutta": "Kolkata", "Bangalore": "Bengaluru"}
TIERS = [("Budget Stay", 1800, 2800), ("Comfort Suites", 3000, 4800), ("Grand Residency", 5500, 9000)]


def hotels_near(iata, limit=3):
    airport = get_airport(iata)
    if not airport:
        return []
    rng = random.Random(f"hotels-{iata}")
    city = OLD_NAMES.get(airport["city"], airport["city"]) or iata
    hotels = [{
        "name": f"{city} {label}",
        "price_per_night_inr": rng.randrange(low, high, 50),
        "distance_from_airport_km": rng.randint(3, 22),
        "simulated": True,
    } for label, low, high in TIERS]
    return sorted(hotels, key=lambda h: h["price_per_night_inr"])[:limit]


def cab_estimate_inr(km):
    return int(round(80 + 17 * km, -1))