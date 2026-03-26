import os
from dataclasses import dataclass
from pathlib import Path


def _csv_env(name: str) -> tuple[str, ...]:
    """Parse comma-separated environment variables into a tuple."""
    raw = os.environ.get(name, "")
    return tuple(part.strip() for part in raw.split(",") if part.strip())

@dataclass(frozen=True)
class Settings:
    DB_PATH: Path = Path(os.environ.get("DB_PATH", "news.db"))
    ARS_RSS_URL: str = "https://feeds.arstechnica.com/arstechnica/index"
    MAX_ITEMS_PER_UPDATE: int = 30
    MAX_CONCURRENT_REQUESTS: int = 6
    HTTP_TIMEOUT: float = 10.0
    HTTP_RETRIES: int = 2
    CORS_ALLOWED_ORIGINS: tuple[str, ...] = _csv_env("CORS_ALLOWED_ORIGINS")
    EXTERNAL_API_KEYS: tuple[str, ...] = _csv_env("EXTERNAL_API_KEYS")

settings = Settings()
