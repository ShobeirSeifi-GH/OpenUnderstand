"""Enforce independent line- and branch-coverage quality gates."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any


def calculate_percentage(covered: int, total: int) -> float:
    """Calculate a coverage percentage.

    A metric with no measurable items is treated as fully covered.
    """
    if total == 0:
        return 100.0

    return covered / total * 100.0


def load_coverage_totals(report_path: Path) -> dict[str, Any]:
    """Load and validate the totals section of a coverage.py JSON report."""
    if not report_path.is_file():
        raise FileNotFoundError(f"Coverage report does not exist: {report_path}")

    try:
        report_data = json.loads(report_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise ValueError(f"Coverage report is not valid JSON: {report_path}") from error

    if not isinstance(report_data, dict):
        raise ValueError("Coverage report root must be a JSON object.")

    totals = report_data.get("totals")

    if not isinstance(totals, dict):
        raise ValueError("Coverage report does not contain a valid 'totals' object.")

    required_fields = {
        "num_statements",
        "covered_lines",
        "num_branches",
        "covered_branches",
    }

    missing_fields = required_fields.difference(totals)

    if missing_fields:
        missing = ", ".join(sorted(missing_fields))
        raise ValueError(f"Coverage report is missing required fields: {missing}")

    return totals


def append_github_summary(
    line_coverage: float,
    branch_coverage: float,
    minimum_line: float,
    minimum_branch: float,
    passed: bool,
) -> None:
    """Append coverage results to the GitHub Actions job summary."""
    summary_file = os.environ.get("GITHUB_STEP_SUMMARY")

    if not summary_file:
        return

    status = "PASS" if passed else "FAIL"

    summary = (
        "\n## Coverage Quality Gates\n\n"
        "| Metric | Actual | Required | Result |\n"
        "|---|---:|---:|---|\n"
        f"| Line coverage | {line_coverage:.2f}% | {minimum_line:.2f}% | "
        f"{'PASS' if line_coverage >= minimum_line else 'FAIL'} |\n"
        f"| Branch coverage | {branch_coverage:.2f}% | {minimum_branch:.2f}% | "
        f"{'PASS' if branch_coverage >= minimum_branch else 'FAIL'} |\n\n"
        f"**Overall result: {status}**\n"
    )

    with Path(summary_file).open("a", encoding="utf-8") as file:
        file.write(summary)


def parse_arguments() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Check line and branch coverage against independent thresholds."
    )

    parser.add_argument(
        "--report",
        type=Path,
        default=Path("coverage-reports/coverage.json"),
        help="Path to the coverage.py JSON report.",
    )
    parser.add_argument(
        "--min-line",
        type=float,
        default=80.0,
        help="Minimum required line coverage percentage.",
    )
    parser.add_argument(
        "--min-branch",
        type=float,
        default=70.0,
        help="Minimum required branch coverage percentage.",
    )

    return parser.parse_args()


def validate_threshold(name: str, value: float) -> None:
    """Validate that a threshold is between zero and one hundred."""
    if not 0.0 <= value <= 100.0:
        raise ValueError(f"{name} must be between 0 and 100; received {value}.")


def main() -> int:
    """Run the coverage quality-gate check."""
    arguments = parse_arguments()

    try:
        validate_threshold("Line threshold", arguments.min_line)
        validate_threshold("Branch threshold", arguments.min_branch)

        totals = load_coverage_totals(arguments.report)

        statement_count = int(totals["num_statements"])
        covered_line_count = int(totals["covered_lines"])
        branch_count = int(totals["num_branches"])
        covered_branch_count = int(totals["covered_branches"])

        line_coverage = calculate_percentage(
            covered=covered_line_count,
            total=statement_count,
        )
        branch_coverage = calculate_percentage(
            covered=covered_branch_count,
            total=branch_count,
        )
    except (FileNotFoundError, ValueError, TypeError, KeyError) as error:
        print(f"Quality-gate error: {error}", file=sys.stderr)
        return 2

    line_passed = line_coverage >= arguments.min_line
    branch_passed = branch_coverage >= arguments.min_branch
    all_passed = line_passed and branch_passed

    print("Coverage quality-gate results")
    print("-" * 52)
    print(
        f"Line coverage:   {line_coverage:6.2f}% "
        f"(required: {arguments.min_line:.2f}%)"
    )
    print(
        f"Branch coverage: {branch_coverage:6.2f}% "
        f"(required: {arguments.min_branch:.2f}%)"
    )
    print("-" * 52)

    append_github_summary(
        line_coverage=line_coverage,
        branch_coverage=branch_coverage,
        minimum_line=arguments.min_line,
        minimum_branch=arguments.min_branch,
        passed=all_passed,
    )

    if not line_passed:
        print("FAILED: line coverage is below the required threshold.", file=sys.stderr)

    if not branch_passed:
        print("FAILED: branch coverage is below the required threshold.", file=sys.stderr)

    if not all_passed:
        return 1

    print("PASSED: all coverage quality gates are satisfied.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
