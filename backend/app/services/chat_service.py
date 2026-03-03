"""
Chat service — handles all user messages and dispatches job actions.

Intent flow:
  1. Parse user text → (action, date, limit)
  2. For ``show`` / ``update_and_show`` with LLM enabled → stream a markdown
     summary with live token delivery via SSE (``stream_start`` /
     ``stream_token`` / ``stream_end`` events).
  3. Without LLM, or for other actions, return plain news lists / text.
"""

import json
import logging
import re
from datetime import date, timedelta
from typing import TYPE_CHECKING

from app.services.async_utils import to_thread
from app.services.job_manager import JobManager
from app.services.llm.base import LLMClient
from app.services.news_service import NewsService
from app.services.sse_manager import SSEManager
from app.utils.date_helpers import resolve_date

if TYPE_CHECKING:
    from app.services.llm.tools.executor import ToolExecutor
    from app.services.llm.tools.classifier.service import TopicClassifierService

logger = logging.getLogger(__name__)

DATE_RE = re.compile(r"\b(\d{4}-\d{2}-\d{2})\b")


class ChatService:
    def __init__(
        self,
        news_service: NewsService,
        llm: LLMClient | None = None,
        llm_enabled: bool = False,
        tool_executor: "ToolExecutor | None" = None,
        topic_classifier_service: "TopicClassifierService | None" = None,
    ) -> None:
        self.news_service = news_service
        self.llm = llm
        self.llm_enabled = llm_enabled
        self.tool_executor = tool_executor
        self.topic_classifier_service = topic_classifier_service

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _resolve_date(self, d: str) -> str:
        return resolve_date(d)

    @staticmethod
    def _safe_int(value, default: int = 10) -> int:
        try:
            return int(value) if value is not None else default
        except Exception:
            return default

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
        """Process a user message, publish SSE events, and record the job result."""
        text = (message or "").strip()

        # ── Intent parsing ───────────────────────────────────────────────────
        if self.llm and self.llm_enabled:
            intent = await to_thread(self.llm.parse_intent, text)
            action = intent.get("action") or "help"
            d = self._resolve_date(intent.get("date") or "today")
            limit = self._safe_int(intent.get("limit", 10))
        else:
            t = text.lower()
            if "today update" in t:
                action, d, limit = "update_and_show", date.today().isoformat(), 10
            elif "yesterday update" in t:
                action, d, limit = "update_and_show", (date.today() - timedelta(days=1)).isoformat(), 10
            elif "update" in t:
                action, d, limit = "update", date.today().isoformat(), 10
            elif "yesterday" in t:
                action, d, limit = "show", (date.today() - timedelta(days=1)).isoformat(), 10
            elif "today" in t:
                action, d, limit = "show", date.today().isoformat(), 10
            else:
                m = DATE_RE.search(t)
                if m:
                    action, d, limit = "show", m.group(1), 10
                elif re.search(r"classif|categoris|categoriz|group.{0,15}topic", t):
                    action, d, limit = "classify", date.today().isoformat(), 20
                else:
                    action, d, limit = "help", date.today().isoformat(), 10

        logger.info("Job %s — action=%s date=%s limit=%d", job_id, action, d, limit)
        job_manager.update(job_id, "running", f"Action: {action} date: {d}")

        # ── Action handlers ──────────────────────────────────────────────────

        if action == "update":
            await self.news_service.update_for_date(d, limit, client_id, job_id)
            result = {"type": "text", "content": f"✅ Update complete for {d}."}
            await sse_manager.publish(client_id, "result", self._sse_payload(result, job_id))
            job_manager.set_result(job_id, result)
            return

        if action in ("show", "update_and_show", "summarize"):
            can_stream = bool(
                self.llm
                and self.llm_enabled
                and self.tool_executor
                and hasattr(self.llm, "stream_summarize_with_tools")
            )
            if can_stream:
                await self._handle_streaming_summary(d, client_id, job_id, sse_manager, job_manager)
            else:
                await self._handle_plain_news(d, limit, client_id, job_id, sse_manager, job_manager)
            return

        if action == "classify":
            await self._handle_classification(d, limit, client_id, job_id, sse_manager, job_manager)
            return

        # ── Help / unknown ───────────────────────────────────────────────────
        result = {
            "type": "text",
            "content": (
                "Try:\n"
                "- **update news** — fetch today's articles\n"
                "- **today** / **yesterday** — summarise that day\n"
                "- **today update** — fetch + summarise today\n"
                "- **2026-02-18** — summarise a specific date\n"
            ),
        }
        await sse_manager.publish(client_id, "result", self._sse_payload(result, job_id))
        job_manager.set_result(job_id, result)

    # ------------------------------------------------------------------
    # Private handlers
    # ------------------------------------------------------------------

    async def _handle_streaming_summary(
        self,
        date_str: str,
        client_id: str,
        job_id: str,
        sse_manager: SSEManager,
        job_manager: JobManager,
    ) -> None:
        """
        Stream an LLM-generated markdown summary via SSE tokens.

        SSE events emitted:
            stream_start  — ``{"job_id": "...", "date": "..."}``
            stream_token  — raw token string (no wrapper for max throughput)
            stream_end    — ``{"job_id": "...", "articles": [{...}, ...]}``
        """
        await sse_manager.publish(
            client_id,
            "stream_start",
            json.dumps({"job_id": job_id, "date": date_str}),
        )

        articles: list[dict] = []
        try:
            async for item in self.llm.stream_summarize_with_tools(  # type: ignore[union-attr]
                date_str, self.tool_executor
            ):
                if isinstance(item, str):
                    # Text token — push immediately for typewriter effect
                    await sse_manager.publish(client_id, "stream_token", item)
                elif isinstance(item, dict):
                    event = item.get("__event")
                    if event == "articles":
                        articles = item.get("data", [])
                    # "done" is the last item — handled by loop exit

        except Exception as exc:
            err_msg = str(exc) or type(exc).__name__
            logger.exception("Streaming summary failed for date=%s job=%s: %s", date_str, job_id, err_msg)
            await sse_manager.publish(
                client_id,
                "stream_end",
                json.dumps({"job_id": job_id, "articles": [], "error": err_msg}),
            )
            job_manager.update(job_id, "failed", f"LLM streaming error: {err_msg}")
            return

        await sse_manager.publish(
            client_id,
            "stream_end",
            json.dumps({"job_id": job_id, "articles": articles}),
        )
        result = {"type": "stream_summary", "date": date_str, "articles": articles}
        job_manager.set_result(job_id, result)

    async def _handle_plain_news(
        self,
        date_str: str,
        limit: int,
        client_id: str,
        job_id: str,
        sse_manager: SSEManager,
        job_manager: JobManager,
    ) -> None:
        """
        Fallback when LLM streaming is not available.
        Fetches articles from cache (or live) and returns a plain list.
        """
        rows = self.news_service.get_news_for_date(date_str, limit=limit)
        if len(rows) < limit:
            await self.news_service.update_for_date(date_str, limit, client_id, job_id)
            rows = self.news_service.get_news_for_date(date_str, limit=limit)

        result = {"type": "news", "date": date_str, "items": rows}
        await sse_manager.publish(client_id, "result", self._sse_payload(result, job_id))
        job_manager.set_result(job_id, result)

    async def _handle_classification(
        self,
        date_str: str,
        limit: int,
        client_id: str,
        job_id: str,
        sse_manager: SSEManager,
        job_manager: JobManager,
    ) -> None:
        """
        Classify news headlines for ``date_str`` and publish the result over SSE.

        SSE events emitted:
            stream_start  — ``{"job_id": "...", "date": "..."}``
            stream_token  — plain-text progress updates ("Loading headlines…", etc.)
            result        — full classification JSON wrapped in _sse_payload
            stream_end    — ``{"job_id": "...", "articles": []}``
        """
        await sse_manager.publish(
            client_id,
            "stream_start",
            json.dumps({"job_id": job_id, "date": date_str}),
        )

        if self.topic_classifier_service is None:
            err_msg = "Topic classifier service is not available."
            logger.error("_handle_classification: %s job=%s", err_msg, job_id)
            await sse_manager.publish(client_id, "stream_token", err_msg)
            await sse_manager.publish(
                client_id, "stream_end", json.dumps({"job_id": job_id, "articles": [], "error": err_msg})
            )
            job_manager.update(job_id, "failed", err_msg)
            return

        try:
            await sse_manager.publish(client_id, "stream_token", f"Loading headlines for {date_str}…")
            await sse_manager.publish(client_id, "stream_token", "Classifying with Groq…")

            classification = await self.topic_classifier_service.classify_by_date(
                date_str, limit=limit
            )

            # Publish the full structured result
            result = {"type": "classification", **classification}
            await sse_manager.publish(client_id, "result", self._sse_payload(result, job_id))
            job_manager.set_result(job_id, result)

            counts = classification.get("topic_counts", {})
            top_topics = sorted(counts.items(), key=lambda x: x[1], reverse=True)
            summary_line = "  ".join(
                f"{t}: {c}" for t, c in top_topics if c > 0
            ) or "no topics found"
            await sse_manager.publish(
                client_id, "stream_token",
                f" Classified {len(classification.get('classified', []))} articles — {summary_line}"
            )

        except Exception as exc:
            err_msg = str(exc) or type(exc).__name__
            logger.exception(
                "Classification failed for date=%s job=%s: %s", date_str, job_id, err_msg
            )
            await sse_manager.publish(client_id, "stream_token", f"❌ Classification failed: {err_msg}")
            await sse_manager.publish(
                client_id, "stream_end",
                json.dumps({"job_id": job_id, "articles": [], "error": err_msg}),
            )
            job_manager.update(job_id, "failed", f"Classification error: {err_msg}")
            return

        await sse_manager.publish(
            client_id, "stream_end", json.dumps({"job_id": job_id, "articles": []})
        )
