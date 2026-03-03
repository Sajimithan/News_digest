"""
Alpha Vantage News & Sentiment provider.

Endpoint: GET https://www.alphavantage.co/query
Function: NEWS_SENTIMENT
Topics:   earnings, financial_markets, economy_fiscal, economy_monetary, economy_macro

Free tier: 25 requests / day, 5 / minute.
"""
from datetime import datetime, timezone

from app.models.stock_article import StockArticle
from app.services.providers.base import BaseProvider


class AlphaVantageProvider(BaseProvider):
    name = "Alpha Vantage"

    _TOPICS = "earnings,financial_markets,economy_fiscal,economy_monetary,economy_macro"

    async def fetch_by_date(self, date_yyyy_mm_dd: str, limit: int) -> list[StockArticle]:
        if not self.config.api_key:
            return []

        # Alpha Vantage needs time_from / time_to as YYYYMMDDThhmm
        time_from = date_yyyy_mm_dd.replace("-", "") + "T0000"
        time_to   = date_yyyy_mm_dd.replace("-", "") + "T2359"

        params = {
            "function":    "NEWS_SENTIMENT",
            "topics":      self._TOPICS,
            "time_from":   time_from,
            "time_to":     time_to,
            "limit":       min(limit, 50),
            "sort":        "RELEVANCE",
            "apikey":      self.config.api_key,
        }

        data = await self._get_json("https://www.alphavantage.co/query", params)
        feed = data.get("feed", [])

        articles: list[StockArticle] = []
        for item in feed:
            title = (item.get("title") or "").strip()
            url   = (item.get("url") or "").strip()
            if not title or not url:
                continue

            # Parse publication time
            raw_time   = item.get("time_published") or ""          # "20260303T143000"
            published_at = raw_time
            published_date = date_yyyy_mm_dd
            if len(raw_time) >= 8:
                try:
                    dt = datetime.strptime(raw_time[:8], "%Y%m%d")
                    published_date = dt.date().isoformat()
                except ValueError:
                    pass

            # Extract tickers (top 3)
            ticker_sentiment = item.get("ticker_sentiment", [])
            tickers = ",".join(
                t["ticker"] for t in ticker_sentiment[:3] if t.get("ticker")
            ) or None

            sentiment = item.get("overall_sentiment_label") or None

            articles.append(
                StockArticle(
                    source="Alpha Vantage",
                    title=title,
                    link=url,
                    published_date=published_date,
                    published_at=published_at,
                    summary=item.get("summary"),
                    tickers=tickers,
                    sentiment=sentiment,
                )
            )

        return articles[:limit]

    async def health_check(self, date_yyyy_mm_dd: str) -> bool:
        items = await self.fetch_by_date(date_yyyy_mm_dd, 1)
        return isinstance(items, list)
