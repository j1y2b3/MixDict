"""DictApi (window bridge) tests, using a fake source (offline)."""
import pytest

from simplenetdict.core.registry import SourcesRegistry
from simplenetdict.core.sources.base import DictionarySource
from simplenetdict.gui.window import DictApi


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

    def test_set_source_valid(self):
        api = self._make_api()
        api.set_source("Youdao")
        assert api.source.reg_name == "Youdao"
        assert api.source.name == "有道"

    def test_set_source_unknown_raises(self):
        api = self._make_api()
        with pytest.raises(ValueError):
            api.set_source("Nope")
