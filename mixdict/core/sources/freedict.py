"""Free Dictionary API

Request URL:
https://freedictionaryapi.com/api/v1/entries/{language}/{word}
Site:
https://freedictionaryapi.com/
Content source:
English Wiktionary (CC BY-SA 4.0)

Only provides dictionary entries for English words currently.
"""

import json
import logging
import urllib.request, urllib.error
from urllib.parse import quote

from mixdict import config, schema
from mixdict.core.sources.base import DictionarySource

logger = logging.getLogger(__name__)


class Source(DictionarySource):
    
    def __init__(self):
        super().__init__(reg_name="FreeDict", name="Free Dictionary API",
                         description="https://freedictionaryapi.com/\n"
                                     "一个免费的词典API，提供来自维基词典的结构化多语言词典数据，"
                                     "遵循知识共享许可协议。\n"
                                     "暂仅支持英文单词。限1000次每小时每IP。")

    def _lookup(self, word: str) -> dict:
        data, is_limited = fetch_json(word)
        if is_limited:
            return limited_page(data["error"], word)
        else:
            return parse_json(data)


def fetch_json(word: str, language: str | None = None, user_agent: str | None = None,
               timeout: float | None = None) -> tuple[dict, bool]:
    """Call Free Dictionary API to get raw JSON.
    
    Return JSON and whether the request limit has been exceeded.
    If the request limit has been exceeded,
    the JSON will be `{"error": urllib.error.HTTPError}`.
    """

    # Set Language.
    if language is None:
        language = "en"

    # URL
    url = f"https://freedictionaryapi.com/api/v1/entries/{language}/{quote(word)}"

    # User-Agent
    if user_agent is None:
        user_agent = config.DEFAULT_USER_AGENT

    # Headers
    headers = {"User-Agent": user_agent}

    # Request
    request = urllib.request.Request(url, headers=headers)

    # Timeout
    if timeout is None:
        timeout = config.DEFAULT_TIMEOUT

    # Open URL
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            data = json.loads(response.read().decode("utf-8"))

    except urllib.error.HTTPError as http_error:
        if http_error.code == 429:
            return {"error": http_error}, True
        else:
            raise http_error

    return data, False

def parse_json(data: dict) -> dict:
    """Parse raw JSON getted by `fetch_json` into data which can be used by GUI."""

    word = data["word"]

    if not data["entries"]:
        page = schema.PageMeta(word, is_found=False)

        section = schema.SectionMeta("未找到")
        section.add_text("没有该词或不是英语")
        page.add_section(section)

    else:
        page = schema.PageMeta(word, is_found=True)

        for entry in data["entries"]:
            section = schema.SectionMeta(entry["partOfSpeech"])

            for pronunciation in entry["pronunciations"]:
                section.add_phonetic(pronunciation["text"], ", ".join(pronunciation["tags"]))

            section.add_text("变形", font_style="stress")
            for form in entry["forms"]:
                section.add_text(f"({", ".join(form["tags"])}) {form["word"]}")

            unfold_senses(entry["senses"], section)

            page.add_section(section)

    section = schema.SectionMeta("来源")
    section.add_link("Wiktionary", data["source"]["url"])
    section.add_link(data["source"]["license"]["name"],
                        data["source"]["license"]["url"])
    page.add_section(section)

    section = schema.SectionMeta("API服务")
    section.add_link("Free Dictionary API", "https://freedictionaryapi.com/")
    page.add_section(section)

    return page.get()

def unfold_senses(senses: dict, section: schema.SectionMeta, index: str | None = None):
    """Expand and add the `senses` and their recursive `subsenses` to the `section`."""

    for i in range(len(senses)):
        if index is None:
            _index = str(i + 1)
        else:
            _index = f"{index}.{i + 1}"
        section.add_text(f"义项 {_index}", font_style="stress")
        section.add_text(senses[i]["definition"])
        section.add_text(", ".join(senses[i]["tags"]), font_style="muted")

        if senses[i]["examples"]:
            section.add_text("示例")
            for example in senses[i]["examples"]:
                section.add_text(example)

        if senses[i]["quotes"]:
            section.add_text("引文")
            for quote in senses[i]["quotes"]:
                section.add_text(f"{quote["text"]}({quote["reference"]})", font_style="muted")

        if senses[i]["synonyms"]:
            section.add_text(f"同义词 {", ".join(senses[i]["synonyms"])}")
        if senses[i]["antonyms"]:
            section.add_text(f"反义词 {", ".join(senses[i]["antonyms"])}")

        unfold_senses(senses[i]["subsenses"], section, _index)

def limited_page(error: Exception, word: str) -> dict:
    """Assemble the `PageMeta` used to warn that the API usage has exceeded the limit."""

    page = schema.ErrorPageMeta(error, word)
    page.add_text("Free Dictionary API 每小时使用次数已达到限制，请稍后再试。")
    return page.get()

if __name__ == "__main__":
    # Test fetch raw JSON.
    import os

    os.makedirs("./tmp", exist_ok=True)
    word = input("Look up word: ")
    dic = fetch_json(word)[0]
    file = f"./tmp/freedict-{word}.json"
    with open(file, "w", encoding="utf-8") as f:
        json.dump(dic, f, ensure_ascii=False, indent=4)