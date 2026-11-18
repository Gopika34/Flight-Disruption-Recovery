from app.llm.intent_router import classify_intent

def test_entitlement_questions_route_to_rule_backed_agent():
    route = classify_intent("Am I eligible for compensation after cancellation?")
    assert route.intent == "entitlement"
    assert route.destination == "agent_with_rules"

def test_flight_status_requires_flight_identifier():
    route = classify_intent("Check status of 6E204")
    assert route.intent == "flight_status"

def test_general_message_falls_back_to_agent():
    route = classify_intent("Can you help me understand my travel options?")
    assert route.destination == "agent"
