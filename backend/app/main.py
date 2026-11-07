# import json

# from fastapi.responses import StreamingResponse

# import asyncio
# import logging

# from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
# from fastapi.middleware.cors import CORSMiddleware
# from pydantic import ValidationError

# from app.core.config import CORS_ORIGINS
# from app.rag.retriever import search_with_related
# from app.rag import generation
# from app.rules.rule_engine import evaluate
# from app.schemas.scenario import Scenario, AskIn
# from app.services.recovery import plan_recovery, enrich_facts
# from app.llm.router import provider_status
# from app.services.clarification import build_clarification

# logger = logging.getLogger(__name__)

# app = FastAPI(
#     title="Flight Disruption Recovery Engine",
#     description=(
#         "AI-assisted flight disruption recovery using "
#         "DGCA policy retrieval and deterministic rule evaluation."
#     ),
#     version="1.0.0",
# )

# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=CORS_ORIGINS,
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )


# QUESTIONS = {
#     "type": "What happened: was the flight cancelled, delayed, or were you denied boarding?",
#     "notice_hours": "How many hours before departure were you told about the cancellation?",
#     "has_contact_info": "Had you given the airline or your travel agent your contact details?",
#     "block_time_minutes": "How long is the scheduled flight in minutes? Or tell me the route.",
#     "basic_fare": "What was the basic fare (without taxes) in rupees?",
#     "fuel_charge": "What was the fuel charge on the ticket in rupees?",
#     "delay_minutes": "How many minutes was the delay?",
#     "checked_in_on_time": "Did you check in on time?",
#     "scheduled_departure": "What was the scheduled departure time (HH:MM, 24-hour)?",
#     "domestic": "Was it a domestic flight?",
#     "confirmed_booking": "Did you have a confirmed booking?",
#     "alternate_departure_delay_minutes": "How late was the replacement flight, in minutes?",
#     "sector": "Was the flight domestic or international?",
#     "ticket_amount_including_taxes": "What was the ticket amount including taxes?",
#     "involuntary": "Was the downgrade forced by the airline?",
#     "distance_km": "What is the route distance in km?",
# }

# QUESTIONS.update({
#     "reason": (
#         "Do you know why the airline cancelled the flight? "
#         "For example, weather, technical issue, operational issue, "
#         "or something else? If the airline did not tell you, say so."
#     ),
#     "alternate_flight_offered": (
#         "Did the airline offer you an acceptable alternative flight? "
#         "Please answer yes or no."
#     ),
#     "domestic": "Was this a domestic flight within India?",
# })


# def _questions(missing):
#     return [
#         QUESTIONS.get(field, f"Please tell me: {field}")
#         for field in missing
#     ]


# # --------------------------------------------------
# # ROOT / HEALTH
# # --------------------------------------------------

# @app.get("/", tags=["Health"])
# def health():
#     return {
#         "status": "running",
#         "service": "Flight Disruption Recovery Engine",
#     }


# # --------------------------------------------------
# # LLM PROVIDER STATUS
# # --------------------------------------------------

# @app.get("/llm/status", tags=["LLM"])
# def llm_status():
#     status = provider_status()

#     return {
#         "status": (
#             "configured"
#             if status["provider_count"] > 0
#             else "not_configured"
#         ),
#         **status,
#     }


# # --------------------------------------------------
# # RAG POLICY SEARCH
# # --------------------------------------------------

# @app.get("/search", tags=["RAG"])
# def search(q: str, k: int = 4):
#     if not q.strip():
#         raise HTTPException(
#             status_code=400,
#             detail="Search query cannot be empty.",
#         )

#     try:
#         results = search_with_related(q, k)

#         return {
#             "query": q,
#             "count": len(results),
#             "results": results,
#         }

#     except ValueError as error:
#         raise HTTPException(
#             status_code=422,
#             detail=str(error),
#         )

#     except Exception:
#         logger.exception("Policy search failed")

#         raise HTTPException(
#             status_code=503,
#             detail="Policy retrieval is currently unavailable.",
#         )


# # --------------------------------------------------
# # DETERMINISTIC RULE EVALUATION
# # --------------------------------------------------

# @app.post("/evaluate", tags=["Recovery"])
# def evaluate_endpoint(scenario: Scenario):
#     """
#     Evaluate passenger facts using Python rules only.

#     No LLM generation is required.
#     """

#     facts, notes = enrich_facts(scenario.facts())

#     try:
#         decision = evaluate(facts)

#     except ValueError as error:
#         raise HTTPException(
#             status_code=422,
#             detail=str(error),
#         )

#     decision["assumptions"] += notes

#     return decision


# # --------------------------------------------------
# # COMPLETE RECOVERY PLAN
# # --------------------------------------------------

# @app.post("/recover", tags=["Recovery"])
# def recover(scenario: Scenario):
#     """
#     Generate a recovery plan containing:
#     - Passenger rights
#     - Compensation decision
#     - Alternative flights
#     - Hotel and cab information
#     - Supporting policy clauses
#     """

#     try:
#         return plan_recovery(scenario.facts())

#     except ValueError as error:
#         raise HTTPException(
#             status_code=422,
#             detail=str(error),
#         )

#     except Exception:
#         logger.exception("Recovery planning failed")

#         raise HTTPException(
#             status_code=500,
#             detail="Could not generate the recovery plan.",
#         )


# # --------------------------------------------------
# # NATURAL LANGUAGE PASSENGER INTERFACE
# # --------------------------------------------------

# @app.post("/ask", tags=["AI Assistant"])
# def ask(body: AskIn):
#     """
#     Passenger message -> fact extraction -> rule engine
#     -> policy-grounded explanation.
    
#     Stateless: send known_facts back with every subsequent turn.
#     """

#     # 1. Extract facts using the central LLM router.
#     try:
#         facts = generation.extract_facts(
#             body.message,
#             body.known_facts,
#         )

#     except Exception:
#         logger.exception("Passenger fact extraction failed")

#         raise HTTPException(
#             status_code=502,
#             detail={
#                 "error": "llm_service_unavailable",
#                 "message": (
#                     "All configured language models failed "
#                     "to extract passenger information."
#                 ),
#             },
#         )

#     # 2. Check whether the disruption type is known.
#     if not facts.get("type"):
#         missing = ["type"]

#         return {
#             "status": "needs_more_info",
#             "known_facts": facts,
#             "missing_facts": missing,
#             "questions": _questions(missing),
#         }

#     # 3. Calculate recovery decision using Python rules.
#     try:
#         plan = plan_recovery(facts)

#     except ValueError as error:
#         raise HTTPException(
#             status_code=422,
#             detail=str(error),
#         )

#     except Exception:
#         logger.exception("Passenger recovery calculation failed")

#         raise HTTPException(
#             status_code=500,
#             detail="Could not calculate the recovery decision.",
#         )

#     # 4. Ask for missing facts before generating explanation.
    
#     decision = plan["decision"]

#     if decision["status"] == "needs_more_info":
#         missing = decision["missing_facts"]

#         return {
#             "status": "needs_more_info",
#             "known_facts": facts,
#             "missing_facts": missing,
#             "questions": _questions(missing),
#         }

#     if decision["status"] != "ok":
#         return {
#             "status": decision["status"],
#             "known_facts": facts,
#             "decision": decision,
#             "message": (
#                 "I cannot reliably determine your eligibility "
#                 "with the information currently available."
#             ),
#         }


#     # 5. Explain the deterministic decision using the LLM router.
#     try:
#         explanation = generation.explain(
#             body.message,
#             plan,
#             plan["clauses"],
#         )

#     except Exception:
#         logger.exception("LLM explanation generation failed")

#         explanation = None

#         plan["explanation_error"] = (
#             "The recovery decision was generated, "
#             "but the language model explanation is unavailable."
#         )

#     # 6. Return final response.
#     return {
#         "status": "ok",
#         "known_facts": facts,
#         "explanation": explanation,
#         **plan,
#     }

# # Continue with your existing structured response.

#     # 6. Return result
#     return {
#         "status": "ok",
#         "known_facts": facts,
#         "explanation": explanation,
#         "decision": decision,
#         "alternatives": plan.get("alternatives", []),
#         "stay": plan.get("stay"),
#         "clauses": plan.get("clauses", []),
#     }
# # --------------------------------------------------
# # STREAMING NATURAL LANGUAGE PASSENGER INTERFACE
# # --------------------------------------------------

# def _sse_event(event_name, data):
#     """
#     Format one Server-Sent Event.
#     """
#     payload = json.dumps(data, default=str)

#     return (
#         f"event: {event_name}\n"
#         f"data: {payload}\n\n"
#     )


# def _next_stream_item(iterator):
#     """
#     Safely get the next synchronous generator item
#     from an async endpoint.
#     """
#     try:
#         return next(iterator)
#     except StopIteration:
#         return None


# @app.post("/ask/stream", tags=["AI Assistant"])
# async def ask_stream(body: AskIn):
#     """
#     Stream:
#     1. Processing status
#     2. Extracted facts
#     3. Missing questions, if needed
#     4. Recovery decision
#     5. Alternatives and clauses
#     6. LLM explanation chunks
#     """

#     async def generate_events():

#         try:
#             # 1. Extraction started
#             yield _sse_event("status", {
#                 "stage": "extracting_facts",
#                 "message": "Understanding your flight disruption."
#             })

#             # Fact extraction uses the existing central router.
#             facts = await asyncio.to_thread(
#                 generation.extract_facts,
#                 body.message,
#                 body.known_facts,
#             )

#             # 2. Send facts immediately
#             yield _sse_event("facts", {
#                 "known_facts": facts,
#             })

#             # 3. Check disruption type
#             if not facts.get("type"):

#                 missing = ["type"]

#                 yield _sse_event("questions", {
#                     "missing_facts": missing,
#                     "questions": _questions(missing),
#                 })

#                 yield _sse_event("done", {
#                     "status": "needs_more_info",
#                 })

#                 return

#             # 4. Calculate recovery plan
#             yield _sse_event("status", {
#                 "stage": "calculating_recovery",
#                 "message": "Calculating your passenger rights."
#             })

#             plan = await asyncio.to_thread(
#                 plan_recovery,
#                 facts,
#             )

#             decision = plan["decision"]

#             # 5. Check for missing required facts
#             if decision["status"] == "needs_more_info":

#                 missing = decision["missing_facts"]

#                 yield _sse_event("decision", decision)

#                 yield _sse_event("questions", {
#                     "missing_facts": missing,
#                     "questions": _questions(missing),
#                 })

#                 yield _sse_event("done", {
#                     "status": "needs_more_info",
#                 })

#                 return
            
#             if decision["status"] != "ok":
#                 yield _sse_event("decision", decision)

#                 yield _sse_event("done", {
#                     "status": decision["status"],
#                     "known_facts": facts,
#                 })

#                 return

#             # 6. Send structured recovery information
#             yield _sse_event("decision", decision)

#             yield _sse_event("alternatives", {
#                 "items": plan.get("alternatives", []),
#             })

#             yield _sse_event("stay", {
#                 "data": plan.get("stay"),
#             })

#             yield _sse_event("clauses", {
#                 "items": plan.get("clauses", []),
#             })

#             # 7. Start explanation streaming
#             yield _sse_event("status", {
#                 "stage": "generating_explanation",
#                 "message": "Preparing your explanation."
#             })

#             chunks = generation.stream_explain(
#                 body.message,
#                 plan,
#                 plan["clauses"],
#             )

#             # The provider generator is synchronous.
#             # Run each next() call in a worker thread.
#             while True:

#                 chunk = await asyncio.to_thread(
#                     _next_stream_item,
#                     chunks,
#                 )

#                 if chunk is None:
#                     break

#                 yield _sse_event("answer_chunk", {
#                     "text": chunk,
#                 })

#             # 8. Finished
#             yield _sse_event("done", {
#                 "status": "ok",
#                 "known_facts": facts,
#             })

#         except Exception:
#             logger.exception("Streaming passenger request failed")

#             yield _sse_event("error", {
#                 "message": (
#                     "The request could not be completed. "
#                     "Please try again."
#                 )
#             })

#     return StreamingResponse(
#         generate_events(),
#         media_type="text/event-stream",
#         headers={
#             "Cache-Control": "no-cache",
#             "Connection": "keep-alive",
#             "X-Accel-Buffering": "no",
#         },
#     )

# # --------------------------------------------------
# # WEBSOCKET RECOVERY SIMULATION
# # --------------------------------------------------

# @app.websocket("/ws/simulate")
# async def simulate(ws: WebSocket):
#     """
#     Real-time recovery simulation.

#     Sends events:
#     1. disruption_detected
#     2. rights_computed
#     3. alternatives_found
#     4. stay_arranged
#     5. complete
#     """

#     await ws.accept()

#     try:
#         payload = await ws.receive_json()

#         scenario = Scenario(**payload)

#         facts = scenario.facts()

#         await ws.send_json({
#             "event": "disruption_detected",
#             "data": facts,
#         })

#         await asyncio.sleep(0.5)

#         plan = await asyncio.to_thread(
#             plan_recovery,
#             facts,
#         )

#         await ws.send_json({
#             "event": "rights_computed",
#             "data": plan["decision"],
#         })

#         await asyncio.sleep(0.5)

#         await ws.send_json({
#             "event": "alternatives_found",
#             "data": plan["alternatives"],
#         })

#         await asyncio.sleep(0.5)

#         await ws.send_json({
#             "event": "stay_arranged",
#             "data": plan["stay"],
#         })

#         await asyncio.sleep(0.3)

#         await ws.send_json({
#             "event": "complete",
#             "data": plan,
#         })

#     except WebSocketDisconnect:
#         logger.info("WebSocket client disconnected")

#     except (ValidationError, ValueError) as error:
#         await ws.send_json({
#             "event": "error",
#             "data": str(error),
#         })

#     except Exception:
#         logger.exception("WebSocket simulation failed")

#         try:
#             await ws.send_json({
#                 "event": "error",
#                 "data": "Recovery simulation failed.",
#             })
#         except Exception:
#             pass

#     finally:
#         try:
#             await ws.close()
#         except Exception:
#             pass
import asyncio
import json
import logging
import time
from uuid import uuid4
from collections import defaultdict, deque
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Query, Request, Response, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import ValidationError

from app.core.config import (
    CORS_ORIGINS,
    ENABLE_DOCS,
    GEMINI_API_KEY,
    AIRLABS_API_KEY,
    RATE_LIMIT_PER_MINUTE,
    validate_production_config,
)
from app.rag.retriever import (
    close_client,
    db_available,
    search_with_related,
    vector_index_status,
)
from app.rag import generation
from app.rules.rule_engine import evaluate
from app.schemas.scenario import Scenario, AskIn
from app.services.recovery import plan_recovery, enrich_facts
from app.services.flights import FlightDataError, get_flight_status
from app.llm.router import provider_status
from app.services.clarification import questions_for
from app.services.sessions import load_facts, save_facts, close_session_cache

if not logging.getLogger().handlers:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_app):
    validate_production_config()      # refuses to start with unsafe production settings
    yield
    close_session_cache()
    close_client()


app = FastAPI(
    lifespan=lifespan,
    docs_url="/docs" if ENABLE_DOCS else None,
    redoc_url="/redoc" if ENABLE_DOCS else None,
    openapi_url="/openapi.json" if ENABLE_DOCS else None,

    title="Flight Disruption Recovery Engine",
    description=(
        "AI-assisted flight disruption recovery using "
        "DGCA policy retrieval and deterministic rule evaluation."
    ),
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=False,          # the API uses no cookies
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type"],
)


# --------------------------------------------------
# RATE LIMITING (per client IP, in memory, per worker)
# --------------------------------------------------

_hits = defaultdict(deque)


def rate_limit(request: Request):
    """Protect the expensive endpoints (LLM + vector search)."""
    if RATE_LIMIT_PER_MINUTE <= 0:
        return

    forwarded = request.headers.get("x-forwarded-for", "")
    ip = forwarded.split(",")[0].strip() or (request.client.host if request.client else "unknown")

    now = time.monotonic()
    window = _hits[ip]
    while window and now - window[0] > 60:
        window.popleft()

    if len(window) >= RATE_LIMIT_PER_MINUTE:
        raise HTTPException(
            status_code=429,
            detail="Too many requests. Please wait a minute and try again.",
            headers={"Retry-After": "60"},
        )

    window.append(now)

    if len(_hits) > 10000:            # keep memory bounded
        for key in [k for k, v in _hits.items() if not v]:
            del _hits[key]


# --------------------------------------------------
# ROOT / HEALTH
# --------------------------------------------------

@app.get("/", tags=["Health"])
def root():
    return {
        "status": "running",
        "service": "Flight Disruption Recovery Engine",
    }


@app.get("/health/live", tags=["Health"])
def health_live():
    """Is the process up? Never touches external services."""
    return {"status": "alive"}


@app.get("/health/ready", tags=["Health"])
def health_ready(response: Response):
    """Can this instance serve policy-grounded requests?

    LLM availability is deliberately NOT required: /evaluate works without it.
    """
    checks = {
        "gemini_key_configured": bool(GEMINI_API_KEY),
        "airlabs_key_configured": bool(AIRLABS_API_KEY),
        "database": "ok" if db_available() else "unavailable",
    }
    checks["vector_index"] = (
        vector_index_status() if checks["database"] == "ok" else "unavailable"
    )

    ready = (
        checks["gemini_key_configured"]
        and checks["database"] == "ok"
        and checks["vector_index"] == "ready"
        and checks["airlabs_key_configured"]
    )
    if not ready:
        response.status_code = 503

    return {"status": "ready" if ready else "not_ready", "checks": checks}


# --------------------------------------------------
# LLM PROVIDER STATUS (sanitized: no raw errors)
# --------------------------------------------------

@app.get("/llm/status", tags=["LLM"])
def llm_status():
    status = provider_status()   # public view

    return {
        "status": "configured" if status["provider_count"] > 0 else "not_configured",
        **status,
    }


# --------------------------------------------------
# RAG POLICY SEARCH
# --------------------------------------------------

@app.get("/search", tags=["RAG"], dependencies=[Depends(rate_limit)])
def search(
    q: str = Query(min_length=2, max_length=300),
    k: int = Query(default=4, ge=1, le=20),
):
    if not q.strip():
        raise HTTPException(
            status_code=400,
            detail="Search query cannot be empty.",
        )

    try:
        results = search_with_related(q, k)

        return {
            "query": q,
            "count": len(results),
            "results": results,
        }

    except ValueError as error:
        raise HTTPException(
            status_code=422,
            detail=str(error),
        )

    except Exception:
        logger.exception("Policy search failed")

        raise HTTPException(
            status_code=503,
            detail="Policy retrieval is currently unavailable.",
        )


# --------------------------------------------------
# LIVE FLIGHT STATUS (AirLabs)
# --------------------------------------------------

@app.get("/flights/{flight_number}", tags=["Flights"], dependencies=[Depends(rate_limit)])
def flight_status(flight_number: str):
    """Return the closest live/scheduled flight record for an IATA flight number."""
    try:
        result = get_flight_status(flight_number)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error))
    except FlightDataError as error:
        raise HTTPException(status_code=503, detail=str(error))
    if result is None:
        raise HTTPException(status_code=404, detail="No matching flight was returned by AirLabs.")
    return result


# --------------------------------------------------
# DETERMINISTIC RULE EVALUATION
# --------------------------------------------------

@app.post("/evaluate", tags=["Recovery"])
def evaluate_endpoint(scenario: Scenario):
    """
    Evaluate passenger facts using Python rules only.

    No LLM generation is required.
    """

    facts, notes = enrich_facts(scenario.facts())

    try:
        decision = evaluate(facts)

    except ValueError as error:
        raise HTTPException(
            status_code=422,
            detail=str(error),
        )

    decision["assumptions"] += notes

    return decision


# --------------------------------------------------
# COMPLETE RECOVERY PLAN
# --------------------------------------------------

@app.post("/recover", tags=["Recovery"], dependencies=[Depends(rate_limit)])
def recover(scenario: Scenario):
    """
    Generate a recovery plan containing:
    - Passenger rights
    - Compensation decision
    - Alternative flights
    - Hotel and cab information
    - Supporting policy clauses
    """

    try:
        return plan_recovery(scenario.facts())

    except ValueError as error:
        raise HTTPException(
            status_code=422,
            detail=str(error),
        )

    except Exception:
        logger.exception("Recovery planning failed")

        raise HTTPException(
            status_code=500,
            detail="Could not generate the recovery plan.",
        )


# --------------------------------------------------
# NATURAL LANGUAGE PASSENGER INTERFACE
# --------------------------------------------------

@app.post("/ask", tags=["AI Assistant"], dependencies=[Depends(rate_limit)])
def ask(body: AskIn):
    """
    Passenger message -> fact extraction -> rule engine
    -> policy-grounded explanation.
    
    MongoDB-backed: session_id loads and saves facts between turns.
    """

    # 1. Load saved facts, then let the caller's supplied facts take precedence
    # so a passenger can explicitly correct an earlier answer.
    session_id = body.session_id or str(uuid4())
    try:
        saved_facts = load_facts(session_id)
        prior_facts = {**saved_facts, **body.known_facts}
        facts = generation.extract_facts(body.message, prior_facts)
        save_facts(session_id, facts)
    except RuntimeError:
        logger.exception("Passenger session storage failed")
        raise HTTPException(status_code=503, detail="Conversation storage is temporarily unavailable. Please retry.")

    except Exception:
        logger.exception("Passenger fact extraction failed")

        raise HTTPException(
            status_code=502,
            detail={
                "error": "llm_service_unavailable",
                "message": (
                    "All configured language models failed "
                    "to extract passenger information."
                ),
            },
        )

    # 2. Check whether the disruption type is known.
    if not facts.get("type"):
        missing = ["type"]

        return {
            "status": "needs_more_info",
            "session_id": session_id,
            "known_facts": facts,
            "missing_facts": missing,
            "questions": questions_for(missing),
        }

    # 3. Calculate recovery decision using Python rules.
    try:
        plan = plan_recovery(facts)

    except ValueError as error:
        raise HTTPException(
            status_code=422,
            detail=str(error),
        )

    except Exception:
        logger.exception("Passenger recovery calculation failed")

        raise HTTPException(
            status_code=500,
            detail="Could not calculate the recovery decision.",
        )

    # 4. Ask for missing facts before generating explanation.
    
    decision = plan["decision"]

    if decision["status"] == "needs_more_info":
        missing = decision["missing_facts"]

        return {
            "status": "needs_more_info",
            "session_id": session_id,
            "known_facts": facts,
            "missing_facts": missing,
            "questions": questions_for(missing),
        }

    if decision["status"] != "ok":
        return {
            "status": decision["status"],
            "session_id": session_id,
            "known_facts": facts,
            "decision": decision,
            "message": (
                "I cannot reliably determine your eligibility "
                "with the information currently available."
            ),
        }


    # 5. Explain the deterministic decision using the LLM router,
    #    but only claim a policy-grounded explanation if the clause
    #    text was actually retrieved.
    evidence = plan.get("evidence", {})
    explanation = None

    if evidence.get("status") == "unavailable":
        plan["evidence_warning"] = (
            "The calculation below is complete, but the supporting policy text "
            "could not be retrieved right now, so no policy-grounded explanation "
            "is provided."
        )
    else:
        try:
            explanation = generation.explain(
                body.message,
                plan,
                plan["clauses"],
            )

        except Exception:
            logger.exception("LLM explanation generation failed")

            plan["explanation_error"] = (
                "The recovery decision was generated, "
                "but the language model explanation is unavailable."
            )

        if evidence.get("status") == "partial":
            plan["evidence_warning"] = (
                "Some cited policy clauses could not be found, so the explanation "
                "covers only the clauses that were retrieved."
            )

    # 6. Return final response.
    return {
        "status": "ok",
        "session_id": session_id,
        "known_facts": facts,
        "explanation": explanation,
        "policy_grounded": evidence.get("status") == "ok" and explanation is not None,
        **plan,
    }


# --------------------------------------------------
# STREAMING NATURAL LANGUAGE PASSENGER INTERFACE
# --------------------------------------------------

def _sse_event(event_name, data):
    """
    Format one Server-Sent Event.
    """
    payload = json.dumps(data, default=str)

    return (
        f"event: {event_name}\n"
        f"data: {payload}\n\n"
    )


def _next_stream_item(iterator):
    """
    Safely get the next synchronous generator item
    from an async endpoint.
    """
    try:
        return next(iterator)
    except StopIteration:
        return None


@app.post("/ask/stream", tags=["AI Assistant"], dependencies=[Depends(rate_limit)])
async def ask_stream(body: AskIn):
    """
    Stream:
    1. Processing status
    2. Extracted facts
    3. Missing questions, if needed
    4. Recovery decision
    5. Alternatives and clauses
    6. LLM explanation chunks
    """

    async def generate_events():

        try:
            session_id = body.session_id or str(uuid4())
            saved_facts = await asyncio.to_thread(load_facts, session_id)
            prior_facts = {**saved_facts, **body.known_facts}
            yield _sse_event("session", {"session_id": session_id})

            # 1. Extraction started
            yield _sse_event("status", {
                "stage": "extracting_facts",
                "message": "Understanding your flight disruption."
            })

            # Fact extraction uses the existing central router.
            facts = await asyncio.to_thread(
                generation.extract_facts,
                body.message,
                prior_facts,
            )
            await asyncio.to_thread(save_facts, session_id, facts)

            # 2. Send facts immediately
            yield _sse_event("facts", {
                "session_id": session_id,
                "known_facts": facts,
            })

            # 3. Check disruption type
            if not facts.get("type"):

                missing = ["type"]

                yield _sse_event("questions", {
                    "missing_facts": missing,
                    "questions": questions_for(missing),
                })

                yield _sse_event("done", {
                    "session_id": session_id,
                    "status": "needs_more_info",
                })

                return

            # 4. Calculate recovery plan
            yield _sse_event("status", {
                "stage": "calculating_recovery",
                "message": "Calculating your passenger rights."
            })

            plan = await asyncio.to_thread(
                plan_recovery,
                facts,
            )

            decision = plan["decision"]

            # 5. Check for missing required facts
            if decision["status"] == "needs_more_info":

                missing = decision["missing_facts"]

                yield _sse_event("decision", decision)

                yield _sse_event("questions", {
                    "missing_facts": missing,
                    "questions": questions_for(missing),
                })

                yield _sse_event("done", {
                    "session_id": session_id,
                    "status": "needs_more_info",
                })

                return
            
            if decision["status"] != "ok":
                yield _sse_event("decision", decision)

                yield _sse_event("done", {
                    "session_id": session_id,
                    "status": decision["status"],
                    "known_facts": facts,
                })

                return

            # 6. Send structured recovery information
            yield _sse_event("decision", decision)

            yield _sse_event("alternatives", {
                "items": plan.get("alternatives", []),
            })

            yield _sse_event("stay", {
                "data": plan.get("stay"),
            })

            yield _sse_event("clauses", {
                "items": plan.get("clauses", []),
            })

            # Do not present an explanation as policy-grounded
            # when the clause text could not be retrieved.
            if plan.get("evidence", {}).get("status") == "unavailable":
                yield _sse_event("warning", {
                    "message": (
                        "The calculation is complete, but the supporting policy "
                        "text is unavailable, so no policy-grounded explanation "
                        "is provided."
                    ),
                })
                yield _sse_event("done", {
                    "session_id": session_id,
                    "status": "ok",
                    "known_facts": facts,
                    "policy_grounded": False,
                })
                return

            # 7. Start explanation streaming
            yield _sse_event("status", {
                "stage": "generating_explanation",
                "message": "Preparing your explanation."
            })

            chunks = generation.stream_explain(
                body.message,
                plan,
                plan["clauses"],
            )

            # The provider generator is synchronous.
            # Run each next() call in a worker thread.
            while True:

                chunk = await asyncio.to_thread(
                    _next_stream_item,
                    chunks,
                )

                if chunk is None:
                    break

                yield _sse_event("answer_chunk", {
                    "text": chunk,
                })

            # 8. Finished
            yield _sse_event("done", {
                "session_id": session_id,
                "status": "ok",
                "known_facts": facts,
                "policy_grounded": plan["evidence"]["status"] == "ok",
            })

        except Exception:
            logger.exception("Streaming passenger request failed")

            yield _sse_event("error", {
                "message": (
                    "The request could not be completed. "
                    "Please try again."
                )
            })

    return StreamingResponse(
        generate_events(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )

# --------------------------------------------------
# WEBSOCKET RECOVERY SIMULATION
# --------------------------------------------------

@app.websocket("/ws/simulate")
async def simulate(ws: WebSocket):
    """
    Real-time recovery simulation.

    Sends events:
    1. disruption_detected
    2. rights_computed
    3. alternatives_found
    4. stay_arranged
    5. complete
    """

    await ws.accept()

    try:
        payload = await ws.receive_json()

        scenario = Scenario(**payload)

        facts = scenario.facts()

        await ws.send_json({
            "event": "disruption_detected",
            "data": facts,
        })

        await asyncio.sleep(0.5)

        plan = await asyncio.to_thread(
            plan_recovery,
            facts,
        )

        await ws.send_json({
            "event": "rights_computed",
            "data": plan["decision"],
        })

        await asyncio.sleep(0.5)

        await ws.send_json({
            "event": "alternatives_found",
            "data": plan["alternatives"],
        })

        await asyncio.sleep(0.5)

        await ws.send_json({
            "event": "stay_arranged",
            "data": plan["stay"],
        })

        await asyncio.sleep(0.3)

        await ws.send_json({
            "event": "complete",
            "data": plan,
        })

    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected")

    except (ValidationError, ValueError) as error:
        await ws.send_json({
            "event": "error",
            "data": str(error),
        })

    except Exception:
        logger.exception("WebSocket simulation failed")

        try:
            await ws.send_json({
                "event": "error",
                "data": "Recovery simulation failed.",
            })
        except Exception:
            pass

    finally:
        try:
            await ws.close()
        except Exception:
            pass