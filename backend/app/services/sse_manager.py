import asyncio
from typing import Dict


class SSEManager:
    def __init__(self) -> None:
        self._queues: Dict[str, asyncio.Queue] = {}
        self._lock = asyncio.Lock()

    async def register(self, client_id: str) -> asyncio.Queue:
        async with self._lock:
            queue = asyncio.Queue()
            self._queues[client_id] = queue
            return queue

    async def unregister(self, client_id: str) -> None:
        async with self._lock:
            self._queues.pop(client_id, None)

    async def publish(self, client_id: str, event: str, data: str) -> None:
        async with self._lock:
            queue = self._queues.get(client_id)
        if queue:
            await queue.put({"event": event, "data": data})

    async def broadcast(self, event: str, data: str) -> None:
        async with self._lock:
            queues = list(self._queues.values())
        for queue in queues:
            await queue.put({"event": event, "data": data})


sse_manager = SSEManager()
