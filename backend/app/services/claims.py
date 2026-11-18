import logging
from typing import Any
from app.schemas.capabilities import (
    AirlineContact,
    ClaimPackageRequest,
    ClaimPackageResponse,
    EvidenceItem,
    TimelineMilestone,
)
from app.rules.rule_engine import evaluate
from app.llm.router import complete
from app.loaders.prompt_loader import load_prompt

logger = logging.getLogger(__name__)

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
    airline_name="Commercial Airline",
    nodal_officer_email="nodal.officer@airline.com",
    appellate_authority_email="appellate.authority@airline.com",
    customer_support_phone="1800-AIRLINE",
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
    facts = dict(req.scenario_facts)
    if "type" not in facts:
        facts["type"] = "cancellation"

    # Evaluate deterministically
    decision = evaluate(facts)
    airline = get_airline_contact(req.flight_number)
    timeline = generate_claim_timeline()
    checklist = generate_evidence_checklist(decision.get("type", "cancellation"))

    comp_amt = float(decision.get("compensation") or 0.0)
    refund_status = (
        "100% Full Ticket Refund Mandated"
        if decision.get("refund") == "full_ticket_refund"
        else "Standard Applicable Refund"
    )

    care_parts = []
    if decision.get("meals"):
        care_parts.append("Mandatory Meals & Refreshments")
    if decision.get("hotel"):
        care_parts.append("Mandatory Overnight Hotel & Taxi Transfers")
    care_status = ", ".join(care_parts) if care_parts else "Statutory Duty-of-Care"

    # Generate formal legal notice via prompt template
    clauses = decision.get("clauses") or ["CAR Section 3 Series M Part IV"]
    clause_str = ", ".join(clauses)

    prompt = load_prompt("claim_package.txt").format(
        passenger_name=req.passenger_name,
        pnr=req.pnr.upper(),
        flight_number=req.flight_number.upper(),
        origin=facts.get("origin", "Origin Airport"),
        destination=facts.get("destination", "Destination Airport"),
        disruption_type=decision.get("type", "flight disruption"),
        expenses_inr=req.out_of_pocket_expenses_inr or 0.0,
        payment_details=req.bank_details_or_upi or "Direct Bank Transfer (NEFT) / UPI to registered account",
        compensation_inr=comp_amt,
        refund_entitlement=refund_status,
        care_entitlement=care_status,
        clauses=clause_str,
        airline_name=airline.airline_name,
        nodal_email=airline.nodal_officer_email,
        appellate_email=airline.appellate_authority_email,
    )

    try:
        notice_text = complete(prompt, temperature=0.2)
    except Exception as exc:
        logger.warning("LLM claim notice drafting fallback triggered: %s", exc)
        notice_text = (
            f"FORMAL STATUTORY GRIEVANCE NOTICE\n"
            f"Issued under DGCA CAR Section 3, Series M, Part IV\n\n"
            f"To,\n"
            f"The Nodal Officer,\n"
            f"{airline.airline_name} ({airline.nodal_officer_email})\n\n"
            f"Sub: Legal Demand for Statutory Compensation of INR {comp_amt:,.2f} "
            f"and Refund/Expense Settlement (PNR: {req.pnr.upper()})\n\n"
            f"Dear Sir/Madam,\n\n"
            f"I was scheduled to travel on flight {req.flight_number.upper()} under PNR {req.pnr.upper()}, "
            f"which was subjected to {decision.get('type')}. "
            f"Pursuant to DGCA CAR Section 3, Series M, Part IV (specifically {clause_str}), "
            f"I hereby demand the immediate settlement of my statutory entitlement of INR {comp_amt:,.2f}.\n\n"
            f"Furthermore, in accordance with DGCA grievance redressal regulations, {airline.airline_name} "
            f"is mandated to resolve this claim within 30 calendar days. Failure to remit this statutory compensation "
            f"will necessitate escalation to the Ministry of Civil Aviation AirSewa portal (airsewa.gov.in) "
            f"and the competent Consumer Disputes Redressal Commission.\n\n"
            f"Sincerely,\n"
            f"{req.passenger_name}\n"
            f"PNR: {req.pnr.upper()}\n"
            f"Flight: {req.flight_number.upper()}"
        )

    escalation_instructions = (
        f"1. Email this notice to {airline.airline_name}'s Nodal Officer at {airline.nodal_officer_email}.\n"
        f"2. Attach copies of your boarding pass, e-ticket, and written delay certificate.\n"
        f"3. Mark your calendar for Day 30. If unresolved, escalate with your grievance token to AirSewa (airsewa.gov.in)."
    )

    return ClaimPackageResponse(
        pnr=req.pnr.upper(),
        disruption_type=decision.get("type", "cancellation"),
        statutory_compensation_inr=comp_amt,
        refund_status=refund_status,
        care_status=care_status,
        airline=airline,
        timeline=timeline,
        evidence_checklist=checklist,
        formal_grievance_notice=notice_text,
        escalation_instructions=escalation_instructions,
    )
