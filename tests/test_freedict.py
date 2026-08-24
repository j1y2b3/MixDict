"""core.sources.freedict 的单元测试(离线,用固定数据,不请求网络)。"""
import email.message
import io
import json
import urllib.error
from unittest import mock

import pytest

from simplenetdict.core.sources.base import APIError
from simplenetdict.core.sources.freedict import FreeDict, fetch_json, parse_json

NOT_FOUND = {
    "isfound": False,
    "word": "qwiruqe",
    "title": "No Definitions Found",
    "message": "Sorry pal, we couldn't find definitions for the word you were looking for.",
    "resolution": "You can try the search again at later time or head to the web instead.",
}


class TestFetchJson:
    class _Resp:
        def __init__(self, content):
            self._content = content

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def read(self):
            return self._content

    def _http_error(self, code: int, body: bytes = b"") -> urllib.error.HTTPError:
        return urllib.error.HTTPError(url="x", code=code, msg="x",
                                      hdrs=email.message.Message(), fp=io.BytesIO(body))

    def test_found_returns_dict_with_isfound(self):
        payload = json.dumps([{"word": "apple"}]).encode("utf-8")
        with mock.patch("urllib.request.urlopen", return_value=self._Resp(payload)):
            data = fetch_json("apple")
        assert data["isfound"] is True
        assert data["word"] == "apple"

    def test_not_found_404(self):
        body = json.dumps({
            "title": "No Definitions Found",
            "message": "Sorry pal, we couldn't find definitions.",
            "resolution": "Try again later.",
        }).encode("utf-8")
        with mock.patch("urllib.request.urlopen", side_effect=self._http_error(404, body)):
            data = fetch_json("qwiruqe")
        assert data["isfound"] is False
        assert data["word"] == "qwiruqe"
        assert data["title"] == "No Definitions Found"

    def test_server_error_raises_api_error(self):
        with mock.patch("urllib.request.urlopen", side_effect=self._http_error(502)):
            with pytest.raises(APIError, match="502"):
                fetch_json("apple")


class TestParseJson:
    def test_not_found_page(self):
        d = parse_json(NOT_FOUND)
        assert d["is_found"] is False
        assert d["is_error"] is False
        assert d["word"] == "qwiruqe"
        assert d["sections"][0]["title"] == "No Definitions Found"
        texts = [it["text"] for it in d["sections"][0]["items"] if it["type"] == "text"]
        assert any("Sorry pal" in t for t in texts)

    def test_found_page(self, fixture_data):
        d = parse_json(fixture_data("freedict-apple"))
        assert d["is_found"] is True
        assert d["word"] == "apple"
        assert d["sections"][0]["title"] == "Result"
        items = d["sections"][0]["items"]
        types = [it["type"] for it in items]
        assert "phonetic" in types
        assert "link" in types
        assert any(it["type"] == "text" and it.get("text") for it in items)


class TestFreeDictSource:
    def test_identity(self):
        source = FreeDict()
        assert source.reg_name == "FreeDict"
        assert source.name == "Free Dictionary API"
        assert source.description

    def test_lookup_returns_schema(self):
        source = FreeDict()
        with mock.patch.object(source, "_lookup", return_value={"ok": 1}):
            assert source.lookup("w") == {"ok": 1}

    def test_lookup_never_raises_on_api_error(self):
        source = FreeDict()
        with mock.patch.object(source, "_lookup", side_effect=APIError("boom")):
            page = source.lookup("w")
        assert page["is_error"] is True
        assert page["sections"][0]["title"] == "错误"
