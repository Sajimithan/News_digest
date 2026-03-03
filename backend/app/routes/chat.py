"""
Chat route.

POST /chat  {"message": "...", "client_id": "..."}

Accepts a user message, creates an async job, and immediately returns
the job ID.  Actual processing and result delivery happen asynchronously
via the SSE stream identified by ``client_id``.
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

router = APIRouter(tags=["chat"])


@router.post("/chat")
async def chat(payload: dict) -> dict:
    """
    Start a chat job.

    Request body::

        {"message": "today update", "client_id": "<uuid>"}

    Response::

        {"job_id": "<uuid>"}

    The result is published as a ``result`` SSE event on the client's
    open ``/events`` stream.

    Raises:
        InputValidationError: If ``message`` or ``client_id`` are missing.
    """
    message = (payload.get("message") or "").strip()
    client_id = (payload.get("client_id") or "").strip()

    if not message:
        raise InputValidationError("'message' field is required.", field="message")
    if not client_id:
        raise InputValidationError(
            "'client_id' field is required.  Open /events first to obtain one.",
            field="client_id",
        )

    job_id = job_manager.create_job()
    job_manager.update(job_id, "queued", f"User asked: {message}")
    await sse_manager.publish(client_id, "status", f"Job queued: {job_id}")

    logger.info("Chat job %s created for client_id=%s message=%r", job_id, client_id, message)

    svc = deps.chat_service
    if svc is None:
        logger.error("chat_service is not initialised — cannot process job %s", job_id)
        return JSONResponse(status_code=503, content={"error": {"type": "ServiceUnavailable", "message": "Chat service not ready. Please retry in a moment."}})

    asyncio.create_task(
        _run_with_timeout(svc, message, client_id, job_id)
    )

    return {"job_id": job_id}


async def _run_with_timeout(
    svc,
    message: str,
    client_id: str,
    job_id: str,
    timeout: float = 90.0,
) -> None:
    """Run handle_job with a hard timeout; publish stream_end on expiry."""
    import json
    try:
        await asyncio.wait_for(
            svc.handle_job(message, client_id, job_id, sse_manager, job_manager),
            timeout=timeout,
        )
    except asyncio.TimeoutError:
        logger.warning("Job %s timed out after %.0fs", job_id, timeout)
        job_manager.update(job_id, "failed", "Timed out")
        await sse_manager.publish(
            client_id,
            "stream_end",
            json.dumps({"job_id": job_id, "articles": [], "error": "Request timed out after 90 s."}),
        )
    except Exception:
        logger.exception("Unhandled error in background job %s", job_id)
        job_manager.update(job_id, "failed", "Unexpected error")
