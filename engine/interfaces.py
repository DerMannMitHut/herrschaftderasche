"""Protocol interfaces for engine backends."""

from __future__ import annotations

from typing import Protocol, runtime_checkable


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


__all__ = ["IOBackend", "LLMBackend"]

