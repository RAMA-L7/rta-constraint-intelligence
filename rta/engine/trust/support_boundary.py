"""
Support Boundary — analysis-coverage / trust model for Ṛta.

Answers the question: "how completely did the validator understand this SDC?"

The validator's deterministic rules are scoped. Some constructs it analyzes
fully, some partially (options silently ignored), some require design/netlist
context, and some are unsupported Tcl/SDC. A "no errors" result must never be
read as "everything was proven correct" when parts of the input were outside
the analysis scope. This module makes that boundary explicit, measurable, and
machine-readable — without inventing severity findings.

Trust status ≠ severity:
  - Severity answers  "how serious is the finding?"
  - Trust status answers "how completely did we understand this input?"

Statuses (precedence high → low):
  UNSUPPORTED             — an unrecognized command is present
  TCL_EXECUTION_REQUIRED  — a Tcl construct requiring execution is present
  PARTIALLY_VALIDATED     — recognized commands had ignored/unknown options
  NETLIST_REQUIRED        — object references need design/netlist context
  VALIDATED               — every construct was fully analyzed within scope
  NOT_VALIDATED           — nothing analyzable found in the input
"""

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set

from sdc_preprocess import preprocess_sdc


# ── Command inventory ──────────────────────────────────────────────────────────
#
# STANDARD_OPTIONS: authoritative option set for each SDC command (Accellera
#   SDC 2.1 / Synopsys-style command reference — the same semantics used to
#   derive golden expectations in Phases 2–5).
#
# INTERPRETED_OPTIONS: the subset the validator's checker actually reads for
#   deterministic analysis. Everything else is silently ignored unless listed.
#   This is the source of truth for the silent-ignore audit.

STANDARD_OPTIONS: Dict[str, Set[str]] = {
    "create_clock":              {"-name", "-period", "-waveform", "-add", "-comment"},
    "create_generated_clock":    {"-name", "-source", "-master_clock", "-divide_by",
                                  "-multiply_by", "-invert", "-preinvert", "-add",
                                  "-edge_shift", "-combinational", "-duty_cycle",
                                  "-period"},
    "set_clock_groups":          {"-group", "-asynchronous", "-logically_exclusive",
                                  "-physically_exclusive", "-allow_paths", "-allow_async_paths"},
    "set_clock_uncertainty":     {"-setup", "-hold", "-rise", "-fall", "-clock",
                                  "-source", "-from", "-to"},
    "set_clock_latency":         {"-source", "-rise", "-fall", "-min", "-max",
                                  "-early", "-late", "-clock"},
    "set_clock_transition":      {"-rise", "-fall", "-min", "-max", "-clock"},
    "set_clock_jitter":          {"-setup", "-hold", "-rise", "-fall", "-early",
                                  "-late", "-clock", "-source"},
    "set_clock_sense":           {"-positive", "-negative", "-stop_propagation", "-clock", "-pulse"},
    "set_propagated_clock":      set(),
    "set_clock_gating_check":    {"-setup", "-hold", "-rise", "-fall", "-clock", "-low", "-high"},
    "set_input_delay":           {"-clock", "-clock_fall", "-rise", "-fall", "-max", "-min",
                                  "-add_delay", "-reference_pin", "-source_latency_included",
                                  "-network_latency_included", "-level_sensitive",
                                  "-disable_clock_gating_check"},
    "set_output_delay":          {"-clock", "-clock_fall", "-rise", "-fall", "-max", "-min",
                                  "-add_delay", "-reference_pin", "-source_latency_included",
                                  "-network_latency_included", "-level_sensitive",
                                  "-disable_clock_gating_check"},
    "set_input_transition":      {"-rise", "-fall", "-min", "-max", "-clock"},
    "set_load":                  {"-min", "-max", "-rise", "-fall", "-pin_load",
                                  "-wire_load", "-clock"},
    "set_driving_cell":          {"-lib_cell", "-pin", "-from_pin", "-to_pin", "-rise",
                                  "-fall", "-min", "-max", "-clock", "-input_transition_rise",
                                  "-input_transition_fall", "-library", "-dont_scale"},
    "set_drive":                 {"-min", "-max", "-rise", "-fall", "-clock"},
    "set_false_path":            {"-from", "-to", "-through", "-rise_from", "-rise_to",
                                  "-fall_from", "-fall_to", "-setup", "-hold"},
    "set_multicycle_path":       {"-setup", "-hold", "-from", "-to", "-through",
                                  "-rise_from", "-rise_to", "-fall_from", "-fall_to",
                                  "-start", "-end"},
    "set_max_delay":             {"-from", "-to", "-through", "-rise_from", "-rise_to",
                                  "-fall_from", "-fall_to", "-setup", "-hold",
                                  "-datapath_only", "-ignore_clock_latency"},
    "set_min_delay":             {"-from", "-to", "-through", "-rise_from", "-rise_to",
                                  "-fall_from", "-fall_to", "-setup", "-hold",
                                  "-ignore_clock_latency"},
    "set_case_analysis":         set(),
    "set_disable_timing":        {"-from", "-to", "-through", "-type"},
    "set_data_check":            {"-from", "-to", "-clock", "-rise_from", "-fall_from",
                                  "-rise_to", "-fall_to", "-setup", "-hold",
                                  "-clock_gating_check"},
    "set_max_transition":        {"-rise", "-fall", "-min", "-max", "-clock"},
    "set_min_transition":        {"-rise", "-fall", "-min", "-max", "-clock"},
    "set_max_capacitance":       {"-rise", "-fall", "-min", "-max", "-clock"},
    "set_min_capacitance":       {"-rise", "-fall", "-min", "-max", "-clock"},
    "set_max_fanout":            {"-clock"},
    "set_max_area":              set(),
    "set_operating_conditions":  {"-min", "-max", "-analysis_type", "-library"},
    "set_timing_derate":         {"-early", "-late", "-cell_delay", "-net_delay",
                                  "-clock_delay", "-data_delay"},
    "set_wire_load_mode":        {"-top", "-segmented", "-enclosed"},
    "set_wire_load_model":       {"-name", "-library", "-min", "-max"},
    "set_ideal_network":         {"-no_propagate", "-delay", "-clock"},
    "set_ideal_latency":         {"-source", "-rise", "-fall", "-min", "-max",
                                  "-early", "-late", "-clock"},
    "set_ideal_transition":      {"-rise", "-fall", "-min", "-max", "-clock"},
    "set_max_dynamic_power":     set(),
    "set_max_leakage_power":     set(),
    "set_min_pulse_width":       {"-low", "-high", "-rise", "-fall", "-clock"},
    "set_dont_use":              set(),
    "set_dont_touch":            set(),
    "group_path":                {"-name", "-from", "-to", "-through", "-weight"},
    "set_voltage":               {"-object_list"},
    "create_voltage_area":       {"-name", "-region", "-guard_band_x", "-guard_band_y"},
    "set_units":                 {"-time", "-capacitance", "-resistance", "-voltage",
                                  "-current", "-power"},
    "set_sdc_version":           set(),
}

INTERPRETED_OPTIONS: Dict[str, Set[str]] = {
    # -waveform is read by constraint_diff.py (change detection), matching the
    # set_units convention of crediting options parsed by ANY validator module.
    "create_clock":              {"-name", "-period", "-waveform"},
    "create_generated_clock":    {"-name", "-period", "-source", "-master_clock",
                                  "-divide_by", "-multiply_by"},
    "set_clock_groups":          {"-group", "-asynchronous", "-logically_exclusive",
                                  "-physically_exclusive"},
    "set_clock_uncertainty":     {"-setup", "-hold", "-rise", "-fall"},
    "set_clock_latency":         set(),
    "set_clock_transition":      set(),
    "set_clock_jitter":          set(),
    "set_propagated_clock":      set(),
    "set_clock_gating_check":    set(),
    "set_input_delay":           {"-clock", "-max", "-min"},
    "set_output_delay":          {"-clock", "-max", "-min"},
    "set_input_transition":      set(),
    "set_load":                  set(),
    "set_driving_cell":          set(),
    "set_drive":                 set(),
    "set_false_path":            {"-from", "-to", "-through"},
    "set_multicycle_path":       {"-setup", "-hold", "-rise_to", "-fall_to"},
    "set_max_delay":             {"-datapath_only"},
    "set_min_delay":             set(),
    "set_case_analysis":         set(),
    "set_disable_timing":        {"-from", "-to"},
    "set_data_check":            {"-clock"},
    "set_max_transition":        set(),
    "set_min_transition":        set(),
    "set_max_capacitance":       set(),
    "set_min_capacitance":       set(),
    "set_max_fanout":            set(),
    "set_max_area":              set(),
    "set_operating_conditions":  {"-max"},
    "set_timing_derate":         {"-early", "-late", "-cell_delay", "-net_delay"},
    "set_wire_load_mode":        set(),
    "set_wire_load_model":       set(),
    "set_ideal_network":         set(),
    "set_ideal_latency":         set(),
    "set_ideal_transition":      set(),
    "set_max_dynamic_power":     set(),
    "set_max_leakage_power":     set(),
    "set_min_pulse_width":       set(),
    "set_dont_use":              set(),
    "set_dont_touch":            set(),
    "group_path":                set(),
    "set_voltage":               set(),
    "create_voltage_area":       set(),
    "set_units":                 {"-time", "-capacitance", "-resistance", "-voltage",
                                  "-current", "-power"},
    "set_sdc_version":           set(),
}

# Commands the validator actually PARSES for analysis. Union of the command
# inventories in checker.py (_grab list), linter.py (COMMAND_CATEGORY) and
# coverage.py (coverage items). A standard SDC command NOT in this set is
# treated as text with no analysis → classified UNSUPPORTED.
RECOGNIZED_COMMANDS: Set[str] = {
    "create_clock", "create_generated_clock", "group_path",
    "set_clock_gating_check", "set_clock_groups", "set_clock_jitter",
    "set_clock_latency", "set_clock_transition", "set_clock_uncertainty",
    "set_data_check", "set_disable_timing", "set_false_path", "set_ideal_network",
    "set_input_delay", "set_min_pulse_width", "set_output_delay",
    "set_propagated_clock", "set_timing_derate", "set_max_delay", "set_min_delay",
    "set_multicycle_path", "set_case_analysis", "set_drive", "set_driving_cell",
    "set_input_transition", "set_load", "set_max_area", "set_max_capacitance",
    "set_max_fanout", "set_max_transition", "set_min_capacitance",
    "set_operating_conditions", "set_wire_load_mode", "set_wire_load_model",
    "set_dont_touch", "set_dont_use", "set_sdc_version", "set_units",
    "set_max_dynamic_power", "set_max_leakage_power", "set_voltage",
    "create_voltage_area",
}

# Standard SDC commands the validator does NOT recognize at all — they silently
# become "other" text. Documented here so the boundary is explicit (Phase 7
# inventory; not newly implemented rules).
STANDARD_UNRECOGNIZED: Set[str] = {
    "set_clock_sense",        # in STANDARD_OPTIONS for doc; no module parses it
    "set_ideal_latency",
    "set_ideal_transition",
    "set_min_transition",
}

# Netlist-dependent collection functions — resolution requires design context
# (ports/pins/cells/nets/hierarchy). Their presence marks the construct
# NETLIST_REQUIRED: the SDC is not wrong, it just cannot be fully verified
# without the design.
NETLIST_COLLECTION_FNS: Set[str] = {
    "get_ports", "get_pins", "get_cells", "get_nets", "get_lib_cells",
    "get_clocks", "get_registers",
    "all_inputs", "all_outputs", "all_clocks", "all_registers",
    "all_nets", "all_cells", "all_ports",
    "filter_collection", "add_to_collection", "remove_from_collection",
}

# Tcl constructs that would require Tcl execution to evaluate. Never executed;
# their presence means the file contains semantics outside static scope.
TCL_EXECUTION_REQUIRED: Set[str] = {
    "if", "foreach", "for", "while", "proc", "source", "exec", "eval",
    "expr", "list", "concat", "lindex", "llength", "lappend", "lrange",
    "string", "format", "array", "switch", "regexp", "regsub", "uplevel",
    "upvar", "return", "break", "continue", "error", "catch", "namespace",
    "puts", "global",
}

# Tcl scalar assignment (`set NAME VALUE`) — the bounded subset supported
# since Phase 4. `set sdc_version` is normalized to set_sdc_version.
TCL_VARIABLE_ASSIGNMENT = "set"

# Design-object queries (`current_design`, `current_instance`) return design
# context — resolvable only with a netlist, never worth executing.
NETLIST_QUERY_COMMANDS: Set[str] = {"current_design", "current_instance"}

# Inline `[expr ...]` / `[eval ...]` / `[exec ...]` / `[source ...]` substitution
# inside a command requires Tcl execution to evaluate. Note: a braced literal
# such as `set x {[expr 5]}` is also flagged — conservative over-flag, safe
# direction (the validator never executes anything).
_INLINE_TCL_RE = re.compile(
    r"\[(?:expr|eval|exec|source)\s", re.IGNORECASE)


# ── Per-construct status ───────────────────────────────────────────────────────

@dataclass
class ConstructStatus:
    command: str                 # command name as found (normalized)
    level: str                   # FULL | PARTIAL | NETLIST_REQUIRED | UNSUPPORTED | TCL_EXECUTION_REQUIRED
    count: int = 0
    netlist_refs: int = 0        # number of netlist-dependent collection refs
    ignored_options: List[str] = field(default_factory=list)   # standard, not interpreted
    unknown_options: List[str] = field(default_factory=list)   # not in standard set
    note: str = ""


@dataclass
class AnalysisScope:
    status: str = "NOT_VALIDATED"
    commands_found: int = 0
    fully_analyzed: int = 0
    partially_analyzed: int = 0
    netlist_required: int = 0
    unsupported: int = 0
    tcl_execution_required: int = 0
    unknown_options: List[str] = field(default_factory=list)
    ignored_options: List[str] = field(default_factory=list)
    constructs: List[ConstructStatus] = field(default_factory=list)
    design: Optional[dict] = None      # Phase 8: set when design context supplied

    def to_dict(self) -> dict:
        return {
            "status": self.status,
            "commands_found": self.commands_found,
            "fully_analyzed": self.fully_analyzed,
            "partially_analyzed": self.partially_analyzed,
            "netlist_required": self.netlist_required,
            "unsupported": self.unsupported,
            "tcl_execution_required": self.tcl_execution_required,
            "unknown_options": self.unknown_options,
            "ignored_options": self.ignored_options,
            "design": self.design,
            "constructs": [
                {"command": c.command, "level": c.level, "count": c.count,
                 "netlist_refs": c.netlist_refs,
                 "ignored_options": c.ignored_options,
                 "unknown_options": c.unknown_options, "note": c.note}
                for c in self.constructs
            ],
        }

    def summary_lines(self) -> List[str]:
        """Human-readable, technically specific summary (no scary generic text)."""
        lines = [
            f"Commands found: {self.commands_found}",
            f"Fully analyzed: {self.fully_analyzed}",
            f"Partially analyzed: {self.partially_analyzed}",
            f"Netlist-dependent references: {self.netlist_required}",
            f"Unsupported commands/Tcl: {self.unsupported + self.tcl_execution_required}",
        ]
        if self.ignored_options:
            lines.append("Options present but not value-analyzed: "
                         + ", ".join(sorted(set(self.ignored_options))[:12]))
        if self.unknown_options:
            lines.append("Unrecognized options: "
                         + ", ".join(sorted(set(self.unknown_options))[:12]))
        return lines


# ── Option / reference extraction ──────────────────────────────────────────────

def _extract_options(cmd_text: str) -> Set[str]:
    """Extract `-option` tokens (options always begin with a letter)."""
    masked = re.sub(r"\[[^\]]*\]", " ", cmd_text)
    masked = re.sub(r"\{[^}]*\}", " ", masked)
    return set(re.findall(r"-[a-zA-Z][\w-]*", masked))


def _extract_netlist_refs(cmd_text: str) -> int:
    return len(re.findall(
        r"\[(all_\w+|get_\w+|filter_collection|add_to_collection|remove_from_collection)\b",
        cmd_text))


def _extract_first_word(cmd_text: str) -> str:
    return cmd_text.strip().split()[0] if cmd_text.strip() else ""


def _normalize_command(cmd_text: str) -> str:
    """Normalize 'set sdc_version' → 'set_sdc_version' (linter convention)."""
    first = _extract_first_word(cmd_text)
    if first == "set":
        rest = cmd_text.strip().split()
        if len(rest) >= 2 and rest[1] == "sdc_version":
            return "set_sdc_version"
        return TCL_VARIABLE_ASSIGNMENT  # scalar assignment (supported subset)
    return first


# ── Analyzer ───────────────────────────────────────────────────────────────────

def analyze_scope(text: str, context=None) -> AnalysisScope:
    """Classify every logical command in an SDC input against the support model.

    ``context`` is an optional design context (Phase 8). When present, supported
    collection references are resolved against it: expressions that provably
    resolve upgrade their command from NETLIST_REQUIRED to FULL (VALIDATED
    trust). Anything outside the resolver subset stays NETLIST_REQUIRED —
    uploading a netlist never upgrades trust without evidence.
    """
    scope = AnalysisScope()
    per_cmd: Dict[tuple, ConstructStatus] = {}
    ignored_all: List[str] = []
    unknown_all: List[str] = []

    for logical in preprocess_sdc(text):
        cmd_text = logical.text.strip()
        if not cmd_text:
            continue
        scope.commands_found += 1
        cmd = _normalize_command(cmd_text)

        # ── Inline Tcl substitution ([expr ...], [exec ...], ...) ────────────
        if _INLINE_TCL_RE.search(cmd_text):
            _merge(per_cmd, ConstructStatus(
                command="[expr/eval/exec ...] substitution", level="TCL_EXECUTION_REQUIRED",
                count=1, note="Value requires Tcl execution — not statically resolvable."))
            continue

        # ── Tcl variable assignment: supported bounded subset ────────────────
        if cmd == TCL_VARIABLE_ASSIGNMENT:
            _merge(per_cmd, ConstructStatus(command="set (variable)", level="FULL", count=1))
            continue

        # ── Design-object queries (current_design / current_instance) ────────
        if cmd in NETLIST_QUERY_COMMANDS:
            _merge(per_cmd, ConstructStatus(
                command=cmd, level="NETLIST_REQUIRED", count=1, netlist_refs=1,
                note="Design-object query — resolvable only with design context."))
            continue

        # ── Unsupported Tcl control/execution constructs ─────────────────────
        if cmd in TCL_EXECUTION_REQUIRED:
            _merge(per_cmd, ConstructStatus(
                command=cmd, level="TCL_EXECUTION_REQUIRED", count=1,
                note="Tcl construct requiring execution — not evaluated by this static validator."))
            continue

        # ── Standard SDC commands the validator does not recognize ───────────
        if cmd not in RECOGNIZED_COMMANDS:
            _merge(per_cmd, ConstructStatus(
                command=cmd, level="UNSUPPORTED", count=1,
                note="Command not recognized by any validator module — present but not analyzed."))
            continue

        # ── Recognized SDC command: option-level audit ───────────────────────
        opts = _extract_options(cmd_text)
        std = STANDARD_OPTIONS.get(cmd, set())
        interp = INTERPRETED_OPTIONS.get(cmd, set())
        ignored = sorted(o for o in opts if o in std and o not in interp)
        unknown = sorted(o for o in opts if o not in std)
        netlist = _extract_netlist_refs(cmd_text)

        if ignored or unknown:
            level = "PARTIAL"
        elif netlist:
            # Phase 8: with design context, references that provably resolve
            # upgrade to FULL; unresolvable/unsupported ones stay NETLIST_REQUIRED.
            if context is not None:
                level = _resolve_level(cmd_text, context)
            else:
                level = "NETLIST_REQUIRED"
        else:
            level = "FULL"

        _merge(per_cmd, ConstructStatus(
            command=cmd, level=level, count=1, netlist_refs=netlist,
            ignored_options=ignored, unknown_options=unknown))
        ignored_all.extend(ignored)
        unknown_all.extend(unknown)

    scope.constructs = sorted(per_cmd.values(), key=lambda c: (c.command, c.level))
    scope.ignored_options = sorted(set(ignored_all))
    scope.unknown_options = sorted(set(unknown_all))

    for c in scope.constructs:
        if c.level == "FULL":
            scope.fully_analyzed += 1
        elif c.level == "PARTIAL":
            scope.partially_analyzed += 1
        elif c.level == "NETLIST_REQUIRED":
            scope.netlist_required += 1
        elif c.level == "UNSUPPORTED":
            scope.unsupported += 1
        elif c.level == "TCL_EXECUTION_REQUIRED":
            scope.tcl_execution_required += 1

    # Trust status (precedence: unsupported > tcl > partial > netlist > full)
    if scope.unsupported:
        scope.status = "UNSUPPORTED"
    elif scope.tcl_execution_required:
        scope.status = "TCL_EXECUTION_REQUIRED"
    elif scope.partially_analyzed:
        scope.status = "PARTIALLY_VALIDATED"
    elif scope.netlist_required:
        scope.status = "NETLIST_REQUIRED"
    elif scope.commands_found and scope.fully_analyzed == scope.commands_found:
        scope.status = "VALIDATED"
    else:
        scope.status = "NOT_VALIDATED"

    # Phase 8: attach design-aware metadata so UI/reports can show which mode
    # was used and what objects were available for resolution.
    scope.design = None
    if context is not None:
        try:
            scope.design = {
                "analysis_mode": "design_aware",
                "top_module": getattr(context, "top_module", ""),
                **context.object_counts(),
            }
        except Exception:
            scope.design = {"analysis_mode": "design_aware"}
    return scope


def _resolve_level(cmd_text: str, context) -> str:
    """Return FULL when every supported collection ref in cmd resolves against
    the design context, else NETLIST_REQUIRED.

    Only get_ports/get_pins/get_cells/get_nets/all_* references are considered
    (get_clocks is SDC-defined and is skipped). Any reference the resolver
    cannot prove stays NETLIST_REQUIRED — trust upgrades only with evidence.
    """
    try:
        from design_context import resolve_collection, _COLL_RE, RESOLVED
        found_any = False
        for m in _COLL_RE.finditer(cmd_text):
            kind = m.group(1).lower()
            if kind in ("get_clocks", "all_clocks"):
                # SDC-defined collections: no netlist resolution needed, and
                # they do not make the command netlist-dependent.
                continue
            found_any = True
            res = resolve_collection(kind, m.group(2).strip(), context)
            if res.kind != RESOLVED:
                return "NETLIST_REQUIRED"
        # Only SDC-defined (get_clocks/all_clocks) refs present → command is
        # fully analyzable with the design context loaded.
        return "FULL"
    except Exception:
        pass
    return "NETLIST_REQUIRED"


def _merge(d: Dict[tuple, ConstructStatus], st: ConstructStatus) -> None:
    """Merge a single-command observation into the per-command aggregate."""
    key = (st.command, st.level)
    if key in d:
        d[key].count += 1
        d[key].netlist_refs += st.netlist_refs
        for o in st.ignored_options:
            if o not in d[key].ignored_options:
                d[key].ignored_options.append(o)
        for o in st.unknown_options:
            if o not in d[key].unknown_options:
                d[key].unknown_options.append(o)
    else:
        d[key] = st
