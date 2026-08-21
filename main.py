"""SimpleNetDict startup entry."""

from src.core.registry import SourcesRegistry
from src.gui.window import run

if __name__ == "__main__":
    run(SourcesRegistry())