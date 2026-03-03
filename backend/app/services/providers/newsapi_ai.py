from datetime import date

from app.models.article import Article
from app.services.providers.base import BaseProvider

# EventRegistry free plan only provides articles from the last ~30 days.
_NEWSAPI_AI_MAX_DAYS = 28


class NewsApiAiProvider(BaseProvider):
    name = "NewsAPI.ai"

    async def fetch_by_date(self, date_yyyy_mm_dd: str, limit: int) -> list[Article]:
        if not self.config.api_key:
            return []

        try:
            target = date.fromisoformat(date_yyyy_mm_dd)
        except ValueError:
            return []

        # Free plan restriction: can't fetch articles older than ~30 days
        if (date.today() - target).days > _NEWSAPI_AI_MAX_DAYS:
            return []

        limit = max(1, min(limit, 100))

        # Note: EventRegistry 'keyword' is a phrase/term search, not boolean.
        # Use a single broad term; OR-lists are treated as literal phrases.
        params = {
            "apiKey": self.config.api_key,
            "action": "getArticles",
            "resultType": "articles",
            "articlesSortBy": "date",
            "articlesCount": limit,
            "lang": "eng",
            "dateStart": date_yyyy_mm_dd,
            "dateEnd": date_yyyy_mm_dd,
            "keyword": "technology",
        }

        data = await self._get_json(
            "https://eventregistry.org/api/v1/article/getArticles",
            params,
        )
        results = (data.get("articles") or {}).get("results", [])

        articles: list[Article] = []
        for item in results:
            title = (item.get("title") or "").strip()
            url = (item.get("url") or "").strip()
            source = (item.get("source") or {}).get("title") or "NewsAPI.ai"
            published_at = item.get("dateTime") or ""

            if not url or not title:
                continue

            articles.append(
                Article(
                    source=source,
                    title=title,
                    link=url,
                    published_date=date_yyyy_mm_dd,
                    published_at=published_at,
                    summary=None,
                )
            )

        return articles
