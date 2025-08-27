"""Entry point for running the sample adventure."""

from pathlib import Path
import sys
import argparse

# Ensure repository root is on the path when executed directly
sys.path.append(str(Path(__file__).resolve().parent.parent))

from engine.game import run


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--language", default="de")
    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args()
    data_path = Path(__file__).parent.parent / "data" / args.language / "world.yaml"
    run(str(data_path), language=args.language, debug=args.debug)
