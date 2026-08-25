"""SimpleNetDict startup entry."""

import logging
from sys import flags

from simplenetdict.core.registry import SourcesRegistry
from simplenetdict.gui.window import run
from simplenetdict import config

if flags.dev_mode:
    config.DEBUG = True

def setup_logger() -> logging.Logger:
    logger = logging.getLogger("simplenetdict")
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
    logger.info("Starting SimpleNetDict...")
    run(SourcesRegistry())