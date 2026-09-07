"""Manage tray icon behaviour."""

import pystray

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from mixdict.gui.window import Window

from mixdict import resources, config


class Tray:

    def __init__(self, window: "Window"):

        self.window = window
        self.image = resources.load_tray_icon()
        self.menu = pystray.Menu(pystray.MenuItem("打开", self.open, default=True),
                                 pystray.MenuItem("退出", self.exit))
        self.icon = pystray.Icon("MixDict", self.image, config.TITLE, self.menu)

    def open(self, icon: "pystray.Icon", item: "pystray.MenuItem"):  # type: ignore
        self.window.show()

    def exit(self, icon: "pystray.Icon", item: "pystray.MenuItem"):  # type: ignore
        config.TO_EXIT = True
        icon.stop()
        self.window.destroy()

    def run(self):
        """Will not block thread."""
        self.icon.run_detached()