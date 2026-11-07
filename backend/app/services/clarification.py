# app/services/clarification.py
"""Single source of truth for follow-up questions.

Keys MUST match the fact names used by the rule engine and the Scenario
schema. (main.py used to keep its own second copy; it now imports from here.)
"""

QUESTIONS = {
    "type": "What happened: was the flight cancelled, delayed, were you denied boarding, or downgraded?",
    "notice_hours": "How many hours before departure were you told about the cancellation?",
    "has_contact_info": "Had you given the airline or your travel agent your email address or phone number?",
    "reason": (
        "Do you know why the airline disrupted the flight? For example weather, "
        "a technical issue, or an operational issue. If the airline did not tell you, say so."
    ),
    "alternate_flight_offered": "Did the airline offer you an alternative flight? Please answer yes or no.",
    "acceptable_alternative_or_refund_provided": "Because you received at least 24 hours notice, did the airline actually provide either an alternative flight or a refund acceptable to you?",
    "alternate_flight_accepted": "Did you accept the alternative flight the airline offered?",
    "extraordinary_circumstances_established": (
        "Has documentary evidence established that the event was beyond the airline's control "
        "and could not have been avoided even if all reasonable measures had been taken?"
    ),
    "overbooking": "Were more passengers with confirmed bookings checked in than there were available seats?",
    "voluntary_surrender": "Did you voluntarily give up your seat, or did the airline refuse to board you against your will?",
    "connecting_same_ticket": "Was this flight part of a connecting journey on the same ticket?",
    "final_arrival_delay_minutes": "How many minutes late did you reach your final destination compared with the original itinerary?",
    "revised_departure_communicated_more_than_24h": (
        "Was the revised departure time communicated more than 24 hours before the original scheduled departure? "
        "For the delay figure, use that revised time as the baseline if yes."
    ),
    "block_time_minutes": "What was the scheduled duration of your flight, in minutes or hours?",
    "basic_fare": "What was your one-way basic fare in rupees, excluding taxes?",
    "fuel_charge": "What was the airline fuel charge in rupees, excluding taxes?",
    "confirmed_booking": "Did you have a confirmed booking for this flight?",
    "checked_in_on_time": "Did you report for check-in within the airline's required time?",
    "alternate_departure_delay_minutes": (
        "How many minutes after the original scheduled departure was the accepted replacement flight scheduled to depart?"
    ),
    "delay_minutes": "How many minutes is the flight delayed from the published schedule, or from the qualifying revised time if it was communicated more than 24 hours earlier?",
    "total_delay_from_published_minutes": "How many minutes is the total delay compared with the originally published departure time? This is needed separately for the hotel rule.",
    "scheduled_departure": "What was the scheduled departure time (HH:MM, 24-hour)?",
    "domestic": "Was this a domestic flight within India?",
    "sector": "Was the flight domestic or international?",
    "ticket_amount_including_taxes": "What was the total ticket amount, including taxes, in rupees?",
    "involuntary": "Was the downgrade imposed by the airline, rather than requested by you?",
    "distance_km": "What was the approximate route distance in kilometres?",
}


def questions_for(missing_fields):
    """Turn missing fact names into passenger-friendly questions."""
    return [
        QUESTIONS.get(field, f"Could you clarify {field.replace('_', ' ')}?")
        for field in dict.fromkeys(missing_fields)
    ]


def is_missing(value):
    if value is None:
        return True

    if isinstance(value, str):
        return value.strip().lower() in {
            "", "unknown", "unclear", "not sure", "not provided", "null", "none",
        }

    return False


def build_clarification(missing_fields, facts):
    missing_fields = list(dict.fromkeys(missing_fields))

    return {
        "status": "needs_more_info",
        "known_facts": facts,
        "missing_facts": missing_fields,
        "questions": questions_for(missing_fields),
    }
