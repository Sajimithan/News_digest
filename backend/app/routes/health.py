"""
Health & debug routes.

GET /health              — lightweight liveness probe
GET /debug/providers     — check each news provider (live API call)
GET /job/{job_id}        — inspect the status/result of an async job
"""

import logging
from datetime import date, datetime, timezone

from fastapi import APIRouter

import app.dependencies as deps
from app.services.job_manager import job_manager

logger = logging.getLogger(__name__)

router = APIRouter(tags=["health", "debug"])


@router.get("/health")
def health() -> dict:
    """
    Lightweight liveness probe.

    Returns 200 OK with server timestamp so load-balancers / monitors
    can confirm the process is alive without touching the database or
    external APIs.
    """
    return {
        "status": "ok",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/debug/providers")
async def debug_providers(client_id: str | None = None) -> dict:
    """
    Run a live health-check against each configured news provider.

    An SSE ``provider_error`` event is published to ``client_id`` (if
    supplied) for every provider that fails.  Useful for diagnosing
    which API keys are working.
    """
    status = await deps.aggregator.check_providers(client_id or "")
    return {"date": date.today().isoformat(), "providers": status}


@router.get("/job/{job_id}")
def job_status(job_id: str) -> dict:
    """
    Return the current status and result (if complete) of an async job.

    Response::

        {
            "job_id":  "...",
            "status":  "queued | running | done | failed | unknown",
            "detail":  "...",
            "result":  {...} | null
        }
    """
    job = job_manager.get(job_id)
    if not job:
        return {"job_id": job_id, "status": "unknown", "detail": None, "result": None}
    return {
        "job_id": job_id,
        "status": job.status,
        "detail": job.detail,
        "result": job.result,
    }
