"""Tray(系统托盘)类的测试,通过 mock 避免真实创建/连接托盘图标。"""
import pytest

from mixdict import config, resources
from mixdict.gui.tray import Tray


class FakeIcon:
    """模拟 pystray.Icon: 记录构造参数,并跟踪 stop/run_detached。"""

    def __init__(self, *args):
        self.args = args
        self.stopped = False
        self.detached = False

    def stop(self):
        self.stopped = True

    def run_detached(self):
        self.detached = True


class FakeWindow:
    """模拟 webview.Window,记录 show/destroy 调用。"""

    def __init__(self):
        self.shown = 0
        self.destroyed = 0

    def show(self):
        self.shown += 1

    def destroy(self):
        self.destroyed += 1


def _make_tray(monkeypatch) -> tuple[Tray, FakeWindow]:
    """构造 Tray: 替换 pystray.Icon 与图标加载,菜单保持真实对象以便断言。"""
    import pystray

    icon_image = object()  # 测试不关心真实图片内容。
    monkeypatch.setattr(resources, "load_tray_icon", lambda: icon_image)
    monkeypatch.setattr(pystray, "Icon", FakeIcon)
    window = FakeWindow()
    return Tray(window), window


class TestTray:
    def test_init_creates_icon_with_title(self, monkeypatch):
        tray, _ = _make_tray(monkeypatch)
        name, image, title, menu = tray.icon.args
        assert name == "MixDict"
        assert image is not None
        assert title == config.TITLE
        assert tray.window is not None

    def test_menu_has_open_default_and_exit(self, monkeypatch):
        tray, _ = _make_tray(monkeypatch)
        name, image, title, menu = tray.icon.args
        texts = [item.text for item in menu.items]
        assert texts == ["打开", "退出"]
        open_item, exit_item = menu.items
        assert open_item.default is True  # 左键单击托盘即触发“打开”。
        assert exit_item.default is False

    def test_open_shows_window(self, monkeypatch):
        tray, window = _make_tray(monkeypatch)
        tray.open(tray.icon, None)
        assert window.shown == 1

    def test_exit_stops_icon_and_destroys_window(self, monkeypatch):
        monkeypatch.setattr(config, "TO_EXIT", False)
        tray, window = _make_tray(monkeypatch)
        tray.exit(tray.icon, None)
        assert config.TO_EXIT is True
        assert tray.icon.stopped is True
        assert window.destroyed == 1

    def test_run_detaches_icon(self, monkeypatch):
        tray, _ = _make_tray(monkeypatch)
        tray.run()
        assert tray.icon.detached is True  # 不阻塞线程(run_detached)。
