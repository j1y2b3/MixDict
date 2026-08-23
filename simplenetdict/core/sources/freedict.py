"""Free Dictionary API

URL:
https://api.dictionaryapi.dev/api/v2/entries/en/<word>
Project address:
https://github.com/meetDeveloper/freeDictionaryAPI
Author:
meetDeveloper (https://github.com/meetDeveloper)
License:
GNU General Public License v3.0
"""

import urllib.request, urllib.error, json

from simplenetdict import config, schema
from simplenetdict.core.sources.base import DictionarySource, APIError, safe_get

IS_FOUND_KEY = "isfound"
WORD_KEY = "word"


class FreeDict(DictionarySource):
    """Free Dictionary dictionary source."""

    def __init__(self):
        super().__init__(reg_name="FreeDict", name="Free Dictionary API",
                         description="当 meetDeveloper 想为 ta 的朋友找一个免费的词典 API 时，"
                                     "网上并没有，所以 ta 创建了一个。\n"
                                     "提供英文单词的释义、音标、发音和例句。不稳定。")

    def _lookup(self, word: str) -> dict:
        return parse_json(fetch_json(word))


def fetch_json(word: str, user_agent: str | None = None, timeout: float | None = None) -> dict:
    """Call Free Dictionary API to get raw JSON."""

    # URL
    url = f"https://api.dictionaryapi.dev/api/v2/entries/en/{word}"

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
            data = json.loads(response.read().decode("utf-8"))[0]  # Raw JSON's top level is a list.
            data[IS_FOUND_KEY] = True
            return data
    except urllib.error.HTTPError as http_error:
        if http_error.code == 404:
            data = json.loads(http_error.read().decode("utf-8", "replace"))
            data[IS_FOUND_KEY] = False
            data[WORD_KEY] = word
            return data
        raise APIError(f"Free Dictionary API returned HTTP {http_error.code}: {http_error.reason}.")

def parse_json(data: dict) -> dict:
    """Parse raw JSON getted by `fetch_json` into data which can be used by GUI."""

    QUERY_WORD_PATH = (WORD_KEY, )
    IS_FPUND_PATH = (IS_FOUND_KEY, )
    word = safe_get(data, QUERY_WORD_PATH)

    # Deal with the situation where no translation for the word is found.
    if not safe_get(data, IS_FPUND_PATH):
        TITLE_PATH = ("title", )
        MESSAGE_PATH = ("message", )
        RESOLUTION_PATH = ("resolution", )

        page = schema.PageMeta(word, is_found=False)
        section = schema.SectionMeta(safe_get(data, TITLE_PATH))
        section.add_text(safe_get(data, MESSAGE_PATH))
        section.add_text(safe_get(data, RESOLUTION_PATH))
        page.add_section(section)
        return page.get()

    page = schema.PageMeta(word, is_found=True)
    section = schema.SectionMeta("Result")

    # Add phonetics.
    PHONETIC_PATH = ("phonetic", )
    PHONETICS_PATH = ("phonetics", )
    PHONETICS_TEXT_REL_PATH = ("text", )
    PHONETICS_AUDIO_REL_PATH = ("audio", )
    PHONETICS_SOURCE_REL_PATH = ("sourceUrl", )

    phonetic = safe_get(data, PHONETIC_PATH)  # This variable will be reused multiple times below.
    if phonetic is not None:
        section.add_phonetic(phonetic)

    for phonetic_data in safe_get(data, PHONETICS_PATH, default=[]):  # This `safe_get()` must return a iterable.
        phonetic = safe_get(phonetic_data, PHONETICS_TEXT_REL_PATH)
        if phonetic is None:
            continue

        audio_url = safe_get(phonetic_data, PHONETICS_AUDIO_REL_PATH)
        section.add_phonetic(phonetic, audio_url=audio_url)
        if audio_url is None:
            continue

        source_url = safe_get(phonetic_data, PHONETICS_SOURCE_REL_PATH)
        if source_url is None:
            continue
        section.add_link(f"此发音来源", source_url)

    # Add meanings.
    MEANINGS_PATH = ("meanings", )
    MEANINGS_PART_OF_SPEECH_REL_PATH = ("partOfSpeech", )
    MEANINGS_DEFINITIONS_REL_PATH = ("definitions", )
    MEANINGS_DEFINITION_REL_REL_PATH = ("definition", )
    MEANINGS_SYNONYMS_REL_REL_PATH = ("synonyms", )
    MEANINGS_ANTONYMS_REL_REL_PATH = ("antonyms", )
    MEANING_EXAMPLE_REL_REL_PATH = ("example", )
    MEANINGS_SYNONYMS_REL_PATH = ("synonyms", )
    MEANINGS_ANTONYMS_REL_PATH = ("antonyms", )

    for meaning_data in safe_get(data, MEANINGS_PATH, default=[]):  # This `safe_get()` must return a iterable.
        section.add_text("")
        section.add_text(safe_get(meaning_data, MEANINGS_PART_OF_SPEECH_REL_PATH))
        synonyms = safe_get(meaning_data, MEANINGS_SYNONYMS_REL_PATH)
        antonyms = safe_get(meaning_data, MEANINGS_ANTONYMS_REL_PATH)
        if synonyms:  # Exclude both `None` and `[]`.
            section.add_text(f"同义词：{", ".join(synonyms)}")
        if antonyms:  # Exclude both `None` and `[]`.
            section.add_text(f"反义词：{", ".join(antonyms)}")

        # This `safe_get()` must return a iterable.
        for definition_data in safe_get(meaning_data, MEANINGS_DEFINITIONS_REL_PATH, default=[]):
            section.add_text("")
            section.add_text(safe_get(definition_data, MEANINGS_DEFINITION_REL_REL_PATH))

            synonyms = safe_get(definition_data, MEANINGS_SYNONYMS_REL_REL_PATH)
            antonyms = safe_get(definition_data, MEANINGS_ANTONYMS_REL_REL_PATH)
            example = safe_get(definition_data, MEANING_EXAMPLE_REL_REL_PATH)
            if synonyms:  # Exclude both `None` and `[]`.
                section.add_text(f"同义词：{", ".join(synonyms)}")
            if antonyms:  # Exclude both `None` and `[]`.
                section.add_text(f"反义词：{", ".join(antonyms)}")
            if example is not None:
                section.add_text(f"例：{example}")

    # Note the source.
    section.add_text("")
    SOURCES_PATH = ("sourceUrls", )
    source_urls = safe_get(data, SOURCES_PATH)
    if source_urls:  # Exclude both `None` and `[]`.
        for source_url in source_urls:
            section.add_link("此页信息来源", source_url)

    page.add_section(section)
    return page.get()

if __name__ == "__main__":
    # Test fetch raw JSON.
    import os

    os.makedirs("./tmp", exist_ok=True)
    word = input("Look up word: ")
    dic = fetch_json(word)
    file = f"./tmp/freedict-{word}.json"
    with open(file, "w", encoding="utf-8") as f:
        json.dump(dic, f, ensure_ascii=False, indent=2)