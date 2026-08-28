"""GUI and user dictionary sources hot-updater.

Facilitate GUI and user dictionary sources develop.
"""
from pathlib import Path
import threading
import time

from webview import Window

from simplenetdict import resources

UPDATE_STYLE = """
document.querySelectorAll('link[rel=stylesheet]').forEach(lnk => {
    const file = lnk.getAttribute('href').split('?')[0];
    lnk.href = file + '?t=' + Date.now();  // Trigger new request.
});
"""


class Watcher:
    """Regularly check and reload GUI (`web/`) and user dictionary sources (`uer_sources/`)."""

    def __init__(self, window: Window, interval: float = 0.5):
        """Start the `Watcher`."""
        self.window = window
        self.interval = interval

        threading.Thread(target=self.watch_gui, daemon=True).start()
        threading.Thread(target=self.watch_user_sources, daemon=True).start()

    def get_files_state(self, directory: Path | str) -> dict[Path, float]:
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

    def watch_gui(self):
        """Regularly check and reload CSS, JavaScript and HTML (files in `web/`)."""
        directory = resources.web_path(".")
        old_files_state = self.get_files_state(directory)

        while True:
            time.sleep(self.interval)

            cur_files_state = self.get_files_state(directory)
            changed_files = self.diff_files(old_files_state, cur_files_state)

            if changed_files:
                old_files_state = cur_files_state

                if any(f.suffix == ".css" for f in changed_files):
                    self.window.evaluate_js(UPDATE_STYLE)
                if any(f.suffix in (".html", ".js") for f in changed_files):
                    self.window.evaluate_js("location.reload()")

    def watch_user_sources(self):
        """Regularly check and reload user dictionary sources (files in `uer_sources/`)."""
        directory = resources.user_sources_dir()
        old_files_state = self.get_files_state(directory)

        while True:
            time.sleep(self.interval)

            cur_files_state = self.get_files_state(directory)
            changed_files = self.diff_files(old_files_state, cur_files_state)

            if changed_files:
                old_files_state = cur_files_state

                ...