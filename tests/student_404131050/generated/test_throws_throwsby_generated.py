"""Curated tests derived from Pynguin-generated test cases."""

import pytest

from openunderstand.analysis_passes import Throws_ThrowsBy as sut


@pytest.mark.generated
def test_generated_listener_starts_with_empty_buffer() -> None:
    listener = sut.Throws_TrowsBy()

    assert listener.implement == []


@pytest.mark.generated
def test_generated_findmethodaccess_accepts_none() -> None:
    listener = sut.Throws_TrowsBy()

    result = listener.findmethodacess(None)

    assert result == []


@pytest.mark.generated
@pytest.mark.parametrize(
    ("root", "exception_name"),
    [
        ("", ""),
        ("n%G", "n%G"),
    ],
)
def test_generated_parent_finder_returns_none_for_invalid_locations(
    root: str,
    exception_name: str,
) -> None:
    result = sut.throws_parent_finder(root, exception_name)

    assert result is None
