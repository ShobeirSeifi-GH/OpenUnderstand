"""Shared pytest fixtures for student 404131050 tests."""

from collections.abc import Callable
from pathlib import Path

import pytest


@pytest.fixture
def java_fixtures_dir() -> Path:
    """Return the directory containing permanent Java test fixtures."""
    return Path(__file__).parent / "fixtures" / "java"


@pytest.fixture
def write_java_file(
    tmp_path: Path,
) -> Callable[[str, str], Path]:
    """Create a temporary Java source file and return its path."""

    def _write_java_file(relative_path: str, source_code: str) -> Path:
        target = tmp_path / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(source_code, encoding="utf-8")
        return target

    return _write_java_file
