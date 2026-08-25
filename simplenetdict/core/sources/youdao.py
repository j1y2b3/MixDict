"""Youdao dictionary source.

URL:
https://dict.youdao.com/jsonapi
"""

import logging
import urllib.request, json
from urllib.parse import quote

from simplenetdict import config, schema
from simplenetdict.core.sources.base import DictionarySource, APIError, safe_get

logger = logging.getLogger(__name__)


class Youdao(DictionarySource):
    """Youdao dictionary source."""

    def __init__(self):
        super().__init__(reg_name="Youdao", name="有道")

    def _lookup(self, word: str) -> dict:
        return parse_json(fetch_json(word))


def fetch_json(word: str, user_agent: str | None = None, timeout: float | None = None) -> dict:
    """Call Youdao jsonapi interface to get raw JSON."""

    # URL
    url = f"https://dict.youdao.com/jsonapi?q={quote(word)}"

    # User-Agent
    if user_agent is None:
        user_agent = config.DEFAULT_USER_AGENT

    # Headers
    headers = {
        "User-Agent": user_agent,
        "Referer": "https://dict.youdao.com/",  # Respond to Youdao source verification.
    }

    # Request
    request = urllib.request.Request(url, headers=headers)

    # Timeout
    if timeout is None:
        timeout = config.DEFAULT_TIMEOUT

    # Open URL
    with urllib.request.urlopen(request, timeout=timeout) as response:
        data = json.loads(response.read().decode("utf-8"))

    if not isinstance(data, dict):
        logger.error("Youdao API returned non-dict root: %s, url=%s", type(data).__name__, url)
        raise APIError(f"Unexpected JSON root type: {type(data).__name__}, API may have changed.")
    return data

def parse_json(data: dict) -> dict:
    """Parse raw JSON getted by `fetch_json` into data which can be used by GUI."""

    AUDIO_URL_BASE = "https://dict.youdao.com/dictvoice?audio="
    IS_HAS_SIMPLE_DICT_PATH = ("meta", "isHasSimpleDict")
    QUERY_WORD_PATH = ("input", )
    word = safe_get(data, QUERY_WORD_PATH)
    section: "schema.SectionMeta"  # This variable will be reused multiple times below.

    # Deal with the situation where no translation for the word is found.
    if "typos" in data or safe_get(data, IS_HAS_SIMPLE_DICT_PATH) == "0":
        page = schema.PageMeta(word, is_found=False)

        TYPOS_PATH = ("typos", "typo")  # `typo` is a list.
        TYPO_WORD_REL_PATH = ("word", )
        TYPO_TRANSLATION_REL_PATH = ("trans", )
        section = schema.SectionMeta("未找到")
        typos = safe_get(data, TYPOS_PATH, default=[])  # This `safe_get()` must return a iterable.
        if typos:
            section.add_text("您要找的是不是：")
            for typo in typos:
                section.add_text(safe_get(typo, TYPO_WORD_REL_PATH))
                section.add_text(safe_get(typo, TYPO_TRANSLATION_REL_PATH))
        section.add_text(f"提示：抱歉没有找到“{word}”相关的词")
        page.add_section(section)

        return page.get()

    page = schema.PageMeta(word, is_found=True)

    # English-Chinese (ec)
    EC_US_PHONETIC_PATH = ("ec", "word", 0, "usphone")
    EC_US_SPEECH_PATH = ("ec", "word", 0, "usspeech")
    EC_UK_PHONETIC_PATH = ("ec", "word", 0, "ukphone")
    EC_UK_SPEECH_PATH = ("ec", "word", 0, "ukspeech")
    EC_TRS_PATH = ("ec", "word", 0, "trs")  # `trs` is a list.
    EC_TRANSLATION_REL_PATH = ("tr", 0, "l", "i", 0)

    section = schema.SectionMeta(title="英汉")

    us_phonetic = safe_get(data, EC_US_PHONETIC_PATH)
    us_audio_url = safe_get(data, EC_US_SPEECH_PATH)
    if us_phonetic is None:
        logger.error("Youdao API lost US phonetic for %r", word)
        raise APIError("Lost US phonetic.")
    if us_audio_url is not None:
        us_audio_url = AUDIO_URL_BASE + us_audio_url
    section.add_phonetic(f"/{us_phonetic}/", "美式发音", us_audio_url)

    uk_phonetic = safe_get(data, EC_UK_PHONETIC_PATH)
    uk_audio_url = safe_get(data, EC_UK_SPEECH_PATH)
    if uk_phonetic is None:
        logger.error("Youdao API lost UK phonetic for %r", word)
        raise APIError("Lost UK phonetic.")
    if uk_audio_url is not None:
        uk_audio_url = AUDIO_URL_BASE + uk_audio_url
    section.add_phonetic(f"/{uk_phonetic}/", "英式发音", uk_audio_url)

    for tr in safe_get(data, EC_TRS_PATH, default=[]):  # This `safe_get()` must return a iterable.
        section.add_text(safe_get(tr, EC_TRANSLATION_REL_PATH))

    page.add_section(section)

    ...

    return page.get()

if __name__ == "__main__":
    # Fetch raw JSON for reference.
    import os

    os.makedirs("./tmp", exist_ok=True)
    word = input("Look up word: ")
    dic = fetch_json(word)
    file = f"./tmp/youdao-{word}.json"
    with open(file, "w", encoding="utf-8") as f:
        json.dump(dic, f, ensure_ascii=False, indent=2)

    # Record appeared items
    file = "./tmp/items.txt"
    new_items = set(dic.keys())
    with open(file, mode="r") as f:
        old_items = set(f.read().split())
    new_items = new_items | old_items
    with open(file, mode="w") as f:
        f.write('\n'.join(new_items))