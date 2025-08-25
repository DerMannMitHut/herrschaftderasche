"""Entry point for running the sample adventure."""

from pathlib import Path
import sys

# Ensure repository root is on the path when executed directly
sys.path.append(str(Path(__file__).resolve().parent.parent))

from engine.game import run


if __name__ == "__main__":
    language = "de"
    data_path = Path(__file__).parent.parent / "data" / language / "world.yaml"
    run(str(data_path), language=language)
