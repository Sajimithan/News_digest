"""
Stock Chat Service.

Handles user messages directed at the Market Intelligence feature.
Parses stock-related intents, fetches financial news, and streams a
two-section LLM response:
  1. Market Summary
  2. Future Trend Prediction + Market Impact Analysis
"""
import json
import logging
import re
from datetime import date, timedelta
from typing import TYPE_CHECKING

from app.services.async_utils import to_thread
from app.services.job_manager import JobManager
from app.services.sse_manager import SSEManager
from app.utils.date_helpers import resolve_date

if TYPE_CHECKING:
    from app.services.llm.groq_llm import GroqLLM
    from app.services.llm.tools.executor import ToolExecutor
    from app.services.stock_news_service import StockNewsService

logger = logging.getLogger(__name__)

DATE_RE = re.compile(r"\b(\d{4}-\d{2}-\d{2})\b")

STOCK_HELP_TEXT = (
    "I can analyze stock market and financial news for any date!\n\n"
    "Try:\n"
    "- **analyze today's market** — full summary + trend prediction\n"
    "- **market news for yesterday** — yesterday's analysis\n"
    "- **2026-02-20** — analyze a specific date\n"
    "- **fetch today** — just fetch market news without analysis\n"
)


class StockChatService:
    def __init__(
        self,
        stock_news_service: "StockNewsService",
        llm: "GroqLLM | None" = None,
        llm_enabled: bool = False,
        tool_executor: "ToolExecutor | None" = None,
    ) -> None:
        self.stock_news_service = stock_news_service
        self.llm = llm
        self.llm_enabled = llm_enabled
        self.tool_executor = tool_executor

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _safe_date(raw: str) -> str:
        try:
            return resolve_date(raw)
        except Exception:
            return date.today().isoformat()

    @staticmethod
    def _sse_payload(result: dict, job_id: str) -> str:
        return json.dumps({"job_id": job_id, "payload": result})

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------

    async def handle_job(
        self,
        message: str,
        client_id: str,
        job_id: str,
        sse_manager: SSEManager,
        job_manager: JobManager,
    ) -> None:
        text = (message or "").strip()

        # ── Intent parsing ───────────────────────────────────────────────────
        if self.llm and self.llm_enabled:
            intent = await to_thread(self.llm.parse_stock_intent, text)
            action = intent.get("action") or "analyze"
            d      = self._safe_date(intent.get("date") or "today")
        else:
            t = text.lower()
            if any(w in t for w in ["fetch", "update"]):
                action = "fetch"
            elif any(w in t for w in ["help", "what can"]):
                action = "help"
            else:
                action = "analyze"

            m = DATE_RE.search(t)
            if m:
                d = m.group(1)
            elif "yesterday" in t:
                d = (date.today() - timedelta(days=1)).isoformat()
            else:
                d = date.today().isoformat()

        logger.info("Stock job %s — action=%s date=%s", job_id, action, d)
        job_manager.update(job_id, "running", f"Stock action: {action} date: {d}")

        # ── Action dispatch ─────────────────────────────────────────────────
        if action == "fetch":
            await self.stock_news_service.update_for_date(d, 20, client_id, job_id)
            result = {"type": "text", "content": f"✅ Stock news fetched for {d}."}
            await sse_manager.publish(client_id, "result", self._sse_payload(result, job_id))
            job_manager.set_result(job_id, result)
            return

        if action == "analyze":
            can_stream = bool(
                self.llm
                and self.llm_enabled
                and self.tool_executor
                and hasattr(self.llm, "stream_stock_analysis_with_tools")
            )
            if can_stream:
                await self._handle_stock_streaming(d, client_id, job_id, sse_manager, job_manager)
            else:
                await self._handle_plain_stock_news(d, client_id, job_id, sse_manager, job_manager)
            return

        # ── Help / unknown ───────────────────────────────────────────────────
        result = {"type": "text", "content": STOCK_HELP_TEXT}
        await sse_manager.publish(client_id, "result", self._sse_payload(result, job_id))
        job_manager.set_result(job_id, result)

    # ------------------------------------------------------------------
    # Private handlers
    # ------------------------------------------------------------------

    async def _handle_stock_streaming(
        self,
        date_str: str,
        client_id: str,
        job_id: str,
        sse_manager: SSEManager,
        job_manager: JobManager,
    ) -> None:
        """Stream the LLM market analysis with trend predictions via SSE."""
        await sse_manager.publish(
            client_id,
            "stream_start",
            json.dumps({"job_id": job_id, "date": date_str}),
        )

        articles: list[dict] = []
        try:
            async for item in self.llm.stream_stock_analysis_with_tools(  # type: ignore
                date_str, self.tool_executor
            ):
                if isinstance(item, str):
                    await sse_manager.publish(client_id, "stream_token", item)
                elif isinstance(item, dict):
                    event = item.get("__event")
                    if event == "articles":
                        articles = item.get("data", [])
        except Exception as exc:
            err_msg = str(exc) or type(exc).__name__
            logger.exception("Stock streaming failed for date=%s job=%s: %s", date_str, job_id, err_msg)
            await sse_manager.publish(
                client_id,
                "stream_end",
                json.dumps({"job_id": job_id, "articles": [], "error": err_msg}),
            )
            job_manager.update(job_id, "failed", f"Stock LLM error: {err_msg}")
            return

        await sse_manager.publish(
            client_id,
            "stream_end",
            json.dumps({"job_id": job_id, "articles": articles}),
        )
        job_manager.set_result(
            job_id, {"type": "stock_stream_summary", "date": date_str, "articles": articles}
        )

    async def _handle_plain_stock_news(
        self,
        date_str: str,
        client_id: str,
        job_id: str,
        sse_manager: SSEManager,
        job_manager: JobManager,
    ) -> None:
        """Fallback (no LLM): fetch and return raw article list."""
        rows = self.stock_news_service.get_news_for_date(date_str)
        if not rows:
            await self.stock_news_service.update_for_date(date_str, 20, client_id, job_id)
            rows = self.stock_news_service.get_news_for_date(date_str)

        items = [
            {"source": s, "title": t, "link": l, "tickers": tk or "", "sentiment": se or ""}
            for s, t, l, tk, se in rows
        ]
        result = {"type": "stock_news", "date": date_str, "items": items}
        await sse_manager.publish(client_id, "result", self._sse_payload(result, job_id))
        job_manager.set_result(job_id, result)
