"""Unit tests for the Throws/ThrowsBy analysis pass."""

from types import SimpleNamespace

import pytest

from openunderstand.analysis_passes import Throws_ThrowsBy as sut


class _TextNode:
    """Minimal replacement for an ANTLR node exposing getText()."""

    def __init__(self, text: str) -> None:
        self._text = text

    def getText(self) -> str:
        return self._text


class MethodDeclarationContext:
    """Fake context whose class name matches the production check."""

    parentCtx = None

    def typeTypeOrVoid(self) -> _TextNode:
        return _TextNode("void")

    def getText(self) -> str:
        return "void execute() throws IOException {}"


class _RootContext:
    parentCtx = None


class _ChildContext:
    def __init__(self, parent: object) -> None:
        self.parentCtx = parent


class _FakeToken:
    def __str__(self) -> str:
        # The production implementation extracts line and column
        # from the fourth comma-separated element.
        return "[@1,0:0='x',<1>,7:4]"


class _QualifiedNameList:
    def getText(self) -> str:
        return "IOException"


class _ThrowsMethodContext:
    start = _FakeToken()

    def THROWS(self) -> bool:
        return True

    def qualifiedNameList(self) -> _QualifiedNameList:
        return _QualifiedNameList()


@pytest.mark.unit
def test_listener_starts_with_empty_reference_buffer() -> None:
    listener = sut.Throws_TrowsBy()

    assert listener.implement == []


@pytest.mark.unit
def test_findmethodreturntype_finds_method_parent() -> None:
    listener = sut.Throws_TrowsBy()
    method_context = MethodDeclarationContext()
    child_context = _ChildContext(method_context)

    return_type, method_content = listener.findmethodreturntype(child_context)

    assert return_type == "void"
    assert method_content == "void execute() throws IOException {}"


@pytest.mark.unit
def test_findmethodreturntype_returns_empty_values_without_method_parent() -> None:
    listener = sut.Throws_TrowsBy()
    child_context = _ChildContext(_RootContext())

    return_type, method_content = listener.findmethodreturntype(child_context)

    assert return_type == ""
    assert method_content == ""


@pytest.mark.unit
def test_parent_finder_returns_none_when_java_file_does_not_exist(
    write_java_file,
) -> None:
    existing_file = write_java_file(
        "src/org/example/ExistingException.java",
        "package org.example; class ExistingException {}",
    )

    result = sut.throws_parent_finder(
        str(existing_file.parents[3]),
        "MissingException",
    )

    assert result is None


@pytest.mark.unit
def test_enter_method_declaration_records_reference_metadata(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    listener = sut.Throws_TrowsBy()
    context = _ThrowsMethodContext()

    monkeypatch.setattr(
        listener,
        "findmethodacess",
        lambda _: ["public"],
    )
    monkeypatch.setattr(
        listener,
        "findmethodreturntype",
        lambda _: ("void", "void execute() throws IOException {}"),
    )
    monkeypatch.setattr(
        sut.class_properties.ClassPropertiesListener,
        "findParents",
        lambda _: ["sample", "Service", "execute"],
    )
    monkeypatch.setattr(
        sut,
        "ProjectModel",
        SimpleNamespace(select=lambda: [SimpleNamespace(root="C:/temporary/project")]),
    )
    monkeypatch.setattr(
        sut,
        "throws_parent_finder",
        lambda _root, _file_name: None,
    )

    listener.enterMethodDeclaration(context)

    assert len(listener.implement) == 1

    reference = listener.implement[0]

    assert reference["scopename"] == "execute"
    assert reference["scopelongname"] == "sample.Service.execute"
    assert reference["scope_parent"] == "Service"
    assert reference["scopemodifiers"] == ["public"]
    assert reference["scopereturntype"] == "void"
    assert reference["refent"] == "IOException"
    assert reference["potential_refent"] == "sample.Service.IOException"
    assert reference["line"] == "7"
    assert reference["col"] == "4"


class _FakeModifier:
    """Fake Java modifier node."""

    def __init__(self, text: str | None) -> None:
        self._text = text

    def classOrInterfaceModifier(self) -> _TextNode | None:
        if self._text is None:
            return None

        return _TextNode(self._text)


class ClassBodyDeclarationContext:
    """Fake context whose class name matches the production code."""

    parentCtx = None

    def __init__(self, modifiers: list[_FakeModifier]) -> None:
        self._modifiers = modifiers

    def modifier(self) -> list[_FakeModifier]:
        return self._modifiers


@pytest.mark.unit
def test_findmethodacess_returns_method_modifiers() -> None:
    listener = sut.Throws_TrowsBy()

    class_body_context = ClassBodyDeclarationContext(
        [
            _FakeModifier("public"),
            _FakeModifier("static"),
            _FakeModifier("final"),
        ]
    )

    child_context = _ChildContext(class_body_context)

    result = listener.findmethodacess(child_context)

    assert result == ["public", "static", "final"]


@pytest.mark.unit
def test_findmethodacess_ignores_non_class_modifiers() -> None:
    listener = sut.Throws_TrowsBy()

    class_body_context = ClassBodyDeclarationContext(
        [
            _FakeModifier("public"),
            _FakeModifier(None),
        ]
    )

    child_context = _ChildContext(class_body_context)

    result = listener.findmethodacess(child_context)

    assert result == ["public"]


@pytest.mark.unit
def test_findmethodacess_returns_empty_list_without_class_body_parent() -> None:
    listener = sut.Throws_TrowsBy()

    child_context = _ChildContext(_RootContext())

    result = listener.findmethodacess(child_context)

    assert result == []


class _ThrowsConstructorContext:
    """Fake constructor context for isolated listener tests."""

    start = _FakeToken()
    parentCtx = None

    def __init__(self, has_throws: bool = True) -> None:
        self._has_throws = has_throws

    def THROWS(self) -> bool:
        return self._has_throws

    def qualifiedNameList(self) -> _QualifiedNameList:
        return _QualifiedNameList()


@pytest.mark.unit
def test_constructor_with_throws_records_reference(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    listener = sut.Throws_TrowsBy()
    context = _ThrowsConstructorContext()

    monkeypatch.setattr(
        listener,
        "findmethodacess",
        lambda _: ["public"],
    )

    monkeypatch.setattr(
        listener,
        "findmethodreturntype",
        lambda _: ("", "Service() throws IOException {}"),
    )

    monkeypatch.setattr(
        sut.class_properties.ClassPropertiesListener,
        "findParents",
        lambda _: ["sample", "Service", "Service"],
    )

    monkeypatch.setattr(
        sut,
        "ProjectModel",
        SimpleNamespace(select=lambda: [SimpleNamespace(root="C:/temporary/project")]),
    )

    monkeypatch.setattr(
        sut,
        "throws_parent_finder",
        lambda _root, _exception_name: None,
    )

    listener.enterConstructorDeclaration(context)

    assert len(listener.implement) == 1

    reference = listener.implement[0]

    assert reference["scopename"] == "Service"
    assert reference["scopelongname"] == "sample.Service.Service"
    assert reference["scope_parent"] == "Service"
    assert reference["scopemodifiers"] == ["public"]
    assert reference["scopereturntype"] == ""
    assert reference["scopecontent"] == "Service() throws IOException {}"
    assert reference["refent"] == "IOException"
    assert reference["potential_refent"] == "sample.Service.IOException"
    assert reference["line"] == "7"
    assert reference["col"] == "4"


@pytest.mark.unit
def test_constructor_without_throws_records_nothing() -> None:
    listener = sut.Throws_TrowsBy()
    context = _ThrowsConstructorContext(has_throws=False)

    listener.enterConstructorDeclaration(context)

    assert listener.implement == []


class _ThrowsInterfaceMethodContext:
    """Fake interface-method context for isolated listener tests."""

    start = _FakeToken()
    parentCtx = None

    def __init__(self, has_throws: bool = True) -> None:
        self._has_throws = has_throws

    def THROWS(self) -> bool:
        return self._has_throws

    def qualifiedNameList(self) -> _QualifiedNameList:
        return _QualifiedNameList()


@pytest.mark.unit
def test_interface_method_with_throws_records_reference(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    listener = sut.Throws_TrowsBy()
    context = _ThrowsInterfaceMethodContext()

    monkeypatch.setattr(
        listener,
        "findmethodacess",
        lambda _: ["public", "abstract"],
    )

    monkeypatch.setattr(
        listener,
        "findmethodreturntype",
        lambda _: (
            "void",
            "void save() throws IOException;",
        ),
    )

    monkeypatch.setattr(
        sut.class_properties.ClassPropertiesListener,
        "findParents",
        lambda _: [
            "sample",
            "Repository",
            "save",
        ],
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

    listener.enterInterfaceMethodDeclaration(context)

    assert len(listener.implement) == 1

    reference = listener.implement[0]

    assert reference["scopename"] == "save"
    assert reference["scopelongname"] == "sample.Repository.save"
    assert reference["scope_parent"] == "Repository"
    assert reference["scopemodifiers"] == ["public", "abstract"]
    assert reference["scopereturntype"] == "void"
    assert reference["scopecontent"] == "void save() throws IOException;"
    assert reference["refent"] == "IOException"
    assert reference["potential_refent"] == "sample.Repository.IOException"
    assert reference["line"] == "7"
    assert reference["col"] == "4"


@pytest.mark.unit
def test_interface_method_without_throws_records_nothing() -> None:
    listener = sut.Throws_TrowsBy()
    context = _ThrowsInterfaceMethodContext(
        has_throws=False,
    )

    listener.enterInterfaceMethodDeclaration(context)

    assert listener.implement == []


@pytest.mark.unit
def test_parent_finder_returns_package_for_existing_exception(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_walk_result: list[tuple[str, list[str], list[str]]] = [
        (
            "C:/project/src/main/java/sample",
            [],
            ["Service.java"],
        ),
        (
            "C:/project/src/main/java/org/example/errors",
            [],
            ["IOException.java"],
        ),
    ]

    monkeypatch.setattr(
        sut.os,
        "walk",
        lambda _root: iter(fake_walk_result),
    )

    result = sut.throws_parent_finder(
        "C:/project",
        "IOException",
    )

    assert result == "org.example.errors"


@pytest.mark.unit
def test_resolved_exception_uses_qualified_name(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    listener = sut.Throws_TrowsBy()
    context = _ThrowsMethodContext()

    monkeypatch.setattr(
        listener,
        "findmethodacess",
        lambda _: ["public"],
    )

    monkeypatch.setattr(
        listener,
        "findmethodreturntype",
        lambda _: (
            "void",
            "void execute() throws IOException {}",
        ),
    )

    monkeypatch.setattr(
        sut.class_properties.ClassPropertiesListener,
        "findParents",
        lambda _: [
            "sample",
            "Service",
            "execute",
        ],
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
        lambda _root, _exception_name: "org.example.errors",
    )

    listener.enterMethodDeclaration(context)

    assert len(listener.implement) == 1

    reference = listener.implement[0]

    assert reference["refent"] == "org.example.errors.IOException"
    assert reference["scopename"] == "execute"
    assert reference["scopelongname"] == "sample.Service.execute"


class _MultipleQualifiedNameList:
    """Fake qualified-name list containing multiple exceptions."""

    def getText(self) -> str:
        return "IOException,SQLException"


class _MultipleThrowsMethodContext:
    """Fake method declaration containing multiple thrown exceptions."""

    start = _FakeToken()
    parentCtx = None

    def THROWS(self) -> bool:
        return True

    def qualifiedNameList(self) -> _MultipleQualifiedNameList:
        return _MultipleQualifiedNameList()


@pytest.mark.unit
@pytest.mark.xfail(
    strict=True,
    reason="Known defect: only the final exception in a throws list is recorded.",
)
def test_method_with_multiple_exceptions_records_every_reference(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    listener = sut.Throws_TrowsBy()
    context = _MultipleThrowsMethodContext()

    monkeypatch.setattr(
        listener,
        "findmethodacess",
        lambda _: ["public"],
    )

    monkeypatch.setattr(
        listener,
        "findmethodreturntype",
        lambda _: (
            "void",
            "void execute() throws IOException, SQLException {}",
        ),
    )

    monkeypatch.setattr(
        sut.class_properties.ClassPropertiesListener,
        "findParents",
        lambda _: [
            "sample",
            "Service",
            "execute",
        ],
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

    listener.enterMethodDeclaration(context)

    recorded_exceptions = [reference["refent"] for reference in listener.implement]

    assert recorded_exceptions == [
        "IOException",
        "SQLException",
    ]


@pytest.mark.unit
def test_short_parent_chain_sets_scope_parent_to_none(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    listener = sut.Throws_TrowsBy()
    context = _ThrowsMethodContext()

    monkeypatch.setattr(
        listener,
        "findmethodacess",
        lambda _: [],
    )

    monkeypatch.setattr(
        listener,
        "findmethodreturntype",
        lambda _: (
            "void",
            "void execute() throws IOException {}",
        ),
    )

    monkeypatch.setattr(
        sut.class_properties.ClassPropertiesListener,
        "findParents",
        lambda _: [
            "Service",
            "execute",
        ],
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

    listener.enterMethodDeclaration(context)

    assert len(listener.implement) == 1

    reference = listener.implement[0]

    assert reference["scopename"] == "execute"
    assert reference["scopelongname"] == "Service.execute"
    assert reference["scope_parent"] is None
    assert reference["potential_refent"] == "Service.IOException"


@pytest.mark.unit
def test_nested_class_uses_immediate_parent_as_scope_parent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    listener = sut.Throws_TrowsBy()
    context = _ThrowsMethodContext()

    monkeypatch.setattr(
        listener,
        "findmethodacess",
        lambda _: ["public"],
    )

    monkeypatch.setattr(
        listener,
        "findmethodreturntype",
        lambda _: (
            "void",
            "void execute() throws IOException {}",
        ),
    )

    monkeypatch.setattr(
        sut.class_properties.ClassPropertiesListener,
        "findParents",
        lambda _: [
            "sample",
            "Outer",
            "Inner",
            "execute",
        ],
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

    listener.enterMethodDeclaration(context)

    assert len(listener.implement) == 1

    reference = listener.implement[0]

    assert reference["scopename"] == "execute"
    assert reference["scopelongname"] == "sample.Outer.Inner.execute"
    assert reference["scope_parent"] == "Inner"
    assert reference["potential_refent"] == "sample.Outer.Inner.IOException"


@pytest.mark.unit
def test_findmethodreturntype_traverses_multiple_parent_levels() -> None:
    listener = sut.Throws_TrowsBy()
    method_context = MethodDeclarationContext()

    intermediate_context = _ChildContext(method_context)
    nested_context = _ChildContext(intermediate_context)

    return_type, method_content = listener.findmethodreturntype(nested_context)

    assert return_type == "void"
    assert method_content == "void execute() throws IOException {}"


@pytest.mark.unit
def test_findmethodacess_traverses_multiple_parent_levels() -> None:
    listener = sut.Throws_TrowsBy()

    class_body_context = ClassBodyDeclarationContext(
        [
            _FakeModifier("public"),
            _FakeModifier("static"),
        ]
    )

    intermediate_context = _ChildContext(class_body_context)
    nested_context = _ChildContext(intermediate_context)

    result = listener.findmethodacess(nested_context)

    assert result == ["public", "static"]


@pytest.mark.unit
def test_enter_method_declaration_passes_context_to_modifier_lookup(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    listener = sut.Throws_TrowsBy()
    context = _ThrowsMethodContext()

    received_contexts: list[object] = []

    def fake_findmethodacess(received_context: object) -> list[str]:
        received_contexts.append(received_context)
        return ["public"]

    monkeypatch.setattr(
        listener,
        "findmethodacess",
        fake_findmethodacess,
    )

    monkeypatch.setattr(
        listener,
        "findmethodreturntype",
        lambda _: (
            "void",
            "void execute() throws IOException {}",
        ),
    )

    monkeypatch.setattr(
        sut.class_properties.ClassPropertiesListener,
        "findParents",
        lambda _: [
            "sample",
            "Service",
            "execute",
        ],
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

    listener.enterMethodDeclaration(context)

    assert received_contexts == [context]
