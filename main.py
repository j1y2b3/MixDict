"""SimpleNetDict startup entry."""

from sys import flags

from simplenetdict.core.registry import SourcesRegistry
from simplenetdict.gui.window import run
from simplenetdict import config

if __name__ == "__main__":
    if flags.dev_mode:
        config.DEBUG = True
    run(SourcesRegistry())