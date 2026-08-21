"""SourcesRegistry tests (offline, no network)."""
import pytest

from simplenetdict import config
from simplenetdict.core.registry import SourcesRegistry
from simplenetdict.core.sources.base import DictionarySource


class FakeSource(DictionarySource):
    """A minimal source used only in tests."""

    def __init__(self, reg_name="Fake", name="假源"):
        super().__init__(reg_name, name)

    def _lookup(self, word: str) -> dict:
        return {"fake": word}


class TestSourcesRegistry:
    def test_builtin_registered(self):
        reg = SourcesRegistry()
        source, name = reg.get("Youdao")
        assert source is not None
        assert name == "有道"

    def test_default_is_youdao(self):
        reg = SourcesRegistry()
        source, name = reg.get_default()
        assert source.reg_name == "Youdao"
        assert name == "有道"

    def test_register_and_get(self):
        reg = SourcesRegistry()
        reg.register(FakeSource())
        source, name = reg.get("Fake")
        assert name == "假源"
        assert source.lookup("x") == {"fake": "x"}

    def test_duplicate_register_raises(self):
        reg = SourcesRegistry()
        with pytest.raises(ValueError):
            reg.register(FakeSource(reg_name="Youdao"))

    def test_force_overwrites(self):
        reg = SourcesRegistry()
        reg.register(FakeSource(reg_name="Youdao", name="覆盖"), force=True)
        _, name = reg.get("Youdao")
        assert name == "覆盖"

    def test_get_unknown_returns_none_none(self):
        reg = SourcesRegistry()
        assert reg.get("Nope") == (None, None)

    def test_get_all_returns_copy(self):
        reg = SourcesRegistry()
        all_ = reg.get_all()
        all_["mutated"] = (None, None)
        assert "mutated" not in reg.sources

    def test_list_returns_display_names(self):
        reg = SourcesRegistry()
        reg.register(FakeSource())
        assert set(reg.list()) == {"有道", "假源"}

    def test_change_default(self):
        reg = SourcesRegistry()
        reg.register(FakeSource())
        reg.change_default("Fake")
        source, _ = reg.get_default()
        assert source.reg_name == "Fake"

    def test_change_default_unknown_raises(self):
        reg = SourcesRegistry()
        with pytest.raises(ValueError):
            reg.change_default("Nope")

    def test_default_missing_raises(self, monkeypatch):
        monkeypatch.setattr(config, "DEFAULT_DICTIONARY_SOURCE", "Nope")
        with pytest.raises(ValueError):
            SourcesRegistry()
