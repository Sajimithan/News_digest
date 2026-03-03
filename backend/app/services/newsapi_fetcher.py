import requests
from datetime import date
from typing import Optional


class NewsAPIFetcher:
    """
    Fetches tech news from NewsAPI.org for a specific date.
    Free tier limitation: historical coverage is limited (usually last 30 days).
    """

    BASE_URL = "https://newsapi.org/v2/everything"

    def __init__(self, api_key: Optional[str] = None, timeout: int = 10):
        self.api_key = api_key
        self.timeout = timeout

    def fetch_for_date(self, date_yyyy_mm_dd: str, limit: int = 15) -> list[dict]:
        if not self.api_key:
            print("NewsAPI key not provided. Set NEWSAPI_API_KEY in .env")
            return []

        try:
            date.fromisoformat(date_yyyy_mm_dd)
        except ValueError:
            print(f"Invalid date format: {date_yyyy_mm_dd}")
            return []

        limit = max(1, min(limit, 100))

        params = {
            "q": "technology OR software OR AI OR cybersecurity OR startup",
            "from": date_yyyy_mm_dd,
            "to": date_yyyy_mm_dd,
            "language": "en",
            "pageSize": limit,
            "sortBy": "publishedAt",
            "apiKey": self.api_key,
        }

        try:
            response = requests.get(
                self.BASE_URL,
                params=params,
                timeout=self.timeout,
                headers={"User-Agent": "TechNewsChatbot/1.0"},
            )

            if response.status_code == 429:
                print(f"NewsAPI rate limit hit for date {date_yyyy_mm_dd}.")
                return []

            if response.status_code != 200:
                print(f"NewsAPI returned status {response.status_code} for date {date_yyyy_mm_dd}")
                return []

            data = response.json()
            articles_raw = data.get("articles", [])
            if not articles_raw:
                return []

            articles = []
            for item in articles_raw:
                title = (item.get("title") or "").strip()
                url = (item.get("url") or "").strip()
                source_name = (item.get("source") or {}).get("name") or "NewsAPI"
                published_at = item.get("publishedAt") or ""

                if not url or not title:
                    continue

                articles.append({
                    "source": source_name,
                    "title": title,
                    "url": url,
                    "published_at": published_at,
                    "date": date_yyyy_mm_dd,
                })

            return articles

        except requests.Timeout:
            print(f"NewsAPI timeout for date {date_yyyy_mm_dd}")
            return []
        except requests.RequestException as e:
            print(f"NewsAPI error for date {date_yyyy_mm_dd}: {e}")
            return []
        except Exception as e:
            print(f"Unexpected error fetching NewsAPI data for {date_yyyy_mm_dd}: {e}")
            return []
