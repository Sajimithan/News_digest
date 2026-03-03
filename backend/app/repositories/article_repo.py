from typing import List, Tuple
from urllib.parse import urlparse, urlunparse

from app.models.article import Article
from app.repositories.db import Database

class ArticleRepository:
    def __init__(self, db: Database):
        self.db = db
        self.db.init_schema()

    def _normalize_url(self, link: str) -> str:
        if not link:
            return link
        parsed = urlparse(link)
        # Strip query params and fragments for canonicalization
        cleaned = parsed._replace(query="", fragment="")
        return urlunparse(cleaned)

    def save(self, article: Article) -> bool:
        normalized_link = self._normalize_url(article.link)
        with self.db.connect() as conn:
            cur = conn.execute("""
                INSERT OR IGNORE INTO articles (source, title, link, published_date, published_at, summary)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (article.source, article.title, normalized_link, article.published_date, article.published_at, article.summary))
            conn.commit()
            return cur.rowcount > 0

    def get_latest_date(self) -> str | None:
        with self.db.connect() as conn:
            row = conn.execute("SELECT MAX(published_date) FROM articles").fetchone()
        return row[0] if row and row[0] else None

    def get_by_date(self, yyyy_mm_dd: str, limit: int = 20) -> List[Tuple[str, str, str]]:
        with self.db.connect() as conn:
            rows = conn.execute("""
                SELECT source, title, link
                FROM articles
                WHERE published_date = ?
                ORDER BY id DESC
                LIMIT ?
            """, (yyyy_mm_dd, limit)).fetchall()
        return rows
