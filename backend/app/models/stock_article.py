from dataclasses import dataclass
from typing import Optional


@dataclass
class StockArticle:
    source: str
    title: str
    link: str
    published_date: str          # YYYY-MM-DD
    published_at: Optional[str] = None
    summary: Optional[str] = None
    tickers: Optional[str] = None     # comma-separated, e.g. "AAPL,MSFT"
    sentiment: Optional[str] = None   # Bullish / Bearish / Neutral / Somewhat-Bullish / etc.
