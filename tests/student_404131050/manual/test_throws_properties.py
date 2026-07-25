"""Property-based tests for Throws reference metadata."""

from types import SimpleNamespace
from unittest.mock import patch

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from openunderstand.analysis_passes import Throws_ThrowsBy as sut


class _TextNode:
    """Minimal parser node exposing getText()."""

    def __init__(self, text: str) -> None:
        self._text = text

    def getText(self) -> str:
        return self._text


class _StartToken:
    """Token containing stable multi-digit line and column values."""

    def __str__(self) -> str:
        return "[@1,0:0='x',<1>,12:34]"


class _ThrowsContext:
    """Minimal method declaration context containing one exception."""

    parentCtx = None
    start = _StartToken()

    def __init__(self, exception_name: str) -> None:
        self._exception_name = exception_name

    def THROWS(self) -> bool:
        return True

    def qualifiedNameList(self) -> _TextNode:
        return _TextNode(self._exception_name)


java_identifier = st.from_regex(
    r"[A-Za-z_$][A-Za-z0-9_$]{0,30}",
    fullmatch=True,
)


@pytest.mark.unit
@pytest.mark.property
@settings(max_examples=50, deadline=None)
@given(exception_name=java_identifier)
def test_method_reference_preserves_valid_java_exception_identifier(
    exception_name: str,
) -> None:
    """Valid Java identifiers must be preserved in reference metadata."""

    listener = sut.Throws_TrowsBy()
    context = _ThrowsContext(exception_name)

    with (
        patch.object(
            listener,
            "findmethodacess",
            return_value=["public"],
        ),
        patch.object(
            listener,
            "findmethodreturntype",
            return_value=(
                "void",
                f"void execute() throws {exception_name} {{}}",
            ),
        ),
        patch.object(
            sut.class_properties.ClassPropertiesListener,
            "findParents",
            return_value=["sample", "Service", "execute"],
        ),
        patch.object(
            sut,
            "ProjectModel",
            SimpleNamespace(
                select=lambda: [
                    SimpleNamespace(
                        root="C:/temporary/project",
                    )
                ]
            ),
        ),
        patch.object(
            sut,
            "throws_parent_finder",
            return_value=None,
        ),
    ):
        listener.enterMethodDeclaration(context)

    assert len(listener.implement) == 1

    reference = listener.implement[0]

    assert reference["refent"] == exception_name
    assert reference["potential_refent"] == f"sample.Service.{exception_name}"
    assert reference["scopename"] == "execute"
    assert reference["scopelongname"] == "sample.Service.execute"
    assert reference["line"] == "12"
    assert reference["col"] == "34"
