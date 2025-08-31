"""Input and output backend using the console."""

from __future__ import annotations

from .interfaces import IOBackend


class ConsoleIO(IOBackend):
    """Read from stdin and write to stdout."""

    def get_input(self, prompt: str = "> ") -> str:
        return input(prompt)

    def output(self, text: str) -> None:
        print(text)


__all__ = ["ConsoleIO"]
