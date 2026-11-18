import asyncio
import json
from typing import Any
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.schemas.capabilities import AirlineContact, ClaimPackageRequest, ClaimPackageResponse
from app.services.claims import AIRLINE_REGISTRY, ClaimFactsIncomplete, build_claim_package

router = APIRouter(prefix="/claims", tags=["Passenger Claims"])


def _sse_event(name: str, data: Any) -> str:
    payload = json.dumps(data, default=str)
    return f"event: {name}\ndata: {payload}\n\n"


@router.get("/airlines", response_model=list[AirlineContact], summary="List airline nodal contacts")
async def list_airline_contacts():
    """Retrieve official Nodal Officer and Appellate Authority contacts for Indian scheduled carriers."""
    return list(AIRLINE_REGISTRY.values())


@router.post("/generate", response_model=ClaimPackageResponse, summary="Generate full passenger claim package")
async def generate_claim(req: ClaimPackageRequest):
    """
    Generate statutory claim package: grievance notice, 30-day resolution timeline,
    and disruption-specific evidence checklist.
    """
    try:
        return await asyncio.to_thread(build_claim_package, req)
    except ClaimFactsIncomplete as exc:
        raise HTTPException(status_code=422, detail={
            "status": exc.status,
            "missing_facts": exc.missing_facts,
            "notes": exc.notes,
            "message": "Please provide the missing facts before generating a claim package.",
        })
    except Exception:
        raise HTTPException(status_code=500, detail="Failed to generate claim package")


@router.post("/stream", summary="Stream claim package generation via Server-Sent Events (SSE)")
async def stream_claim(req: ClaimPackageRequest):
    """
    Progressively stream claim package milestones, evidence checklist,
    and notice drafting tokens directly to the frontend.
    """
    async def event_generator():
        try:
            yield _sse_event("session", {"pnr": req.pnr, "flight": req.flight_number})
            yield _sse_event("status", {"message": "Evaluating statutory entitlement against DGCA CAR..."})

            pkg = await asyncio.to_thread(build_claim_package, req)

            yield _sse_event("summary", {
                "pnr": pkg.pnr,
                "disruption_type": pkg.disruption_type,
                "compensation_inr": pkg.statutory_compensation_inr,
                "refund_status": pkg.refund_status,
                "care_status": pkg.care_status,
                "airline": pkg.airline.model_dump(),
            })

            yield _sse_event("timeline", {
                "milestones": [m.model_dump() for m in pkg.timeline]
            })

            yield _sse_event("checklist", {
                "items": [item.model_dump() for item in pkg.evidence_checklist]
            })

            yield _sse_event("status", {"message": "Drafting statutory grievance notice..."})

            # This is a deterministic document, not model token output.
            yield _sse_event("notice", {"text": pkg.formal_grievance_notice})

            yield _sse_event("escalation", {
                "instructions": pkg.escalation_instructions
            })

            yield _sse_event("done", {
                "status": "complete",
                "pnr": pkg.pnr,
                "statutory_compensation_inr": pkg.statutory_compensation_inr,
            })

        except ClaimFactsIncomplete as exc:
            yield _sse_event("needs_more_info", {
                "status": exc.status, "missing_facts": exc.missing_facts, "notes": exc.notes
            })
            yield _sse_event("done", {"status": "needs_more_info"})
        except Exception:
            yield _sse_event("error", {"message": "Claim package generation failed. Please retry."})
            yield _sse_event("done", {"status": "failed"})

    return StreamingResponse(event_generator(), media_type="text/event-stream")
