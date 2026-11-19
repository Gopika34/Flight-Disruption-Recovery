

import logging
import json

from langchain_core.tools import tool

from app.rag.retriever import search_with_related
from app.services.flights import get_flight_status, FlightDataError


logger = logging.getLogger(__name__)


# ==================================================
# TOOL 1: DGCA POLICY SEARCH
# ==================================================

@tool
def search_dgca_policy(query: str) -> str:
    """
    Search Indian DGCA aviation regulations and retrieve
    relevant clauses and supporting policy evidence.

    Use this tool when passengers ask about aviation rules,
    cancellation, delays, denied boarding or passenger rights.
    """

    try:
        results = search_with_related(query, k=4)

        if not results:
            return "No relevant DGCA policy clauses were found."

        return json.dumps(
            results,
            ensure_ascii=False,
            default=str,
        )

    except Exception:
        logger.exception("DGCA policy tool failed")
        return "DGCA policy retrieval is currently unavailable."


# ==================================================
# TOOL 2: LIVE FLIGHT STATUS
# ==================================================

@tool
def get_live_flight_status(flight_number: str) -> str:
    """
    Retrieve live or scheduled flight information using AirLabs.

    Use this tool when passengers ask about a specific flight's
    status, departure, arrival or delay.

    Accepts an IATA flight number such as 6E204 or AI202.
    """

    try:
        result = get_flight_status(flight_number)

        if result is None:
            return "No matching flight record was returned."

        return json.dumps(
            result,
            ensure_ascii=False,
            default=str,
        )

    except (ValueError, FlightDataError) as error:
        return str(error)

    except Exception:
        logger.exception("Flight status tool failed")
        return "Live flight status is temporarily unavailable."


# ==================================================
# TOOL 3: PREPARE PASSENGER CLAIM PACKAGE
# ==================================================

@tool
def prepare_passenger_claim_package(
    pnr: str,
    flight_number: str,
    disruption_type: str,
    passenger_name: str = "Passenger",
    out_of_pocket_expenses_inr: float = 0.0,
    scenario_facts: dict | None = None,
) -> str:
    """
    Prepare a complete statutory passenger compensation claim package.
    Generates a formal legal grievance notice under DGCA CAR Section 3,
    statutory timeline milestones, evidence checklists, and airline nodal contacts.

    Parameters:
    - pnr: Passenger booking reference (e.g. ABC123).
    - flight_number: Operating flight code (e.g. 6E204 or AI504).
    - passenger_name: Full passenger name.
    - disruption_type: cancellation, delay, denied_boarding, or downgrading.
    - out_of_pocket_expenses_inr: Extra expenses incurred for food/transport/hotel.
    """
    from app.schemas.capabilities import ClaimPackageRequest
    from app.services.claims import build_claim_package

    try:
        req = ClaimPackageRequest(
            passenger_name=passenger_name,
            pnr=pnr,
            flight_number=flight_number,
            out_of_pocket_expenses_inr=out_of_pocket_expenses_inr,
            scenario_facts={**(scenario_facts or {}), "type": disruption_type,
                            "flight_number": flight_number},
        )
        res = build_claim_package(req)
        return json.dumps(
            {
                "status": "success",
                "pnr": res.pnr,
                "disruption_type": res.disruption_type,
                "statutory_compensation_inr": res.statutory_compensation_inr,
                "refund_status": res.refund_status,
                "care_status": res.care_status,
                "airline_contact": res.airline.model_dump(),
                "timeline_milestones": len(res.timeline),
                "evidence_checklist_items": len(res.evidence_checklist),
                "grievance_notice_preview": res.formal_grievance_notice[:350] + "...",
            },
            ensure_ascii=False,
            default=str,
        )
    except Exception as exc:
        from app.services.claims import ClaimFactsIncomplete
        if isinstance(exc, ClaimFactsIncomplete):
            return json.dumps({
                "status": exc.status,
                "missing_facts": exc.missing_facts,
                "notes": exc.notes,
                "next_action": "Ask the passenger for these facts; do not invent them.",
            })
        logger.exception("Claim package tool failed")
        return "Claim package generation is temporarily unavailable."


# ==================================================
# TOOL 4: SEARCH ALTERNATIVE FLIGHTS
# ==================================================

@tool
def search_alternative_flights(
    origin: str,
    destination: str,
    disrupted_flight_number: str,
    max_wait_hours: float = 24.0,
) -> str:
    """
    Search and compare alternative commercial flights for rebooking.
    Evaluates provider-returned schedule times and wait windows. AirLabs does
    not supply bookable fare or confirmed seat inventory through this integration.

    Parameters:
    - origin: 3-letter IATA origin airport (e.g. DEL, BOM).
    - destination: 3-letter IATA destination airport (e.g. BLR, MAA).
    - disrupted_flight_number: The flight that was delayed or cancelled.
    - max_wait_hours: Maximum allowable wait time in hours.
    """
    from app.schemas.capabilities import RebookingSearchRequest
    from app.services.rebooking import search_flight_offers

    try:
        req = RebookingSearchRequest(
            origin=origin,
            destination=destination,
            disrupted_flight_number=disrupted_flight_number,
            max_wait_hours=max_wait_hours,
        )
        res = search_flight_offers(req)
        return json.dumps(
            {
                "status": "success",
                "origin": res.origin,
                "destination": res.destination,
                "offers_count": res.offers_count,
                "search_status": res.search_status,
                "offers": [o.model_dump() for o in res.offers[:4]],
                "source_notice": "Schedule-only data; no live fares or confirmed seats.",
                "rights_note": res.passenger_rights_note,
            },
            ensure_ascii=False,
            default=str,
        )
    except Exception as exc:
        logger.exception("Alternative flight search tool failed")
        return "Alternative flight schedule search is temporarily unavailable."


# ==================================================
# TOOL 5: EMERGENCY STAY & TRANSPORT
# ==================================================

@tool
def find_emergency_stay_and_transport(
    airport_code: str,
    delay_hours: float,
    is_overnight: bool = False,
    airline_name: str = "",
    delay_start_local_time: str | None = None,
) -> str:
    """
    Find emergency hotel accommodation and airport taxi transport for
    stranded passengers. Evaluates the supplied timing facts and returns curated
    hotel directory references and estimated transport information. Availability is unverified.

    Parameters:
    - airport_code: 3-letter IATA airport code where passenger is stranded.
    - delay_hours: Duration of flight delay in hours.
    - is_overnight: Whether delay extends overnight or between 20:00 and 09:00.
    - airline_name: Name of operating airline responsible for care.
    """
    from app.schemas.capabilities import EmergencyStayRequest
    from app.services.stay_transport import search_emergency_stay_and_transport

    try:
        req = EmergencyStayRequest(
            airport_code=airport_code,
            delay_hours=delay_hours,
            is_overnight=is_overnight,
            delay_start_local_time=delay_start_local_time,
            airline_name=airline_name or None,
        )
        res = search_emergency_stay_and_transport(req)
        return json.dumps(
            {
                "status": "success",
                "airport": res.airport_code,
                "duty_of_care_mandated": res.duty_of_care_mandated,
                "statutory_clause": res.statutory_clause,
                "hotels_count": len(res.hotels),
                "top_hotels": [h.model_dump() for h in res.hotels[:3]],
                "availability_notice": "Hotel listings are unverified directory references; prices are estimates.",
                "transport_options": [t.model_dump() for t in res.transport],
                "counter_script": res.counter_demand_script,
            },
            ensure_ascii=False,
            default=str,
        )
    except Exception as exc:
        logger.exception("Emergency stay tool failed")
        return "Emergency stay information is temporarily unavailable."



# ==================================================
# TOOL 6: DETERMINISTIC DISRUPTION EVALUATION
# ==================================================

@tool
def evaluate_disruption(disruption_facts: dict) -> str:
    """Evaluate passenger entitlements using FlightGuard's deterministic Python rules.

    Supply only facts explicitly provided by the passenger or verified by a
    trusted provider. Supported keys are the Scenario schema fields: type,
    origin, destination, flight_number, notice_hours, delay_minutes,
    block_time_minutes, checked_in_on_time, domestic, and other documented
    Scenario fields. If required facts are missing, the tool returns the
    rule engine's missing-information result; never guess missing values.
    """
    from pydantic import ValidationError
    from app.schemas.scenario import Scenario
    from app.services.recovery import enrich_facts
    from app.rules.rule_engine import evaluate

    try:
        if not isinstance(disruption_facts, dict):
            return json.dumps({"status": "invalid_input", "message": "disruption_facts must be an object."})
        validated = Scenario.model_validate(disruption_facts).facts()
        if not validated.get("type"):
            return json.dumps({"status": "needs_more_info", "missing_facts": ["type"], "message": "Identify the disruption type before evaluating."})
        enriched, notes = enrich_facts(validated)
        decision = evaluate(enriched)
        return json.dumps({"status": decision.get("status", "ok"), "decision": decision, "assumptions_and_notes": notes, "facts_used": enriched}, ensure_ascii=False, default=str)
    except ValidationError as exc:
        return json.dumps({"status": "invalid_input", "validation_errors": exc.errors(include_input=False)}, ensure_ascii=False, default=str)
    except ValueError as exc:
        return json.dumps({"status": "needs_more_info", "message": str(exc), "next_action": "Ask the passenger for the missing or unsupported facts; do not infer them."})
    except Exception:
        logger.exception("Deterministic disruption evaluation tool failed")
        return json.dumps({"status": "unavailable", "message": "The entitlement engine is temporarily unavailable."})


# ==================================================
# REGISTER TOOLS
# ==================================================

flight_tools = [
    search_dgca_policy,
    get_live_flight_status,
    prepare_passenger_claim_package,
    search_alternative_flights,
    find_emergency_stay_and_transport,
    evaluate_disruption,

]
