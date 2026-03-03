import asyncio
from fastapi import APIRouter
from datetime import date
from app.services.news_service import NewsService
from app.services.job_manager import job_manager
from app.services.sse_manager import sse_manager

def build_news_router(news_service: NewsService) -> APIRouter:
    router = APIRouter()

    @router.post("/update")
    async def update(payload: dict | None = None):
        payload = payload or {}
        client_id = (payload.get("client_id") or "").strip()
        if not client_id:
            return {"type": "text", "content": "Missing client_id for SSE stream."}

        job_id = job_manager.create_job()
        job_manager.update(job_id, "queued", "Update requested")
        await sse_manager.publish(client_id, "status", f"Job queued: {job_id}")

        async def run_update() -> None:
            target_date = date.today().isoformat()
            await news_service.update_for_date(target_date, 15, client_id, job_id)
            rows = news_service.get_news_for_date(target_date, limit=15)
            result = {"type": "news", "date": target_date, "items": rows}
            await sse_manager.publish(client_id, "result", json_dumps(result, job_id))
            job_manager.set_result(job_id, result)

        asyncio.create_task(run_update())

        return {"job_id": job_id}

    @router.get("/news")
    async def news(d: str | None = None, limit: int = 15):
        d = d or date.today().isoformat()
        items = news_service.get_news_for_date(d, limit=limit)
        return {"date": d, "items": [{"source": s, "title": t, "link": l} for s, t, l in items]}

    return router


def json_dumps(result: dict, job_id: str) -> str:
    import json

    return json.dumps({"job_id": job_id, "payload": result})
