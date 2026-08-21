"""Resource management utilities.

Works in both source code (not packed) and PyInstaller-frozen (packed) modes.
"""
import sys
from pathlib import Path

# Not packed: project root (parent of src/). Packed: PyInstaller temp dir.
ROOT_DIR = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent))

def web_path(name: str) -> Path:
    """Return the absolute path of a file under src/gui/web/."""
    return ROOT_DIR / "src" / "gui" / "web" / name

def assets_path(name: str) -> Path:
    """Return the absolute path of a file under assets/."""
    return ROOT_DIR / "assets" / name

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