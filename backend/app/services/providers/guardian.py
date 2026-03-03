from datetime import date

from app.models.article import Article
from app.services.providers.base import BaseProvider


class GuardianProvider(BaseProvider):
    name = "Guardian"

    async def fetch_by_date(self, date_yyyy_mm_dd: str, limit: int) -> list[Article]:
        if not self.config.api_key:
            return []

        try:
            date.fromisoformat(date_yyyy_mm_dd)
        except ValueError:
            return []

        limit = max(1, min(limit, 50))

        params = {
            "api-key": self.config.api_key,
            "section": "technology",
            "from-date": date_yyyy_mm_dd,
            "to-date": date_yyyy_mm_dd,
            "page-size": limit,
            "show-fields": "headline,trailText",
            "order-by": "newest",
        }

        data = await self._get_json("https://content.guardianapis.com/search", params)
        response_data = data.get("response", {})
        results = response_data.get("results", [])

        articles: list[Article] = []
        for item in results:
            title = (item.get("webTitle") or "").strip()
            url = (item.get("webUrl") or "").strip()
            published_at = item.get("webPublicationDate") or ""
            fields = item.get("fields", {})
            headline = (fields.get("headline") or title).strip()

            if not url or not title:
                continue

            articles.append(
                Article(
                    source="The Guardian",
                    title=headline or title,
                    link=url,
                    published_date=date_yyyy_mm_dd,
                    published_at=published_at,
                    summary=None,
                )
            )

        return articles
