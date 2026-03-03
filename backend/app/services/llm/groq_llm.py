"""
Groq LLM client.

Provides:
  - ``parse_intent()``:  sync, langchain-based intent parser
  - ``summarize()``:     sync, langchain-based batch summarizer (legacy)
  - ``stream_summarize_with_tools()``:  async generator that streams a
      markdown summary using Groq function-calling + SSE token delivery
"""

import json
import logging
import re
import time
from typing import TYPE_CHECKING, AsyncGenerator, Union

import groq as _groq
from groq import AsyncGroq
from langchain_groq import ChatGroq

from app.services.llm.base import Intent, LLMClient
from app.services.llm.tools.definitions import ALL_TOOLS, ALL_STOCK_TOOLS
from app.services.llm.tools.market_analyst.prompt import STOCK_STREAM_SYSTEM, STOCK_INTENT_SYSTEM

if TYPE_CHECKING:
    from app.services.llm.tools.executor import ToolExecutor

logger = logging.getLogger(__name__)


def _parse_wait_seconds(raw: str) -> float:
    """Parse wait time (seconds) from a Groq rate limit error message."""
    # e.g. "Please try again in 1m30.5s"
    m = re.search(r'(\d+)m\s*(\d+(?:\.\d+)?)s', raw)
    if m:
        return int(m.group(1)) * 60 + float(m.group(2))
    # e.g. "2m"
    m = re.search(r'(\d+(?:\.\d+)?)m(?:[^a-z]|$)', raw)
    if m:
        return float(m.group(1)) * 60
    # e.g. "14.413s"
    m = re.search(r'(\d+(?:\.\d+)?)s', raw)
    if m:
        return float(m.group(1))
    return 60.0  # default: retry primary after 1 minute


def _rate_limit_msg(exc: Exception) -> str:
    """Extract a friendly wait-time message from a Groq RateLimitError."""
    raw = str(exc)
    wait_s = _parse_wait_seconds(raw)
    if wait_s >= 60:
        wait = f"{int(wait_s // 60)}m {int(wait_s % 60)}s"
    else:
        wait = f"{wait_s:.0f}s"
    return (
        f"⚠️ Groq rate limit reached on both models — please try again in {wait}.\n"
        "The primary model will automatically be retried once its cooldown expires."
    )

# System prompt used for streaming summaries (tool-calling path)
_STREAM_SYSTEM = """\
You are a precise tech-news analyst.
You have two tools available:

1. `fetch_news_for_date`  — retrieve article headlines for a date, then write a
   concise markdown summary (use this for summarise / show / update_and_show).
2. `classify_news_topics` — classify each headline into a topic category and
   return structured JSON (use this when the user asks to classify or categorise).

For SUMMARY requests:
1. Call `fetch_news_for_date` to retrieve articles.
2. Write a concise markdown summary of the day's most important tech stories.

Formatting rules for summaries:
- First line: one-sentence "headline" overview of the day in **bold**.
- Then a blank line.
- Then 5–8 bullet points (use `- `).
- Each bullet: **Bold topic label** — 1–2 sentence description. *(Source Name)*
- Group bullets by theme when possible (AI, Security, Products, Companies…).
- Do NOT invent details not present in the headlines.
- Do NOT include URLs in the body — they will be shown separately.

For CLASSIFICATION requests:
1. Call `classify_news_topics` with the requested date.
2. When you receive the classification JSON, produce a brief markdown summary
   of the topic breakdown (e.g. "Found 20 articles—  8 AI_ML, 4 CYBERSECURITY…").
   Then tell the user the full structured data is available.
"""


class GroqLLM(LLMClient):
    def __init__(
        self,
        model: str = "llama-3.1-8b-instant",
        stream_model: str = "llama-3.3-70b-versatile",
        fallback_stream_model: str = "llama-3.1-8b-instant",
    ) -> None:
        self.model = model
        self._primary_stream_model = stream_model
        self._fallback_stream_model = fallback_stream_model
        # Timestamp until which the primary stream model is considered rate-limited.
        # 0.0 means the primary is healthy and should be used.
        self._stream_rate_limited_until: float = 0.0
        # Sync client (langchain) — used for intent parsing and legacy summarize
        self.llm = ChatGroq(model=model, temperature=0.0, max_retries=2)
        # Async client (groq SDK) — used for streaming with tool calling
        self._async_client = AsyncGroq()

    @property
    def stream_model(self) -> str:
        """Return the primary model normally; the fallback while rate-limited."""
        if time.time() < self._stream_rate_limited_until:
            return self._fallback_stream_model
        return self._primary_stream_model

    def _on_stream_rate_limited(self, exc: _groq.RateLimitError) -> None:
        """Record a primary-model rate limit and switch to fallback for the cooldown period."""
        wait_s = _parse_wait_seconds(str(exc))
        self._stream_rate_limited_until = time.time() + wait_s
        logger.warning(
            "Groq rate limit on primary stream model '%s' — "
            "falling back to '%s' for %.0f s.",
            self._primary_stream_model,
            self._fallback_stream_model,
            wait_s,
        )

    def parse_intent(self, user_message: str) -> Intent:
        """
        Convert messy human text into a small JSON instruction.
        Force JSON output, parse it, and sanitize fields.
        """
        system = (
            "You are an intent parser for a tech news chatbot.\n"
            "Return ONLY valid JSON, no extra text.\n"
            "Schema:\n"
            "{"
            '  "action": "update"|"show"|"update_and_show"|"summarize"|"classify"|"help",'
            '  "date": "today" or "YYYY-MM-DD" or "yesterday",'
            '  "limit": number'
            "}\n"
            "Rules:\n"
            "- 'today update' -> action=update_and_show date=today\n"
            "- 'today' -> action=show date=today\n"
            "- 'yesterday update' -> action=update_and_show date=yesterday\n"
            "- 'yesterday' -> action=show date=yesterday\n"
            "- 'update' only -> action=update\n"
            "- 'summarize' -> action=summarize date=today unless a date is given\n"
            "- 'classify' / 'categorize' / 'group by topic' -> action=classify date=today unless a date is given\n"
            "- If limit not mentioned, set limit to 10\n"
        )

        msg = self.llm.invoke(
            [
                ("system", system),
                ("human", user_message),
            ]
        )

        text = (msg.content or "").strip()

        try:
            data = json.loads(text)
        except Exception:
            # Model returned invalid JSON
            return {"action": "help", "date": "today", "limit": 10}

        # Safe defaults
        action = data.get("action") or "help"
        date = data.get("date") or "today"

        raw_limit = data.get("limit", 10)
        try:
            limit = int(raw_limit) if raw_limit is not None else 10
        except Exception:
            limit = 10

        # Clamp limit
        if limit < 1:
            limit = 1
        if limit > 30:
            limit = 30

        return {"action": action, "date": date, "limit": limit}

    def summarize(self, date: str, headlines: list[tuple[str, str, str]]) -> str:
        items = "\n".join([f"- ({s}) {t}" for s, t, _ in headlines[:15]])

        prompt = (
            f"Summarize the most important tech news for {date}.\n"
            "Use simple English.\n"
            "Give 5-8 bullet points.\n"
            "Do NOT invent facts beyond the headlines.\n\n"
            f"Headlines:\n{items}"
        )

        msg = self.llm.invoke(
            [
                ("system", "You are a careful tech news summarizer."),
                ("human", prompt),
            ]
        )
        return (msg.content or "").strip()

    async def stream_summarize_with_tools(
        self,
        date_str: str,
        executor: "ToolExecutor",
    ) -> AsyncGenerator[Union[str, dict], None]:
        """
        Stream a markdown summary for ``date_str`` using Groq tool-calling.

        The model is given the ``fetch_news_for_date`` tool.  It calls the tool,
        receives the articles JSON, and then streams its summary token by token.

        Yields:
            str  — a raw text/markdown token to display immediately.
            dict — a control message, one of:
                   {"__event": "articles", "data": [{source, title, link}…]}
                   {"__event": "done"}
        """
        # ── If the primary is already rate-limited, skip tool calling entirely ──
        if self.stream_model == self._fallback_stream_model:
            async for item in self._stream_summary_no_tools(date_str, executor):
                yield item
            return

        messages: list[dict] = [
            {"role": "system", "content": _STREAM_SYSTEM},
            {
                "role": "user",
                "content": (
                    f"Please summarize the most important tech news for {date_str}. "
                    "Use the fetch_news_for_date tool to retrieve the articles first."
                ),
            },
        ]

        # ── First pass: let model decide to call the fetch_news tool ─────────
        try:
            first_response = await self._async_client.chat.completions.create(
                model=self.stream_model,
                messages=messages,
                tools=ALL_TOOLS,
                tool_choice="auto",
            )
        except _groq.RateLimitError as exc:
            self._on_stream_rate_limited(exc)
            # Fallback model doesn't support tool calling reliably — bypass it
            async for item in self._stream_summary_no_tools(date_str, executor):
                yield item
            return

        assistant_msg = first_response.choices[0].message

        if not assistant_msg.tool_calls:
            # Model skipped the tool — stream whatever it said and exit
            logger.warning("Model produced no tool calls for date=%s; streaming raw reply.", date_str)
            content = assistant_msg.content or ""
            if content:
                yield content
            yield {"__event": "done"}
            return

        # ── Append assistant's tool-call turn to history ────────────────────
        messages.append({
            "role": "assistant",
            "content": assistant_msg.content or "",
            "tool_calls": [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments,
                    },
                }
                for tc in assistant_msg.tool_calls
            ],
        })

        # ── Execute every tool call and collect articles ─────────────────────
        articles_data: list[dict] = []
        for tool_call in assistant_msg.tool_calls:
            result_json = await executor.execute(tool_call)
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "name": tool_call.function.name,
                "content": result_json,
            })
            try:
                parsed = json.loads(result_json)
                articles_data.extend(parsed.get("articles", []))
            except json.JSONDecodeError:
                pass

        # Yield articles so the caller can pass them to the frontend
        yield {"__event": "articles", "data": articles_data}

        # ── Second pass: stream the final markdown summary ───────────────────
        try:
            stream = await self._async_client.chat.completions.create(
                model=self.stream_model,
                messages=messages,
                stream=True,
            )
        except _groq.RateLimitError as exc:
            self._on_stream_rate_limited(exc)
            # Articles already yielded — rebuild a clean no-tools prompt and stream
            lines = [
                f"- ({a.get('source', '')}) {a.get('title', '')}"
                for a in articles_data[:15]
            ]
            articles_text = "\n".join(lines) if lines else "No articles found."
            fallback_messages = [
                {"role": "system", "content": _STREAM_SYSTEM},
                {
                    "role": "user",
                    "content": (
                        f"Please summarize the most important tech news for {date_str}.\n\n"
                        f"Here are the articles:\n{articles_text}"
                    ),
                },
            ]
            try:
                stream = await self._async_client.chat.completions.create(
                    model=self._fallback_stream_model,
                    messages=fallback_messages,
                    stream=True,
                )
            except _groq.RateLimitError as exc2:
                raise RuntimeError(_rate_limit_msg(exc2)) from exc2

        async for chunk in stream:
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta.content
            if delta:
                yield delta

        yield {"__event": "done"}

    async def _stream_summary_no_tools(
        self,
        date_str: str,
        executor: "ToolExecutor",
    ) -> AsyncGenerator[Union[str, dict], None]:
        """
        Fallback streaming path for news summaries.

        Fetches articles directly (no model-driven tool call) and streams the
        summary without sending ``tools`` to the API.  Used when the fallback
        model (llama-3.1-8b-instant) is active, because smaller models do not
        reliably support Groq tool calling and may generate invalid tool names.
        """
        result_json = await executor._fetch_news_for_date(date=date_str)
        articles_data: list[dict] = []
        try:
            parsed = json.loads(result_json)
            articles_data = parsed.get("articles", [])
        except Exception:
            pass

        yield {"__event": "articles", "data": articles_data}

        lines = [
            f"- ({a.get('source', '')}) {a.get('title', '')}"
            for a in articles_data[:15]
        ]
        articles_text = "\n".join(lines) if lines else "No articles found for this date."

        messages: list[dict] = [
            {"role": "system", "content": _STREAM_SYSTEM},
            {
                "role": "user",
                "content": (
                    f"Please summarize the most important tech news for {date_str}.\n\n"
                    f"Here are the articles:\n{articles_text}"
                ),
            },
        ]

        try:
            stream = await self._async_client.chat.completions.create(
                model=self._fallback_stream_model,
                messages=messages,
                stream=True,
            )
        except _groq.RateLimitError as exc:
            raise RuntimeError(_rate_limit_msg(exc)) from exc

        async for chunk in stream:
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta.content
            if delta:
                yield delta

        yield {"__event": "done"}

    # ------------------------------------------------------------------
    # Stock / market analysis methods
    # ------------------------------------------------------------------

    def parse_stock_intent(self, user_message: str) -> dict:
        """
        Parse a stock/market chatbot message → ``{"action": "analyze"|"fetch"|"help", "date": "YYYY-MM-DD"}``.
        """
        from app.utils.date_helpers import resolve_date as _resolve_date

        msg = self.llm.invoke(
            [
                ("system", STOCK_INTENT_SYSTEM),
                ("human", user_message),
            ]
        )
        text = (msg.content or "").strip()
        try:
            data = json.loads(text)
        except Exception:
            return {"action": "analyze", "date": "today"}

        action   = data.get("action") or "analyze"
        raw_date = data.get("date") or "today"
        try:
            date_str = _resolve_date(raw_date)
        except Exception:
            date_str = _resolve_date("today")

        return {"action": action, "date": date_str}

    async def stream_stock_analysis_with_tools(
        self,
        date_str: str,
        executor: "ToolExecutor",
    ) -> AsyncGenerator[Union[str, dict], None]:
        """
        Stream a two-section market analysis for ``date_str``:
          1. Market Summary (news bullets)
          2. Future Trend Prediction (sentiment, sectors, risks, outlook)

        Yields:
            str  — markdown token.
            dict — ``{"__event": "articles"|"done", "data": [...]}``
        """
        # ── If the primary is already rate-limited, skip tool calling entirely ──
        if self.stream_model == self._fallback_stream_model:
            async for item in self._stream_stock_no_tools(date_str, executor):
                yield item
            return

        messages: list[dict] = [
            {"role": "system", "content": STOCK_STREAM_SYSTEM},
            {
                "role": "user",
                "content": (
                    f"Analyze the stock market and financial news for {date_str}. "
                    "Use fetch_stock_news_for_date to retrieve articles first, "
                    "then write the full Market Summary and Future Trend Prediction."
                ),
            },
        ]

        # ── First pass: model calls fetch_stock_news_for_date ────────────────
        try:
            first_response = await self._async_client.chat.completions.create(
                model=self.stream_model,
                messages=messages,
                tools=ALL_STOCK_TOOLS,
                tool_choice="auto",
            )
        except _groq.RateLimitError as exc:
            self._on_stream_rate_limited(exc)
            # Fallback model doesn't support tool calling reliably — bypass it
            async for item in self._stream_stock_no_tools(date_str, executor):
                yield item
            return

        assistant_msg = first_response.choices[0].message

        if not assistant_msg.tool_calls:
            logger.warning(
                "Stock model: no tool calls for date=%s; streaming raw reply.", date_str
            )
            content = assistant_msg.content or ""
            if content:
                yield content
            yield {"__event": "done"}
            return

        messages.append({
            "role": "assistant",
            "content": assistant_msg.content or "",
            "tool_calls": [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {"name": tc.function.name, "arguments": tc.function.arguments},
                }
                for tc in assistant_msg.tool_calls
            ],
        })

        # ── Execute tool calls, collect articles ─────────────────────────────
        articles_data: list[dict] = []
        for tool_call in assistant_msg.tool_calls:
            result_json = await executor.execute(tool_call)
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "name": tool_call.function.name,
                "content": result_json,
            })
            try:
                parsed = json.loads(result_json)
                articles_data.extend(parsed.get("articles", []))
            except Exception:
                pass

        yield {"__event": "articles", "data": articles_data}

        # ── Second pass: stream the full analysis ─────────────────────────────
        try:
            stock_stream = await self._async_client.chat.completions.create(
                model=self.stream_model,
                messages=messages,
                stream=True,
            )
        except _groq.RateLimitError as exc:
            self._on_stream_rate_limited(exc)
            # Articles already yielded — rebuild a clean no-tools prompt and stream
            lines = [
                f"- ({a.get('source', '')}) {a.get('title', '')}"
                for a in articles_data[:15]
            ]
            articles_text = "\n".join(lines) if lines else "No articles found."
            fallback_messages = [
                {"role": "system", "content": STOCK_STREAM_SYSTEM},
                {
                    "role": "user",
                    "content": (
                        f"Analyze the stock market and financial news for {date_str}.\n\n"
                        f"Here are the articles:\n{articles_text}\n\n"
                        "Write the full Market Summary and Future Trend Prediction."
                    ),
                },
            ]
            try:
                stock_stream = await self._async_client.chat.completions.create(
                    model=self._fallback_stream_model,
                    messages=fallback_messages,
                    stream=True,
                )
            except _groq.RateLimitError as exc2:
                raise RuntimeError(_rate_limit_msg(exc2)) from exc2

        async for chunk in stock_stream:
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta.content
            if delta:
                yield delta

        yield {"__event": "done"}

    async def _stream_stock_no_tools(
        self,
        date_str: str,
        executor: "ToolExecutor",
    ) -> AsyncGenerator[Union[str, dict], None]:
        """
        Fallback streaming path for stock analysis.

        Fetches articles directly (no model-driven tool call) and streams the
        analysis without sending ``tools`` to the API.  Used when the fallback
        model (llama-3.1-8b-instant) is active.
        """
        result_json = await executor._fetch_stock_news_for_date(date=date_str)
        articles_data: list[dict] = []
        try:
            parsed = json.loads(result_json)
            articles_data = parsed.get("articles", [])
        except Exception:
            pass

        yield {"__event": "articles", "data": articles_data}

        lines = [
            f"- ({a.get('source', '')}) {a.get('title', '')}"
            for a in articles_data[:15]
        ]
        articles_text = "\n".join(lines) if lines else "No articles found for this date."

        messages: list[dict] = [
            {"role": "system", "content": STOCK_STREAM_SYSTEM},
            {
                "role": "user",
                "content": (
                    f"Analyze the stock market and financial news for {date_str}.\n\n"
                    f"Here are the articles:\n{articles_text}\n\n"
                    "Write the full Market Summary and Future Trend Prediction."
                ),
            },
        ]

        try:
            stream = await self._async_client.chat.completions.create(
                model=self._fallback_stream_model,
                messages=messages,
                stream=True,
            )
        except _groq.RateLimitError as exc:
            raise RuntimeError(_rate_limit_msg(exc)) from exc

        async for chunk in stream:
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta.content
            if delta:
                yield delta

        yield {"__event": "done"}
