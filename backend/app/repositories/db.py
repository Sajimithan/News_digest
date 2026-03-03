import sqlite3
from pathlib import Path
from threading import Lock

class Database:
    """
    Singleton-style DB manager.
    - One shared instance controls schema initialization.
    - For SQLite with FastAPI, we create connections per operation (safe).
    """
    _instance = None
    _lock = Lock()

    def __new__(cls, db_path: Path):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance.db_path = db_path
                cls._instance._init_done = False
        return cls._instance

    def connect(self) -> sqlite3.Connection:
        # check_same_thread=False can help in threaded servers, but we keep short-lived connections anyway
        return sqlite3.connect(self.db_path)

    def init_schema(self) -> None:
        if self._init_done:
            return
        with self.connect() as conn:
            conn.execute("""
            CREATE TABLE IF NOT EXISTS articles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source TEXT NOT NULL,
                title TEXT NOT NULL,
                link TEXT NOT NULL UNIQUE,
                published_date TEXT NOT NULL,
                published_at TEXT,
                summary TEXT
            )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_articles_date ON articles(published_date)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_articles_link ON articles(link)")
            conn.commit()
        self._init_done = True
