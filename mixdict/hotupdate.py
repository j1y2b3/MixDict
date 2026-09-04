"""GUI and user dictionary sources hot-updater.

Should only use in debug mod.
Facilitate GUI and user dictionary sources develop.
"""
import logging
from pathlib import Path
import threading
import time

from webview import Window
from mixdict.core.registry import SourcesRegistry

from mixdict import resources

UPDATE_STYLE = """
document.querySelectorAll('link[rel=stylesheet]').forEach(lnk => {
    const file = lnk.getAttribute('href').split('?')[0];
    lnk.href = file + '?t=' + Date.now();  // Trigger new request.
});
"""
REFRESH_DICT_LIST = """
displayCurrentSource();
document.getElementById("source-list").replaceChildren();
displayDictSourcesList();
"""

logger = logging.getLogger(__name__)


class Watcher:
    """Regularly check and reload GUI (`web/`) and user dictionary sources (`uer_sources/`)."""

    def __init__(self, window: Window,
                 sources_registry: SourcesRegistry,
                 interval: float = 0.5):
        """Start the `Watcher`."""
        self.window = window
        self.sources_registry = sources_registry
        self.interval = interval

        threading.Thread(target=self.watch_gui, daemon=True).start()
        threading.Thread(target=self.watch_user_sources, daemon=True).start()

    def get_files_state(self, directory: Path | str) -> dict[Path, float]:
        """Return the (path, timestamp) pairs of files in the specified directory."""

        directory = Path(directory)
        files_state = {}

        for file in directory.rglob("*"):
            if file.is_file():
                files_state[file] = file.stat().st_mtime

        return files_state

    def diff_files(self, old: dict[Path, float], new: dict[Path, float]) -> list[Path]:
        """Compare and return the differences between old and new files state returned by `get_files_state()`.
        
        Return the files with changed content and files added in `new`.
        Not return files removed in `new`.
        """
        changed_files = []

        for file in new:
            if new[file] != old.get(file):
                changed_files.append(file)

        return changed_files

    def removed_files(self, old: dict[Path, float], new: dict[Path, float]) -> list[Path]:
        """Like `diff_files()` but only return the removed files."""

        removed_files = []

        for file in old:
            if file not in new:
                removed_files.append(file)

        return removed_files

    def watch_gui(self):
        """Regularly check and reload CSS, JavaScript and HTML (files in `web/`)."""
        directory = resources.web_path(".")
        old_files_state = self.get_files_state(directory)

        while True:
            time.sleep(self.interval)

            cur_files_state = self.get_files_state(directory)
            changed_files = self.diff_files(old_files_state, cur_files_state)

            if not changed_files:
                continue

            old_files_state = cur_files_state

            if any(file.suffix == ".css" for file in changed_files):
                self.window.evaluate_js(UPDATE_STYLE)
            if any(file.suffix in (".html", ".js") for file in changed_files):
                self.window.evaluate_js("location.reload()")

    def watch_user_sources(self):
        """Regularly check and reload user dictionary sources (files in `uer_sources/`)."""
        directory = resources.user_sources_dir()
        old_files_state = self.get_files_state(directory)

        # Reference to `sources_registry.user_sources_reg_map` (not a copy).
        source_files_map: dict[Path, str] = self.sources_registry.user_sources_reg_map

        while True:
            try:
                time.sleep(self.interval)

                cur_files_state = self.get_files_state(directory)
                changed_files = self.diff_files(old_files_state, cur_files_state)
                removed_files = self.removed_files(old_files_state, cur_files_state)

                if not(changed_files or removed_files):
                    continue

                old_files_state = cur_files_state

                for file in removed_files:
                    removed_reg_name = source_files_map.pop(file, "")
                    try:
                        self.sources_registry.unregister(removed_reg_name)
                    except Exception:
                        logger.exception("Failed to unregister user source %s", file)
                        continue

                for file in changed_files:
                    if file.suffix != ".py":
                        continue

                    try:
                        source = resources.load_user_source(file)
                    except Exception:
                        logger.exception("Failed to initialise user source %s", file)
                        continue
                    if source is None:
                        continue

                    try:
                        old_reg_name = source_files_map.get(file)
                        new_reg_name = source.reg_name

                        if old_reg_name is not None and source.reg_name != old_reg_name:
                            self.sources_registry.unregister(old_reg_name)
                        self.sources_registry.register(source, force=True)  # Update registry.
                        source_files_map[file] = new_reg_name  # Update local record.
                    except Exception:
                        logger.exception("Failed to register user source %s", file)
                        continue

                self.window.evaluate_js(REFRESH_DICT_LIST)

            except Exception as error:
                logger.exception("Hot update error")