"""Shared test helpers: load saved API snapshots from tests/fixtures/."""
import json
from pathlib import Path

import pytest

from mixdict import config, resources

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture(autouse=True)
def production_mode(monkeypatch):
    """Run sources in production mode so `lookup()` swallows errors into error pages."""
    monkeypatch.setattr(config, "DEBUG", False)


@pytest.fixture
def isolated_user_sources(monkeypatch, tmp_path):
    """Point `user_sources_dir` at an empty dir so registries see no user sources."""
    empty_dir = tmp_path / "empty_user_sources"
    empty_dir.mkdir()
    monkeypatch.setattr(resources, "user_sources_dir", lambda: empty_dir)


def load_fixture(name: str) -> dict:
    """Load a saved API snapshot from tests/fixtures/<name>.json."""
    return json.loads((FIXTURES_DIR / f"{name}.json").read_text(encoding="utf-8"))


@pytest.fixture
def fixture_data():
    """Fixture that provides the `load_fixture` function to tests."""
    return load_fixture
