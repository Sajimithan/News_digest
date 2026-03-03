import asyncio
import random
from dataclasses import dataclass
from typing import Protocol

import httpx

from app.models.article import Article


class Provider(Protocol):
    name: str

    async def fetch_by_date(self, date_yyyy_mm_dd: str, limit: int) -> list[Article]:
        ...

    async def fetch_latest(self, limit: int) -> list[Article]:
        ...

    async def health_check(self, date_yyyy_mm_dd: str) -> bool:
        ...


@dataclass
class ProviderConfig:
    api_key: str | None
    timeout: float = 10.0
    retries: int = 2


class BaseProvider:
    name: str = "provider"

    def __init__(
        self,
        config: ProviderConfig,
        client: httpx.AsyncClient,
        semaphore: asyncio.Semaphore,
    ):
        self.config = config
        self.client = client
        self.semaphore = semaphore

    async def _get_json(self, url: str, params: dict) -> dict:
        backoff = 0.6
        for attempt in range(self.config.retries + 1):
            async with self.semaphore:
                try:
                    response = await self.client.get(
                        url,
                        params=params,
                        timeout=self.config.timeout,
                        headers={"User-Agent": "TechNewsChatbot/1.0"},
                    )
                except httpx.RequestError:
                    response = None

            if response is None:
                await self._sleep_backoff(backoff, attempt)
                continue

            if response.status_code in (429, 500, 502, 503, 504):
                await self._sleep_backoff(backoff, attempt)
                continue

            response.raise_for_status()
            return response.json()

        return {}

    async def _sleep_backoff(self, base: float, attempt: int) -> None:
        jitter = random.random() * 0.2
        await asyncio.sleep(base * (2 ** attempt) + jitter)

    async def fetch_latest(self, limit: int) -> list[Article]:
        from datetime import date

        return await self.fetch_by_date(date.today().isoformat(), limit)

    async def health_check(self, date_yyyy_mm_dd: str) -> bool:
        items = await self.fetch_by_date(date_yyyy_mm_dd, limit=1)
        return len(items) > 0
