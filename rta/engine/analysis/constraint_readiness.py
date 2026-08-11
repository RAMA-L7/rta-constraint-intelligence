"""
SDC Constraint Readiness — handoff-quality aggregation layer (Phase 11).

Answers the question: *"Given everything the validator actually knows, is this
constraint set ready to hand to the next engineering stage (STA / implementation)?"*

This module is a CONSUMER, not a re-implementation. It never re-parses the SDC
and never re-derives SDC semantics. It aggregates evidence already produced by
the existing analysis engines:

    CheckResult.issues       — checker rule findings (error/warning/info, line/line2)
    CheckResult.scope        — analysis coverage / trust boundary (Phase 7)
    CheckResult.coverage     — design-aware constraint coverage (Phase 9)
    CheckResult.interactions — semantic constraint interactions (Phase 10)

What READY means (and does NOT mean):
  READY ≠ timing clean.  READY ≠ signoff complete.  READY ≠ "setup/hold pass".
  READY = "the constraint set satisfies the validator's supported,
  evidence-backed readiness criteria for the stated analysis mode."

Status model (categorical — NO fake numeric score):
  READY                 — no blockers, no review items, no advisories
  READY_WITH_ADVISORIES — no blockers, no review items; only info-level
                          duplicates/overrides/style advisories
  REVIEW_REQUIRED       — heuristic warnings, exception overlaps needing STA,
                          unconstrained data I/O, partial analysis, unsupported
                          constructs, unknown-intent coverage
  BLOCKED               — deterministic high-confidence problems (error rules,
                          definite contradictions, undefined required refs)
  INSUFFICIENT_CONTEXT  — an analysis engine failed / the readiness claim cannot
                          be made (never used merely because a netlist is absent)

Mode awareness: SDC-only analysis NEVER blocks for lacking a netlist. The
DESIGN_CONTEXT dimension reports INSUFFICIENT_CONTEXT (limited design
verification) but the overall status is computed from what IS analyzable, and
a ``limited_design_verification`` flag is set instead.

Every finding maps to an action category and a priority:
  P0 — blocks reliable constraint analysis
  P1 — likely handoff issue
  P2 — engineering review
  P3 — cleanup / advisory
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional


# ── Statuses ──────────────────────────────────────────────────────────────────
READY = "READY"
READY_WITH_ADVISORIES = "READY_WITH_ADVISORIES"
REVIEW_REQUIRED = "REVIEW_REQUIRED"
BLOCKED = "BLOCKED"
INSUFFICIENT_CONTEXT = "INSUFFICIENT_CONTEXT"

ALL_STATUSES = (READY, READY_WITH_ADVISORIES, REVIEW_REQUIRED, BLOCKED,
                INSUFFICIENT_CONTEXT)

# ── Dimensions ────────────────────────────────────────────────────────────────
DIM_CLOCKS = "CLOCKS"
DIM_IO = "I/O"
DIM_EXCEPTIONS = "EXCEPTIONS"
DIM_COVERAGE = "COVERAGE"
DIM_CONSISTENCY = "CONSISTENCY"
DIM_TRUST = "ANALYSIS_TRUST"
DIM_DESIGN = "DESIGN_CONTEXT"

DIMENSIONS = (DIM_CLOCKS, DIM_IO, DIM_EXCEPTIONS, DIM_COVERAGE,
              DIM_CONSISTENCY, DIM_TRUST, DIM_DESIGN)

# ── Explicit rule → tier mapping ─────────────────────────────────────────────
# Deterministic, high-confidence problems: BLOCK readiness.
# (These include error-severity rules plus warning-severity DEFINITE
# contradictions / undefined required references whose semantics justify a
# handoff block — never every warning.)
BLOCKER_RULES = {
    # Errors — no timing reference / broken definitions
    "SDC-001", "SDC-002", "SDC-003", "SDC-004", "SDC-005", "SDC-006",
    "SDC-008", "SDC-009", "SDC-010", "SDC-011",
    # Definite undefined clock references in I/O delays / generated clocks
    "SDC-046", "SDC-047",
    # Definite contradictions (warning severity, but provable)
    "SDC-049", "SDC-069",
    # Design-aware reference failures (only present with a netlist)
    "SDC-055", "SDC-056", "SDC-057", "SDC-058",
}

# SDC-007 is deliberately NOT a blocker: it is a NAME-BASED heuristic
# ("create_clock on likely data port") that can false-positive on legitimately
# named dedicated clock ports (e.g. data_clk). Per the no-false-blocker
# principle, a heuristic must not gate handoff — it stays REVIEW tier.
# SDC-048 (undefined clock inside set_clock_groups) is likewise REVIEW: it is
# a definite undefined reference but the group is advisory (a dead group entry
# does not break timing computation the way an I/O delay on a ghost clock
# does), so it requires review rather than blocking.

# Likely handoff issues / heuristic findings: engineering review.
REVIEW_RULES = {
    # Heuristic checker warnings (SDC-007 name-based clock-port heuristic included)
    "SDC-007",
    "SDC-020", "SDC-021", "SDC-022", "SDC-023", "SDC-024", "SDC-025",
    "SDC-026", "SDC-027", "SDC-028", "SDC-029", "SDC-030", "SDC-031",
    "SDC-032", "SDC-033", "SDC-034", "SDC-035", "SDC-036", "SDC-037",
    "SDC-040", "SDC-041", "SDC-042", "SDC-043", "SDC-044", "SDC-045",
    # Undefined clock in clock groups (definite ref, advisory impact)
    "SDC-048",
    # Design-aware coverage findings
    "SDC-059", "SDC-064", "SDC-065", "SDC-066",
    # Clock-relation warnings
    "SDC-060", "SDC-061", "SDC-062", "SDC-063",
    # Timing-exception overlap — needs STA
    "SDC-070",
}

# Info-level: cleanup / advisory, never block.
ADVISORY_RULES = {
    "SDC-067",  # exact duplicate
    "SDC-068",  # overridden constraint
    "SDC-100", "SDC-101", "SDC-102", "SDC-103", "SDC-104", "SDC-105",
    "SDC-106", "SDC-107", "SDC-108", "SDC-109", "SDC-110", "SDC-111",
    "SDC-112", "SDC-113", "SDC-114", "SDC-115", "SDC-116", "SDC-117",
    "SDC-118", "SDC-119", "SDC-120", "SDC-121", "SDC-122", "SDC-123",
    "SDC-124", "SDC-125", "SDC-126", "SDC-130", "SDC-131", "SDC-132",
}

# Dimension assignment (rule → dimension). Rules not listed here are assigned
# by an explicit fallback so nothing is silently dropped.
_RULE_DIMENSION: Dict[str, str] = {
    "SDC-001": DIM_CLOCKS, "SDC-002": DIM_CLOCKS, "SDC-003": DIM_CLOCKS,
    "SDC-004": DIM_CLOCKS, "SDC-007": DIM_CLOCKS, "SDC-010": DIM_CLOCKS,
    "SDC-046": DIM_CLOCKS, "SDC-047": DIM_CLOCKS, "SDC-048": DIM_CLOCKS,
    "SDC-060": DIM_CLOCKS, "SDC-061": DIM_CLOCKS, "SDC-062": DIM_CLOCKS,
    "SDC-063": DIM_CLOCKS,
    "SDC-005": DIM_IO, "SDC-006": DIM_IO, "SDC-008": DIM_IO,
    "SDC-009": DIM_IO, "SDC-028": DIM_IO, "SDC-029": DIM_IO,
    "SDC-059": DIM_IO, "SDC-064": DIM_IO, "SDC-065": DIM_IO,
    "SDC-066": DIM_IO,
    "SDC-020": DIM_EXCEPTIONS, "SDC-021": DIM_EXCEPTIONS,
    "SDC-037": DIM_EXCEPTIONS, "SDC-070": DIM_EXCEPTIONS,
    "SDC-011": DIM_CONSISTENCY, "SDC-031": DIM_CONSISTENCY,
    "SDC-049": DIM_CONSISTENCY, "SDC-067": DIM_CONSISTENCY,
    "SDC-068": DIM_CONSISTENCY, "SDC-069": DIM_CONSISTENCY,
    "SDC-055": DIM_DESIGN, "SDC-056": DIM_DESIGN, "SDC-057": DIM_DESIGN,
    "SDC-058": DIM_DESIGN,
}

# ── Action model ──────────────────────────────────────────────────────────────
_ACTION: Dict[str, str] = {
    "SDC-001": "DEFINE_CLOCK",
    "SDC-002": "FIX_CLOCK_DEFINITION",
    "SDC-003": "FIX_CLOCK_DEFINITION",
    "SDC-004": "FIX_CLOCK_DEFINITION",
    "SDC-005": "ADD_INPUT_CONSTRAINT",
    "SDC-006": "ADD_OUTPUT_CONSTRAINT",
    "SDC-007": "FIX_CLOCK_DEFINITION",
    "SDC-008": "FIX_CLOCK_REFERENCE",
    "SDC-009": "FIX_CLOCK_REFERENCE",
    "SDC-010": "FIX_CLOCK_REFERENCE",
    "SDC-011": "FIX_CASE_ANALYSIS",
    "SDC-020": "REVIEW_EXCEPTION",
    "SDC-021": "REVIEW_EXCEPTION",
    "SDC-022": "REVIEW_DELAY_VALUE",
    "SDC-023": "REVIEW_DELAY_VALUE",
    "SDC-024": "DECLARE_CLOCK_GROUPS",
    "SDC-025": "REVIEW_ELECTRICAL",
    "SDC-026": "REVIEW_DELAY_VALUE",
    "SDC-027": "REVIEW_EXCEPTION",
    "SDC-028": "ADD_INPUT_CONSTRAINT",
    "SDC-029": "ADD_OUTPUT_CONSTRAINT",
    "SDC-030": "REVIEW_CLOCK_MODEL",
    "SDC-031": "FIX_CLOCK_GROUPS",
    "SDC-032": "FIX_DERATE",
    "SDC-033": "FIX_DERATE",
    "SDC-034": "FIX_DATA_CHECK",
    "SDC-035": "REVIEW_DISABLE_TIMING",
    "SDC-036": "REVIEW_DISABLE_TIMING",
    "SDC-037": "REVIEW_EXCEPTION",
    "SDC-040": "FIX_DERATE",
    "SDC-041": "FIX_DERATE",
    "SDC-042": "FIX_DERATE",
    "SDC-043": "FIX_DERATE",
    "SDC-044": "FIX_OPERATING_CONDITIONS",
    "SDC-045": "REVIEW_DELAY_VALUE",
    "SDC-046": "FIX_CLOCK_REFERENCE",
    "SDC-047": "FIX_CLOCK_REFERENCE",
    "SDC-048": "FIX_CLOCK_REFERENCE",
    "SDC-049": "FIX_CASE_ANALYSIS",
    "SDC-055": "FIX_DESIGN_REFERENCE",
    "SDC-056": "FIX_DESIGN_REFERENCE",
    "SDC-057": "FIX_DESIGN_REFERENCE",
    "SDC-058": "FIX_DESIGN_REFERENCE",
    "SDC-059": "REVIEW_UNCONSTRAINED_PORT",
    "SDC-060": "REVIEW_CLOCK_RELATION",
    "SDC-061": "REVIEW_CLOCK_RELATION",
    "SDC-062": "REVIEW_CLOCK_RELATION",
    "SDC-063": "REVIEW_CLOCK_RELATION",
    "SDC-064": "ADD_INPUT_CONSTRAINT",
    "SDC-065": "ADD_OUTPUT_CONSTRAINT",
    "SDC-066": "ADD_INPUT_CONSTRAINT",
    "SDC-067": "REMOVE_OR_CONFIRM_DUPLICATE",
    "SDC-068": "REVIEW_OVERRIDE",
    "SDC-069": "FIX_DELAY_WINDOW",
    "SDC-070": "RUN_STA",
}

# Priority per action category (P0 blocks, P1 likely handoff, P2 review, P3 cleanup)
_ACTION_PRIORITY: Dict[str, str] = {
    "DEFINE_CLOCK": "P0",
    "FIX_CLOCK_DEFINITION": "P0",
    "FIX_CLOCK_REFERENCE": "P0",
    "FIX_CASE_ANALYSIS": "P0",
    "FIX_DELAY_WINDOW": "P0",
    "FIX_DESIGN_REFERENCE": "P0",
    "ADD_INPUT_CONSTRAINT": "P1",
    "ADD_OUTPUT_CONSTRAINT": "P1",
    "DECLARE_CLOCK_GROUPS": "P1",
    "REVIEW_UNCONSTRAINED_PORT": "P1",
    "REVIEW_EXCEPTION": "P2",
    "REVIEW_DELAY_VALUE": "P2",
    "REVIEW_ELECTRICAL": "P2",
    "REVIEW_CLOCK_MODEL": "P2",
    "FIX_CLOCK_GROUPS": "P2",
    "FIX_DERATE": "P2",
    "FIX_DATA_CHECK": "P2",
    "REVIEW_DISABLE_TIMING": "P2",
    "FIX_OPERATING_CONDITIONS": "P2",
    "REVIEW_CLOCK_RELATION": "P2",
    "RUN_STA": "P2",
    "REMOVE_OR_CONFIRM_DUPLICATE": "P3",
    "REVIEW_OVERRIDE": "P3",
}

# Fallback tier for issue codes not explicitly mapped above.
_DEFAULT_TIER = {"error": BLOCKED, "warning": REVIEW_REQUIRED, "info": READY_WITH_ADVISORIES}


# ── Evidence model ────────────────────────────────────────────────────────────

@dataclass
class ReadinessFinding:
    code: str
    severity: str
    msg: str
    line: int = 0
    line2: int = 0
    tier: str = ""                # BLOCKED | REVIEW_REQUIRED | READY_WITH_ADVISORIES
    dimension: str = ""
    action: str = ""
    priority: str = ""


@dataclass
class ReadinessEvidence:
    dimension: str
    status: str
    summary: str = ""
    findings: List[ReadinessFinding] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "dimension": self.dimension,
            "status": self.status,
            "summary": self.summary,
            "findings": [
                {"code": f.code, "severity": f.severity, "msg": f.msg,
                 "line": f.line, "line2": f.line2, "tier": f.tier,
                 "action": f.action, "priority": f.priority}
                for f in self.findings],
        }


@dataclass
class ReadinessResult:
    overall: str = INSUFFICIENT_CONTEXT
    mode: str = "SDC_ONLY"                     # SDC_ONLY | DESIGN_AWARE
    limited_design_verification: bool = False  # SDC-only + netlist-dependent refs
    engine_failed: bool = False                # an analysis engine crashed (SDC-140)
    dimensions: Dict[str, ReadinessEvidence] = field(default_factory=dict)
    blockers: List[dict] = field(default_factory=list)
    review_items: List[dict] = field(default_factory=list)
    advisories: List[dict] = field(default_factory=list)
    actions: List[dict] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)
    not_timing_signoff: bool = True

    def to_dict(self) -> dict:
        return {
            "overall": self.overall,
            "mode": self.mode,
            "limited_design_verification": self.limited_design_verification,
            "engine_failed": self.engine_failed,
            "dimensions": {
                d: ev.to_dict() for d, ev in self.dimensions.items()},
            "blockers": self.blockers,
            "review_items": self.review_items,
            "advisories": self.advisories,
            "actions": self.actions,
            "notes": self.notes,
            "not_timing_signoff": True,
        }


# ── Helpers ───────────────────────────────────────────────────────────────────

def _tier_for(code: str, severity: str) -> str:
    if code in BLOCKER_RULES:
        return BLOCKED
    if code in REVIEW_RULES:
        return REVIEW_REQUIRED
    if code in ADVISORY_RULES:
        return READY_WITH_ADVISORIES
    # Unmapped code → conservative default by severity.
    return _DEFAULT_TIER.get(severity, REVIEW_REQUIRED)


def _dimension_for(code: str) -> str:
    return _RULE_DIMENSION.get(code, DIM_TRUST)


def _action_for(code: str) -> str:
    return _ACTION.get(code, "REVIEW_FINDING")


def _priority_for(action: str) -> str:
    return _ACTION_PRIORITY.get(action, "P2")


def _status_of(tiers: List[str]) -> str:
    """Aggregate a set of finding tiers into one dimension/overall status."""
    if BLOCKED in tiers:
        return BLOCKED
    if REVIEW_REQUIRED in tiers:
        return REVIEW_REQUIRED
    if READY_WITH_ADVISORIES in tiers:
        return READY_WITH_ADVISORIES
    return READY


# ── Main entry point ──────────────────────────────────────────────────────────

def analyze_readiness(result) -> ReadinessResult:
    """Aggregate existing validator evidence into a readiness review.

    ``result`` is a ``CheckResult`` (from checker.check_sdc). Everything the
    readiness layer reports comes from that object — it never re-parses the SDC.
    """
    rd = ReadinessResult()

    issues = list(getattr(result, "issues", None) or [])
    scope = getattr(result, "scope", None) or {}
    coverage = getattr(result, "coverage", None) or {}
    interactions = getattr(result, "interactions", None) or {}

    # ── Analysis mode ─────────────────────────────────────────────────────────
    design_info = scope.get("design") or {}
    if design_info.get("analysis_mode") == "design_aware":
        rd.mode = "DESIGN_AWARE"

    # ── Engine failures → never READY (no false confidence) ───────────────────
    # If any analysis engine crashed (SDC-140), the readiness claim cannot be
    # made on full evidence. We cap overall at REVIEW_REQUIRED (the affected
    # dimension is unknown), never READY — the exact no-false-confidence
    # guarantee: "validator found no problems" must never read as "validator
    # checked everything" when an engine failed.
    engine_notes = []
    for item in getattr(result, "info", None) or []:
        if getattr(item, "code", "") == "SDC-140":
            engine_notes.append(getattr(item, "msg", ""))
    if engine_notes:
        rd.notes.extend([f"Analysis engine failure: {n}" for n in engine_notes])
        rd.notes.append(
            "One or more analysis engines failed — readiness is capped at "
            "REVIEW_REQUIRED because evidence is incomplete.")
        rd.engine_failed = True

    # No analyzable commands → the readiness claim cannot be established at all.
    if scope.get("commands_found", 0) == 0 and not issues:
        rd.overall = INSUFFICIENT_CONTEXT
        rd.notes.append("No SDC commands found — readiness cannot be established.")
        return rd

    # ── Classify every finding ────────────────────────────────────────────────
    findings: List[ReadinessFinding] = []
    for it in issues:
        code = getattr(it, "code", "") or ""
        sev = getattr(it, "sev", "info") or "info"
        findings.append(ReadinessFinding(
            code=code, severity=sev,
            msg=getattr(it, "msg", "") or "",
            line=getattr(it, "line", 0) or 0,
            line2=getattr(it, "line2", 0) or 0,
            tier=_tier_for(code, sev),
            dimension=_dimension_for(code),
            action=_action_for(code),
            priority=_priority_for(_action_for(code)),
        ))

    # Trust-boundary signals (not Issues — from the scope model).
    if scope.get("unsupported") or scope.get("tcl_execution_required"):
        n = scope.get("unsupported", 0) + scope.get("tcl_execution_required", 0)
        findings.append(ReadinessFinding(
            code="SCOPE-UNSUPPORTED", severity="warning",
            msg=f"{n} construct(s) outside the validator's analysis scope were "
                f"NOT checked (unsupported command or Tcl requiring execution).",
            tier=REVIEW_REQUIRED, dimension=DIM_TRUST,
            action="REVIEW_UNSUPPORTED_CONSTRUCT",
            priority=_priority_for("REVIEW_UNSUPPORTED_CONSTRUCT"),
        ))
    if scope.get("partially_analyzed"):
        findings.append(ReadinessFinding(
            code="SCOPE-PARTIAL", severity="warning",
            msg=f"{scope['partially_analyzed']} command(s) were only partially "
                f"analyzed (some options silently ignored).",
            tier=REVIEW_REQUIRED, dimension=DIM_TRUST,
            action="REVIEW_UNSUPPORTED_CONSTRUCT",
            priority=_priority_for("REVIEW_UNSUPPORTED_CONSTRUCT"),
        ))
    if scope.get("netlist_required") and rd.mode == "DESIGN_AWARE":
        findings.append(ReadinessFinding(
            code="SCOPE-NETLIST", severity="warning",
            msg=f"{scope['netlist_required']} reference(s) remain netlist-"
                f"dependent even with design context loaded (unsupported "
                f"collection expression).",
            tier=REVIEW_REQUIRED, dimension=DIM_DESIGN,
            action="PROVIDE_NETLIST",
            priority=_priority_for("PROVIDE_NETLIST"),
        ))

    # ── Coverage dimension (design-aware only) ────────────────────────────────
    cov_summ = coverage.get("summary") or {}
    if rd.mode == "DESIGN_AWARE" and cov_summ:
        b_in, b_out = cov_summ.get("inputs", {}), cov_summ.get("outputs", {})
        cov_tiers = []
        parts = []
        if b_in.get("unconstrained"):
            cov_tiers.append(REVIEW_REQUIRED)
            parts.append(f"{b_in['unconstrained']} input(s) unconstrained")
        if b_out.get("unconstrained"):
            cov_tiers.append(REVIEW_REQUIRED)
            parts.append(f"{b_out['unconstrained']} output(s) unconstrained")
        if b_in.get("partial") or b_out.get("partial"):
            cov_tiers.append(REVIEW_REQUIRED)
            parts.append(f"{b_in.get('partial',0)+b_out.get('partial',0)} partial-bus")
        if b_in.get("unknown") or b_out.get("unknown"):
            cov_tiers.append(REVIEW_REQUIRED)
            parts.append("unknown-intent ports present")
        if not cov_tiers:
            cov_tiers.append(READY)
        rd.dimensions[DIM_COVERAGE] = ReadinessEvidence(
            dimension=DIM_COVERAGE,
            status=_status_of(cov_tiers),
            summary="; ".join(parts) if parts else "all ports constrained or exempt",
        )
    else:
        rd.dimensions[DIM_COVERAGE] = ReadinessEvidence(
            dimension=DIM_COVERAGE,
            status="NOT_APPLICABLE",
            summary="coverage requires design context (SDC-only mode)",
        )

    # ── DESIGN_CONTEXT dimension ──────────────────────────────────────────────
    if rd.mode == "DESIGN_AWARE":
        dg_tiers = [f.tier for f in findings if f.dimension == DIM_DESIGN]
        top = design_info.get("top_module", "")
        if not top:
            dg_tiers.append(REVIEW_REQUIRED)
        rd.dimensions[DIM_DESIGN] = ReadinessEvidence(
            dimension=DIM_DESIGN,
            status=_status_of(dg_tiers) if dg_tiers else READY,
            summary=f"top={top}; design-aware validation active",
        )
    else:
        rd.dimensions[DIM_DESIGN] = ReadinessEvidence(
            dimension=DIM_DESIGN,
            status=INSUFFICIENT_CONTEXT,
            summary="design context not supplied — object existence and "
                    "coverage unverifiable (SDC-only mode)",
        )
        if scope.get("netlist_required"):
            rd.limited_design_verification = True

    # ── Per-dimension aggregation ─────────────────────────────────────────────
    by_dim: Dict[str, List[ReadinessFinding]] = {}
    for f in findings:
        by_dim.setdefault(f.dimension, []).append(f)
    for dim in DIMENSIONS:
        if dim in (DIM_COVERAGE, DIM_DESIGN):
            continue  # already set above
        dim_findings = by_dim.get(dim, [])
        tiers = [f.tier for f in dim_findings]
        summary = ""
        if dim_findings:
            summary = f"{len(dim_findings)} finding(s)"
        rd.dimensions[dim] = ReadinessEvidence(
            dimension=dim, status=_status_of(tiers),
            summary=summary, findings=sorted(dim_findings,
                                             key=lambda f: (f.tier, f.code, f.line)),
        )

    # ── Overall status ────────────────────────────────────────────────────────
    dim_statuses = [ev.status for ev in rd.dimensions.values()
                    if ev.status not in ("NOT_APPLICABLE", INSUFFICIENT_CONTEXT)]
    rd.overall = _status_of(dim_statuses)
    if rd.overall == READY and rd.limited_design_verification:
        rd.overall = READY_WITH_ADVISORIES
    # Engine failure caps the verdict — evidence is incomplete, so the claim
    # can never be READY (nor a clean ADVISORIES-only verdict).
    if rd.engine_failed and rd.overall not in (BLOCKED, REVIEW_REQUIRED):
        rd.overall = REVIEW_REQUIRED

    # ── Buckets (for UI / CLI / report) ───────────────────────────────────────
    def _bucketed(f: ReadinessFinding) -> dict:
        return {"code": f.code, "severity": f.severity, "msg": f.msg,
                "line": f.line, "line2": f.line2, "action": f.action,
                "priority": f.priority, "dimension": f.dimension}

    ordered = sorted(findings, key=lambda f: (f.priority, f.line, f.code))
    rd.blockers = [_bucketed(f) for f in ordered if f.tier == BLOCKED]
    rd.review_items = [_bucketed(f) for f in ordered if f.tier == REVIEW_REQUIRED]
    rd.advisories = [_bucketed(f) for f in ordered if f.tier == READY_WITH_ADVISORIES]

    # ── Actions (deduped, priority-ordered) ───────────────────────────────────
    seen_actions: Dict[str, dict] = {}
    for f in ordered:
        key = f.action
        if key not in seen_actions:
            seen_actions[key] = {
                "category": key, "priority": f.priority, "count": 0,
                "evidence": [], "detail": ""}
        seen_actions[key]["count"] += 1
        if len(seen_actions[key]["evidence"]) < 3:
            seen_actions[key]["evidence"].append(
                f"{f.code}" + (f" L{f.line}" if f.line else "")
                + (f"↔L{f.line2}" if f.line2 else ""))
    prio_order = {"P0": 0, "P1": 1, "P2": 2, "P3": 3}
    rd.actions = sorted(seen_actions.values(),
                        key=lambda a: (prio_order.get(a["priority"], 9),
                                       -a["count"], a["category"]))

    if rd.overall == READY:
        rd.notes.append(
            "No blockers, review items, or advisories — the constraint set "
            "satisfies the validator's supported readiness criteria for this mode.")
    if rd.mode == "SDC_ONLY" and rd.limited_design_verification:
        rd.notes.append(
            "SDC-only mode: object references (get_ports/get_pins/all_*) could "
            "not be verified against a design. Upload a netlist for design-aware "
            "readiness. This limitation does not by itself block readiness.")
    rd.notes.append(
        "This is a constraint-readiness review, NOT an STA timing signoff. "
        "READY does not mean setup/hold timing passes.")
    return rd
