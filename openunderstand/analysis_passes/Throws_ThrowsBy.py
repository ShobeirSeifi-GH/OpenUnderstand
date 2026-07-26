import os

from gen.javaLabeled.JavaParserLabeled import JavaParserLabeled
from gen.javaLabeled.JavaParserLabeledListener import JavaParserLabeledListener

import openunderstand.analysis_passes.class_properties as class_properties
from openunderstand.oudb.models import ProjectModel


def throws_parent_finder(root_dir, file_name):
    for root, _dirs, files in os.walk(root_dir):
        for file in files:
            if file.endswith(".java") and file == (file_name + ".java"):
                root_splited = str(root).split("/")
                org_index = root_splited.index("org")
                return ".".join(root_splited[org_index:])


class Throws_TrowsBy(JavaParserLabeledListener):
    def __init__(self):
        self.implement = []

    def findmethodreturntype(self, c):
        return_type = ""
        context = ""
        current = c

        declaration_types = {
            "ConstructorDeclarationContext",
            "MethodDeclarationContext",
            "InterfaceMethodDeclarationContext",
        }

        while current is not None:
            current_type = type(current).__name__

            if current_type in declaration_types:
                type_type_or_void = getattr(
                    current,
                    "typeTypeOrVoid",
                    None,
                )

                if type_type_or_void is not None:
                    type_node = type_type_or_void()

                    if type_node is not None:
                        return_type = type_node.getText()

                context = current.getText()
                break

            current = getattr(current, "parentCtx", None)

        return return_type, context

    def findmethodacess(self, c):
        parents = ""
        modifiers = []
        current = c
        while current is not None:
            if "ClassBodyDeclaration" in type(current.parentCtx).__name__:
                parents = current.parentCtx.modifier()
                break
            current = current.parentCtx
        for x in parents:
            if x.classOrInterfaceModifier():
                modifiers.append(x.classOrInterfaceModifier().getText())
        return modifiers

    def _record_throws_references(
        self,
        ctx: JavaParserLabeled.EnumDeclarationContext,
    ):
        if not ctx.THROWS():
            return

        modifiers = self.findmethodacess(ctx)
        method_return, method_context = self.findmethodreturntype(ctx)

        exception_names = [
            name.strip() for name in ctx.qualifiedNameList().getText().split(",") if name.strip()
        ]

        allrefs = class_properties.ClassPropertiesListener.findParents(ctx)
        refent = allrefs[-1]
        entlongname = ".".join(allrefs)
        root = ProjectModel.select()[0].root
        [line, col] = str(ctx.start).split(",")[3].split(":")

        for exception_name in exception_names:
            resolved_name = exception_name
            exception_package = throws_parent_finder(
                root,
                exception_name,
            )

            if exception_package is not None:
                resolved_name = exception_package + "." + exception_name

            self.implement.append(
                {
                    "scopename": refent,
                    "scopelongname": entlongname,
                    "scopemodifiers": modifiers,
                    "scopereturntype": method_return,
                    "scopecontent": method_context,
                    "line": line,
                    "col": col[:-1],
                    "refent": resolved_name,
                    "scope_parent": (allrefs[-2] if len(allrefs) > 2 else None),
                    "potential_refent": (".".join(allrefs[:-1]) + "." + resolved_name),
                }
            )

    def enterMethodDeclaration(
        self,
        ctx: JavaParserLabeled.EnumDeclarationContext,
    ):
        self._record_throws_references(ctx)

    def enterConstructorDeclaration(
        self,
        ctx: JavaParserLabeled.EnumDeclarationContext,
    ):
        self._record_throws_references(ctx)

    def enterInterfaceMethodDeclaration(
        self,
        ctx: JavaParserLabeled.EnumDeclarationContext,
    ):
        self._record_throws_references(ctx)
