import com.sun.source.tree.ClassTree;
import com.sun.source.tree.CompilationUnitTree;
import com.sun.source.tree.MethodTree;
import com.sun.source.tree.Tree;
import com.sun.source.util.JavacTask;
import com.sun.source.util.TreeScanner;

import java.io.IOException;
import java.nio.file.Path;
import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.Collections;
import java.util.Deque;
import java.util.List;

import javax.tools.Diagnostic;
import javax.tools.DiagnosticCollector;
import javax.tools.JavaCompiler;
import javax.tools.JavaFileObject;
import javax.tools.StandardJavaFileManager;
import javax.tools.ToolProvider;

public final class ThrowsOracle {

    private ThrowsOracle() {
    }

    public static void main(String[] args) throws IOException {
        if (args.length != 1) {
            System.err.println("Usage: ThrowsOracle <Java source file>");
            System.exit(2);
        }

        JavaCompiler compiler = ToolProvider.getSystemJavaCompiler();

        if (compiler == null) {
            System.err.println("A full JDK is required.");
            System.exit(2);
        }

        DiagnosticCollector<JavaFileObject> diagnostics =
                new DiagnosticCollector<>();

        List<String> rows = new ArrayList<>();

        try (StandardJavaFileManager fileManager =
                     compiler.getStandardFileManager(
                             diagnostics,
                             null,
                             null
                     )) {

            Iterable<? extends JavaFileObject> sourceFiles =
                    fileManager.getJavaFileObjectsFromPaths(
                            List.of(Path.of(args[0]))
                    );

            JavacTask task = (JavacTask) compiler.getTask(
                    null,
                    fileManager,
                    diagnostics,
                    List.of("-proc:none"),
                    null,
                    sourceFiles
            );

            Iterable<? extends CompilationUnitTree> units =
                    task.parse();

            TreeScanner<Void, Void> scanner =
                    new TreeScanner<>() {

                        private final Deque<String> owners =
                                new ArrayDeque<>();

                        @Override
                        public Void visitClass(
                                ClassTree node,
                                Void unused
                        ) {
                            String owner =
                                    node.getSimpleName().toString();

                            boolean namedClass = !owner.isEmpty();

                            if (namedClass) {
                                owners.push(owner);
                            }

                            try {
                                return super.visitClass(node, unused);
                            } finally {
                                if (namedClass) {
                                    owners.pop();
                                }
                            }
                        }

                        @Override
                        public Void visitMethod(
                                MethodTree node,
                                Void unused
                        ) {
                            if (!owners.isEmpty()
                                    && !node.getThrows().isEmpty()) {

                                String owner = owners.peek();

                                String declaration =
                                        node.getName()
                                                .contentEquals("<init>")
                                                ? owner
                                                : node.getName().toString();

                                for (Tree exceptionType
                                        : node.getThrows()) {

                                    rows.add(
                                            owner
                                                    + "\t"
                                                    + declaration
                                                    + "\t"
                                                    + exceptionType
                                    );
                                }
                            }

                            return super.visitMethod(node, unused);
                        }
                    };

            for (CompilationUnitTree unit : units) {
                scanner.scan(unit, null);
            }
        }

        boolean hasErrors = diagnostics
                .getDiagnostics()
                .stream()
                .anyMatch(
                        diagnostic ->
                                diagnostic.getKind()
                                        == Diagnostic.Kind.ERROR
                );

        if (hasErrors) {
            diagnostics.getDiagnostics().forEach(
                    diagnostic ->
                            System.err.println(diagnostic.toString())
            );
            System.exit(1);
        }

        Collections.sort(rows);
        rows.forEach(System.out::println);
    }
}