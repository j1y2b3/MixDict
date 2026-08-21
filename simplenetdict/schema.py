"""Data framework for the data provided to the GUI.

Data format:
```
{
    "is_found": bool,
    "word": str,
    "sections": [
        {
            "title": str,
            "items": [
                {
                    "type": str,
                    ...
                }
            ]
        },
        ...
    ]
}
```
"""


class _Meta:
    """A base class holding the underlying dict for data builders.
    
    Call method `get()` to retrieve the built dictionary.
    """

    def __init__(self):
        self.meta = {}

    def get(self) -> dict:
        """Get the built dict (JSON-serializable)."""
        return self.meta


class PageMeta(_Meta):
    """Single page builder -> {is_found, word, sections}."""

    def __init__(self, word: str, is_found: bool):
        """Start a new page result for `word`, marking whether it was found via `is_found`."""
        super().__init__()

        self.meta["is_found"] = is_found
        self.meta["word"] = word
        self.meta["sections"] = []

    def add_section(self, section: "SectionMeta"):
        """Append a section (built by `SectionMeta`) to the page."""
        self.meta["sections"].append(section.get())


class SectionMeta(_Meta):
    """Section builder -> {title, items}."""

    def __init__(self, title: str):
        """Start a new section with the given `title`."""
        super().__init__()

        self.meta["title"] = title
        self.meta["items"] = []

    def _add_item(self, type: str, **fields) -> "SectionMeta":
        """Append an item dict `{type, **fields}.`
        
        Returns self for chaining.
        """
        self.meta["items"].append({"type": type, **fields})
        return self  # Support chained calls.

    def add_text(self, text: str) -> "SectionMeta":
        """Append a plain-text item."""
        return self._add_item("text", text=text)

    def add_phonetic(self, name: str, phonetic: str, audio_url: str | None = None) -> "SectionMeta":
        """Append a phonetic item (pronunciation), with optional `audio_url`."""
        return self._add_item("phonetic", name=name, phonetic=phonetic, audio_url=audio_url)


class ErrorPageMeta(PageMeta):
    """Error page builder, providing error information"""

    def __init__(self, error: Exception, word: str):
        """Start an error page."""
        super().__init__(word, is_found=False)

        section = SectionMeta(title="错误")
        section.add_text(f"{type(error).__name__}: {error}")
        self.add_section(section)


if __name__ == "__main__":
    # Generate data for web debugging.
    import os, json

    # Prepare data
    word = "test"
    test_page = PageMeta(word, is_found=True)
    test_section = SectionMeta("Test title")
    test_section.add_phonetic("test phonetic name", "test phonetic", "https://www.example.com/test-audio-url.wav")
    test_section.add_text("Test text.")
    test_page.add_section(test_section)
    test_error_page = ErrorPageMeta(Exception("Test error."), word)

    # Wirte into file
    dir_path = "./simplenetdict/gui/web/samples"
    os.makedirs(dir_path, exist_ok=True)
    with open(f"{dir_path}/page.json", mode="w", encoding="utf-8") as f:
        json.dump(test_page.get(), f, ensure_ascii=False, indent=2)
    with open(f"{dir_path}/error-page.json", mode="w", encoding="utf-8") as f:
        json.dump(test_error_page.get(), f, ensure_ascii=False, indent=2)