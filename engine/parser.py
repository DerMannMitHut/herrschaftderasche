"""Simple command parser."""

def parse(command: str) -> str:
    """Return a normalized command string."""
    return command.strip().lower()
