"""resources path/read helpers tests."""
import sys
from pathlib import Path

from simplenetdict import resources


class TestResources:
    def test_web_path(self):
        p = resources.web_path("index.html")
        assert p == resources.ROOT_DIR / "simplenetdict" / "gui" / "web" / "index.html"
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
