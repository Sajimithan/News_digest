from sse_starlette.sse import EventSourceResponse
from fastapi import APIRouter
from fastapi import Request

from app.services.sse_manager import sse_manager

router = APIRouter()

@router.get("/events")
async def events(request: Request, client_id: str):
    queue = await sse_manager.register(client_id)

    async def gen():
        try:
            while True:
                if await request.is_disconnected():
                    break
                msg = await queue.get()
                yield msg
        finally:
            await sse_manager.unregister(client_id)

    return EventSourceResponse(gen())
