
import json
import logging

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
    passenger_name: str = "Passenger",
    disruption_type: str = "cancellation",
    out_of_pocket_expenses_inr: float = 0.0,
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
            scenario_facts={"type": disruption_type, "flight_number": flight_number},
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
        logger.exception("Claim package tool failed")
        return f"Could not generate claim package: {str(exc)}"


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
    Evaluates departure times, wait deltas, price estimates, and DGCA
    compensation impact (e.g. whether alternate within 2h affects compensation).

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
                "offers": [o.model_dump() for o in res.offers[:4]],
                "rights_note": res.passenger_rights_note,
            },
            ensure_ascii=False,
            default=str,
        )
    except Exception as exc:
        logger.exception("Alternative flight search tool failed")
        return f"Could not retrieve alternative flights: {str(exc)}"


# ==================================================
# TOOL 5: EMERGENCY STAY & TRANSPORT
# ==================================================

@tool
def find_emergency_stay_and_transport(
    airport_code: str,
    delay_hours: float = 6.0,
    is_overnight: bool = True,
    airline_name: str = "",
) -> str:
    """
    Find emergency hotel accommodation and airport taxi transport for
    stranded passengers. Evaluates statutory duty-of-care under DGCA Para 3.4.3
    and provides airline counter demand scripts and verified hotel options.

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
                "transport_options": [t.model_dump() for t in res.transport],
                "counter_script": res.counter_demand_script,
            },
            ensure_ascii=False,
            default=str,
        )
    except Exception as exc:
        logger.exception("Emergency stay tool failed")
        return f"Could not retrieve emergency stay options: {str(exc)}"


# ==================================================
# REGISTER TOOLS
# ==================================================

flight_tools = [
    search_dgca_policy,
    get_live_flight_status,
    prepare_passenger_claim_package,
    search_alternative_flights,
    find_emergency_stay_and_transport,
]
