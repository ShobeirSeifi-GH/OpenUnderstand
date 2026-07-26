"""Integration and persistence tests for Throws and ThrowsBy references."""

from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from antlr4 import CommonTokenStream, InputStream, ParseTreeWalker
from gen.javaLabeled.JavaLexer import JavaLexer
from gen.javaLabeled.JavaParserLabeled import JavaParserLabeled

from openunderstand.analysis_passes import Throws_ThrowsBy as sut
from openunderstand.ounderstand import project as project_module


def _reference_metadata() -> dict[str, object]:
    """Return one listener result suitable for persistence tests."""

    return {
        "scopename": "execute",
        "scopelongname": "sample.Service.execute",
        "scopemodifiers": ["public"],
        "scopereturntype": "void",
        "scopecontent": "void execute() throws IOException {}",
        "line": "7",
        "col": "4",
        "refent": "java.io.IOException",
        "scope_parent": "Service",
        "potential_refent": "sample.Service.java.io.IOException",
    }


@pytest.mark.integration
def test_malformed_java_is_recovered_without_listener_crash(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """ANTLR should report malformed input while the listener remains usable."""

    fixture_path = (
        Path(__file__).parents[1] / "fixtures" / "java" / "malformed" / "BrokenThrows.java"
    )
    source = fixture_path.read_text(encoding="utf-8")

    lexer = JavaLexer(InputStream(source))
    parser = JavaParserLabeled(CommonTokenStream(lexer))
    tree = parser.compilationUnit()

    assert parser.getNumberOfSyntaxErrors() > 0

    listener = sut.Throws_TrowsBy()

    monkeypatch.setattr(
        listener,
        "findmethodacess",
        lambda _context: [],
    )
    monkeypatch.setattr(
        listener,
        "findmethodreturntype",
        lambda _context: ("void", source),
    )
    monkeypatch.setattr(
        sut.class_properties.ClassPropertiesListener,
        "findParents",
        lambda _context: ["sample", "BrokenThrows", "execute"],
    )
    monkeypatch.setattr(
        sut,
        "ProjectModel",
        SimpleNamespace(
            select=lambda: [
                SimpleNamespace(
                    root="C:/temporary/project",
                )
            ]
        ),
    )
    monkeypatch.setattr(
        sut,
        "throws_parent_finder",
        lambda _root, _exception_name: None,
    )

    ParseTreeWalker().walk(listener, tree)

    assert len(listener.implement) == 1
    assert listener.implement[0]["refent"] == "IOException"
    assert listener.implement[0]["scopename"] == "execute"


@pytest.mark.unit
def test_add_throws_creates_matching_inverse_throwsby_reference(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """ThrowsBy must reverse the entity and scope of the Throws reference."""

    project = project_module.Project()

    file_entity = SimpleNamespace(_id=10, name="Example.java")
    method_entity = SimpleNamespace(_id=20, name="execute")
    exception_entity = SimpleNamespace(_id=30, name="IOException")

    reference_calls: list[dict[str, Any]] = []

    def fake_entity_get_or_create(
        **_kwargs: Any,
    ) -> tuple[SimpleNamespace, bool]:
        return method_entity, False

    def fake_reference_get_or_create(
        **kwargs: Any,
    ) -> tuple[SimpleNamespace, bool]:
        reference_calls.append(dict(kwargs))
        return SimpleNamespace(), False

    monkeypatch.setattr(
        project_module,
        "EntityModel",
        SimpleNamespace(
            get_or_create=fake_entity_get_or_create,
        ),
    )
    monkeypatch.setattr(
        project_module,
        "ReferenceModel",
        SimpleNamespace(
            get_or_create=fake_reference_get_or_create,
        ),
    )
    monkeypatch.setattr(
        project,
        "findKindWithKeywords",
        lambda _kind, _modifiers: 60,
    )
    monkeypatch.setattr(
        project,
        "getThrowEntity",
        lambda _longname, _file_address, _file_entity: exception_entity,
    )

    project.addThrows_TrowsByRefs(
        [_reference_metadata()],
        file_entity,
        "Example.java",
        236,
        237,
        True,
    )

    assert len(reference_calls) == 2

    throws_reference = reference_calls[0]
    throwsby_reference = reference_calls[1]

    assert throws_reference["_kind"] == 236
    assert throws_reference["_ent"] is exception_entity
    assert throws_reference["_scope"] is method_entity

    assert throwsby_reference["_kind"] == 237
    assert throwsby_reference["_ent"] is method_entity
    assert throwsby_reference["_scope"] is exception_entity

    assert throwsby_reference["_file"] is throws_reference["_file"]
    assert throwsby_reference["_line"] == throws_reference["_line"]
    assert throwsby_reference["_column"] == throws_reference["_column"]


@pytest.mark.integration
def test_repeated_analysis_pass_uses_stable_reference_identity(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Repeated persistence passes must request the same reference identities."""

    project = project_module.Project()

    file_entity = SimpleNamespace(_id=10, name="Example.java")
    method_entity = SimpleNamespace(_id=20, name="execute")
    exception_entity = SimpleNamespace(_id=30, name="IOException")

    reference_calls: list[dict[str, Any]] = []

    def fake_entity_get_or_create(
        **_kwargs: Any,
    ) -> tuple[SimpleNamespace, bool]:
        return method_entity, False

    def fake_reference_get_or_create(
        **kwargs: Any,
    ) -> tuple[SimpleNamespace, bool]:
        reference_calls.append(dict(kwargs))
        return SimpleNamespace(), False

    monkeypatch.setattr(
        project_module,
        "EntityModel",
        SimpleNamespace(
            get_or_create=fake_entity_get_or_create,
        ),
    )
    monkeypatch.setattr(
        project_module,
        "ReferenceModel",
        SimpleNamespace(
            get_or_create=fake_reference_get_or_create,
        ),
    )
    monkeypatch.setattr(
        project,
        "findKindWithKeywords",
        lambda _kind, _modifiers: 60,
    )
    monkeypatch.setattr(
        project,
        "getThrowEntity",
        lambda _longname, _file_address, _file_entity: exception_entity,
    )

    for _ in range(2):
        project.addThrows_TrowsByRefs(
            [_reference_metadata()],
            file_entity,
            "Example.java",
            236,
            237,
            True,
        )

    assert len(reference_calls) == 4

    identity_fields = (
        "_kind",
        "_file",
        "_line",
        "_column",
        "_ent",
        "_scope",
    )

    first_pass = [tuple(call[field] for field in identity_fields) for call in reference_calls[:2]]
    second_pass = [tuple(call[field] for field in identity_fields) for call in reference_calls[2:]]

    assert second_pass == first_pass
    assert {call["_kind"] for call in reference_calls} == {236, 237}


@pytest.mark.integration
def test_throws_reference_graph_is_bidirectional_and_consistent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Every Throws edge must have exactly one consistent inverse edge."""

    project = project_module.Project()

    file_entity = SimpleNamespace(_id=10, name="Example.java")
    method_entity = SimpleNamespace(_id=20, name="execute")

    exception_entities = {
        "java.io.IOException": SimpleNamespace(
            _id=30,
            name="IOException",
        ),
        "java.sql.SQLException": SimpleNamespace(
            _id=31,
            name="SQLException",
        ),
    }

    first_reference = _reference_metadata()

    second_reference = {
        **_reference_metadata(),
        "refent": "java.sql.SQLException",
        "potential_refent": "sample.Service.java.sql.SQLException",
        "line": "8",
        "col": "12",
    }

    reference_calls: list[dict[str, Any]] = []

    def fake_entity_get_or_create(
        **_kwargs: Any,
    ) -> tuple[SimpleNamespace, bool]:
        return method_entity, False

    def fake_reference_get_or_create(
        **kwargs: Any,
    ) -> tuple[SimpleNamespace, bool]:
        reference_calls.append(dict(kwargs))
        return SimpleNamespace(), False

    def fake_get_throw_entity(
        longname: str,
        _file_address: str,
        _file_entity: object,
    ) -> SimpleNamespace:
        return exception_entities[longname]

    monkeypatch.setattr(
        project_module,
        "EntityModel",
        SimpleNamespace(
            get_or_create=fake_entity_get_or_create,
        ),
    )
    monkeypatch.setattr(
        project_module,
        "ReferenceModel",
        SimpleNamespace(
            get_or_create=fake_reference_get_or_create,
        ),
    )
    monkeypatch.setattr(
        project,
        "findKindWithKeywords",
        lambda _kind, _modifiers: 60,
    )
    monkeypatch.setattr(
        project,
        "getThrowEntity",
        fake_get_throw_entity,
    )

    project.addThrows_TrowsByRefs(
        [
            first_reference,
            second_reference,
        ],
        file_entity,
        "Example.java",
        236,
        237,
        True,
    )

    throws_calls = [call for call in reference_calls if call["_kind"] == 236]
    throwsby_calls = [call for call in reference_calls if call["_kind"] == 237]

    assert len(throws_calls) == 2
    assert len(throwsby_calls) == 2

    direct_edges = {
        (
            call["_scope"]._id,
            call["_ent"]._id,
            call["_file"]._id,
            call["_line"],
            call["_column"],
        )
        for call in throws_calls
    }

    inverse_edges = {
        (
            call["_ent"]._id,
            call["_scope"]._id,
            call["_file"]._id,
            call["_line"],
            call["_column"],
        )
        for call in throwsby_calls
    }

    assert direct_edges == inverse_edges
    assert len(direct_edges) == len(throws_calls)

    for source_id, target_id, *_location in direct_edges:
        assert source_id != target_id
