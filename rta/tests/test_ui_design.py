"""
UI design-layer regression tests (Phase 15 vertical slice).

These protect the PREMIUM UI components without touching the deterministic
backend. They assert:
  - Phase 14 stored-XSS rule: every user-controlled value rendered through
    custom HTML helpers is escaped.
  - The universal status system covers every backend status string with an
    icon + label (never color-only).
  - Design tokens are internally consistent (colors resolve, fonts defined).
  - Findings/source helpers never crash on adversarial input.
"""

import html as _html

import pytest

from ui import theme
from ui.components import status_badge_html, empty_state_html
from ui.validator import (
    _finding_object, _finding_clock, _requires_sta, _loc, findings_table_html,
    source_excerpt_html, full_source_viewer_html, finding_detail_html,
)

EVIL = "<script>alert(1)</script> & \"quoted\" 'single'"


# ═══════════════════════════════════════════════════════════════════════════
# HTML escaping (Phase 14 stored-XSS rule — must not regress)
# ═══════════════════════════════════════════════════════════════════════════

class _Issue:
    def __init__(self, sev="error", code="SDC-X", msg="", line=0, line2=0, identity=None):
        self.sev = sev
        self.code = code
        self.msg = msg
        self.line = line
        self.line2 = line2
        self.identity = identity


def test_esc_basic():
    assert theme.esc("<script>") == "&lt;script&gt;"
    assert theme.esc('a & "b"') == "a &amp; &quot;b&quot;"
    assert theme.esc(None) == ""
    assert theme.esc(42) == "42"


def test_status_badge_escapes_label():
    html = status_badge_html("severity", "error")
    assert "<script>" not in html
    assert html.startswith('<span class="sdc-status')


def test_status_badge_unknown_status_falls_back_safely():
    # An unrecognized status must render a neutral badge, not a raw string.
    html = status_badge_html("readiness", EVIL)
    assert "<script>" not in html
    assert "alert" not in html


def test_empty_state_escapes_all_text():
    html = empty_state_html(EVIL, EVIL, EVIL)
    assert "<script>" not in html
    assert "&lt;script&gt;" in html


def test_findings_table_escapes_messages_and_identities():
    issue = _Issue(sev="error", code=EVIL, msg=EVIL, line=7,
                   identity={"primary_object": EVIL, "clock": EVIL})
    html = findings_table_html([issue])
    assert "<script>" not in html
    assert "&lt;script&gt;" in html
    assert "&quot;" in html


def test_source_viewers_escape_lines():
    lines = [EVIL, "create_clock -name clk -period 5.0 [get_ports clk]"]
    for html in (source_excerpt_html(lines, _Issue(line=1)),
                 full_source_viewer_html(lines, {1: "hl"})):
        assert "<script>" not in html
        assert "&lt;script&gt;" in html


def test_finding_detail_escapes_and_sta_marker():
    issue = _Issue(sev="warning", code="SDC-070", msg=EVIL, line=3, line2=9,
                   identity={"primary_object": EVIL, "clock": EVIL,
                             "interaction_type": "overlap"})
    html = finding_detail_html(issue, None)
    assert "<script>" not in html
    assert "REQUIRES STA" in html


# ═══════════════════════════════════════════════════════════════════════════
# Status system coverage (icon + label for every backend status)
# ═══════════════════════════════════════════════════════════════════════════

def test_severity_statuses_covered():
    for sev in ("fatal", "error", "warning", "info"):
        assert sev in theme.SEVERITY
        meta = theme.SEVERITY[sev]
        assert meta["icon"] in theme.ICONS
        assert meta["label"]


def test_trust_statuses_covered():
    for st in ("VALIDATED", "PARTIALLY_VALIDATED", "NETLIST_REQUIRED",
               "TCL_EXECUTION_REQUIRED", "UNSUPPORTED", "NOT_VALIDATED"):
        assert st in theme.TRUST, f"trust status {st} missing from token map"
        assert theme.TRUST[st]["icon"] in theme.ICONS
        assert theme.TRUST[st]["label"]


def test_readiness_statuses_covered():
    for st in ("READY", "READY_WITH_ADVISORIES", "REVIEW_REQUIRED", "BLOCKED",
               "INSUFFICIENT_CONTEXT"):
        assert st in theme.READINESS
        assert theme.READINESS[st]["icon"] in theme.ICONS


def test_diff_statuses_covered():
    for st in ("NEW", "RESOLVED", "CHANGED", "UNCHANGED"):
        assert st in theme.DIFF
        assert theme.DIFF[st]["icon"] in theme.ICONS


def test_all_icon_names_resolve():
    for meta in list(theme.SEVERITY.values()) + list(theme.TRUST.values()) \
            + list(theme.READINESS.values()) + list(theme.DIFF.values()):
        assert meta["icon"] in theme.ICONS, f"missing icon {meta['icon']}"


# ═══════════════════════════════════════════════════════════════════════════
# Token consistency
# ═══════════════════════════════════════════════════════════════════════════

def test_tokens_are_valid_hex_colors():
    for name, value in theme.COLORS.items():
        assert value.startswith("#") and len(value) in (7, 9), f"{name}={value}"
        int(value[1:], 16)  # must parse


def test_font_tokens_defined():
    assert "Inter" in theme.FONT_UI
    assert "JetBrains Mono" in theme.FONT_MONO


def test_spacing_and_radius_scales():
    assert theme.SPACING["1"] == 4
    assert theme.RADIUS["sm"] == 4
    assert theme.RADIUS["lg"] == 12


# ═══════════════════════════════════════════════════════════════════════════
# Validator helpers behave on adversarial inputs
# ═══════════════════════════════════════════════════════════════════════════

def test_identity_helpers_defensive():
    assert _finding_object(_Issue()) == ""
    assert _finding_clock(_Issue()) == ""
    assert _loc(_Issue()) == ""
    # Non-dict identity must not crash
    assert _finding_object(_Issue(identity="junk")) == ""
    assert _finding_object(_Issue(identity={"primary_object": "din"})) == "din"
    assert _loc(_Issue(line=4, line2=9)) == "L4 ↔ L9"


def test_requires_sta_only_from_evidence():
    assert _requires_sta(_Issue(code="SDC-070")) is True
    assert _requires_sta(_Issue(code="SDC-008")) is False
    assert _requires_sta(_Issue(code="SDC-069",
                               identity={"interaction_type": "contradiction"})) is False
    assert _requires_sta(_Issue(code="SDC-069",
                               identity={"interaction_type": "overlap_sta_review"})) is True


def test_findings_table_empty():
    assert findings_table_html([]) == ""


def test_source_excerpt_no_lines():
    assert source_excerpt_html(["a", "b"], _Issue(line=0, line2=0)) == ""
    assert source_excerpt_html([], _Issue(line=1)) == ""
