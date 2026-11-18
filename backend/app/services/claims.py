from app.schemas.capabilities import (
    AirlineContact,
    ClaimPackageRequest,
    ClaimPackageResponse,
    EvidenceItem,
    TimelineMilestone,
)
from app.rules.rule_engine import evaluate



class ClaimFactsIncomplete(ValueError):
    def __init__(self, status: str, missing_facts: list[str], notes: list[str] | None = None):
        self.status = status
        self.missing_facts = missing_facts
        self.notes = notes or []
        super().__init__(f"Claim cannot be prepared: {status}. Missing facts: {', '.join(missing_facts) or 'review required'}")

AIRLINE_REGISTRY: dict[str, AirlineContact] = {
    "6E": AirlineContact(
        airline_code="6E",
        airline_name="IndiGo",
        nodal_officer_email="nodalofficer@goindigo.in",
        appellate_authority_email="appellateauthority@goindigo.in",
        customer_support_phone="+91-124-6173838",
        portal_url="https://www.goindigo.in/customer-support.html",
    ),
    "AI": AirlineContact(
        airline_code="AI",
        airline_name="Air India",
        nodal_officer_email="nodal.officer@airindia.com",
        appellate_authority_email="appellate.authority@airindia.com",
        customer_support_phone="1860-233-1407",
        portal_url="https://www.airindia.com/feedback-and-grievance.html",
    ),
    "SG": AirlineContact(
        airline_code="SG",
        airline_name="SpiceJet",
        nodal_officer_email="nodalofficer@spicejet.com",
        appellate_authority_email="appellateauthority@spicejet.com",
        customer_support_phone="+91-124-4983410",
        portal_url="https://www.spicejet.com/contact-us",
    ),
    "QP": AirlineContact(
        airline_code="QP",
        airline_name="Akasa Air",
        nodal_officer_email="nodalofficer@akasaair.com",
        appellate_authority_email="appellateauthority@akasaair.com",
        customer_support_phone="+91-9606-112131",
        portal_url="https://www.akasaair.com/contact-us",
    ),
    "UK": AirlineContact(
        airline_code="UK",
        airline_name="Vistara (Air India)",
        nodal_officer_email="nodalofficer@airvistara.com",
        appellate_authority_email="appellateauthority@airvistara.com",
        customer_support_phone="+91-9289-228888",
        portal_url="https://www.airvistara.com/trip/customer-support",
    ),
}

DEFAULT_AIRLINE = AirlineContact(
    airline_code="GEN",
    airline_name="Operating Airline — verify carrier",
    nodal_officer_email="Not available — verify on the airline's official website",
    appellate_authority_email="Not available — verify on the airline's official website",
    customer_support_phone="Not available — verify on the airline's official website",
    portal_url="https://airsewa.gov.in",
)


def get_airline_contact(flight_number: str) -> AirlineContact:
    cleaned = flight_number.strip().upper()
    prefix = cleaned[:2] if len(cleaned) >= 2 else ""
    return AIRLINE_REGISTRY.get(prefix, DEFAULT_AIRLINE)


def generate_claim_timeline() -> list[TimelineMilestone]:
    return [
        TimelineMilestone(
            step=1,
            day_marker="Day 0",
            title="Airport Evidence & Written Endorsement",
            description=(
                "Collect physical delay/cancellation slip signed by airline staff, "
                "preserve boarding passes, baggage tags, and take photos of departure screens (FIDS)."
            ),
            authority="Airport Ground Services Desk",
            action_required="Demand written irregularity certificate before exiting terminal.",
        ),
        TimelineMilestone(
            step=2,
            day_marker="Day 1",
            title="Formal Grievance Submission to Nodal Officer",
            description=(
                "Submit formal statutory claim letter citing DGCA CAR Section 3, Series M, Part IV "
                "with booking reference (PNR), e-ticket, and payment bank account/UPI details."
            ),
            authority="Airline Nodal Officer (DGCA CAR Para 3.9)",
            action_required="Email the prepared grievance notice with evidence attached.",
        ),
        TimelineMilestone(
            step=3,
            day_marker="Day 30",
            title="Statutory Airline Redressal SLA",
            description=(
                "Under DGCA consumer grievance regulations, scheduled airlines are legally mandated "
                "to resolve passenger claims within 30 calendar days."
            ),
            authority="Operating Airline Appellate Registry",
            action_required="Verify bank account credit for compensation / refund.",
        ),
        TimelineMilestone(
            step=4,
            day_marker="Day 31+",
            title="Ministry of Civil Aviation AirSewa Escalation",
            description=(
                "If the airline fails to respond or wrongfully rejects statutory compensation, "
                "escalate directly to the AirSewa portal for binding regulatory investigation."
            ),
            authority="Ministry of Civil Aviation / DGCA Nodal Officer",
            action_required="File grievance at airsewa.gov.in quoting airline ticket and PNR.",
        ),
        TimelineMilestone(
            step=5,
            day_marker="Up to 2 Years",
            title="Consumer Disputes Redressal Commission (NCDRC)",
            description=(
                "Statutory limitation period under the Consumer Protection Act for deficiency of service, "
                "seeking full compensation plus damages for harassment."
            ),
            authority="District / State Consumer Disputes Redressal Commission",
            action_required="Submit claim on e-Daakhil portal if AirSewa resolution is unsatisfactory.",
        ),
    ]


def generate_evidence_checklist(disruption_type: str) -> list[EvidenceItem]:
    checklist = [
        EvidenceItem(
            id="ticket_pnr",
            title="Confirmed E-Ticket / PNR Booking Confirmation",
            description="Copy of confirmed booking showing passenger name, travel date, and fare breakup.",
            mandatory=True,
            tip="Preserve initial PDF booking confirmation from airline or travel agent.",
        ),
        EvidenceItem(
            id="boarding_pass",
            title="Original Boarding Pass",
            description="Paper boarding pass stub or digital Apple Wallet / PDF boarding pass.",
            mandatory=True,
            tip="Ensure barcode and seat assignment remain legible.",
        ),
        EvidenceItem(
            id="written_certificate",
            title="Written Airline Delay / Cancellation Certificate",
            description="Formal written slip or stamp endorsed by the airline duty manager at the airport.",
            mandatory=True,
            tip="If airline staff refuses, note duty manager name and counter number.",
        ),
        EvidenceItem(
            id="fids_screen_photo",
            title="Terminal Flight Information Display Screen (FIDS) Photo",
            description="Timestamped photograph of airport departure screen showing delayed/cancelled status.",
            mandatory=False,
            tip="Capture photo with airport terminal clock visible in the frame.",
        ),
        EvidenceItem(
            id="airline_notifications",
            title="Airline SMS, WhatsApp, and Email Irregularity Alerts",
            description="Official digital notices sent by the airline revising departure or cancelling flight.",
            mandatory=True,
            tip="Take full-screen screenshots displaying sender ID and timestamp.",
        ),
        EvidenceItem(
            id="out_of_pocket_bills",
            title="Itemized Out-of-Pocket Expense Invoices (Meals, Water, Taxi, Hotel)",
            description="Original tax invoices for meals, local transport, or emergency lodging necessitated by the disruption.",
            mandatory=False,
            tip="Ensure bills have GST numbers and date/time stamps matching disruption period.",
        ),
    ]

    if disruption_type == "denied_boarding":
        checklist.append(
            EvidenceItem(
                id="checkin_reporting_proof",
                title="Proof of On-Time Reporting at Airport Counter / Gate",
                description="Evidence that passenger reported prior to check-in closure with valid travel documents.",
                mandatory=True,
                tip="Check-in kiosk slip, security stamp, or airport CCTV timestamp reference.",
            )
        )
    return checklist


def build_claim_package(req: ClaimPackageRequest) -> ClaimPackageResponse:
    """Build a claim only after the deterministic engine has a complete decision.

    Legal entitlements are never delegated to an LLM. Passenger bank/payment
    details are deliberately excluded from generated text and model prompts.
    """
    facts = dict(req.scenario_facts)
    if not facts.get("type"):
        raise ClaimFactsIncomplete("needs_more_info", ["type"])
    facts.setdefault("flight_number", req.flight_number.upper())

    decision = evaluate(facts)
    status = decision.get("status")
    if status != "ok":
        raise ClaimFactsIncomplete(
            status or "unable_to_determine",
            list(decision.get("missing_facts") or []),
            list(decision.get("notes") or []),
        )

    airline = get_airline_contact(req.flight_number)
    timeline = generate_claim_timeline()
    disruption_type = decision.get("type", facts["type"])
    checklist = generate_evidence_checklist(disruption_type)

    # A zero is used only when the rule engine explicitly returns status=ok
    # and a null/zero compensation value. Incomplete decisions are rejected above.
    raw_compensation = decision.get("compensation")
    comp_amt = float(raw_compensation) if raw_compensation is not None else None
    comp_display = f"INR {comp_amt:,.2f}" if comp_amt is not None else "no statutory compensation amount was calculated by the rule engine"
    refund_status = (
        "100% Full Ticket Refund Mandated"
        if decision.get("refund") == "full_ticket_refund"
        else "No full-ticket refund determined by the supplied facts"
    )

    care_parts = []
    if decision.get("meals"):
        care_parts.append("Meals and refreshments")
    if decision.get("hotel"):
        care_parts.append("Hotel accommodation and transfers")
    care_status = ", ".join(care_parts) if care_parts else "No additional duty-of-care entitlement determined"

    clauses = decision.get("clauses") or ["CAR Section 3 Series M Part IV"]
    clause_str = ", ".join(clauses)
    origin = str(facts.get("origin") or "[Origin]")
    destination = str(facts.get("destination") or "[Destination]")
    expenses = float(req.out_of_pocket_expenses_inr or 0.0)

    # Deterministic notice: an LLM must not alter legal amounts, facts or claims.
    notice_text = (
        "FORMAL PASSENGER GRIEVANCE — DRAFT FOR REVIEW\n"
        "DGCA CAR Section 3, Series M, Part IV\n\n"
        f"To: Nodal Officer, {airline.airline_name} ({airline.nodal_officer_email})\n"
        f"Subject: Flight disruption grievance — PNR {req.pnr.upper()}, flight {req.flight_number.upper()}\n\n"
        "Dear Sir/Madam,\n\n"
        f"I, {req.passenger_name}, booked on flight {req.flight_number.upper()} under PNR {req.pnr.upper()}, "
        f"was affected by a {disruption_type.replace('_', ' ')} on the route {origin} to {destination}.\n\n"
        f"Based on the facts currently supplied, the deterministic assessment records {comp_display}. "
        f"The applicable provisions identified by the assessment are: {clause_str}. "
        f"Refund assessment: {refund_status}. Duty-of-care assessment: {care_status}.\n\n"
        f"Documented out-of-pocket expenses supplied: INR {expenses:,.2f}. This figure is a passenger-reported "
        "expense amount and is not represented as an automatically approved reimbursement. Please review the "
        "attached ticket, payment proof, disruption notice and supporting receipts, and provide a written response "
        "with the basis of your decision.\n\n"
        "This is a draft for passenger review. Please verify every factual detail and the applicable policy text "
        "before submission.\n\n"
        f"Sincerely,\n{req.passenger_name}\nPNR: {req.pnr.upper()}\nFlight: {req.flight_number.upper()}"
    )

    escalation_instructions = (
        f"1. Review this draft and correct any inaccurate passenger or flight details.\n"
        f"2. Submit it through {airline.airline_name}'s official grievance channel: {airline.portal_url}.\n"
        f"3. Attach your e-ticket, boarding pass, airline disruption communication and relevant receipts.\n"
        "4. Retain the grievance reference and escalate through the applicable official channel if unresolved."
    )

    return ClaimPackageResponse(
        pnr=req.pnr.upper(),
        disruption_type=disruption_type,
        statutory_compensation_inr=comp_amt,
        refund_status=refund_status,
        care_status=care_status,
        airline=airline,
        timeline=timeline,
        evidence_checklist=checklist,
        formal_grievance_notice=notice_text,
        escalation_instructions=escalation_instructions,
    )
