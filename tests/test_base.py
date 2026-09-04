"""DictionarySource base tests."""
import pytest

from mixdict.core.sources.base import DictionarySource


class GoodSource(DictionarySource):
    def __init__(self):
        super().__init__(reg_name="Good", name="好源")

    def _lookup(self, word: str) -> dict:
        return {"ok": word}


class BadSource(DictionarySource):
    def __init__(self):
        super().__init__(reg_name="Bad", name="坏源")

    def _lookup(self, word: str) -> dict:
        raise RuntimeError("boom")


class TestDictionarySource:
    def test_abstract_cannot_instantiate(self):
        with pytest.raises(TypeError):
            DictionarySource("x", "y")

    def test_non_ascii_reg_name_raises(self):
        class NonAscii(DictionarySource):
            def _lookup(self, word: str) -> dict:
                return {}

        with pytest.raises(ValueError):
            NonAscii("中文", "显示名")

    def test_lookup_happy_path(self):
        assert GoodSource().lookup("w") == {"ok": "w"}

    def test_lookup_never_raises_on_error(self):
        page = BadSource().lookup("w")
        assert page["is_found"] is False
        assert page["word"] == "w"
        assert page["sections"][0]["title"] == "错误"
        text = page["sections"][0]["items"][0]["text"]
        assert "RuntimeError" in text
        assert "boom" in text

    def test_lookup_error_is_logged(self, caplog):
        import logging

        with caplog.at_level(logging.ERROR, logger="mixdict"):
            BadSource().lookup("w")
        assert any("lookup() failed" in record.message for record in caplog.records)

    def test_description_defaults_empty(self):
        assert GoodSource().description == ""

    def test_description_custom(self):
        class DescSource(DictionarySource):
            def __init__(self):
                super().__init__(reg_name="Desc", name="描述源", description="自定义描述")

            def _lookup(self, word: str) -> dict:
                return {}

        assert DescSource().description == "自定义描述"

    def test_dev_mode_error_hook(self, monkeypatch):
        from mixdict import config

        monkeypatch.setattr(config, "DEBUG", True)
        page = GoodSource().lookup("$test-error-display")
        assert page["is_error"] is True
        assert page["sections"][0]["title"] == "错误"

    def test_dev_mode_hook_only_for_test_word(self, monkeypatch):
        from mixdict import config

        monkeypatch.setattr(config, "DEBUG", True)
        assert GoodSource().lookup("w") == {"ok": "w"}

    def test_dev_mode_re_raises_error(self, monkeypatch):
        from mixdict import config

        monkeypatch.setattr(config, "DEBUG", True)
        with pytest.raises(RuntimeError, match="boom"):
            BadSource().lookup("w")

    def test_safe_get_missing_returns_default(self):
        from mixdict.core.sources.base import safe_get

        assert safe_get({"a": 1}, ("a", "b")) is None
        assert safe_get({"a": 1}, ("a", "b"), default="X") == "X"

    def test_safe_get_nested(self):
        from mixdict.core.sources.base import safe_get

        assert safe_get({"a": {"b": [1, 2]}}, ("a", "b", 1)) == 2
