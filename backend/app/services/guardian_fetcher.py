import requests
from datetime import datetime, date
from typing import Optional


class GuardianFetcher:
    """
    Fetches tech news from The Guardian API for any specific date.
    This provides reliable historical news data back to 2000.
    
    Free tier: 500 requests/day
    Get API key: https://open-platform.theguardian.com/access/
    """

    BASE_URL = "https://content.guardianapis.com/search"

    def __init__(self, api_key: Optional[str] = None, timeout: int = 15):
        """
        Initialize Guardian fetcher.
        
        Args:
            api_key: Guardian API key (optional, but recommended)
            timeout: HTTP request timeout in seconds
        """
        self.api_key = api_key
        self.timeout = timeout

    def fetch_for_date(
        self, 
        date_yyyy_mm_dd: str, 
        limit: int = 15
    ) -> list[dict]:
        """
        Fetch tech news for a specific date from The Guardian.
        
        Args:
            date_yyyy_mm_dd: Date in YYYY-MM-DD format
            limit: Maximum number of articles to fetch (default: 15, max: 50)
            
        Returns:
            List of article dicts with keys: source, title, url, published_at, date
            Returns empty list if fetch fails or no results found.
            
        Example:
            >>> fetcher = GuardianFetcher(api_key="your-key")
            >>> articles = fetcher.fetch_for_date("2024-02-15", limit=10)
            >>> print(articles[0])
            {
                'source': 'The Guardian',
                'title': 'AI breakthroughs reshape industry',
                'url': 'https://...',
                'published_at': '2024-02-15T14:30:00Z',
                'date': '2024-02-15'
            }
        """
        if not self.api_key:
            print("Guardian API key not provided. Set GUARDIAN_API_KEY in .env")
            return []
        
        # Validate date format
        try:
            target_date = date.fromisoformat(date_yyyy_mm_dd)
        except ValueError:
            print(f"Invalid date format: {date_yyyy_mm_dd}")
            return []
        
        # Validate and clamp limit
        limit = max(1, min(limit, 50))
        
        # Build request parameters
        params = {
            "api-key": self.api_key,
            "section": "technology",  # Focus on tech news
            "from-date": date_yyyy_mm_dd,
            "to-date": date_yyyy_mm_dd,
            "page-size": limit,
            "show-fields": "headline,trailText",  # Get headline and summary
            "order-by": "newest"
        }
        
        try:
            response = requests.get(
                self.BASE_URL, 
                params=params, 
                timeout=self.timeout,
                headers={'User-Agent': 'TechNewsChatbot/1.0'}
            )
            
            # Check for rate limiting
            if response.status_code == 429:
                print(f"Guardian API rate limit hit for date {date_yyyy_mm_dd}.")
                return []
            
            # Check for authentication errors
            if response.status_code == 401:
                print(f"Guardian API authentication failed. Check your API key.")
                return []
            
            # Check for non-200 status codes
            if response.status_code != 200:
                print(f"Guardian API returned status {response.status_code} for date {date_yyyy_mm_dd}")
                return []
            
            # Parse JSON
            try:
                data = response.json()
            except ValueError as json_err:
                print(f"Guardian API returned invalid JSON for date {date_yyyy_mm_dd}: {json_err}")
                return []
            
            # Guardian returns data in response.results
            response_data = data.get("response", {})
            articles_raw = response_data.get("results", [])
            
            if not articles_raw:
                print(f"No Guardian articles found for {date_yyyy_mm_dd}")
                return []
            
            # Transform to our standard format
            articles = []
            for item in articles_raw:
                # Extract fields
                title = item.get("webTitle", "").strip()
                url = item.get("webUrl", "").strip()
                published_at = item.get("webPublicationDate", "")
                fields = item.get("fields", {})
                headline = fields.get("headline", title)
                
                # Skip items without required fields
                if not url or not title:
                    continue
                
                # Parse publication date
                pub_date = self._parse_guardian_date(published_at) or date_yyyy_mm_dd
                
                articles.append({
                    "source": "The Guardian",
                    "title": headline or title,
                    "url": url,
                    "published_at": pub_date,
                    "date": date_yyyy_mm_dd,
                })
            
            return articles
            
        except requests.Timeout:
            print(f"Guardian API timeout for date {date_yyyy_mm_dd}")
            return []
        except requests.RequestException as e:
            print(f"Guardian API error for date {date_yyyy_mm_dd}: {e}")
            return []
        except Exception as e:
            print(f"Unexpected error fetching Guardian data for {date_yyyy_mm_dd}: {e}")
            return []

    def _parse_guardian_date(self, date_str: str) -> Optional[str]:
        """
        Parse Guardian date format (ISO 8601) to our format.
        
        Args:
            date_str: Guardian date string like "2024-02-15T14:30:00Z"
            
        Returns:
            ISO format date string or None if parsing fails
        """
        if not date_str:
            return None
        
        try:
            # Guardian uses ISO 8601 format, which is compatible
            dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            return dt.date().isoformat()
        except Exception:
            return None
