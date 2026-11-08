"""Deterministic DGCA CAR Rev 4 rule engine.

The engine only evaluates facts that have been explicitly collected. It never
uses LLM guesses, generated flight schedules, or estimated block times to
calculate passenger entitlements.
"""

EXTRAORDINARY_REASONS = {
    "weather", "fog", "atc", "air_traffic_control", "security", "strike",
    "natural_disaster", "political_instability", "civil_war", "insurrection",
    "riot", "flood", "explosion", "government_order", "labor_dispute", "labour_dispute",
}


ORDINARY_REASONS = {
    "technical", "technical_issue", "technical_fault", "mechanical",
    "maintenance", "crew", "crew_shortage", "operational",
    "airline_operational", "airline_issue", "staff_shortage",
}

def normalize_reason(reason):
    if not reason:
        return None
    value = str(reason).strip().lower().replace("-", "_").replace(" ", "_")
    return value.removesuffix("_stated_unverified")


def is_extraordinary(reason):
    return normalize_reason(reason) in EXTRAORDINARY_REASONS


def is_known_reason(reason):
    value = normalize_reason(reason)
    return value in EXTRAORDINARY_REASONS or value in ORDINARY_REASONS


def _result(kind, clauses):
    return {
        "type": kind,
        "status": "ok",
        "missing_facts": [],
        "compensation": None,
        "refund": None,
        "meals": None,
        "hotel": None,
        "alt_or_refund": None,
        "clauses": list(clauses),
        "notes": [],
        "assumptions": [],
    }


def _needs_info(result, missing):
    result["status"] = "needs_more_info"
    result["missing_facts"] = list(dict.fromkeys(missing))
    return result


def _cannot_determine(result, note):
    result["status"] = "unable_to_determine"
    result["notes"].append(note)
    return result


def _minutes(hhmm):
    hours, minutes = hhmm.split(":")
    return int(hours) * 60 + int(minutes)


def _extraordinary_exemption(facts):
    """Return True/False/None (None means an apparent exception needs evidence).

    A documented finding can establish the broad 'other factors beyond control'
    limb even when the passenger-reported cause is not in the named examples.
    """
    established = facts.get("extraordinary_circumstances_established")
    if established is True:
        return True
    if is_extraordinary(facts.get("reason")):
        return established
    return False


# ---------- Cancellation (3.3) ----------
def evaluate_cancellation(f):
    r = _result("cancellation", ["3.3.1", "3.3.2", "3.3.3", "3.3.4", "3.3.5"])
    notice = f.get("notice_hours")
    if notice is None:
        return _needs_info(r, ["notice_hours"])

    # 3.3.1: notice at least two weeks, or less than two weeks but up to
    # 24 hours. The airline must also provide an alternate/refund acceptable
    # to the passenger. Notice alone does not prove that the remedy was provided.
    acceptable_option = None
    if notice >= 24:
        acceptable_option = f.get("acceptable_alternative_or_refund_provided")
        if not isinstance(acceptable_option, bool):
            return _needs_info(r, ["acceptable_alternative_or_refund_provided"])
        if notice == 24:
            r["assumptions"].append(
                "Exactly 24 hours is included in the 'up to 24 hours' window in 3.3.1."
            )
        if acceptable_option is True:
            r["compensation"] = 0
            r["alt_or_refund"] = True
            r["notes"].append(
                "The passenger confirms receiving an alternate flight or refund "
                "acceptable under 3.3.1; no 3.3.2 compensation is calculated."
            )
            return r

    # 3.3.3 removes financial compensation where adequate contact information
    # was not supplied, but does not remove refund/alternate obligations.
    if not isinstance(f.get("has_contact_info"), bool):
        return _needs_info(r, ["has_contact_info"])
    if f["has_contact_info"] is False:
        r["compensation"] = 0
        r["alt_or_refund"] = True
        r["clauses"] = ["3.3.2", "3.3.3", "3.3.5"]
        r["notes"].append(
            "No adequate email address or phone number was supplied at booking. "
            "Financial compensation is not payable under 3.3.3; refund or "
            "reasonable alternate arrangements remain applicable."
        )
        return r

    reason = normalize_reason(f.get("reason"))
    if reason is None:
        return _needs_info(r, ["reason"])
    if reason == "unknown" or not is_known_reason(reason):
        return _cannot_determine(
            r,
            "The airline has not supplied a recognized disruption reason. The engine will not assume the cause is ordinary or extraordinary; request the airline's written reason and supporting records.",
        )

    exemption = _extraordinary_exemption(f)
    if is_extraordinary(reason) and exemption is None:
        return _cannot_determine(
            r,
            "The airline-stated extraordinary cause has not been verified against the DGCA test. A passenger cannot establish this legal exception from personal knowledge alone; request the airline's supporting evidence before determining compensation.",
        )
    if exemption is True:
        r["compensation"] = 0
        r["alt_or_refund"] = True
        r["clauses"] = ["1.4", "1.5", "3.3.1", "3.3.2", "3.3.4", "3.3.5"]
        r["notes"].append(
            "The extraordinary-circumstances exception is treated as established "
            "based on the supplied evidence. It removes compensation, not the "
            "separate refund/alternate-flight obligations."
        )
        return r

    # A passenger only avoids the 3.3.2 compensation path when an acceptable
    # alternative was actually accepted. An offer alone is not acceptance.
    if notice < 24:
        offered = f.get("alternate_flight_offered")
        if not isinstance(offered, bool):
            return _needs_info(r, ["alternate_flight_offered"])
        accepted = f.get("alternate_flight_accepted")
        if not offered and accepted is True:
            return _cannot_determine(r, "The facts conflict: an alternate flight is marked as accepted but none was offered.")
        if offered and not isinstance(accepted, bool):
            return _needs_info(r, ["alternate_flight_accepted"])
        if accepted is True:
            r["compensation"] = 0
            r["alt_or_refund"] = True
            r["notes"].append("The passenger confirms accepting the alternate flight.")
            return r
    elif acceptable_option is False:
        r["notes"].append(
            "The passenger reports that no acceptable alternate flight or refund was provided "
            "within the 3.3.1 notice window. The 3.3.2 compensation path is evaluated."
        )

    required = ["block_time_minutes", "basic_fare", "fuel_charge"]
    missing = [key for key in required if f.get(key) is None]
    if missing:
        return _needs_info(r, missing)

    block = f["block_time_minutes"]
    cap = 5000 if block <= 60 else 7500 if block <= 120 else 10000
    r["compensation"] = min(cap, f["basic_fare"] + f["fuel_charge"])
    r["refund"] = "full_ticket_refund"
    r["alt_or_refund"] = True
    r["clauses"] = ["3.3.1", "3.3.2", "3.3.5"]
    r["notes"].append(
        "No acceptable alternate flight was accepted. The calculated amount is "
        "the lesser of the applicable cap and one-way basic fare plus airline "
        "fuel charge (taxes excluded), in addition to a full ticket refund."
    )
    if is_extraordinary(reason):
        r["assumptions"].append(
            "The airline's stated extraordinary-circumstances reason has not been "
            "established as meeting the full 1.4/1.5 test; the exemption was not applied."
        )
    else:
        r["assumptions"].append(
            "The reported cause is treated as an ordinary airline-related cause. "
            "A documented event may still qualify under the broader 1.4/1.5 test; "
            "the airline's evidence should be reviewed if disputed."
        )
    return r


# ---------- Denied boarding (3.2) ----------
def evaluate_denied_boarding(f):
    r = _result("denied_boarding", ["2.6", "3.2.1", "3.2.2", "3.2.3"])
    for key in ("confirmed_booking", "checked_in_on_time"):
        if f.get(key) is None:
            return _needs_info(r, [key])
    if not f["confirmed_booking"] or not f["checked_in_on_time"]:
        r["compensation"] = 0
        r["notes"].append(
            "The confirmed-booking and timely-presentation conditions in definition 2.6 are not met."
        )
        return r

    if f.get("voluntary_surrender") is None:
        return _needs_info(r, ["voluntary_surrender"])
    if f["voluntary_surrender"]:
        r["compensation"] = 0
        r["notes"].append(
            "The passenger voluntarily surrendered the seat. The involuntary denied-boarding "
            "compensation calculation in 3.2.2 does not apply; assess the airline's agreed benefits."
        )
        return r

    if f.get("overbooking") is None:
        return _needs_info(r, ["overbooking"])
    if not f["overbooking"]:
        return _cannot_determine(
            r,
            "The facts do not establish the overbooking condition in 3.2.1. "
            "This engine does not calculate a 3.2.2 amount for other refusal reasons.",
        )

    if f.get("connecting_same_ticket") is None:
        return _needs_info(r, ["connecting_same_ticket"])
    if f["connecting_same_ticket"]:
        final_delay = f.get("final_arrival_delay_minutes")
        if final_delay is None:
            return _needs_info(r, ["final_arrival_delay_minutes"])
        if final_delay < 180:
            r["compensation"] = 0
            r["notes"].append(
                "The same-ticket connecting passenger did not arrive at least three hours late; "
                "the additional condition in 3.2.3 is not met."
            )
            return r

    for key in ("basic_fare", "fuel_charge"):
        if f.get(key) is None:
            return _needs_info(r, [key])

    offered = f.get("alternate_flight_offered")
    if not isinstance(offered, bool):
        return _needs_info(r, ["alternate_flight_offered"])
    accepted = f.get("alternate_flight_accepted")
    if offered and not isinstance(accepted, bool):
        return _needs_info(r, ["alternate_flight_accepted"])
    if not offered and accepted is True:
        return _cannot_determine(r, "The facts conflict: an alternate flight is marked as accepted but none was offered.")

    base = f["basic_fare"] + f["fuel_charge"]
    if not offered or accepted is False:
        r["compensation"] = min(4.0 * base, 20000)
        r["refund"] = "full_ticket_refund"
        r["clauses"] = ["2.6", "3.2.1", "3.2.2(c)"]
        r["notes"].append(
            "No alternate flight was accepted. Clause 3.2.2(c) provides a full ticket "
            "refund plus 400% of one-way basic fare and airline fuel charge, capped at INR 20,000."
        )
        return r

    delay = f.get("alternate_departure_delay_minutes")
    if delay is None:
        return _needs_info(r, ["alternate_departure_delay_minutes"])
    if delay <= 60:
        r["compensation"] = 0
        r["notes"].append("The accepted alternate flight is scheduled within one hour (3.2.2).")
        return r
    if delay <= 24 * 60:
        r["compensation"] = min(2.0 * base, 10000)
        r["clauses"] = ["2.6", "3.2.1", "3.2.2(a)"]
        return r
    r["compensation"] = min(4.0 * base, 20000)
    r["clauses"] = ["2.6", "3.2.1", "3.2.2(b)"]
    return r


# ---------- Delay (3.4) ----------
def evaluate_delay(f):
    r = _result("delay", ["3.4.1", "3.4.2", "3.4.3", "3.4.4", "3.4.5", "3.8.1"])
    reason = normalize_reason(f.get("reason"))
    if reason and reason != "unknown":
        r["clauses"] += ["1.4", "1.5"]
    required = ["delay_minutes", "total_delay_from_published_minutes", "block_time_minutes", "checked_in_on_time", "scheduled_departure", "domestic"]
    missing = [key for key in required if f.get(key) is None]
    if missing:
        return _needs_info(r, missing)

    delay, block = f["delay_minutes"], f["block_time_minutes"]
    threshold = 120 if block <= 150 else 180 if block <= 300 else 240
    meals_due = bool(f["checked_in_on_time"] and delay >= threshold)

    scheduled = _minutes(f["scheduled_departure"])
    night_departure = scheduled >= 20 * 60 or scheduled <= 3 * 60
    total_delay = f["total_delay_from_published_minutes"]
    hotel_due = total_delay > 24 * 60 or (night_departure and total_delay > 360)

    alt_due = False
    if f["domestic"] and delay > 360:
        # delay_minutes is supplied as the applicable legal baseline by the
        # fact extractor; total_delay_from_published_minutes remains separate
        # for hotel eligibility.
        alt_due = True

    # A reason is only material when a threshold benefit may be due. For a
    # short delay with no meal/hotel/alternate entitlement, do not ask an
    # irrelevant question. Unknown causes never become ordinary by default.
    benefit_may_be_due = meals_due or hotel_due or alt_due
    if benefit_may_be_due and reason is None:
        return _needs_info(r, ["reason"])
    if benefit_may_be_due and (reason == "unknown" or not is_known_reason(reason)):
        return _cannot_determine(
            r,
            "The airline has not supplied a recognized disruption reason. The engine will not assume the cause is ordinary or extraordinary; request the airline's written reason and supporting records.",
        )

    exemption = _extraordinary_exemption(f)
    if benefit_may_be_due and is_extraordinary(reason) and exemption is None:
        return _cannot_determine(
            r,
            "The airline-stated extraordinary cause has not been verified against the DGCA test. A passenger cannot establish this legal exception from personal knowledge alone; request the airline's supporting evidence before determining facilities.",
        )

    exempt = exemption is True
    r["meals"] = bool(meals_due and not exempt)
    r["hotel"] = bool(hotel_due and not exempt)
    r["alt_or_refund"] = bool(alt_due)  # 3.4.4 exempts 3.8 facilities, not 3.4.2.

    if exempt:
        r["assumptions"].append(
            "The extraordinary-circumstances exemption was marked established from supplied evidence. "
            "It applies to 3.8 facilities; the separate 3.4.2 option is assessed independently."
        )
    elif is_extraordinary(reason):
        r["assumptions"].append(
            "The airline's stated extraordinary-circumstances reason was not established against "
            "the full 1.4/1.5 test, so the 3.4.4 exemption was not applied."
        )
    else:
        r["assumptions"].append(
            "The reported cause is treated as an ordinary airline-related cause. "
            "A documented event may still qualify under the broader 1.4/1.5 test; "
            "the airline's evidence should be reviewed if disputed."
        )
    if alt_due:
        r["notes"].append(
            "Domestic delay exceeds six hours. The passenger must be offered an alternate "
            "flight within six hours or a full refund under 3.4.2."
        )
    return r


# ---------- Downgrading (3.5) ----------
def evaluate_downgrade(f):
    r = _result("downgrading", ["3.5.1"])
    required = ["sector", "ticket_amount_including_taxes", "involuntary"]
    if f.get("sector") == "international":
        required.append("distance_km")
    missing = [key for key in required if f.get(key) is None]
    if missing:
        return _needs_info(r, missing)

    if not f["involuntary"]:
        r["compensation"] = 0
        r["notes"].append("The reimbursement rule in 3.5.1 applies to involuntary downgrading only.")
        return r

    amount = f["ticket_amount_including_taxes"]
    if f["sector"] == "domestic":
        percentage = 0.75
        r["clauses"] = ["3.5.1", "3.5.1(a)"]
    else:
        km = f["distance_km"]
        percentage = 0.30 if km <= 1500 else 0.50 if km <= 3500 else 0.75
        r["clauses"] = ["3.5.1", "3.5.1(b)"]
    r["compensation"] = round(amount * percentage, 2)
    return r


HANDLERS = {
    "cancellation": evaluate_cancellation,
    "denied_boarding": evaluate_denied_boarding,
    "delay": evaluate_delay,
    "downgrading": evaluate_downgrade,
}


def evaluate(facts):
    kind = facts.get("type")
    if kind not in HANDLERS:
        raise ValueError(f"Unsupported disruption type: {kind!r}")
    return HANDLERS[kind](facts)
