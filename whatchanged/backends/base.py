"""Base backend interface for What Changed? vision models."""

from abc import ABC, abstractmethod
from typing import List, Protocol, Tuple, runtime_checkable
import numpy as np
from whatchanged.report import ChangeReport


@runtime_checkable
class Backend(Protocol):
    """Protocol that all vision model backends must satisfy."""

    @property
    def name(self) -> str:
        """Human-readable identifier for the backend (e.g. 'Ollama (gemma4:e4b)')."""
        ...

    def describe_change(
        self,
        before: np.ndarray,
        after: np.ndarray,
        rules: list[str],
    ) -> ChangeReport:
        """Analyzes visual changes between before and after frames and evaluates rules."""
        ...

    def is_available(self) -> Tuple[bool, str]:
        """Returns (is_ready, status_message) for pre-flight checking."""
        ...
