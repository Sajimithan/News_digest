"""
News routes.

POST /update              {"client_id": "..."}  — trigger an async news-update job
GET  /news?d=YYYY-MM-DD   &limit=15             — read cached articles for a date
GET  /news/classify?d=YYYY-MM-DD&limit=20       — classify cached headlines with Groq
"""

import asyncio
import json
import logging
from datetime import date

from fastapi import APIRouter

import app.dependencies as deps
from app.exceptions.errors import DataNotFoundError, InputValidationError
from app.utils.date_helpers import resolve_date, validate_iso_date
from app.services.job_manager import job_manager
from app.services.sse_manager import sse_manager

logger = logging.getLogger(__name__)

router = APIRouter(tags=["news"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _sse_payload(result: dict, job_id: str) -> str:
    """Serialise a result dict as the JSON string pushed over SSE."""
    return json.dumps({"job_id": job_id, "payload": result})


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/update")
async def update(payload: dict | None = None) -> dict:
    """
    Trigger an asynchronous news-update job for today's date.

    Request body::

        {"client_id": "<uuid>"}

    Response::

        {"job_id": "<uuid>"}

    Progress and the final result are published as SSE events on the
    client's open ``/events`` stream.

    Raises:
        InputValidationError: If ``client_id`` is missing.
    """
    payload = payload or {}
    client_id = (payload.get("client_id") or "").strip()

    if not client_id:
        raise InputValidationError(
            "'client_id' field is required.  Open /events first to obtain one.",
            field="client_id",
        )

    job_id = job_manager.create_job()
    job_manager.update(job_id, "queued", "Update requested")
    await sse_manager.publish(client_id, "status", f"Job queued: {job_id}")

    logger.info("Update job %s created for client_id=%s", job_id, client_id)

    async def _run_update() -> None:
        target_date = date.today().isoformat()
        try:
            await deps.news_service.update_for_date(target_date, 15, client_id, job_id)
            rows = deps.news_service.get_news_for_date(target_date, limit=15)
            result = {"type": "news", "date": target_date, "items": rows}
            await sse_manager.publish(client_id, "result", _sse_payload(result, job_id))
            job_manager.set_result(job_id, result)
            logger.info("Update job %s complete — %d articles", job_id, len(rows))
        except Exception:
            logger.exception("Update job %s failed", job_id)
            job_manager.update(job_id, "failed", "Unexpected error during update.")

    asyncio.create_task(_run_update())
    return {"job_id": job_id}


@router.get("/news")
async def news(d: str | None = None, limit: int = 15) -> dict:
    """
    Return cached news articles for a given date.

    Query parameters:
        d     — date in ``YYYY-MM-DD`` format (defaults to today)
        limit — maximum number of articles to return (default 15)

    Response::

        {"date": "YYYY-MM-DD", "items": [{"source": "...", "title": "...", "link": "..."}, ...]}

    This endpoint reads the local SQLite cache only; it does **not** trigger
    a live fetch.  Use ``POST /update`` to populate the cache first.

    Raises:
        InputValidationError: If ``d`` is not a valid ISO date string.
    """
    target = (d or date.today().isoformat()).strip()

    try:
        date.fromisoformat(target)
    except ValueError:
        raise InputValidationError(
            f"Invalid date format: {target!r}. Expected YYYY-MM-DD.",
            field="d",
        )

    items = deps.news_service.get_news_for_date(target, limit=limit)
    return {
        "date": target,
        "items": [{"source": s, "title": t, "link": lnk} for s, t, lnk in items],
    }


@router.get("/news/classify")
async def classify_news(d: str | None = None, limit: int = 20) -> dict:
    """
    Classify cached tech-news headlines for a given date using Groq.

    Query parameters:
        d     — date in ``YYYY-MM-DD`` format, or ``"today"``/``"yesterday"``
                (defaults to today)
        limit — maximum number of articles to classify (default 20)

    Response::

        {
            "date": "YYYY-MM-DD",
            "classified": [
                {
                    "title":      "...",
                    "source":     "...",
                    "link":       "...",
                    "topic":      "AI_ML",
                    "confidence": 0.95,
                    "reason":     "..."
                },
                ...
            ],
            "topic_counts": {
                "AI_ML": 3,
                "CYBERSECURITY": 5,
                ...
            }
        }

    If no articles exist in the cache the service will attempt a live fetch
    before classifying.  If the fetch also returns nothing, a
    ``DataNotFoundError`` (404) is raised.

    Raises:
        InputValidationError: If ``d`` is not a valid date string (400).
        DataNotFoundError:    If no articles are available (404).
        ProviderError:        If the Groq API fails (502).
    """
    if deps.topic_classifier_service is None:
        raise InputValidationError(
            "Topic classifier service is not configured "
            "(GROQ_API_KEY may be missing).",
            field="d",
        )

    raw = (d or "today").strip()
    resolved = resolve_date(raw)

    try:
        validate_iso_date(resolved)
    except ValueError:
        raise InputValidationError(
            f"Invalid date: {raw!r}. Use YYYY-MM-DD, 'today', or 'yesterday'.",
            field="d",
        )

    return await deps.topic_classifier_service.classify_by_date(resolved, limit=limit)
