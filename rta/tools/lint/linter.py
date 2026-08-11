"""
SDC Linter — Format, reorganize, and clean up SDC constraint files.

Usage:
    from linter import lint_sdc
    result = lint_sdc(sdc_text)
    print(result.formatted_text)

CLI:
    sdc-tools lint input.sdc                    # formatted to stdout
    sdc-tools lint input.sdc --fix              # overwrite in-place
    sdc-tools lint input.sdc --output out.sdc   # write to file
    sdc-tools lint input.sdc --check            # exit 1 if not lint-clean
"""

import re
from dataclasses import dataclass, field
from typing import List, Tuple, Optional


# ── Section ordering ────────────────────────────────────────────────────────────

SECTION_ORDER = [
    "header",
    "sdc_version",
    "units",
    "clocks",
    "generated_clocks",
    "clock_attributes",
    "clock_groups",
    "io_constraints",
    "false_paths",
    "multicycle_paths",
    "max_min_delay",
    "case_analysis",
    "disable_timing",
    "design_rules",
    "operating_conditions",
    "timing_derate",
    "wire_load",
    "ideal_network",
    "power",
    "dft",
    "dont_use",
    "other",
]

# SDC command → category mapping
COMMAND_CATEGORY: dict[str, str] = {
    "set_sdc_version":        "sdc_version",
    "set_units":              "units",
    "create_clock":           "clocks",
    "create_generated_clock": "generated_clocks",
    "set_clock_latency":      "clock_attributes",
    "set_clock_transition":   "clock_attributes",
    "set_clock_uncertainty":  "clock_attributes",
    "set_clock_jitter":       "clock_attributes",
    "set_propagated_clock":   "clock_attributes",
    "set_clock_gating_check": "clock_attributes",
    "set_clock_groups":       "clock_groups",
    "set_input_delay":        "io_constraints",
    "set_output_delay":       "io_constraints",
    "set_driving_cell":       "io_constraints",
    "set_input_transition":   "io_constraints",
    "set_drive":              "io_constraints",
    "set_load":               "io_constraints",
    "set_false_path":         "false_paths",
    "set_multicycle_path":    "multicycle_paths",
    "set_max_delay":          "max_min_delay",
    "set_min_delay":          "max_min_delay",
    "set_case_analysis":      "case_analysis",
    "set_disable_timing":     "disable_timing",
    "set_max_fanout":         "design_rules",
    "set_max_transition":     "design_rules",
    "set_max_capacitance":    "design_rules",
    "set_min_capacitance":    "design_rules",
    "set_max_area":           "design_rules",
    "set_operating_conditions": "operating_conditions",
    "set_timing_derate":      "timing_derate",
    "set_wire_load_mode":     "wire_load",
    "set_wire_load_model":    "wire_load",
    "set_ideal_network":      "ideal_network",
    "set_max_dynamic_power":  "power",
    "set_max_leakage_power":  "power",
    "set_min_pulse_width":    "power",
    "set_dont_use":           "dont_use",
    "set_dont_touch":         "dont_use",
    "group_path":             "other",
    "set_voltage":            "other",
    "create_voltage_area":    "other",
}

SECTION_LABELS: dict[str, str] = {
    "sdc_version":        "SDC Version",
    "units":              "Units",
    "clocks":             "Clock Definitions",
    "generated_clocks":   "Generated Clock Definitions",
    "clock_attributes":   "Clock Attributes",
    "clock_groups":       "Clock Groups (CDC)",
    "io_constraints":     "I/O Constraints",
    "false_paths":        "False Paths",
    "multicycle_paths":   "Multicycle Paths",
    "max_min_delay":      "Max / Min Delay",
    "case_analysis":      "Case Analysis",
    "disable_timing":     "Disable Timing Arcs",
    "design_rules":       "Design Rule Constraints",
    "operating_conditions": "Operating Conditions",
    "timing_derate":      "Timing Derate (AOCV)",
    "wire_load":          "Wire Load Models",
    "ideal_network":      "Ideal Networks / Reset",
    "power":              "Power Constraints",
    "dft":                "DFT / Scan",
    "dont_use":           "Don't-Use / Don't-Touch Cells",
    "other":              "Other Constraints",
}

# Commands whose continuation lines start with whitespace
_MULTI_LINE_COMMANDS = {
    "set_false_path", "set_multicycle_path", "set_max_delay", "set_min_delay",
    "set_input_delay", "set_output_delay", "set_driving_cell",
    "set_load", "set_case_analysis", "set_disable_timing",
    "create_clock", "create_generated_clock", "set_clock_groups",
}


# ── Data classes ────────────────────────────────────────────────────────────────

@dataclass
class SdcLine:
    """A single line from an SDC file with its classification."""
    raw: str
    category: str = "other"
    is_comment: bool = False
    is_blank: bool = False
    is_section_header: bool = False
    is_continuation: bool = False
    command: str = ""


@dataclass
class LintResult:
    """Result of linting an SDC file."""
    original_text: str
    formatted_text: str = ""
    issues: List[str] = field(default_factory=list)
    line_count_original: int = 0
    line_count_formatted: int = 0
    warnings: int = 0
    fixed: int = 0


# ── Line parsing ────────────────────────────────────────────────────────────────

_COMMAND_RE = re.compile(r'^\s*(set\s+\w+|set_\w+|create_\w+|group_\w+)\b')

def _classify_line(raw: str) -> SdcLine:
    """Classify a single SDC line."""
    stripped = raw.strip()
    line = SdcLine(raw=raw)

    if not stripped:
        line.is_blank = True
        return line

    if stripped.startswith("#"):
        line.is_comment = True
        return line

    if stripped.startswith("\\") or raw.startswith("  ") or raw.startswith("\t"):
        line.is_continuation = True
        return line
    # Treat leading - as continuation only for indented arguments
    # (not standalone commands that start with a flag)
    if stripped.startswith("-") and raw.startswith("  "):
        line.is_continuation = True
        return line

    m = _COMMAND_RE.match(stripped)
    if m:
        cmd = m.group(1).replace(" ", "_")  # normalize "set sdc_version" → "set_sdc_version"
        line.command = cmd
        line.category = COMMAND_CATEGORY.get(cmd, "other")
    else:
        line.category = "other"

    return line


def _parse_lines(text: str) -> List[SdcLine]:
    """Parse all lines of an SDC file."""
    lines = []
    for raw in text.splitlines(keepends=False):
        line = _classify_line(raw)
        # Detect continuation lines (indented lines after multi-line commands)
        if line.is_continuation and lines:
            lines[-1].is_continuation = True
            # Actually: continuation means the PREVIOUS line continues
            # We want to group them together
        lines.append(line)
    return lines


# ── Formatting ──────────────────────────────────────────────────────────────────

def _categorize_lines(
    lines: List[SdcLine],
) -> Tuple[dict[str, List[SdcLine]], List[SdcLine]]:
    """Group lines by category. Returns (categories, leading_comments)."""
    categories: dict[str, List[SdcLine]] = {}
    leading_comments: List[SdcLine] = []
    in_leading = True

    for line in lines:
        if in_leading and (line.is_comment or line.is_blank):
            leading_comments.append(line)
            continue
        in_leading = False

        if line.is_comment or line.is_blank or line.is_continuation:
            continue

        cat = line.category
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(line)

        # Collect trailing comment that follows this command
        # (handled by joining approach below)

    return categories, leading_comments


def _assemble_formatted(
    categories: dict[str, List[SdcLine]],
    leading_comments: List[SdcLine],
    original_lines: List[str],
) -> str:
    """Assemble the formatted SDC text from categorized lines."""
    output: List[str] = []

    # Leading comments (existing header)
    for c in leading_comments:
        if c.raw.strip():
            output.append(c.raw)

    output.append("")
    output.append("# ═══════════════════════════════════════════════════════════════")
    output.append("#  SDC Lint — Reorganized Constraint File")
    output.append("# ═══════════════════════════════════════════════════════════════")
    output.append("")

    # Build index of original line content by looking up original text
    # We want to preserve original text for each command, including continuations
    original_by_cmd: dict[str, List[str]] = {}
    _command_start_re = re.compile(r'^\s*(set\s+\w+|set_\w+|create_\w+|group_\w+)\b')

    i = 0
    while i < len(original_lines):
        line_text = original_lines[i]
        stripped = line_text.strip()
        if not stripped or stripped.startswith("#"):
            i += 1
            continue
        m = _command_start_re.match(stripped)
        if m:
            cmd = m.group(1).replace(" ", "_")
            # Collect the full command including backslash continuations
            full_line = line_text.rstrip()
            i += 1
            while i < len(original_lines) and original_lines[i].rstrip().endswith("\\"):
                full_line += " " + original_lines[i].strip().lstrip("\\").strip()
                i += 1
            if cmd not in original_by_cmd:
                original_by_cmd[cmd] = []
            original_by_cmd[cmd].append(full_line)
        else:
            i += 1

    for section in SECTION_ORDER:
        lines_in_section = categories.get(section, [])
        if not lines_in_section:
            continue

        label = SECTION_LABELS.get(section, section.replace("_", " ").title())
        output.append("")
        output.append(f"# ── {label} {'─' * max(2, 50 - len(label))}")
        output.append("")

        for sdc_line in lines_in_section:
            cmd = sdc_line.command
            # Use original text if available
            if cmd in original_by_cmd and original_by_cmd[cmd]:
                orig = original_by_cmd[cmd].pop(0)
                output.append(orig)
            else:
                output.append(sdc_line.raw.rstrip())

    output.append("")
    return "\n".join(output)


def _count_issues(
    lines: List[str],
) -> Tuple[List[str], int]:
    """Check for common SDC issues and count warnings."""
    issues: List[str] = []
    warnings = 0

    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue

        # Check for trailing whitespace
        if line != line.rstrip():
            issues.append(f"Line {i}: Trailing whitespace")
            warnings += 1

        # Check for tabs
        if "\t" in line:
            issues.append(f"Line {i}: Contains tab character")
            warnings += 1

        # Check for long lines (>120 chars)
        if len(line) > 120:
            issues.append(f"Line {i}: Line too long ({len(line)} chars, max 120)")
            warnings += 1

    return issues, warnings


# ── Main lint function ──────────────────────────────────────────────────────────

def lint_sdc(text: str, fix: bool = True) -> LintResult:
    """Lint an SDC file: detect issues and optionally reformat.

    Args:
        text: Raw SDC text.
        fix: If True, generate formatted text. If False, only detect issues.

    Returns:
        LintResult with issues, warnings count, and optionally formatted text.
    """
    result = LintResult(original_text=text)
    lines = text.splitlines(keepends=False)
    result.line_count_original = len(lines)

    # Detect issues
    issues, warnings = _count_issues(lines)
    result.issues = issues
    result.warnings = warnings

    if fix:
        parsed = [_classify_line(l) for l in lines]
        categories, leading_comments = _categorize_lines(parsed)
        fmt = _assemble_formatted(categories, leading_comments, lines)
        result.formatted_text = fmt
        result.line_count_formatted = len(fmt.splitlines())

        # Count lines that changed
        orig_clean = [l.rstrip() for l in lines if l.strip() and not l.strip().startswith("#")]
        fmt_clean = [l.rstrip() for l in fmt.splitlines() if l.strip() and not l.strip().startswith("#")]
        if orig_clean != fmt_clean:
            result.fixed = 1  # at minimum, reorganized

    return result


def lint_sdc_file(filepath: str, fix: bool = True, output_path: Optional[str] = None) -> LintResult:
    """Lint an SDC file on disk. Optionally write formatted output."""
    with open(filepath, "r", encoding="utf-8") as f:
        text = f.read()

    result = lint_sdc(text, fix=fix)

    if fix and result.formatted_text:
        out = output_path or filepath
        with open(out, "w", encoding="utf-8") as f:
            f.write(result.formatted_text)

    return result
