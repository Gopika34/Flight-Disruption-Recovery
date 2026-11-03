"""Deterministic rule engine for DGCA CAR Section 3, Series M, Part IV (Rev 4).
No LLM and no database: facts in, decisions out."""

EXTRAORDINARY_REASONS = {
    "weather", "fog", "atc", "air_traffic_control", "security", "strike",
    "natural_disaster", "political_instability", "riot", "flood", "government_order",
}
STATED_REASON = ("The cause is the airline's stated reason and is not independently verified. "
                 "Weather, ATC and security are treated as extraordinary (1.4, 1.5); "
                 "technical faults are not (working assumption).")


def normalize_reason(reason):
    if not reason:
        return None
    return str(reason).lower().replace("_stated_unverified", "")


def is_extraordinary(reason):
    return normalize_reason(reason) in EXTRAORDINARY_REASONS


def _result(kind, clauses):
    return {"type": kind, "status": "ok", "missing_facts": [], "compensation": None,
            "meals": None, "hotel": None, "alt_or_refund": None,
            "clauses": list(clauses), "notes": [], "assumptions": []}


def _needs_info(result, missing):
    result["status"] = "needs_more_info"
    result["missing_facts"] = missing
    return result


def _to_minutes(hhmm):
    hours, minutes = hhmm.split(":")
    return int(hours) * 60 + int(minutes)


# ---------- Cancellation (3.3) ----------
def evaluate_cancellation(f):
    r = _result("cancellation", ["3.3.1", "3.3.2"])
    notice = f.get("notice_hours")
    if notice is None:
        return _needs_info(r, ["notice_hours"])

    if notice >= 24:
        r["compensation"] = 0
        r["clauses"] = ["3.3.1"]
        r["notes"].append("Informed 24 hours or more before departure: alternate flight or refund, "
                          "no cash compensation (3.3.1).")
        if notice == 24:
            r["assumptions"].append("Exactly 24 hours is read as inside 'up to 24 hours' (3.3.1).")
        return r

    if f.get("has_contact_info") is False:
        r["compensation"] = 0
        r["clauses"].append("3.3.3")
        r["notes"].append("No contact information given: no financial compensation (3.3.3). "
                          "Refund or reasonable alternate arrangements still apply.")
        return r

    if is_extraordinary(f.get("reason")):
        r["compensation"] = 0
        r["clauses"] += ["3.3.4", "1.4", "1.5", "3.3.5"]
        r["notes"].append("No compensation under the extraordinary-circumstances exception (3.3.4). "
                          "Refund and alternate-flight options are assessed separately (3.3.5).")
        r["assumptions"].append(STATED_REASON)
        return r

    required = ["has_contact_info", "block_time_minutes", "basic_fare", "fuel_charge"]
    missing = [k for k in required if f.get(k) is None]
    if missing:
        return _needs_info(r, missing)

    block = f["block_time_minutes"]
    cap = 5000 if block <= 60 else 7500 if block <= 120 else 10000
    r["compensation"] = min(cap, f["basic_fare"] + f["fuel_charge"])
    r["notes"].append("Compensation is the lesser of the cap and basic fare plus fuel charge (taxes excluded). "
                      "It is separate from the full refund or an acceptable alternate flight.")
    r["assumptions"].append("Assumes no acceptable alternate flight was provided (3.3.2).")
    return r


# ---------- Denied boarding (3.2) ----------
def evaluate_denied_boarding(f):
    r = _result("denied_boarding", ["2.6", "3.2.1", "3.2.2"])
    required = ["confirmed_booking", "checked_in_on_time", "alternate_departure_delay_minutes",
                "basic_fare", "fuel_charge"]
    missing = [k for k in required if f.get(k) is None]
    if missing:
        return _needs_info(r, missing)

    if not (f["confirmed_booking"] and f["checked_in_on_time"]):
        r["compensation"] = 0
        r["notes"].append("Denied boarding needs a confirmed booking and timely presentation (2.6).")
        return r

    delay = f["alternate_departure_delay_minutes"]
    base = f["basic_fare"] + f["fuel_charge"]
    if delay <= 60:
        r["compensation"] = 0
        r["notes"].append("Alternate flight within one hour: no compensation (3.2.2).")
        if delay == 60:
            r["assumptions"].append("Exactly 60 minutes is read as inside 'within one hour' (3.2.2).")
    elif delay <= 24 * 60:
        r["compensation"] = min(2.0 * base, 10000)
        r["clauses"].append("3.2.2(a)")
    else:
        r["compensation"] = min(4.0 * base, 20000)
        r["clauses"].append("3.2.2(b)")
    return r


# ---------- Delay (3.4) ----------
def evaluate_delay(f):
    r = _result("delay", ["3.4.1", "3.4.2", "3.4.3", "3.4.4", "3.8.1"])
    reason = normalize_reason(f.get("reason"))
    if reason and reason != "unknown":
        r["clauses"] += ["1.4", "1.5"]

    required = ["delay_minutes", "block_time_minutes", "checked_in_on_time",
                "scheduled_departure", "domestic"]
    missing = [k for k in required if f.get(k) is None]
    if missing:
        r["clauses"].append("3.4.5")
        return _needs_info(r, missing)

    delay, block = f["delay_minutes"], f["block_time_minutes"]
    threshold = 120 if block <= 150 else 180 if block <= 300 else 240      # 3.4.1
    meals_due = f["checked_in_on_time"] and delay >= threshold

    sched = _to_minutes(f["scheduled_departure"])
    night_departure = sched >= 20 * 60 or sched <= 3 * 60                  # 2000 to 0300
    hotel_due = delay > 24 * 60 or (night_departure and delay > 360)       # 3.4.3
    alt_due = bool(f["domestic"]) and delay > 360                          # 3.4.2

    exempt = is_extraordinary(f.get("reason"))                             # 3.4.4
    r["meals"] = bool(meals_due and not exempt)
    r["hotel"] = bool(hotel_due and not exempt)
    r["alt_or_refund"] = alt_due

    if exempt:
        r["assumptions"].append(STATED_REASON)
        if meals_due or hotel_due:
            r["notes"].append("Meals or hotel would apply, but 3.4.4 can exempt the airline for "
                              "extraordinary circumstances.")
    if alt_due:
        r["notes"].append("3.4.4 exempts only the 3.8 facilities, so the 3.4.2 alternate-or-refund "
                          "option is not treated as exempt (literal reading).")
    return r


# ---------- Downgrade (3.5) ----------
def evaluate_downgrade(f):
    r = _result("downgrading", ["3.5.1"])
    required = ["sector", "ticket_amount_including_taxes", "involuntary"]
    if f.get("sector") == "international":
        required.append("distance_km")
    missing = [k for k in required if f.get(k) is None]
    if missing:
        return _needs_info(r, missing)

    if not f["involuntary"]:
        r["compensation"] = 0
        r["notes"].append("The rule covers involuntary downgrading only (3.5.1).")
        return r

    amount = f["ticket_amount_including_taxes"]
    if f["sector"] == "domestic":
        pct = 0.75
        r["clauses"].append("3.5.1(a)")
    else:
        km = f["distance_km"]
        pct = 0.30 if km <= 1500 else 0.50 if km <= 3500 else 0.75
        r["clauses"].append("3.5.1(b)")
    r["compensation"] = round(amount * pct, 2)
    return r


HANDLERS = {
    "cancellation": evaluate_cancellation,
    "denied_boarding": evaluate_denied_boarding,
    "delay": evaluate_delay,
    "downgrading": evaluate_downgrade,
}


def evaluate(facts):
    kind = facts.get("type") or facts.get("disruption_type")
    handler = HANDLERS.get(kind)
    if handler is None:
        raise ValueError(f"Unsupported disruption type: {kind}")
    return handler(facts)