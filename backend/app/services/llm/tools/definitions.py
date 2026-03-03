"""
Groq function-calling tool definitions.

These schemas are passed as ``tools=ALL_TOOLS`` when calling the Groq API.
The model calls one or more of these tools and we execute them in
``executor.py`` before streaming the final answer.
"""

# Schema for the fetch_news_for_date tool
FETCH_NEWS_TOOL: dict = {
    "type": "function",
    "function": {
        "name": "fetch_news_for_date",
        "description": (
            "Fetch technology & software news articles stored for a specific date. "
            "Returns article titles, sources, and URLs.  "
            "Always call this tool before writing the news summary."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "date": {
                    "type": "string",
                    "description": (
                        "The date to fetch articles for, in ISO 8601 format YYYY-MM-DD "
                        "(e.g. '2026-02-20').  Required."
                    ),
                },
            },
            "required": ["date"],
        },
    },
}

# Schema for the classify_news_topics tool
CLASSIFY_NEWS_TOOL: dict = {
    "type": "function",
    "function": {
        "name": "classify_news_topics",
        "description": (
            "Classify technology news headlines for a specific date into topic categories "
            "(AI_ML, CYBERSECURITY, CLOUD_DEVOPS, PROGRAMMING_FRAMEWORKS, MOBILE_DEVICES, "
            "OPEN_SOURCE, DATA_INFRA, BIG_TECH_BUSINESS, GAMING, SCIENCE_TECH, OTHER).  "
            "Returns a structured JSON result with per-article classification and topic counts.  "
            "Call this tool when the user asks to classify, categorise, or group news by topic."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "date": {
                    "type": "string",
                    "description": (
                        'The date to classify articles for.  Accepts "today", "yesterday", '
                        "or an ISO-8601 date string (YYYY-MM-DD).  Required."
                    ),
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of articles to classify (default 20).",
                },
            },
            "required": ["date"],
        },
    },
}

# All tools exposed to the tech-news model.
ALL_TOOLS: list[dict] = [FETCH_NEWS_TOOL, CLASSIFY_NEWS_TOOL]

# ---------------------------------------------------------------------------
# Stock / financial news tool
# ---------------------------------------------------------------------------

FETCH_STOCK_NEWS_TOOL: dict = {
    "type": "function",
    "function": {
        "name": "fetch_stock_news_for_date",
        "description": (
            "Fetch stock market, financial, and business news articles stored for a specific date. "
            "Returns article titles, sources, URLs, tickers, and sentiment labels.  "
            "Always call this tool before writing the market summary or trend prediction."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "date": {
                    "type": "string",
                    "description": (
                        "The date to fetch articles for, in ISO 8601 format YYYY-MM-DD "
                        "(e.g. '2026-03-03').  Required."
                    ),
                },
            },
            "required": ["date"],
        },
    },
}

# Tools exposed to the stock / market analysis model.
ALL_STOCK_TOOLS: list[dict] = [FETCH_STOCK_NEWS_TOOL]
