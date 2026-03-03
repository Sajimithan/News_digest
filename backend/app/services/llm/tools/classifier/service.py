"""
Topic Classifier Service.

Uses Groq (fast model) to classify each fetched news headline into a fixed
set of technology topic categories and returns a structured JSON result.

Usage::

    svc = TopicClassifierService(news_service)
    result = await svc.classify_by_date("2026-02-24", limit=20)

The returned dict matches the output schema defined in the prompt module.
"""

import json
import logging
import re
from typing import TYPE_CHECKING

from groq import AsyncGroq

from app.exceptions.errors import DataNotFoundError, ProviderError
from app.services.llm.tools.classifier.prompt import (
    SYSTEM_PROMPT,
    build_user_prompt,
)

if TYPE_CHECKING:
    from app.services.news_service import NewsService

logger = logging.getLogger(__name__)

# --------------------------------------------------------------------------- #
# Constants                                                                     #
# --------------------------------------------------------------------------- #

VALID_TOPICS: frozenset[str] = frozenset({
    "AI_ML",
    "CYBERSECURITY",
    "CLOUD_DEVOPS",
    "PROGRAMMING_FRAMEWORKS",
    "MOBILE_DEVICES",
    "OPEN_SOURCE",
    "DATA_INFRA",
    "BIG_TECH_BUSINESS",
    "GAMING",
    "SCIENCE_TECH",
    "OTHER",
})

# Regex to extract a JSON object from a response that may contain prose/fences
_JSON_RE = re.compile(r"\{[\s\S]*\}", re.DOTALL)


class TopicClassifierService:
    """
    Classifies fetched tech-news headlines into fixed topic categories.

    Constructor dependencies:
        news_service:  Used to load cached articles and, if needed, trigger
                       a live fetch when the cache is empty for a given date.
        model:         Groq model name to use for classification.
                       Defaults to the fast/cheap ``llama-3.1-8b-instant``.

    The Groq API key is read automatically from the ``GROQ_API_KEY``
    environment variable (same behaviour as the existing GroqLLM class).
    """

    def __init__(
        self,
        news_service: "NewsService",
        model: str = "llama-3.1-8b-instant",
    ) -> None:
        self.news_service = news_service
        self.model = model
        # AsyncGroq() reads GROQ_API_KEY from env — same as existing GroqLLM
        self._client = AsyncGroq()

    # ---------------------------------------------------------------------- #
    # Public API                                                               #
    # ---------------------------------------------------------------------- #

    async def classify_by_date(self, date_str: str, limit: int = 20) -> dict:
        """
        Classify tech-news headlines for ``date_str`` and return a JSON-ready dict.

        Args:
            date_str: ISO-8601 date string, e.g. ``"2026-02-24"``.
                      Relative strings ("today", "yesterday") should be
                      resolved *before* calling this method — use
                      :func:`app.utils.date_helpers.resolve_date`.
            limit:    Maximum number of articles to classify (default 20).

        Returns:
            Dict matching the output schema::

                {
                    "date": "YYYY-MM-DD",
                    "classified": [{"title", "source", "link", "topic",
                                    "confidence", "reason"}, ...],
                    "topic_counts": {"AI_ML": int, ...}
                }

        Raises:
            DataNotFoundError: No articles available for ``date_str`` even
                               after attempting a live fetch.
            ProviderError:     Groq API returned an error or unparseable output.
        """
        # ── 1. Load articles from cache ──────────────────────────────────────
        articles = self._load_articles(date_str, limit)

        # ── 2. If cache empty, trigger live fetch then retry once ────────────
        if not articles:
            logger.info(
                "TopicClassifier: cache empty for %s — triggering live fetch", date_str
            )
            await self.news_service.update_for_date(
                date_str, limit, client_id="", job_id="__classifier_fetch__"
            )
            articles = self._load_articles(date_str, limit)

        if not articles:
            raise DataNotFoundError(
                f"No tech news articles found for {date_str}. "
                "Try 'update news' first to fetch articles for this date."
            )

        logger.info(
            "TopicClassifier: classifying %d articles for %s", len(articles), date_str
        )

        # ── 3. Call Groq ─────────────────────────────────────────────────────
        raw = await self._call_groq(date_str, articles)

        # ── 4. Parse and sanitize the response ───────────────────────────────
        return self._parse_and_sanitize(raw, date_str)

    # ---------------------------------------------------------------------- #
    # Private helpers                                                          #
    # ---------------------------------------------------------------------- #

    def _load_articles(self, date_str: str, limit: int) -> list[dict]:
        """
        Read articles from the DB cache and normalise them to dicts.

        Returns a list of ``{"source", "title", "link"}`` dicts.
        """
        rows = self.news_service.get_news_for_date(date_str, limit=limit)
        return [{"source": s, "title": t, "link": lnk} for s, t, lnk in rows]

    async def _call_groq(self, date_str: str, articles: list[dict]) -> str:
        """
        Send the classification request to Groq and return the raw response text.

        Raises:
            ProviderError: If the Groq API raises any exception.
        """
        user_prompt = build_user_prompt(date_str, articles)

        try:
            response = await self._client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.0,   # deterministic — JSON output
                max_tokens=4096,
            )
        except Exception as exc:
            raise ProviderError(
                f"Groq API error during topic classification: {exc}",
                provider="Groq",
            ) from exc

        content = ""
        if response.choices:
            content = (response.choices[0].message.content or "").strip()

        if not content:
            raise ProviderError(
                "Groq returned an empty response for topic classification.",
                provider="Groq",
            )

        return content

    def _parse_and_sanitize(self, raw: str, date_str: str) -> dict:
        """
        Parse the Groq response into a validated, sanitized classification dict.

        Handles malformed output gracefully:
        - Strips markdown code fences
        - Uses regex fallback to extract JSON from extra prose
        - Clamps confidence to [0.0, 1.0]
        - Maps unknown topics to "OTHER"
        - Ensures topic_counts includes all 11 categories (missing ones → 0)

        Raises:
            ProviderError: If the response cannot be parsed as JSON at all.
        """
        # ── Strip markdown code fences if present ────────────────────────────
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```[a-zA-Z]*\n?", "", cleaned)
            cleaned = re.sub(r"```$", "", cleaned).strip()

        # ── Attempt direct JSON parse ─────────────────────────────────────────
        data: dict | None = None
        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError:
            # ── Regex fallback: extract first {...} block ──────────────────
            m = _JSON_RE.search(cleaned)
            if m:
                try:
                    data = json.loads(m.group(0))
                except json.JSONDecodeError:
                    pass

        if data is None:
            logger.error(
                "TopicClassifier: could not parse Groq response as JSON.\n%s", raw[:500]
            )
            raise ProviderError(
                "Groq returned an unparseable response for topic classification. "
                "The model output was not valid JSON.",
                provider="Groq",
            )

        # ── Sanitize each classified entry ────────────────────────────────────
        sanitized: list[dict] = []
        for entry in data.get("classified", []):
            if not isinstance(entry, dict):
                continue

            topic = str(entry.get("topic") or "OTHER").strip().upper()
            if topic not in VALID_TOPICS:
                logger.debug(
                    "TopicClassifier: unknown topic %r → mapped to OTHER", topic
                )
                topic = "OTHER"

            raw_conf = entry.get("confidence")
            try:
                conf = float(raw_conf) if raw_conf is not None else 0.5
            except (ValueError, TypeError):
                conf = 0.5
            conf = max(0.0, min(1.0, conf))  # clamp to [0.0, 1.0]

            reason = str(entry.get("reason") or "").strip()
            # Truncate reason to 100 chars as a hard safety rail
            reason = reason[:100]

            sanitized.append({
                "title":      str(entry.get("title") or ""),
                "source":     str(entry.get("source") or ""),
                "link":       str(entry.get("link") or ""),
                "topic":      topic,
                "confidence": round(conf, 4),
                "reason":     reason,
            })

        # ── Build topic_counts with all categories defaulting to 0 ───────────
        counts: dict[str, int] = {t: 0 for t in VALID_TOPICS}
        for entry in sanitized:
            counts[entry["topic"]] = counts.get(entry["topic"], 0) + 1

        return {
            "date":         date_str,
            "classified":   sanitized,
            "topic_counts": counts,
        }
