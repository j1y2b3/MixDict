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
        self.set_source(self.source_reg_name)

    @property
    def source(self) -> DictionarySource:
        """The current source instance (always fetched fresh from the registry)."""

        source = self.sources_registry.get(self.source_reg_name)
        if source is None:  # Need update `self.source_reg_name`.
            logger.info("Current source %r removed, reverted to %r",
                        self.source_reg_name, self.sources_registry.default_source_reg_name)
            self.source_reg_name = self.sources_registry.default_source_reg_name
            return self.sources_registry.get(self.source_reg_name)  # type: ignore
        return source

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
        return self.source.reg_name

    def list_sources_reg_name(self) -> list[str]:
        """Return the `reg_name`s of all registered sources."""
        return self.sources_registry.list()

    def set_source(self, reg_name: str):
        """Set the current source to `reg_name`."""

        if self.sources_registry.get(reg_name) is None:
            raise ValueError(f"Unknown source: {reg_name!r}")
        self.source_reg_name = reg_name

    def lookup(self, word: str) -> dict:
        """Use current source looking up `word`, return data format according to simplenetdict/schema.py."""

        source = self.source
        logger.debug("Look up %r via %s %s", word, source.reg_name, source)
        return source.lookup(word)


class Window:

    def __init__(self, sources_registry: SourcesRegistry):

        self.screen = webview.screens[0]
        self.storage_path = str(resources.webview_storage_path())

        # Adapt screen size
        self.width = max(config.WINDOW_MIN_SIZE[0], int(self.screen.width * config.WINDOW_SIZE_RATE[0]))
        self.height = max(config.WINDOW_MIN_SIZE[1], int(self.screen.height * config.WINDOW_SIZE_RATE[1]))

        self.window = webview.create_window(
            title=config.TITLE,
            url=str(resources.web_path("index.html")),  # pywebview will start a built-in HTTP server automatically.
            js_api=DictApi(sources_registry),
            width=self.width,
            height=self.height,
            min_size=config.WINDOW_MIN_SIZE,
            screen=self.screen,  # pywebview automatically centers the window.
            text_select=True,
            background_color="#000000"
        )

    def get_window(self):
        if self.window is None:
            logger.error("Webview window creation was cancelled.")
            raise RuntimeError("Failed to create webview window.")
        return self.window

    def run(self):
        """Start pywebview window."""
        logger.info("Store cache at %s", self.storage_path)
        webview.start(debug=config.DEBUG, storage_path=self.storage_path)