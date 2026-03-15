"""
Tech News Chatbot — application entry point.

Architecture Notes
==================
- SSE is server → client streaming.  REST endpoints create async jobs and
  return a job_id immediately; SSE streams progress and results.
- Parallel fetching uses asyncio.gather with a shared httpx.AsyncClient and
  a global Semaphore to cap concurrent outbound requests.
- LLM usage (Groq) is isolated to intent-parsing and summarisation and runs
  off the event loop via asyncio.to_thread so it never blocks request handling.
- Service objects are wired once at startup and stored in app.dependencies so
  route modules can import them without circular-import issues.
- Global exception handlers are registered via app.exceptions.handlers so
  individual route functions stay free of try/except boilerplate.
"""

import asyncio
import logging
import os
from pathlib import Path

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.responses import HTMLResponse

from app.config import settings
from app.dependencies import chat_service  # noqa: F401 — imported for TYPE_CHECKING users
import app.dependencies as deps
from app.exceptions.handlers import register_exception_handlers
from app.repositories.article_repo import ArticleRepository
from app.repositories.db import Database
from app.routes import chat, health, news, sse
from app.routes import stock as stock_route
from app.services.chat_service import ChatService
from app.services.llm.groq_llm import GroqLLM
from app.services.llm.tools.executor import ToolExecutor
from app.services.llm.tools.classifier.service import TopicClassifierService
from app.services.news_aggregator import NewsAggregator
from app.services.news_service import NewsService
from app.services.providers.base import ProviderConfig
from app.services.providers.guardian import GuardianProvider
from app.services.providers.newsapi_ai import NewsApiAiProvider
from app.services.providers.newsapi_org import NewsApiOrgProvider
from app.services.providers.alphavantage import AlphaVantageProvider
from app.services.providers.finnhub import FinnhubProvider
from app.services.providers.guardian_business import GuardianBusinessProvider
from app.services.providers.newsapi_business import NewsApiBusinessProvider
from app.repositories.stock_article_repo import StockArticleRepository
from app.services.stock_news_service import StockNewsService
from app.services.stock_chat_service import StockChatService
from app.services.rss_fetcher import RSSFetcher
from app.services.sse_manager import sse_manager

# Load .env BEFORE reading any os.getenv() calls
load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Application factory
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Tech News Chatbot",
    description="Fetch, cache, and chat about tech news from multiple providers.",
    version="2.0.1",  # Auto-deployed from GitHub Actions
)

# Global exception handlers — must be registered before routes are added
register_exception_handlers(app)

# ---------------------------------------------------------------------------
# Infrastructure / shared resources
# ---------------------------------------------------------------------------

db = Database(settings.DB_PATH)
repo = ArticleRepository(db)
fetcher = RSSFetcher()

semaphore = asyncio.Semaphore(settings.MAX_CONCURRENT_REQUESTS)
async_client = httpx.AsyncClient(timeout=settings.HTTP_TIMEOUT)

# ---------------------------------------------------------------------------
# News providers
# ---------------------------------------------------------------------------

guardian_provider = GuardianProvider(
    ProviderConfig(
        api_key=os.getenv("GUARDIAN_API_KEY"),
        timeout=settings.HTTP_TIMEOUT,
        retries=settings.HTTP_RETRIES,
    ),
    async_client,
    semaphore,
)
newsapi_org_provider = NewsApiOrgProvider(
    ProviderConfig(
        api_key=os.getenv("NEWSAPI_API_KEY"),
        timeout=settings.HTTP_TIMEOUT,
        retries=settings.HTTP_RETRIES,
    ),
    async_client,
    semaphore,
)
newsapi_ai_provider = NewsApiAiProvider(
    ProviderConfig(
        api_key=os.getenv("NEWSAPIAI_API_KEY"),
        timeout=settings.HTTP_TIMEOUT,
        retries=settings.HTTP_RETRIES,
    ),
    async_client,
    semaphore,
)

aggregator = NewsAggregator(
    providers=[guardian_provider, newsapi_org_provider, newsapi_ai_provider],
    sse_manager=sse_manager,
    semaphore=semaphore,
)

# ---------------------------------------------------------------------------
# Stock / Market intelligence providers
# ---------------------------------------------------------------------------

stock_repo = StockArticleRepository(db)

alpha_provider = AlphaVantageProvider(
    ProviderConfig(
        api_key=os.getenv("ALPHAVANTAGE_API_KEY"),
        timeout=settings.HTTP_TIMEOUT,
        retries=settings.HTTP_RETRIES,
    ),
    async_client,
    semaphore,
)
finnhub_provider = FinnhubProvider(
    ProviderConfig(
        api_key=os.getenv("FINNHUB_API_KEY"),
        timeout=settings.HTTP_TIMEOUT,
        retries=settings.HTTP_RETRIES,
    ),
    async_client,
    semaphore,
)
guardian_business_provider = GuardianBusinessProvider(
    ProviderConfig(
        api_key=os.getenv("GUARDIAN_API_KEY"),   # reuse existing Guardian key
        timeout=settings.HTTP_TIMEOUT,
        retries=settings.HTTP_RETRIES,
    ),
    async_client,
    semaphore,
)
newsapi_business_provider = NewsApiBusinessProvider(
    ProviderConfig(
        api_key=os.getenv("NEWSAPI_API_KEY"),    # reuse existing NewsAPI.org key
        timeout=settings.HTTP_TIMEOUT,
        retries=settings.HTTP_RETRIES,
    ),
    async_client,
    semaphore,
)

stock_aggregator = NewsAggregator(
    providers=[
        alpha_provider,
        finnhub_provider,
        guardian_business_provider,
        newsapi_business_provider,
    ],
    sse_manager=sse_manager,
    semaphore=semaphore,
)

# ---------------------------------------------------------------------------
# Services
# ---------------------------------------------------------------------------

news_service = NewsService(repo, fetcher, aggregator)
stock_news_service = StockNewsService(stock_repo, stock_aggregator)

# Topic classifier — always created (guards on groq_key before calling Groq)
topic_classifier = TopicClassifierService(news_service)

# Tool executor — handle both tech-news and stock-news tools
tool_executor = ToolExecutor(
    news_service,
    topic_classifier_service=topic_classifier,
    stock_news_service=stock_news_service,
)

groq_key = os.getenv("GROQ_API_KEY")
_intent_model = os.getenv("GROQ_INTENT_MODEL", "llama-3.1-8b-instant")
_stream_model = os.getenv("GROQ_STREAM_MODEL", "llama-3.3-70b-versatile")
_fallback_stream_model = os.getenv("GROQ_FALLBACK_STREAM_MODEL", "llama-3.1-8b-instant")
if groq_key:
    llm = GroqLLM(
        model=_intent_model,
        stream_model=_stream_model,
        fallback_stream_model=_fallback_stream_model,
    )
    _chat_service = ChatService(
        news_service,
        llm=llm,
        llm_enabled=True,
        tool_executor=tool_executor,
        topic_classifier_service=topic_classifier,
    )
    _stock_chat_service = StockChatService(
        stock_news_service,
        llm=llm,
        llm_enabled=True,
        tool_executor=tool_executor,
    )
    logger.info(
        "Groq LLM enabled (intent=%s, stream=%s, fallback=%s)",
        _intent_model, _stream_model, _fallback_stream_model,
    )
else:
    _chat_service = ChatService(
        news_service,
        llm=None,
        llm_enabled=False,
        topic_classifier_service=topic_classifier,
    )
    _stock_chat_service = StockChatService(
        stock_news_service,
        llm=None,
        llm_enabled=False,
    )
    logger.info("Groq LLM disabled — GROQ_API_KEY not set.  Using rule-based intent parsing.")

# Populate the dependency container so route modules can access services
deps.chat_service = _chat_service
deps.news_service = news_service
deps.aggregator = aggregator
deps.tool_executor = tool_executor
deps.topic_classifier_service = topic_classifier
deps.stock_chat_service = _stock_chat_service
deps.stock_news_service = stock_news_service

# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

app.include_router(sse.router)
app.include_router(chat.router)
app.include_router(news.router)
app.include_router(health.router)
app.include_router(stock_route.router)

# ---------------------------------------------------------------------------
# UI — React build (production) or legacy HTML (fallback)
# ---------------------------------------------------------------------------

_FRONTEND_DIST = Path(__file__).parent.parent / "frontend" / "dist"
_LEGACY_INDEX = Path(__file__).parent / "views" / "index.html"


if _FRONTEND_DIST.exists():
    # Serve the compiled React app.  StaticFiles(html=True) handles
    # client-side routing by serving index.html for unknown paths.
    from fastapi.staticfiles import StaticFiles  # noqa: E402
    app.mount("/", StaticFiles(directory=_FRONTEND_DIST, html=True), name="frontend")
    logger.info("Serving React frontend from %s", _FRONTEND_DIST)
else:
    # Dev fallback: serve the original plain-HTML UI
    @app.get("/", response_class=HTMLResponse, include_in_schema=False)
    def index() -> str:
        """Serve the legacy single-page chatbot HTML UI."""
        return _LEGACY_INDEX.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Lifecycle
# ---------------------------------------------------------------------------

@app.on_event("shutdown")
async def _shutdown() -> None:
    """Close the shared HTTP client when the server stops."""
    await async_client.aclose()
    logger.info("HTTP client closed.")
