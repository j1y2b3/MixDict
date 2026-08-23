"""Dictionary source base/protocol and utilities.

All sources produce the same GUI-ready schema page through `lookup()`.
"""

from abc import ABC, abstractmethod
from sys import flags

from typing import Any
from collections.abc import Iterable

from simplenetdict import schema
from sys import flags


class APIError(Exception):
    pass


class DictionarySource(ABC):
    """A dictionary backend producing a schema page for a word.

    Subclasses must call `super().__init__(reg_name=..., name=...[, description=...])` and implement `_lookup()`.
    The public `lookup()` catches any error and returns an error page instead, so it never raises.
    """

    reg_name: str
    name: str
    description: str = ""

    def __init__(self, reg_name: str, name: str, description: str = ""):
        if not reg_name.isascii():
            raise ValueError(f"reg_name must be ASCII, got {reg_name!r}")
        self.reg_name = reg_name  # Must be ascii string.
        self.name = name  # Display name
        self.description = description

    def lookup(self, word: str) -> dict:
        """Return the schema page for `word`; never raises."""
        if flags.dev_mode and word == "$test-error-display":
            return schema.ErrorPageMeta(Exception("This is an error."), word).get()
        try:
            return self._lookup(word)
        except Exception as error:
            if flags.dev_mode:
                raise error
            return schema.ErrorPageMeta(error, word).get()

    @abstractmethod
    def _lookup(self, word: str) -> dict:
        """Fetch and parse `word` into a schema page."""


def safe_get(data: dict | list, path: Iterable[str | int], *, default=None) -> Any:
    """Get a value from nested data by traversing `path`, returning `default` if any segment missing.

    Supports both dict keys and list indices.
    """
    cur = data
    for item in path:
        if isinstance(cur, dict) and isinstance(item, str):
            if item not in cur:
                return default
            cur = cur[item]

        elif isinstance(cur, list) and isinstance(item, int):
            length = len(cur)
            if not (-length <= item <= length - 1):
                return default
            cur = cur[item]

        else:
            return default

    return cur