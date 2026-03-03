"""
Finnhub market news provider.

Endpoint: GET https://finnhub.io/api/v1/news
Categories: general, forex, crypto, merger

Free tier: 60 API calls / minute.
Date filtering: Finnhub returns recent general news — we filter client-side
by the requested date using the unix ``datetime`` field.
"""
from datetime import date as _date, timezone, datetime

from app.models.stock_article import StockArticle
from app.services.providers.base import BaseProvider


class FinnhubProvider(BaseProvider):
    name = "Finnhub"

    async def fetch_by_date(self, date_yyyy_mm_dd: str, limit: int) -> list[StockArticle]:
        if not self.config.api_key:
            return []

        params = {
            "category": "general",
            "token":    self.config.api_key,
            "minId":    0,
        }

        data = await self._get_json("https://finnhub.io/api/v1/news", params)
        if not isinstance(data, list):
            return []

        articles: list[StockArticle] = []
        for item in data:
            title = (item.get("headline") or "").strip()
            url   = (item.get("url") or "").strip()
            if not title or not url:
                continue

            # Convert unix timestamp → date string
            unix_ts = item.get("datetime") or 0
            try:
                dt    = datetime.fromtimestamp(unix_ts, tz=timezone.utc)
                pub_date = dt.date().isoformat()
                published_at = dt.isoformat()
            except Exception:
                pub_date     = date_yyyy_mm_dd
                published_at = None

            # Filter to requested date only
            if pub_date != date_yyyy_mm_dd:
                continue

            articles.append(
                StockArticle(
                    source="Finnhub",
                    title=title,
                    link=url,
                    published_date=pub_date,
                    published_at=published_at,
                    summary=item.get("summary"),
                    tickers=None,
                    sentiment=None,
                )
            )

            if len(articles) >= limit:
                break

        return articles

    async def health_check(self, date_yyyy_mm_dd: str) -> bool:
        if not self.config.api_key:
            return False
        params = {"category": "general", "token": self.config.api_key}
        data = await self._get_json("https://finnhub.io/api/v1/news", params)
        return isinstance(data, list)
