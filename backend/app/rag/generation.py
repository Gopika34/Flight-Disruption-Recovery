import json
import logging
import re
from app.llm.router import complete, stream_complete
from app.schemas.scenario import sanitize_facts
from app.loaders.prompt_loader import load_prompt

logger = logging.getLogger(__name__)


EXTRACT_PROMPT = load_prompt("fact_extraction.txt")
EXPLAIN_PROMPT = load_prompt("passenger_explanation.txt")

ALLOWED = {
    "type",
    "origin",
    "destination",
    "flight_number",
    "reason",
    "notice_hours",
    "has_contact_info",
    "block_time_minutes",
    "basic_fare",
    "fuel_charge",
    "delay_minutes",
    "total_delay_from_published_minutes",
    "checked_in_on_time",
    "scheduled_departure",
    "confirmed_booking",
    "alternate_departure_delay_minutes",
    "sector",
    "domestic",
    "ticket_amount_including_taxes",
    "involuntary",
    "distance_km",
    "alternate_flight_offered",
    "acceptable_alternative_or_refund_provided",
    "alternate_flight_accepted",
    "extraordinary_circumstances_established",
    "overbooking",
    "voluntary_surrender",
    "connecting_same_ticket",
    "final_arrival_delay_minutes",
    "revised_departure_communicated_more_than_24h",
}


def _json_from(text):
    text = (text or "").strip()

    # Remove optional Markdown code fences.
    text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s*```$", "", text)

    data = json.loads(text)

    if not isinstance(data, dict):
        raise ValueError("Expected a JSON object.")

    return data


def _nonempty(text):
    text = (text or "").strip()

    if not text:
        raise ValueError("Empty answer.")

    return text


def extract_facts(message, known=None):
    known = known or {}

    prompt = EXTRACT_PROMPT.format(
        known=json.dumps(known, default=str),
        message=message,
    )

    extracted = complete(
        prompt,
        json_mode=True,
        temperature=0,
        validate=_json_from,
    )

    # Ignore keys outside the supported fact schema.
    extracted = {
        key: value
        for key, value in extracted.items()
        if key in ALLOWED and value is not None
    }

    # Drop any value that fails the Scenario schema (e.g. notice_hours="unknown")
    # so one bad LLM value can't make the next /ask turn fail validation.
    extracted, rejected = sanitize_facts(extracted)
    if rejected:
        logger.warning("Discarded invalid extracted facts: %s", rejected)

    # Existing known facts remain available.
    # New explicitly extracted facts can update them.
    return {**known, **extracted}


def explanation_prompt(message, plan, clauses):
    slim = {
        "decision": plan["decision"],
        "alternatives": plan.get("alternatives", [])[:3],
        "stay": plan.get("stay"),
    }

    return EXPLAIN_PROMPT.format(
        message=message,
        plan=json.dumps(slim, default=str),
        clauses=json.dumps(clauses, default=str),
    )


def explain(message, plan, clauses):
    prompt = explanation_prompt(message, plan, clauses)

    return complete(
        prompt,
        temperature=0.2,
        validate=_nonempty,
    )


def stream_explain(message, plan, clauses):
    prompt = explanation_prompt(message, plan, clauses)

    return stream_complete(
        prompt,
        temperature=0.2,
    )
