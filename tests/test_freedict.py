"""core.sources.freedict 的单元测试(离线,用固定数据,不请求网络)。"""
import email.message
import io
import json
import urllib.error
from unittest import mock

import pytest

from mixdict.core.sources.base import APIError
from mixdict.core.sources.freedict import Source as FreeDict, fetch_json, parse_json

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

    def test_server_error_raises_api_error(self, caplog):
        import logging

        with mock.patch("urllib.request.urlopen", side_effect=self._http_error(502)):
            with caplog.at_level(logging.WARNING, logger="mixdict"):
                with pytest.raises(APIError, match="502"):
                    fetch_json("apple")
        assert any("FreeDict API HTTP 502" in record.message for record in caplog.records)

    def test_other_http_error_raises_api_error(self):
        # 非 404 的 4xx(如 429)与 5xx 一样转成可读的 APIError
        with mock.patch("urllib.request.urlopen", side_effect=self._http_error(429)):
            with pytest.raises(APIError, match="429"):
                fetch_json("apple")

    def test_empty_list_root_raises_api_error(self):
        # 成功分支根是空列表:转成可读的 APIError
        with mock.patch("urllib.request.urlopen", return_value=self._Resp(b"[]")):
            with pytest.raises(APIError, match="expected a non-empty list"):
                fetch_json("apple")

    def test_dict_root_raises_api_error(self):
        # 成功分支根是 dict 而非 list:转成可读的 APIError
        with mock.patch("urllib.request.urlopen", return_value=self._Resp(b'{"word": "apple"}')):
            with pytest.raises(APIError, match="expected a non-empty list"):
                fetch_json("apple")

    def test_404_non_json_body_raises_api_error(self):
        # 404 响应体不是 JSON:转成可读的 APIError
        with mock.patch("urllib.request.urlopen",
                        side_effect=self._http_error(404, b"<html>not found</html>")):
            with pytest.raises(APIError, match="404 with non-JSON body"):
                fetch_json("apple")

    def test_404_non_dict_body_raises_api_error(self):
        # 404 响应体是合法 JSON 但不是 dict:转成可读的 APIError
        with mock.patch("urllib.request.urlopen",
                        side_effect=self._http_error(404, b"[1, 2]")):
            with pytest.raises(APIError, match="404 with unexpected body"):
                fetch_json("apple")

    def test_multi_item_list_takes_first(self):
        # 成功分支取列表第一个元素
        with mock.patch("urllib.request.urlopen",
                        return_value=self._Resp(b'[{"word": "a"}, {"word": "b"}]')):
            assert fetch_json("apple")["word"] == "a"


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
        assert d["sections"][0]["title"] == "结果"
        items = d["sections"][0]["items"]
        types = [it["type"] for it in items]
        assert "phonetic" in types
        assert "link" in types
        assert any(it["type"] == "text" and it.get("text") for it in items)

    def test_empty_data_not_found(self):
        # 空响应:is_found=False,word/title 为 None,不崩(锁当前行为)
        d = parse_json({})
        assert d["is_found"] is False
        assert d["is_error"] is False
        assert d["word"] is None
        assert d["sections"][0]["title"] is None

    def test_found_minimal(self):
        # 只有 isfound/word:is_found=True,至少有一个空 text 项,不崩
        d = parse_json({"isfound": True, "word": "x"})
        assert d["is_found"] is True
        assert d["word"] == "x"
        assert d["sections"][0]["title"] == "结果"
        assert d["sections"][0]["items"]

    def test_found_no_meanings_has_phonetic(self):
        # 有 phonetic 无 meanings:正常输出音标,不崩
        d = parse_json({"isfound": True, "word": "x",
                        "phonetics": [{"text": "/x/"}], "meanings": []})
        types = [it["type"] for it in d["sections"][0]["items"]]
        assert "phonetic" in types

    def test_synonyms_none_does_not_crash(self):
        # synonyms/antonyms 为 None 时跳过,释义正常输出,不崩
        data = {"isfound": True, "word": "x", "meanings": [{
            "partOfSpeech": "n", "synonyms": None, "antonyms": None,
            "definitions": [{"definition": "d"}],
        }]}
        d = parse_json(data)
        texts = [it["text"] for it in d["sections"][0]["items"] if it["type"] == "text"]
        assert "d" in texts

    def test_no_word_key_word_none(self):
        # 缺 word 键:word 为 None,is_found=True,不崩(锁当前行为)
        d = parse_json({"isfound": True})
        assert d["is_found"] is True
        assert d["word"] is None


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
