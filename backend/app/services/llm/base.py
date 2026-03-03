from typing import Protocol, TypedDict, Optional, Literal

Action = Literal["update", "show", "update_and_show", "summarize", "help"]

class Intent(TypedDict, total=False):
    action: Action
    date: str          # "today" or "YYYY-MM-DD"
    limit: int

class LLMClient(Protocol):
    def parse_intent(self, user_message: str) -> Intent: ...
    def summarize(self, date: str, headlines: list[tuple[str, str, str]]) -> str: ...
