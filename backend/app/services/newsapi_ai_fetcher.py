import requests
from datetime import date
from typing import Optional


class NewsAPIAIFetcher:
    """
    Fetches tech news from NewsAPI.ai (Event Registry) for a specific date.
    Requires an API key.
    """

    BASE_URL = "https://eventregistry.org/api/v1/article/getArticles"

    def __init__(self, api_key: Optional[str] = None, timeout: int = 10):
        self.api_key = api_key
        self.timeout = timeout

    def fetch_for_date(self, date_yyyy_mm_dd: str, limit: int = 15) -> list[dict]:
        if not self.api_key:
            print("NewsAPI.ai key not provided. Set NEWSAPIAI_API_KEY in .env")
            return []

        try:
            date.fromisoformat(date_yyyy_mm_dd)
        except ValueError:
            print(f"Invalid date format: {date_yyyy_mm_dd}")
            return []

        limit = max(1, min(limit, 100))

        params = {
            "apiKey": self.api_key,
            "action": "getArticles",
            "resultType": "articles",
            "articlesSortBy": "date",
            "articlesCount": limit,
            "lang": "eng",
            "dateStart": date_yyyy_mm_dd,
            "dateEnd": date_yyyy_mm_dd,
            "keyword": "technology OR software OR AI OR cybersecurity OR startup",
        }

        try:
            response = requests.get(
                self.BASE_URL,
                params=params,
                timeout=self.timeout,
                headers={"User-Agent": "TechNewsChatbot/1.0"},
            )

            if response.status_code == 429:
                print(f"NewsAPI.ai rate limit hit for date {date_yyyy_mm_dd}.")
                return []

            if response.status_code != 200:
                print(f"NewsAPI.ai returned status {response.status_code} for date {date_yyyy_mm_dd}")
                return []

            data = response.json()
            articles_raw = (data.get("articles") or {}).get("results", [])
            if not articles_raw:
                return []

            articles = []
            for item in articles_raw:
                title = (item.get("title") or "").strip()
                url = (item.get("url") or "").strip()
                source = (item.get("source") or {}).get("title") or "NewsAPI.ai"
                published_at = item.get("dateTime") or ""

                if not url or not title:
                    continue

                articles.append({
                    "source": source,
                    "title": title,
                    "url": url,
                    "published_at": published_at,
                    "date": date_yyyy_mm_dd,
                })

            return articles

        except requests.Timeout:
            print(f"NewsAPI.ai timeout for date {date_yyyy_mm_dd}")
            return []
        except requests.RequestException as e:
            print(f"NewsAPI.ai error for date {date_yyyy_mm_dd}: {e}")
            return []
        except Exception as e:
            print(f"Unexpected error fetching NewsAPI.ai data for {date_yyyy_mm_dd}: {e}")
            return []
