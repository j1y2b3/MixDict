"""DictApi (window bridge) tests, using a fake source (offline)."""
import pytest

from src.core.registry import SourcesRegistry
from src.core.sources.base import DictionarySource
from src.gui.window import DictApi


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

    def test_list_sources(self):
        api = self._make_api()
        assert "假源" in api.list_sources()
        assert "有道" in api.list_sources()

    def test_lookup(self):
        api = self._make_api()
        assert api.lookup("w") == {"fake": "w"}

    def test_change_source_valid(self):
        api = self._make_api()
        api.change_source("Youdao")
        assert api.source.reg_name == "Youdao"
        assert api.source_name == "有道"

    def test_change_source_unknown_raises(self):
        api = self._make_api()
        with pytest.raises(ValueError):
            api.change_source("Nope")
