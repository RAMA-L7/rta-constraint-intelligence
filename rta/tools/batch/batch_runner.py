"""
SDC Batch Runner — Process all SDC files in a directory.

Usage:
    from batch_runner import batch_check, batch_report
    results = batch_check("designs/")
    results = batch_report("designs/", report_type="coverage")

CLI:
    sdc-tools batch check ./sdc_files/
    sdc-tools batch report coverage ./sdc_files/ --output-dir ./reports/
    sdc-tools batch lint ./sdc_files/ --fix
"""

import os
from dataclasses import dataclass, field
from typing import List, Optional, Callable
from pathlib import Path


# ── Data classes ────────────────────────────────────────────────────────────────

@dataclass
class BatchResult:
    """Result of processing a single SDC file."""
    filepath: str
    status: str              # "ok" | "error" | "skipped"
    message: str = ""
    data: object = None      # module-specific result (CheckResult, etc.)


@dataclass
class BatchSummary:
    """Summary of all batch processing results."""
    total: int = 0
    ok: int = 0
    errors: int = 0
    skipped: int = 0
    results: List[BatchResult] = field(default_factory=list)

    def print_summary(self) -> str:
        lines = [
            f"Batch Summary:",
            f"  Total:  {self.total}",
            f"  OK:     {self.ok}",
            f"  Errors: {self.errors}",
            f"  Skipped: {self.skipped}",
        ]
        return "\n".join(lines)


# ── File discovery ──────────────────────────────────────────────────────────────

def find_sdc_files(directory: str, recursive: bool = True) -> List[str]:
    """Find all .sdc files in a directory."""
    path = Path(directory)
    if not path.exists():
        raise FileNotFoundError(f"Directory not found: {directory}")
    if not path.is_dir():
        raise NotADirectoryError(f"Not a directory: {directory}")

    pattern = "**/*.sdc" if recursive else "*.sdc"
    return sorted([str(p) for p in path.glob(pattern) if p.is_file()])


# ── Batch processing functions ──────────────────────────────────────────────────

def _process_files(
    filepaths: List[str],
    processor: Callable[[str], BatchResult],
    max_files: int = 0,
) -> BatchSummary:
    """Process multiple files with a processor function."""
    if max_files and len(filepaths) > max_files:
        filepaths = filepaths[:max_files]

    summary = BatchSummary(total=len(filepaths))

    for fp in filepaths:
        try:
            result = processor(fp)
            summary.results.append(result)
            if result.status == "ok":
                summary.ok += 1
            elif result.status == "error":
                summary.errors += 1
            else:
                summary.skipped += 1
        except Exception as e:
            summary.results.append(BatchResult(
                filepath=fp, status="error",
                message=f"Unexpected error: {e}",
            ))
            summary.errors += 1

    return summary


def batch_check(directory: str, verbose: bool = False) -> BatchSummary:
    """Run SDC checker on all .sdc files in a directory."""
    from checker import check_sdc

    def _check_file(fp: str) -> BatchResult:
        try:
            with open(fp, "r", encoding="utf-8") as f:
                text = f.read()
        except Exception as e:
            return BatchResult(filepath=fp, status="error", message=f"Cannot read: {e}")

        result = check_sdc(text)

        status = "ok"
        msg = f"{len(result.errors)} errors, {len(result.warnings)} warnings"
        if result.errors:
            status = "error"
        elif result.warnings:
            status = "ok"  # warnings don't fail

        detail = result if verbose else None
        return BatchResult(filepath=fp, status=status, message=msg, data=detail)

    files = find_sdc_files(directory)
    return _process_files(files, _check_file)


def batch_report(
    directory: str,
    report_type: str = "check",
    output_dir: Optional[str] = None,
) -> BatchSummary:
    """Generate HTML reports for all .sdc files in a directory."""
    from checker import check_sdc
    from reporter import generate_check_report, generate_coverage_report
    from coverage import parse_sdc_coverage

    def _report_file(fp: str) -> BatchResult:
        try:
            with open(fp, "r", encoding="utf-8") as f:
                text = f.read()
        except Exception as e:
            return BatchResult(filepath=fp, status="error", message=f"Cannot read: {e}")

        try:
            if report_type == "check":
                result = check_sdc(text)
                html = generate_check_report(result, Path(fp).name)
            elif report_type == "coverage":
                result = parse_sdc_coverage(text, Path(fp).name)
                html = generate_coverage_report(result, Path(fp).name)
            else:
                return BatchResult(filepath=fp, status="skipped",
                                   message=f"Unknown report type: {report_type}")

            if output_dir:
                out_path = Path(output_dir) / f"{Path(fp).stem}_{report_type}.html"
                out_path.write_text(html, encoding="utf-8")
                return BatchResult(filepath=fp, status="ok",
                                   message=f"Written to {out_path}")
            return BatchResult(filepath=fp, status="ok",
                               message=f"Report generated ({len(html)} bytes)")

        except Exception as e:
            return BatchResult(filepath=fp, status="error",
                               message=f"Report failed: {e}")

    files = find_sdc_files(directory)

    if output_dir:
        Path(output_dir).mkdir(parents=True, exist_ok=True)

    return _process_files(files, _report_file)


def batch_lint(directory: str, fix: bool = False) -> BatchSummary:
    """Lint all .sdc files in a directory."""
    from linter import lint_sdc_file

    def _lint_file(fp: str) -> BatchResult:
        result = lint_sdc_file(fp, fix=fix)
        if result.warnings > 0:
            status = "error" if result.warnings > 5 else "ok"
            msg = f"{result.warnings} warnings, {result.fixed} fixes applied"
        else:
            status = "ok"
            msg = "Clean"

        return BatchResult(filepath=fp, status=status, message=msg, data=result)

    files = find_sdc_files(directory)
    return _process_files(files, _lint_file)
