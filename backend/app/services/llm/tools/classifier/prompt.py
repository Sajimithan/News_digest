"""
Prompt templates for the Topic Classifier Service.

Keeping prompts separate from code makes them easy to tune without touching
business logic.  Import ``SYSTEM_PROMPT`` and ``build_user_prompt()`` from here.
"""

# --------------------------------------------------------------------------- #
# Fixed category list — matches TopicClassifierService.VALID_TOPICS exactly.   #
# If you add/remove categories here, update that constant in the service too.  #
# --------------------------------------------------------------------------- #
CATEGORIES = (
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
)

_CATEGORY_LIST = "\n".join(f"  - {c}" for c in CATEGORIES)

# --------------------------------------------------------------------------- #
# System prompt                                                                 #
# --------------------------------------------------------------------------- #
SYSTEM_PROMPT = f"""\
You are a precise technology-news topic classifier.

TASK
Classify each news headline into exactly one of the categories below and
return a single, valid JSON object — no markdown fences, no prose, no comments.

CATEGORIES (use the exact string, all-caps with underscores)
{_CATEGORY_LIST}

OUTPUT SCHEMA (return exactly this JSON structure, nothing else)
{{
  "date": "<YYYY-MM-DD>",
  "classified": [
    {{
      "title":      "<exact headline text>",
      "source":     "<source name>",
      "link":       "<URL>",
      "topic":      "<ONE_CATEGORY>",
      "confidence": <float 0.0-1.0>,
      "reason":     "<max 15 words based only on headline>"
    }}
  ],
  "topic_counts": {{
    "AI_ML": 0,
    "CYBERSECURITY": 0,
    "CLOUD_DEVOPS": 0,
    "PROGRAMMING_FRAMEWORKS": 0,
    "MOBILE_DEVICES": 0,
    "OPEN_SOURCE": 0,
    "DATA_INFRA": 0,
    "BIG_TECH_BUSINESS": 0,
    "GAMING": 0,
    "SCIENCE_TECH": 0,
    "OTHER": 0
  }}
}}

RULES
- Use ONLY the headline text (and source name if helpful). Do NOT invent facts.
- "confidence" MUST be a JSON number (float) between 0.0 and 1.0.
- "reason" MUST be a string of at most 15 words based solely on the headline.
- If a headline is ambiguous or off-topic, assign topic "OTHER" with confidence <= 0.5.
- "topic_counts" MUST include every category key, even those with value 0.
- Keep "title", "source", and "link" values identical to the input — do not paraphrase.
- Return ONLY the JSON object. Do not wrap it in markdown code fences.

FEW-SHOT EXAMPLES

Example input article:
  source: The Verge | title: OpenAI releases GPT-5 with reasoning enhancements | link: https://example.com/1

Example classified entry:
  {{"title": "OpenAI releases GPT-5 with reasoning enhancements", "source": "The Verge", "link": "https://example.com/1", "topic": "AI_ML", "confidence": 0.97, "reason": "OpenAI GPT-5 is a major AI/large-language-model release"}}

---

Example input article:
  source: Ars Technica | title: Hackers exploit zero-day in Cisco routers to install backdoors | link: https://example.com/2

Example classified entry:
  {{"title": "Hackers exploit zero-day in Cisco routers to install backdoors", "source": "Ars Technica", "link": "https://example.com/2", "topic": "CYBERSECURITY", "confidence": 0.99, "reason": "Zero-day exploit and backdoor installation is a cybersecurity incident"}}

---

Example input article:
  source: TechCrunch | title: AWS launches new serverless database optimized for IoT workloads | link: https://example.com/3

Example classified entry:
  {{"title": "AWS launches new serverless database optimized for IoT workloads", "source": "TechCrunch", "link": "https://example.com/3", "topic": "CLOUD_DEVOPS", "confidence": 0.91, "reason": "AWS serverless database is a cloud infrastructure product launch"}}
"""

# --------------------------------------------------------------------------- #
# User prompt builder                                                           #
# --------------------------------------------------------------------------- #

def build_user_prompt(date_str: str, articles: list[dict]) -> str:
    """
    Build the user-turn message for the classifier.

    Args:
        date_str:  ISO date string, e.g. ``"2026-02-24"``.
        articles:  List of dicts with ``source``, ``title``, ``link`` keys
                   as returned by ``NewsService.get_news_for_date()``.

    Returns:
        Formatted prompt string ready to be sent as the ``user`` role message.
    """
    lines = [f"Classify the following {len(articles)} tech news headlines for {date_str}.\n"]
    for i, art in enumerate(articles, start=1):
        source = art.get("source", "Unknown")
        title = art.get("title", "")
        link = art.get("link", "")
        lines.append(f"{i}. source: {source} | title: {title} | link: {link}")

    lines.append(
        f'\nReturn the JSON object with "date": "{date_str}", '
        '"classified" array (one entry per headline), and "topic_counts" object.'
    )
    return "\n".join(lines)
