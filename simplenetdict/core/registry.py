"""Registry of dictionary sources (built-in + user plugins).

Sources are keyed by their ASCII `reg_name`.
"""

from pathlib import Path

from simplenetdict import config
from simplenetdict import resources
from simplenetdict.core.sources import youdao, freedict
from simplenetdict.core.sources.base import DictionarySource


class SourcesRegistry:
    """Hold registered sources, keyed by `reg_name`, with a default source."""

    def __init__(self):
        """Create an empty registry and register the built-in sources."""

        self.sources: dict[str, DictionarySource] = {}
        self._builtin_reg_names: set[str] = set()
        self.user_sources_reg_map: dict[Path, str] = {}  # For hotupdate.
        self.default_source_reg_name: str = config.DEFAULT_DICTIONARY_SOURCE
        self._register_builtins()
        self._register_users()

    def register(self, source: DictionarySource, force: bool = False, builtin: bool = False):
        """Register a source instance under its `reg_name`.

        Raise ValueError if the `reg_name` is already taken, unless `force`
        is True, in which case the existing entry is overwritten.
        A non-builtin source cannot overwrite a builtin one even with `force`.
        Set `builtin` to mark `reg_name` as built-in, protecting it from
        overwrite by non-builtin sources and from unregistration.
        """
        reg_name = source.reg_name

        if not force and reg_name in self.sources:
            raise ValueError(f"Source {reg_name!r} already registered; use force=True to overwrite.")
        if force and not builtin and reg_name in self._builtin_reg_names:
            raise ValueError(f"Non-builtin source cannot overwrite builtin source {reg_name!r}.")
        if builtin:
            self._builtin_reg_names.add(reg_name)
        self.sources[reg_name] = source

    def unregister(self, reg_name: str):
        """Unregister the source instance with the given `reg_name`.

        Do nothing if `reg_name` is not currently registered.
        Raise if attempt to unregister a builtin source.
        """
        if reg_name in self._builtin_reg_names:
            raise ValueError(f"Cannot unregister builtin source {reg_name!r}.")
        if self.sources.pop(reg_name, None) is None:
            return
        if reg_name == self.default_source_reg_name:
            self.default_source_reg_name = config.DEFAULT_DICTIONARY_SOURCE

    def _register_builtins(self):
        """Register the built-in dictionary sources."""
        self.register(youdao.Source(), builtin=True)
        self.register(freedict.Source(), builtin=True)

        # Prevent the default source from being not registered.
        if self.default_source_reg_name not in self.sources:
            raise ValueError(f"Default source {self.default_source_reg_name!r} is not registered; "
                             "check config.DEFAULT_DICTIONARY_SOURCE.")

    def _register_users(self):
        """Scan and register the user dictionary sources."""
        for file in sorted(resources.user_sources_dir().glob("*.py")):
            source = resources.load_user_source(file)
            if source is None:
                continue
            self.register(source)
            self.user_sources_reg_map[file] = source.reg_name

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