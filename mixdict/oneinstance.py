"""Single-instance application lock.

If a second instance is launched, it will terminate itself and activate
the existing application window.
"""

import errno
import logging
import socket
import threading

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from mixdict.gui.window import Window
    from mixdict.gui.tray import Tray

from mixdict import config

LOCALHOST = "127.0.0.1"
PORT = 50712 if config.DEBUG else 51712
BUFSIZE = 1024
TIMEOUT = 0.3

SHOW = b"show"
QUIT = b"quit"

logger = logging.getLogger(__name__)


class SingleInstance:

    def __init__(self, window: "Window", tray: "Tray"):

        self.window = window
        self.tray = tray

    def _check_exist(self, _socket: socket.socket | None = None) -> bool:
        """Check whether exist another app instance.
        
        If exist, call `self._on_quit()` and return the result, otherwise, return `False`.
        Will close the passed `_socket`!
        """

        if _socket is None:
            _socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        with _socket as s:
            s.settimeout(TIMEOUT)
            try:
                s.connect((LOCALHOST, PORT))

            except (ConnectionRefusedError, TimeoutError):  # Not exist app instance.
                logger.debug("Port %s no listening", PORT)
                return False

            else:  # Exist app instance.
                return self._on_quit(s)

    def _on_quit(self, _socket: socket.socket) -> bool:
        """Send "show window" command to existing instance socket and receive "quit" command.
        
        If existing instance exit during the period, return `False`;
        If received "quit" command normally, retrun `True`.
        """

        try:
            _socket.sendall(SHOW)
            recv = _socket.recv(BUFSIZE)
        except (ConnectionResetError, BrokenPipeError, TimeoutError):  # Existing instance exited.
            recv = b""

        if recv == QUIT:
            return True
        elif not recv:  # Existing instance exited.
            return False
        else:
            logger.error("Received unknown command: %s", recv)
            return False

    def _get_lock(self, max_depth: int = 3) -> socket.socket | None:
        """Try to get a binded socket until succeed or exist another app instance.
        
        Use `max_depth` to set max attempt depth.
        """

        # Create a socket every level because `_check_exist()` will close it.
        _socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            _socket.bind((LOCALHOST, PORT))
        except OSError as os_error:
            if os_error.errno != errno.EADDRINUSE:  # Not be occupied.
                logger.exception("Failed to bind lock port %s", PORT)
                raise
            if max_depth <= 1:  # Prevent Excessive Recursion.
                logger.error("Port %s occupied but not detected anothor activatable inetance "
                             "(may occupied by an unrelated program)", PORT)
                raise

            # Exist app instance.
            if self._check_exist(_socket):  # This will close the `_socket`.
                return None
            else:  # Existing instance exited.
                return self._get_lock(max_depth - 1)
        else:
            return _socket

    def _listen(self, binded_socket: socket.socket):
        """Run single instance lock loop."""

        binded_socket.listen(2)
        with binded_socket as s:
            while True:  # Listening loop.
                try:
                    conn, _ = s.accept()
                except OSError:
                    logger.critical("Single instance listening socket failed, unlocked", exc_info=True)
                    break

                try:
                    with conn:
                        recv = conn.recv(BUFSIZE)
                        if not recv:
                            continue
                        if recv == QUIT:
                            self.tray.exit()
                            break
                        conn.sendall(QUIT)
                        if recv == SHOW:
                            self.window.show()
                except OSError:
                    logger.warning("OSError when connecting new instance", exc_info=True)
                    continue

    def run(self) -> bool:
        """Start single instance locker.
        
        If start successfully, return `True`;
        If exist another instance, return `False`.
        """
        logger.info("Single instance checking...")

        if self._check_exist():
            logger.info("Exist another instance, exit after showing its window")
            return False

        binded_socket = self._get_lock()
        if binded_socket is None:
            logger.info("Exist another instance, exit after showing its window")
            return False

        threading.Thread(target=self._listen, args=[binded_socket],
                         daemon=True, name="mixdict-single-instance").start()
        logger.debug("Single instance lock start successfully, listening port %s", PORT)
        return True