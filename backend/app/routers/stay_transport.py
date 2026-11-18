import asyncio
import json
from typing import Any
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.schemas.capabilities import (
    EmergencyDutyOfCareResponse,
    EmergencyStayRequest,
)
from app.services.stay_transport import search_emergency_stay_and_transport

router = APIRouter(prefix="/stay-transport", tags=["Emergency Stay & Transport"])


def _sse_event(name: str, data: Any) -> str:
    payload = json.dumps(data, default=str)
    return f"event: {name}\ndata: {payload}\n\n"


@router.post("/evaluate", response_model=EmergencyDutyOfCareResponse, summary="Evaluate emergency stay and transport")
async def evaluate_stay_and_transport(req: EmergencyStayRequest):
    """
    Evaluate statutory duty of care under DGCA Para 3.4.3 & 3.8.1 (b).
    Returns curated hotel directory references and clearly labelled taxi estimates,
    and official counter demand scripts.
    """
    try:
        return await asyncio.to_thread(search_emergency_stay_and_transport, req)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Emergency stay evaluation failed: {str(exc)}")


@router.post("/stream", summary="Stream emergency stay options and counter script via SSE")
async def stream_stay(req: EmergencyStayRequest):
    """
    Progressively stream duty-of-care verification, hotel accommodation options,
    cab transfer estimates, and counter demand scripts.
    """
    async def event_generator():
        try:
            yield _sse_event("status", {
                "message": f"Evaluating DGCA duty-of-care obligations at {req.airport_code}..."
            })

            res = await asyncio.to_thread(search_emergency_stay_and_transport, req)

            yield _sse_event("duty_of_care", {
                "mandated": res.duty_of_care_mandated,
                "clause": res.statutory_clause,
                "statement": res.airline_liability_statement,
            })

            yield _sse_event("hotels", {
                "count": len(res.hotels),
                "options": [h.model_dump() for h in res.hotels],
            })

            yield _sse_event("transport", {
                "count": len(res.transport),
                "options": [t.model_dump() for t in res.transport],
            })

            yield _sse_event("counter_script", {
                "text": res.counter_demand_script
            })

            yield _sse_event("self_booking_claim", {
                "template": res.self_booking_claim_template
            })

            yield _sse_event("done", {
                "status": "complete",
                "airport": res.airport_code,
                "duty_mandated": res.duty_of_care_mandated,
            })

        except Exception:
            yield _sse_event("error", {"message": "Emergency stay information is temporarily unavailable."})
            yield _sse_event("done", {"status": "failed"})

    return StreamingResponse(event_generator(), media_type="text/event-stream")
