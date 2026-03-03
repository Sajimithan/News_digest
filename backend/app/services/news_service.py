from datetime import datetime, timezone
from dateutil import parser as date_parser

from app.models.article import Article
from app.repositories.article_repo import ArticleRepository
from app.services.async_utils import to_thread
from app.services.news_aggregator import NewsAggregator
from app.services.rss_fetcher import RSSFetcher
from app.config import settings

class NewsService:
    def __init__(
        self,
        repo: ArticleRepository,
        fetcher: RSSFetcher,
        aggregator: NewsAggregator,
    ):
        self.repo = repo
        self.fetcher = fetcher
        self.aggregator = aggregator

    def _extract_date(self, entry) -> tuple[str, str | None]:
        candidates = []
        if hasattr(entry, "published"):
            candidates.append(entry.published)
        if hasattr(entry, "updated"):
            candidates.append(entry.updated)

        for c in candidates:
            try:
                dt = date_parser.parse(c)
                return dt.date().isoformat(), c
            except Exception:
                continue

        # fallback to today (UTC)
        today = datetime.now(timezone.utc).date().isoformat()
        return today, None

    def update_from_ars(self, max_items: int | None = None) -> int:
        max_items = max_items or settings.MAX_ITEMS_PER_UPDATE

        parsed = self.fetcher.fetch_and_parse(settings.ARS_RSS_URL)
        if getattr(parsed, "bozo", 0) == 1:
            # feed parse failed; return 0 new items
            return 0

        count = 0
        for entry in parsed.entries[:max_items]:
            title = getattr(entry, "title", "").strip() or "(no title)"
            link = getattr(entry, "link", "").strip()
            summary = getattr(entry, "summary", None)
            if not link:
                continue

            published_date, published_at = self._extract_date(entry)

            article = Article(
                source="Ars Technica",
                title=title,
                link=link,
                published_date=published_date,
                published_at=published_at,
                summary=summary,
            )
            self.repo.save(article)
            count += 1

        return count

    async def update_for_date(self, yyyy_mm_dd: str, limit: int, client_id: str, job_id: str) -> int:
        """
        Fetch tech news for a specific date using all providers in parallel.
        
        Args:
            yyyy_mm_dd: Date in YYYY-MM-DD format
            limit: Maximum number of articles to fetch (default: 15)
            
        Returns:
            Number of new articles saved to database
        """
        articles_data, _stats = await self.aggregator.fetch_from_all(
            yyyy_mm_dd,
            limit,
            client_id,
            job_id,
        )
        
        if not articles_data:
            return 0
        
        count = 0
        for item in articles_data:
            title = item.title.strip()
            url = item.link.strip()
            source = item.source or "Unknown"
            published_at = item.published_at or ""
            date = item.published_date or yyyy_mm_dd
            
            if not url or not title:
                continue
            
            article = Article(
                source=source,
                title=title,
                link=url,
                published_date=date,
                published_at=published_at,
                summary=None,
            )
            saved = await to_thread(self.repo.save, article)
            if saved:
                count += 1
        
        return count

    def get_latest_available_date(self) -> str | None:
        return self.repo.get_latest_date()

    def get_news_for_date(self, yyyy_mm_dd: str, limit: int = 15):
        return self.repo.get_by_date(yyyy_mm_dd, limit=limit)
