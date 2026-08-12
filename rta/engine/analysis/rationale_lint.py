"""
Rationale-comment linting (F1, SDC-150).

Answers: *does every timing exception that can silently hide a violation carry
an explanatory comment?*

SDC-020 already *tells* the engineer to document false paths ("Add a comment
explaining why"); this module enforces it. An undocumented exception is a
"silent killer": a later engineer cannot tell whether the path was exempted
because it is genuinely false (async CDC, test mode) or because someone hid a
real violation. Field practice treats timing constraints as first-class,
versioned artifacts; a rationale comment is the audit trail.

SCOPE
=====
Pure text / line-proximity check. No new data model, no netlist required, no
clock model required. Runs in BOTH SDC-only and design-aware modes.

  set_false_path
  set_multicycle_path
  set_case_analysis

are the three exception types that can silence a real violation and that
SDC-020-style advice asks to document.

NOISE BUDGET
============
A finding fires only when NO substantive comment exists within the 3 lines
immediately above the exception OR inline on the same line. A comment counts
as substantive when, after stripping the leading '#', whitespace, and pure
separator characters ('-', '=', '*', '_', '/'), at least 10 characters of
actual prose remain. This keeps decorative comment fences
('# -----------------------------------') quiet while requiring real
rationale for exceptions.

Anything the resolver cannot prove stays silent — never a false positive.
"""

from dataclasses import dataclass
from typing import List, Optional

#: The three exception commands that can hide a violation.
_EXCEPTION_KEYWORDS: tuple = (
    "set_false_path",
    "set_multicycle_path",
    "set_case_analysis",
)

#: Minimum characters of prose for a comment to count as substantive rationale.
MIN_COMMENT_CHARS: int = 10

#: Lines above the exception that still count as "nearby" (the comment block).
PROXIMITY_LINES: int = 3

#: Chars that make a comment look decorative rather than explanatory.
_SEPARATOR_CHARS: str = "#-=*_/ \t"


@dataclass
class Finding:
    """A single rationale-lint finding (SDC-150)."""

    sev: str
    code: str
    msg: str
    line: int = 0


def _strip_comment(line: str) -> str:
    """Return the comment text of a line (after the first '#'), stripped."""
    idx = line.find("#")
    if idx == -1:
        return ""
    return line[idx + 1:].strip()


def _is_substantive(comment: str) -> bool:
    """True when a comment carries real prose, not just a decorative fence."""
    if not comment:
        return False
    prose = comment.strip(_SEPARATOR_CHARS)
    return len(prose) >= MIN_COMMENT_CHARS


def _exception_keyword(line: str) -> Optional[str]:
    """Return the exception keyword the line starts with, or None."""
    stripped = line.strip()
    low = stripped.lower()
    for kw in _EXCEPTION_KEYWORDS:
        if low.startswith(kw):
            return kw
    return None


def rationale_findings(text: str) -> List[Finding]:
    """Scan ``text`` for exceptions lacking an explanatory comment.

    Returns one ``Finding`` (SDC-150, warning) per undocumented exception
    line. ``line`` is 1-based, matching the rest of the checker.
    """
    lines = text.splitlines()
    findings: List[Finding] = []

    for lineno, line in enumerate(lines, start=1):
        kw = _exception_keyword(line)
        if kw is None:
            continue

        # Inline comment on the same line — or on any backslash-continuation
        # line of a multiline command (e.g. trailing '  # async CDC' on the
        # last continuation line) — counts immediately.
        block_end = lineno
        probe = lineno - 1  # 0-based index of the keyword line
        while probe < len(lines) and lines[probe].rstrip().endswith("\\"):
            probe += 1
            block_end = probe + 1
        block_lines = lines[lineno - 1:block_end]
        if any(_is_substantive(_strip_comment(bl)) for bl in block_lines):
            continue

        # Comment block in the PROXIMITY_LINES lines directly above.
        start = max(0, lineno - 1 - PROXIMITY_LINES)
        nearby = lines[start:lineno - 1]
        if any(_is_substantive(_strip_comment(above)) for above in nearby):
            continue

        findings.append(Finding(
            sev="warning",
            code="SDC-150",
            msg=(
                f"set_{kw.replace('set_', '')} without an explanatory comment — "
                "an undocumented timing exception can hide a real violation. "
                "Add a comment above the line or inline (e.g. "
                "'# async CDC — two-flop synchronizer, no timing path')."
            ),
            line=lineno,
        ))

    return findings
