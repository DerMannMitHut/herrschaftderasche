"""Entry point for running the sample adventure."""

from pathlib import Path
import argparse

from engine.game import run


def run_cli() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--language", default="de")
    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args()
    data_path = (
        Path(__file__).parent.parent
        / "data"
        / args.language
        / f"world.{args.language}.yaml"
    )
    run(str(data_path), language=args.language, debug=args.debug)


if __name__ == "__main__":
    run_cli()
