import os
from dataclasses import dataclass
from pathlib import Path

@dataclass(frozen=True)
class Settings:
    DB_PATH: Path = Path(os.environ.get("DB_PATH", "news.db"))
    ARS_RSS_URL: str = "https://feeds.arstechnica.com/arstechnica/index"
    MAX_ITEMS_PER_UPDATE: int = 30
    MAX_CONCURRENT_REQUESTS: int = 6
    HTTP_TIMEOUT: float = 10.0
    HTTP_RETRIES: int = 2

settings = Settings()
