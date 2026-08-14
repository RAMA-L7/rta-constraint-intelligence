"""
SDC Constraint Checker
Validates SDC files and reports errors, warnings, and best-practice suggestions.
"""

import re
from dataclasses import dataclass, field
from typing import List, Dict

from sdc_preprocess import (
    preprocess_sdc, find_line, parse_collection,
    extract_flag_numbers, NUM_PATTERN,
)
from support_boundary import analyze_scope


@dataclass
class Issue:
    sev: str       # "error" | "warning"
    code: str
    msg: str
    line: int = 0  # line number in source (0 = unknown)
    line2: int = 0  # optional second source line for conflict findings (0 = n/a)
    # Phase 13: optional structured identity (message-independent semantic
    # fields) attached where the generating engine has richer data than the
    # message (constraint interactions, design-aware resolution). When absent,
    # snapshot builders derive identity from the SDC command text at the
    # finding's line — never from the human-readable message.
    identity: dict = None


@dataclass
class InfoItem:
    code: str
    msg: str
    line: int = 0  # line number in source (0 = unknown); P1-1: populated where the
                   # item maps to a concrete SDC command


@dataclass
class CheckResult:
    issues: List[Issue] = field(default_factory=list)
    info: List[InfoItem] = field(default_factory=list)
    stats: Dict[str, int] = field(default_factory=dict)
    scope: dict = field(default_factory=dict)  # analysis coverage / trust status (Phase 7)
    coverage: dict = field(default_factory=dict)  # design constraint coverage (Phase 9)
    interactions: dict = field(default_factory=dict)  # semantic constraint interactions (Phase 10)
    readiness: dict = field(default_factory=dict)  # constraint readiness review (Phase 11)
    # Phase 13: normalized logical commands retained so snapshot builders can
    # derive STRUCTURED finding identity from the SDC command text (never from
    # the human-readable message). Provenance-only; not serialized.
    logical: list = field(default_factory=list)

    @property
    def errors(self):
        return [i for i in self.issues if i.sev == "error"]

    @property
    def warnings(self):
        return [i for i in self.issues if i.sev == "warning"]


KNOWN_COMMON_COND = {"WORST", "BEST", "TYP", "TYPICAL", "SSG", "TT", "FFG", "SS", "FF"}


def _grab(text: str, pattern: str) -> List[str]:
    return re.findall(pattern, text, re.MULTILINE)


def _find_line(text: str, pattern: str) -> int:
    """Find the line number where pattern first appears."""
    m = re.search(pattern, text, re.MULTILINE)
    if m:
        return text[:m.start()].count("\n") + 1
    return 0


def _cmd_line(logical, cmd: str) -> int:
    """Return the source line of the logical command that matches ``cmd``.

    P1-1: every per-command finding should carry a reliable source location.
    Uses the same prefix-match strategy as the existing SDC-046/047 lookups
    (find_line on the first 40 chars), so a finding on a command gets the
    command's original start line; returns 0 (unknown) when unmappable.
    """
    if not cmd:
        return 0
    return find_line(logical, cmd.strip()[:40])


def _group_line(logical, clock_a: str, clock_b: str) -> int:
    """Return the source line of the set_clock_groups command that declares
    both ``clock_a`` and ``clock_b``; 0 when no such command exists.

    Used for SDC-060/061 mismatch findings whose evidence lives in a
    set_clock_groups declaration (P1-1 source-location consistency).
    """
    for c in logical:
        if "set_clock_groups" in c.text and clock_a in c.text and clock_b in c.text:
            return c.start_line
    return 0


def _flag_value(text: str, flag: str):
    """Return the numeric value of ``-flag <number>`` in text (None if absent)."""
    for f, v in extract_flag_numbers(text):
        if f == flag:
            return v
    return None


def _delay_value(text: str, command: str):
    """Return the delay value to compare against the clock period.

    Prefers the -max (setup-path) value so a statement carrying both -max and
    -min is compared on its setup constraint; falls back to -min, then to the
    first numeric literal in the statement.
    """
    v = _flag_value(text, '-max')
    if v is None:
        v = _flag_value(text, '-min')
    if v is None:
        m = re.search(r'(' + NUM_PATTERN + r')', text)
        v = float(m.group(1)) if m else None
    return v


# ── Semantic helpers (Phase 5) ──────────────────────────────────────────────

def _clock_ref(stmt: str, flag: str = "clock"):
    """Extract a clock reference from ``-<flag> <ref>`` in a statement.

    ``flag`` is the option name WITHOUT the leading dash (e.g. ``"clock"`` or
    ``"master_clock"``). Returns ``(names, netlist_dependent)`` where ``names``
    is a list of identifier names the reference statically implies, and
    ``netlist_dependent`` is True when the reference cannot be resolved from
    the SDC alone (wildcards, ``[all_clocks]``, or non-clock collections like
    ``[get_ports ...]`` / ``[get_pins ...]``).

    Examples:
      ``-clock nonexistent_clk``     → (['nonexistent_clk'], False)
      ``-clock [get_clocks clk_a]``  → (['clk_a'], False)
      ``-clock [get_clocks {a b}]``  → (['a', 'b'], False)
      ``-clock [get_ports p]``       → ([], True)   netlist-dependent
      ``-clock [all_clocks]``        → ([], True)
      ``-clock [get_clocks *]``      → ([], True)
    """
    m = re.search(r'-' + flag + r'\s+(\[[^\]]*\]|\S+)', stmt)
    if not m:
        return [], True  # no reference → treat as unresolvable (no diagnostic)
    ref = m.group(1)
    if ref.startswith('['):
        inner = ref[1:-1].strip()
        if not inner or inner == 'all_clocks':
            return [], True
        if inner.startswith('get_clocks'):
            names = parse_collection(ref)
            # A wildcard INSIDE the collection (e.g. [get_clocks *] or
            # [get_clocks {clk* sync*}]) is netlist-dependent — the matched set
            # cannot be determined from the SDC alone. Reviewer fix.
            if any(('*' in n or '?' in n) for n in names):
                return [], True
            return names, False
        # get_ports / get_pins / get_cells / all_inputs / all_outputs / all_registers
        return [], True
    if '*' in ref or '?' in ref:
        return [], True
    return [ref.strip()], False


def _mcp_endpoint_sig(mc: str):
    """Return (kind, endpoint_sig) for a set_multicycle_path command.

    ``kind`` is 'setup' or 'hold' (or None if the command declares neither
    flag — a bare `set_multicycle_path 2` applies to setup). ``endpoint_sig``
    is a whitespace-normalized ``-from ... -to ...`` signature, or None when
    the command omits both -from and -to (global path). Two commands share a
    fix relationship only when their endpoint signatures are identical.
    """
    kind = 'hold' if '-hold' in mc else ('setup' if '-setup' in mc else None)
    f = re.search(r'-from\s+([^\s\[\]]+|\[[^\]]*\])', mc)
    t = re.search(r'-to\s+([^\s\[\]]+|\[[^\]]*\])', mc)
    if not (f and t):
        return (kind, None) if kind else (None, None)
    sig = re.sub(r'\s+', '', f.group(1) + t.group(1))
    return (kind, sig) if kind else (None, sig)


def _is_data_port_name(name: str) -> bool:
    """Heuristic: does a port name look like a data/address port?

    Uses token boundaries on ``_ [ ] { } . /`` so snake_case names like
    ``data_in``, ``addr_0`` and ``data0`` are caught while ``clk_core``,
    ``rst_n`` and ``scan_en`` are not.
    """
    tokens = re.split(r'[_\[\]{}./]+', name)
    for tok in tokens:
        stem = re.sub(r'\d+$', '', tok)
        if stem.lower() in ('data', 'addr', 'bus', 'wdata', 'rdata', 'din', 'dout'):
            return True
    return False


def check_sdc(text: str, context=None) -> CheckResult:
    """Validate SDC text.

    ``context`` optionally carries a design context (Phase 8) built from a
    Verilog netlist / object inventory. When provided, netlist-dependent
    references are resolved where provable (SDC-055..059) and the trust scope
    upgrades NETLIST_REQUIRED → VALIDATED for supported references. When
    omitted, behavior is exactly the historical SDC-only mode.
    """
    result = CheckResult()
    issues = result.issues
    info   = result.info
    # Normalize once: strip comments, join backslash-newline continuations,
    # and keep per-command source provenance for line reporting.
    logical = preprocess_sdc(text)
    orig = text
    text = '\n'.join(c.text for c in logical)
    lines = orig.splitlines()
    # Phase 13: retain the normalized logical commands so structured finding
    # identity can be derived from SDC command text (message-independent).
    result.logical = logical

    # ── Grab all commands ─────────────────────────────────────────────────────
    clocks          = _grab(text, r'create_clock[^;\n]*')
    gen_clocks      = _grab(text, r'create_generated_clock[^;\n]*')
    group_path      = _grab(text, r'group_path[^;\n]*')
    clk_gating_chk  = _grab(text, r'set_clock_gating_check[^;\n]*')
    clk_groups      = _grab(text, r'set_clock_groups[^;\n]*')
    clk_jitter      = _grab(text, r'set_clock_jitter[^;\n]*')
    clk_latency     = _grab(text, r'set_clock_latency[^;\n]*')
    clk_transition  = _grab(text, r'set_clock_transition[^;\n]*')
    clk_uncertainty = _grab(text, r'set_clock_uncertainty[^;\n]*')
    data_check      = _grab(text, r'set_data_check[^;\n]*')
    disable_timing  = _grab(text, r'set_disable_timing[^;\n]*')
    false_paths     = _grab(text, r'set_false_path[^;\n]*')
    ideal_network   = _grab(text, r'set_ideal_network[^;\n]*')
    input_delay     = _grab(text, r'set_input_delay[^;\n]*')
    min_pulse_width = _grab(text, r'set_min_pulse_width[^;\n]*')
    output_delay    = _grab(text, r'set_output_delay[^;\n]*')
    propagated      = _grab(text, r'set_propagated_clock[^;\n]*')
    timing_derate   = _grab(text, r'set_timing_derate[^;\n]*')
    max_delay       = _grab(text, r'set_max_delay[^;\n]*')
    min_delay       = _grab(text, r'set_min_delay[^;\n]*')
    mc_paths        = _grab(text, r'set_multicycle_path[^;\n]*')
    case_analysis   = _grab(text, r'set_case_analysis[^;\n]*')
    drive           = _grab(text, r'set_drive[^;\n]*')
    driving_cell    = _grab(text, r'set_driving_cell[^;\n]*')
    input_transition= _grab(text, r'set_input_transition[^;\n]*')
    load            = _grab(text, r'set_load[^;\n]*')
    max_area        = _grab(text, r'set_max_area[^;\n]*')
    max_cap         = _grab(text, r'set_max_capacitance[^;\n]*')
    max_fanout      = _grab(text, r'set_max_fanout[^;\n]*')
    max_trans       = _grab(text, r'set_max_transition[^;\n]*')
    oper_cond       = _grab(text, r'set_operating_conditions[^;\n]*')
    wire_load_mode  = _grab(text, r'set_wire_load_mode[^;\n]*')
    wire_load_model = _grab(text, r'set_wire_load_model[^;\n]*')
    dont_touch      = _grab(text, r'set_dont_touch[^;\n]*')
    dont_use        = _grab(text, r'set_dont_use[^;\n]*')
    sdc_version     = _grab(text, r'set\s+sdc_version[^;\n]*')
    set_units       = _grab(text, r'set_units[^;\n]*')
    max_dyn_power   = _grab(text, r'set_max_dynamic_power[^;\n]*')
    max_leak_power  = _grab(text, r'set_max_leakage_power[^;\n]*')
    voltage         = _grab(text, r'set_voltage[^;\n]*')
    voltage_area    = _grab(text, r'create_voltage_area[^;\n]*')

    virtual_clocks = [c for c in clocks if '[get_ports' not in c and '[get_pins' not in c]

    # ── ERRORS ────────────────────────────────────────────────────────────────
    if not clocks and not gen_clocks:
        ln = find_line(logical, 'create_clock') or find_line(logical, 'set_input_delay') or 1
        issues.append(Issue("error", "SDC-001",
            "No create_clock defined. Synthesis has no timing reference — all paths are unconstrained.", line=ln))

    # Duplicate clock names
    clock_names = [m for c in clocks if (m := re.search(r'-name\s+(\S+)', c)) and (m := m.group(1))]
    seen, dupes = set(), set()
    for n in clock_names:
        if n in seen:
            dupes.add(n)
        seen.add(n)
    for n in dupes:
        issues.append(Issue("error", "SDC-002",
            f'Duplicate clock name "{n}" — two create_clock commands use the same name.',
            line=_cmd_line(logical, f"create_clock -name {n}")))

    # Generated clock missing -source
    for gc in gen_clocks:
        if '-source' not in gc:
            issues.append(Issue("error", "SDC-003",
                f'create_generated_clock missing required -source: "{gc[:70]}…"',
                line=_cmd_line(logical, gc)))
        if '-divide_by' in gc and '-multiply_by' in gc:
            issues.append(Issue("error", "SDC-004",
                f'create_generated_clock has both -divide_by and -multiply_by — use one only.',
                line=_cmd_line(logical, gc)))

    if not input_delay and clocks:
        issues.append(Issue("error", "SDC-005",
            "No set_input_delay — all input ports are unconstrained."))
    if not output_delay and clocks:
        issues.append(Issue("error", "SDC-006",
            "No set_output_delay — all output ports are unconstrained."))

    for c in clocks:
        port_m = re.search(r'\[get_ports\s+([^\]]+)\]', c)
        if port_m and _is_data_port_name(port_m.group(1)):
            issues.append(Issue("error", "SDC-007",
                f'create_clock on likely data port "{port_m.group(1)}" — use dedicated clock ports only.',
                line=_cmd_line(logical, c)))

    # Build a clock-name → period lookup (primary + generated clocks that declare a period)
    period_map: Dict[str, float] = {}
    # Every DEFINED clock name (primary + generated + virtual) for undefined-reference checks
    defined_clock_names: set = set()
    for c in clocks:
        nm = re.search(r'-name\s+(\S+)', c)
        if nm:
            defined_clock_names.add(nm.group(1))
        per_m = re.search(r'-period\s+(' + NUM_PATTERN + r')', c)
        if nm and per_m:
            period_map.setdefault(nm.group(1), float(per_m.group(1)))
    for gc in gen_clocks:
        nm = re.search(r'-name\s+(\S+)', gc)
        if nm:
            defined_clock_names.add(nm.group(1))
        per_m = re.search(r'-period\s+(' + NUM_PATTERN + r')', gc)
        if nm and per_m:
            period_map.setdefault(nm.group(1), float(per_m.group(1)))

    # SDC-046 — DEFINITELY-undefined clock references (no netlist can define a
    # clock that is never declared by create_clock/create_generated_clock).
    # This fixes the P0 fallback bug: previously a delay referencing a
    # nonexistent clock was silently compared against the tightest defined clock,
    # producing a wrong-but-plausible SDC-008/009 finding.
    for id_ in input_delay:
        names, net_dep = _clock_ref(id_, 'clock')
        if not net_dep and names:
            for rn in names:
                if rn not in defined_clock_names:
                    ln = find_line(logical, id_.strip()[:40])
                    issues.append(Issue("error", "SDC-046",
                        f'set_input_delay -clock "{rn}" references an undefined clock '
                        f'(no create_clock/create_generated_clock defines it).',
                        line=ln))
    for od in output_delay:
        names, net_dep = _clock_ref(od, 'clock')
        if not net_dep and names:
            for rn in names:
                if rn not in defined_clock_names:
                    ln = find_line(logical, od.strip()[:40])
                    issues.append(Issue("error", "SDC-046",
                        f'set_output_delay -clock "{rn}" references an undefined clock '
                        f'(no create_clock/create_generated_clock defines it).',
                        line=ln))

    # SDC-047 — create_generated_clock -master_clock referencing an undefined clock.
    for gc in gen_clocks:
        names, net_dep = _clock_ref(gc, 'master_clock')
        if not net_dep and names:
            for rn in names:
                if rn not in defined_clock_names:
                    ln = find_line(logical, gc.strip()[:40])
                    issues.append(Issue("warning", "SDC-047",
                        f'create_generated_clock -master_clock "{rn}" references an undefined '
                        f'master clock — generated clock period/phase cannot be determined.',
                        line=ln))

    # SDC-048 — set_clock_groups referencing undefined clocks.
    for cg in clk_groups:
        for gm in re.finditer(r'-group\s+(\[[^\]]*\]|\{[^}]*\}|\S+)', cg):
            gnames = parse_collection(gm.group(1))
            for gname in gnames:
                # Skip wildcards / netlist-dependent tokens — only bare clock
                # names can be statically verified as defined.
                if (gname and gname not in defined_clock_names and
                        not any(ch in gname for ch in '*?[]{}')):
                    ln = find_line(logical, cg.strip()[:40])
                    issues.append(Issue("warning", "SDC-048",
                        f'set_clock_groups references clock "{gname}" which is not defined '
                        f'by any create_clock/create_generated_clock.',
                        line=ln))

    # SDC-008 / SDC-009: an I/O delay that equals/exceeds its referenced clock's
    # period leaves no timing margin for the external path. Each delay statement
    # is compared ONLY against the clock it names (via -clock), so a single
    # statement produces at most one finding. When the clock reference is missing
    # or netlist-dependent, the delay is checked once against the tightest defined
    # period instead of being duplicated per clock.
    for id_ in input_delay:
        val = _delay_value(id_, 'set_input_delay')
        if val is None:
            continue
        names, net_dep = _clock_ref(id_, 'clock')
        ln = find_line(logical, id_.strip()[:40]) if id_ else 0
        ref_name = names[0] if names else None
        if ref_name and ref_name in period_map:
            if val >= period_map[ref_name]:
                issues.append(Issue("error", "SDC-008",
                    f'set_input_delay {val}ns equals/exceeds clock {ref_name} period '
                    f'{period_map[ref_name]}ns — leaves no timing margin for input logic.',
                    line=ln))
        elif period_map and not (ref_name and ref_name not in period_map):
            # No usable -clock reference → fall back to the tightest period once.
            tgt_name = min(period_map, key=period_map.get)
            if val >= period_map[tgt_name]:
                issues.append(Issue("error", "SDC-008",
                    f'set_input_delay {val}ns equals/exceeds clock {tgt_name} period '
                    f'{period_map[tgt_name]}ns — leaves no timing margin for input logic.',
                    line=ln))

    for od in output_delay:
        val = _delay_value(od, 'set_output_delay')
        if val is None:
            continue
        names, net_dep = _clock_ref(od, 'clock')
        ln = find_line(logical, od.strip()[:40]) if od else 0
        ref_name = names[0] if names else None
        if ref_name and ref_name in period_map:
            if val >= period_map[ref_name]:
                issues.append(Issue("error", "SDC-009",
                    f'set_output_delay {val}ns equals/exceeds clock {ref_name} period '
                    f'{period_map[ref_name]}ns — leaves no timing margin for output logic.',
                    line=ln))
        elif period_map and not (ref_name and ref_name not in period_map):
            tgt_name = min(period_map, key=period_map.get)
            if val >= period_map[tgt_name]:
                issues.append(Issue("error", "SDC-009",
                    f'set_output_delay {val}ns equals/exceeds clock {tgt_name} period '
                    f'{period_map[tgt_name]}ns — leaves no timing margin for output logic.',
                    line=ln))

    for vc in virtual_clocks:
        name_m = re.search(r'-name\s+(\S+)', vc)
        if name_m:
            name = name_m.group(1)
            if any(name in p for p in propagated):
                issues.append(Issue("error", "SDC-010",
                    f'set_propagated_clock applied to virtual clock "{name}" — virtual clocks have no physical source.',
                    line=_cmd_line(logical, vc)))

    for ca in case_analysis:
        val_m = re.search(r'set_case_analysis\s+(\S+)', ca)
        if val_m:
            val = val_m.group(1).lower()
            if val not in ('0', '1', 'rising', 'falling', 'rise', 'fall'):
                issues.append(Issue("error", "SDC-011",
                    f'set_case_analysis invalid value "{val_m.group(1)}" — allowed: 0, 1, rising, falling.',
                    line=_cmd_line(logical, ca)))

    # SDC-049 — contradictory set_case_analysis values on the SAME object.
    # e.g. 'set_case_analysis 0 [get_ports mode]' then '1' later — the tool would
    # override, but two conflicting constants on one pin in one file is a bug.
    # Both source lines are reported for provenance.
    ca_objects: Dict[str, tuple] = {}   # object-str → (value, line, raw)
    for ca in case_analysis:
        val_m = re.search(r'set_case_analysis\s+(\S+)', ca)
        obj_m = re.search(r'\[(?:get_ports|get_pins|get_cells)\s+([^\]]+)\]', ca)
        if not (val_m and obj_m):
            continue
        obj = obj_m.group(1).strip()
        val = val_m.group(1).lower()
        ln = find_line(logical, ca.strip()[:40]) if ca else 0
        if obj in ca_objects:
            prev_val, prev_ln, _ = ca_objects[obj]
            if prev_val != val:
                issues.append(Issue("warning", "SDC-049",
                    f'Contradictory set_case_analysis on "{obj}": line {prev_ln} → {prev_val} '
                    f'vs line {ln} → {val}. The later value overrides the earlier — '
                    f'verify this is intentional.',
                    line=ln, line2=prev_ln))
            ca_objects[obj] = (val, ln, ca)
        else:
            ca_objects[obj] = (val, ln, ca)

    # ── WARNINGS ──────────────────────────────────────────────────────────────
    for fp in false_paths:
        if not re.search(r'-from.*async|-to.*async|-through.*scan|-from.*test', fp, re.I):
            # Match a bare token OR a full bracketed collection as one unit so
            # the message quotes the complete reference (e.g. "[get_ports rst_n]"
            # instead of truncating at the first space). Same pattern as
            # _mcp_endpoint_sig above.
            f_m = re.search(r'-from\s+([^\s\[\]]+|\[[^\]]*\])', fp)
            t_m = re.search(r'-to\s+([^\s\[\]]+|\[[^\]]*\])', fp)
            if f_m and t_m:
                issues.append(Issue("warning", "SDC-020",
                    f'set_false_path from {f_m.group(1)} to {t_m.group(1)} — confirm this is a genuine false path.',
                    line=_cmd_line(logical, fp)))

    # SDC-021 — multicycle -setup N (N>1) needs a matching -hold fix. The fix
    # may live in the SAME command ('-setup 2 -hold 1') or in a SEPARATE
    # set_multicycle_path command on the same -from/-to endpoints — both are
    # standard SDC style (e.g. 'set_multicycle_path 2 -setup ...' followed by
    # 'set_multicycle_path 1 -hold ...'). Only a hold on IDENTICAL endpoints
    # counts as the fix; a hold elsewhere leaves the setup path unfixed.
    # A hold fix counts only when it shares IDENTICAL explicit endpoints; a
    # global -hold (no -from/-to) is deliberately NOT credited for a global
    # setup — conservative direction (an extra advisory, never a missed one).
    _hold_sig_set = {sig[1] for sig in (_mcp_endpoint_sig(m) for m in mc_paths)
                     if sig is not None and sig[0] == 'hold' and sig[1] is not None}
    for mc in mc_paths:
        s_m = re.search(r'-setup\s+(\d+)', mc) or re.search(r'set_multicycle_path\s+(\d+)', mc)
        if not (s_m and int(s_m.group(1)) > 1):
            continue
        if '-hold' in mc:
            continue  # same-command fix
        sig = _mcp_endpoint_sig(mc)
        if sig and sig[1] and sig[1] in _hold_sig_set:
            continue  # matching -hold fix on the same endpoints elsewhere
        issues.append(Issue("warning", "SDC-021",
            f'Multicycle path -setup {s_m.group(1)} has no -hold fix. Add -hold {int(s_m.group(1))-1}.',
            line=_cmd_line(logical, mc)))

    for u in clk_uncertainty:
        # Extract every -setup/-hold/-rise/-fall value plus a leading flagless
        # value, regardless of option order (e.g. '-setup 100.0 -hold 50.0').
        # At most one SDC-022 (tightest) and one SDC-023 (loosest) per statement
        # so a command with both -setup and -hold produces no duplicate findings.
        vals = [v for _, v in extract_flag_numbers(u)]
        m0 = re.search(r'set_clock_uncertainty\s*(' + NUM_PATTERN + r')', u)
        if m0:
            vals.append(float(m0.group(1)))
        if vals:
            if min(vals) < 0.05:
                issues.append(Issue("warning", "SDC-022",
                    f'Clock uncertainty {min(vals)}ns is unrealistically tight — below 0.05ns causes over-optimization.',
                    line=_cmd_line(logical, u)))
            if max(vals) > 0.5:
                issues.append(Issue("warning", "SDC-023",
                    f'Clock uncertainty {max(vals)}ns is very high (>0.5ns). Verify this is intentional.',
                    line=_cmd_line(logical, u)))

    if len(clocks) > 1 and not clk_groups:
        issues.append(Issue("warning", "SDC-024",
            f'{len(clocks)} clocks defined but no set_clock_groups — CDC paths may be analyzed as synchronous.'))

    for dt in dont_touch:
        if re.search(r'\[all_cells\]|\*', dt):
            issues.append(Issue("warning", "SDC-025",
                'set_dont_touch with wildcard — blocks all optimization and degrades QoR significantly.',
                line=_cmd_line(logical, dt)))

    for mt in max_trans:
        v_m = re.search(r'set_max_transition\s+(' + NUM_PATTERN + r')', mt)
        if v_m and float(v_m.group(1)) < 0.05:
            issues.append(Issue("warning", "SDC-026",
                f'set_max_transition {v_m.group(1)}ns extremely tight — may be unachievable.',
                line=_cmd_line(logical, mt)))

    for md in max_delay:
        if '-datapath_only' not in md:
            issues.append(Issue("warning", "SDC-027",
                'set_max_delay without -datapath_only — hold constraints on same path may be violated.',
                line=_cmd_line(logical, md)))

    if input_delay and not any('-min' in i for i in input_delay):
        issues.append(Issue("warning", "SDC-028",
            'No set_input_delay -min — hold timing at input ports cannot be checked.'))
    if output_delay and not any('-min' in o for o in output_delay):
        issues.append(Issue("warning", "SDC-029",
            'No set_output_delay -min — hold timing at output ports is unconstrained.'))

    if clocks and not propagated:
        issues.append(Issue("warning", "SDC-030",
            'No set_propagated_clock — ideal clock model is over-optimistic for post-layout correlation.'))

    for cg in clk_groups:
        if not re.search(r'-asynchronous|-logically_exclusive|-physically_exclusive', cg):
            issues.append(Issue("warning", "SDC-031",
                'set_clock_groups without -asynchronous/-logically_exclusive/-physically_exclusive.',
                line=_cmd_line(logical, cg)))

    if timing_derate:
        has_early = any('-early' in t for t in timing_derate)
        has_late  = any('-late' in t for t in timing_derate)
        if has_early and not has_late:
            issues.append(Issue("warning", "SDC-032", 'set_timing_derate has -early but no -late.',
                line=_cmd_line(logical, timing_derate[0])))
        if has_late and not has_early:
            issues.append(Issue("warning", "SDC-033", 'set_timing_derate has -late but no -early.',
                line=_cmd_line(logical, timing_derate[0])))

    for dc in data_check:
        if '-clock' not in dc:
            issues.append(Issue("warning", "SDC-034", 'set_data_check without -clock reference.',
                line=_cmd_line(logical, dc)))

    if len(disable_timing) > 5:
        issues.append(Issue("warning", "SDC-035",
            f'{len(disable_timing)} set_disable_timing commands — large count can hide real violations.',
            line=_cmd_line(logical, disable_timing[0])))
    for dt in disable_timing:
        if '-from' not in dt and '-to' not in dt:
            issues.append(Issue("warning", "SDC-036",
                'set_disable_timing without -from/-to disables ALL arcs on cell — almost always wrong.',
                line=_cmd_line(logical, dt)))

    half_setup = [m for m in mc_paths if '-setup' in m and ('-rise_to' in m or '-fall_to' in m)]
    half_hold  = [m for m in mc_paths if '-hold'  in m and ('-rise_to' in m or '-fall_to' in m)]
    if half_setup and not half_hold:
        issues.append(Issue("warning", "SDC-037",
            'Half-cycle setup paths found but no matching -hold 0 counterpart. Hold analysis will be wrong.',
            line=_cmd_line(logical, half_setup[0])))

    # ── MMC / Derate reasonableness warnings (SDC-040..045) ────────────────
    for td in timing_derate:
        # cell_early: typically > 1.0 (makes early paths slower = more conservative)
        m = re.search(r'-early\s+-cell_delay\s+(' + NUM_PATTERN + r')', td)
        if m and float(m.group(1)) < 1.0:
            issues.append(Issue("warning", "SDC-040",
                f'set_timing_derate -early -cell_delay {m.group(1)} < 1.0 — early derate is typically > 1.0 for conservative hold analysis.',
                line=_cmd_line(logical, td)))
        # cell_late: typically < 1.0 (makes late paths slower = more conservative)
        m = re.search(r'-late\s+-cell_delay\s+(' + NUM_PATTERN + r')', td)
        if m and float(m.group(1)) > 1.0:
            issues.append(Issue("warning", "SDC-041",
                f'set_timing_derate -late -cell_delay {m.group(1)} > 1.0 — late derate is typically < 1.0 for conservative setup analysis.',
                line=_cmd_line(logical, td)))
        # net_early: typically > 1.0
        m = re.search(r'-early\s+-net_delay\s+(' + NUM_PATTERN + r')', td)
        if m and float(m.group(1)) < 1.0:
            issues.append(Issue("warning", "SDC-042",
                f'set_timing_derate -early -net_delay {m.group(1)} < 1.0 — early net derate is typically > 1.0.',
                line=_cmd_line(logical, td)))
        # net_late: typically < 1.0
        m = re.search(r'-late\s+-net_delay\s+(' + NUM_PATTERN + r')', td)
        if m and float(m.group(1)) > 1.0:
            issues.append(Issue("warning", "SDC-043",
                f'set_timing_derate -late -net_delay {m.group(1)} > 1.0 — late net derate is typically < 1.0.',
                line=_cmd_line(logical, td)))

    for oc in oper_cond:
        name_m = re.search(r'set_operating_conditions\s+(?:-max\s+)?(\S+)', oc)
        if name_m:
            cond_name = name_m.group(1)
            if cond_name and not any(p in cond_name.upper() for p in KNOWN_COMMON_COND):
                issues.append(Issue("warning", "SDC-044",
                    f'Operating condition "{cond_name}" does not match common patterns (WORST/BEST/TYP/SSG/TT/FFG).',
                    line=_cmd_line(logical, oc)))    # Clock uncertainty hold vs setup ratio
    for u in clk_uncertainty:
        h_val = _flag_value(u, '-hold')
        s_val = _flag_value(u, '-setup')
        if h_val is not None and s_val is not None and s_val > 0 and abs(h_val / s_val - 0.5) > 0.15:
            issues.append(Issue("warning", "SDC-045",
                f'Clock uncertainty -hold {h_val}ns is not ~0.5x of -setup {s_val}ns (ratio={h_val/s_val:.2f}). Verify intentional.',
                line=_cmd_line(logical, u)))

    # ── Clock Relations (SDC-060..063) ─────────────────────────────────────────
    try:
        from clock_relations import analyze_clock_relations
        rel_result = analyze_clock_relations(text)
        for m in rel_result.mismatches:
            if m.severity == "warning":
                # P1-1: SDC-060/061 mismatch findings map to the set_clock_groups
                # command that declares the pair — resolve its source line when
                # the declaration exists, else 0 (unknown).
                ln = _group_line(logical, m.clock_a, m.clock_b)
                issues.append(Issue("warning", m.code, m.msg, line=ln))
        # Aggregate info-level relation findings (pairs lacking an explicit
        # set_clock_groups declaration — SDC-062 — plus SDC-063 verify-intentional
        # advisories). These are advisory and can number in the hundreds for
        # designs with many clocks; the full pair-by-pair detail is still
        # available in the Clock Relations tab and its matrix. P1-2: the engine
        # now exposes these as explicit collections, so the aggregation reads
        # the real collections instead of re-deriving them from `mismatches`.
        rel_info = list(rel_result.missing_constraints) + list(rel_result.advisories)
        if rel_info:
            code = sorted({m.code for m in rel_info})[0]
            sample = rel_info[0]
            info.append(InfoItem(
                code,
                f"{len(rel_info)} clock pair(s) lack an explicit set_clock_groups declaration "
                f"(e.g. {sample.clock_a}/{sample.clock_b} — inferred {sample.expected.strip('-')}). "
                f"See the Clock Relations tab / matrix for the full pair-by-pair breakdown.",
            ))
    except Exception as exc:
        info.append(InfoItem("SDC-140", f"Clock relation analysis skipped: {exc}"))

    # ── INFO ──────────────────────────────────────────────────────────────────
    if not sdc_version:
        info.append(InfoItem("SDC-100", "No sdc_version declaration. Add 'set sdc_version 2.2' at the top."))
    if not set_units:
        info.append(InfoItem("SDC-101", "No set_units — add 'set_units -time ns -capacitance pF' to avoid unit mismatches."))
    if not max_fanout:
        info.append(InfoItem("SDC-102", "No set_max_fanout — consider set_max_fanout 20 [all_inputs]."))
    if not max_trans:
        info.append(InfoItem("SDC-103", "No set_max_transition — add set_max_transition 0.2 [all_nets]."))
    if not max_cap:
        info.append(InfoItem("SDC-104", "No set_max_capacitance."))
    if not load:
        info.append(InfoItem("SDC-105", "No set_load on outputs."))
    if not driving_cell and not input_transition and not drive:
        info.append(InfoItem("SDC-106", "No set_driving_cell / set_input_transition / set_drive — input slew is ideal."))
    if not clk_latency:
        info.append(InfoItem("SDC-107", "No set_clock_latency — model insertion delay with set_clock_latency -source before CTS."))
    if not clk_transition:
        info.append(InfoItem("SDC-108", "No set_clock_transition — constrain clock slew with set_clock_transition 0.1 [all_clocks]."))
    if not case_analysis:
        info.append(InfoItem("SDC-109", "No set_case_analysis — use for scan_en, test_mode to prevent DFT paths dominating timing."))
    if not ideal_network and clocks:
        info.append(InfoItem("SDC-110", "No set_ideal_network — mark reset/scan_en as ideal."))
    if len(false_paths) > 10:
        info.append(InfoItem("SDC-111", f'{len(false_paths)} set_false_path commands — audit each one is genuinely a false path.',
                             line=_cmd_line(logical, false_paths[0])))
    if len(mc_paths) > 8:
        info.append(InfoItem("SDC-112", f'{len(mc_paths)} set_multicycle_path commands — document each one.',
                             line=_cmd_line(logical, mc_paths[0])))
    if not dont_use:
        info.append(InfoItem("SDC-113", "No set_dont_use — consider excluding weak/problematic cells."))
    if not oper_cond:
        info.append(InfoItem("SDC-114", "No set_operating_conditions — specify PVT corner explicitly."))
    if not timing_derate:
        info.append(InfoItem("SDC-115", "No set_timing_derate — needed for AOCV/POCVM advanced signoff."))
    if not clk_jitter:
        info.append(InfoItem("SDC-116", "No set_clock_jitter — model random jitter separately from uncertainty."))
    if not group_path:
        info.append(InfoItem("SDC-117", "No group_path — improves synthesis optimization focus on critical interfaces."))
    if not clk_gating_chk:
        info.append(InfoItem("SDC-118", "No set_clock_gating_check — needed if design uses clock gating cells."))
    if disable_timing:
        info.append(InfoItem("SDC-119", f'{len(disable_timing)} set_disable_timing found — verify each is intentional.',
                             line=_cmd_line(logical, disable_timing[0])))
    if min_delay:
        info.append(InfoItem("SDC-120", f'{len(min_delay)} set_min_delay — verify no conflicts with hold constraints.',
                             line=_cmd_line(logical, min_delay[0])))
    if not wire_load_mode and not wire_load_model:
        info.append(InfoItem("SDC-121", "No wire load constraints — needed for flows without extracted RC."))
    if not max_area:
        info.append(InfoItem("SDC-122", "No set_max_area — add area target for synthesis."))
    if not max_dyn_power and not max_leak_power:
        info.append(InfoItem("SDC-123", "No power constraints."))
    if not min_pulse_width and clk_gating_chk:
        info.append(InfoItem("SDC-124", "set_clock_gating_check present but no set_min_pulse_width."))
    if voltage and not voltage_area:
        info.append(InfoItem("SDC-125", "set_voltage found but no create_voltage_area."))
    if virtual_clocks:
        info.append(InfoItem("SDC-126",
            f'{len(virtual_clocks)} virtual clock(s) detected — ensure set_input_delay/set_output_delay references them correctly.',
            line=_cmd_line(logical, virtual_clocks[0])))

    # ── MMC info items (SDC-130..132) ──────────────────────────────────────
    if oper_cond:
        # Check if any comment line near set_operating_conditions mentions a corner.
        # Use the ORIGINAL text (comments are stripped from the logical text).
        comment_lines = [l.strip() for l in orig.splitlines() if l.strip().startswith('#')]
        has_corner_comment = any(
            any(kw in cl.upper() for kw in ('CORNER', 'PVT', 'WORST', 'BEST', 'TYPICAL'))
            for cl in comment_lines
        )
        if not has_corner_comment:
            info.append(InfoItem("SDC-130",
                'set_operating_conditions found but no corner/PVT context in comments — consider adding a corner label for clarity.'))

    if len(oper_cond) > 1:
        info.append(InfoItem("SDC-131",
            f'{len(oper_cond)} set_operating_conditions commands — typically one per SDC file in multi-corner flows.'))

    if timing_derate and not oper_cond:
        info.append(InfoItem("SDC-132",
            'set_timing_derate found without set_operating_conditions — specify the PVT corner for the derate values.'))

    # ── Design-aware validation (Phase 8, optional) ───────────────────────────
    # Only when a design context is supplied. Resolves supported collections;
    # anything outside the resolver subset stays NETLIST_REQUIRED (never
    # flagged, never claimed resolved). SDC-only mode is completely unaffected.
    if context is not None:
        try:
            from design_context import validate_design_references
            for f in validate_design_references(orig, context):
                issues.append(Issue(f.sev, f.code, f.msg, line=f.line))
        except Exception as exc:  # never let design-aware analysis break the check
            info.append(InfoItem("SDC-140", f"Design-aware validation skipped: {exc}"))
        # Phase 9: design constraint coverage — "how completely does this SDC
        # describe timing intent for the supplied design?". Coverage is
        # machine-readable and separate from correctness findings; only the
        # DEFINITE conditions (SDC-064/065/066) become Issues. Anything
        # uncertain stays a coverage status, never an error.
        try:
            from design_coverage import coverage_findings, analyze_coverage
            for f in coverage_findings(orig, context):
                issues.append(Issue(f["sev"], f["code"], f["msg"], line=f["line"]))
            result.coverage = analyze_coverage(orig, context).to_dict()
        except Exception as exc:
            info.append(InfoItem("SDC-140", f"Constraint coverage analysis skipped: {exc}"))

    # ── Constraint interactions (Phase 10) ───────────────────────────────────
    # "Do multiple individually-valid constraints interact in a suspicious,
    # redundant, overridden, or contradictory way?" Runs in BOTH SDC-only and
    # design-aware modes. Provable findings only: exact duplicates (info),
    # silent overrides (info), contradictory max/min delay windows (warning),
    # and timing-exception object overlap requiring STA (info). Dual-line
    # provenance via Issue.line/line2.
    try:
        from constraint_interactions import analyze_interactions
        ia = analyze_interactions(text, context)
        result.interactions = ia.to_dict()
        for f in ia.findings:
            issues.append(Issue(f["severity"], f["code"], f["msg"],
                                line=f["line"], line2=f["line2"],
                                identity=f.get("identity")))
    except Exception as exc:
        info.append(InfoItem("SDC-140", f"Constraint-interaction analysis skipped: {exc}"))

    # ── Rationale-comment linting (SDC-150) — Feature F1 ─────────────────────
    # Enforces the advice SDC-020 already gives: every timing exception that
    # can hide a violation should carry an explanatory comment. Pure text /
    # line-proximity check — no netlist, no clock model. Runs in BOTH SDC-only
    # and design-aware modes. Provable-only: a finding fires only when no
    # substantive comment exists nearby (3 lines above or inline).
    try:
        from rationale_lint import rationale_findings
        for f in rationale_findings(orig):
            issues.append(Issue(f.sev, f.code, f.msg, line=f.line))
    except Exception as exc:  # never let rationale linting break the check
        info.append(InfoItem("SDC-140", f"Rationale-comment linting skipped: {exc}"))

    # ── Async reset & CDC structural completeness (SDC-151..153) — Feature F2 ──
    # Design-aware only: flags nets that structurally drive >=2 flip-flop reset
    # pins but have no (or only blanket/wildcard) timing exception. Provable-only
    # — SDC-only mode (context=None) returns zero findings. Complements SDC-020
    # (false-path documentation) without duplicating any existing rule.
    try:
        from async_reset_check import reset_findings
        for f in reset_findings(orig, context):
            issues.append(Issue(f.sev, f.code, f.msg, line=f.line))
    except Exception as exc:  # never let async-reset analysis break the check
        info.append(InfoItem("SDC-140", f"Async-reset analysis skipped: {exc}"))

    # ── DFT / scan-mode constraint completeness (SDC-154..155) — Feature F3 ───
    # Flag incomplete scan_enable/test_mode mode coverage (SDC-154, SDC-only
    # Phase A) and scan false paths that are provably too broad (SDC-155,
    # Phase A SDC-only + Phase B scan-chain shape from net_pins when a netlist
    # is present). Never invents DFT intent: SDC-154 fires only on PARTIAL
    # case analysis of a scan-named signal; SDC-155 fires only on blanket
    # wildcards or explicit scan/test references. Zero noise on non-DFT files.
    try:
        from dft_scan_check import dft_findings
        for f in dft_findings(orig, context):
            issues.append(Issue(f.sev, f.code, f.msg, line=f.line))
    except Exception as exc:  # never let DFT analysis break the check
        info.append(InfoItem("SDC-140", f"DFT/scan analysis skipped: {exc}"))

    # ── AOCV/POCV derate methodology (SDC-156..157) — Feature F4 ────────────
    # Advisory methodology-consistency axis on top of the value-sanity derate
    # rules (SDC-032/033/040-043/054): flags flat-only derates on flows that
    # signal an advanced (<=16nm) node (SDC-156) and flat+sigma/table derate
    # mixes (SDC-157). INFO-level by approved decision — never a
    # warning/error. Provable-only: a condition like SS_0P8V_25C (temperature)
    # or SSG_0P7V_125C never matches a node hint. Runs in BOTH modes (no
    # netlist needed).
    try:
        from derate_methodology import derate_methodology_findings
        for f in derate_methodology_findings(orig):
            if f.sev in ("warning", "error"):
                issues.append(Issue(f.sev, f.code, f.msg, line=f.line))
            else:
                info.append(InfoItem(f.code, f.msg))
    except Exception as exc:  # never let derate-methodology analysis break the check
        info.append(InfoItem("SDC-140", f"Derate-methodology analysis skipped: {exc}"))

    # ── Analysis coverage / trust scope (Phase 7 + 8) ────────────────────────
    # Records how completely the validator understood the input: fully analyzed
    # commands vs partially analyzed (ignored options) vs netlist-dependent refs
    # vs unsupported constructs. Never invents severity findings — it answers
    # "how completely did we understand this input?", a different dimension.
    result.scope = analyze_scope(orig, context=context).to_dict()

    # ── Constraint readiness (Phase 11) ───────────────────────────────────────
    # Aggregates the evidence already collected above (issues, scope, coverage,
    # interactions) into a categorical readiness review. It never re-parses the
    # SDC and never re-derives rule semantics — it is a consumer layer only.
    # READY never means "timing passes"; it means the constraint set satisfies
    # the validator's supported, evidence-backed readiness criteria for the
    # stated analysis mode.
    try:
        from constraint_readiness import analyze_readiness
        result.readiness = analyze_readiness(result).to_dict()
    except Exception as exc:
        info.append(InfoItem("SDC-140", f"Constraint-readiness analysis skipped: {exc}"))

    result.stats = {
        "Clocks":          len(clocks),
        "Generated clocks":len(gen_clocks),
        "Virtual clocks":  len(virtual_clocks),
        "Input delays":    len(input_delay),
        "Output delays":   len(output_delay),
        "False paths":     len(false_paths),
        "Multicycle paths":len(mc_paths),
        "Clock groups":    len(clk_groups),
        "Uncertainty":     len(clk_uncertainty),
        "Clk transition":  len(clk_transition),
        "Clk jitter":      len(clk_jitter),
        "Max transition":  len(max_trans),
        "Max cap":         len(max_cap),
        "Case analysis":   len(case_analysis),
        "Disable arcs":    len(disable_timing),
        "Timing derate":   len(timing_derate),
        "Oper conditions": len(oper_cond),
        "Group paths":     len(group_path),
        "Propagated":      len(propagated),
    }
    return result
