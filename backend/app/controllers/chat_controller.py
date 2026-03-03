import asyncio
from fastapi import APIRouter

from app.services.chat_service import ChatService
from app.services.job_manager import job_manager
from app.services.sse_manager import sse_manager

def build_chat_router(chat_service: ChatService) -> APIRouter:
    router = APIRouter()

    @router.post("/chat")
    async def chat(payload: dict):
        message = (payload.get("message") or "").strip()
        client_id = (payload.get("client_id") or "").strip()
        if not message:
            return {"type": "text", "content": "Say something like: 'today update'."}
        if not client_id:
            return {"type": "text", "content": "Missing client_id for SSE stream."}

        job_id = job_manager.create_job()
        job_manager.update(job_id, "queued", f"User asked: {message}")
        await sse_manager.publish(client_id, "status", f"Job queued: {job_id}")

        asyncio.create_task(
            chat_service.handle_job(message, client_id, job_id, sse_manager, job_manager)
        )

        return {"job_id": job_id}

    return router
