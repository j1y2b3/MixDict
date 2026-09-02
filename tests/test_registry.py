"""SourcesRegistry tests (offline, no network)."""
import pytest

from simplenetdict import config
from simplenetdict.core.registry import SourcesRegistry
from simplenetdict.core.sources.base import DictionarySource

pytestmark = pytest.mark.usefixtures("isolated_user_sources")


class FakeSource(DictionarySource):
    """A minimal source used only in tests."""

    def __init__(self, reg_name="Fake", name="假源"):
        super().__init__(reg_name, name)

    def _lookup(self, word: str) -> dict:
        return {"fake": word}


class TestSourcesRegistry:
    def test_builtin_registered(self):
        reg = SourcesRegistry()
        source = reg.get("Youdao")
        assert source is not None
        assert source.name == "有道"

    def test_default_matches_config(self):
        reg = SourcesRegistry()
        source = reg.get(reg.default_source_reg_name)
        assert source.reg_name == config.DEFAULT_DICTIONARY_SOURCE

    def test_register_and_get(self):
        reg = SourcesRegistry()
        reg.register(FakeSource())
        source = reg.get("Fake")
        assert source.name == "假源"
        assert source.lookup("x") == {"fake": "x"}

    def test_duplicate_register_raises(self):
        reg = SourcesRegistry()
        with pytest.raises(ValueError):
            reg.register(FakeSource(reg_name="Youdao"))

    def test_force_overwrites_non_builtin(self):
        reg = SourcesRegistry()
        reg.register(FakeSource(reg_name="Fake"))
        reg.register(FakeSource(reg_name="Fake", name="覆盖"), force=True)
        source = reg.get("Fake")
        assert source.name == "覆盖"

    def test_force_cannot_overwrite_builtin(self):
        reg = SourcesRegistry()
        with pytest.raises(ValueError):
            reg.register(FakeSource(reg_name="Youdao", name="覆盖"), force=True)

    def test_cannot_unregister_builtin(self):
        reg = SourcesRegistry()
        with pytest.raises(ValueError):
            reg.unregister("Youdao")

    def test_get_unknown_returns_none(self):
        reg = SourcesRegistry()
        assert reg.get("Nope") is None

    def test_get_all_returns_copy(self):
        reg = SourcesRegistry()
        all_ = reg.get_all()
        all_["mutated"] = None
        assert "mutated" not in reg.sources

    def test_list_returns_reg_names(self):
        reg = SourcesRegistry()
        reg.register(FakeSource())
        assert set(reg.list()) == {"Youdao", "FreeDict", "Fake"}

    def test_change_default(self):
        reg = SourcesRegistry()
        reg.register(FakeSource())
        reg.change_default("Fake")
        source = reg.get(reg.default_source_reg_name)
        assert source.reg_name == "Fake"

    def test_change_default_unknown_raises(self):
        reg = SourcesRegistry()
        with pytest.raises(ValueError):
            reg.change_default("Nope")

    def test_default_missing_raises(self, monkeypatch):
        monkeypatch.setattr(config, "DEFAULT_DICTIONARY_SOURCE", "Nope")
        with pytest.raises(ValueError):
            SourcesRegistry()

    def test_user_sources_reg_map_always_exists(self):
        # 无论 DEBUG 与否,registry 总提供热更新账目,避免 watcher 线程 AttributeError。
        reg = SourcesRegistry()
        assert reg.user_sources_reg_map == {}

    def test_register_users_records_map(self, monkeypatch, tmp_path):
        from simplenetdict import resources

        plugin_dir = tmp_path / "plugins"
        plugin_dir.mkdir()
        plugin = plugin_dir / "demo.py"
        plugin.write_text(
            "from simplenetdict.core.sources.base import DictionarySource\n"
            "\n"
            "\n"
            "class Source(DictionarySource):\n"
            "    def __init__(self):\n"
            "        super().__init__(reg_name='Demo', name='演示')\n"
            "\n"
            "    def _lookup(self, word: str) -> dict:\n"
            "        return {'word': word}\n",
            encoding="utf-8",
        )
        monkeypatch.setattr(resources, "user_sources_dir", lambda: plugin_dir)

        reg = SourcesRegistry()
        assert reg.user_sources_reg_map[plugin] == "Demo"
        assert reg.get("Demo") is not None
        assert "Demo" in reg.list()
