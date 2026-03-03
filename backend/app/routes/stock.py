"""
Stock / Market Intelligence routes.

POST /stock/chat  — submit a market question, returns job_id immediately.
                    Results are delivered via the shared SSE stream.
"""
import asyncio
import logging

from fastapi import APIRouter
from fastapi.responses import JSONResponse

import app.dependencies as deps
from app.exceptions.errors import InputValidationError
from app.services.job_manager import job_manager
from app.services.sse_manager import sse_manager

logger = logging.getLogger(__name__)

router = APIRouter(tags=["stock"])


@router.post("/stock/chat")
async def stock_chat(payload: dict) -> dict:
    """
    Start a market-intelligence chat job.

    Request body::

        {"message": "analyze today's market", "client_id": "<uuid>"}

    Response::

        {"job_id": "<uuid>"}

    The result is delivered via the SSE stream as ``stream_start`` /
    ``stream_token`` / ``stream_end`` events.

    Raises:
        InputValidationError: if ``message`` or ``client_id`` are missing.
    """
    message   = (payload.get("message") or "").strip()
    client_id = (payload.get("client_id") or "").strip()

    if not message:
        raise InputValidationError("'message' field is required.", field="message")
    if not client_id:
        raise InputValidationError("'client_id' field is required.", field="client_id")

    if deps.stock_chat_service is None:
        return JSONResponse(
            status_code=503,
            content={"error": {"message": "Stock chat service is not available."}},
        )

    job_id = job_manager.create_job()

    asyncio.create_task(
        deps.stock_chat_service.handle_job(
            message=message,
            client_id=client_id,
            job_id=job_id,
            sse_manager=sse_manager,
            job_manager=job_manager,
        )
    )

    return {"job_id": job_id}
