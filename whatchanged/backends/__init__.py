"""Backend registry and factory for What Changed?."""

from typing import Optional
from whatchanged.backends.base import Backend
from whatchanged.backends.ollama_backend import OllamaBackend
from whatchanged.backends.gemini_backend import GeminiBackend
from whatchanged.config import Settings
from whatchanged.report import ChangeReport


class FakeBackend(Backend):
    """Deterministic fake backend for headless unit tests and offline simulations."""

    def __init__(
        self,
        canned_changes: Optional[list[str]] = None,
        canned_rule_ids: Optional[list[int]] = None,
        should_raise: bool = False,
        parse_error: bool = False,
    ) -> None:
        self.canned_changes = canned_changes if canned_changes is not None else ["Object added"]
        self.canned_rule_ids = canned_rule_ids if canned_rule_ids is not None else []
        self.should_raise = should_raise
        self.parse_error = parse_error
        self.calls = 0

    @property
    def name(self) -> str:
        return "FakeBackend (Testing)"

    def is_available(self) -> tuple[bool, str]:
        return True, "FakeBackend is always ready."

    def describe_change(self, before, after, rules: list[str]) -> ChangeReport:
        self.calls += 1
        if self.should_raise:
            raise RuntimeError("Fake backend simulated execution failure")
        if self.parse_error:
            return ChangeReport(changes=[], triggered_rule_ids=[], raw="Invalid response", parse_error=True)
        return ChangeReport(
            changes=list(self.canned_changes),
            triggered_rule_ids=list(self.canned_rule_ids),
            raw="Fake JSON OK",
            parse_error=False,
        )


def get_backend(name: str, settings: Settings) -> Backend:
    """Instantiates the specified backend provider ('ollama', 'gemini', or 'fake')."""
    lower = (name or settings.backend).lower()
    if "fake" in lower:
        return FakeBackend()
    if "gemini" in lower:
        return GeminiBackend(settings)
    return OllamaBackend(settings)


__all__ = ["Backend", "OllamaBackend", "GeminiBackend", "FakeBackend", "get_backend"]
