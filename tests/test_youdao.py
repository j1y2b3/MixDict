"""core.youdao 的单元测试(离线,用固定 fixture,不请求网络)。"""
import email.message
import json
import urllib.error
from unittest import mock

import pytest

from mixdict.core.sources.base import APIError
from mixdict.core.sources.youdao import Source as Youdao, fetch_json, parse_json, safe_get


# ---- 模拟有道 jsonapi 返回的 fixture ----

FOUND = {
    "input": "apple",
    "meta": {"isHasSimpleDict": "1"},
    "ec": {
        "source": {"name": "有道词典"},
        "word": [{
            "usphone": "ˈæp(ə)l",
            "ukphone": "ˈæp(ə)l",
            "usspeech": "apple&type=2",
            "ukspeech": "apple&type=1",
            "trs": [
                {"tr": [{"l": {"i": ["n. 苹果"]}}]},
                {"tr": [{"l": {"i": ["n. 苹果树"]}}]},
            ],
        }],
    },
}

NOT_FOUND = {
    "input": "qwiruqe",
    "meta": {"isHasSimpleDict": "0"},
    "typos": {"typo": [
        {"word": "quire", "trans": "n. 一刀"},
        {"word": "cirque", "trans": "n. 圆环"},
    ]},
}

# 缺发音字段(usspeech/ukspeech)的健壮性用例
NO_SPEECH = {
    "input": "x",
    "meta": {"isHasSimpleDict": "1"},
    "ec": {"word": [{
        "usphone": "x",
        "ukphone": "x",
        "trs": [{"tr": [{"l": {"i": ["n. 缺发音"]}}]}],
    }]},
}

# 缺 trs 的健壮性用例
NO_TRS = {
    "input": "y",
    "meta": {"isHasSimpleDict": "1"},
    "ec": {"word": [{
        "usphone": "y", "usspeech": "y&type=2",
        "ukphone": "y", "ukspeech": "y&type=1",
    }]},
}


class TestSafeGet:
    def test_normal_dict(self):
        assert safe_get({"a": {"b": 1}}, ("a", "b")) == 1

    def test_missing_key_returns_default(self):
        assert safe_get({"a": 1}, ("a", "b")) is None
        assert safe_get({"a": 1}, ("a", "b"), default="X") == "X"

    def test_list_index(self):
        assert safe_get({"l": [10, 20, 30]}, ("l", 1)) == 20

    def test_index_out_of_range(self):
        assert safe_get({"l": [10]}, ("l", 5)) is None
        assert safe_get({"l": [10]}, ("l", -5)) is None

    def test_negative_index(self):
        assert safe_get({"l": [10, 20]}, ("l", -1)) == 20

    def test_type_mismatch(self):
        assert safe_get({"a": 1}, (0,)) is None      # int 索引 dict
        assert safe_get([1, 2], ("a",)) is None       # str 索引 list

    def test_empty_path(self):
        assert safe_get({"a": 1}, ()) == {"a": 1}


class TestParseJson:
    def test_found_word(self):
        d = parse_json(FOUND)
        assert d["is_found"] is True
        assert d["word"] == "apple"
        assert d["sections"][0]["title"] == "英汉"
        items = d["sections"][0]["items"]
        assert items[0]["type"] == "phonetic"
        assert items[0]["name"] == "美式发音"
        assert items[0]["phonetic"] == "/ˈæp(ə)l/"
        assert items[0]["audio_url"] == "https://dict.youdao.com/dictvoice?audio=apple&type=2"
        texts = [it["text"] for it in items if it["type"] == "text"]
        assert texts == ["n. 苹果", "n. 苹果树"]

    def test_not_found_with_typos(self):
        d = parse_json(NOT_FOUND)
        assert d["is_found"] is False
        assert d["word"] == "qwiruqe"
        texts = [it["text"] for it in d["sections"][0]["items"] if it["type"] == "text"]
        assert any("quire" in t for t in texts)
        assert any("cirque" in t for t in texts)
        assert any("qwiruqe" in t for t in texts)  # 提示里带查询词,而不是 "None"

    def test_no_speech_does_not_crash(self):
        d = parse_json(NO_SPEECH)
        assert d["is_found"] is True
        audio = [it["audio_url"] for it in d["sections"][0]["items"]
                 if it["type"] == "phonetic"]
        assert len(audio) == 2
        assert all(a is None for a in audio)  # 缺发音时 audio_url 为 None,而非拼坏的 URL

    def test_no_trs_does_not_crash(self):
        d = parse_json(NO_TRS)
        assert d["is_found"] is True
        types = [it["type"] for it in d["sections"][0]["items"]]
        # ec 分支末尾新增来源链接(7220990),缺 trs 时只剩音标 + 链接,不崩。
        assert types == ["phonetic", "phonetic", "link"]

    def test_missing_us_phonetic_skipped(self):
        # e9b01ef:有道 API 可能返回无美式发音的释义,缺 usphone 不再抛错,仅跳过美式音标。
        data = {
            "input": "z",
            "meta": {"isHasSimpleDict": "1"},
            "ec": {"word": [{"ukphone": "z"}]},
        }
        d = parse_json(data)
        assert d["is_found"] is True
        names = [it["name"] for it in d["sections"][0]["items"] if it["type"] == "phonetic"]
        assert "英式发音" in names
        assert "美式发音" not in names

    def test_missing_uk_phonetic_skipped(self):
        # 对称:缺 ukphone 时仅保留美式音标。
        data = {
            "input": "z",
            "meta": {"isHasSimpleDict": "1"},
            "ec": {"word": [{"usphone": "z"}]},
        }
        d = parse_json(data)
        assert d["is_found"] is True
        names = [it["name"] for it in d["sections"][0]["items"] if it["type"] == "phonetic"]
        assert "美式发音" in names
        assert "英式发音" not in names

    def test_empty_data_returns_empty_found_page(self):
        # ec/ce 条件化后:空响应不再抛,返回空 found 页(锁当前行为)
        d = parse_json({})
        assert d["is_found"] is True
        assert d["word"] is None
        assert d["sections"] == []

    def test_ec_empty_no_crash(self):
        # e9b01ef:ec 结构为空不再因缺音标抛错,返回 found 页且无音标/释义(锁当前行为)。
        data = {"input": "x", "meta": {"isHasSimpleDict": "1"}, "ec": {}}
        d = parse_json(data)
        assert d["is_found"] is True
        assert d["word"] == "x"
        content = [it for it in d["sections"][0]["items"] if it["type"] in ("phonetic", "text")]
        assert content == []

    def test_ec_word_empty_list_no_crash(self):
        # 对称:word 为空列表时同 ec:{}。
        data = {"input": "x", "meta": {"isHasSimpleDict": "1"}, "ec": {"word": []}}
        d = parse_json(data)
        assert d["is_found"] is True
        assert d["word"] == "x"
        content = [it for it in d["sections"][0]["items"] if it["type"] in ("phonetic", "text")]
        assert content == []

    def test_non_dict_root_does_not_crash(self):
        # 非 dict 结构(如 list 根):无 ec/ce → 不抛,返回空 found 页(锁当前行为)
        d = parse_json([1, 2])
        assert d["is_found"] is True
        assert d["word"] is None
        assert d["sections"] == []

    def test_not_found_without_input_word_is_none(self):
        # 查无此词但缺 input:is_found=False,word 为 None,不崩
        d = parse_json({"meta": {"isHasSimpleDict": "0"}})
        assert d["is_found"] is False
        assert d["word"] is None

    def test_trs_not_list_does_not_crash(self):
        # trs 结构异常(是 dict 而非 list)时:不崩,释义输出 None(锁当前行为)
        data = {
            "input": "x",
            "meta": {"isHasSimpleDict": "1"},
            "ec": {"word": [{
                "usphone": "u", "usspeech": "u&type=2",
                "ukphone": "k", "ukspeech": "k&type=1",
                "trs": {"oops": 1},
            }]},
        }
        d = parse_json(data)
        assert d["is_found"] is True
        texts = [it["text"] for it in d["sections"][0]["items"] if it["type"] == "text"]
        assert texts == [None]

    def test_tr_missing_l_does_not_crash(self):
        # tr 里缺 l/i 结构时:输出 None 而非崩溃(锁当前行为)
        data = {
            "input": "x",
            "meta": {"isHasSimpleDict": "1"},
            "ec": {"word": [{
                "usphone": "u", "usspeech": "u&type=2",
                "ukphone": "k", "ukspeech": "k&type=1",
                "trs": [{"tr": [{"l": {"i": []}}]}],
            }]},
        }
        d = parse_json(data)
        texts = [it["text"] for it in d["sections"][0]["items"] if it["type"] == "text"]
        assert texts == [None]

    def test_empty_string_phonetic_locked_behavior(self):
        # 空字符串音标:当前行为是 "//" 和拼坏的 audio_url(待改进,先锁行为)
        data = {
            "input": "x",
            "meta": {"isHasSimpleDict": "1"},
            "ec": {"word": [{"usphone": "", "usspeech": "", "ukphone": "", "ukspeech": ""}]},
        }
        d = parse_json(data)
        phonetics = [it for it in d["sections"][0]["items"] if it["type"] == "phonetic"]
        assert all(it["phonetic"] == "//" for it in phonetics)
        assert all(it["audio_url"] == "https://dict.youdao.com/dictvoice?audio=" for it in phonetics)

    def test_chinese_ce_branch(self, fixture_data):
        # 中文词条(pingguo.json 抓包):无 ec 走 ce 分支,输出"汉英"section。
        d = parse_json(fixture_data("pingguo"))
        assert d["is_found"] is True
        assert d["word"] == "苹果"
        assert d["sections"][0]["title"] == "汉英"
        assert d["sections"][0]["items"] == [
            {"type": "text", "text": "apple", "font_style": "stress"},
            {"type": "text", "text": "苹果；", "font_style": "normal"},
        ]


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

    def test_valid_json_dict(self):
        payload = json.dumps({"input": "apple"}).encode("utf-8")
        with mock.patch("urllib.request.urlopen", return_value=self._Resp(payload)):
            assert fetch_json("apple") == {"input": "apple"}

    def test_non_dict_root_raises(self):
        payload = json.dumps([1, 2]).encode("utf-8")
        with mock.patch("urllib.request.urlopen", return_value=self._Resp(payload)):
            with pytest.raises(APIError, match="Unexpected JSON root type"):
                fetch_json("apple")

    def test_invalid_json_raises(self):
        # 响应体不是合法 JSON:json.loads 抛 JSONDecodeError(被 lookup() 吞掉)
        with mock.patch("urllib.request.urlopen", return_value=self._Resp(b"<html>oops</html>")):
            with pytest.raises(json.JSONDecodeError):
                fetch_json("apple")

    def test_http_error_propagates(self):
        # 有道未特殊处理 HTTPError:直接向上抛(由 lookup() 吞成错误页,锁当前行为)
        err = urllib.error.HTTPError(url="x", code=503, msg="Service Unavailable",
                                     hdrs=email.message.Message(), fp=None)
        with mock.patch("urllib.request.urlopen", side_effect=err):
            with pytest.raises(urllib.error.HTTPError):
                fetch_json("apple")


class TestYoudaoSource:
    def test_identity(self):
        source = Youdao()
        assert source.reg_name == "Youdao"
        assert source.name == "有道"

    def test_lookup_returns_schema(self):
        source = Youdao()
        with mock.patch.object(source, "_lookup", return_value={"ok": 1}):
            assert source.lookup("w") == {"ok": 1}

    def test_lookup_never_raises(self):
        source = Youdao()
        with mock.patch.object(source, "_lookup", side_effect=RuntimeError("boom")):
            page = source.lookup("w")
        assert page["is_found"] is False
        assert page["sections"][0]["title"] == "错误"

    def test_lookup_never_raises_on_api_error(self):
        source = Youdao()
        with mock.patch.object(source, "_lookup", side_effect=APIError("boom")):
            page = source.lookup("w")
        assert page["is_found"] is False
        assert page["sections"][0]["title"] == "错误"


class TestRealFixtures:
    """Tests against saved real API responses (tests/fixtures/, offline)."""

    def test_apple_fixture_found(self, fixture_data):
        d = parse_json(fixture_data("apple"))
        assert d["is_found"] is True
        assert d["word"] == "apple"
        assert any(s["title"] == "英汉" for s in d["sections"])
        items = next(s for s in d["sections"] if s["title"] == "英汉")["items"]
        assert any(it["type"] == "phonetic" for it in items)
        assert any(it["type"] == "text" for it in items)

    def test_qwiruqe_fixture_not_found(self, fixture_data):
        d = parse_json(fixture_data("qwiruqe"))
        assert d["is_found"] is False
        assert d["word"] == "qwiruqe"
        texts = " ".join(it["text"] for s in d["sections"] for it in s["items"])
        assert "quire" in texts
        assert "cirque" in texts

    def test_buzhidao_fixture_typos(self, fixture_data):
        d = parse_json(fixture_data("buzhidao"))
        assert d["is_found"] is False
        texts = " ".join(it["text"] for s in d["sections"] for it in s["items"])
        assert "不知道" in texts
