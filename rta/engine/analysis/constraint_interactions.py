"""
Semantic constraint-interaction analysis (Phase 10).

Answers: *do multiple individually-valid constraints interact in a suspicious,
redundant, overridden, or contradictory way?*

This is NOT syntax checking, NOT object-existence checking, NOT coverage, and
NOT static timing analysis. It compares *normalized constraint records* and
applies provable SDC semantics:

  EXACT_DUPLICATE      — identical normalized command (same objects, options,
                         same value) issued again later
  SEMANTIC_DUPLICATE   — same intent expressed in equivalent form (e.g. 0.25
                         vs 2.5e-1 — handled by numeric normalization)
  REDUNDANT            — same effect, no harm (reported at info level)
  LEGAL_MULTIPLE       — intentionally independent constraints (-min/-max,
                         -rise/-fall, -setup/-hold, different clocks/ports,
                         -add_delay accumulation) — NEVER flagged
  OVERRIDE             — later command with the same identity but a different
                         value silently replaces the earlier one (SDC
                         replacement semantics for I/O delay / uncertainty /
                         electrical constraints)
  DEFINITE_CONFLICT    — provable contradiction (set_max_delay < set_min_delay
                         on provably identical endpoints)
  POSSIBLE_CONFLICT    — object overlap between timing exceptions; exact path
                         interaction requires STA (reported, never an error)
  AMBIGUOUS / STA_REQUIRED — cannot be decided statically; surfaced as trust
                         status, never as an error

PRINCIPLES
  - False positives are more dangerous than missing low-confidence conflicts.
    Only DEFINITE_CONFLICT is emitted at warning severity; everything else is
    info-level and clearly labeled.
  - Object overlap is NOT path overlap. We never claim two timing exceptions
    affect the same path unless the exact path interaction is provable.
  - Command ordering is preserved (index + start_line). A later command can
    override an earlier one; comparisons are never an unordered bag.
  - Existing rules own their territory: SDC-002 (duplicate clock names),
    SDC-049 (contradictory set_case_analysis), clock_relations (same-source
    physically-exclusive clocks). We do NOT double-report those.
  - Grouping/indexing keeps the common path near-linear; no all-pairs O(N²)
    comparison.
"""

import re
from dataclasses import dataclass, field
from typing import Dict, FrozenSet, List, Optional, Set, Tuple

from sdc_preprocess import preprocess_sdc, parse_number
from design_context import (
    DesignContext, resolve_collection, RESOLVED,
    _expand_collection_args, _split_bit_select,
)
from finding_identity import identity_from_interaction


# ── Interaction categories (never collapsed) ──────────────────────────────────
EXACT_DUPLICATE = "EXACT_DUPLICATE"
SEMANTIC_DUPLICATE = "SEMANTIC_DUPLICATE"
REDUNDANT = "REDUNDANT"
LEGAL_MULTIPLE = "LEGAL_MULTIPLE"
OVERRIDE = "OVERRIDE"
DEFINITE_CONFLICT = "DEFINITE_CONFLICT"
POSSIBLE_CONFLICT = "POSSIBLE_CONFLICT"
AMBIGUOUS = "AMBIGUOUS"
STA_REQUIRED = "STA_REQUIRED"

ALL_CATEGORIES = (EXACT_DUPLICATE, SEMANTIC_DUPLICATE, REDUNDANT, LEGAL_MULTIPLE,
                  OVERRIDE, DEFINITE_CONFLICT, POSSIBLE_CONFLICT, AMBIGUOUS,
                  STA_REQUIRED)

# ── Rule codes ────────────────────────────────────────────────────────────────
R_DUP = "SDC-067"      # exact duplicate constraint          (info)
R_OVR = "SDC-068"      # overridden constraint               (info)
R_CONF = "SDC-069"     # contradictory max/min delay         (warning)
R_EXC = "SDC-070"      # timing-exception interaction        (info, STA review)

_SEV = {R_DUP: "info", R_OVR: "info", R_CONF: "warning", R_EXC: "info"}

# Commands whose repeated same-identity constraints REPLACE (last wins).
_REPLACEMENT = {"set_input_delay", "set_output_delay", "set_clock_uncertainty",
                "set_load", "set_input_transition", "set_driving_cell"}

# Timing-exception commands (endpoint-level semantics).
_EXCEPTIONS = {"set_false_path", "set_multicycle_path", "set_max_delay",
               "set_min_delay"}

_COLL_ANY = re.compile(
    r'\[(get_ports|get_pins|get_cells|get_nets|get_clocks|'
    r'all_inputs|all_outputs|all_clocks|all_registers)\s*([^\]]*)\]')


# ── Normalized constraint record ──────────────────────────────────────────────

@dataclass
class ConstraintRecord:
    command: str
    index: int                 # command order (0-based)
    start_line: int
    end_line: int
    objects: FrozenSet[str] = frozenset()      # normalized object base names
    clock: str = ""                            # -clock reference (I/O delays)
    from_set: FrozenSet[str] = frozenset()     # exception endpoints
    to_set: FrozenSet[str] = frozenset()
    through_set: FrozenSet[str] = frozenset()
    min_max: str = ""                          # "min" | "max" | ""
    rise_fall: str = ""                        # "rise" | "fall" | ""
    setup_hold: str = ""                       # "setup" | "hold" | ""
    modes: FrozenSet[str] = frozenset()        # analysis modes the whole
                                               # COMMAND declares ({"max"},
                                               # {"max","min"}, {"setup"}...).
                                               # Two commands are exact
                                               # duplicates only when their
                                               # mode sets match — a later
                                               # command that re-states ONE
                                               # mode of a multi-mode command
                                               # is a partial re-specification,
                                               # not a duplicate.
    add_delay: bool = False
    datapath_only: bool = False
    value: Optional[float] = None
    value_str: str = ""
    raw: str = ""

    def identity(self) -> tuple:
        """Semantic identity WITHOUT value — members of one group differ only
        by value (→ duplicate/override) or are legal multiples."""
        return (self.command, self.objects, self.clock, self.min_max,
                self.rise_fall, self.setup_hold, self.add_delay,
                self.from_set, self.to_set, self.through_set,
                self.datapath_only)


# ── Collection helpers ────────────────────────────────────────────────────────

def _obj_token(kind: str, name: str) -> str:
    """Normalize a collection member to a comparable token."""
    base, spec = _split_bit_select(name)
    if spec is not None and spec != "*":
        return f"{kind}:{base}[{spec}]"
    return f"{kind}:{base}"


def _collection_members(expr: str) -> FrozenSet[str]:
    """Expand one collection expression into normalized object tokens.

    ``[get_ports {din[3:0]}]`` → {port:din[3:0], port:din[2:0]...} is NOT
    attempted — bit-range selectors are kept verbatim (comparing a range to
    its elements is not provable equality). Wildcards stay wildcard tokens.
    """
    m = _COLL_ANY.match(expr)
    if not m:
        return frozenset()
    kind = m.group(1)
    args = m.group(2).strip()
    if kind.startswith("all_"):
        return frozenset({kind.upper()})
    out = set()
    for a in _expand_collection_args(args):
        out.add(_obj_token(kind, a))
    return frozenset(out)


def _clock_ref(text: str) -> str:
    """Extract -clock reference: '-clock [get_clocks c]' → 'c'; '-clock c' → 'c'."""
    m = re.search(r'-clock\s+(\S+)', text)
    if not m:
        return ""
    ref = m.group(1)
    if ref.startswith("["):
        inner = ref[1:-1].strip()
        im = _COLL_ANY.match("[" + inner + "]")
        if im:
            parts = _expand_collection_args(im.group(2))
            return parts[0] if parts else ""
        return inner
    return ref


def _collection_tokens(text: str, kinds=("get_ports", "get_pins", "get_cells",
                                         "get_nets", "get_clocks",
                                         "all_inputs", "all_outputs",
                                         "all_clocks", "all_registers")) -> FrozenSet[str]:
    """All normalized object tokens referenced by collections in text."""
    out: Set[str] = set()
    for m in _COLL_ANY.finditer(text):
        if m.group(1) in kinds:
            out |= _collection_members(m.group(0))
    return frozenset(out)


def _resolve_wildcards(tokens: FrozenSet[str], ctx: Optional[DesignContext]) -> FrozenSet[str]:
    """Resolve wildcard collection tokens against design context.

    Without context (or for unresolvable patterns) wildcards stay wildcard
    tokens and are marked UNRESOLVABLE via a sentinel so downstream overlap
    logic refuses to claim provable equality/intersection.
    """
    if not ctx:
        return tokens
    out: Set[str] = set()
    for t in tokens:
        if "*" in t or "?" in t:
            try:
                kind, pat = t.split(":", 1)
                if not kind.startswith("get_"):
                    out.add(t)
                    continue
                res = resolve_collection(kind, pat, ctx)
                if res.kind == RESOLVED:
                    for name in res.matches:
                        out.add(f"{kind}:{name}")
                    continue
            except Exception:
                pass
            out.add(t)   # unresolvable → keep wildcard token (not provable)
        else:
            out.add(t)
    return frozenset(out)


# ── Record extraction ─────────────────────────────────────────────────────────

_NUM = r'[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?'


def _flag_values(text: str) -> Dict[str, float]:
    """'-max 2.0 -min 0.5' → {'max': 2.0, 'min': 0.5} (first occurrence wins)."""
    out: Dict[str, float] = {}
    for m in re.finditer(r'-(\w+)\s+(' + _NUM + r')', text):
        flag, val = m.group(1), m.group(2)
        if flag in ("max", "min", "setup", "hold", "rise", "fall"):
            out.setdefault(flag, float(val))
    return out


def _extract_io_record(cmd, idx: int, kinds) -> List[ConstraintRecord]:
    t = cmd.text.strip()
    name = t.split()[0] if t.split() else ""
    fv = _flag_values(t)
    objects = _collection_tokens(t, kinds)
    clock = _clock_ref(t)
    add = bool(re.search(r'-add_delay', t))
    rf = ""
    if re.search(r'-rise\b', t) and not re.search(r'-fall\b', t):
        rf = "rise"
    elif re.search(r'-fall\b', t) and not re.search(r'-rise\b', t):
        rf = "fall"
    modes = frozenset(
        m for m in ("max", "min", "rise", "fall")
        if re.search(r'-' + m + r'\b', t))

    # -max / -min may appear as flag-value pairs ('-max 2.0') OR as trailing
    # boolean selectors ('2.0 ... -max'). Both forms select the same analysis
    # mode, so both must normalize to the same record identity.
    has_max = bool(re.search(r'-max\b', t))
    has_min = bool(re.search(r'-min\b', t))
    bare_m = re.search(r'(?<![\-\w])(' + _NUM + r')',
                       re.sub(r'-(max|min)\s*', '', t))
    bare_val = float(bare_m.group(1)) if bare_m else None

    recs = []
    if has_max or has_min:
        if has_max:
            recs.append(ConstraintRecord(name, idx, cmd.start_line,
                                         cmd.end_line, objects=objects,
                                         clock=clock, min_max="max",
                                         rise_fall=rf, modes=modes,
                                         add_delay=add,
                                         value=fv.get("max", bare_val),
                                         value_str=str(fv.get("max", bare_val)),
                                         raw=t))
        if has_min:
            recs.append(ConstraintRecord(name, idx, cmd.start_line,
                                         cmd.end_line, objects=objects,
                                         clock=clock, min_max="min",
                                         rise_fall=rf, modes=modes,
                                         add_delay=add,
                                         value=fv.get("min", bare_val),
                                         value_str=str(fv.get("min", bare_val)),
                                         raw=t))
    else:
        recs.append(ConstraintRecord(name, idx, cmd.start_line,
                                     cmd.end_line, objects=objects,
                                     clock=clock, rise_fall=rf, modes=modes,
                                     add_delay=add, value=bare_val,
                                     value_str=str(bare_val) if bare_val is not None else "",
                                     raw=t))
    return recs


def _extract_uncertainty_record(cmd, idx: int) -> List[ConstraintRecord]:
    t = cmd.text.strip()
    name = t.split()[0] if t.split() else ""
    fv = _flag_values(t)
    clocks = _collection_tokens(t, ("get_clocks", "all_clocks"))
    frm = _clock_tokens_after(t, "from")
    to = _clock_tokens_after(t, "to")
    objects = frozenset(clocks | frm | to)
    rf = ""
    if re.search(r'-rise\b', t) and not re.search(r'-fall\b', t):
        rf = "rise"
    elif re.search(r'-fall\b', t) and not re.search(r'-rise\b', t):
        rf = "fall"
    modes = frozenset(
        m for m in ("setup", "hold", "rise", "fall")
        if re.search(r'-' + m + r'\b', t))
    recs = []
    for sh in ("setup", "hold"):
        if sh in fv:
            recs.append(ConstraintRecord(name, idx, cmd.start_line,
                                         cmd.end_line, objects=objects,
                                         setup_hold=sh, rise_fall=rf,
                                         modes=modes,
                                         value=fv[sh], value_str=str(fv[sh]),
                                         raw=t))
    if not recs:
        m = re.search(r'(?<![-\w])(' + _NUM + r')', t)
        recs.append(ConstraintRecord(name, idx, cmd.start_line,
                                     cmd.end_line, objects=objects,
                                     rise_fall=rf, modes=modes,
                                     value=float(m.group(1)) if m else None,
                                     value_str=m.group(1) if m else "", raw=t))
    return recs


def _clock_tokens_after(text: str, flag: str) -> FrozenSet[str]:
    m = re.search(r'-' + flag + r'\s+(\[[^\]]*\]|\S+)', text)
    if not m:
        return frozenset()
    ref = m.group(1)
    if ref.startswith("["):
        inner = ref[1:-1].strip()
        im = _COLL_ANY.match("[" + inner + "]")
        if im:
            return frozenset({f"clock:{n}" for n in _expand_collection_args(im.group(2))})
        return frozenset()
    return frozenset({f"clock:{ref}"})


def _extract_exception_record(cmd, idx: int, ctx: Optional[DesignContext]) -> ConstraintRecord:
    t = cmd.text.strip()
    name = t.split()[0] if t.split() else ""
    frm = _flag_endpoints(t, "from")
    to = _flag_endpoints(t, "to")
    thru = _flag_endpoints(t, "through")
    # rise_from / fall_from / rise_to / fall_to also collected (aggregated into
    # the same endpoint set — conservative: any edge overlap is a candidate).
    frm |= _flag_endpoints(t, "rise_from") | _flag_endpoints(t, "fall_from")
    to |= _flag_endpoints(t, "rise_to") | _flag_endpoints(t, "fall_to")
    frm = _resolve_wildcards(frm, ctx)
    to = _resolve_wildcards(to, ctx)
    thru = _resolve_wildcards(thru, ctx)
    fv = _flag_values(t)
    # -setup / -hold may be boolean switches ('set_multicycle_path 2 -setup')
    # OR flag-value pairs ('-setup 2'). Both forms select the analysis mode.
    sh = ""
    if re.search(r'-setup\b', t):
        sh = "setup"
    elif re.search(r'-hold\b', t):
        sh = "hold"
    modes = frozenset(m for m in ("setup", "hold")
                      if re.search(r'-' + m + r'\b', t))
    val = None
    if fv:
        val = fv.get("setup", fv.get("hold", fv.get("max", fv.get("min"))))
    else:
        m = re.search(r'(?<![-\w])(' + _NUM + r')', t)
        if m:
            val = float(m.group(1))
    return ConstraintRecord(name, idx, cmd.start_line, cmd.end_line,
                            from_set=frozenset(frm), to_set=frozenset(to),
                            through_set=frozenset(thru),
                            setup_hold=sh, modes=modes,
                            datapath_only=bool(re.search(r'-datapath_only', t)),
                            value=val, value_str=str(val) if val is not None else "",
                            raw=t)


def _flag_endpoints(text: str, flag: str) -> Set[str]:
    out: Set[str] = set()
    for m in re.finditer(r'-' + flag + r'\s+(\[[^\]]*\]|\S+)', text):
        ref = m.group(1)
        if ref.startswith("["):
            im = _COLL_ANY.match("[" + ref[1:-1].strip() + "]")
            if im:
                for token in _collection_members(im.group(0)):
                    out.add(token)
        else:
            out.add(ref)
    return out


def _extract_electrical_record(cmd, idx: int) -> ConstraintRecord:
    t = cmd.text.strip()
    name = t.split()[0] if t.split() else ""
    objects = _collection_tokens(t)
    m = re.search(r'(?<![-\w])(' + _NUM + r')', t)
    return ConstraintRecord(name, idx, cmd.start_line, cmd.end_line,
                            objects=objects,
                            value=float(m.group(1)) if m else None,
                            value_str=m.group(1) if m else "", raw=t)


def extract_records(text: str, ctx: Optional[DesignContext] = None) -> List[ConstraintRecord]:
    """Normalize the SDC into constraint records (preprocessed once)."""
    logical = preprocess_sdc(text)
    recs: List[ConstraintRecord] = []
    for idx, cmd in enumerate(logical):
        t = cmd.text.strip()
        if not t:
            continue
        name = t.split()[0] if t.split() else ""
        if name == "set_input_delay":
            recs.extend(_extract_io_record(cmd, idx, ("get_ports", "get_pins",
                                                      "all_inputs")))
        elif name == "set_output_delay":
            recs.extend(_extract_io_record(cmd, idx, ("get_ports", "get_pins",
                                                      "all_outputs")))
        elif name == "set_clock_uncertainty":
            recs.extend(_extract_uncertainty_record(cmd, idx))
        elif name in _EXCEPTIONS:
            recs.append(_extract_exception_record(cmd, idx, ctx))
        elif name in ("set_load", "set_input_transition", "set_driving_cell"):
            recs.append(_extract_electrical_record(cmd, idx))
    return recs


# ── Group analysis (duplicates / overrides) ───────────────────────────────────

def _analyze_groups(recs: List[ConstraintRecord]) -> List[dict]:
    """Group by semantic identity; detect exact duplicates and overrides.

    - add_delay records are legal accumulation → excluded from findings.
    - Exception command value overrides (e.g. two different multicycle N) are
      intentionally NOT flagged (high false-positive risk); only exact
      duplicates of exceptions are reported.
    - Records whose SOURCE COMMANDS declare different mode sets (e.g. one
      command carries -max -min, the next only -max) are never duplicates/
      overrides of each other — the later command is a partial
      re-specification, not a repeat.
    - Findings are deduped per (earlier index, later index, category) so a
      single duplicated multi-mode command pair yields one finding.
    """
    findings: List[dict] = []
    groups: Dict[tuple, List[ConstraintRecord]] = {}
    for r in recs:
        groups.setdefault(r.identity(), []).append(r)
    reported: Set[Tuple[int, int, str]] = set()

    def _emit(category, code, a, b, msg):
        pair = (min(a.index, b.index), max(a.index, b.index), category)
        if pair in reported:
            return
        reported.add(pair)
        findings.append(_mk_finding(category, code, a, b, msg))

    for _key, grp in groups.items():
        if len(grp) < 2:
            continue
        grp.sort(key=lambda r: r.index)
        non_add = [r for r in grp if not r.add_delay]
        if len(non_add) < 2:
            continue
        cmd = non_add[0].command
        is_exception = cmd in _EXCEPTIONS

        # Exact duplicates: identical value repeated AND the two source
        # commands declared the same mode set.
        first_by_val: Dict[float, ConstraintRecord] = {}
        for r in non_add:
            if r.value is None:
                if is_exception:
                    # endpoint-identical exception without numeric value
                    prev = first_by_val.get(None)
                    if prev is None:
                        first_by_val[None] = r
                    else:
                        if prev.modes != r.modes:
                            continue
                        _emit(EXACT_DUPLICATE, R_DUP, prev, r,
                              "identical constraint repeated on lines "
                              f"{prev.start_line} and {r.start_line} (redundant)")
                    continue
                continue
            prev = first_by_val.get(r.value)
            if prev is not None and prev.modes == r.modes:
                _emit(EXACT_DUPLICATE, R_DUP, prev, r,
                      f"identical {cmd} (value {r.value_str}) repeated on lines "
                      f"{prev.start_line} and {r.start_line} "
                      f"(redundant — the second is a no-op)")
            else:
                # (Re)anchor this value to the current record so a LATER
                # record with the same value+modes compares against the newest
                # same-mode command — never against a stale record from a
                # command with a different mode set.
                first_by_val[r.value] = r

        # Overrides: replacement-semantics commands, later value differs.
        # NOTE: mode-set equality is NOT required here. A later command that
        # re-states ONE mode of a multi-mode command with a different value
        # DOES override that mode (e.g. '-max 5.0 -min 1.5' then '-max 6.0'
        # replaces the max while the min survives). Only identical-value
        # restatements (duplicates) need the full mode-set match.
        if cmd in _REPLACEMENT and len({r.value for r in non_add}) > 1:
            last = non_add[-1]
            if last.value is None:
                last = None
            seen: Set[float] = set()
            for r in non_add[:-1]:
                if r.value is None or r.value in seen:
                    continue
                seen.add(r.value)
                if last is not None and r.value != last.value:
                    _emit(OVERRIDE, R_OVR, r, last,
                          f"{cmd} value {r.value_str} on line {r.start_line} is "
                          f"overridden by value {last.value_str} on line "
                          f"{last.start_line} (same objects/clock/edge, no "
                          f"-add_delay) — the earlier constraint is dead; "
                          f"verify this is intentional")
    return findings


def _mk_finding(category: str, code: str, a: ConstraintRecord, b: ConstraintRecord,
                msg: str) -> dict:
    # line = the LATER command (primary), line2 = the EARLIER (reference) —
    # matching the SDC-049 dual-line convention.
    if a.start_line > b.start_line:
        a, b = b, a
    # Structured, message-independent identity (Phase 13). OVERRIDE is
    # order-sensitive (earlier value replaced by later) → direction preserved.
    # Symmetric categories (duplicates, conflicts) canonicalize pair ordering.
    objects_a = a.objects | a.from_set | a.to_set | a.through_set
    objects_b = b.objects | b.from_set | b.to_set | b.through_set
    ident = identity_from_interaction(
        code, category, a.command,
        objects_a, objects_b,
        a.clock or b.clock,
        a.value_str or "", b.value_str or "",
        a.min_max or a.setup_hold or a.rise_fall,
        direction_preserved=(category == OVERRIDE),
    )
    return {
        "category": category,
        "code": code,
        "severity": _SEV[code],
        "msg": msg,
        "line": b.start_line,
        "line2": a.start_line,
        "command": a.command,
        "confidence": "HIGH",
        "index1": a.index,
        "index2": b.index,
        "identity": ident.to_dict(),
    }


# ── Cross-command checks ──────────────────────────────────────────────────────

def _provable(tokens: FrozenSet[str]) -> bool:
    """False if the set contains any wildcard/unresolvable token."""
    return all("*" not in t and "?" not in t for t in tokens)


def _max_min_conflicts(recs: List[ConstraintRecord]) -> List[dict]:
    """set_max_delay value < set_min_delay value on provably identical
    endpoints → DEFINITE_CONFLICT (impossible constraint, provable without
    STA)."""
    findings: List[dict] = []
    maxs = [r for r in recs if r.command == "set_max_delay"]
    mins = [r for r in recs if r.command == "set_min_delay"]
    if not maxs or not mins:
        return findings
    min_by_key: Dict[tuple, List[ConstraintRecord]] = {}
    for mn in mins:
        if not _provable(mn.from_set | mn.to_set | mn.through_set):
            continue
        min_by_key.setdefault((mn.from_set, mn.to_set, mn.through_set,
                               mn.datapath_only), []).append(mn)
    for mx in maxs:
        if not _provable(mx.from_set | mx.to_set | mx.through_set):
            continue
        key = (mx.from_set, mx.to_set, mx.through_set, mx.datapath_only)
        if mx.value is None:
            continue
        for mn in min_by_key.get(key, []):
            if mn.value is not None and mx.value < mn.value:
                findings.append(_mk_finding(
                    DEFINITE_CONFLICT, R_CONF, mn, mx,
                    f"set_max_delay {mx.value_str} < set_min_delay "
                    f"{mn.value_str} on provably identical endpoints "
                    f"(lines {mn.start_line} and {mx.start_line}) — the "
                    f"required window is impossible (max must be ≥ min)"))
    return findings


def _exception_interactions(recs: List[ConstraintRecord]) -> List[dict]:
    """false_path vs multicycle/max/min-delay with PROVABLE endpoint overlap.

    Object overlap is NOT path overlap — a false path and a multicycle path
    can legally target different edge/phase combinations of the same objects.
    We therefore report POSSIBLE_CONFLICT (info) with an explicit
    'requires STA / path analysis' statement, never an error.
    """
    findings: List[dict] = []
    fps = [r for r in recs if r.command == "set_false_path"]
    others = [r for r in recs if r.command in ("set_multicycle_path",
                                               "set_max_delay",
                                               "set_min_delay")]
    if not fps or not others:
        return findings

    # Index others by every endpoint object they mention, storing the record
    # itself so candidate iteration never re-scans the full list (near-linear).
    obj_to_others: Dict[str, List[ConstraintRecord]] = {}
    for o in others:
        eps = o.from_set | o.to_set | o.through_set
        if not _provable(eps) or not eps:
            continue
        for t in eps:
            obj_to_others.setdefault(t, []).append(o)

    reported: Set[Tuple[int, int, str]] = set()
    id_to_rec = {id(r): r for r in others}
    for fp in fps:
        if not _provable(fp.from_set | fp.to_set | fp.through_set):
            continue
        cands: Set[int] = set()
        for t in (fp.from_set | fp.to_set | fp.through_set):
            cands |= {id(o) for o in obj_to_others.get(t, [])}
        if not cands:
            continue
        for oid in cands:
            o = id_to_rec.get(oid)
            if o is None:
                continue
            # Path overlap requires start-side AND end-side intersection.
            start_over = bool(fp.from_set & o.from_set) or \
                         bool(fp.through_set & o.through_set)
            end_over = bool(fp.to_set & o.to_set) or \
                       bool(fp.through_set & o.through_set)
            if not (start_over and end_over):
                continue
            pair = (min(fp.index, o.index), max(fp.index, o.index), o.command)
            if pair in reported:
                continue
            reported.add(pair)
            # line = LATER command, line2 = EARLIER (SDC-049 convention).
            if fp.start_line > o.start_line:
                later, earlier = fp, o
            else:
                later, earlier = o, fp
            objects_fp = fp.from_set | fp.to_set | fp.through_set
            objects_o = o.from_set | o.to_set | o.through_set
            ident = identity_from_interaction(
                R_EXC, POSSIBLE_CONFLICT, fp.command,
                objects_fp, objects_o,
                "", fp.value_str or "", o.value_str or "",
                fp.setup_hold or o.setup_hold,
                direction_preserved=False,   # symmetric: canonicalize pair order
            )
            findings.append({
                "category": POSSIBLE_CONFLICT,
                "code": R_EXC,
                "severity": _SEV[R_EXC],
                "msg": (f"set_false_path (line {fp.start_line}) and "
                        f"{o.command} (line {o.start_line}) have overlapping "
                        f"endpoint objects. Exact path interaction is NOT "
                        f"provable statically — requires STA/path analysis "
                        f"to confirm whether the same timing path is affected."),
                "line": later.start_line,
                "line2": earlier.start_line,
                "command": fp.command,
                "confidence": "MEDIUM",
                "index1": fp.index,
                "index2": o.index,
                "identity": ident.to_dict(),
            })
    return findings


# ── Public entry point ────────────────────────────────────────────────────────

@dataclass
class InteractionAnalysis:
    findings: List[dict] = field(default_factory=list)
    constraints_analyzed: int = 0
    legal_multiples: int = 0

    def summary(self) -> dict:
        def _cnt(cat: str) -> int:
            return sum(1 for f in self.findings if f["category"] == cat)
        return {
            "constraints_analyzed": self.constraints_analyzed,
            "exact_duplicates": _cnt(EXACT_DUPLICATE),
            "semantic_duplicates": _cnt(SEMANTIC_DUPLICATE),
            "redundant": _cnt(REDUNDANT),
            "legal_multiples": self.legal_multiples,
            "overrides": _cnt(OVERRIDE),
            "definite_conflicts": _cnt(DEFINITE_CONFLICT),
            "possible_conflicts": _cnt(POSSIBLE_CONFLICT),
            "ambiguous": _cnt(AMBIGUOUS),
            "sta_required": _cnt(STA_REQUIRED),
            "confidence_is_not_correctness": True,
        }

    def to_dict(self) -> dict:
        return {
            "summary": self.summary(),
            "findings": [
                {k: f[k] for k in ("category", "code", "severity", "msg",
                                   "line", "line2", "command", "confidence",
                                   "identity") if k in f}
                for f in self.findings],
        }


def analyze_interactions(text: str, ctx: Optional[DesignContext] = None) -> InteractionAnalysis:
    """Run the semantic interaction analyzer over ``text``.

    Runs in SDC-only AND design-aware modes (object overlap is only claimed
    when provable; design context resolves wildcards where possible). Pure
    SDC-only behavior of existing rules is unaffected.
    """
    recs = extract_records(text, ctx)
    findings = _analyze_groups(recs)
    findings += _max_min_conflicts(recs)
    findings += _exception_interactions(recs)

    # Deterministic order: by line, then category.
    findings.sort(key=lambda f: (f["line"], f["line2"], f["code"]))

    # Legal-multiple accounting: groups with >1 non-add_delay record that
    # produced no finding are legitimate multiple constraints (min/max,
    # rise/fall, setup/hold, different clocks/ports, etc.).
    legal_groups = 0
    groups: Dict[tuple, List[ConstraintRecord]] = {}
    for r in recs:
        groups.setdefault(r.identity(), []).append(r)
    finding_pairs = {(f["index1"], f["index2"]) for f in findings}
    for grp in groups.values():
        if len(grp) >= 2:
            pairs = {(grp[i].index, grp[j].index)
                     for i in range(len(grp))
                     for j in range(i + 1, len(grp))}
            if not (pairs & finding_pairs):
                legal_groups += 1

    ia = InteractionAnalysis(findings=findings,
                            constraints_analyzed=len(recs),
                            legal_multiples=legal_groups)
    return ia
