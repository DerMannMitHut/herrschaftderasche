"""Entry point for running the sample adventure."""

import argparse
from pathlib import Path

from engine.game import run
from engine.llm import OllamaLLM


def run_cli() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--language", default="de")
    parser.add_argument("--debug", action="store_true")
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
    run(str(data_path), language=args.language, llm_backend=llm, debug=args.debug)


if __name__ == "__main__":
    run_cli()
