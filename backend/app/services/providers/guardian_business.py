"""
Guardian Business / Finance provider.

Same API as GuardianProvider but queries the ``business`` and ``money``
sections rather than ``technology``.
"""
from datetime import date

from app.models.stock_article import StockArticle
from app.services.providers.base import BaseProvider


class GuardianBusinessProvider(BaseProvider):
    name = "Guardian Business"

    async def fetch_by_date(self, date_yyyy_mm_dd: str, limit: int) -> list[StockArticle]:
        if not self.config.api_key:
            return []

        try:
            date.fromisoformat(date_yyyy_mm_dd)
        except ValueError:
            return []

        limit = max(1, min(limit, 50))

        params = {
            "api-key":    self.config.api_key,
            "section":    "business|money",
            "from-date":  date_yyyy_mm_dd,
            "to-date":    date_yyyy_mm_dd,
            "page-size":  limit,
            "show-fields": "headline,trailText",
            "order-by":   "newest",
            "q":          "stock market OR trading OR earnings OR interest rates OR Federal Reserve OR inflation OR GDP",
        }

        data = await self._get_json("https://content.guardianapis.com/search", params)
        results = data.get("response", {}).get("results", [])

        articles: list[StockArticle] = []
        for item in results:
            title        = (item.get("webTitle") or "").strip()
            url          = (item.get("webUrl") or "").strip()
            published_at = item.get("webPublicationDate") or ""
            fields       = item.get("fields", {})
            headline     = (fields.get("headline") or title).strip()

            if not url or not title:
                continue

            articles.append(
                StockArticle(
                    source="The Guardian",
                    title=headline or title,
                    link=url,
                    published_date=date_yyyy_mm_dd,
                    published_at=published_at,
                )
            )

        return articles

    async def health_check(self, date_yyyy_mm_dd: str) -> bool:
        items = await self.fetch_by_date(date_yyyy_mm_dd, 1)
        return isinstance(items, list)
