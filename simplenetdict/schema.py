"""Data framework for the data provided to the GUI.

Data format:
```
{
    "is_found": bool,
    "is_error": bool,
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
    """A base class holding the underlying dict for metadata builders.
    
    Call method `get()` to retrieve the built dictionary.
    """

    def __init__(self):
        self.meta = {}

    def get(self) -> dict:
        """Get the built dict (JSON-serializable)."""
        return self.meta


class PageMeta(_Meta):
    """Single page metadata builder -> {is_found, word, sections}."""

    def __init__(self, word: str, is_found: bool, is_error: bool = False):
        """Start a new page metadata for `word`, marking whether it was found via `is_found`."""
        super().__init__()

        self.meta["is_found"] = is_found
        self.meta["is_error"] = is_error
        self.meta["word"] = word
        self.meta["sections"] = []

    def add_section(self, section: "SectionMeta"):
        """Append a section metadata (built by `SectionMeta`) to the page metadata."""
        self.meta["sections"].append(section.get())


class SectionMeta(_Meta):
    """Section metadata builder -> {title, items}."""

    def __init__(self, title: str):
        """Start a new section metadata with the given `title`."""
        super().__init__()

        self.meta["title"] = title
        self.meta["items"] = []

    def _add_item(self, type: str, check_exist: bool = False, **fields) -> "SectionMeta":
        """Append an item dict `{type, **fields}.`
        
        Returns self for chaining.
        """
        item = {"type": type, **fields}
        if check_exist:
            if item not in self.meta["items"]:
                self.meta["items"].append(item)
        else:
            self.meta["items"].append(item)
        return self  # Support chained calls.

    def add_text(self, text: str) -> "SectionMeta":
        """Append a plain-text item."""
        return self._add_item("text", text=text)

    def add_phonetic(self, phonetic: str, name: str | None = None,
                     audio_url: str | None = None, check_exist: bool = False) -> "SectionMeta":
        """Append a phonetic item (pronunciation), with optional `audio_url`.
        
        `phonetic` must be the style like "/fəˈnɛtɪk/".
        """
        return self._add_item("phonetic", phonetic=phonetic, name=name,
                              audio_url=audio_url, check_exist=check_exist)

    def add_link(self, text: str, url: str):
        """Append a web link item."""
        return self._add_item("link", text=text, url=url)


class ErrorPageMeta(PageMeta):
    """Error page metadata builder, providing error information"""

    def __init__(self, error: Exception, word: str):
        """Start an error page metadata."""
        super().__init__(word, is_found=False, is_error=True)

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