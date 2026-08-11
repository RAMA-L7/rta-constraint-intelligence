"""
Design-aware Constraint Coverage — timing-intent analysis (Phase 9).

Answers the question: *how completely does this SDC describe timing intent for
the supplied design?* — WITHOUT building a timing engine.

This module is deliberately NOT a static timing analyzer. It never computes
arrival/required times, slack, cell delays, or path delays. It operates on
structure + constraints only:

  - which real top-level inputs have set_input_delay (and which provably do not)
  - which outputs have set_output_delay
  - which buses are fully / partially covered
  - do supported timing-exception collections resolve to real design objects
  - are generated-clock -source / create_clock targets structurally resolvable

COVERAGE vs CORRECTNESS (mandatory distinction):
  Coverage answers "was something constrained?"
  Correctness answers "was it constrained correctly?"
  These are NOT equivalent. A covered port may still violate SDC-008/009/046;
  an exempt clock port is not "unconstrained data". The coverage engine only
  reports coverage status; correctness findings come from checker.py rules and
  are never suppressed by coverage. Conversely, a "100% coverage" summary means
  every object was intentionally constrained or exempt — it does NOT mean
  timing will close.

Statuses (never forced into a binary):
  CONSTRAINED            — referenced by a matching constraint
  UNCONSTRAINED          — provably no matching constraint (definite finding)
  PARTIALLY_CONSTRAINED  — bus: only some bits referenced (definite finding)
  EXEMPT                 — clock/reset/scan/test/constant/control port (no
                           I/O delay expected by design convention)
  UNKNOWN                — intent cannot be determined from SDC + structure
  NOT_APPLICABLE         — e.g. inout handled conservatively

Port classification (name heuristic is EVIDENCE ONLY, never authoritative):
  CLOCK / RESET / SCAN / TEST / CONTROL / CONSTANT / DATA / INOUT / UNKNOWN
  Structural evidence (which instance pins a port's net connects to) is
  stronger than a name hint; names are only a fallback. Uncertain classes stay
  UNKNOWN and are surfaced as coverage status, never as errors.

New diagnostics (design-aware ONLY, all warning level — safe, reproducible):
  SDC-064 — structurally-evidenced data INPUT with no set_input_delay
  SDC-065 — structurally-evidenced data OUTPUT with no set_output_delay
  SDC-066 — bus with provable partial bit coverage (some bits constrained)

Generated-clock / create_clock "dead target" and exception endpoint results are
reported as COVERAGE STATUS (machine-readable), not as error rules: a partial
netlist can legitimately produce zero structural fanout, and object resolution
never proves path existence.
"""

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple

from sdc_preprocess import preprocess_sdc
from design_context import (
    DesignContext,
    DesignPort,
    resolve_collection,
    _COLL_RE,
    _expand_collection_args,
    _split_bit_select,
    RESOLVED,
    EMPTY,
    UNDEFINED,
    UNSUPPORTED,
    classify_port_structure,
)


# ── Coverage statuses / port classes ─────────────────────────────────────────

CONSTRAINED = "CONSTRAINED"
UNCONSTRAINED = "UNCONSTRAINED"
PARTIALLY_CONSTRAINED = "PARTIALLY_CONSTRAINED"
EXEMPT = "EXEMPT"
UNKNOWN = "UNKNOWN"
NOT_APPLICABLE = "NOT_APPLICABLE"

PORT_STATUSES = (CONSTRAINED, UNCONSTRAINED, PARTIALLY_CONSTRAINED,
                 EXEMPT, UNKNOWN, NOT_APPLICABLE)

# Ports whose class makes I/O delay unnecessary by design convention. A port
# classified EXEMPT_CLASS is never reported unconstrained, but stays visible
# in the coverage summary so users can audit WHY it was exempt.
EXEMPT_CLASSES = ("CLOCK", "RESET", "SCAN", "TEST", "CONSTANT", "CONTROL", "INOUT")


# ── Per-object coverage records ───────────────────────────────────────────────

@dataclass
class PortCoverage:
    name: str
    direction: str                  # input | output | inout
    port_class: str                 # CLOCK / DATA / RESET / ... / UNKNOWN
    status: str                     # one of PORT_STATUSES
    evidence: str = ""              # why this classification / status
    line: int = 0                   # SDC line of the covering constraint (0=n/a)


@dataclass
class ClockCoverage:
    name: str
    period: Optional[float] = None
    target: str = ""                # resolved port/pin or "(virtual)"
    structurally_resolved: bool = False   # target exists in design context
    fanout: int = 0                 # structural loads on the target's net
    is_virtual: bool = False
    status: str = "DEFINED"         # DEFINED | RESOLVED | NO_STRUCTURAL_FANOUT


@dataclass
class ExceptionCoverage:
    command: str                    # set_false_path / set_multicycle_path / ...
    line: int = 0
    status: str = "PATH_EXISTENCE_UNKNOWN"
    # status ∈ {OBJECTS_RESOLVED, EMPTY_COLLECTION, PARTIALLY_RESOLVED,
    #           UNSUPPORTED, PATH_EXISTENCE_UNKNOWN}
    endpoints: List[str] = field(default_factory=list)


@dataclass
class ConstraintCoverage:
    inputs: List[PortCoverage] = field(default_factory=list)
    outputs: List[PortCoverage] = field(default_factory=list)
    clocks: List[ClockCoverage] = field(default_factory=list)
    exceptions: List[ExceptionCoverage] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)

    def summary(self) -> Dict[str, dict]:
        def _bucket(objs: List[PortCoverage]) -> dict:
            return {
                "total": len(objs),
                "constrained": sum(1 for o in objs if o.status == CONSTRAINED),
                "unconstrained": sum(1 for o in objs if o.status == UNCONSTRAINED),
                "partial": sum(1 for o in objs if o.status == PARTIALLY_CONSTRAINED),
                "exempt": sum(1 for o in objs if o.status == EXEMPT),
                "unknown": sum(1 for o in objs if o.status == UNKNOWN),
                "not_applicable": sum(1 for o in objs if o.status == NOT_APPLICABLE),
            }

        clk_defined = len(self.clocks)
        clk_resolved = sum(1 for c in self.clocks if c.structurally_resolved)
        clk_dead = sum(1 for c in self.clocks
                       if c.structurally_resolved and c.fanout == 0
                       and not c.is_virtual)
        exc_total = len(self.exceptions)
        exc_resolved = sum(1 for e in self.exceptions if e.status == "OBJECTS_RESOLVED")
        exc_empty = sum(1 for e in self.exceptions if e.status == "EMPTY_COLLECTION")
        exc_partial = sum(1 for e in self.exceptions if e.status == "PARTIALLY_RESOLVED")
        exc_unsupported = sum(1 for e in self.exceptions
                              if e.status in ("UNSUPPORTED", "PATH_EXISTENCE_UNKNOWN"))

        return {
            "inputs": _bucket(self.inputs),
            "outputs": _bucket(self.outputs),
            "clocks": {
                "defined": clk_defined,
                "structurally_resolved": clk_resolved,
                "no_structural_fanout": clk_dead,
            },
            "exceptions": {
                "total": exc_total,
                "objects_resolved": exc_resolved,
                "empty_collection": exc_empty,
                "partially_resolved": exc_partial,
                "unsupported_or_unknown": exc_unsupported,
            },
            # Coverage is NOT correctness: a fully covered design can still
            # have timing errors, and an exempt port is not "verified correct".
            "coverage_is_not_correctness": True,
        }

    def to_dict(self) -> dict:
        return {
            "inputs": [
                {"name": p.name, "direction": p.direction, "class": p.port_class,
                 "status": p.status, "evidence": p.evidence, "line": p.line}
                for p in self.inputs],
            "outputs": [
                {"name": p.name, "direction": p.direction, "class": p.port_class,
                 "status": p.status, "evidence": p.evidence, "line": p.line}
                for p in self.outputs],
            "clocks": [
                {"name": c.name, "period": c.period, "target": c.target,
                 "structurally_resolved": c.structurally_resolved,
                 "fanout": c.fanout, "is_virtual": c.is_virtual, "status": c.status}
                for c in self.clocks],
            "exceptions": [
                {"command": e.command, "line": e.line, "status": e.status,
                 "endpoints": e.endpoints}
                for e in self.exceptions],
            "notes": self.notes,
            "summary": self.summary(),
        }


# ── SDC constraint extraction ─────────────────────────────────────────────────

def _collect_delay_refs(logical, ctx: DesignContext) -> Dict[str, Set]:
    """Map port base name → set of bit specs referenced by I/O delays.

    Returns (input_refs, output_refs): {base: set(spec)} where spec ∈
    {None (whole), int, '*', (lo,hi)}. Wildcards are resolved against the
    design context so 'data_*' contributes every matching port (whole-bus).
    ``logical`` is the ALREADY-preprocessed logical-command list (preprocessed
    once by the caller — never re-preprocessed per port).
    """
    in_refs: Dict[str, Set] = {}
    out_refs: Dict[str, Set] = {}

    def _add(store: Dict[str, Set], kind: str, args: str) -> None:
        exprs = _expand_collection_args(args)
        for e in exprs:
            if any(ch in e for ch in '*?'):
                res = resolve_collection(kind, e, ctx)
                if res.kind == RESOLVED:
                    for m in res.matches:
                        store.setdefault(m, set()).add(None)
                continue
            base, spec = _split_bit_select(e)
            store.setdefault(base, set()).add(spec)

    for cmd in logical:
        t = cmd.text
        for m in _COLL_RE.finditer(t):
            kind = m.group(1).lower()
            if kind != "get_ports":
                continue
            args = m.group(2).strip()
            if re.match(r'set_input_delay', t):
                _add(in_refs, "get_ports", args)
            elif re.match(r'set_output_delay', t):
                _add(out_refs, "get_ports", args)
    return in_refs, out_refs


def _collect_case_targets(logical, ctx: DesignContext) -> Set[str]:
    """Port base names referenced by set_case_analysis.

    A port pinned by set_case_analysis has its timing intent defined (it is
    deliberately driven to a constant) — treated as covered, per SDC
    convention. Wildcards resolve against the design context.
    """
    targets: Set[str] = set()
    for cmd in logical:
        if not re.match(r'set_case_analysis', cmd.text):
            continue
        for m in _COLL_RE.finditer(cmd.text):
            kind = m.group(1).lower()
            if kind != "get_ports":
                continue
            args = m.group(2).strip()
            for e in _expand_collection_args(args):
                if any(ch in e for ch in '*?'):
                    res = resolve_collection(kind, e, ctx)
                    if res.kind == RESOLVED:
                        targets.update(res.matches)
                    continue
                base, _ = _split_bit_select(e)
                targets.add(base)
    return targets


def _bus_covered(specs: Set, port: DesignPort) -> Tuple[str, str]:
    """Given referenced bit-specs for a port, return (status, evidence).

    - Whole/star reference or full-range → CONSTRAINED
    - Bus with only some bits referenced → PARTIALLY_CONSTRAINED
    - No references handled by the caller (UNCONSTRAINED)
    """
    if not port.is_bus():
        return CONSTRAINED, "referenced by I/O delay"
    if None in specs or '*' in specs:
        return CONSTRAINED, "whole bus referenced by I/O delay"
    lo, hi = min(port.lsb, port.msb), max(port.lsb, port.msb)
    covered = set()
    for s in specs:
        if s is None or s == '*':
            return CONSTRAINED, "whole bus referenced by I/O delay"
        if isinstance(s, tuple):
            covered.update(range(max(s[0], lo), min(s[1], hi) + 1))
        elif isinstance(s, int):
            covered.add(s)
    total = hi - lo + 1
    if len(covered) >= total:
        return CONSTRAINED, "all bus bits referenced by I/O delay"
    if covered:
        return PARTIALLY_CONSTRAINED, \
            f"{len(covered)}/{total} bus bits covered (bits {sorted(covered)})"
    return UNCONSTRAINED, "no bus bit referenced by I/O delay"


# ── Timing-exception endpoint resolution ──────────────────────────────────────

_EXCEPTION_CMDS = ("set_false_path", "set_multicycle_path", "set_max_delay",
                   "set_min_delay")
_EXCEPTION_FLAGS = ("from", "to", "through", "rise_from", "rise_to",
                    "fall_from", "fall_to")


def _exception_status(args: str, kind: str, ctx: DesignContext) -> str:
    res = resolve_collection(kind, args, ctx)
    if res.kind == RESOLVED:
        return "OBJECTS_RESOLVED"
    if res.kind == EMPTY:
        return "EMPTY_COLLECTION"
    if res.kind == UNDEFINED:
        return "PARTIALLY_RESOLVED"   # explicit object missing elsewhere (SDC-055)
    return "UNSUPPORTED"


def _collect_exceptions(logical, ctx: DesignContext) -> List[ExceptionCoverage]:
    out: List[ExceptionCoverage] = []
    for cmd in logical:
        t = cmd.text.strip()
        cmd_name = t.split()[0] if t.split() else ""
        if cmd_name not in _EXCEPTION_CMDS:
            continue
        statuses = []
        endpoints = []
        for fl in _EXCEPTION_FLAGS:
            for m in re.finditer(r'-' + fl + r'\s+(\[[^\]]*\]|\S+)', t):
                ref = m.group(1)
                if not ref.startswith('['):
                    continue
                inner = ref[1:-1].strip()
                inner_m = re.match(r'(get_ports|get_pins|get_cells|get_nets|all_\w+)'
                                   r'\s*(.*)', inner)
                if not inner_m:
                    continue
                kind = inner_m.group(1).lower()
                args = inner_m.group(2).strip()
                endpoints.append(f"{kind} {args}")
                statuses.append(_exception_status(args, kind, ctx))
        if not statuses:
            statuses.append("PATH_EXISTENCE_UNKNOWN")
        # Worst non-resolved status wins; OBJECTS_RESOLVED only if all resolve.
        if "EMPTY_COLLECTION" in statuses:
            status = "EMPTY_COLLECTION"
        elif "PARTIALLY_RESOLVED" in statuses:
            status = "PARTIALLY_RESOLVED"
        elif "UNSUPPORTED" in statuses:
            status = "UNSUPPORTED"
        elif "OBJECTS_RESOLVED" in statuses:
            status = "OBJECTS_RESOLVED"
        else:
            status = "PATH_EXISTENCE_UNKNOWN"
        out.append(ExceptionCoverage(command=cmd_name, line=cmd.start_line,
                                     status=status, endpoints=endpoints))
    return out


# ── Clock structural coverage ─────────────────────────────────────────────────

def _collect_clocks(logical, ctx: DesignContext) -> List[ClockCoverage]:
    out: List[ClockCoverage] = []
    defined: Set[str] = set()
    for cmd in logical:
        t = cmd.text
        name_m = re.search(r'-name\s+(\S+)', t)
        name = name_m.group(1) if name_m else ""
        if re.match(r'create_generated_clock', t):
            src_m = re.search(r'-source\s+\[(get_ports|get_pins|get_cells|get_nets)'
                              r'\s+([^\]]*)\]', t)
            tgt_m = re.search(r'\[(get_ports|get_pins|get_cells|get_nets)\s+([^\]]*)\]\s*$', t)
            period = None
            per_m = re.search(r'-period\s+([\d.eE+-]+)', t)
            if per_m:
                try:
                    period = float(per_m.group(1))
                except ValueError:
                    period = None
            source = f"{src_m.group(1)} {src_m.group(2)}" if src_m else ""
            target = f"{tgt_m.group(1)} {tgt_m.group(2)}" if tgt_m else ""
            cc = ClockCoverage(name=name, period=period, target=target,
                               is_virtual=False)
            if src_m:
                kind = src_m.group(1).lower()
                res = resolve_collection(kind, src_m.group(2).strip(), ctx)
                if res.kind == RESOLVED:
                    cc.structurally_resolved = True
                    cc.fanout = _net_fanout(ctx, src_m.group(2).strip())
                    cc.status = ("RESOLVED" if cc.fanout or kind == "get_ports"
                                 else "NO_STRUCTURAL_FANOUT")
            out.append(cc)
            if name:
                defined.add(name)
            continue
        if re.match(r'create_clock', t):
            if 'get_ports' not in t and 'get_pins' not in t:
                out.append(ClockCoverage(name=name, is_virtual=True, status="DEFINED"))
                if name:
                    defined.add(name)
                continue
            per_m = re.search(r'-period\s+([\d.eE+-]+)', t)
            period = None
            if per_m:
                try:
                    period = float(per_m.group(1))
                except ValueError:
                    period = None
            tgt_m = re.search(r'\[(get_ports|get_pins|get_cells|get_nets)\s+([^\]]*)\]', t)
            kind = tgt_m.group(1).lower() if tgt_m else ""
            args = tgt_m.group(2).strip() if tgt_m else ""
            target = f"{kind} {args}" if kind else ""
            cc = ClockCoverage(name=name, period=period, target=target)
            if kind:
                res = resolve_collection(kind, args, ctx)
                if res.kind == RESOLVED:
                    cc.structurally_resolved = True
                    cc.fanout = _net_fanout(ctx, args)
                    cc.status = ("RESOLVED" if cc.fanout else
                                 "NO_STRUCTURAL_FANOUT")
            out.append(cc)
            if name:
                defined.add(name)
    return out


def _net_fanout(ctx: DesignContext, args: str) -> int:
    """Count structural loads on the net named by a resolved collection arg."""
    base, _ = _split_bit_select(args)
    return len(ctx.net_loads(base)) if base in ctx.net_pins else 0


# ── Top-level port coverage ───────────────────────────────────────────────────

def _analyze_ports(logical, ctx: DesignContext) -> Tuple[List[PortCoverage],
                                                         List[PortCoverage]]:
    in_refs, out_refs = _collect_delay_refs(logical, ctx)
    case_targets = _collect_case_targets(logical, ctx)
    # Line lookup: first SDC line containing each covering command pattern,
    # built ONCE so we never re-preprocess per port.
    line_idx = _build_line_index(logical)
    inputs: List[PortCoverage] = []
    outputs: List[PortCoverage] = []

    for pname, dp in ctx.ports.items():
        pclass, evidence = classify_port_structure(pname, ctx)
        line = 0

        if pclass in EXEMPT_CLASSES:
            # Bucket by direction so an exempt OUTPUT (e.g. a clock output
            # port) is counted with outputs, not inputs.
            rec = PortCoverage(pname, dp.direction, pclass, EXEMPT,
                               evidence=evidence)
            if dp.direction == "output":
                outputs.append(rec)
            else:
                inputs.append(rec)
            continue

        # set_case_analysis pins a port's intent → covered (per SDC convention).
        case_ev = f"set_case_analysis" if pname in case_targets else ""

        if dp.direction == "input":
            refs = in_refs.get(pname, set())
            if refs or case_ev:
                status, ev = _bus_covered(refs, dp) if refs else (CONSTRAINED, case_ev)
                line = _delay_line(line_idx, "set_input_delay", pname)
                inputs.append(PortCoverage(pname, dp.direction, pclass, status,
                                           evidence=ev, line=line))
            else:
                # UNKNOWN intent stays UNKNOWN (never inflated to a definite
                # UNCONSTRAINED) — only structurally-data ports are definite.
                status = UNCONSTRAINED if pclass == "DATA" else UNKNOWN
                inputs.append(PortCoverage(pname, dp.direction, pclass, status,
                                           evidence=evidence or "no set_input_delay"))
        elif dp.direction == "output":
            refs = out_refs.get(pname, set())
            if refs or case_ev:
                status, ev = _bus_covered(refs, dp) if refs else (CONSTRAINED, case_ev)
                line = _delay_line(line_idx, "set_output_delay", pname)
                outputs.append(PortCoverage(pname, dp.direction, pclass, status,
                                            evidence=ev, line=line))
            else:
                status = UNCONSTRAINED if pclass == "DATA" else UNKNOWN
                outputs.append(PortCoverage(pname, dp.direction, pclass, status,
                                            evidence=evidence or "no set_output_delay"))
        else:  # inout — conservative: NOT_APPLICABLE unless explicitly delayed
            refs = in_refs.get(pname, set()) | out_refs.get(pname, set())
            status = CONSTRAINED if (refs or case_ev) else NOT_APPLICABLE
            inputs.append(PortCoverage(pname, dp.direction, pclass, status,
                                       evidence="inout handled conservatively"))
    return inputs, outputs


def _build_line_index(logical) -> Dict[str, int]:
    """Map (command prefix, port name present) → first line. Built once."""
    idx: Dict[tuple, int] = {}
    for cmd in logical:
        t = cmd.text
        if not t.strip():
            continue
        for m in _COLL_RE.finditer(t):
            if m.group(1).lower() != "get_ports":
                continue
            for e in _expand_collection_args(m.group(2)):
                base, _ = _split_bit_select(e)
                key = (base,)
                if key not in idx:
                    idx[key] = cmd.start_line
    return idx


def _delay_line(line_idx: Dict[tuple, int], cmd: str, pname: str) -> int:
    return line_idx.get((pname,), 0)


# ── Public entry point ────────────────────────────────────────────────────────

def analyze_coverage(text: str, ctx: DesignContext) -> ConstraintCoverage:
    """Compute design-aware constraint coverage for ``text`` against ``ctx``.

    Design context REQUIRED. In SDC-only mode coverage cannot be computed —
    the checker simply does not call this (existing behavior unchanged). The
    SDC is preprocessed exactly ONCE; all sub-analyses share the logical list
    (no per-port or per-pass re-preprocessing).
    """
    logical = preprocess_sdc(text)
    inputs, outputs = _analyze_ports(logical, ctx)
    clocks = _collect_clocks(logical, ctx)
    exceptions = _collect_exceptions(logical, ctx)
    return ConstraintCoverage(inputs=inputs, outputs=outputs,
                              clocks=clocks, exceptions=exceptions)


# ── Findings (SDC-064..066) ───────────────────────────────────────────────────

def coverage_findings(text: str, ctx: DesignContext) -> List[dict]:
    """Return design-aware coverage findings as dicts {sev, code, msg, line}.

    Only DEFINITE, reproducible conditions produce findings:

      SDC-064 — structurally-evidenced data input without set_input_delay
      SDC-065 — structurally-evidenced data output without set_output_delay
      SDC-066 — provable partial bus coverage (some bits unconstrained)

    Anything uncertain stays a coverage status (never an error).
    """
    cov = analyze_coverage(text, ctx)
    findings: List[dict] = []
    for p in cov.inputs:
        if p.status == UNCONSTRAINED and p.port_class == "DATA":
            findings.append({
                "sev": "warning", "code": "SDC-064", "line": p.line,
                "msg": (f"input port '{p.name}' has structural data evidence "
                        f"({p.evidence or 'data pins'}) but no set_input_delay — "
                        f"external setup/hold at this boundary is unconstrained."),
            })
        elif p.status == PARTIALLY_CONSTRAINED:
            findings.append({
                "sev": "warning", "code": "SDC-066", "line": p.line,
                "msg": (f"input bus '{p.name}' is only partially constrained: "
                        f"{p.evidence}."),
            })
    for p in cov.outputs:
        if p.status == UNCONSTRAINED and p.port_class == "DATA":
            findings.append({
                "sev": "warning", "code": "SDC-065", "line": p.line,
                "msg": (f"output port '{p.name}' has structural data evidence "
                        f"({p.evidence or 'data pins'}) but no set_output_delay — "
                        f"external setup/hold at this boundary is unconstrained."),
            })
        elif p.status == PARTIALLY_CONSTRAINED:
            findings.append({
                "sev": "warning", "code": "SDC-066", "line": p.line,
                "msg": (f"output bus '{p.name}' is only partially constrained: "
                        f"{p.evidence}."),
            })
    return findings
