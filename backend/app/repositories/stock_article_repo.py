from typing import List, Tuple
from urllib.parse import urlparse, urlunparse

from app.models.stock_article import StockArticle
from app.repositories.db import Database


class StockArticleRepository:
    """
    Handles persistence for stock / financial news articles.
    Creates the ``stock_articles`` table if it does not exist.
    Uses the same shared :class:`Database` (same SQLite file) as the tech
    news repo so a single file stores all data.
    """

    def __init__(self, db: Database) -> None:
        self.db = db
        self._init_stock_schema()

    def _init_stock_schema(self) -> None:
        with self.db.connect() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS stock_articles (
                    id             INTEGER PRIMARY KEY AUTOINCREMENT,
                    source         TEXT NOT NULL,
                    title          TEXT NOT NULL,
                    link           TEXT NOT NULL UNIQUE,
                    published_date TEXT NOT NULL,
                    published_at   TEXT,
                    summary        TEXT,
                    tickers        TEXT,
                    sentiment      TEXT,
                    created_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_sa_date ON stock_articles(published_date)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_sa_link ON stock_articles(link)"
            )
            conn.commit()

    def _normalize_url(self, link: str) -> str:
        if not link:
            return link
        parsed = urlparse(link)
        cleaned = parsed._replace(query="", fragment="")
        return urlunparse(cleaned)

    def save(self, article: StockArticle) -> bool:
        normalized_link = self._normalize_url(article.link)
        with self.db.connect() as conn:
            cur = conn.execute(
                """
                INSERT OR IGNORE INTO stock_articles
                    (source, title, link, published_date, published_at, summary, tickers, sentiment)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    article.source,
                    article.title,
                    normalized_link,
                    article.published_date,
                    article.published_at,
                    article.summary,
                    article.tickers,
                    article.sentiment,
                ),
            )
            conn.commit()
            return cur.rowcount > 0

    def get_latest_date(self) -> str | None:
        with self.db.connect() as conn:
            row = conn.execute(
                "SELECT MAX(published_date) FROM stock_articles"
            ).fetchone()
        return row[0] if row and row[0] else None

    def get_by_date(
        self, yyyy_mm_dd: str, limit: int = 20
    ) -> List[Tuple[str, str, str, str | None, str | None]]:
        """Returns (source, title, link, tickers, sentiment) tuples."""
        with self.db.connect() as conn:
            rows = conn.execute(
                """
                SELECT source, title, link, tickers, sentiment
                FROM stock_articles
                WHERE published_date = ?
                ORDER BY id DESC
                LIMIT ?
                """,
                (yyyy_mm_dd, limit),
            ).fetchall()
        return rows
