"""schema(部件工厂)的单元测试。"""
from simplenetdict import schema


class TestSchema:
    def test_page_meta_basic(self):
        page = schema.PageMeta("apple", True)
        assert page.get() == {"is_found": True, "word": "apple", "sections": []}

    def test_page_not_found(self):
        page = schema.PageMeta("qwiruqe", False)
        assert page.get()["is_found"] is False
        assert page.get()["word"] == "qwiruqe"

    def test_section_text_items(self):
        sec = schema.SectionMeta("英汉")
        sec.add_text("n. 苹果").add_text("n. 苹果树")
        assert sec.get() == {
            "title": "英汉",
            "items": [
                {"type": "text", "text": "n. 苹果"},
                {"type": "text", "text": "n. 苹果树"},
            ],
        }

    def test_add_phonetic(self):
        sec = schema.SectionMeta("发音")
        sec.add_phonetic("美", "ˈæp(ə)l", "https://example/a.mp3")
        assert sec.get()["items"][0] == {
            "type": "phonetic",
            "name": "美",
            "phonetic": "ˈæp(ə)l",
            "audio_url": "https://example/a.mp3",
        }

    def test_add_phonetic_no_audio(self):
        sec = schema.SectionMeta("发音")
        sec.add_phonetic("美", "ˈæp(ə)l")
        assert sec.get()["items"][0]["audio_url"] is None

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
        assert d["word"] == "word"
        assert d["sections"][0]["title"] == "错误"
        assert "ValueError: bad word" in d["sections"][0]["items"][0]["text"]
