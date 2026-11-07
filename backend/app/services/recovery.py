"""Glue layer: rule engine decision + flight/hotel/cab tools = one recovery plan."""
import logging
import re
from datetime import datetime
from app.rules.rule_engine import evaluate
from app.rag.retriever import RetrievalUnavailable, get_clause
from app.services.airports import distance_km
from app.services.flights import (
    FlightDataError, find_alternatives, estimate_block_minutes, now_ist,
)
from app.core.config import AIRLABS_API_KEY


logger = logging.getLogger(__name__)


def base_id(clause_id):
    return re.sub(r"\(.*\)$", "", clause_id)            # "3.2.2(a)" -> "3.2.2"


def enrich_facts(facts):
    """Fill what we can work out ourselves, and say so (never silently).

    Only facts that are genuinely derivable are added. An ESTIMATED flight
    time is never written into block_time_minutes: the legal thresholds need
    the scheduled block time, so the passenger is asked for it instead.
    """
    f, notes = dict(facts), []
    km = distance_km(f.get("origin"), f.get("destination"))
    if km is not None:
        if f.get("block_time_minutes") is None:
            notes.append(
                f"Estimated flight time is about {estimate_block_minutes(km)} min "
                f"({km:.0f} km route), shown for information only and NOT used for "
                f"eligibility. Please give the scheduled duration of the flight."
            )
        if f.get("domestic") is None:
            f["domestic"] = True                          # the airport list only holds Indian airports
            notes.append("Both airports are in India, so the flight is treated as domestic.")
        if f.get("type") == "downgrading":
            f.setdefault("sector", "domestic")
            f.setdefault("distance_km", round(km))
    return f, notes


def flight_info(facts):
    """Display-only route facts. Never fed to the rule engine."""
    km = distance_km(facts.get("origin"), facts.get("destination"))
    if km is None:
        return None
    return {
        "route_distance_km": round(km),
        "estimated_block_time_minutes": estimate_block_minutes(km),
        "estimate_note": "Estimate for information only; not used for eligibility.",
    }


def fetch_clauses(clause_ids):
    """Exact text of the clauses the engine cited.

    Returns (clauses, evidence). evidence["status"] is:
      "ok"          every cited clause was retrieved
      "partial"     the database answered but some clauses do not exist
      "unavailable" the database could not be reached (no clause text at all)
    """
    wanted = list(dict.fromkeys(base_id(c) for c in clause_ids))
    out, missing = [], []

    for cid in wanted:
        try:
            c = get_clause(cid)
        except RetrievalUnavailable:
            logger.exception("Policy database unavailable while fetching clauses")
            return [], {"status": "unavailable", "missing_clause_ids": wanted}
        if c:
            out.append({"clause_id": c["clause_id"], "section_title": c.get("section_title"),
                        "page_start": c.get("page_start"), "text": c["text"]})
        else:
            missing.append(cid)

    status = "ok" if not missing else "partial"
    return out, {"status": status, "missing_clause_ids": missing}


def _wants_alternatives(kind, decision, facts):
    if kind in ("cancellation", "denied_boarding"):
        return True
    return kind == "delay" and (decision.get("alt_or_refund") or (facts.get("delay_minutes") or 0) >= 180)


def plan_recovery(facts):
    facts, notes = enrich_facts(facts)
    decision = evaluate(facts)                            # raises ValueError for unknown type
    decision["assumptions"] = decision["assumptions"] + notes
    plan = {"decision": decision, "alternatives": [], "stay": None, "clauses": [],
            "flight_info": flight_info(facts),
            "flight_data": {"provider": "AirLabs", "status": "not_requested", "coverage_hours": 10},
            "evidence": {"status": "not_requested", "missing_clause_ids": []}}
    if decision["status"] != "ok":
        return plan

    now = now_ist()
    origin, dest = facts.get("origin"), facts.get("destination")
    if origin and dest and _wants_alternatives(facts["type"], decision, facts):
        if not AIRLABS_API_KEY:
            plan["flight_data"] = {
                "provider": "AirLabs", "status": "not_configured", "coverage_hours": 10,
                "message": "Set AIRLABS_API_KEY to retrieve live flight schedules.",
            }
        else:
            try:
                plan["alternatives"] = find_alternatives(
                    origin, dest, after=now, exclude_flight=facts.get("flight_number")
                )
                plan["flight_data"] = {
                    "provider": "AirLabs", "status": "live_data", "coverage_hours": 10,
                    "result_count": len(plan["alternatives"]),
                    "message": (
                        "Schedules are only available up to 10 hours ahead. "
                        "Seat inventory and fares are not supplied by this endpoint."
                        if plan["alternatives"] else
                        "AirLabs returned no matching schedule records in its available window. "
                        "This does not prove that no airline alternative exists."
                    ),
                }
            except FlightDataError as error:
                logger.warning("Live flight lookup failed: %s", error)
                plan["flight_data"] = {
                    "provider": "AirLabs", "status": "unavailable", "coverage_hours": 10,
                    "message": str(error),
                }

    owed = bool(decision.get("hotel"))
    wait_hours = None
    if plan["alternatives"]:
        wait_hours = (datetime.fromisoformat(plan["alternatives"][0]["departure"]) - now).total_seconds() / 3600
    if owed or (origin and wait_hours is not None and wait_hours > 8):
        plan["stay"] = {
            "owed_by_airline": owed,
            "provider_status": "not_integrated",
            "hotel_options": [],
            "cab_estimate_inr": None,
            "note": (
                "The airline must provide hotel accommodation and transfers where 3.4.3 / 3.8 applies. "
                "No live hotel inventory provider is integrated, so this system will not invent hotel names or prices."
                if owed else
                "A long wait is indicated, but no live hotel inventory provider is integrated. "
                "No hotel names or prices are fabricated."
            ),
        }

    plan["clauses"], plan["evidence"] = fetch_clauses(decision["clauses"])
    return plan