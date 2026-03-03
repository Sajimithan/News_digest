"""
Tool executor — maps LLM tool-call requests to real service calls.

Usage:
    executor = ToolExecutor(news_service)
    result_json = await executor.execute(tool_call)

``tool_call`` is a ``groq.types.chat.ChatCompletionMessageToolCall`` object
returned by the Groq API.  The executor looks up the function name, runs the
appropriate handler, and returns a JSON string to be fed back to the model.
"""

import json
import logging
from datetime import date, timedelta
from typing import TYPE_CHECKING, Any

from app.utils.date_helpers import resolve_date

if TYPE_CHECKING:
    from app.services.news_service import NewsService
    from app.services.stock_news_service import StockNewsService
    from app.services.llm.tools.classifier.service import TopicClassifierService

logger = logging.getLogger(__name__)


class ToolExecutor:
    """
    Executes Groq tool calls by routing to registered async handlers.

    New tools:
      1. Add a schema to ``definitions.ALL_TOOLS``.
      2. Add ``"tool_name": self._handler`` to ``self._handlers`` below.
      3. Implement the handler as an ``async def _handler(self, **kwargs) -> str``.
    """

    def __init__(
        self,
        news_service: "NewsService",
        topic_classifier_service: "TopicClassifierService | None" = None,
        stock_news_service: "StockNewsService | None" = None,
    ) -> None:
        self.news_service = news_service
        self.topic_classifier_service = topic_classifier_service
        self.stock_news_service = stock_news_service
        self._handlers: dict[str, Any] = {
            "fetch_news_for_date":      self._fetch_news_for_date,
            "classify_news_topics":     self._classify_news_topics,
            "fetch_stock_news_for_date": self._fetch_stock_news_for_date,
        }

    async def execute(self, tool_call) -> str:
        """
        Execute a single tool call and return the result as a JSON string.

        Args:
            tool_call: ``ChatCompletionMessageToolCall`` from the Groq SDK.

        Returns:
            JSON string to be sent back to the model as a tool-role message.
        """
        fn_name = tool_call.function.name
        raw_args = tool_call.function.arguments or "{}"

        try:
            args: dict = json.loads(raw_args)
        except json.JSONDecodeError:
            logger.warning("Tool %s received non-JSON arguments: %s", fn_name, raw_args)
            return json.dumps({"error": f"Could not parse arguments for {fn_name}."})

        handler = self._handlers.get(fn_name)
        if handler is None:
            logger.warning("Unknown tool called by model: %s", fn_name)
            return json.dumps({"error": f"Unknown tool: {fn_name}."})

        try:
            return await handler(**args)
        except TypeError as exc:
            logger.warning("Wrong arguments for %s: %s", fn_name, exc)
            return json.dumps({"error": f"Invalid arguments for {fn_name}: {exc}"})
        except Exception:
            logger.exception("Unexpected error executing tool %s", fn_name)
            return json.dumps({"error": f"Tool {fn_name} failed unexpectedly."})

    # ------------------------------------------------------------------
    # Handlers — each returns a JSON string
    # ------------------------------------------------------------------

    async def _fetch_news_for_date(self, date: str, **kwargs) -> str:
        """
        Fetch tech-news articles for ``date`` from the DB cache.
        If the cache is empty, trigger a live fetch first (silent — no SSE).

        ``limit`` is intentionally removed from the tool schema to avoid
        the model passing it as a string (Groq type-validation failure).
        A fixed limit of 15 is used instead.
        """        
        limit = 15

        rows = self.news_service.get_news_for_date(date, limit=limit)

        if not rows:
            logger.info("Tool fetch_news: cache empty for %s — triggering live fetch", date)
            # Silent update (no SSE client; job_id is a sentinel string)
            await self.news_service.update_for_date(
                date, limit, client_id="", job_id="__tool_fetch__"
            )
            rows = self.news_service.get_news_for_date(date, limit=limit)

        if not rows:
            logger.info("Tool fetch_news: no articles available for %s", date)
            return json.dumps({
                "date": date,
                "articles": [],
                "message": f"No tech news articles are available for {date}.",
            })

        articles = [
            {"source": source, "title": title, "link": link}
            for source, title, link in rows
        ]
        logger.info("Tool fetch_news_for_date(%s) → %d articles", date, len(articles))
        return json.dumps({"date": date, "articles": articles})

    async def _classify_news_topics(self, date: str, limit: int = 20, **kwargs) -> str:
        """
        Classify tech-news headlines for ``date`` into topic categories.

        Resolves relative date strings ("today", "yesterday") before calling
        the TopicClassifierService.  Returns the classification JSON as a string.
        """
        if self.topic_classifier_service is None:
            logger.warning("classify_news_topics called but TopicClassifierService not wired")
            return json.dumps({"error": "Topic classifier service is not available."})

        resolved = resolve_date(date)

        try:
            result = await self.topic_classifier_service.classify_by_date(resolved, limit=int(limit))
            logger.info(
                "Tool classify_news_topics(%s) → %d classified, counts=%s",
                resolved,
                len(result.get("classified", [])),
                result.get("topic_counts", {}),
            )
            return json.dumps(result)
        except Exception as exc:
            logger.exception("Tool classify_news_topics failed for date=%s: %s", resolved, exc)
            return json.dumps({"error": str(exc)})

    async def _fetch_stock_news_for_date(self, date: str, **kwargs) -> str:
        """
        Fetch stock/financial news for ``date`` from the DB cache.
        If the cache is empty, trigger a silent live fetch first.
        """
        if self.stock_news_service is None:
            logger.warning("fetch_stock_news_for_date called but StockNewsService not wired")
            return json.dumps({"error": "Stock news service is not available."})

        limit = 20
        resolved = resolve_date(date)

        rows = self.stock_news_service.get_news_for_date(resolved, limit=limit)
        if not rows:
            logger.info("Stock tool: cache empty for %s — triggering live fetch", resolved)
            await self.stock_news_service.update_for_date(
                resolved, limit, client_id="", job_id="__stock_tool_fetch__"
            )
            rows = self.stock_news_service.get_news_for_date(resolved, limit=limit)

        if not rows:
            return json.dumps({
                "date": resolved,
                "articles": [],
                "message": f"No stock/market news articles are available for {resolved}.",
            })

        articles = [
            {
                "source":    source,
                "title":     title,
                "link":      link,
                "tickers":   tickers or "",
                "sentiment": sentiment or "Neutral",
            }
            for source, title, link, tickers, sentiment in rows
        ]
        logger.info("Tool fetch_stock_news_for_date(%s) → %d articles", resolved, len(articles))
        return json.dumps({"date": resolved, "articles": articles})
