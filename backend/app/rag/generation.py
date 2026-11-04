"""The 'G' in RAG: Gemini turns messy text into facts, and turns the engine's decision into a
plain-English answer. It never decides amounts: the rule engine does."""
import json
import re
from google import genai
from google.genai import types
from app.core.config import GEMINI_API_KEY, GEN_MODEL

_client = genai.Client(api_key=GEMINI_API_KEY)

ALLOWED = {
    "type", "origin", "destination", "flight_number", "reason", "notice_hours", "has_contact_info",
    "block_time_minutes", "basic_fare", "fuel_charge", "delay_minutes", "checked_in_on_time",
    "scheduled_departure", "confirmed_booking", "alternate_departure_delay_minutes",
    "sector", "ticket_amount_including_taxes", "involuntary", "distance_km",
}

EXTRACT_PROMPT = """You extract facts about an Indian domestic flight disruption from a passenger's message.
Return ONLY one JSON object. Use null for anything the passenger did not say. Never guess or invent.

Keys:
- type: "cancellation" | "delay" | "denied_boarding" | "downgrading"
- origin, destination: 3-letter IATA codes (Chennai MAA, Delhi DEL, Mumbai BOM, Bengaluru BLR, Hyderabad HYD, Kolkata CCU)
- flight_number: string like "6E201"
- reason: one of weather, fog, atc, security, strike, natural_disaster, technical, crew, operational, unknown
- notice_hours: number, how many hours BEFORE departure the passenger was told about a cancellation
- has_contact_info: true/false, whether the passenger had given the airline/agent contact details
- block_time_minutes: scheduled flight duration in minutes
- basic_fare, fuel_charge: numbers in INR (basic fare and fuel charge, NOT taxes)
- delay_minutes: number, total delay of departure
- checked_in_on_time: true/false
- scheduled_departure: "HH:MM" 24-hour
- confirmed_booking: true/false
- alternate_departure_delay_minutes: for denied boarding, delay of the replacement flight
- sector: "domestic" | "international"
- ticket_amount_including_taxes: number INR (for downgrading)
- involuntary: true/false (was the downgrade forced by the airline)
- distance_km: number

Facts already known (keep them unless the passenger corrects them): {known}
Passenger message: {message}"""

EXPLAIN_PROMPT = """You are an assistant explaining air-passenger rights under DGCA CAR Section 3 Series M Part IV.
Write a short, friendly answer for the passenger using ONLY the decision JSON and the clause texts below.
Rules:
- Never invent amounts or rules. Quote amounts exactly as they appear in the decision.
- Cite clause numbers in square brackets, like [3.4.1].
- Mention each assumption in plain words.
- Mention the alternative flights and hotel only if they are present in the decision data.
- Say the cause of disruption is the airline's stated reason when assumptions say so.
- End with: "This is guidance based on the CAR text, not legal advice."
- Max 180 words.

Passenger message: {message}
Decision and tools output: {plan}
Clause texts: {clauses}"""


def _json_from(text):
    text = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.MULTILINE).strip()
    return json.loads(text)


def extract_facts(message, known=None):
    known = known or {}
    prompt = EXTRACT_PROMPT.format(known=json.dumps(known), message=message)
    resp = _client.models.generate_content(
        model=GEN_MODEL, contents=prompt,
        config=types.GenerateContentConfig(response_mime_type="application/json", temperature=0))
    new = _json_from(resp.text)
    new = {k: v for k, v in new.items() if k in ALLOWED and v is not None}
    return {**known, **new}                         # newest answer wins, nothing known is lost


def explain(message, plan, clauses):
    slim = {"decision": plan["decision"], "alternatives": plan["alternatives"][:3], "stay": plan["stay"]}
    prompt = EXPLAIN_PROMPT.format(message=message,
                                   plan=json.dumps(slim, default=str),
                                   clauses=json.dumps(clauses))
    resp = _client.models.generate_content(
        model=GEN_MODEL, contents=prompt,
        config=types.GenerateContentConfig(temperature=0.2))
    return resp.text.strip()