"""Simple input and output helpers."""

def get_input(prompt: str = "> ") -> str:
    return input(prompt)

def output(text: str) -> None:
    print(text)
