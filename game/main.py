"""Entry point for running the sample adventure."""

import argparse
import sys
from pathlib import Path

from engine.game import run
from engine.llm import OllamaLLM


def run_cli() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--language", default="de")
    parser.add_argument(
        "--debug",
        nargs="?",
        const=True,
        metavar="FILE",
        help=(
            "Enable debug mode; optionally provide FILE to tee STDOUT to it and redirect STDERR only to it"
        ),
    )
    parser.add_argument(
        "--llm",
        action="store_true",
        help="Enable LLM (Ollama) for command interpretation",
    )
    parser.add_argument(
        "--llm-model",
        dest="llm_model",
        default=None,
        help="Override OLLAMA_MODEL (e.g., mistral, llama3)",
    )
    parser.add_argument(
        "--llm-base-url",
        dest="llm_base_url",
        default=None,
        help="Override OLLAMA_BASE_URL (e.g., http://localhost:11434)",
    )
    parser.add_argument(
        "--llm-timeout",
        dest="llm_timeout",
        type=int,
        default=None,
        help="Override request timeout in seconds (default 30)",
    )
    args = parser.parse_args()
    data_path = Path(__file__).parent.parent / "data" / args.language / f"world.{args.language}.yaml"
    llm = (
        OllamaLLM(
            model=args.llm_model,
            base_url=args.llm_base_url,
            timeout=args.llm_timeout,
            check_model=True,
        )
        if args.llm
        else None
    )
    debug_opt = args.debug

    if isinstance(debug_opt, str):  # --debug FILE provided
        # Enable world debug output and tee/redirect streams accordingly
        orig_stdout = sys.stdout
        orig_stderr = sys.stderr

        class _TeeStdout:
            def __init__(self, console_stream, file_stream):
                self._console = console_stream
                self._file = file_stream

            def write(self, s: str) -> int:  # type: ignore[override]
                n1 = self._console.write(s)
                n2 = self._file.write(s)
                return n1 if n1 is not None else (n2 or 0)

            def flush(self) -> None:
                self._console.flush()
                self._file.flush()

            def isatty(self) -> bool:  # pragma: no cover - tty detection
                return False

            @property
            def encoding(self) -> str:  # pragma: no cover - compatibility
                return getattr(self._console, "encoding", "utf-8")

        class _OnlyFile:
            def __init__(self, file_stream):
                self._file = file_stream

            def write(self, s: str) -> int:  # type: ignore[override]
                return self._file.write(s)

            def flush(self) -> None:
                self._file.flush()

            def isatty(self) -> bool:  # pragma: no cover - tty detection
                return False

            @property
            def encoding(self) -> str:  # pragma: no cover - compatibility
                return getattr(self._file, "encoding", "utf-8")

        with open(debug_opt, "w", encoding="utf-8") as fh:
            try:
                sys.stdout = _TeeStdout(orig_stdout, fh)
                sys.stderr = _OnlyFile(fh)
                run(str(data_path), language=args.language, llm_backend=llm, debug=True)
            finally:
                sys.stdout = orig_stdout
                sys.stderr = orig_stderr
    elif debug_opt is True:  # --debug without file
        run(str(data_path), language=args.language, llm_backend=llm, debug=True)
    else:
        run(str(data_path), language=args.language, llm_backend=llm, debug=False)


if __name__ == "__main__":
    run_cli()
