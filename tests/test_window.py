"""DictApi (window bridge) tests, using a fake source (offline)."""
import pytest

from mixdict.core.registry import SourcesRegistry
from mixdict.core.sources.base import DictionarySource
from mixdict.gui.window import DictApi

pytestmark = pytest.mark.usefixtures("isolated_user_sources")


class FakeSource(DictionarySource):
    def __init__(self):
        super().__init__(reg_name="Fake", name="假源")

    def _lookup(self, word: str) -> dict:
        return {"fake": word}


class TestDictApi:
    def _make_api(self) -> DictApi:
        reg = SourcesRegistry()
        reg.register(FakeSource())
        reg.change_default("Fake")
        return DictApi(reg)

    def test_list_sources_reg_name(self):
        api = self._make_api()
        assert "Fake" in api.list_sources_reg_name()
        assert "Youdao" in api.list_sources_reg_name()

    def test_lookup(self):
        api = self._make_api()
        assert api.lookup("w") == {"fake": "w"}

    def test_set_current_source_valid(self):
        api = self._make_api()
        api.set_current_source("Youdao")
        assert api.source.reg_name == "Youdao"
        assert api.source.name == "有道"

    def test_set_current_source_unknown_raises(self):
        api = self._make_api()
        with pytest.raises(ValueError):
            api.set_current_source("Nope")

    def test_get_source_name_unknown_returns_none(self):
        api = self._make_api()
        assert api.get_source_name("Nope") is None

    def test_get_source_description_unknown_returns_empty(self):
        api = self._make_api()
        assert api.get_source_description("Nope") == ""

    def test_get_source_description_known_source(self):
        api = self._make_api()
        assert api.get_source_description("FreeDict")  # FreeDict 有描述
        assert api.get_source_description("Youdao") == ""  # 有道无描述


class _FakeClosingEvent:
    """模拟 pywebview 的 `events.closing`,支持 `+=` 注册 handler。"""

    def __init__(self):
        self.handlers = []

    def __iadd__(self, handler):
        self.handlers.append(handler)
        return self


class _Events:
    def __init__(self):
        self.closing = _FakeClosingEvent()


class _FakeWebviewWindow:
    """模拟 webview.Window: 记录 hide() 并暴露 events.closing。"""

    def __init__(self):
        self.events = _Events()
        self.hide_calls = 0

    def hide(self):
        self.hide_calls += 1


class TestWindow:
    """Window(GUI 窗口)类的测试,通过 mock 避免真实创建窗口。"""

    def _make_window(self, monkeypatch, create_result):
        import webview
        from mixdict.gui.window import Window

        class FakeScreen:
            width = 1920
            height = 1080

        monkeypatch.setattr(webview, "screens", [FakeScreen()])
        monkeypatch.setattr(webview, "create_window", lambda **kwargs: create_result)
        return Window(SourcesRegistry()), create_result

    def test_window_property_returns_created(self, monkeypatch):
        fake = _FakeWebviewWindow()
        win, returned = self._make_window(monkeypatch, fake)
        assert returned is fake
        assert win.window is fake

    def test_window_creation_cancelled_raises(self, monkeypatch):
        # create_window 返回 None(创建被取消)时,__init__ 阶段即抛错。
        with pytest.raises(RuntimeError, match="Failed to create webview window"):
            self._make_window(monkeypatch, None)

    def test_create_window_starts_hidden(self, monkeypatch):
        # 后台驻留:窗口应以 hidden=True 启动。
        import webview
        from mixdict.gui.window import Window

        class FakeScreen:
            width = 1920
            height = 1080

        captured = {}
        monkeypatch.setattr(webview, "screens", [FakeScreen()])
        monkeypatch.setattr(webview, "create_window", lambda **kwargs: captured.update(kwargs) or _FakeWebviewWindow())
        Window(SourcesRegistry())
        assert captured["hidden"] is True

    def test_closing_handler_registered(self, monkeypatch):
        fake = _FakeWebviewWindow()
        win, _ = self._make_window(monkeypatch, fake)
        assert fake.events.closing.handlers == [win._on_closing]

    def test_on_closing_hides_and_cancels_close(self, monkeypatch):
        # 点 X 关闭 → 隐藏窗口并取消关闭(除非正在退出)。
        from mixdict import config

        monkeypatch.setattr(config, "TO_EXIT", False)
        fake = _FakeWebviewWindow()
        win, _ = self._make_window(monkeypatch, fake)
        assert win._on_closing() is False
        assert fake.hide_calls == 1

    def test_on_closing_allows_exit(self, monkeypatch):
        # 托盘“退出”已置 TO_EXIT → 放行真正的关闭。
        from mixdict import config

        monkeypatch.setattr(config, "TO_EXIT", True)
        fake = _FakeWebviewWindow()
        win, _ = self._make_window(monkeypatch, fake)
        assert win._on_closing() is None
        assert fake.hide_calls == 0
