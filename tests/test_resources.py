"""resources path/read helpers tests."""
import sys
from pathlib import Path

import pytest

from mixdict import resources


class TestResources:
    def test_web_path(self):
        p = resources.web_path("index.html")
        assert p == resources.ROOT_DIR / "mixdict" / "gui" / "web" / "index.html"
        assert p.is_absolute()

    def test_assets_path(self):
        p = resources.assets_path("app.ico")
        assert p == resources.ROOT_DIR / "assets" / "app.ico"

    def test_user_sources_dir_not_frozen(self, monkeypatch):
        monkeypatch.delattr(sys, "frozen", raising=False)
        assert resources.user_sources_dir() == resources.ROOT_DIR / "user_sources"

    def test_user_sources_dir_frozen(self, monkeypatch, tmp_path):
        exe = tmp_path / "app" / "app.exe"
        monkeypatch.setattr(sys, "frozen", True, raising=False)
        monkeypatch.setattr(sys, "executable", str(exe))
        assert resources.user_sources_dir() == tmp_path / "app" / "user_sources"

    def test_user_source_path(self, monkeypatch):
        monkeypatch.delattr(sys, "frozen", raising=False)
        assert resources.user_source_path("x.py") == resources.ROOT_DIR / "user_sources" / "x.py"

    def test_webview_storage_path(self):
        from platformdirs import user_cache_dir

        p = resources.webview_storage_path()
        assert p == Path(user_cache_dir("MixDict", appauthor=False))
        assert p.is_absolute()


class TestLoadTrayIcon:
    def test_load_tray_icon_returns_image(self, monkeypatch):
        # 托盘图标已随仓库提交,应能正常打开为 PIL 图像。
        from PIL import Image

        icon_path = resources.ROOT_DIR / "assets" / "tray-icon.png"
        monkeypatch.setattr(resources, "assets_path", lambda name: icon_path)
        icon = resources.load_tray_icon()
        assert isinstance(icon, Image.Image)
        assert icon.width > 0 and icon.height > 0

    def test_load_tray_icon_missing_raises(self, monkeypatch, tmp_path):
        missing = tmp_path / "no-tray-icon.png"
        monkeypatch.setattr(resources, "assets_path", lambda name: missing)
        with pytest.raises(FileNotFoundError, match="Tray icon lost"):
            resources.load_tray_icon()
