"""Dictionary source base/protocol.

All sources produce the same GUI-ready schema page through `lookup()`.
"""

from abc import ABC, abstractmethod

from simplenetdict import schema


class APIError(Exception):
    pass


class DictionarySource(ABC):
    """A dictionary backend producing a schema page for a word.

    Subclasses must call `super().__init__(reg_name=..., name=...)` and implement `_lookup()`.
    The public `lookup()` catches any error and returns an error page instead, so it never raises.
    """

    reg_name: str
    name: str

    def __init__(self, reg_name: str, name: str):
        if not reg_name.isascii():
            raise ValueError(f"reg_name must be ASCII, got {reg_name!r}")
        self.reg_name:str = reg_name  # Must be ascii string.
        self.name: str = name  # Display name

    def lookup(self, word: str) -> dict:
        """Return the schema page for `word`; never raises."""
        try:
            return self._lookup(word)
        except Exception as error:
            return schema.ErrorPageMeta(error, word).get()

    @abstractmethod
    def _lookup(self, word: str) -> dict:
        """Fetch and parse `word` into a schema page."""