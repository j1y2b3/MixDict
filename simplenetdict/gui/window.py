"""SimpleNetDict GUI (pywebview)."""

import logging

import webview

from simplenetdict.core.sources.base import DictionarySource

from simplenetdict.core.registry import SourcesRegistry
from simplenetdict import resources, config

logger = logging.getLogger(__name__)


class DictApi:
    """Methods exposed to the frontend JS through `window.pywebview.api`.
    
    For details, see: https://pywebview.flowrl.com/guide/interdomain.html
    """

    def __init__(self, sources_registry: SourcesRegistry):
        """Store the registry and pick the current default source."""

        self.sources_registry = sources_registry
        self.source_reg_name = self.sources_registry.default_source_reg_name
        self.source: DictionarySource
        self.set_source(self.source_reg_name)

        self._window: webview.Window  # Must add `_` to prevent recursive scanning by pywebview.
        self.is_window_maximized = False

    def get_source_name(self, reg_name: str) -> str | None:
        """Return the name of the source for `reg_name`."""
        source = self.sources_registry.get(reg_name)
        if source is None:
            return None
        return source.name

    def get_source_description(self, reg_name: str) -> str:
        """Return the description of the source for `reg_name`."""
        source = self.sources_registry.get(reg_name)
        if source is None:
            return ""
        return source.description

    def current_source_reg_name(self) -> str:
        """Return the `reg_name` of the current source."""
        return self.source_reg_name

    def list_sources_reg_name(self) -> list[str]:
        """Return the `reg_name`s of all registered sources."""
        return self.sources_registry.list()

    def set_source(self, reg_name: str):
        """Set the current source to `reg_name`."""
        source = self.sources_registry.get(reg_name)
        if source is None:
            raise ValueError(f"Unknown source: {reg_name!r}")
        self.source = source
        self.source_reg_name = source.reg_name

    def lookup(self, word: str) -> dict:
        """Use current source looking up `word`, return data format according to simplenetdict/schema.py."""
        logger.debug("Look up %r via %s", word, self.source.reg_name)
        return self.source.lookup(word)

    def set_window(self, window: webview.Window):
        self._window = window

    def minimize_window(self):
        self._window.minimize()

    def toggle_maximize_window(self) -> bool:
        """Return whether the window is now maximized."""
        if self.is_window_maximized:
            self._window.restore()
        else:
            self._window.maximize()
        self.is_window_maximized = not self.is_window_maximized
        return self.is_window_maximized

    def close_window(self):
        self._window.destroy()


def run(sources_registry: SourcesRegistry):
    """Start pywebview window."""

    screen = webview.screens[0]
    api = DictApi(sources_registry)

    # Adapt screen size
    width = max(config.WINDOW_MIN_SIZE[0], int(screen.width * config.WINDOW_SIZE_RATE[0]))
    height = max(config.WINDOW_MIN_SIZE[1], int(screen.height * config.WINDOW_SIZE_RATE[1]))

    webview.settings['DRAG_REGION_DIRECT_TARGET_ONLY'] = True
    window = webview.create_window(
        title=config.TITLE,
        url=str(resources.web_path("index.html")),  # pywebview will start a built-in HTTP server automatically.
        js_api=api,
        width=width,
        height=height,
        min_size=config.WINDOW_MIN_SIZE,
        screen=screen,  # pywebview automatically centers the window.
        text_select=True,
        frameless=True,
        easy_drag=False
    )
    if window is None:
        logger.error("Webview window creation was cancelled.")
        raise RuntimeError("Failed to create webview window.")
    api.set_window(window)
    webview.start(debug=config.DEBUG)

if __name__ == "__main__":
    run(SourcesRegistry())