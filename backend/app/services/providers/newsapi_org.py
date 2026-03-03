from datetime import date

from app.models.article import Article
from app.services.providers.base import BaseProvider

# NewsAPI.org free plan only allows articles from the last 30 days.
_NEWSAPI_ORG_MAX_DAYS = 28


class NewsApiOrgProvider(BaseProvider):
    name = "NewsAPI.org"

    async def fetch_by_date(self, date_yyyy_mm_dd: str, limit: int) -> list[Article]:
        if not self.config.api_key:
            return []

        try:
            target = date.fromisoformat(date_yyyy_mm_dd)
        except ValueError:
            return []

        # Free plan restriction: can't fetch articles older than ~30 days
        if (date.today() - target).days > _NEWSAPI_ORG_MAX_DAYS:
            return []

        limit = max(1, min(limit, 100))

        params = {
            "q": "technology OR software OR AI OR cybersecurity",
            "from": date_yyyy_mm_dd,
            "to": date_yyyy_mm_dd,
            "language": "en",
            "pageSize": limit,
            "sortBy": "publishedAt",
            "apiKey": self.config.api_key,
        }

        data = await self._get_json("https://newsapi.org/v2/everything", params)
        results = data.get("articles", [])

        articles: list[Article] = []
        for item in results:
            title = (item.get("title") or "").strip()
            url = (item.get("url") or "").strip()
            source_name = (item.get("source") or {}).get("name") or "NewsAPI"
            published_at = item.get("publishedAt") or ""

            if not url or not title:
                continue

            articles.append(
                Article(
                    source=source_name,
                    title=title,
                    link=url,
                    published_date=date_yyyy_mm_dd,
                    published_at=published_at,
                    summary=None,
                )
            )

        return articles
