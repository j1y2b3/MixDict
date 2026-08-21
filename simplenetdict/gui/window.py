"""SimpleNetDict GUI (pywebview)."""

from sys import flags

import webview

from simplenetdict.core.sources.base import DictionarySource

from simplenetdict.core.registry import SourcesRegistry
from simplenetdict import resources, config


class DictApi:
    """Methods exposed to the frontend JS through `window.pywebview.api`.
    
    For details, see: https://pywebview.flowrl.com/guide/interdomain.html
    """

    def __init__(self, sources_registry: SourcesRegistry):
        """Store the registry and pick the current default source."""

        self.sources_registry = sources_registry
        self.source_reg_name = self.sources_registry.default_source_reg_name
        self.source: DictionarySource
        self.source_name: str
        self.change_source(self.source_reg_name)

    def list_sources(self) -> list[str]:
        """Return the `reg_name`s of all registered sources."""
        return self.sources_registry.list()

    def change_source(self, reg_name: str):
        """Switch the current source to `reg_name`."""

        source, name = self.sources_registry.get(reg_name)
        if source is None or name is None:
            raise ValueError(f"Unknown source: {reg_name!r}")
        self.source = source
        self.source_name = name

    def lookup(self, word: str) -> dict:
        """Use current source looking up `word`, return data format according to simplenetdict/schema.py."""
        return self.source.lookup(word)


def run(sources_registry: SourcesRegistry, debug: bool = False):
    """Start pywebview window."""

    screen = webview.screens[0]

    # Adapt screen size
    width = max(config.WINDOW_MIN_SIZE[0], int(screen.width * config.WINDOW_SIZE_RATE[0]))
    height = max(config.WINDOW_MIN_SIZE[1], int(screen.height * config.WINDOW_SIZE_RATE[1]))

    webview.create_window(
        title=config.TITLE,
        url=str(resources.web_path("index.html")),  # pywebview will start a built-in HTTP server automatically
        js_api=DictApi(sources_registry),
        width=width,
        height=height,
        min_size=config.WINDOW_MIN_SIZE,
        screen=screen,  # pywebview automatically centers the window
        text_select=True
    )
    if flags.dev_mode:  # Start with `-X dev`
        debug = True
    webview.start(debug=debug)

if __name__ == "__main__":
    run(SourcesRegistry())