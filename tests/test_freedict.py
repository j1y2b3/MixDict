"""core.sources.freedict 的单元测试(离线,用固定数据,不请求网络)。"""
import email.message
import io
import json
import urllib.error
from unittest import mock

import pytest

from mixdict.core.sources.base import APIError
from mixdict.core.sources.freedict import (
    Source as FreeDict,
    fetch_json,
    limited_page,
    parse_json,
)

# 未找到:新 API 对查无此词返回 HTTP 200 + entries 为空。
NOT_FOUND = {
    "word": "qwiruqe",
    "entries": [],
    "source": {
        "url": "https://en.wiktionary.org",
        "license": {"name": "CC BY-SA 4.0",
                    "url": "https://creativecommons.org/licenses/by-sa/4.0/"},
    },
}


def _http_error(code: int) -> urllib.error.HTTPError:
    return urllib.error.HTTPError(url="x", code=code, msg="x",
                                  hdrs=email.message.Message(), fp=io.BytesIO())


def _sense(definition, *, tags=(), examples=(), quotes=(), synonyms=(), antonyms=(), subsenses=()):
    """Build a minimal sense dict following the API shape (with recursive `subsenses`)."""
    return {
        "definition": definition,
        "tags": list(tags),
        "examples": list(examples),
        "quotes": [{"text": text, "reference": ref} for text, ref in quotes],
        "synonyms": list(synonyms),
        "antonyms": list(antonyms),
        "subsenses": list(subsenses),
    }


def _entry(part_of_speech, senses=(), pronunciations=(), forms=()):
    return {
        "partOfSpeech": part_of_speech,
        "pronunciations": list(pronunciations),
        "forms": [{"word": word, "tags": list(tags)} for word, tags in forms],
        "senses": list(senses),
    }


def _source_page(word="x"):
    return {"url": "https://en.wiktionary.org/wiki/x",
            "license": {"name": "CC BY-SA 4.0",
                        "url": "https://creativecommons.org/licenses/by-sa/4.0/"}}


class TestFetchJson:
    """fetch_json 返回 (data, is_limited),只把 429 当"限流",其余错误原样上抛。"""

    class _Resp:
        def __init__(self, content):
            self._content = content

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def read(self):
            return self._content

    def _requested_url(self, mock_urlopen) -> str:
        return mock_urlopen.call_args.args[0].full_url

    def test_found_returns_data_and_not_limited(self):
        payload = json.dumps({"word": "apple", "entries": []}).encode("utf-8")
        with mock.patch("urllib.request.urlopen", return_value=self._Resp(payload)) as m:
            data, is_limited = fetch_json("apple")
        assert is_limited is False
        assert data["word"] == "apple"

    def test_url_is_english_and_word_is_quoted(self):
        with mock.patch("urllib.request.urlopen", return_value=self._Resp(b"{}")) as m:
            fetch_json("red apple")
        url = self._requested_url(m)
        assert url.startswith("https://freedictionaryapi.com/api/v1/entries/en/")
        assert url.endswith("/red%20apple")

    def test_custom_language_in_url(self):
        with mock.patch("urllib.request.urlopen", return_value=self._Resp(b"{}")) as m:
            fetch_json("苹果", language="zh")
        assert self._requested_url(m).endswith("/zh/%E8%8B%B9%E6%9E%9C")

    def test_http_429_marks_limited(self):
        with mock.patch("urllib.request.urlopen", side_effect=_http_error(429)):
            data, is_limited = fetch_json("apple")
        assert is_limited is True
        assert isinstance(data["error"], urllib.error.HTTPError)
        assert data["error"].code == 429

    def test_http_error_other_than_429_raises(self):
        # 404/403/500 等不再转成可读 APIError,而是原样上抛(由 lookup 兜成错误页)。
        for code in (403, 404, 500):
            with mock.patch("urllib.request.urlopen", side_effect=_http_error(code)):
                with pytest.raises(urllib.error.HTTPError):
                    fetch_json("apple")

    def test_network_error_propagates(self):
        # 网络错误(URLError/超时)同样上抛,由 lookup 兜成错误页。
        with mock.patch("urllib.request.urlopen", side_effect=urllib.error.URLError("boom")):
            with pytest.raises(urllib.error.URLError):
                fetch_json("apple")


class TestParseJson:
    def test_not_found_page(self):
        d = parse_json(NOT_FOUND)
        assert d["is_found"] is False
        assert d["is_error"] is False
        assert d["word"] == "qwiruqe"
        assert [s["title"] for s in d["sections"]] == ["未找到", "来源", "API服务"]
        texts = [it["text"] for it in d["sections"][0]["items"] if it["type"] == "text"]
        assert any("没有该词或不是英语" in t for t in texts)

    def test_found_page(self, fixture_data):
        d = parse_json(fixture_data("freedictapi-apple"))
        assert d["is_found"] is True
        assert d["word"] == "apple"
        assert d["sections"][0]["title"] == "noun"

        items = d["sections"][0]["items"]
        texts = [it.get("text") for it in items if it["type"] == "text"]

        # 音标(带/不带来源标签)。
        phones = [it for it in items if it["type"] == "phonetic"]
        assert any(it["phonetic"] == "/ˈæp.əl/" and it["name"] == "" for it in phones)
        assert any(it["phonetic"] == "/ˈæp.əl/" and it["name"] == "US" for it in phones)

        # 变形。
        assert "变形" in texts
        assert "(plural) apples" in texts

        # 义项与递归子义项编号。
        assert "义项 1" in texts
        assert "A common, firm, round fruit produced by a tree of the genus Malus." in texts
        assert "义项 1.1" in texts
        assert any("The fruit of the tree Malus domestica" in t for t in texts)

        # 标签 muted。
        muted = {it["text"] for it in items
                 if it["type"] == "text" and it.get("font_style") == "muted"}
        assert {"obsolete", "transitive"} <= muted

        # 示例。
        assert "A large smile appled his full cheeks." in texts
        assert "custard apple, rose apple, thorn apple" in texts

        # 引文。
        assert any("baked apple" in t for t in texts)

        # 同义词 / 反义词。
        assert "同义词 malus" in texts
        assert "反义词 unapple" in texts

    def test_sections_order_and_links(self, fixture_data):
        d = parse_json(fixture_data("freedictapi-apple"))
        assert [s["title"] for s in d["sections"]] == ["noun", "来源", "API服务"]

        source_links = [(it["text"], it["url"]) for it in d["sections"][1]["items"]
                        if it["type"] == "link"]
        assert ("Wiktionary", "https://en.wiktionary.org/wiki/apple") in source_links
        assert ("CC BY-SA 4.0", "https://creativecommons.org/licenses/by-sa/4.0/") in source_links

        api_links = [(it["text"], it["url"]) for it in d["sections"][2]["items"]
                     if it["type"] == "link"]
        assert ("Free Dictionary API", "https://freedictionaryapi.com/") in api_links

    def test_multiple_entries_each_own_section(self):
        data = {"word": "x", "entries": [
            _entry("noun"),
            _entry("verb"),
        ], "source": _source_page()}
        d = parse_json(data)
        assert d["is_found"] is True
        assert [s["title"] for s in d["sections"]] == ["noun", "verb", "来源", "API服务"]

    def test_deep_subsenses_recursive_indexing(self):
        leaf = _sense("leaf def")
        child = _sense("child def", subsenses=[leaf])
        root = _sense("root def", subsenses=[child])
        data = {"word": "x", "entries": [_entry("n", senses=[root])], "source": _source_page()}
        d = parse_json(data)
        texts = [it["text"] for it in d["sections"][0]["items"] if it["type"] == "text"]
        assert "义项 1" in texts
        assert "义项 1.1" in texts
        assert "义项 1.1.1" in texts
        assert "leaf def" in texts

    def test_entry_without_senses_no_crash(self):
        data = {"word": "x", "entries": [_entry("n")], "source": _source_page()}
        d = parse_json(data)
        assert d["is_found"] is True
        assert d["sections"][0]["title"] == "n"


class TestLimitedPage:
    def test_limited_page_mentions_rate_limit(self):
        d = limited_page(_http_error(429), "apple")
        assert d["is_error"] is True
        assert d["is_found"] is False
        assert d["word"] == "apple"
        assert d["sections"][0]["title"] == "错误"
        texts = [it["text"] for it in d["sections"][0]["items"] if it["type"] == "text"]
        assert any("429" in t for t in texts)
        assert any("已达到限制" in t for t in texts)


class TestFreeDictSource:
    def test_identity(self):
        source = FreeDict()
        assert source.reg_name == "FreeDict"
        assert source.name == "Free Dictionary API"
        assert source.description
        assert "freedictionaryapi.com" in source.description

    def test_lookup_found(self):
        source = FreeDict()
        payload = {"word": "apple", "entries": [_entry("noun")], "source": _source_page()}
        with mock.patch("mixdict.core.sources.freedict.fetch_json",
                        return_value=(payload, False)):
            page = source.lookup("apple")
        assert page["is_found"] is True

    def test_lookup_limited(self):
        source = FreeDict()
        with mock.patch("mixdict.core.sources.freedict.fetch_json",
                        return_value=({"error": _http_error(429)}, True)):
            page = source.lookup("apple")
        assert page["is_error"] is True
        texts = [it["text"] for it in page["sections"][0]["items"] if it["type"] == "text"]
        assert any("已达到限制" in t for t in texts)

    def test_lookup_never_raises_on_api_error(self):
        source = FreeDict()
        with mock.patch.object(source, "_lookup", side_effect=APIError("boom")):
            page = source.lookup("w")
        assert page["is_error"] is True
        assert page["sections"][0]["title"] == "错误"
