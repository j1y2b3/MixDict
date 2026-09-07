"""Resource management utilities.

Works in both source code (not packed) and PyInstaller-frozen (packed) modes.
"""

import logging
import runpy
import sys
from pathlib import Path

import platformdirs
from PIL import Image

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from PIL.ImageFile import ImageFile
    from mixdict.core.sources.base import DictionarySource

from mixdict import config

# Not packed: project root (parent of mixdict/). Packed: PyInstaller temp dir.
ROOT_DIR = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent))

logger = logging.getLogger(__name__)

def web_path(name: str) -> Path:
    """Return the absolute path of a file under mixdict/gui/web/."""
    return ROOT_DIR / config.APP_NAME.lower() / "gui" / "web" / name

def assets_path(name: str) -> Path:
    """Return the absolute path of a file under assets/."""
    return ROOT_DIR / "assets" / name

def load_tray_icon() -> "ImageFile":
    """Return the tray icon instance."""
    icon_path = assets_path("tray-icon.png")
    if not icon_path.exists():
        raise FileNotFoundError(f"Tray icon lost: {icon_path.absolute()}")
    return Image.open(icon_path)

def user_sources_dir() -> Path:
    """Return the directory that stores user dictionary sources.

    Not packed: <project root>/user_sources.
    Packed: <app dir>/user_sources, next to the executable file, so it stays
    user-writable (bundled data under `_internal` is not suitable).
    """
    if getattr(sys, "frozen", False):
        # Packed: writable, in the same directory as the executable file
        return Path(sys.executable).parent / "user_sources"
    return ROOT_DIR / "user_sources"  # Not packed: user_sources/ in the project root

def user_source_path(name: str) -> Path:
    """Return the absolute path of a user source file under the user sources directory."""
    return user_sources_dir() / name

def load_user_source(file_path: Path | str) -> "DictionarySource | None":
    """Load a single user dictionary source file and return its dictionary source."""
    logger.debug("Loading user source %s", file_path)

    try:
        namespace = runpy.run_path(str(file_path), run_name=f"user_sources.{Path(file_path).stem}")
    except Exception:
        logger.exception("Failed to load user source %s", file_path)
        return None

    from mixdict.core.sources.base import DictionarySource  # For runtime type checking.
    source = namespace.get("Source")
    if source is None:
        logger.error("User source %s: lost `Source` class", file_path)
        return None
    if not (isinstance(source, type) and issubclass(source, DictionarySource)):
        logger.error("User source %s: unknown `Source` type: '%s'", file_path, type(source).__name__)
        return None
    
    logger.debug("Loaded user source %s", file_path)
    return source()  # type: ignore[call-arg]

def webview_storage_path() -> Path:
    """Return a cache dir for pywebview WebView2 data."""
    app_name = config.APP_NAME
    if config.DEBUG:
        app_name += "-dev"
    return platformdirs.user_cache_path(app_name, appauthor=False)
