import asyncio
import json
from typing import Any
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.schemas.capabilities import (
    RebookingComparisonResponse,
    RebookingHandoffResponse,
    RebookingSearchRequest,
    RebookingSelectRequest,
)
from app.services.rebooking import process_rebooking_selection, search_flight_offers

router = APIRouter(prefix="/rebooking", tags=["Alternative Rebooking"])


def _sse_event(name: str, data: Any) -> str:
    payload = json.dumps(data, default=str)
    return f"event: {name}\ndata: {payload}\n\n"


@router.post("/search", response_model=RebookingComparisonResponse, summary="Search and compare alternative flights")
async def search_alternatives(req: RebookingSearchRequest):
    """
    Search commercial flight options, compare schedules, aircraft, prices,
    and analyze DGCA compensation impact under Para 3.3.2.
    """
    try:
        return await asyncio.to_thread(search_flight_offers, req)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception:
        raise HTTPException(status_code=503, detail="Flight schedule search is temporarily unavailable")


@router.post("/select", response_model=RebookingHandoffResponse, summary="Select flight offer and request confirmation/handoff")
async def select_alternative(req: RebookingSelectRequest):
    """
    Follows a strict multi-step reservation progression:
    1. Passenger selects offer -> refreshes price & asks for explicit confirmation.
    2. Explicit confirmation received -> generates statutory rebooking voucher and handoff link.
    """
    try:
        return await asyncio.to_thread(process_rebooking_selection, req)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception:
        raise HTTPException(status_code=500, detail="Rebooking selection failed")


@router.post("/stream", summary="Stream flight alternative search via SSE")
async def stream_rebooking(req: RebookingSearchRequest):
    """
    Progressively stream alternative flight options and statutory passenger rights notes.
    """
    async def event_generator():
        try:
            yield _sse_event("status", {
                "message": f"Querying commercial schedules for {req.origin} -> {req.destination}..."
            })

            res = await asyncio.to_thread(search_flight_offers, req)

            yield _sse_event("offers", {
                "count": res.offers_count,
                "offers": [o.model_dump() for o in res.offers],
                "search_status": res.search_status,
            })

            yield _sse_event("rights", {
                "note": res.passenger_rights_note
            })

            yield _sse_event("done", {
                "status": "complete",
                "origin": res.origin,
                "destination": res.destination,
            })

        except Exception:
            yield _sse_event("error", {"message": "Flight schedule search is temporarily unavailable."})
            yield _sse_event("done", {"status": "failed"})

    return StreamingResponse(event_generator(), media_type="text/event-stream")
