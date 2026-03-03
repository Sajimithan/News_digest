from fastapi import APIRouter
from datetime import date

from app.services.job_manager import job_manager
from app.services.news_aggregator import NewsAggregator


def build_debug_router(aggregator: NewsAggregator) -> APIRouter:
    router = APIRouter()

    @router.get("/debug/providers")
    async def debug_providers(client_id: str | None = None):
        status = await aggregator.check_providers(client_id or "")
        return {"date": date.today().isoformat(), "providers": status}

    @router.get("/job/{job_id}")
    async def job_status(job_id: str):
        job = job_manager.get(job_id)
        if not job:
            return {"job_id": job_id, "status": "unknown"}
        return {
            "job_id": job_id,
            "status": job.status,
            "detail": job.detail,
            "result": job.result,
        }

    return router
