"""
Clock Relation Analyzer
Parses clock definitions, infers correct relationships, and detects mismatches
in set_clock_groups constraints. Inspired by Ausdia's "Seemingly Simple Clock
Relations Quiz" — incorrect clock relations cause SI pessimism or masked timing paths.
"""

import re
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from itertools import combinations

from sdc_preprocess import preprocess_sdc, parse_collection, NUM_PATTERN


# ── Dataclasses ──────────────────────────────────────────────────────────────

@dataclass
class ClockDefCK:
    """A clock definition parsed from an SDC file."""
    name: str
    period: float
    source_port: str
    is_generated: bool = False
    master_clock: str = ""       # master clock name for generated clocks
    divide_by: int = 1
    is_virtual: bool = False
    source_node: str = ""        # -source object (port OR pin) the clock derives from
    gen_node: str = ""           # node this clock is generated/drives (pin or port)
    raw_text: str = ""


@dataclass
class ClockPair:
    """Inferred relationship between two clocks."""
    clock_a: str
    clock_b: str
    inferred_relation: str       # "asynchronous" | "synchronous" | "physically_exclusive" | "logically_exclusive"
    reason: str
    confidence: float = 1.0      # 0.0–1.0


@dataclass
class ClockMismatch:
    """A mismatch between inferred and specified clock relationships."""
    code: str                    # SDC-060..063
    severity: str                # "warning" | "info"
    clock_a: str
    clock_b: str
    specified: str               # what the SDC says
    expected: str                # what it should be
    msg: str


@dataclass
class RelationAnalysisResult:
    """Full analysis result.

    The mismatch collection is split by SEMANTIC category so every stats key
    equals the length of its collection (P1-2/P1-7 consistency contract):

    - ``mismatches``          — warning-severity real conflicts (SDC-060/061)
    - ``missing_constraints`` — info-severity SDC-062 (no set_clock_groups
                                declared for an async/exclusive pair)
    - ``advisories``          — info-severity SDC-063 (declared exclusion that
                                appears asynchronous — verify intentional)

    ``stats['mismatches'] == len(mismatches)``, ``stats['missing'] ==
    len(missing_constraints)``, ``stats['advisories'] == len(advisories)``.
    """
    clocks: List[ClockDefCK] = field(default_factory=list)
    pairs: List[ClockPair] = field(default_factory=list)
    existing_groups: List[Dict] = field(default_factory=list)
    mismatches: List[ClockMismatch] = field(default_factory=list)
    missing_constraints: List[ClockMismatch] = field(default_factory=list)
    advisories: List[ClockMismatch] = field(default_factory=list)
    stats: Dict[str, int] = field(default_factory=dict)


# ── Clock parsing ────────────────────────────────────────────────────────────

def parse_clocks_from_sdc(text: str) -> List[ClockDefCK]:
    """Extract all create_clock and create_generated_clock definitions."""
    clocks: List[ClockDefCK] = []

    # Primary clocks: create_clock -name NAME -period PERIOD [get_ports PORT]
    for m in re.finditer(
        r'create_clock\s+(-name\s+\S+\s+)?'
        r'(?:-period\s+(' + NUM_PATTERN + r')\s+)'
        r'(?:\[get_ports\s+(\S+)\])?'
        r'(.*)',
        text, re.MULTILINE
    ):
        name = ""
        name_m = re.search(r'-name\s+(\S+)', m.group(0))
        if name_m:
            name = name_m.group(1)
        period = float(m.group(2)) if m.group(2) else 5.0
        port = m.group(3) or ""
        extra = m.group(4) or ""
        # Skip if this is actually a generated clock line
        if 'create_generated_clock' in m.group(0):
            continue
        # Check for -add flag (multiple clocks on same port)
        has_add = '-add' in extra
        clocks.append(ClockDefCK(
            name=name,
            period=period,
            source_port=port,
            is_generated=False,
            source_node=port,
            gen_node=port,
            raw_text=m.group(0).strip(),
        ))

    # Generated clocks: parse each command then extract flags individually
    for m in re.finditer(
        r'create_generated_clock\s+(.+?)(?=\n\S|\Z)',
        text, re.DOTALL
    ):
        cmd = m.group(0)
        name_m = re.search(r'-name\s+(\S+)', cmd)
        name = name_m.group(1) if name_m else ""
        div_m = re.search(r'-divide_by\s+(\d+)', cmd)
        divide_by = int(div_m.group(1)) if div_m else 1
        mul_m = re.search(r'-multiply_by\s+(\d+)', cmd)
        multiply_by = int(mul_m.group(1)) if mul_m else None
        src_m = re.search(r'-source\s+\[get_ports\s+(\S+)\]', cmd)
        port = src_m.group(1) if src_m else ""
        master_m = re.search(r'-master_clock\s+(\S+)', cmd)
        master = master_m.group(1) if master_m else ""

        # -source object (port OR pin) — the node this clock derives from.
        # The generated output node is the last get_ports/get_pins object in the
        # command. Capturing both lets us link generated clocks through pins even
        # when -master_clock is omitted (e.g. div4's source is div2's output pin).
        objs = re.findall(r'\[(?:get_ports|get_pins|get_cells)\s+([^\]]+)\]', cmd)
        source_node = objs[0].strip().split()[0] if objs else ""
        gen_node = objs[-1].strip().split()[0] if objs else ""

        # Try to find master clock period
        master_period = 5.0
        for ck in clocks:
            if ck.name == master:
                master_period = ck.period
                break

        gen_period = master_period * divide_by if divide_by > 1 else master_period
        if multiply_by and multiply_by > 0:
            gen_period = master_period / multiply_by

        clocks.append(ClockDefCK(
            name=name,
            period=gen_period,
            source_port=port,
            is_generated=True,
            master_clock=master,
            divide_by=divide_by,
            source_node=source_node,
            gen_node=gen_node,
            raw_text=m.group(0).strip(),
        ))

    return clocks


# ── Relation inference ───────────────────────────────────────────────────────

def infer_relation(ck_a: ClockDefCK, ck_b: ClockDefCK,
                   clocks: Optional[List[ClockDefCK]] = None,
                   ancestor_sets: Optional[Dict[str, set]] = None) -> ClockPair:
    """Determine the correct relationship between two clocks.

    ``clocks`` is the full clock list used to resolve ancestor chains; it is
    optional for backward compatibility and defaults to the two clocks compared.
    ``ancestor_sets`` is an optional precomputed ``{clock_name: set_of_ancestors}``
    cache (Phase 4 perf: avoids O(N) ancestor scans per pair, making the full
    analysis O(N^2) instead of O(N^3) for large designs).
    """
    clocks = clocks if clocks is not None else [ck_a, ck_b]
    a, b = ck_a, ck_b

    if ancestor_sets is not None:
        anc_a = ancestor_sets.get(a.name, set())
        anc_b = ancestor_sets.get(b.name, set())
    else:
        anc_a = set(_get_ancestors(a, clocks))
        anc_b = set(_get_ancestors(b, clocks))

    # Rules 3/4 come first: two PRIMARY clocks on the SAME source port are
    # physically exclusive (only one active at a time). This is a stronger,
    # more specific signal than any ancestor link between same-port clocks.
    if (a.source_port and b.source_port and
            a.source_port == b.source_port and
            not a.is_generated and not b.is_generated):
        if a.period != b.period:
            return ClockPair(
                clock_a=a.name, clock_b=b.name,
                inferred_relation="physically_exclusive",
                reason=f"Both primary clocks on port {a.source_port} with different periods ({a.period} vs {b.period} ns) — only one active at a time",
            )
        return ClockPair(
            clock_a=a.name, clock_b=b.name,
            inferred_relation="physically_exclusive",
            reason=f"Identical primary clocks on port {a.source_port} — duplicates",
        )    # Rule 1: Parent-child / ancestor-descendant — one derives from the other
    if a.name in anc_b:
        return ClockPair(
            clock_a=a.name, clock_b=b.name,
            inferred_relation="synchronous",
            reason=f"{a.name} is an ancestor of {b.name} — synchronous (derived clock)",
        )
    if b.name in anc_a:
        return ClockPair(
            clock_a=a.name, clock_b=b.name,
            inferred_relation="synchronous",
            reason=f"{b.name} is an ancestor of {a.name} — synchronous (derived clock)",
        )

    # Rule 2: Shared common ancestor → same clock domain
    common = anc_a & anc_b
    if common:
        return ClockPair(
            clock_a=a.name, clock_b=b.name,
            inferred_relation="synchronous",
            reason=f"Share common ancestor clock(s): {', '.join(sorted(common))}",
        )

    # Rule 5: Different source ports, no common ancestor → asynchronous
    if a.source_port != b.source_port:
        return ClockPair(
            clock_a=a.name, clock_b=b.name,
            inferred_relation="asynchronous",
            reason=f"Different source ports ({a.source_port or '?'} vs {b.source_port or '?'}) with no common ancestor — no deterministic phase relationship",
        )

    # Default: asynchronous
    return ClockPair(
        clock_a=a.name, clock_b=b.name,
        inferred_relation="asynchronous",
        reason="Unable to determine a specific relationship — defaulting to asynchronous",
        confidence=0.5,
    )


def _get_ancestors(ck: ClockDefCK, clocks: List[ClockDefCK]) -> List[str]:
    """Return the ordered ancestor clock-name chain (parent, grandparent, ...).

    A clock's parent is resolved, in priority order:
      1. ``-master_clock`` name
      2. its ``-source`` node (port or pin) matching another clock's generated
         output node (``gen_node``) — links div4 → div2 via the shared pin
      3. its ``-source`` port matching another clock's source port (primary links)

    The chain is walked until no further ancestor is resolvable.
    """
    by_name = {c.name: c for c in clocks}
    chain: List[str] = []
    seen = set()
    cur = ck
    while True:
        nxt = None
        if cur.master_clock and cur.master_clock in by_name:
            nxt = by_name[cur.master_clock]
        elif cur.source_node:
            for pc in clocks:
                if (pc is not cur and pc.gen_node
                        and pc.gen_node == cur.source_node):
                    nxt = pc
                    break
        elif cur.source_port:
            for pc in clocks:
                if (pc is not cur and pc.source_port
                        and pc.source_port == cur.source_port):
                    nxt = pc
                    break
        if nxt is None or nxt.name in seen:
            break
        chain.append(nxt.name)
        seen.add(nxt.name)
        cur = nxt
    return chain


# ── Existing group parsing ───────────────────────────────────────────────────

def _parse_existing_groups(text: str) -> List[Dict]:
    """Extract set_clock_groups constraints."""
    # Join line continuations (\ + newline) so multi-line commands are single lines
    cleaned = re.sub(r'\\\s*\n\s*', ' ', text)
    groups = []
    for m in re.finditer(
        r'set_clock_groups\s+'
        r'(-asynchronous|-logically_exclusive|-physically_exclusive)\s+'
        r'(.+?)(?=\n\S|\Z)',
        cleaned, re.DOTALL
    ):
        group_type = m.group(1).lstrip('-')
        body = m.group(2)

        # Extract clock group lists — handle braced collections like
        # [get_clocks {clk_a clk_b}] (each brace group = one Tcl list).
        clock_groups = []
        for gm in re.finditer(r'-group\s+(\[[^\]]+\]|\{[^}]*\}|\S+)', body):
            clock_names = parse_collection(gm.group(1))
            if clock_names:
                clock_groups.append(clock_names)

        # Generate all pairs from this constraint
        specified_pairs = set()
        if len(clock_groups) >= 2:
            for gi, gj in combinations(range(len(clock_groups)), 2):
                for ca in clock_groups[gi]:
                    for cb in clock_groups[gj]:
                        pair_key = tuple(sorted([ca, cb]))
                        specified_pairs.add((pair_key, group_type))

        groups.append({
            'type': group_type,
            'clock_groups': clock_groups,
            'pairs': specified_pairs,
            'raw': m.group(0).strip(),
        })

    return groups


# ── Mismatch detection ──────────────────────────────────────────────────────

def _find_mismatches(
    pairs: List[ClockPair],
    existing_groups: List[Dict],
) -> List[ClockMismatch]:
    """Compare inferred vs. specified relationships and find mismatches."""
    mismatches: List[ClockMismatch] = []

    # Build a lookup: (clock_a, clock_b) → specified_type
    specified: Dict[Tuple[str, str], str] = {}
    for grp in existing_groups:
        for (pair_key, grp_type) in grp['pairs']:
            specified[pair_key] = grp_type

    # Also build reverse lookup for all clocks mentioned in groups
    all_specified_clocks = set()
    for grp in existing_groups:
        for cg in grp['clock_groups']:
            all_specified_clocks.update(cg)

    for pair in pairs:
        key = tuple(sorted([pair.clock_a, pair.clock_b]))

        if key in specified:
            specified_type = specified[key]
            if specified_type != pair.inferred_relation and not (
                pair.inferred_relation == "synchronous" and specified_type == "asynchronous"
            ):
                # Synchronous marked as asynchronous is generally OK (conservative)
                # Mismatch!
                if (pair.inferred_relation == "physically_exclusive" and
                        specified_type == "asynchronous"):
                    mismatches.append(ClockMismatch(
                        code="SDC-060",
                        severity="warning",
                        clock_a=pair.clock_a, clock_b=pair.clock_b,
                        specified=f"-{specified_type}",
                        expected=f"-physically_exclusive",
                        msg=(
                            f"Clocks {pair.clock_a}/{pair.clock_b} marked -asynchronous but "
                            f"should be -physically_exclusive: {pair.reason}. "
                            f"Using -asynchronous causes unnecessary Crosstalk/SI analysis on paths that can never exist."
                        ),
                    ))
                elif (pair.inferred_relation == "synchronous" and
                      specified_type in ("logically_exclusive", "physically_exclusive")):
                    mismatches.append(ClockMismatch(
                        code="SDC-061",
                        severity="warning",
                        clock_a=pair.clock_a, clock_b=pair.clock_b,
                        specified=f"-{specified_type}",
                        expected="synchronous (no exclusion needed)",
                        msg=(
                            f"Clocks {pair.clock_a}/{pair.clock_b} marked -{specified_type} but "
                            f"are actually synchronous: {pair.reason}. "
                            f"This masks real timing paths and leaves setup/hold un-optimized."
                        ),
                    ))
                elif (pair.inferred_relation == "asynchronous" and
                      specified_type in ("logically_exclusive", "physically_exclusive")):
                    mismatches.append(ClockMismatch(
                        code="SDC-063",
                        severity="info",
                        clock_a=pair.clock_a, clock_b=pair.clock_b,
                        specified=f"-{specified_type}",
                        expected=f"-asynchronous",
                        msg=(
                            f"Clocks {pair.clock_a}/{pair.clock_b} marked -{specified_type} but "
                            f"appear to be asynchronous: {pair.reason}. "
                            f"Verify this is intentional."
                        ),
                    ))
        else:
            # No constraint specified for this pair
            # Synchronous pairs don't need set_clock_groups — skip
            if pair.inferred_relation == "synchronous":
                continue
            if pair.inferred_relation in ("asynchronous", "physically_exclusive"):
                mismatches.append(ClockMismatch(
                    code="SDC-062",
                    severity="info",
                    clock_a=pair.clock_a, clock_b=pair.clock_b,
                    specified="(none)",
                    expected=f"-{pair.inferred_relation}",
                    msg=(
                        f"No set_clock_groups for {pair.clock_a}/{pair.clock_b}. "
                        f"Inferred: {pair.inferred_relation}. {pair.reason}."
                    ),
                ))

    return mismatches


# ── Main entry point ─────────────────────────────────────────────────────────

def analyze_clock_relations(text: str) -> RelationAnalysisResult:
    """Analyze all clock relations in an SDC file.

    1. Parse all clock definitions
    2. Infer correct relationship for every pair
    3. Parse existing set_clock_groups constraints
    4. Detect mismatches and missing constraints
    """
    # Normalize once: strip comments and join continuations so phantom clocks
    # from commented-out commands and split multi-line commands are handled
    # identically to single-line input.
    text = '\n'.join(c.text for c in preprocess_sdc(text))
    clocks = parse_clocks_from_sdc(text)
    existing_groups = _parse_existing_groups(text)

    # Precompute ancestor sets once per clock (Phase 4 perf: the old per-pair
    # ancestor scan made the full analysis O(N^3); cached lookups are O(N^2)).
    ancestor_sets = {c.name: set(_get_ancestors(c, clocks)) for c in clocks}

    # Generate all pairs
    pairs: List[ClockPair] = []
    for ca, cb in combinations(clocks, 2):
        pairs.append(infer_relation(ca, cb, clocks, ancestor_sets))

    # Find mismatches
    mismatches = _find_mismatches(pairs, existing_groups)

    # ── P1-2/P1-7: split findings into semantic categories so every stats key
    # equals the length of its collection. SDC-062 ("no set_clock_groups") is a
    # MISSING CONSTRAINT, not a mismatch — the CLI/API must never report
    # stats.mismatches == 0 while a list named `mismatches` holds 18 SDC-062s.
    warning_mm = [m for m in mismatches if m.severity == "warning"]
    missing_mm = [m for m in mismatches if m.code == "SDC-062"]
    advisory_mm = [m for m in mismatches if m.code == "SDC-063"]

    # Stats
    n_sync = sum(1 for p in pairs if p.inferred_relation == "synchronous")
    n_async = sum(1 for p in pairs if p.inferred_relation == "asynchronous")
    n_phy = sum(1 for p in pairs if p.inferred_relation == "physically_exclusive")
    n_log = sum(1 for p in pairs if p.inferred_relation == "logically_exclusive")

    stats = {
        "clocks": len(clocks),
        "pairs": len(pairs),
        "synchronous": n_sync,
        "asynchronous": n_async,
        "physically_exclusive": n_phy,
        "logically_exclusive": n_log,
        "mismatches": len(warning_mm),
        "missing": len(missing_mm),
        "advisories": len(advisory_mm),
        "constraints": len(existing_groups),
    }

    return RelationAnalysisResult(
        clocks=clocks,
        pairs=pairs,
        existing_groups=existing_groups,
        mismatches=warning_mm,
        missing_constraints=missing_mm,
        advisories=advisory_mm,
        stats=stats,
    )
