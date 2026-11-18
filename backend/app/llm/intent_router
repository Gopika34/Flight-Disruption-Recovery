"""Low-cost deterministic intent routing for FlightGuard.

This router does not make legal decisions. It only selects the safest
workflow; the Python rule engine remains the entitlement authority.
"""
from dataclasses import dataclass
import re

@dataclass(frozen=True)
class IntentRoute:
    intent: str
    destination: str
    reason: str


def classify_intent(message: str) -> IntentRoute:
    text = re.sub(r"\s+", " ", (message or "").lower()).strip()
    if re.search(r"\b(compensation|eligible|entitled|refund amount|how much.*(refund|compensation)|claim amount)\b", text):
        return IntentRoute("entitlement", "agent_with_rules", "Entitlement questions must use the deterministic rule engine.")
    if re.search(r"\b(status|where is|departure|arrival|running late)\b", text) and re.search(r"\b(?:[a-z]{1,3}\s?\d{2,4}|\d[a-z]\s?\d{2,4})\b", text):
        return IntentRoute("flight_status", "agent_with_flight_tool", "A flight identifier was detected; use the flight status tool.")
    if re.search(r"\b(alternative|another flight|rebook|rebooking|next flight)\b", text):
        return IntentRoute("rebooking", "agent_with_rebooking_tool", "The request concerns alternative flight schedules.")
    if re.search(r"\b(hotel|stay|accommodation|taxi|transport|stranded)\b", text):
        return IntentRoute("care", "agent_with_care_tool", "The request concerns accommodation or ground transport.")
    if re.search(r"\b(complaint|claim|grievance|draft.*(email|letter))\b", text):
        return IntentRoute("claims", "agent_with_claim_tool", "The request concerns claim preparation.")
    if re.search(r"\b(dgca|policy|rights|rule|regulation|cancellation|cancelled|delay|delayed|denied boarding|downgraded)\b", text):
        return IntentRoute("policy_or_disruption", "agent_with_rag", "The request needs policy-grounded assistance.")
    return IntentRoute("general_flight_help", "agent", "No specialized workflow was confidently identified.")
