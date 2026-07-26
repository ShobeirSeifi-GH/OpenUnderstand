"""Differential Oracle validation using the javac Tree API."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from antlr4 import CommonTokenStream, InputStream, ParseTreeWalker
from gen.javaLabeled.JavaLexer import JavaLexer
from gen.javaLabeled.JavaParserLabeled import JavaParserLabeled

from openunderstand.analysis_passes import Throws_ThrowsBy as sut

_REPOSITORY_ROOT = Path(__file__).resolve().parents[3]

_FIXTURE_PATH = (
    _REPOSITORY_ROOT
    / "tests"
    / "student_404131050"
    / "fixtures"
    / "java"
    / "oracle"
    / "OracleThrows.java"
)

_ORACLE_SOURCE_PATH = (
    _REPOSITORY_ROOT / "tests" / "student_404131050" / "oracle" / "ThrowsOracle.java"
)

Edge = tuple[str, str, str]

_EXPECTED_EDGES: set[Edge] = {
    (
        "OracleThrows",
        "OracleThrows",
        "FirstException",
    ),
    (
        "OracleThrows",
        "OracleThrows",
        "SecondException",
    ),
    (
        "OracleThrows",
        "execute",
        "FirstException",
    ),
    (
        "OracleThrows",
        "execute",
        "SecondException",
    ),
    (
        "OracleContract",
        "run",
        "FirstException",
    ),
    (
        "OracleContract",
        "run",
        "SecondException",
    ),
}


def _run_javac_oracle(class_directory: Path) -> set[Edge]:
    """Compile and execute the independent javac-based Oracle."""

    javac = shutil.which("javac")
    java = shutil.which("java")

    if javac is None or java is None:
        pytest.skip("A complete JDK is required for Oracle validation.")

    compile_result = subprocess.run(
        [
            javac,
            "-encoding",
            "UTF-8",
            "-d",
            str(class_directory),
            str(_ORACLE_SOURCE_PATH),
        ],
        cwd=_REPOSITORY_ROOT,
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )

    assert compile_result.returncode == 0, compile_result.stderr

    execution_result = subprocess.run(
        [
            java,
            "-cp",
            str(class_directory),
            "ThrowsOracle",
            str(_FIXTURE_PATH),
        ],
        cwd=_REPOSITORY_ROOT,
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )

    assert execution_result.returncode == 0, execution_result.stderr

    edges: set[Edge] = set()

    for output_line in execution_result.stdout.splitlines():
        if not output_line.strip():
            continue

        fields = output_line.split("\t")

        assert len(fields) == 3, f"Unexpected Oracle output: {output_line!r}"

        owner, declaration, exception = fields

        edges.add(
            (
                owner,
                declaration,
                exception,
            )
        )

    return edges


def _find_owner(context: Any) -> str:
    """Find the enclosing class or interface name."""

    current = getattr(context, "parentCtx", None)

    owner_context_types = {
        "ClassDeclarationContext",
        "InterfaceDeclarationContext",
    }

    while current is not None:
        if type(current).__name__ in owner_context_types:
            return current.IDENTIFIER().getText()

        current = getattr(current, "parentCtx", None)

    raise AssertionError("No enclosing class or interface was found.")


def _find_reference_parents(context: Any) -> list[str]:
    """Return deterministic scope information for the target pass."""

    owner = _find_owner(context)
    declaration = context.IDENTIFIER().getText()

    return [
        "oracle",
        owner,
        declaration,
    ]


def _run_openunderstand(
    monkeypatch: pytest.MonkeyPatch,
) -> set[Edge]:
    """Extract Throws edges with the OpenUnderstand pass."""

    source = _FIXTURE_PATH.read_text(encoding="utf-8")

    lexer = JavaLexer(InputStream(source))
    parser = JavaParserLabeled(CommonTokenStream(lexer))
    tree = parser.compilationUnit()

    assert parser.getNumberOfSyntaxErrors() == 0

    listener = sut.Throws_TrowsBy()

    monkeypatch.setattr(
        listener,
        "findmethodacess",
        lambda _context: [],
    )

    monkeypatch.setattr(
        sut.class_properties.ClassPropertiesListener,
        "findParents",
        staticmethod(_find_reference_parents),
    )

    monkeypatch.setattr(
        sut,
        "ProjectModel",
        SimpleNamespace(
            select=lambda: [
                SimpleNamespace(
                    root=str(_FIXTURE_PATH.parent),
                )
            ]
        ),
    )

    monkeypatch.setattr(
        sut,
        "throws_parent_finder",
        lambda _root, _exception: None,
    )

    ParseTreeWalker().walk(listener, tree)

    return {
        (
            str(reference["scope_parent"]),
            str(reference["scopename"]),
            str(reference["refent"]).rsplit(".", maxsplit=1)[-1],
        )
        for reference in listener.implement
    }


@pytest.mark.oracle
@pytest.mark.integration
def test_openunderstand_matches_javac_throws_oracle(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """OpenUnderstand Throws edges must match the javac AST."""

    oracle_edges = _run_javac_oracle(tmp_path)
    openunderstand_edges = _run_openunderstand(monkeypatch)

    assert oracle_edges == _EXPECTED_EDGES
    assert openunderstand_edges == oracle_edges
