"""
Async reset & CDC structural completeness (F2, SDC-151/152/153).

Answers: *is every structurally-identifiable reset tree in the supplied design
actually constrained by a timing exception?*

Teams routinely blanket ``set_false_path`` / ``set_clock_groups -asynchronous``
over async-reset and CDC paths without verifying the applied mechanism. Both
failure modes are silent:

  - **under-constraining** — a reset tree with NO exception at all: false hold
    violations on the deassertion path, or CDC paths never analyzed.
  - **over-constraining** — a wildcard false path matching far more instances
    than intended, hiding the sync-input vs deassertion distinction.

DESIGN-AWARE ONLY
=================
Requires a ``DesignContext`` (netlist). When ``ctx`` is None (SDC-only mode)
this module returns NO findings — nothing structural can be proven, and the
project's provable-only ethos forbids guessing. These rules are skipped
entirely in SDC-only mode.

Rules (all warnings, provable-only)
===================================
``SDC-151`` — Unconstrained reset tree
    A net structurally driving >= ``RESET_FANOUT_THRESHOLD`` (2) flip-flop
    reset pins (RESET-class instance pins) with no exception touching it:
    no ``set_false_path`` / ``set_multicycle_path`` / ``set_case_analysis`` /
    ``set_max_delay`` / ``set_min_delay`` / ``set_ideal_network`` referencing
    the net or any top-level port that structurally feeds it.

``SDC-152`` — Suspect blanket false path
    A wildcard ``set_false_path`` (``-from [all_inputs]`` / ``*`` /
    ``[all_ports]`` etc.) provably covers the reset tree while no TARGETED
    exception exists. A blanket cut hides the sync-input vs deassertion
    distinction that a reset synchronizer requires. (The ``-asynchronous``
    clock-group variant is named in the fix text; clock groups are clock-level
    and cannot be provably mapped to a reset net by this module.)

``SDC-153`` — Reset synchronizer input unconstrained
    A reset tree whose net ALSO connects to DATA-role instance pin(s) — the
    structural shape of an async-reset synchronizer's sync stage — with no
    exception. The sync input and the deassertion path need distinct
    handling, not one blanket false path.

Coverage model (provable)
=========================
A candidate reset net's coverage names are its own name plus every top-level
port that structurally feeds it (traced through instance input pins:
``port net -> instance/inputPin -> module port net``). An exception "touches"
the tree when any covered name appears in a ``get_ports`` / ``get_nets`` /
``get_pins`` reference of an exception command. Wildcard ``all_*``/``*``
references are NOT targeted coverage — they are the SDC-152 trigger.
"""

import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Set

from sdc_preprocess import preprocess_sdc

#: Fixed, documented threshold (approved decision #2): a net must structurally
#: drive at least this many RESET-class instance pins to count as a reset tree.
RESET_FANOUT_THRESHOLD: int = 2

#: Exception commands that can "touch" (constrain) a reset tree.
_EXCEPTION_CMDS = (
    "set_false_path", "set_multicycle_path", "set_case_analysis",
    "set_max_delay", "set_min_delay", "set_ideal_network",
)

#: Wildcard / all-* collection prefixes that are BLANKET (not targeted) coverage.
_BLANKET_PREFIXES = ("[all_inputs]", "[all_ports]", "[all_outputs]",
                     "[all_registers]", "[all_cells]", "[all_nets]",
                     "[all_clocks]")


@dataclass
class Finding:
    """A single async-reset finding (SDC-151/152/153)."""

    sev: str
    code: str
    msg: str
    line: int = 0


def _pin_role(pin_name: str) -> str:
    """RESET-class detection for an instance pin name.

    Mirrors ``design_context._pin_role`` (single source of truth stays in
    design_context; this is the one role this module needs). Case-insensitive
    suffix match on reset pin names with a boundary guard so 'contest' is not
    a reset pin and 'rst_n' is.
    """
    low = pin_name.lower()
    for name in ("arstn", "resetn", "reset", "rstn", "arst", "rn", "rst"):
        if low.endswith(name) and (
                len(low) == len(name) or not low[-len(name) - 1].isalnum()):
            return "RESET"
    return ""


def _is_data_pin(pin_name: str) -> bool:
    """DATA-class detection (D/DIN/Q/DOUT ...) for sync-stage shape evidence."""
    low = pin_name.lower()
    for name in ("dout", "d", "din", "q", "qn", "do", "data", "di"):
        if low.endswith(name) and (
                len(low) == len(name) or not low[-len(name) - 1].isalnum()):
            return True
    return False


def _reset_nets(ctx) -> List[str]:
    """Nets structurally driving >= RESET_FANOUT_THRESHOLD RESET-class pins."""
    out = []
    for net, pins in ctx.net_pins.items():
        reset_pins = [p for p in pins if _pin_role(ctx.pin_name(p)) == "RESET"]
        if len(reset_pins) >= RESET_FANOUT_THRESHOLD:
            out.append(net)
    return out


def _port_reachability(ctx) -> Dict[str, Set[str]]:
    """One-time map: top-level port -> set of nets reachable through input pins.

    Computed once per design (not per candidate net) so large netlists stay
    linear-ish: each port's BFS closure is the module-port names its net can
    reach. ``_port_feeds_net`` then becomes a set lookup.
    """
    reach: Dict[str, Set[str]] = {}
    for port in ctx.ports:
        seen: Set[str] = set()
        frontier = [port]
        while frontier:
            cur = frontier.pop()
            if cur in seen:
                continue
            seen.add(cur)
            for pin_path in ctx.net_pins.get(cur, set()):
                path, _, pname = pin_path.rpartition("/")
                inst = ctx.instances.get(path)
                if not inst:
                    continue
                d = ctx.module_port_dirs.get(inst.module, {}).get(pname, "")
                if d == "input":
                    frontier.append(pname)
        reach[port] = seen
    return reach


def _coverage_names(ctx, net: str, reach: Dict[str, Set[str]]) -> List[str]:
    """Coverage names for a reset net: itself + feeding top-level ports."""
    names = [net]
    for port, seen in reach.items():
        if port != net and net in seen:
            names.append(port)
    return names


def _exception_commands(text: str) -> List[str]:
    """Exception commands from ``text`` (comments stripped, continuations
    joined, one entry per command) — the only commands that can touch a reset
    tree. ``create_clock`` / ``set_input_delay`` / ``set_load`` etc. are NOT
    exception coverage and never count."""
    out = []
    for cmd in preprocess_sdc(text):
        low = cmd.text.lstrip().lower()
        if any(low.startswith(k) for k in _EXCEPTION_CMDS):
            out.append(cmd.text)
    return out


def _targeted_refs(exception_cmds: List[str], names: List[str]) -> Set[str]:
    """Names of the reset tree referenced by TARGETED (non-wildcard) exception
    collections. Only exception commands count as coverage; a reference in a
    non-exception command (input delay, load, ...) never suppresses a finding.

    Token-boundary match so 'rst_n' is not "covered" by a reference to
    'rst_n_sync' or 'pwr_rst_n': the name must stand alone within the
    collection arguments (word chars are [A-Za-z0-9_]).
    """
    touched: Set[str] = set()
    if not exception_cmds:
        return touched
    for name in names:
        pat = re.compile(r"(?<![\w]){}(?![\w])".format(re.escape(name)))
        for cmd in exception_cmds:
            for m in re.findall(
                    r"\[(?:get_ports|get_nets|get_pins)\s+([^\]]*)\]", cmd):
                if pat.search(m):
                    touched.add(name)
                    break
            if name in touched:
                break
    return touched


def _blanket_false_paths(exception_cmds: List[str]) -> List[str]:
    """set_false_path commands whose -from side is wildcard/all-*.

    A blanket FROM side (``[all_inputs]`` / ``[all_ports]`` / ``*``) provably
    covers any reset port on that side — the over-constraining shape.
    """
    out = []
    for cmd in exception_cmds:
        if not cmd.lstrip().lower().startswith("set_false_path"):
            continue
        low = cmd.lower()
        from_m = re.search(r"-from\s+(\[[^\]]*\]|\S+)", low)
        ref = (from_m.group(1) if from_m else "").lower()
        if not ref:
            continue
        if any(ref.startswith(p) for p in _BLANKET_PREFIXES) or "*" in ref:
            out.append(cmd)
    return out


def reset_findings(text: str, ctx=None) -> List[Finding]:
    """Scan an SDC + design context for unconstrained reset / CDC structures.

    ``ctx`` (DesignContext) is optional. When absent (SDC-only mode) this
    returns an empty list — nothing structural can be proven.

    Returns one ``Finding`` per candidate reset tree (warning), with the
    structural evidence (net + feeding ports + reset-pin count) in the message.
    """
    if ctx is None:
        return []

    findings: List[Finding] = []
    exception_cmds = _exception_commands(text)
    blanket = _blanket_false_paths(exception_cmds)
    reach = _port_reachability(ctx)

    for net in _reset_nets(ctx):
        reset_pin_count = sum(
            1 for p in ctx.net_pins.get(net, set())
            if _pin_role(ctx.pin_name(p)) == "RESET")
        names = _coverage_names(ctx, net, reach)
        display = " / ".join(names)
        # Fix suggestion should reference a top-level port when one feeds the
        # tree (hierarchical designs: internal net 'rst' is driven by port
        # 'rst_n'); fall back to the net name itself in flat designs.
        fix_ref = names[-1] if len(names) > 1 else names[0]
        sync_shape = any(
            _is_data_pin(ctx.pin_name(p)) for p in ctx.net_pins.get(net, set()))

        touched = _targeted_refs(exception_cmds, names)
        if touched:
            continue  # targeted exception already constrains this tree

        # SDC-152: a blanket wildcard false path provably covers the tree and
        # no targeted exception exists.
        blanket_line = 0
        for cmd in blanket:
            low = cmd.lower()
            from_m = re.search(r"-from\s+(\[[^\]]*\]|\S+)", low)
            ref = (from_m.group(1) if from_m else "").lower()
            if any(ref.startswith(p) for p in _BLANKET_PREFIXES) or "*" in ref:
                blanket_line = _find_line(text, cmd)
                findings.append(Finding(
                    "warning", "SDC-152",
                    f"Wildcard false path covers reset tree '{display}' "
                    f"({reset_pin_count} reset pin(s)) with no targeted "
                    f"exception — a blanket cut hides the sync-input vs "
                    f"deassertion distinction. Replace with a targeted "
                    f"set_false_path on the reset net (or -through its "
                    f"synchronizer), and consider whether a "
                    f"set_clock_groups -asynchronous is masking CDC paths.",
                    line=blanket_line,
                ))
                break
        if blanket_line:
            continue

        # SDC-153: synchronizer sync-stage shape — the reset net also drives
        # DATA pins (the reset is fed into a flop's data input).
        if sync_shape:
            findings.append(Finding(
                "warning", "SDC-153",
                f"Reset tree '{display}' ({reset_pin_count} reset pin(s)) also "
                    f"drives data input(s) — async-reset synchronizer sync "
                    f"stage. The sync input and the deassertion path need "
                    f"distinct exceptions, not one blanket false path.",
            ))
            continue

        # SDC-151: plain unconstrained reset tree.
        findings.append(Finding(
            "warning", "SDC-151",
            f"Reset tree '{display}' drives {reset_pin_count} flip-flop reset "
                f"pin(s) but has no timing exception — async reset deassertion "
                f"and CDC paths are unconstrained. Add a targeted "
                f"set_false_path (e.g. -from [get_ports {fix_ref}] "
                f"-to [all_registers]) or set_ideal_network, and verify the "
                f"reset synchronizer input.",
        ))

    return findings


def _find_line(text: str, needle: str) -> int:
    """1-based line of the first occurrence of ``needle`` (0 if absent)."""
    idx = text.find(needle)
    if idx == -1:
        return 0
    return text[:idx].count("\n") + 1
