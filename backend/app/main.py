import asyncio
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import CORS_ORIGINS
from app.rag.retriever import search_with_related
from app.rag import generation
from app.rules.rule_engine import evaluate
from app.schemas import Scenario, AskIn
from app.services.recovery import plan_recovery, enrich_facts

app = FastAPI(title="Flight Disruption Recovery Engine")
app.add_middleware(CORSMiddleware, allow_origins=CORS_ORIGINS, allow_methods=["*"], allow_headers=["*"])

QUESTIONS = {
    "type": "What happened: was the flight cancelled, delayed, or were you denied boarding?",
    "notice_hours": "How many hours before departure were you told about the cancellation?",
    "has_contact_info": "Had you given the airline or your travel agent your contact details?",
    "block_time_minutes": "How long is the scheduled flight (in minutes)? Or tell me the route.",
    "basic_fare": "What was the basic fare (without taxes) in rupees?",
    "fuel_charge": "What was the fuel charge on the ticket in rupees?",
    "delay_minutes": "How many minutes was the delay?",
    "checked_in_on_time": "Did you check in on time?",
    "scheduled_departure": "What was the scheduled departure time (HH:MM, 24-hour)?",
    "domestic": "Was it a domestic flight?",
    "confirmed_booking": "Did you have a confirmed booking?",
    "alternate_departure_delay_minutes": "How late was the replacement flight, in minutes?",
    "sector": "Was the flight domestic or international?",
    "ticket_amount_including_taxes": "What was the ticket amount including taxes?",
    "involuntary": "Was the downgrade forced by the airline?",
    "distance_km": "What is the route distance in km?",
}


def _questions(missing):
    return [QUESTIONS.get(m, f"Please tell me: {m}") for m in missing]


@app.get("/")
def health():
    return {"status": "running"}


@app.get("/search")
def search(q: str, k: int = 4):
    return {"query": q, "results": search_with_related(q, k)}


@app.post("/evaluate")
def evaluate_endpoint(s: Scenario):
    """Rules only: no LLM, no database. Facts in, decision out."""
    facts, notes = enrich_facts(s.facts())
    try:
        decision = evaluate(facts)
    except ValueError as e:
        raise HTTPException(422, str(e))
    decision["assumptions"] += notes
    return decision


@app.post("/recover")
def recover(s: Scenario):
    """Decision + alternative flights + hotel/cab + exact clause texts."""
    try:
        return plan_recovery(s.facts())
    except ValueError as e:
        raise HTTPException(422, str(e))


@app.post("/ask")
def ask(body: AskIn):
    """Natural language in, grounded answer out. Stateless: send back known_facts each turn."""
    try:
        facts = generation.extract_facts(body.message, body.known_facts)
    except Exception as e:
        raise HTTPException(502, f"Could not read the message (Gemini): {e}")

    if not facts.get("type"):
        return {"status": "needs_more_info", "known_facts": facts,
                "missing_facts": ["type"], "questions": _questions(["type"])}
    plan = plan_recovery(facts)
    if plan["decision"]["status"] == "needs_more_info":
        missing = plan["decision"]["missing_facts"]
        return {"status": "needs_more_info", "known_facts": facts,
                "missing_facts": missing, "questions": _questions(missing)}

    try:
        explanation = generation.explain(body.message, plan, plan["clauses"])
    except Exception as e:
        explanation = None                          # the plan is still valid without the prose
        plan["explanation_error"] = str(e)
    return {"status": "ok", "known_facts": facts, "explanation": explanation, **plan}


@app.websocket("/ws/simulate")
async def simulate(ws: WebSocket):
    """Real-time demo: send a Scenario as JSON, get the recovery plan pushed step by step."""
    await ws.accept()
    try:
        scenario = Scenario(**(await ws.receive_json()))
        await ws.send_json({"event": "disruption_detected", "data": scenario.facts()})
        await asyncio.sleep(0.8)
        plan = await asyncio.to_thread(plan_recovery, scenario.facts())
        await ws.send_json({"event": "rights_computed", "data": plan["decision"]})
        await asyncio.sleep(0.8)
        await ws.send_json({"event": "alternatives_found", "data": plan["alternatives"]})
        await asyncio.sleep(0.8)
        await ws.send_json({"event": "stay_arranged", "data": plan["stay"]})
        await asyncio.sleep(0.4)
        await ws.send_json({"event": "complete", "data": plan})
    except WebSocketDisconnect:
        return
    except Exception as e:
        await ws.send_json({"event": "error", "data": str(e)})
    finally:
        try:
            await ws.close()
        except Exception:
            pass