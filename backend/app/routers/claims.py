import asyncio
import json
from typing import Any
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.schemas.capabilities import AirlineContact, ClaimPackageRequest, ClaimPackageResponse
from app.services.claims import AIRLINE_REGISTRY, build_claim_package

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
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to generate claim package: {str(exc)}")


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

            # Stream notice tokens
            words = pkg.formal_grievance_notice.split(" ")
            chunk = []
            for word in words:
                chunk.append(word)
                if len(chunk) >= 6:
                    yield _sse_event("token", {"text": " ".join(chunk) + " "})
                    chunk = []
                    await asyncio.sleep(0.015)
            if chunk:
                yield _sse_event("token", {"text": " ".join(chunk)})

            yield _sse_event("escalation", {
                "instructions": pkg.escalation_instructions
            })

            yield _sse_event("done", {
                "status": "complete",
                "pnr": pkg.pnr,
                "statutory_compensation_inr": pkg.statutory_compensation_inr,
            })

        except Exception as exc:
            yield _sse_event("error", {"message": str(exc)})
            yield _sse_event("done", {"status": "failed"})

    return StreamingResponse(event_generator(), media_type="text/event-stream")
