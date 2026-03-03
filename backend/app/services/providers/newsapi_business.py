"""
NewsAPI.org Business / Finance provider.

Same API as NewsApiOrgProvider but queries finance/market/trading keywords
rather than technology topics.
"""
from app.models.stock_article import StockArticle
from app.services.providers.base import BaseProvider


class NewsApiBusinessProvider(BaseProvider):
    name = "NewsAPI Business"

    _QUERY = (
        "stock market OR Wall Street OR S&P 500 OR Nasdaq OR Dow Jones "
        "OR earnings OR Federal Reserve OR interest rates OR inflation OR "
        "trading OR cryptocurrency OR bitcoin OR bonds OR IPO OR merger"
    )

    async def fetch_by_date(self, date_yyyy_mm_dd: str, limit: int) -> list[StockArticle]:
        if not self.config.api_key:
            return []

        params = {
            "apiKey":   self.config.api_key,
            "q":        self._QUERY,
            "from":     date_yyyy_mm_dd,
            "to":       date_yyyy_mm_dd,
            "language": "en",
            "sortBy":   "publishedAt",
            "pageSize": min(limit, 100),
        }

        data     = await self._get_json("https://newsapi.org/v2/everything", params)
        articles_raw = data.get("articles", [])

        articles: list[StockArticle] = []
        for item in articles_raw:
            title = (item.get("title") or "").strip()
            url   = (item.get("url") or "").strip()
            if not title or not url or title == "[Removed]":
                continue

            source_name  = (item.get("source", {}) or {}).get("name") or "NewsAPI"
            published_at = item.get("publishedAt") or ""

            articles.append(
                StockArticle(
                    source=source_name,
                    title=title,
                    link=url,
                    published_date=date_yyyy_mm_dd,
                    published_at=published_at,
                    summary=item.get("description"),
                )
            )

        return articles

    async def health_check(self, date_yyyy_mm_dd: str) -> bool:
        items = await self.fetch_by_date(date_yyyy_mm_dd, 1)
        return isinstance(items, list)
