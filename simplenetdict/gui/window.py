"""SimpleNetDict GUI (pywebview)."""

import logging
import time

import webview

from simplenetdict.core.sources.base import DictionarySource

from simplenetdict.core.registry import SourcesRegistry
from simplenetdict import resources, config

logger = logging.getLogger(__name__)

UPDATE_CSS = """
document.querySelectorAll('link[rel=stylesheet]').forEach(lnk => {
    const file = lnk.getAttribute('href').split('?')[0];
    lnk.href = file + '?t=' + Date.now();  // Trigger new request.
});
"""


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


def _live_update_gui(window: webview.Window, interval: float = 0.5):
    """Regularly check and update CSS, JavaScript and HTML (files in `web/`)."""

    web_dir = resources.web_path(".")
    old_files_state = {f: f.stat().st_mtime for f in web_dir.rglob("*") if f.is_file()}

    while True:
        time.sleep(interval)

        new_files_state = {f: f.stat().st_mtime for f in web_dir.rglob("*") if f.is_file()}
        changed_files = {f for f in new_files_state if new_files_state[f] != old_files_state.get(f)}

        if changed_files:
            old_files_state = new_files_state
            if any(f.suffix == ".css" for f in changed_files):
                window.evaluate_js(UPDATE_CSS)

        if any(f.suffix in (".html", ".js") for f in changed_files):
                window.evaluate_js("location.reload()")

def run(sources_registry: SourcesRegistry):
    """Start pywebview window."""

    screen = webview.screens[0]
    storage_path = str(resources.webview_storage_path())

    # Adapt screen size
    width = max(config.WINDOW_MIN_SIZE[0], int(screen.width * config.WINDOW_SIZE_RATE[0]))
    height = max(config.WINDOW_MIN_SIZE[1], int(screen.height * config.WINDOW_SIZE_RATE[1]))

    window = webview.create_window(
        title=config.TITLE,
        url=str(resources.web_path("index.html")),  # pywebview will start a built-in HTTP server automatically.
        js_api=DictApi(sources_registry),
        width=width,
        height=height,
        min_size=config.WINDOW_MIN_SIZE,
        screen=screen,  # pywebview automatically centers the window.
        text_select=True
    )

    if config.DEBUG:
        import threading
        threading.Thread(target=_live_update_gui, args=(window,), daemon=True).start()
    logger.info("Store cache at %s", storage_path)
    webview.start(debug=config.DEBUG, storage_path=storage_path)

if __name__ == "__main__":
    run(SourcesRegistry())