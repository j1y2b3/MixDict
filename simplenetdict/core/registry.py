"""Registry of dictionary sources (built-in + user plugins).

Sources are keyed by their ASCII `reg_name`.
"""

from simplenetdict import config
from simplenetdict.core.sources import youdao
from simplenetdict.core.sources.base import DictionarySource


class SourcesRegistry:
    """Hold registered sources, keyed by `reg_name`, with a default source."""

    def __init__(self):
        """Create an empty registry and register the built-in sources."""
        self.sources: dict[str, DictionarySource] = {}
        self.default_source_reg_name: str = config.DEFAULT_DICTIONARY_SOURCE
        self._register_builtins()

    def register(self, source: DictionarySource, force: bool = False):
        """Register a source instance under its `reg_name`.

        Raise ValueError if the `reg_name` is already taken, unless
        `force` is True, in which case the existing entry is overwritten.
        """
        if not force and source.reg_name in self.sources:
            raise ValueError(f"Source {source.reg_name!r} already registered; use force=True to overwrite.")
        self.sources[source.reg_name] = source

    def _register_builtins(self):
        """Register the built-in dictionary sources."""
        self.register(youdao.Youdao())

        # Prevent the default source from being not registered
        if self.default_source_reg_name not in self.sources:
            raise ValueError(f"Default source {self.default_source_reg_name!r} is not registered; "
                             "check config.DEFAULT_DICTIONARY_SOURCE.")

    def get(self, reg_name: str) -> DictionarySource | None:
        """Return the dictionary source for `reg_name`, or None."""
        return self.sources.get(reg_name) or None

    def get_all(self) -> dict[str, DictionarySource]:
        """Return a copy of registery including all sources."""
        return dict(self.sources)

    def list(self) -> list[str]:
        """Return the `reg_name`s of all registered sources."""
        return list(self.sources.keys())

    def change_default(self, reg_name: str):
        """Set the default source to `reg_name`; raise ValueError if unregistered."""
        if reg_name not in self.sources:
            raise ValueError(f"Source {reg_name!r} is not registered; call register() first.")
        self.default_source_reg_name = reg_name