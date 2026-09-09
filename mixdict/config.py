"""Global settings."""

VERSION = "v0.1.0"
APP_NAME = "MixDict"
TITLE = "东拼西凑的词典"
DESCRIPTION = "A simple network dictionary GUI program built on some network dictionary sources and pywebview."

WINDOW_SIZE_RATE = (0.6, 0.7)  # width, height
WINDOW_MIN_SIZE = (640, 480)  # width, height

DEFAULT_TIMEOUT = 10.0
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/151.0.0.0 "
    "Safari/537.36"
)
DEFAULT_DICTIONARY_SOURCE = "Youdao"

TO_EXIT = False
DEBUG = False