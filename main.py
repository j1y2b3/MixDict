"""SimpleNetDict startup entry."""

from simplenetdict.core.registry import SourcesRegistry
from simplenetdict.gui.window import run

if __name__ == "__main__":
    run(SourcesRegistry())