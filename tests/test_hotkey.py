"""HotKey(全局热键)类的测试。

通过替换模块级 `user32` 避免注册真实系统热键;监听循环以同步方式
直接调用 `_listen()`,不启动真实后台线程。
"""
import ctypes
import importlib
import logging
import sys
import threading

import pytest

import mixdict.hotkey as hotkey

MODS = None
if sys.platform == "win32":
    MODS = hotkey.MOD_CONTROL | hotkey.MOD_WIN | hotkey.MOD_NOREPEAT


class FakeUser32:
    """模拟 user32: 记录注册/注销,并按队列回放 GetMessageW 的消息。"""

    def __init__(self, register_ok: bool = True, message_queue=None):
        self.register_ok = register_ok
        # 队列元素: (bRet, message, wParam)
        self.message_queue = list(message_queue or [])
        self.register_calls = []
        self.unregister_calls = []

    def RegisterHotKey(self, hwnd, id, modifiers, vk):
        self.register_calls.append((hwnd, id, modifiers, vk))
        return 1 if self.register_ok else 0

    def GetMessageW(self, lp_msg, hwnd, w_min, w_max):
        b_ret, message, w_param = self.message_queue.pop(0)
        msg = getattr(lp_msg, "_obj", None)  # ctypes.byref(msg)._obj is msg
        if msg is not None:
            msg.message = message
            msg.wParam = w_param
        return b_ret

    def UnregisterHotKey(self, hwnd, id):
        self.unregister_calls.append((hwnd, id))


class FakeThread:
    """替代 threading.Thread: 捕获 target,但不真正启动后台线程。"""

    def __init__(self, target=None, daemon=None):
        self.target = target
        self.daemon = daemon

    def start(self):
        pass  # 测试中手动调用 hk._listen() 以同步执行。


class FakeWindow:
    def __init__(self):
        self.show_calls = 0

    def show(self):
        self.show_calls += 1


@pytest.fixture
def fake_user32(monkeypatch):
    fake = FakeUser32()
    monkeypatch.setattr(hotkey, "user32", fake)
    return fake


def _make_hotkey(monkeypatch, window=None):
    """构造 HotKey,但不启动真实监听线程(用 FakeThread 拦截)。"""
    monkeypatch.setattr(threading, "Thread", FakeThread)
    window = window or FakeWindow()
    hk = hotkey.HotKey(window)
    return hk, window


class TestHotKeyWindows:
    pytestmark = pytest.mark.skipif(sys.platform != "win32", reason="仅 Windows 平台")

    def test_register_hotkey_args(self, monkeypatch, fake_user32):
        hk, _ = _make_hotkey(monkeypatch)
        fake_user32.message_queue = [(0, 0, 0)]
        hk._listen()
        assert fake_user32.register_calls == [
            (None, hotkey.ON_SHOW_WINDOW, MODS, ord("T"))
        ]

    def test_wm_hotkey_triggers_show(self, monkeypatch, fake_user32):
        hk, window = _make_hotkey(monkeypatch)
        fake_user32.message_queue = [
            (1, hotkey.WM_HOTKEY, hotkey.ON_SHOW_WINDOW),
            (0, 0, 0),  # WM_QUIT → 退出循环。
        ]
        hk._listen()
        assert window.show_calls == 1

    def test_ignores_hotkey_with_other_id(self, monkeypatch, fake_user32):
        hk, window = _make_hotkey(monkeypatch)
        fake_user32.message_queue = [
            (1, hotkey.WM_HOTKEY, 999),  # 其他热键 id → 不处理。
            (0, 0, 0),
        ]
        hk._listen()
        assert window.show_calls == 0

    def test_ignores_other_messages(self, monkeypatch, fake_user32):
        hk, window = _make_hotkey(monkeypatch)
        fake_user32.message_queue = [
            (1, 0x0100, hotkey.ON_SHOW_WINDOW),  # WM_KEYDOWN,非 WM_HOTKEY。
            (0, 0, 0),
        ]
        hk._listen()
        assert window.show_calls == 0

    def test_register_failure_raises(self, monkeypatch, fake_user32):
        fake_user32.register_ok = False
        hk, _ = _make_hotkey(monkeypatch)
        # ctypes.WinError 是工厂函数(返回 WindowsError/OSError),故捕获 OSError。
        with pytest.raises(OSError):
            hk._listen()
        # 注册失败发生在 try 之外,不注销。
        assert fake_user32.unregister_calls == []

    def test_getmessage_error_raises_and_unregisters(self, monkeypatch, fake_user32):
        hk, _ = _make_hotkey(monkeypatch)
        fake_user32.message_queue = [(-1, 0, 0)]
        with pytest.raises(OSError):
            hk._listen()
        assert fake_user32.unregister_calls == [(None, hotkey.ON_SHOW_WINDOW)]

    def test_quit_breaks_and_unregisters(self, monkeypatch, fake_user32):
        hk, window = _make_hotkey(monkeypatch)
        fake_user32.message_queue = [(0, 0, 0)]
        hk._listen()
        assert fake_user32.unregister_calls == [(None, hotkey.ON_SHOW_WINDOW)]
        assert window.show_calls == 0


class TestHotKeyPlatformGuard:
    def test_hotkey_defined_only_on_windows(self, monkeypatch, caplog):
        if sys.platform == "win32":
            # 模拟非 Windows:模块应能安全导入(走 else 分支记 warning),
            # 不访问 ctypes.windll 导致崩溃。
            monkeypatch.setattr(sys, "platform", "linux")
            with caplog.at_level(logging.WARNING, logger="mixdict.hotkey"):
                importlib.reload(hotkey)
            assert any("not supported platform" in r.message for r in caplog.records)
            # 恢复 win32 分支,避免影响其他测试。
            monkeypatch.setattr(sys, "platform", "win32")
            importlib.reload(hotkey)
            assert hasattr(hotkey, "HotKey")
        else:
            assert not hasattr(hotkey, "HotKey")
