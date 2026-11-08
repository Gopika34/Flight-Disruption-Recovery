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
    TRUSTED_PROXY_COUNT,
    IS_PRODUCTION,
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

# httpx logs every request URL at INFO, and AirLabs needs api_key in the query
# string. Keep these loggers quiet so the key never reaches the logs.
for _noisy in ("httpx", "httpcore"):
    logging.getLogger(_noisy).setLevel(logging.WARNING)
    
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

_hits: dict[str, deque] = {}
_last_sweep = 0.0
_WINDOW_S = 60
_MAX_TRACKED_IPS = 10000


def client_ip(conn) -> str:
    """Real client address for a Request or WebSocket.

    X-Forwarded-For is client-controlled on its left side, so it is only read
    when TRUSTED_PROXY_COUNT > 0, and then we take the hop appended by OUR
    outermost proxy (counted from the right), never the first value.
    """
    peer = conn.client.host if conn.client else "unknown"
    if TRUSTED_PROXY_COUNT <= 0:
        return peer
    hops = [h.strip() for h in conn.headers.get("x-forwarded-for", "").split(",") if h.strip()]
    if len(hops) >= TRUSTED_PROXY_COUNT:
        return hops[-TRUSTED_PROXY_COUNT]
    return peer


def _sweep(now):
    """Drop idle IPs so memory stays bounded."""
    global _last_sweep
    if now - _last_sweep < _WINDOW_S and len(_hits) <= _MAX_TRACKED_IPS:
        return
    _last_sweep = now
    for key in [k for k, v in _hits.items() if not v or now - v[-1] > _WINDOW_S]:
        del _hits[key]


def allow_request(ip: str) -> bool:
    if RATE_LIMIT_PER_MINUTE <= 0:
        return True
    now = time.monotonic()
    _sweep(now)
    window = _hits.setdefault(ip, deque())
    while window and now - window[0] > _WINDOW_S:
        window.popleft()
    if len(window) >= RATE_LIMIT_PER_MINUTE:
        return False
    window.append(now)
    return True


def rate_limit(request: Request):
    """Protect the expensive endpoints (LLM + vector search + AirLabs)."""
    if not allow_request(client_ip(request)):
        raise HTTPException(
            status_code=429,
            detail="Too many requests. Please wait a minute and try again.",
            headers={"Retry-After": str(_WINDOW_S)},
        )

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
    Passenger message -> one fact-extraction call -> Python rules
    -> live Indian alternative flights -> deterministic explanation.

    Facts are persisted in MongoDB between conversation turns.
    """

    session_id = body.session_id or str(uuid4())

    # 1. Load previous conversation facts.
    try:
        saved_facts = load_facts(session_id)
        prior_facts = {**saved_facts, **body.known_facts}

    except RuntimeError:
        logger.exception("Passenger session storage failed")
        raise HTTPException(
            status_code=503,
            detail="Conversation storage is temporarily unavailable.",
        )

    # 2. Extract facts. This is the only LLM call in this endpoint.
    try:
        facts = generation.extract_facts(
            body.message,
            prior_facts,
        )

    except generation.FactTypeConflict as conflict:
        return {
            "status": "needs_more_info",
            "session_id": session_id,
            "known_facts": prior_facts,
            "missing_facts": ["type"],
            "questions": [
                (
                    f"Earlier you described the disruption as "
                    f"'{conflict.previous_type}', but your latest message "
                    f"suggests '{conflict.proposed_type}'. "
                    "Which one actually happened? Please explicitly correct "
                    "the earlier answer if it was wrong."
                )
            ],
            "reason": "conflicting_disruption_type",
        }

    except Exception:
        logger.exception("Passenger fact extraction failed")
        raise HTTPException(
            status_code=502,
            detail={
                "error": "llm_service_unavailable",
                "message": "Could not understand the passenger's message. Please retry.",
            },
        )

    # 3. Persist extracted facts.
    try:
        save_facts(session_id, facts)

    except RuntimeError:
        logger.exception("Could not save passenger facts")
        raise HTTPException(
            status_code=503,
            detail="Could not save this conversation. Please retry.",
        )

    # 4. We need to know what kind of disruption occurred.
    if not facts.get("type"):
        missing = ["type"]

        return {
            "status": "needs_more_info",
            "session_id": session_id,
            "known_facts": facts,
            "missing_facts": missing,
            "questions": questions_for(missing),
        }

    # 5. Evaluate facts and build the recovery plan using Python.
    try:
        plan = plan_recovery(facts)

    except ValueError as error:
        raise HTTPException(
            status_code=422,
            detail=str(error),
        )

    except Exception:
        logger.exception("Recovery planning failed")
        raise HTTPException(
            status_code=500,
            detail="Could not calculate the recovery plan.",
        )

    decision = plan["decision"]

    # 6. Ask all missing questions together.
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
                "The system could not reliably complete this evaluation. "
                "Please review the decision details."
            ),
        }

    # 7. Generate the explanation locally. No LLM request.
    explanation = generation.build_explanation(plan)

    evidence_status = plan.get("evidence", {}).get("status")

    if evidence_status == "unavailable":
        plan["evidence_warning"] = (
            "The rule calculation completed, but the supporting policy "
            "text could not be retrieved."
        )

    elif evidence_status == "partial":
        plan["evidence_warning"] = (
            "Some policy clauses could not be retrieved. Review the "
            "available evidence before relying on the result."
        )

    # 8. Return the complete response.
    return {
       "status": "ok",
        "session_id": session_id,
        "known_facts": facts,
        "explanation": explanation,
        "entitlement": generation.entitlement_payload(decision),
        "explanation_mode": "deterministic",
        "policy_grounded": evidence_status == "ok",
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


@app.post(
    "/ask/stream",
    tags=["AI Assistant"],
    dependencies=[Depends(rate_limit)],
)
async def ask_stream(body: AskIn):
    """
    Passenger message -> fact extraction -> deterministic rules
    -> policy retrieval -> streamed LLM explanation.

    Passenger-facing stream:
        session: session metadata
        token: explanation text chunks
        question: clarification question, if needed
        error: safe error message
        done: completion metadata

    Internal pipeline data is never sent to the frontend.
    """

    async def generate_events():

        session_id = body.session_id or str(uuid4())

        try:
            # 1. Load conversation facts.
            saved_facts = await asyncio.to_thread(
                load_facts,
                session_id,
            )

            prior_facts = {
                **saved_facts,
                **body.known_facts,
            }

            # Session metadata is for the frontend to retain,
            # not something it should display as chat text.
            yield _sse_event(
                "session",
                {"session_id": session_id},
            )

            # 2. Extract facts.
            facts = await asyncio.to_thread(
                generation.extract_facts,
                body.message,
                prior_facts,
            )

            await asyncio.to_thread(
                save_facts,
                session_id,
                facts,
            )

            # 3. Ask for disruption type if missing.
            if not facts.get("type"):

                questions = questions_for(["type"])

                for question in questions:
                    yield _sse_event(
                        "question",
                        {"text": question},
                    )

                yield _sse_event(
                    "done",
                    {
                        "session_id": session_id,
                        "status": "needs_more_info",
                    },
                )
                return

            # 4. Run deterministic recovery plan.
            plan = await asyncio.to_thread(
                plan_recovery,
                facts,
            )

            decision = plan["decision"]

            # 5. Ask for missing facts.
            if decision["status"] == "needs_more_info":

                questions = questions_for(
                    decision["missing_facts"]
                )

                for question in questions:
                    yield _sse_event(
                        "question",
                        {"text": question},
                    )

                yield _sse_event(
                    "done",
                    {
                        "session_id": session_id,
                        "status": "needs_more_info",
                    },
                )
                return

            # 6. Handle unsuccessful evaluation.
            if decision["status"] != "ok":

                yield _sse_event(
                    "error",
                    {
                        "message": (
                            "I could not complete your flight disruption "
                            "evaluation with the available information."
                        )
                    },
                )

                yield _sse_event(
                    "done",
                    {
                        "session_id": session_id,
                        "status": decision["status"],
                    },
                )
                return

            evidence_status = plan.get("evidence", {}).get("status")

            # 7. Python-computed result goes out FIRST, so the passenger always
            # sees verified amounts regardless of what the LLM writes next.
            yield _sse_event(
                "result",
                {
                    "entitlement": generation.entitlement_payload(decision),
                    "summary": generation.entitlement_summary(decision),
                    "policy_grounded": evidence_status == "ok",
                },
            )

            # 8. Only let the LLM talk when the cited clause text was retrieved.
            # Otherwise send the deterministic explanation instead.
            if evidence_status != "ok":
                yield _sse_event(
                    "token",
                    {"text": generation.build_explanation(plan)},
                )
                yield _sse_event(
                    "done",
                    {
                        "session_id": session_id,
                        "status": "ok",
                        "explanation_mode": "deterministic",
                        "policy_grounded": False,
                    },
                )
                return

            iterator = iter(
                generation.stream_explain(
                    body.message,
                    plan,
                )
            )

            streamed_anything = False

            while True:

                chunk = await asyncio.to_thread(
                    _next_stream_item,
                    iterator,
                )

                if chunk is None:
                    break

                if not chunk:
                    continue

                streamed_anything = True

                yield _sse_event(
                    "token",
                    {"text": chunk},
                )

            if not streamed_anything:
                raise RuntimeError(
                    "The language model returned an empty explanation."
                )

            # 9. Finish.
            yield _sse_event(
                "done",
                {
                    "session_id": session_id,
                    "status": "ok",
                    "explanation_mode": "llm",
                    "policy_grounded": True,
                },
            )

        except generation.FactTypeConflict as conflict:

            yield _sse_event(
                "question",
                {
                    "text": (
                        f"Earlier you described the disruption as "
                        f"{conflict.previous_type}, but now your message "
                        f"suggests {conflict.proposed_type}. "
                        "Which one actually happened? Please explicitly "
                        "correct your earlier answer if it was wrong."
                    )
                },
            )

            yield _sse_event(
                "done",
                {
                    "session_id": session_id,
                    "status": "needs_more_info",
                },
            )

        except Exception:

            logger.exception(
                "Streaming passenger explanation failed"
            )

            yield _sse_event(
                "error",
                {
                    "message": (
                        "I could not generate your explanation right now. "
                        "Please try again."
                    )
                },
            )

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
    # Browsers always send Origin; only allow the configured frontends. A
    # missing Origin (non-browser client) is tolerated in development only.
    origin = ws.headers.get("origin")
    if origin is None:
        origin_ok = not IS_PRODUCTION
    else:
        origin_ok = origin in CORS_ORIGINS
    if not origin_ok or not allow_request(client_ip(ws)):
        await ws.close(code=1008)          # policy violation
        return

    await ws.accept()

    try:
        payload = await asyncio.wait_for(ws.receive_json(), timeout=15)

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

    except asyncio.TimeoutError:
        logger.info("WebSocket client sent nothing in time")

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
