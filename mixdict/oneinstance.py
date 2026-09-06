"""Single-instance application lock.

If a second instance is launched, it will terminate itself and activate
the existing application window.
"""

import errno
import logging
import socket
import threading

from webview import Window

from mixdict import config

LOCALHOST = "127.0.0.1"
PORT = 50712 if config.DEBUG else 51712
BUFSIZE = 1024

SHOW = b"show"
QUIT = b"quit"

logger = logging.getLogger(__name__)


class SingleInstance:

    def __init__(self, window: Window):

        self.window = window

    def _check_exist(self, _socket: socket.socket | None = None) -> bool:
        """Check whether exist another app instance.
        
        If exist, call `self._on_quit()` and return the result, otherwise, return `False`.
        """

        if _socket is None:
            _socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        with _socket as s:
            s.settimeout(0.3)
            try:
                s.connect((LOCALHOST, PORT))

            except (ConnectionRefusedError, TimeoutError):  # Not exist app instance.
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
                raise os_error
            if max_depth <= 1:  # Prevent Excessive Recursion.
                raise os_error

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
                    with conn:
                        recv = conn.recv(1024)
                        if not recv:
                            continue
                        conn.sendall(QUIT)
                        if recv == SHOW:
                            self.window.show()

                except OSError:
                    logger.exception("OSError when connecting new instance")
                    continue

    def run(self) -> bool:
        """Start single instance locker.
        
        If start successfully, return `True`;
        If exist another instance, return `False`.
        """

        if self._check_exist():
            return False

        binded_socket = self._get_lock()
        if binded_socket is None:
            return False

        threading.Thread(target=self._listen, args=[binded_socket], daemon=True).start()
        return True