"""User data and config persistence."""

import json
import logging

from typing import Any

from mixdict import resources

logger = logging.getLogger(__name__)


class Storage:

    def __init__(self):
        pass

    def init(self):
        """Read storage file and initialise."""

        self.config_file_path = resources.user_config_file_path()
        self._config: dict[str, Any] = {}

        with self.config_file_path.open(mode="r", encoding="utf-8") as config_file:
            try:
                config_file_content = config_file.read()
                if config_file_content:
                    _config = json.loads(config_file_content)
                else:
                    _config = {}
            except (json.decoder.JSONDecodeError, UnicodeDecodeError):
                _config = {}
                logger.warning("Bad config file, deprecated")

            if not isinstance(_config, dict):
                _config = {}
                logger.warning("Unknown config JSON root type: %s, deprecated", type(_config).__name__)

            for key in _config:
                self.set(key, _config[key], check_key=True, save=False)
            logger.info("Loaded config file at %s", self.config_file_path.resolve())

    def set(self, key: str, value: Any, check_key: bool = False, save: bool = True):
        """Set an storage item.
        
        If set `check_key` True, skip non-string `key` item,
        Otherwise, convert other type `key` to string.
        Will save config each set otherwise set `save` False.
        Returns self for chaining.
        """

        if not isinstance(key, str):
            if check_key:
                logger.warning("Unknown config key type: %r, deprecated", type(key).__name__)
                return
            else:
                key = str(key)

        self._config[key] = value
        if save:
            self.save()
        return self

    def get(self, key: str, default: Any | None = None) -> Any:
        """Get a value by `key`, returning default if missing."""
        return self._config.get(key, default)

    def save(self):
        """Save user data and config file."""

        self.config_file_path = resources.user_config_file_path()
        with self.config_file_path.open(mode="w", encoding="utf-8") as config_file:
            try:
                json.dump(self._config, config_file)
            except Exception as error:
                logger.error("Failed to save config file: %s", error)
            logger.debug("Saved config at %s", self.config_file_path.resolve())