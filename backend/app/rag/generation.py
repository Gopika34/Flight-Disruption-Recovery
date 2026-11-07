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


class FactTypeConflict(Exception):
    """Raised when a new message appears to contradict the saved disruption type."""

    def __init__(self, previous_type, proposed_type):
        self.previous_type = previous_type
        self.proposed_type = proposed_type
        super().__init__(
            f"Conflicting disruption types: {previous_type} and {proposed_type}"
        )


def _json_from(text):
    text = (text or "").strip()

    text = re.sub(
        r"^```(?:json)?\s*",
        "",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(r"\s*```$", "", text)

    data = json.loads(text)

    if not isinstance(data, dict):
        raise ValueError("Expected a JSON object.")

    return data


def _is_explicit_correction(message):
    """Allow a passenger to deliberately correct an earlier answer."""
    text = (message or "").lower()

    correction_phrases = (
        "actually",
        "i meant",
        "i mean",
        "correction",
        "to correct",
        "i was mistaken",
        "that was incorrect",
        "change it to",
        "it was not",
        "it wasn't",
        "instead it was",
    )

    return any(phrase in text for phrase in correction_phrases)


def extract_facts(message, known=None):
    """
    Extract facts from one passenger message.

    Existing facts are retained. New valid facts can update old values.
    A conflicting disruption type requires an explicit correction.
    """
    known = dict(known or {})

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

    if not isinstance(extracted, dict):
        raise ValueError("Fact extractor did not return a JSON object.")

    extracted = {
        key: value
        for key, value in extracted.items()
        if key in ALLOWED and value is not None
    }

    extracted, rejected = sanitize_facts(extracted)

    if rejected:
        logger.warning("Discarded invalid extracted facts: %s", rejected)

    old_type = known.get("type")
    new_type = extracted.get("type")

    if (
        old_type
        and new_type
        and old_type != new_type
        and not _is_explicit_correction(message)
    ):
        raise FactTypeConflict(old_type, new_type)

    return {**known, **extracted}


def build_explanation(plan):
    """
    Build a safe explanation from the deterministic recovery plan.

    No LLM call. No new legal conclusions or compensation amounts.
    """
    decision = plan.get("decision", {})
    status = decision.get("status", "unknown")

    if status != "ok":
        return (
            "The recovery engine could not complete the evaluation. "
            "Please review the missing information or the decision details."
        )

    parts = [
        "Your flight disruption details have been evaluated by the "
        "deterministic recovery rules."
    ]

    clauses = plan.get("clauses") or []
    clause_ids = [
        str(item.get("clause_id"))
        for item in clauses
        if item.get("clause_id")
    ]

    if clause_ids:
        parts.append(
            "The supporting DGCA policy references retrieved for this "
            "evaluation are: " + ", ".join(clause_ids) + "."
        )

    evidence_status = plan.get("evidence", {}).get("status")

    if evidence_status == "unavailable":
        parts.append(
            "The policy database was unavailable, so the supporting policy "
            "text could not be retrieved. Please treat the result as "
            "provisional until the evidence is available."
        )
    elif evidence_status == "partial":
        parts.append(
            "Some policy references could not be retrieved. Review the "
            "available evidence before relying on this result."
        )

    alternatives = plan.get("alternatives") or []

    if alternatives:
        parts.append(
            f"{len(alternatives)} alternative scheduled flight(s) were "
            "returned by the live flight data provider. These are schedules, "
            "not confirmed seat reservations."
        )
    else:
        flight_status = plan.get("flight_data", {}).get("status")

        if flight_status == "live_data":
            parts.append(
                "No matching alternative schedules were returned in the "
                "provider's available search window. This does not prove "
                "that no alternatives exist."
            )
        elif flight_status == "unavailable":
            parts.append(
                "Live alternative flight data is temporarily unavailable."
            )
        elif flight_status == "not_configured":
            parts.append(
                "Live alternative flight search is not configured."
            )

    stay = plan.get("stay")

    if stay:
        parts.append(
            "Accommodation information is included in the recovery plan. "
            "Live hotel inventory is not currently integrated."
        )

    parts.append(
        "Review the decision, assumptions, missing evidence and policy "
        "references before taking action with the airline."
    )

    return " ".join(parts)

def explanation_prompt(message, plan):
    """
    Prepare a limited, trusted context for the passenger-facing LLM.

    The LLM explains the deterministic decision.
    It does not calculate or modify passenger rights.
    """

    decision = plan.get("decision", {})

    context = {
        "decision": decision,
        "assumptions": decision.get("assumptions", []),
        "notes": decision.get("notes", []),
        "evidence_status": plan.get("evidence", {}).get("status"),
    }

    clauses = plan.get("clauses", []) or []
    alternatives = plan.get("alternatives", []) or []

    return EXPLAIN_PROMPT.format(
        message=message,
        decision=json.dumps(context, ensure_ascii=False, default=str),
        clauses=json.dumps(clauses, ensure_ascii=False, default=str),
        alternatives=json.dumps(
            alternatives[:3],
            ensure_ascii=False,
            default=str,
        ),
        stay=json.dumps(
            plan.get("stay"),
            ensure_ascii=False,
            default=str,
        ),
        evidence=json.dumps(
            plan.get("evidence", {}),
            ensure_ascii=False,
            default=str,
        ),
    )


def stream_explain(message, plan):
    """
    Stream a passenger-facing explanation.

    All compensation and eligibility decisions come from Python.
    """

    prompt = explanation_prompt(message, plan)

    yield from stream_complete(
        prompt,
        temperature=0.2,
    )