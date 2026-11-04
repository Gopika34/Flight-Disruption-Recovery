"""Glue layer: rule engine decision + flight/hotel/cab tools = one recovery plan."""
import re
from datetime import datetime
from app.rules.rule_engine import evaluate
from app.rag.retriever import get_clause
from app.services.airports import get_airport, distance_km
from app.services.flights import find_alternatives, estimate_block_minutes, now_ist
from app.services.hotels import hotels_near, cab_estimate_inr


def base_id(clause_id):
    return re.sub(r"\(.*\)$", "", clause_id)            # "3.2.2(a)" -> "3.2.2"


def enrich_facts(facts):
    """Fill what we can work out ourselves, and say so (never silently)."""
    f, notes = dict(facts), []
    km = distance_km(f.get("origin"), f.get("destination"))
    if km is not None:
        if f.get("block_time_minutes") is None:
            f["block_time_minutes"] = estimate_block_minutes(km)
            notes.append(f"Block time estimated as {f['block_time_minutes']} min from the "
                         f"{km:.0f} km route distance; give the scheduled block time for an exact answer.")
        if f.get("domestic") is None:
            f["domestic"] = True
            notes.append("Both airports are in India, so the flight is treated as domestic.")
        if f.get("type") == "downgrading":
            f.setdefault("sector", "domestic")
            f.setdefault("distance_km", round(km))
    return f, notes


def fetch_clauses(clause_ids):
    """Exact text of the clauses the engine cited (no similarity guessing needed)."""
    out = []
    try:
        for cid in dict.fromkeys(base_id(c) for c in clause_ids):
            c = get_clause(cid)
            if c:
                out.append({"clause_id": c["clause_id"], "section_title": c.get("section_title"),
                            "page_start": c.get("page_start"), "text": c["text"]})
    except Exception:
        pass                                              # DB down: still return the plan
    return out


def _wants_alternatives(kind, decision, facts):
    if kind in ("cancellation", "denied_boarding"):
        return True
    return kind == "delay" and (decision.get("alt_or_refund") or (facts.get("delay_minutes") or 0) >= 180)


def plan_recovery(facts):
    facts, notes = enrich_facts(facts)
    decision = evaluate(facts)                            # raises ValueError for unknown type
    decision["assumptions"] = decision["assumptions"] + notes
    plan = {"decision": decision, "alternatives": [], "stay": None, "clauses": []}
    if decision["status"] != "ok":
        return plan

    now = now_ist()
    origin, dest = facts.get("origin"), facts.get("destination")
    if origin and dest and _wants_alternatives(facts["type"], decision, facts):
        plan["alternatives"] = find_alternatives(origin, dest, after=now,
                                                 exclude_flight=facts.get("flight_number"))

    owed = bool(decision.get("hotel"))
    wait_hours = None
    if plan["alternatives"]:
        wait_hours = (datetime.fromisoformat(plan["alternatives"][0]["departure"]) - now).total_seconds() / 3600
    if origin and (owed or (wait_hours is not None and wait_hours > 8)):
        hotels = hotels_near(origin)
        if hotels:
            best = hotels[0]
            plan["stay"] = {
                "owed_by_airline": owed, "hotel": best,
                "cab_estimate_inr": cab_estimate_inr(best["distance_from_airport_km"]),
                "note": ("The airline must provide this (3.4.3 / 3.8)." if owed else
                         "Not owed by the airline, but your next flight is far away; this is an optional, self-paid option."),
            }

    plan["clauses"] = fetch_clauses(decision["clauses"])
    return plan