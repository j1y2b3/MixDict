"""schema(部件工厂)的单元测试。"""
from simplenetdict import schema


class TestSchema:
    def test_page_meta_basic(self):
        page = schema.PageMeta("apple", True)
        assert page.get() == {"is_found": True, "is_error": False, "word": "apple", "sections": []}

    def test_page_not_found(self):
        page = schema.PageMeta("qwiruqe", False)
        assert page.get()["is_found"] is False
        assert page.get()["is_error"] is False
        assert page.get()["word"] == "qwiruqe"

    def test_section_text_items(self):
        sec = schema.SectionMeta("英汉")
        sec.add_text("n. 苹果").add_text("n. 苹果树")
        assert sec.get() == {
            "title": "英汉",
            "items": [
                {"type": "text", "text": "n. 苹果", "font_style": "normal"},
                {"type": "text", "text": "n. 苹果树", "font_style": "normal"},
            ],
        }

    def test_add_text_font_style(self):
        sec = schema.SectionMeta("英汉")
        sec.add_text("n. 苹果", font_style="stress")
        assert sec.get()["items"][0]["font_style"] == "stress"

    def test_add_phonetic_check_exist(self):
        sec = schema.SectionMeta("发音")
        sec.add_phonetic("/ˈæp(ə)l/", check_exist=True)
        sec.add_phonetic("/ˈæp(ə)l/", check_exist=True)
        sec.add_phonetic("/bænənə/", check_exist=True)
        phonetics = [it["phonetic"] for it in sec.get()["items"]]
        assert phonetics == ["/ˈæp(ə)l/", "/bænənə/"]

    def test_add_phonetic(self):
        sec = schema.SectionMeta("发音")
        sec.add_phonetic("ˈæp(ə)l", "美", "https://example/a.mp3")
        assert sec.get()["items"][0] == {
            "type": "phonetic",
            "name": "美",
            "phonetic": "ˈæp(ə)l",
            "audio_url": "https://example/a.mp3",
        }

    def test_add_phonetic_no_audio(self):
        sec = schema.SectionMeta("发音")
        sec.add_phonetic("ˈæp(ə)l", "美")
        assert sec.get()["items"][0]["audio_url"] is None

    def test_add_phonetic_no_name(self):
        sec = schema.SectionMeta("发音")
        sec.add_phonetic("/ˈæp(ə)l/")
        assert sec.get()["items"][0] == {
            "type": "phonetic",
            "phonetic": "/ˈæp(ə)l/",
            "name": None,
            "audio_url": None,
        }

    def test_add_link(self):
        sec = schema.SectionMeta("来源")
        sec.add_link("维基词典", "https://en.wiktionary.org/wiki/apple")
        assert sec.get()["items"][0] == {
            "type": "link",
            "text": "维基词典",
            "url": "https://en.wiktionary.org/wiki/apple",
        }

    def test_add_link_returns_self(self):
        sec = schema.SectionMeta("来源")
        assert sec.add_link("维基词典", "https://en.wiktionary.org/wiki/apple") is sec

    def test_page_add_section(self):
        page = schema.PageMeta("apple", True)
        page.add_section(schema.SectionMeta("英汉").add_text("n. 苹果"))
        assert page.get()["sections"][0]["title"] == "英汉"
        assert page.get()["sections"][0]["items"][0]["type"] == "text"


class TestErrorPageMeta:
    def test_error_page_structure(self):
        page = schema.ErrorPageMeta(ValueError("bad word"), "word")
        d = page.get()
        assert d["is_found"] is False
        assert d["is_error"] is True
        assert d["word"] == "word"
        assert d["sections"][0]["title"] == "错误"
        assert "ValueError: bad word" in d["sections"][0]["items"][0]["text"]
