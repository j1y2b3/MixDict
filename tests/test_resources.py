"""resources path/read helpers tests."""
import sys
from pathlib import Path

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
