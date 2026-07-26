"""Performance regression benchmark for the Throws/ThrowsBy analysis."""

from __future__ import annotations

import argparse
import json
import statistics
import time
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from openunderstand.analysis_passes import Throws_ThrowsBy as sut


class _TextNode:
    """Minimal parser node exposing getText()."""

    def __init__(self, text: str) -> None:
        self._text = text

    def getText(self) -> str:
        return self._text


class _StartToken:
    """Stable source-location token."""

    def __str__(self) -> str:
        return "[@1,0:0='x',<1>,12:34]"


class _ThrowsContext:
    """Synthetic declaration containing three exceptions."""

    parentCtx = None
    start = _StartToken()

    def THROWS(self) -> bool:
        return True

    def qualifiedNameList(self) -> _TextNode:
        return _TextNode("IOException,SQLException,TimeoutException")


def _run_batch(declaration_count: int) -> float:
    """Process a declaration batch and return elapsed seconds."""

    listener = sut.Throws_TrowsBy()
    context = _ThrowsContext()

    started_at = time.perf_counter()

    for _ in range(declaration_count):
        listener.enterMethodDeclaration(context)

    elapsed = time.perf_counter() - started_at
    expected_references = declaration_count * 3

    if len(listener.implement) != expected_references:
        raise RuntimeError(
            "Unexpected reference count: "
            f"expected {expected_references}, "
            f"received {len(listener.implement)}"
        )

    return elapsed


def _parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()

    parser.add_argument("--small-batch", type=int, default=1000)
    parser.add_argument("--large-batch", type=int, default=2000)
    parser.add_argument("--repeats", type=int, default=5)
    parser.add_argument("--max-seconds", type=float, default=3.0)
    parser.add_argument("--max-growth", type=float, default=3.0)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("performance-reports/throws-performance.json"),
    )

    return parser.parse_args()


def main() -> int:
    args = _parse_arguments()

    with (
        patch.object(
            sut.Throws_TrowsBy,
            "findmethodacess",
            return_value=["public"],
        ),
        patch.object(
            sut.Throws_TrowsBy,
            "findmethodreturntype",
            return_value=(
                "void",
                "void execute() throws IOException {}",
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
                        root="C:/benchmark/project",
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
        _run_batch(100)

        small_samples = [_run_batch(args.small_batch) for _ in range(args.repeats)]
        large_samples = [_run_batch(args.large_batch) for _ in range(args.repeats)]

    small_median = statistics.median(small_samples)
    large_median = statistics.median(large_samples)

    growth_ratio = large_median / small_median if small_median > 0 else float("inf")

    references_processed = args.large_batch * 3
    references_per_second = references_processed / large_median

    result = {
        "small_batch": args.small_batch,
        "large_batch": args.large_batch,
        "repeats": args.repeats,
        "small_median_seconds": round(small_median, 6),
        "large_median_seconds": round(large_median, 6),
        "growth_ratio": round(growth_ratio, 3),
        "references_per_second": round(
            references_per_second,
            2,
        ),
        "max_seconds": args.max_seconds,
        "max_growth": args.max_growth,
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, indent=2),
        encoding="utf-8",
    )

    print("Throws/ThrowsBy performance benchmark")
    print("-" * 48)
    print(f"Small batch median: {small_median:.6f}s")
    print(f"Large batch median: {large_median:.6f}s")
    print(f"Growth ratio:       {growth_ratio:.3f}x")
    print(f"References/sec:     {references_per_second:,.2f}")
    print("-" * 48)

    failures: list[str] = []

    if large_median > args.max_seconds:
        failures.append(f"large batch exceeded {args.max_seconds:.2f}s")

    if growth_ratio > args.max_growth:
        failures.append(f"growth ratio exceeded {args.max_growth:.2f}x")

    if failures:
        for failure in failures:
            print(f"FAILED: {failure}")
        return 1

    print("PASSED: performance regression gates satisfied.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
