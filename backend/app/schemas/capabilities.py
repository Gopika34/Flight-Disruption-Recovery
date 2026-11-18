from datetime import datetime, timezone
from typing import Any, Literal
from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# 1. Conversational Messages & Session
# ---------------------------------------------------------------------------

class ChatMessage(BaseModel):
    model_config = ConfigDict(extra="allow")

    role: Literal["user", "assistant", "system", "tool"]
    content: str = Field(default="", max_length=10000)
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    name: str | None = None
    tool_call_id: str | None = None
    tool_calls: list[dict[str, Any]] | None = None


class ConversationSession(BaseModel):
    session_id: str
    messages: list[ChatMessage] = Field(default_factory=list)
    facts: dict[str, Any] = Field(default_factory=dict)
    active_capability: str | None = None
    updated_at: str | None = None


# ---------------------------------------------------------------------------
# 2. Passenger Claim Package Models
# ---------------------------------------------------------------------------

class EvidenceItem(BaseModel):
    id: str
    title: str
    description: str
    mandatory: bool
    collected: bool = False
    tip: str


class TimelineMilestone(BaseModel):
    step: int
    day_marker: str
    title: str
    description: str
    authority: str
    action_required: str


class AirlineContact(BaseModel):
    airline_code: str
    airline_name: str
    nodal_officer_email: str
    appellate_authority_email: str
    customer_support_phone: str
    portal_url: str


class ClaimPackageRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    session_id: str | None = None
    passenger_name: str = Field(default="Passenger", min_length=2, max_length=100)
    passenger_email: str | None = None
    passenger_phone: str | None = None
    pnr: str = Field(min_length=4, max_length=12)
    flight_number: str = Field(min_length=2, max_length=15)
    bank_details_or_upi: str | None = None
    out_of_pocket_expenses_inr: float | None = Field(default=0.0, ge=0)
    scenario_facts: dict[str, Any] = Field(default_factory=dict)


class ClaimPackageResponse(BaseModel):
    pnr: str
    disruption_type: str
    statutory_compensation_inr: float | None = None
    refund_status: str
    care_status: str
    airline: AirlineContact
    timeline: list[TimelineMilestone]
    evidence_checklist: list[EvidenceItem]
    formal_grievance_notice: str
    escalation_instructions: str


# ---------------------------------------------------------------------------
# 3. Alternative Flight Rebooking Models
# ---------------------------------------------------------------------------

class FlightOffer(BaseModel):
    offer_id: str
    flight_number: str
    airline: str
    origin: str
    destination: str
    departure: str
    arrival: str
    duration_minutes: int
    wait_time_hours: float
    stops: int = 0
    aircraft: str | None = None
    price_inr: int | None = None
    seat_class: str = "Economy"
    provider_booking_url: str | None = None
    dgca_compensation_impact: str
    recommended: bool = False
    data_source: str = "unknown"
    price_status: str = "unknown"
    availability_status: str = "unverified"
    expires_at: str | None = None


class RebookingSearchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    origin: str = Field(min_length=3, max_length=3)
    destination: str = Field(min_length=3, max_length=3)
    disrupted_flight_number: str
    departure_date: str | None = None
    max_wait_hours: float | None = Field(default=24.0, ge=1.0, le=72.0)
    disruption_type: str = "cancellation"


class RebookingComparisonResponse(BaseModel):
    origin: str
    destination: str
    disrupted_flight_number: str
    offers_count: int
    offers: list[FlightOffer]
    passenger_rights_note: str
    search_status: Literal["results_found", "no_results", "provider_not_configured", "provider_unavailable"] = "no_results"


class RebookingSelectRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    pnr: str
    passenger_name: str
    selected_offer_id: str
    disrupted_flight_number: str
    explicit_confirmation: bool = False


class RebookingHandoffResponse(BaseModel):
    status: Literal["quote_ready", "confirmed", "handoff_ready"]
    pnr: str
    passenger_name: str
    original_flight: str
    target_flight: str
    target_departure: str
    statutory_clause: str
    voucher_id: str | None = None
    booking_url: str | None = None
    agent_presentation_instructions: str
    confirmation_required: bool = False


# ---------------------------------------------------------------------------
# 4. Emergency Stay & Transport Models
# ---------------------------------------------------------------------------

class HotelOffer(BaseModel):
    id: str
    name: str
    tier: Literal["Budget Stay", "Comfort Suites", "Grand Residency"]
    distance_km: float
    estimated_transit_minutes: int
    price_per_night_inr: int
    free_airport_shuttle: bool
    address: str
    phone: str
    booking_url: str | None = None
    # Kept for backwards compatibility; directory data must never claim live availability.
    verified_available: bool = False
    availability_status: str = "unverified"
    listing_source: str = "curated_directory"
    price_status: str = "estimated_not_live"
    contact_status: str = "directory_reference_verify"
    shuttle_status: str = "unverified_listing_detail"


class TransportOption(BaseModel):
    mode: str
    estimated_fare_inr: int
    estimated_duration_minutes: int
    pickup_point: str
    booking_link_or_instructions: str
    fare_status: str = "estimated_not_live"
    availability_status: str = "not_checked"


class EmergencyStayRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    airport_code: str = Field(min_length=3, max_length=3)
    delay_hours: float = Field(ge=0)
    is_overnight: bool = False
    delay_start_local_time: str | None = Field(default=None, pattern=r"^(?:[01]\d|2[0-3]):[0-5]\d$")
    passenger_count: int = Field(default=1, ge=1, le=9)
    airline_name: str | None = None


class EmergencyDutyOfCareResponse(BaseModel):
    airport_code: str
    hotel_directory_status: str = "curated_directory_unverified"
    duty_of_care_mandated: bool
    statutory_clause: str
    airline_liability_statement: str
    hotels: list[HotelOffer]
    transport: list[TransportOption]
    counter_demand_script: str
    self_booking_claim_template: str
