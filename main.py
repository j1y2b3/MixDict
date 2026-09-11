"""MixDict v0.1.0

A simple network dictionary GUI program built on some network dictionary sources and pywebview.
Copyright © 2026 Jin Yubin
License: The MIT License (MIT)
"""

import argparse
import logging
import sys

from mixdict import config
if sys.flags.dev_mode:
    config.DEBUG = True

from mixdict import resources
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
    else:
        logger.setLevel(logging.INFO)
    formatter = logging.Formatter("[%(asctime)s][%(name)s][%(threadName)s][%(levelname)s] %(message)s")

    console_handler = logging.StreamHandler()
    if config.DEBUG:
        console_handler.setLevel(logging.DEBUG)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    file_handler = logging.FileHandler(resources.log_file_path(), encoding="utf-8")
    if config.DEBUG:
        file_handler.setLevel(logging.DEBUG)
    else:
        file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger

def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""

    parser = argparse.ArgumentParser(
        prog=config.APP_NAME,
        description=config.DESCRIPTION
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {config.VERSION}"
    )
    parser.add_argument(
        "-d", "--debug",
        action="store_true",
        help="user debug mod"
    )
    parser.add_argument(
        "--hidden",
        action="store_true",
        help="hide the window at startup"
    )
    parser.add_argument(
        "-q", "--quit",
        action="store_true",
        help="request the current application instance to exit"
    )
    args = parser.parse_args()

    if args.debug:
        config.DEBUG = True

    if args.quit:
        print("Not yet implemented.")

    return args

def main(args: argparse.Namespace):
    storage = Storage()
    sources_registry = SourcesRegistry()
    window = Window(sources_registry, storage)
    single_instance = SingleInstance(window)
    if not single_instance.run():
        return

    storage.init()
    sources_registry.init()
    window.init(args.hidden)

    tray = Tray(window)
    HotKey(window)
    if config.DEBUG:
        Watcher(window, sources_registry)
    tray.run()
    window.run()

if __name__ == "__main__":
    args = parse_args()
    logger = setup_logger()
    logger.info("Starting MixDict...")

    try:
        main(args)
    except Exception:
        logger.exception("Failed to start app")