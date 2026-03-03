import requests
import feedparser

class RSSFetcher:
    """
    Fetch RSS content via requests (HTTP), then parse with feedparser.
    """
    def fetch_and_parse(self, url: str):
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
        # feedparser can parse bytes or text
        return feedparser.parse(resp.content)
