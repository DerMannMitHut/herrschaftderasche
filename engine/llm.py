"""Placeholder LLM backend."""

from __future__ import annotations

from .interfaces import LLMBackend


class NoOpLLM(LLMBackend):
    """Backend that returns the command unchanged."""

    def interpret(self, command: str) -> str:
        return command


__all__ = ["NoOpLLM"]

