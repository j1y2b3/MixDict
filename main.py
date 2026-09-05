"""MixDict startup entry."""

import logging
from sys import flags

from mixdict.core.registry import SourcesRegistry
from mixdict.gui.window import Window
from mixdict.hotupdate import Watcher
from mixdict import config

if flags.dev_mode:
    config.DEBUG = True

def setup_logger() -> logging.Logger:
    logger = logging.getLogger("mixdict")
    if config.DEBUG:
        logger.setLevel(logging.DEBUG)

    handler = logging.StreamHandler()
    if config.DEBUG:
        handler.setLevel(logging.DEBUG)

    formatter = logging.Formatter("[%(name)s][%(levelname)s] %(message)s")
    handler.setFormatter(formatter)

    logger.addHandler(handler)

    return logger

if __name__ == "__main__":
    logger = setup_logger()
    logger.info("Starting MixDict...")

    sources_registry = SourcesRegistry()
    window = Window(sources_registry)
    if config.DEBUG:
        Watcher(window.window, sources_registry)
    window.run()