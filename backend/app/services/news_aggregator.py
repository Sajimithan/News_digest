import asyncio
import json
from datetime import date
from typing import Iterable

from app.models.article import Article
from app.services.providers.base import Provider
from app.services.sse_manager import SSEManager


class NewsAggregator:
    def __init__(
        self,
        providers: Iterable[Provider],
        sse_manager: SSEManager,
        semaphore: asyncio.Semaphore,
    ) -> None:
        self.providers = list(providers)
        self.sse_manager = sse_manager
        self.semaphore = semaphore

    async def fetch_from_all(
        self,
        date_yyyy_mm_dd: str,
        limit: int,
        client_id: str,
        job_id: str,
    ) -> tuple[list[Article], dict]:
        tasks = [
            self._fetch_provider(provider, date_yyyy_mm_dd, limit, client_id, job_id)
            for provider in self.providers
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        all_articles: list[Article] = []
        stats: dict[str, int] = {}
        for provider, result in zip(self.providers, results):
            if isinstance(result, Exception):
                stats[provider.name] = 0
                continue
            stats[provider.name] = len(result)
            all_articles.extend(result)

        await self.sse_manager.publish(
            client_id,
            "job_done",
            json.dumps({"job_id": job_id, "total": len(all_articles)}),
        )

        return all_articles, stats

    async def check_providers(self, client_id: str) -> dict[str, bool]:
        today = date.today().isoformat()
        status: dict[str, bool] = {}
        for provider in self.providers:
            try:
                ok = await provider.health_check(today)
                status[provider.name] = ok
            except Exception:
                status[provider.name] = False
                await self.sse_manager.publish(
                    client_id,
                    "provider_error",
                    f"{provider.name} health check failed",
                )
        return status

    async def _fetch_provider(
        self,
        provider: Provider,
        date_yyyy_mm_dd: str,
        limit: int,
        client_id: str,
        job_id: str,
    ) -> list[Article]:
        await self.sse_manager.publish(
            client_id,
            "provider_started",
            json.dumps({"job_id": job_id, "provider": provider.name}),
        )
        try:
            items = await provider.fetch_by_date(date_yyyy_mm_dd, limit)
            await self.sse_manager.publish(
                client_id,
                "provider_done",
                json.dumps({"job_id": job_id, "provider": provider.name, "count": len(items)}),
            )
            return items
        except Exception as exc:
            await self.sse_manager.publish(
                client_id,
                "provider_error",
                json.dumps({"job_id": job_id, "provider": provider.name, "error": str(exc)}),
            )
            return []
