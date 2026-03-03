from dataclasses import dataclass
from typing import Optional

@dataclass
class Article:
    source: str
    title: str
    link: str
    published_date: str          # YYYY-MM-DD
    published_at: Optional[str] = None
    summary: Optional[str] = None
