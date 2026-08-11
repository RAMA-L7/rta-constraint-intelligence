"""
Ṛta — Design tokens (single source of truth).

Implements the approved token system from docs/product/VISUAL_DESIGN_SYSTEM.md
(Aracade-docs light direction: achromatic hairline surfaces, near-black text,
restrained accent; semantic status colors from the Arcade syntax palette).

This module is UI-only. It must never be imported by the deterministic
backend modules (checker, readiness_diff, ...) and never affects validation
results. All values are presentation tokens.
"""

from __future__ import annotations

import html as _html

# ═══════════════════════════════════════════════════════════════════════════
# COLOR TOKENS (Arcade-docs light — achromatic hairline surfaces, restrained
# accent; semantic status colors taken from the Arcade docs syntax palette:
# success #2F6E4E · error #A8453A · warning #8A6C14 · info #2563EB).
# ═══════════════════════════════════════════════════════════════════════════

COLORS = {
    "background_primary":   "#FFFFFF",
    "background_secondary": "#F6F6F6",
    "surface":              "#FFFFFF",
    "surface_elevated":     "#FFFFFF",
    "surface_overlay":      "#FFFFFF",
    "border_subtle":        "#EAEAEA",
    "border_active":        "#D4D4D4",
    "text_primary":         "#18181B",
    "text_secondary":       "#3F3F46",
    "text_muted":           "#71717A",
    "accent_primary":       "#111111",
    "accent_secondary":     "#2563EB",
    "success":              "#2F6E4E",
    "warning":              "#8A6C14",
    "error":                "#A8453A",
    "info":                 "#2563EB",
    "unknown":              "#71717A",
    "not_applicable":       "#9CA3AF",
    "focus":                "#2563EB",
    "diff_new":             "#2F6E4E",
    "diff_resolved":        "#2563EB",
    "diff_changed":         "#8A6C14",
    "diff_unchanged":       "#9CA3AF",
    "code_bg":              "#F6F6F6",
    "code_gutter":          "#9CA3AF",
}

# ═══════════════════════════════════════════════════════════════════════════
# TYPOGRAPHY / SPACING / RADIUS / MOTION TOKENS
# ═══════════════════════════════════════════════════════════════════════════

FONT_UI = "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif"
FONT_MONO = "'JetBrains Mono', 'Fira Code', 'Cascadia Code', Consolas, monospace"

SPACING = {"1": 4, "2": 8, "3": 12, "4": 16, "5": 20, "6": 24, "8": 32,
           "10": 40, "12": 48, "16": 64, "24": 96, "32": 128}

RADIUS = {"sm": 4, "md": 8, "lg": 12, "full": 999}

MOTION = {"micro": "150ms", "nav": "220ms", "data": "300ms"}

# ═══════════════════════════════════════════════════════════════════════════
# STATUS METADATA — icon + label + color + shape (never color alone)
# ═══════════════════════════════════════════════════════════════════════════

SEVERITY = {
    "fatal":   {"label": "FATAL",   "icon": "fatal",   "color": "error",  "shape": "octagon"},
    "error":   {"label": "ERROR",   "icon": "error",   "color": "error",  "shape": "octagon"},
    "warning": {"label": "WARNING", "icon": "warning", "color": "warning", "shape": "triangle"},
    "info":    {"label": "INFO",    "icon": "info",    "color": "info",   "shape": "circle"},
}

TRUST = {
    "VALIDATED":              {"label": "VALIDATED",              "icon": "node",    "color": "success", "shape": "square-filled"},
    "PARTIALLY_VALIDATED":    {"label": "PARTIAL",                "icon": "node-half", "color": "warning", "shape": "square-half"},
    "NETLIST_REQUIRED":       {"label": "NETLIST",                "icon": "netlist", "color": "info",    "shape": "square-net"},
    "TCL_EXECUTION_REQUIRED": {"label": "TCL EXEC",               "icon": "tcl",     "color": "unknown", "shape": "square-term"},
    "UNSUPPORTED":            {"label": "UNSUPPORTED",            "icon": "ban",     "color": "error",   "shape": "slash-circle"},
    "NOT_VALIDATED":          {"label": "NOT CHECKED",            "icon": "node-hollow", "color": "unknown", "shape": "square-hollow"},
}

READINESS = {
    "READY":                  {"label": "READY",                  "icon": "shield-check", "color": "success", "shape": "shield"},
    "READY_WITH_ADVISORIES":  {"label": "READY+",                 "icon": "shield-dot",   "color": "success", "shape": "shield-dot"},
    "REVIEW_REQUIRED":        {"label": "REVIEW",                 "icon": "warning",      "color": "warning", "shape": "triangle"},
    "BLOCKED":                {"label": "BLOCKED",                "icon": "error",        "color": "error",   "shape": "octagon"},
    "INSUFFICIENT_CONTEXT":   {"label": "LIMITED",                "icon": "shield-question", "color": "unknown", "shape": "shield-hollow"},
    "NOT_APPLICABLE":         {"label": "N/A",                    "icon": "na",           "color": "not_applicable", "shape": "square-hollow"},
}

DIFF = {
    "NEW":       {"label": "NEW",       "icon": "diff-new",       "color": "diff_new",       "shape": "plus-diamond"},
    "RESOLVED":  {"label": "RESOLVED",  "icon": "diff-resolved",  "color": "diff_resolved",  "shape": "check-circle"},
    "CHANGED":   {"label": "CHANGED",   "icon": "diff-changed",   "color": "diff_changed",   "shape": "swap"},
    "UNCHANGED": {"label": "UNCHANGED", "icon": "diff-unchanged", "color": "diff_unchanged", "shape": "equals"},
}

PASS_FAIL = {
    "PASS": {"label": "PASS", "icon": "check", "color": "success", "shape": "circle-check"},
    "FAIL": {"label": "FAIL", "icon": "error", "color": "error",   "shape": "octagon"},
}

# ═══════════════════════════════════════════════════════════════════════════
# ICONS — inline SVG (stroke-based, 16px grid, 1.5px stroke)
# ═══════════════════════════════════════════════════════════════════════════

def _icon(inner: str) -> str:
    return (
        f'<svg class="sdc-icon" width="14" height="14" viewBox="0 0 16 16" '
        f'fill="none" stroke="currentColor" stroke-width="1.5" '
        f'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">{inner}</svg>'
    )

ICONS = {
    "error": _icon('<path d="M8 1.5 14.5 8 8 14.5 1.5 8Z"/><path d="m6 6 4 4M10 6l-4 4"/>'),
    "fatal": _icon('<path d="M8 1 14.5 8 8 15 1.5 8Z"/><path d="M8 4.5 11.5 8 8 11.5 4.5 8Z"/><path d="m6.6 6.6 2.8 2.8M9.4 6.6l-2.8 2.8"/>'),
    "warning": _icon('<path d="M8 2 14.5 13H1.5Z"/><path d="M8 6.5v3.2"/><path d="M8 11.4v.1"/>'),
    "info": _icon('<circle cx="8" cy="8" r="6.2"/><path d="M8 7.2v3.8"/><path d="M8 5.1v.1"/>'),
    "check": _icon('<circle cx="8" cy="8" r="6.2"/><path d="m5.2 8.2 1.9 1.9 3.7-4"/>'),
    "ban": _icon('<circle cx="8" cy="8" r="6.2"/><path d="m4.5 4.5 7 7"/>'),
    "unknown": _icon('<circle cx="8" cy="8" r="6.2"/><path d="M6.2 6.4a2 2 0 1 1 3 1.9c-.7.4-1.2.8-1.2 1.7"/><path d="M8 11.9v.1"/>'),
    "na": _icon('<rect x="2.8" y="2.8" width="10.4" height="10.4" rx="1.5"/><path d="M5.5 8h5"/>'),
    "node": _icon('<rect x="3.5" y="3.5" width="9" height="9" rx="1"/><path d="M8 1v2.5M8 12.5V15M1 8h2.5M12.5 8H15"/>'),
    "node-half": _icon('<path d="M3.5 3.5h9v9h-9Z"/><path d="M8 3.5v9"/><path d="M8 1v2.5M8 12.5V15M1 8h2.5M12.5 8H15"/>'),
    "node-hollow": _icon('<rect x="3.5" y="3.5" width="9" height="9" rx="1"/>'),
    "netlist": _icon('<rect x="3.5" y="3.5" width="9" height="9" rx="1"/><path d="m8 6 2.2 2-2.2 2M5.8 6l-2.2 2 2.2 2"/>'),
    "tcl": _icon('<rect x="2.6" y="3.2" width="10.8" height="9.6" rx="1.2"/><path d="m5.4 6.2 2.6 1.8-2.6 1.8M9 9.8h1.8"/>'),
    "shield-check": _icon('<path d="M8 1.6 13 3.6v4.3c0 3.2-2 5.5-5 6.5-3-1-5-3.3-5-6.5V3.6Z"/><path d="m5.8 8 1.6 1.6 3-3.2"/>'),
    "shield-dot": _icon('<path d="M8 1.6 13 3.6v4.3c0 3.2-2 5.5-5 6.5-3-1-5-3.3-5-6.5V3.6Z"/><path d="M8 7.2v.1"/>'),
    "shield-question": _icon('<path d="M8 1.6 13 3.6v4.3c0 3.2-2 5.5-5 6.5-3-1-5-3.3-5-6.5V3.6Z"/><path d="M6.4 6.3a1.7 1.7 0 1 1 2.6 1.5c-.7.4-1 .9-1 1.5"/><path d="M8 11v.1"/>'),
    "clock": _icon('<circle cx="8" cy="8" r="6"/><path d="M8 4.4V8l2.4 1.6"/>'),
    "node-link": _icon('<rect x="1.8" y="6" width="4" height="4" rx=".8"/><rect x="10.2" y="6" width="4" height="4" rx=".8"/><path d="M5.8 8h4.4"/>'),
    "bus": _icon('<path d="M1 4h14M1 8h14M1 12h14"/>'),
    "diff-new": _icon('<path d="M8 1.8 14.2 8 8 14.2 1.8 8Z"/><path d="M8 5.5v5M5.5 8h5"/>'),
    "diff-resolved": _icon('<circle cx="8" cy="8" r="6.2"/><path d="m5.2 8.2 1.9 1.9 3.7-4"/>'),
    "diff-changed": _icon('<path d="M3 5h7.5a2.5 2.5 0 0 1 0 5H6M6 8 3 5l3-3"/>'),
    "diff-unchanged": _icon('<path d="M5 8h6"/>'),
    "search": _icon('<circle cx="7" cy="7" r="4.4"/><path d="m10.4 10.4 3 3"/>'),
    "filter": _icon('<path d="M2 4h12M4.8 8h6.4M7 12h2"/>'),
    "run": _icon('<path d="M5 3.5v9l7-4.5Z"/>'),
    "copy": _icon('<rect x="5.4" y="5.4" width="8" height="8" rx="1.2"/><path d="M10.6 3H3.6A1.6 1.6 0 0 0 2 4.6v7"/>'),
    "chevron": _icon('<path d="m6 4 4 4-4 4"/>'),
    "line": _icon('<path d="M3 13 13 3"/>'),
    "bracket": _icon('<path d="M5 2.5H3.8A1.3 1.3 0 0 0 2.5 3.8v2.9A1.3 1.3 0 0 1 1.2 8a1.3 1.3 0 0 1 1.3 1.3v2.9a1.3 1.3 0 0 0 1.3 1.3H5M11 2.5h1.2a1.3 1.3 0 0 1 1.3 1.3v2.9a1.3 1.3 0 0 0 1.3 1.3 1.3 1.3 0 0 0-1.3 1.3v2.9a1.3 1.3 0 0 1-1.3 1.3H11"/>'),
    "overview": _icon('<rect x="2.2" y="2.2" width="4.4" height="4.4" rx=".8"/><rect x="9.4" y="2.2" width="4.4" height="4.4" rx=".8"/><rect x="2.2" y="9.4" width="4.4" height="4.4" rx=".8"/><rect x="9.4" y="9.4" width="4.4" height="4.4" rx=".8"/>'),
    "validator": _icon('<path d="M8 1.6 13 3.6v4.3c0 3.2-2 5.5-5 6.5-3-1-5-3.3-5-6.5V3.6Z"/><path d="m5.8 8 1.6 1.6 3-3.2"/>'),
    "context": _icon('<path d="M8 1.5v4M8 5.5 5 9M8 5.5 11 9M8 9v2.5M5 9v2.5M11 9v2.5"/><circle cx="8" cy="14" r="1"/><circle cx="5" cy="13.5" r="1"/><circle cx="11" cy="13.5" r="1"/>'),
    "readiness": _icon('<path d="M2.5 13V9M6.5 13V5.5M10.5 13V3M14.5 13V7"/>'),
    "diff": _icon('<path d="M2.5 4h8M8.5 4 6 1.5M8.5 4 6 6.5"/><path d="M13.5 12h-8M7.5 12 10 9.5M7.5 12 10 14.5"/>'),
    "reports": _icon('<path d="M4 2.5h5.5L13 6v7.5H4Z"/><path d="M9.5 2.5V6H13M6 9.5h4M6 11.5h4"/>'),
    "ci": _icon('<path d="M1.5 6h4v4h4v4h5"/><path d="m1.5 6 2-2 2 2M14.5 14l-2 2-2-2"/>'),
    "generator": _icon('<circle cx="8" cy="8" r="2.4"/><path d="M8 1.8v2M8 12.2v2M1.8 8h2M12.2 8h2M3.6 3.6l1.4 1.4M11 11l1.4 1.4M12.4 3.6 11 5M5 11l-1.4 1.4"/>'),
    "linter": _icon('<path d="M3 13h10"/><path d="M4.5 13 3 9.5V8h3v1.5Z"/><path d="M6 8V6.5h1.2V5M7.2 5h1.6v1.5M8.8 6.5h1.2V8"/><path d="M10 8h3v1.5l-1.5 3.5"/>'),
    "converter": _icon('<path d="M4 3h6a3 3 0 0 1 0 6H6a3 3 0 0 0 0 6h6"/><path d="m12 1.5 2 1.5-2 1.5M4 11.5l-2 1.5 2 1.5"/>'),
    "corners": _icon('<rect x="2.5" y="2.5" width="4.5" height="4.5" rx=".8"/><rect x="9" y="2.5" width="4.5" height="4.5" rx=".8"/><rect x="2.5" y="9" width="4.5" height="4.5" rx=".8"/><rect x="9" y="9" width="4.5" height="4.5" rx=".8"/>'),
    "mmc": _icon('<path d="m8 2 6 3-6 3-6-3Z"/><path d="m2 8 6 3 6-3"/><path d="m2 11.5 6 3 6-3"/>'),
    "rules": _icon('<path d="M3 2.5h7a2 2 0 0 1 2 2v9H5a2 2 0 0 1-2-2Z"/><path d="M12 11.5h1.5v-7a2 2 0 0 0-2-2H6"/>'),
    "test_drive": _icon('<circle cx="8" cy="8" r="6.2"/><path d="M6.4 5.2v5.6l4.8-2.8Z"/>'),
    "feedback": _icon('<path d="M8 2.2c3.4 0 6 2.4 6 5.3S11.4 12.8 8 12.8c-.8 0-1.6-.1-2.3-.4L3 13.5l.8-2.4C2.7 10 2 8.8 2 7.5c0-2.9 2.6-5.3 6-5.3Z"/><path d="M6 7.5h.1M9 7.5h.1M12 7.5h.1"/>'),
    "close": _icon('<path d="m4.5 4.5 7 7M11.5 4.5l-7 7"/>'),
    "external": _icon('<path d="M6 3H3.5v9.5H13V11"/><path d="M9.5 3H13v3.5M13 3l-6 6"/>'),
    "download": _icon('<path d="M8 2.5v7M5.2 7 8 9.8 10.8 7"/><path d="M2.5 11v2.5h11V11"/>'),
    "tree": _icon('<path d="M8 1.5V6M8 6 5.5 9M8 6l2.5 3M5.5 9v3.5M10.5 9v3.5M8 6v3.5"/><path d="M4.5 12.5h2M9.5 12.5h2M4.5 14.5h2M9.5 14.5h2"/>'),
    "gauge": _icon('<path d="M2.5 11.5a6 6 0 1 1 11 0"/><path d="M8 11.5 10.8 8.4"/>'),
    "pipeline": _icon('<rect x="2" y="3" width="3.2" height="3.2" rx=".7"/><rect x="10.8" y="9.8" width="3.2" height="3.2" rx=".7"/><path d="M5.2 4.6h3a2 2 0 0 1 2 2v3"/>'),
    "layers": _icon('<path d="m8 2 6 3-6 3-6-3Z"/><path d="m2 8 6 3 6-3"/>'),
    "book": _icon('<path d="M3 2.5h7a2 2 0 0 1 2 2v9H5a2 2 0 0 1-2-2Z"/><path d="M12 11.5h1.5v-7a2 2 0 0 0-2-2H6"/>'),
    "chat": _icon('<path d="M8 2.2c3.4 0 6 2.4 6 5.3S11.4 12.8 8 12.8c-.8 0-1.6-.1-2.3-.4L3 13.5l.8-2.4C2.7 10 2 8.8 2 7.5c0-2.9 2.6-5.3 6-5.3Z"/>'),
    "gear": _icon('<circle cx="8" cy="8" r="2.4"/><path d="M8 1.8v2M8 12.2v2M1.8 8h2M12.2 8h2M3.6 3.6l1.4 1.4M11 11l1.4 1.4M12.4 3.6 11 5M5 11l-1.4 1.4"/>'),
    "wrench": _icon('<path d="M13.5 4.2a3.6 3.6 0 0 1-4.7 4.4L4.4 13a1.5 1.5 0 0 1-2.1-2.1l4.4-4.4a3.6 3.6 0 0 1 4.4-4.7L8.6 3.8l1 1.6 1.6 1 2.3-2.2Z"/>'),
    "swap": _icon('<path d="M4 5h7.5a2.5 2.5 0 0 1 0 5H6M6 8 3 5l3-3"/>'),
    "grid": _icon('<path d="M3 3h3.2v3.2H3Z"/><path d="M9.8 3H13v3.2H9.8Z"/><path d="M3 9.8h3.2V13H3Z"/><path d="M9.8 9.8H13V13H9.8Z"/>'),
}


def icon(name: str) -> str:
    """Return the inline SVG for ``name`` (safe, static — no user input)."""
    return ICONS.get(name, ICONS["info"])


# ═══════════════════════════════════════════════════════════════════════════
# ESCAPING — Phase 14 stored-XSS rule: EVERY user-controlled value that is
# interpolated into custom HTML must pass through esc().
# ═══════════════════════════════════════════════════════════════════════════

def esc(value) -> str:
    """HTML-escape arbitrary user-controlled content for safe interpolation."""
    if value is None:
        return ""
    return _html.escape(str(value), quote=True)
