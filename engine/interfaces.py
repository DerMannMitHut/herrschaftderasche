"""Protocol interfaces for engine backends."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:  # pragma: no cover - typing only
    from .language import LanguageManager
    from .persistence import LogEntry
    from .world import World


@runtime_checkable
class IOBackend(Protocol):
    """Interface for input and output backends."""

    def get_input(self, prompt: str = "> ") -> str:  # pragma: no cover - interface
        """Return user input for the given prompt."""
        ...

    def output(self, text: str) -> None:  # pragma: no cover - interface
        """Display ``text`` to the user."""
        ...


@runtime_checkable
class LLMBackend(Protocol):
    """Interface for language model helpers."""

    def interpret(self, command: str) -> str:  # pragma: no cover - interface
        """Return a normalized version of ``command``."""
        ...

    def set_context(
        self,
        world: World,
        language: LanguageManager,
        log: list[LogEntry],
    ) -> None:  # pragma: no cover - interface
        """Provide world, language manager and log for context-aware interpretation."""
        ...


__all__ = ["IOBackend", "LLMBackend"]
