"""
Dependency container.

Holds references to the application's singleton service objects.
``main.py`` populates these values once at startup, before any request is served.
Routes import from this module instead of receiving services via constructor
arguments, which keeps the router files free of factory boilerplate while
avoiding circular imports.

Usage in a route file:
    import app.dependencies as deps

    @router.post("/chat")
    async def chat(payload: dict):
        result = await deps.chat_service.handle_job(...)
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    # Imported only for type-checking; not at runtime to prevent circular imports.
    from app.services.chat_service import ChatService
    from app.services.news_service import NewsService
    from app.services.news_aggregator import NewsAggregator
    from app.services.llm.tools.executor import ToolExecutor
    from app.services.llm.tools.classifier.service import TopicClassifierService
    from app.services.stock_chat_service import StockChatService
    from app.services.stock_news_service import StockNewsService

# Service singletons — set by main.py before the ASGI server starts serving
chat_service: "ChatService | None" = None
news_service: "NewsService | None" = None
aggregator: "NewsAggregator | None" = None
tool_executor: "ToolExecutor | None" = None
topic_classifier_service: "TopicClassifierService | None" = None
stock_chat_service: "StockChatService | None" = None
stock_news_service: "StockNewsService | None" = None
