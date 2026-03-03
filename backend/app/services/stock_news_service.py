"""
Stock News Service.

Fetches, caches, and retrieves stock / financial / market news articles.
Mirrors ``NewsService`` but uses ``StockArticleRepository`` and
stock-specific news providers via ``NewsAggregator``.
"""
import logging
from datetime import datetime, timezone

from app.models.stock_article import StockArticle
from app.repositories.stock_article_repo import StockArticleRepository
from app.services.async_utils import to_thread
from app.services.news_aggregator import NewsAggregator

logger = logging.getLogger(__name__)


class StockNewsService:
    def __init__(
        self,
        repo: StockArticleRepository,
        aggregator: NewsAggregator,
    ) -> None:
        self.repo = repo
        self.aggregator = aggregator

    def get_latest_date(self) -> str | None:
        return self.repo.get_latest_date()

    def get_news_for_date(self, yyyy_mm_dd: str, limit: int = 20):
        """Return (source, title, link, tickers, sentiment) tuples for ``date``."""
        return self.repo.get_by_date(yyyy_mm_dd, limit=limit)

    async def update_for_date(
        self,
        yyyy_mm_dd: str,
        limit: int,
        client_id: str,
        job_id: str,
    ) -> int:
        """Fetch stock news from all configured providers and save to DB."""
        articles_data, _stats = await self.aggregator.fetch_from_all(
            yyyy_mm_dd, limit, client_id, job_id
        )

        if not articles_data:
            return 0

        count = 0
        for item in articles_data:
            if not item.link or not item.title:
                continue

            article = StockArticle(
                source=item.source or "Unknown",
                title=item.title.strip(),
                link=item.link.strip(),
                published_date=getattr(item, "published_date", yyyy_mm_dd) or yyyy_mm_dd,
                published_at=getattr(item, "published_at", None),
                summary=getattr(item, "summary", None),
                tickers=getattr(item, "tickers", None),
                sentiment=getattr(item, "sentiment", None),
            )
            saved = await to_thread(self.repo.save, article)
            if saved:
                count += 1

        logger.info("StockNewsService.update_for_date(%s) → %d new articles", yyyy_mm_dd, count)
        return count
