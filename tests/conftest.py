"""Shared test helpers: load saved API snapshots from tests/fixtures/."""
import json
from pathlib import Path

import pytest

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def load_fixture(name: str) -> dict:
    """Load a saved API snapshot from tests/fixtures/<name>.json."""
    return json.loads((FIXTURES_DIR / f"{name}.json").read_text(encoding="utf-8"))


@pytest.fixture
def fixture_data():
    """Fixture that provides the `load_fixture` function to tests."""
    return load_fixture
