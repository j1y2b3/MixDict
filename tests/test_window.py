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
        return Window(SourcesRegistry())

    def test_get_window_returns_created(self, monkeypatch):
        fake_window = object()
        win = self._make_window(monkeypatch, fake_window)
        assert win.get_window() is fake_window

    def test_get_window_none_raises(self, monkeypatch):
        win = self._make_window(monkeypatch, None)
        with pytest.raises(RuntimeError, match="Failed to create webview window"):
            win.get_window()
