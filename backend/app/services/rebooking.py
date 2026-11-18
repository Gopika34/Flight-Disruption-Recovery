"""Alternative flight discovery. AirLabs provides schedule data, not bookable fares.

This module intentionally does not invent prices, availability or reservations.
A production booking flow needs a separate offer/order provider integration.
"""
import logging
import uuid
import hashlib
from datetime import datetime, timedelta
import jwt

from app.core.config import AIRLABS_API_KEY
from app.schemas.capabilities import (
    FlightOffer, RebookingComparisonResponse, RebookingHandoffResponse,
    RebookingSearchRequest, RebookingSelectRequest,
)
from app.services.flights import FlightDataError, find_alternatives, now_ist

logger = logging.getLogger(__name__)

AIRLINE_DIRECT_URLS = {
    "6E": "https://www.goindigo.in", "AI": "https://www.airindia.com",
    "SG": "https://www.spicejet.com", "QP": "https://www.akasaair.com",
    "UK": "https://www.airindia.com",
}
AIRLINE_NAMES = {"6E": "IndiGo", "AI": "Air India", "SG": "SpiceJet", "QP": "Akasa Air", "UK": "Air India"}
OFFER_TTL = timedelta(minutes=10)


def _offer_signing_key() -> bytes:
    from app.core.config import GUEST_TOKEN_SECRET
    if not GUEST_TOKEN_SECRET or len(GUEST_TOKEN_SECRET) < 32:
        raise RuntimeError("Offer signing secret is not configured")
    return hashlib.sha256((GUEST_TOKEN_SECRET + ":flight-offers").encode()).digest()


def search_flight_offers(req: RebookingSearchRequest) -> RebookingComparisonResponse:
    now = now_ist()
    origin, dest = req.origin.upper(), req.destination.upper()
    if origin == dest:
        raise ValueError("Origin and destination must be different airports")

    raw_flights = []
    search_status = "provider_not_configured"
    if AIRLABS_API_KEY:
        try:
            raw_flights = find_alternatives(
                origin, dest, after=now,
                exclude_flight=req.disrupted_flight_number.upper(),
            ) or []
            search_status = "results_found" if raw_flights else "no_results"
        except FlightDataError as exc:
            search_status = "provider_unavailable"
            logger.warning("AirLabs alternative schedule lookup failed: %s", type(exc).__name__)

    offers: list[FlightOffer] = []
    for idx, flight in enumerate(raw_flights[:8]):
        try:
            dep = datetime.fromisoformat(flight["departure"])
            arr = datetime.fromisoformat(flight["arrival"])
            wait_hours = max(0.0, round((dep - now).total_seconds() / 3600, 1))
            if req.max_wait_hours is not None and wait_hours > req.max_wait_hours:
                continue
            duration = int((arr - dep).total_seconds() / 60)
            if duration <= 0:
                continue
            flight_number = str(flight["flight_number"]).upper()
            carrier = flight_number[:2]
            expires_at = now + OFFER_TTL
            offer_id = ""
            offer = FlightOffer(
                offer_id=offer_id,
                flight_number=flight_number,
                airline=AIRLINE_NAMES.get(carrier, flight.get("airline", "Unknown carrier")),
                origin=origin, destination=dest,
                departure=flight["departure"], arrival=flight["arrival"],
                duration_minutes=duration, wait_time_hours=wait_hours,
                stops=0, aircraft=flight.get("aircraft"),
                price_inr=None, seat_class="Not confirmed",
                provider_booking_url=AIRLINE_DIRECT_URLS.get(carrier),
                dgca_compensation_impact=(
                    "Schedule information only. Rebooking choice must be assessed separately against the passenger's facts and applicable DGCA clause."
                ),
                recommended=(idx == 0),
                data_source="airlabs_schedule",
                price_status="not_provided_by_schedule_provider",
                availability_status="schedule_only_not_seat_confirmed",
                expires_at=expires_at.isoformat(),
            )
            token_payload = {
                "typ": "schedule_offer",
                "iss": "flightguard-api",
                "sub": uuid.uuid4().hex,
                "iat": int(now.timestamp()),
                "exp": int(expires_at.timestamp()),
                "offer": offer.model_dump(exclude={"offer_id"}),
            }
            offer.offer_id = jwt.encode(token_payload, _offer_signing_key(), algorithm="HS256")
            offers.append(offer)
        except (KeyError, TypeError, ValueError) as exc:
            logger.warning("Skipping malformed schedule result: %s", type(exc).__name__)

    if offers:
        rights_note = (
            "These are schedule records returned by AirLabs, not bookable inventory. No seat, fare, ticket "
            "or rebooking is confirmed. Check the operating airline's official channel for live price and availability."
        )
    elif search_status == "provider_not_configured":
        rights_note = "Live alternative schedule lookup is not configured. No flight options have been fabricated."
    elif search_status == "provider_unavailable":
        rights_note = "The flight schedule provider could not be reached. No flight options have been fabricated; retry later."
    else:
        rights_note = "The schedule provider returned no matching alternatives for the requested route and time window."
    return RebookingComparisonResponse(
        origin=origin, destination=dest,
        disrupted_flight_number=req.disrupted_flight_number.upper(),
        offers_count=len(offers), offers=offers,
        passenger_rights_note=rights_note,
        search_status=search_status if offers else ("no_results" if search_status == "results_found" else search_status),
    )


def process_rebooking_selection(req: RebookingSelectRequest) -> RebookingHandoffResponse:
    try:
        claims = jwt.decode(
            req.selected_offer_id,
            _offer_signing_key(),
            algorithms=["HS256"],
            issuer="flightguard-api",
            options={"require": ["exp", "iat", "sub"]},
        )
    except jwt.PyJWTError as exc:
        raise ValueError("This schedule option is unknown or expired. Search again before continuing.") from exc

    if claims.get("typ") != "schedule_offer" or not isinstance(claims.get("offer"), dict):
        raise ValueError("This schedule option is invalid. Search again before continuing.")
    offer = claims["offer"]
    target_flight = offer["flight_number"]
    target_departure = offer["departure"]
    booking_url = offer.get("provider_booking_url")
    clause = "DGCA CAR Section 3, Series M, Part IV — verify the applicable clause for this passenger's circumstances"

    if not req.explicit_confirmation:
        return RebookingHandoffResponse(
            status="quote_ready", pnr=req.pnr.upper(), passenger_name=req.passenger_name,
            original_flight=req.disrupted_flight_number.upper(), target_flight=target_flight,
            target_departure=target_departure, statutory_clause=clause,
            voucher_id=None, booking_url=booking_url,
            agent_presentation_instructions=(
                "Schedule option selected. No live fare or seat availability was provided by the schedule source. "
                "Review the airline's official booking channel and confirm the actual fare and seat before purchase."
            ),
            confirmation_required=True,
        )

    # Explicit user consent only authorizes opening the airline channel. It does
    # not authorize this service to claim it has booked, ticketed or issued a voucher.
    return RebookingHandoffResponse(
        status="handoff_ready", pnr=req.pnr.upper(), passenger_name=req.passenger_name,
        original_flight=req.disrupted_flight_number.upper(), target_flight=target_flight,
        target_departure=target_departure, statutory_clause=clause,
        voucher_id=None, booking_url=booking_url,
        agent_presentation_instructions=(
            "Passenger confirmed they want to continue. Open the airline's official channel to verify current fare, "
            "seat availability and eligibility. This system has not booked or ticketed the flight and has not "
            "issued an airline voucher. Obtain airline confirmation before treating the rebooking as complete."
        ),
        confirmation_required=False,
    )
