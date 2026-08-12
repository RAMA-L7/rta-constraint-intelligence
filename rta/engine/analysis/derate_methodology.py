"""
AOCV/POCV-aware derate methodology (F4, SDC-156/157).

Answers: *is the derate methodology consistent with the node/flow the file
itself signals?*

The existing derate rules (SDC-032/033/040-043/054) validate VALUES —
direction, ordering, monotonicity — but never the METHODOLOGY. A derate
strategy that was correct for an older node silently persists after a flow
migrates to a smaller one: reintroducing excess pessimism (wasted area/power
on phantom violations) or insufficient margin (real risk missed). This module
adds the methodology axis on top of those value-sanity checks.

INFO-LEVEL ONLY
===============
Both rules are ``info``, never warning/error: a flat derate is *correct* for
many blocks, and the project's no-overclaim ethos forbids alarm fatigue on
an advisory signal. Approved as info in the feature-plan decision gate
(pending domain-engineer confirmation before any warning upgrade).

Rules (advisory, provable-only)
===============================
``SDC-156`` — Flat derate on advanced-node flow
    The file itself signals an advanced (<=16nm) methodology — a small-node
    token in a ``set_operating_conditions`` command (e.g. ``SS_0P72V_16C``),
    an explicit ``Nnm`` mention, or a POCV/AOCV keyword — yet all derates are
    flat single-number ``set_timing_derate`` values.

``SDC-157`` — Derate methodology mix
    Flat derates coexist with sigma/table-based derates (an SDC command
    carrying ``sigma`` / ``pocv`` / ``derate_table``) in one file — an
    inconsistency flag; the two methodologies are not meant to be mixed.

Provable-only, no node-size magic: a condition like ``SS_0P8V_25C`` (25 is a
temperature) never matches a node hint, nor does ``SSG_0P7V_125C`` (0.7V /
125C). Only standalone small-node tokens (3/5/7/16 at word boundaries) or
explicit ``Nnm`` suffixes count.
"""

import re
from dataclasses import dataclass
from typing import List

from sdc_preprocess import preprocess_sdc


#: Numbers that read as small process nodes ONLY when they appear as
#: standalone word-boundary tokens — never inside a temperature (25C, 125C,
#: 85C) or a voltage fraction (0P72V, 0P7V).
_NODE_NUMBER_ALT = "|".join(("16", "7", "5", "3"))

#: Node token inside an operating-condition name or comment: word-boundary
#: guarded on both sides, optional nm-style suffix, never followed by a digit
#: (so '25C'/'125C' cannot match '5'/'3').
_NODE_TOKEN_RE = re.compile(
    # Boundary guard: only digits/letters block a match — underscore is a
    # legitimate separator in condition names (SS_0P72V_16C), so '_' must NOT
    # block. '25C'/'125C'/'0P7V' cannot match because the digit/letter before
    # the node number blocks it.
    r"(?<![0-9A-Za-z])(?:" + _NODE_NUMBER_ALT + r")(?:nm|nmc|nmc_)?(?![0-9])",
    re.IGNORECASE,
)

#: Explicit ``Nnm`` mention anywhere in the text (e.g. a header comment
#: '# 5nm POCV flow').
_NM_SUFFIX_RE = re.compile(
    r"(?<![0-9])(?:" + _NODE_NUMBER_ALT + r")nm(?![0-9])", re.IGNORECASE)

#: POCV/AOCV methodology keywords — in condition names, comments, or command
#: options (``-pocv``, ``-sigma``, ``derate_table``, ``set_pocv_derate`` ...).
#: Boundary = letter/digit only, so underscore is a SEPARATOR: matches
#: ``CUSTOM_POCV_CORNER`` and ``set_pocv_derate`` but not ``nonsigma``.
_ADVANCED_KEYWORD_RE = re.compile(
    r"(?<![0-9A-Za-z])(?:pocv|aocv|sigma|derate_table)(?![0-9A-Za-z])",
    re.IGNORECASE)

#: Advanced-DERATE command classification (SDC-157): the keyword must sit in
#: an OPTION (``-sigma``, ``-pocv``, ``-derate_table``) or a command NAME
#: (``set_pocv_derate``, ``set_aocv_derate``, a bare ``derate_table`` token).
#: Deliberately NOT a whole-command scan: an object reference like
#: ``[get_pins sigma_ctrl]`` is a signal name, not a derate methodology —
#: counting it would fire SDC-157 on designs with no methodology problem.
_ADVANCED_DERATE_RE = re.compile(
    r"-(?:sigma|pocv|derate_table)\b"
    r"|set_\w*(?:pocv|aocv|sigma|derate_table)\w*"
    r"|\bderate_table\b",
    re.IGNORECASE)


@dataclass
class Finding:
    """A single derate-methodology finding (SDC-156/157)."""

    sev: str
    code: str
    msg: str
    line: int = 0


def _find_line(text: str, needle: str) -> int:
    """1-based line of the first occurrence of ``needle`` (0 if absent)."""
    idx = text.find(needle)
    if idx == -1:
        return 0
    return text[:idx].count("\n") + 1


def derate_methodology_findings(text: str) -> List[Finding]:
    """Scan an SDC for derate-methodology inconsistency (SDC-156/157).

    Pure SDC-only analysis — needs neither a netlist nor a clock model.
    Returns info-level ``Finding`` objects; both rules are advisory by
    approved decision and never fire on value-sanity grounds (those stay
    with SDC-032/033/040-043/054).
    """
    commands = [c.text for c in preprocess_sdc(text)]

    # Flat derates: set_timing_derate commands with no sigma/pocv/table form.
    flat_derates = [
        cmd for cmd in commands
        if cmd.lstrip().lower().startswith("set_timing_derate")
        and not _ADVANCED_KEYWORD_RE.search(cmd)
    ]
    # Advanced derates: actual SDC commands carrying a sigma/table/pocv form
    # (e.g. set_pocv_derate ..., set_timing_derate ... -sigma ..., a
    # derate_table command). An operating-condition command is NOT a derate
    # command even when its name mentions POCV.
    advanced_derates = [
        cmd for cmd in commands
        if _ADVANCED_DERATE_RE.search(cmd)
        and not cmd.lstrip().lower().startswith("set_operating_conditions")
    ]

    findings: List[Finding] = []

    def _line_fragment(cmd: str) -> str:
        ln = _find_line(text, cmd)
        return f" (line {ln})" if ln else ""

    # SDC-157 — flat + sigma/table derates mixed in one file.
    if flat_derates and advanced_derates:
        first = advanced_derates[0]
        findings.append(Finding(
            "info", "SDC-157",
            f"Derate methodology mix: flat set_timing_derate values sit "
            f"alongside sigma/table-based derates{_line_fragment(first)} in one "
            f"file. Flat and statistical/table derates are not meant to be "
            f"mixed — pick one methodology for the corner.",
            line=_find_line(text, first),
        ))

    # SDC-156 — advanced-node flow signals but flat-only derates. Requires a
    # genuine node/methodology signal AND flat derates AND no advanced derate
    # commands (an actual advanced command makes it the SDC-157 mix instead).
    if flat_derates and not advanced_derates:
        condition_cmds = [
            cmd for cmd in commands
            if cmd.lstrip().lower().startswith("set_operating_conditions")
        ]
        node_in_condition = any(
            _NODE_TOKEN_RE.search(cmd) for cmd in condition_cmds)
        node_hint = (
            node_in_condition
            # POCV/AOCV/sigma keyword inside a NAMED operating-condition
            # command (e.g. SS_0P72V_16C_POCV). Deliberately NOT a whole-text
            # scan: section-header comments like '# Timing Derate (AOCV)' are
            # documentation, not a methodology claim (corpus-proven noise).
            or any(_ADVANCED_KEYWORD_RE.search(cmd) for cmd in condition_cmds)
            or bool(_NM_SUFFIX_RE.search(text))
        )
        if node_hint:
            first = flat_derates[0]
            evidence = ("small-node operating condition" if node_in_condition
                        else "small-node keyword (nm suffix or POCV/AOCV/sigma "
                             "mention)")
            findings.append(Finding(
                "info", "SDC-156",
                f"Flat-only derate on an advanced-node flow: {evidence} signals "
                f"a small-node methodology (detectable advanced set: 3/5/7/16nm), "
                f"but only flat set_timing_derate values are used"
                f"{_line_fragment(first)}. Consider table-based AOCV or "
                f"sigma-based POCV derates — flat values at small nodes "
                f"reintroduce excess pessimism or insufficient margin.",
                line=_find_line(text, first),
            ))

    return findings
