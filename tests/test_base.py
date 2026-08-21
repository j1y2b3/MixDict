"""DictionarySource base tests."""
import pytest

from src.core.sources.base import DictionarySource


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
