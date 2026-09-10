"""MixDict GUI (pywebview)."""

import logging
import json
from pathlib import Path

import webview

from typing import Callable, Any
from mixdict.core.sources.base import DictionarySource
from mixdict.storage import Storage

from mixdict.core.registry import SourcesRegistry
from mixdict import autostart, config, resources

FOCUS_QUERY_INPUT = """
setTimeout(() => document.getElementById("query-input").focus(), 1);
"""

logger = logging.getLogger(__name__)


class DictApi:
    """Methods exposed to the frontend JS through `window.pywebview.api`.
    
    For details, see: https://pywebview.flowrl.com/guide/interdomain.html
    """

    def __init__(self, sources_registry: SourcesRegistry, storage: Storage):
        """Store the registry and pick the current default source."""

        self._sources_registry = sources_registry
        self._storage = storage

        self._source_reg_name = self._storage.get("currentSourceRegName")
        if self._source_reg_name is None:
            self._source_reg_name = self._sources_registry.default_source_reg_name
        self.set_current_source(self._source_reg_name, no_exist_ok=True)

    # Dictionary sources
    @property
    def source(self) -> DictionarySource:
        """The current source instance (always fetched fresh from the registry)."""

        source = self._sources_registry.get(self._source_reg_name)
        if source is None:  # Need update `self._source_reg_name`.
            logger.info("Current source %r removed, reverted to %r",
                        self._source_reg_name, self._sources_registry.default_source_reg_name)
            self._source_reg_name = self._sources_registry.default_source_reg_name
            return self._sources_registry.get(self._source_reg_name)  # type: ignore
        return source

    def get_source_name(self, reg_name: str) -> str | None:
        """Return the name of the source for `reg_name`."""

        source = self._sources_registry.get(reg_name)
        if source is None:
            return None
        return source.name

    def get_source_description(self, reg_name: str) -> str:
        """Return the description of the source for `reg_name`."""

        source = self._sources_registry.get(reg_name)
        if source is None:
            return ""
        return source.description

    def current_source_reg_name(self) -> str:
        """Return the `reg_name` of the current source."""
        return self.source.reg_name

    def list_sources_reg_name(self) -> list[str]:
        """Return the `reg_name`s of all registered sources."""
        return self._sources_registry.list()

    def set_current_source(self, reg_name: str, no_exist_ok: bool = False):
        """Set the current source to `reg_name`.
        
        If set `no_exist_ok` True and source `reg_name` not exists,
        revert to default source `reg_name`.
        """

        if self._sources_registry.get(reg_name) is None:
            if no_exist_ok:
                logger.warning("Dictionary source %r not exists, revert to %r",
                               reg_name, config.DEFAULT_DICTIONARY_SOURCE)
                reg_name = config.DEFAULT_DICTIONARY_SOURCE
            else:
                raise ValueError(f"Unknown source: {reg_name!r}")
        self._source_reg_name = reg_name
        self._storage.set("currentSourceRegName", reg_name)

    def lookup(self, word: str) -> dict:
        """Use current source looking up `word`, return data format according to mixdict/schema.py."""

        source = self.source
        result_page = source.lookup(word)

        logger.debug("Look up %r via %s %s", word, source.reg_name, source)
        if config.DEBUG:
            dump_path = Path("tmp") / f"page-{word}.json"
            dump_path.write_text(json.dumps(result_page, ensure_ascii=False, indent=4), encoding="utf-8")
            logger.debug("Saved result page to %s", dump_path.resolve())

        return result_page

    # Storage
    def storage_set(self, key: str, value: Any, check_key: bool = False, save: bool = True):
        self._storage.set(key, value, check_key, save)

    def storage_get(self, key: str, default: Any | None = None) -> Any:
        return self._storage.get(key, default)

    # Stratup run
    def is_startup_run_supported(self) -> bool:
        return autostart.SUPPORTED

    def is_startup_run(self) -> bool | None:
        return autostart.is_enabled()

    def enable_startup_run(self) -> bool:
        return autostart.enable()

    def disable_startup_run(self) -> bool:
        return autostart.disable()


class Window:

    def __init__(self, sources_registry: SourcesRegistry, storage: Storage):

        self.sources_registry = sources_registry
        self.storage = storage

    def init(self, hidden: bool = False):

        self.screen = webview.screens[0]
        self.storage_path = str(resources.webview_storage_path())

        # Adapt screen size.
        self.width = max(config.WINDOW_MIN_SIZE[0], int(self.screen.width * config.WINDOW_SIZE_RATE[0]))
        self.height = max(config.WINDOW_MIN_SIZE[1], int(self.screen.height * config.WINDOW_SIZE_RATE[1]))

        self._window = webview.create_window(
            title=config.TITLE,
            url=str(resources.web_path("index.html")),  # pywebview will start a built-in HTTP server automatically.
            js_api=DictApi(self.sources_registry, self.storage),
            width=self.width,
            height=self.height,
            min_size=config.WINDOW_MIN_SIZE,
            screen=self.screen,  # pywebview automatically centers the window.
            text_select=True,
            background_color="#000000",
            hidden=hidden
        )

        self.window.events.closing += self._on_closing

    @property
    def window(self) -> webview.Window:
        if self._window is None:
            logger.error("Webview window creation was cancelled.")
            raise RuntimeError("Failed to create webview window.")
        return self._window

    def show(self):
        self.window.on_top = True
        self.window.show()
        self.window.evaluate_js(FOCUS_QUERY_INPUT)
        self.window.on_top = False

    def destroy(self):
        self.window.destroy()

    def evaluate_js(self, script: str, callback: Callable[..., Any] | None = None) -> Any:
        return self.window.evaluate_js(script, callback)

    def _on_closing(self) -> bool | None:
        if config.TO_EXIT:
            return None
        self.window.hide()
        return False

    def run(self):
        """Start pywebview window."""
        logger.info("Store cache at %s", self.storage_path)
        webview.start(debug=config.DEBUG, storage_path=self.storage_path,
                      icon=str(resources.assets_path("icon.ico")))