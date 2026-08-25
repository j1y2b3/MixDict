"""Shared test helpers: load saved API snapshots from tests/fixtures/."""
import json
from pathlib import Path

import pytest

from simplenetdict import config

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture(autouse=True)
def production_mode(monkeypatch):
    """Run sources in production mode so `lookup()` swallows errors into error pages."""
    monkeypatch.setattr(config, "DEBUG", False)


def load_fixture(name: str) -> dict:
    """Load a saved API snapshot from tests/fixtures/<name>.json."""
    return json.loads((FIXTURES_DIR / f"{name}.json").read_text(encoding="utf-8"))


@pytest.fixture
def fixture_data():
    """Fixture that provides the `load_fixture` function to tests."""
    return load_fixture
