"""SingleInstance(单实例锁)测试。

尽量用受控的本地 socket server 模拟"已有实例",验证探测/协议/竞争逻辑;
需要真实 `_listen` 的用例通过手动启动 + 保活 socket,避免 GC 关 socket 造成忙循环。
"""
import errno
import socket
import threading

import pytest

from mixdict import oneinstance as oi

# 保活引用: 防止测试结束 socket 被 GC 关闭,导致 _listen 的 except-continue 忙循环。
_LIVE_SOCKS: list[socket.socket] = []


class FakeWindow:
    def __init__(self):
        self.show_calls = 0

    def show(self):
        self.show_calls += 1


def _free_port() -> int:
    """向系统要一个空闲端口(释放后使用,单测内极小概率被抢)。"""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind((oi.LOCALHOST, 0))
    port = s.getsockname()[1]
    s.close()
    return port


def _make_si(monkeypatch, window=None) -> tuple[oi.SingleInstance, int]:
    """把模块级 PORT 指到临时端口,返回 (SingleInstance, port)。"""
    port = _free_port()
    monkeypatch.setattr(oi, "PORT", port)
    return oi.SingleInstance(window or FakeWindow()), port


def _spawn_server(port: int, behavior: str = "quit"):
    """起一个模拟"已有实例"的监听 socket。

    behavior:
      quit    -> 收到 SHOW 回 QUIT
      garbage -> 收到 SHOW 回乱码
      close   -> 收到 SHOW 后直接关连接(不回)
      silent  -> 收到 SHOW 后保持连接但不回(测客户端超时)
    """
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.bind((oi.LOCALHOST, port))
    srv.listen(1)
    stop = threading.Event()

    def loop():
        srv.settimeout(0.2)
        while not stop.is_set():
            try:
                conn, _ = srv.accept()
            except socket.timeout:
                continue
            except OSError:
                break
            with conn:
                try:
                    data = conn.recv(1024)
                except OSError:
                    continue
                if data != oi.SHOW:
                    continue
                if behavior == "quit":
                    conn.sendall(oi.QUIT)
                elif behavior == "garbage":
                    conn.sendall(b"xx")
                elif behavior == "silent":
                    stop.wait(0.5)  # 保持打开但不回,等客户端超时
                # behavior == "close": 不 send,with 退出即关连接。

    threading.Thread(target=loop, daemon=True).start()
    return srv, stop


def _close_server(srv: socket.socket, stop: threading.Event):
    stop.set()
    try:
        srv.close()
    except OSError:
        pass


class TestCheckExist:
    def test_no_instance_returns_false(self, monkeypatch):
        si, _ = _make_si(monkeypatch)
        assert si._check_exist() is False

    def test_existing_quit_reply_returns_true(self, monkeypatch):
        si, port = _make_si(monkeypatch)
        srv, stop = _spawn_server(port, "quit")
        try:
            assert si._check_exist() is True
        finally:
            _close_server(srv, stop)

    def test_existing_but_closed_returns_false(self, monkeypatch):
        # 主实例收到 SHOW 后退出(不回 QUIT) → 视为"无存活实例"。
        si, port = _make_si(monkeypatch)
        srv, stop = _spawn_server(port, "close")
        try:
            assert si._check_exist() is False
        finally:
            _close_server(srv, stop)


class TestOnQuit:
    def _connect(self, port: int) -> socket.socket:
        c = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        c.connect((oi.LOCALHOST, port))
        return c

    def test_quit_reply_returns_true(self, monkeypatch):
        si, port = _make_si(monkeypatch)
        srv, stop = _spawn_server(port, "quit")
        c = self._connect(port)
        try:
            assert si._on_quit(c) is True
        finally:
            c.close()
            _close_server(srv, stop)

    def test_peer_closed_returns_false(self, monkeypatch):
        si, port = _make_si(monkeypatch)
        srv, stop = _spawn_server(port, "close")
        c = self._connect(port)
        try:
            assert si._on_quit(c) is False
        finally:
            c.close()
            _close_server(srv, stop)

    def test_unknown_reply_returns_false_and_logs(self, monkeypatch, caplog):
        si, port = _make_si(monkeypatch)
        srv, stop = _spawn_server(port, "garbage")
        c = self._connect(port)
        try:
            with caplog.at_level("ERROR", logger="mixdict.oneinstance"):
                assert si._on_quit(c) is False
            assert "unknown command" in caplog.text
        finally:
            c.close()
            _close_server(srv, stop)

    def test_timeout_returns_false(self, monkeypatch):
        # 主实例在但不回应 → recv 超时 → 按"没收到 QUIT"处理(外层 bind 兜底)。
        si, port = _make_si(monkeypatch)
        srv, stop = _spawn_server(port, "silent")
        c = self._connect(port)
        c.settimeout(0.05)
        try:
            assert si._on_quit(c) is False
        finally:
            c.close()
            _close_server(srv, stop)


class TestGetLock:
    def test_acquires_when_port_free(self, monkeypatch):
        si, port = _make_si(monkeypatch)
        sock = si._get_lock()
        assert sock is not None
        assert sock.getsockname()[1] == port
        sock.close()

    def test_returns_none_when_instance_exists(self, monkeypatch):
        si, port = _make_si(monkeypatch)
        srv, stop = _spawn_server(port, "quit")
        try:
            assert si._get_lock() is None
        finally:
            _close_server(srv, stop)

    def test_raises_when_port_held_without_listener(self, monkeypatch):
        # 无关程序 bind 但不 listen → 探测不到实例 → 重试耗尽后 raise EADDRINUSE。
        si, port = _make_si(monkeypatch)
        holder = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        holder.bind((oi.LOCALHOST, port))  # 只 bind 不 listen
        try:
            with pytest.raises(OSError) as excinfo:
                si._get_lock(max_depth=1)  # 快速失败,避免多次 connect 超时
            assert excinfo.value.errno == errno.EADDRINUSE
        finally:
            holder.close()

    def test_non_eaddrinuse_error_propagates(self, monkeypatch):
        si, _ = _make_si(monkeypatch)

        class _BindErrSocket:
            def bind(self, addr):
                raise OSError(errno.EACCES, "permission denied")

            def close(self):
                pass

        monkeypatch.setattr(oi.socket, "socket", lambda *a, **k: _BindErrSocket())
        with pytest.raises(OSError) as excinfo:
            si._get_lock()
        assert excinfo.value.errno == errno.EACCES


class TestRun:
    def test_second_instance_returns_false(self, monkeypatch):
        si, _ = _make_si(monkeypatch)
        monkeypatch.setattr(si, "_check_exist", lambda: True)
        assert si.run() is False

    def test_get_lock_none_returns_false(self, monkeypatch):
        si, _ = _make_si(monkeypatch)
        monkeypatch.setattr(si, "_check_exist", lambda: False)
        monkeypatch.setattr(si, "_get_lock", lambda: None)
        assert si.run() is False

    def test_first_instance_starts_listen_thread(self, monkeypatch):
        si, _ = _make_si(monkeypatch)
        monkeypatch.setattr(si, "_check_exist", lambda: False)

        fake_socket = object()
        monkeypatch.setattr(si, "_get_lock", lambda: fake_socket)

        captured = {}

        class FakeThread:
            def __init__(self, target=None, args=None, daemon=None, name=None):
                captured["target"] = target
                captured["args"] = args
                captured["name"] = name
                captured["daemon"] = daemon

            def start(self):
                captured["started"] = True

        monkeypatch.setattr(threading, "Thread", FakeThread)
        assert si.run() is True
        # 每次访问 si._listen 都会新建 bound method 对象,故比较底层函数而非 `is`。
        assert captured["target"].__func__ is oi.SingleInstance._listen
        assert captured["target"].__self__ is si
        assert captured["args"] == [fake_socket]
        assert captured["daemon"] is True
        assert captured["name"] == "mixdict-single-instance"
        assert captured["started"] is True


class TestListen:
    """需要真实 `_listen` 的用例:socket 保活不 close,进程结束时由 OS 回收。"""

    def _start_listener(self, si: oi.SingleInstance, port: int) -> socket.socket:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind((oi.LOCALHOST, port))
        threading.Thread(target=si._listen, args=[sock], daemon=True).start()
        _LIVE_SOCKS.append(sock)  # 保活,避免 GC 关闭后 _listen 忙循环
        return sock

    def test_show_triggers_window_show_and_quit_reply(self, monkeypatch):
        window = FakeWindow()
        si, port = _make_si(monkeypatch, window)
        self._start_listener(si, port)

        c = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        c.settimeout(1.0)
        try:
            c.connect((oi.LOCALHOST, port))
            c.sendall(oi.SHOW)
            assert c.recv(1024) == oi.QUIT
        finally:
            c.close()
        assert window.show_calls == 1

    def test_second_instance_run_activates_first(self, monkeypatch):
        # 端到端:第一个实例真实监听,第二个实例 run() 应返回 False 并让第一个 show。
        window1 = FakeWindow()
        si1, port = _make_si(monkeypatch, window1)
        self._start_listener(si1, port)

        si2 = oi.SingleInstance(FakeWindow())
        assert si2.run() is False  # _check_exist 探测到 si1 → 发 SHOW → 收 QUIT
        assert window1.show_calls == 1

    def test_listen_ignores_garbage_connection(self, monkeypatch):
        # 空/垃圾连接不应杀死监听线程(先 QUIT 再 show 的逻辑不受影响)。
        window = FakeWindow()
        si, port = _make_si(monkeypatch, window)
        self._start_listener(si, port)

        # 发一条非 SHOW 的垃圾,服务器应忽略并继续存活。
        c = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        c.settimeout(1.0)
        try:
            c.connect((oi.LOCALHOST, port))
            c.sendall(b"garbage")
        finally:
            c.close()

        # 之后正常 SHOW 仍能触发。
        c2 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        c2.settimeout(1.0)
        try:
            c2.connect((oi.LOCALHOST, port))
            c2.sendall(oi.SHOW)
            assert c2.recv(1024) == oi.QUIT
        finally:
            c2.close()
        assert window.show_calls == 1
