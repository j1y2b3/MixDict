"""Manage hotkey."""

import ctypes
from ctypes import wintypes
import logging
import sys
import threading

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from mixdict.gui.window import Window

logger = logging.getLogger(__name__)

if sys.platform == "win32":

    WM_HOTKEY = 0x0312
    MOD_ALT = 0x0001
    MOD_CONTROL = 0x0002
    MOD_SHIFT = 0x0004
    MOD_WIN = 0x0008
    MOD_NOREPEAT = 0x4000

    ON_SHOW_WINDOW = 1

    user32 = ctypes.windll.user32


    class HotKey:
        """Global hotkey (Windows)."""

        def __init__(self, window: "Window"):

            self.window = window

            # Start listening thread.
            threading.Thread(target=self._listen, daemon=True, name="mixdict-hotkey").start()

        def _listen(self):
            """Start hotkey listening."""
            msg = wintypes.MSG()

            # Register hotkeys (must in listening thread).
            if not user32.RegisterHotKey(None, ON_SHOW_WINDOW,
                                         MOD_CONTROL | MOD_WIN | MOD_NOREPEAT, ord('T')):
                try:
                    raise ctypes.WinError()
                except:
                    logger.exception("Failed to register the global hotkey (may occupied); "
                                     "the hotkey function is unavailable")
                return

            try:
                while True:
                    bRet = user32.GetMessageW(ctypes.byref(msg), None, 0, 0)
                    if bRet == -1:
                        raise ctypes.WinError()
                    elif bRet == 0:
                        break
                    elif msg.message == WM_HOTKEY:

                        if msg.wParam == ON_SHOW_WINDOW:
                            self.window.show()

            finally:
                user32.UnregisterHotKey(None, ON_SHOW_WINDOW)


else:
    class HotKey:
        """Global hotkey (unsupported platform)."""
        def __init__(self, window: "Window"):
            pass
    logger.warning("Currently not supported platform: %r", sys.platform)