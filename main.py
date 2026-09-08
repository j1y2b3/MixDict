"""MixDict startup entry."""

import logging
from sys import flags

from mixdict import config
if flags.dev_mode:
    config.DEBUG = True

from mixdict.core.registry import SourcesRegistry
from mixdict.gui.window import Window
from mixdict.gui.tray import Tray
from mixdict.hotkey import HotKey
from mixdict.hotupdate import Watcher
from mixdict.oneinstance import SingleInstance
from mixdict.storage import Storage

def setup_logger() -> logging.Logger:
    logger = logging.getLogger(config.APP_NAME.lower())
    if config.DEBUG:
        logger.setLevel(logging.DEBUG)

    handler = logging.StreamHandler()
    if config.DEBUG:
        handler.setLevel(logging.DEBUG)

    formatter = logging.Formatter("[%(name)s][%(levelname)s] %(message)s")
    handler.setFormatter(formatter)

    logger.addHandler(handler)
    return logger

def main():
    storage = Storage()
    sources_registry = SourcesRegistry()
    window = Window(sources_registry, storage)
    single_instance = SingleInstance(window)
    if not single_instance.run():
        return

    storage.init()
    sources_registry.init()
    window.init()

    tray = Tray(window)
    HotKey(window)
    if config.DEBUG:
        Watcher(window, sources_registry)
    tray.run()
    window.run()

if __name__ == "__main__":
    logger = setup_logger()
    logger.info("Starting MixDict...")

    try:
        main()
    except Exception:
        logger.exception("Failed to start app")