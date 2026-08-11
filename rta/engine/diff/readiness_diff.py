"""
SDC Readiness Diff, Baselines & CI Quality Gates (Phases 12 + 13).

Answers: *"What became better, worse, or unchanged compared with a known
baseline?"* and *"Should this SDC change pass an automated constraint-quality
gate?"*

Two different diff types exist and are kept separate:

  A. Constraint/content diff  — "what constraints changed?" (constraint_diff.py)
  B. Analysis/readiness diff  — "what engineering consequences changed?"
     (this module — compares readiness snapshots built from CheckResult)

Phase 13 (production hardening) adds to the Phase 12 foundation:

  - STRUCTURED FINDING IDENTITY (finding_identity.py). A finding's identity is
    now (identity_version, rule_id, finding_type, command, objects, clock,
    value, mode, edge, interaction_type, endpoint_signature) derived from the
    SDC COMMAND TEXT / interaction-engine semantic records — never from the
    human-readable message. Rewording an explanation can no longer turn
    UNCHANGED into RESOLVED+NEW.
  - IDENTITY STRENGTH. Findings either carry STRUCTURED identity (command- or
    record-derived) or LEGACY_NORMALIZED (message-derived fallback, honestly
    labeled — never falsely called structured).
  - SEVERITY-CHANGE SEMANTICS. Severity is part of the full key but excluded
    from the value-insensitive base key, so WARNING→ERROR is CHANGED, never
    RESOLVED+NEW.
  - SNAPSHOT SCHEMA v2. Adds identity_version, per-finding identity +
    strength, tool-capability metadata, fingerprint_version and migration
    metadata. v1 snapshots remain loadable and comparable via legacy keys
    (legacy normalized comparison), with migration status surfaced.
  - STRUCTURAL DESIGN FINGERPRINT v2. Derived from parsed design objects
    (ports incl. ranges, instances incl. module, nets, connectivity summary)
    — never raw source text — so formatting changes are invisible while real
    structural changes are detected.
  - BASELINE DEBT MODEL. existing/new/resolved debt (blockers, review,
    advisories, coverage, trust) is exposed so a gate can distinguish
    pre-existing debt from new debt.
  - CUSTOM POLICY ENGINE (policy_engine.py). Declarative, inert configuration
    data (JSON or YAML). Policies are data, never code: no eval/exec/imports.

Regression classification (never a single fake accuracy score):
  BLOCKING_REGRESSION  — new deterministic blocker appeared
  REVIEW_REGRESSION    — new review-tier finding (heuristic/needs-STA/etc.)
  ADVISORY_REGRESSION  — only new info/advisory findings
  NEUTRAL_CHANGE       — nothing meaningful changed
  IMPROVEMENT          — blockers/review items resolved, readiness improved
  CONTEXT_CHANGE       — analysis context changed (netlist/top/mode), so the
                         delta is not a pure SDC regression
  ENGINE_FAILURE       — analysis engines crashed; evidence is incomplete

CI gates (opt-in only — never active by default):
  BLOCKERS_ONLY            — fail if current analysis is BLOCKED
  NO_READINESS_REGRESSION  — fail only on blocking/review regressions vs baseline
  STRICT                   — fail on blockers or review regressions
  CUSTOM                   — declarative policy (policy_engine.py)

Exit-code contract (used ONLY when --gate is requested):
  0 = gate passed
  1 = analysis/readiness gate failed
  2 = invalid invocation/input (unknown policy, corrupt baseline, invalid policy)
  3 = analysis engine failure (SDC-140) — a gate must NEVER report PASS

Engine failure: if the current run's analysis engines crashed (SDC-140), the
gate can never report PASS even if no new blockers are found.

Baseline files are untrusted input: load_snapshot() validates schema, required
fields, types, and size. Nothing is ever executed from a baseline file.
"""

import hashlib
import json
import re
from collections import Counter
from typing import Dict, List, Optional, Tuple

from rules_registry import APP_VERSION
from constraint_readiness import (_tier_for, BLOCKED, REVIEW_REQUIRED,
                                  READY_WITH_ADVISORIES)
from finding_identity import (
    IDENTITY_VERSION, STRENGTH_STRUCTURED, STRENGTH_LEGACY,
    identity_from_dict, identity_simple, identity_legacy,
    identity_from_commands, identity_keys, make_identity_key,
    FT_SCOPE, FT_RULE,
)

# ── Snapshot schema ──────────────────────────────────────────────────────────
SCHEMA_VERSION = 2
ACCEPTED_SCHEMA_VERSIONS = (1, 2)
MAX_SNAPSHOT_BYTES = 20 * 1024 * 1024  # 20 MB safety cap
FINGERPRINT_VERSION = 2

# ── Baseline compatibility statuses ──────────────────────────────────────────
COMPATIBLE = "COMPATIBLE"
COMPATIBLE_WITH_CONTEXT_CHANGE = "COMPATIBLE_WITH_CONTEXT_CHANGE"
PARTIALLY_COMPARABLE = "PARTIALLY_COMPARABLE"
INCOMPATIBLE = "INCOMPATIBLE"

# ── Regression classes ───────────────────────────────────────────────────────
BLOCKING_REGRESSION = "BLOCKING_REGRESSION"
REVIEW_REGRESSION = "REVIEW_REGRESSION"
ADVISORY_REGRESSION = "ADVISORY_REGRESSION"
NEUTRAL_CHANGE = "NEUTRAL_CHANGE"
IMPROVEMENT = "IMPROVEMENT"
CONTEXT_CHANGE = "CONTEXT_CHANGE"
ENGINE_FAILURE = "ENGINE_FAILURE"

# ── Gate policies ────────────────────────────────────────────────────────────
POLICY_BLOCKERS_ONLY = "BLOCKERS_ONLY"
POLICY_NO_REGRESSION = "NO_READINESS_REGRESSION"
POLICY_STRICT = "STRICT"
POLICY_CUSTOM = "CUSTOM"
GATE_POLICIES = (POLICY_BLOCKERS_ONLY, POLICY_NO_REGRESSION, POLICY_STRICT, POLICY_CUSTOM)

# Exit codes
EXIT_PASS = 0
EXIT_GATE_FAILED = 1
EXIT_INVALID = 2
EXIT_ENGINE_FAILURE = 3

# Readiness status ordinal for transition semantics (BLOCKED is worst).
_STATUS_ORD = {
    "READY": 0,
    "READY_WITH_ADVISORIES": 1,
    "REVIEW_REQUIRED": 2,
    "BLOCKED": 3,
    "INSUFFICIENT_CONTEXT": None,   # not comparable — handled specially
    "NOT_APPLICABLE": None,
}

# Construct trust levels as produced by support_boundary (scope.constructs
# command → level). FULL == fully analyzed within scope; absent is treated as
# 0 (no trust problem) by _trust_delta.
_TRUST_ORD = {
    "FULL": 0,
    "NETLIST_REQUIRED": 1,
    "PARTIAL": 2,
    "TCL_EXECUTION_REQUIRED": 3,
    "UNSUPPORTED": 4,
    # Legacy aliases kept for safety.
    "VALIDATED": 0,
    "PARTIALLY_VALIDATED": 2,
    "NOT_VALIDATED": 5,
}


# ── Message normalization (LEGACY fallback identity only) ────────────────────
# NOTE: the legacy normalization is FROZEN to the exact Phase 12 behavior. v1
# baselines stored keys produced by this regex; changing it silently changes
# the legacy key space and breaks v1↔v2 migration (false NEW+RESOLVED). Do not
# edit _LINE_REF_RE / normalize_msg in future phases — structured identity is
# the forward path; legacy keys exist ONLY for Phase 12 baseline compatibility.
_NUM = r'[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?'
_NUM_RE = re.compile(r'(?<![\w.])(' + _NUM + r')(ns|ps|fs|us|µs|ms|MHz|GHz|Hz|V)?(?![A-Za-z0-9_.])')
_LINE_REF_RE = re.compile(r'\blines?\s+\d+(?:\s+and\s+\d+)?\b')
_BIT_SELECT_RE = re.compile(r'\[\s*[-+]?\d+(?:\s*:\s*[-+]?\d+)?\s*\]')


def _canon_num(num: str, unit: str, strip: bool) -> str:
    if strip:
        return "N" + (unit or "")
    try:
        return f"{float(num):g}" + (unit or "")
    except ValueError:
        return num + (unit or "")


def normalize_msg(msg: str, strip_numbers: bool = False) -> str:
    """Canonicalize a message for the LEGACY identity fallback.

    Used only when no structured identity can be derived (synthesized SCOPE-*
    signals and design-aware findings without command provenance). Never used
    as the preferred identity for command-derived findings.
    """
    s = " ".join(str(msg).split())
    s = _LINE_REF_RE.sub(" ", s)
    ranges: List[str] = []

    def _keep(m):
        ranges.append(m.group(0))
        return "\x00RANGE\x00"

    s = _BIT_SELECT_RE.sub(_keep, s)

    def _rep(m):
        return _canon_num(m.group(1), m.group(2) or "", strip_numbers)

    s = _NUM_RE.sub(_rep, s)
    for r in ranges:
        s = s.replace("\x00RANGE\x00", r, 1)
    return " ".join(s.split())


def finding_identity(code: str, severity: str, msg: str) -> Tuple[str, str]:
    """Legacy message-derived identity keys (kept for v1 snapshot compat and
    for callers that do not build structured identity)."""
    full = (code, severity, normalize_msg(msg, strip_numbers=False))
    base = (code, normalize_msg(msg, strip_numbers=True))
    return full, base


# ── Finding record (structured identity preferred) ───────────────────────────

def _finding_record(code, severity, msg, line=0, line2=0,
                    identity=None, logical=None, context="SDC_ONLY") -> dict:
    """Build a finding record with BOTH key spaces.

    - identity (dict) is preferred when the generating engine attached a
      structured identity (interactions / design-aware rules).
    - Otherwise the SDC command text at the finding's line(s) is used to
      derive STRUCTURED identity (message-independent).
    - Otherwise the LEGACY message-normalized identity is used, honestly
      labeled LEGACY_NORMALIZED.
    """
    if identity:
        try:
            ident = identity_from_dict(identity)
            full = list(ident.full_key()) + [severity]
            base = list(ident.base_key())
            strength = ident.strength
        except Exception:
            ident = None
    if not identity or ident is None:
        cmd_a = _cmd_at(logical, line)
        cmd_b = _cmd_at(logical, line2) if line2 else ""
        canonicalize = code not in ("SDC-068",)  # override preserves direction
        full, base, ident_dict, strength = make_identity_key(
            code, severity, msg, cmd_a, cmd_b,
            canonicalize_pair=canonicalize,
            context=context)
        identity = ident_dict
    # The LEGACY message-normalized key is stored on EVERY finding so a
    # schema-v1 baseline (whose full_id is the legacy key) can be compared
    # against a schema-v2 current snapshot in the SAME key space. Structured
    # identity is preferred for v2↔v2; the legacy key is the honest common
    # denominator for v1↔v2 migration comparisons.
    legacy_full, legacy_base = finding_identity(code, severity, msg)
    return {
        "code": code, "severity": severity, "msg": str(msg)[:240],
        "line": int(line or 0), "line2": int(line2 or 0),
        "full_id": list(full), "base_id": list(base),
        "legacy_full_id": list(legacy_full), "legacy_base_id": list(legacy_base),
        "identity": identity,
        "identity_strength": strength,
        "tier": _tier_for(code, severity),
    }


def _cmd_at(logical, line: int) -> str:
    """Return the SDC command text at physical ``line`` (original coords)."""
    if not logical or not line:
        return ""
    for c in logical:
        if c.start_line <= line <= c.end_line:
            return c.text
    return ""


def _design_mode(result) -> str:
    scope = getattr(result, "scope", None) or {}
    design = scope.get("design") or {}
    return "DESIGN_AWARE" if design.get("analysis_mode") == "design_aware" else "SDC_ONLY"


# ── Design identity ──────────────────────────────────────────────────────────

def design_fingerprint(context) -> str:
    """Deterministic, content-derived structural fingerprint (v2).

    Derived ONLY from the design's parsed structure (top module, module names,
    port names + directions + bit ranges, instance paths + module types, net
    names, connectivity counts) — never from raw source text — so identical
    designs always fingerprint identically and formatting changes are
    invisible. Any real structural change (added/removed port, bus width
    change, hierarchy change, top change) changes the fingerprint.
    """
    if context is None:
        return ""
    try:
        top = str(getattr(context, "top_module", "") or "")
        mods = sorted(str(m) for m in (getattr(context, "modules", None) or set()))
        ports = []
        for n, p in (getattr(context, "ports", None) or {}).items():
            rng = ""
            try:
                if p.is_bus():
                    rng = f":{p.msb}:{p.lsb}"
            except Exception:
                rng = ""
            ports.append(f"{n}:{p.direction}{rng}")
        insts = []
        for path, inst in (getattr(context, "instances", None) or {}).items():
            mod = getattr(inst, "module", "") or ""
            insts.append(f"{path}:{mod}")
        insts = sorted(insts)  # instance order is semantically irrelevant
        nets = sorted(getattr(context, "nets", None) or {})
        try:
            conn = getattr(context, "connectivity_counts", lambda: {})() or {}
        except Exception:
            conn = {}
        conn_s = ",".join(f"{k}={v}" for k, v in sorted(conn.items()))
        payload = "\n".join([top] + mods + sorted(ports) + insts + nets + [conn_s])
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]
    except Exception:
        return ""


# ── Snapshot construction ────────────────────────────────────────────────────

def build_snapshot(result, context=None, source_name: str = "", filename: str = "") -> dict:
    """Serialize a CheckResult (plus optional design context) into a snapshot.

    The snapshot captures normalized EVIDENCE (not rendered strings):
      - schema v2 + identity_version + fingerprint_version + capabilities
      - readiness verdict + per-dimension status
      - findings with structured identity (identity dict + strength) AND legacy
        keys (v1 compatibility)
      - coverage per-object status (design-aware mode)
      - analysis-trust per-construct level
      - interaction findings (Phase 10)
      - design-context metadata + structural fingerprint
      - engine-failure flag
    """
    rdy = getattr(result, "readiness", None) or {}
    scope = getattr(result, "scope", None) or {}
    cov = getattr(result, "coverage", None) or {}
    ints = getattr(result, "interactions", None) or {}
    logical = getattr(result, "logical", None) or []
    ctx_label = _design_mode(result)

    # Engine failure — from readiness flag OR SDC-140 info items.
    engine_failed = bool(rdy.get("engine_failed"))
    if not engine_failed:
        for item in getattr(result, "info", None) or []:
            if getattr(item, "code", "") == "SDC-140":
                engine_failed = True
                break

    findings = [_finding_record(getattr(i, "code", ""), getattr(i, "sev", "info"),
                                getattr(i, "msg", ""), getattr(i, "line", 0),
                                getattr(i, "line2", 0),
                                identity=getattr(i, "identity", None),
                                logical=logical, context=ctx_label)
                for i in (getattr(result, "issues", None) or [])]

    # Trust-boundary signals synthesized by the readiness layer (SCOPE-*).
    # These get a STRUCTURED identity (finding_type=ANALYSIS_SCOPE, value=count)
    # so a change in the number of unsupported constructs is CHANGED, not
    # NEW+RESOLVED — while rewording never affects them.
    if scope.get("unsupported") or scope.get("tcl_execution_required"):
        n = int(scope.get("unsupported", 0) or 0) + int(scope.get("tcl_execution_required", 0) or 0)
        ident = identity_simple("SCOPE-UNSUPPORTED", primary_object="scope",
                                finding_type=FT_SCOPE,
                                mode=f"{n}")
        findings.append(_finding_record(
            "SCOPE-UNSUPPORTED", "warning",
            f"{n} construct(s) outside the validator's analysis scope were NOT checked.",
            identity=ident.to_dict(), logical=logical, context=ctx_label))
    if scope.get("partially_analyzed"):
        m = int(scope.get("partially_analyzed", 0) or 0)
        ident = identity_simple("SCOPE-PARTIAL", primary_object="scope",
                                finding_type=FT_SCOPE, mode=f"{m}")
        findings.append(_finding_record(
            "SCOPE-PARTIAL", "warning",
            f"{m} command(s) only partially analyzed (some options silently ignored).",
            identity=ident.to_dict(), logical=logical, context=ctx_label))

    design = scope.get("design") or {}
    snap = {
        "schema_version": SCHEMA_VERSION,
        "identity_version": IDENTITY_VERSION,
        "tool_version": APP_VERSION,
        "source_name": source_name or filename,
        "created": "",
        "capabilities": {
            "structured_identity": True,
            "identity_version": IDENTITY_VERSION,
            "fingerprint_version": FINGERPRINT_VERSION,
            "design_aware": bool(design.get("analysis_mode") == "design_aware"),
            "interactions": True,
            "coverage": True,
            "readiness": True,
            "readiness_diff": True,
            "custom_policies": True,
        },
        "analysis": {
            "mode": "DESIGN_AWARE" if design.get("analysis_mode") == "design_aware" else "SDC_ONLY",
            "top_module": design.get("top_module", "") or "",
            "design_fingerprint": design_fingerprint(context),
            "fingerprint_version": FINGERPRINT_VERSION,
            "design_counts": {k: v for k, v in design.items()
                              if k not in ("analysis_mode", "top_module")},
            "commands_found": int(scope.get("commands_found", 0) or 0),
            "engine_failed": engine_failed,
        },
        "readiness": {
            "overall": rdy.get("overall", ""),
            "mode": rdy.get("mode", "SDC_ONLY"),
            "dimensions": {d: (ev.get("status", "") if isinstance(ev, dict) else "")
                           for d, ev in (rdy.get("dimensions") or {}).items()},
        },
        "findings": findings,
        "coverage": {
            "inputs": {p.get("name", ""): p.get("status", "")
                       for p in (cov.get("inputs") or [])},
            "outputs": {p.get("name", ""): p.get("status", "")
                        for p in (cov.get("outputs") or [])},
        },
        "scope": {
            "status": scope.get("status", "NOT_VALIDATED"),
            "constructs": {c.get("command", ""): c.get("level", "")
                           for c in (scope.get("constructs") or [])},
        },
        "interactions": [
            _finding_record(f.get("code", ""), f.get("severity", "info"),
                            f.get("msg", ""), f.get("line", 0), f.get("line2", 0),
                            identity=f.get("identity"), logical=logical,
                            context=ctx_label)
            for f in (ints.get("findings") or [])
        ],
        "migration": {"original_schema_version": SCHEMA_VERSION,
                      "current_schema_version": SCHEMA_VERSION,
                      "migration_status": "NATIVE"},
    }
    return snap


# ── Snapshot validation / loading (untrusted input) ─────────────────────────

_REQUIRED_KEYS_V2 = ("schema_version", "tool_version", "analysis", "readiness",
                     "findings", "coverage", "scope", "interactions")
_REQUIRED_KEYS_V1 = ("schema_version", "tool_version", "analysis", "readiness",
                     "findings", "coverage", "scope", "interactions")


def validate_snapshot(snap: dict) -> List[str]:
    """Return a list of schema/type errors. Empty list == valid.

    Accepts schema v1 AND v2 (v1 baselines remain usable). v1 findings carry
    no identity fields; v2 fields, when present, are type-checked. Unknown
    schema versions are rejected.
    """
    errs: List[str] = []
    if not isinstance(snap, dict):
        return ["snapshot is not a JSON object"]
    ver = snap.get("schema_version")
    if ver not in ACCEPTED_SCHEMA_VERSIONS:
        return [f"unsupported schema_version {ver} "
                f"(accepted: {', '.join(map(str, ACCEPTED_SCHEMA_VERSIONS))})"]
    required = _REQUIRED_KEYS_V1 if ver == 1 else _REQUIRED_KEYS_V2
    for k in required:
        if k not in snap:
            errs.append(f"missing required key '{k}'")
    for k in ("tool_version",):
        if k in snap and not isinstance(snap[k], str):
            errs.append(f"'{k}' must be a string")
    if ver == 2:
        iv = snap.get("identity_version")
        if not isinstance(iv, int):
            errs.append("'identity_version' must be an integer")
    an = snap.get("analysis")
    if not isinstance(an, dict):
        errs.append("'analysis' must be an object")
    else:
        for k in ("mode", "top_module", "design_fingerprint"):
            if k not in an:
                errs.append(f"analysis.{k} missing")
        if an.get("mode") not in ("SDC_ONLY", "DESIGN_AWARE"):
            errs.append(f"analysis.mode invalid: {an.get('mode')}")
        if not isinstance(an.get("engine_failed"), bool):
            errs.append("analysis.engine_failed must be boolean")
    if not isinstance(snap.get("findings"), list):
        errs.append("'findings' must be a list")
    if not isinstance(snap.get("readiness"), dict) or not isinstance(snap["readiness"].get("overall"), str):
        errs.append("'readiness.overall' must be a string")
    if not isinstance(snap.get("coverage"), dict):
        errs.append("'coverage' must be an object")
    if not isinstance(snap.get("scope"), dict):
        errs.append("'scope' must be an object")
    # Per-finding type checks (defensive — baselines are untrusted).
    if isinstance(snap.get("findings"), list):
        for i, f in enumerate(snap["findings"]):
            if not isinstance(f, dict):
                errs.append(f"findings[{i}] must be an object")
                continue
            if not isinstance(f.get("code", ""), str):
                errs.append(f"findings[{i}].code must be a string")
            if "identity" in f and f["identity"] is not None and \
                    not isinstance(f["identity"], dict):
                errs.append(f"findings[{i}].identity must be an object")
    return errs


def snapshot_migration_status(snap: dict) -> dict:
    """Return migration metadata for a loaded snapshot.

    NATIVE    — written by this schema version.
    MIGRATED  — older schema, compared via legacy normalized identity.
    INCOMPATIBLE — unknown schema (never loaded in the first place).
    """
    ver = snap.get("schema_version")
    if ver == SCHEMA_VERSION:
        status = "NATIVE"
    elif ver in ACCEPTED_SCHEMA_VERSIONS:
        status = "MIGRATED"
    else:
        status = "INCOMPATIBLE"
    return {"original_schema_version": ver,
            "current_schema_version": SCHEMA_VERSION,
            "migration_status": status}


def load_snapshot(text: str) -> Tuple[Optional[dict], List[str]]:
    """Parse + validate a snapshot from JSON text. Never executes anything.

    Returns (snapshot, errors). On any validation error the snapshot is None
    and the caller must fail safely (never silently trust malformed data).
    """
    if len(text.encode("utf-8")) > MAX_SNAPSHOT_BYTES:
        return None, [f"baseline file exceeds {MAX_SNAPSHOT_BYTES} bytes safety cap"]
    try:
        snap = json.loads(text)
    except json.JSONDecodeError as e:
        return None, [f"baseline is not valid JSON: {e}"]
    errs = validate_snapshot(snap)
    if errs:
        return None, errs
    # Attach migration metadata in memory (never rewrites the stored file).
    snap["migration"] = snapshot_migration_status(snap)
    return snap, []


def snapshot_to_json(snap: dict) -> str:
    return json.dumps(snap, indent=2)


# ── Baseline compatibility ───────────────────────────────────────────────────

def classify_compatibility(base: dict, cur: dict) -> Tuple[str, List[str]]:
    """Determine whether two snapshots are meaningfully comparable.

    Returns (status, reasons):
      COMPATIBLE                       — same schema/mode/design context
      COMPATIBLE_WITH_CONTEXT_CHANGE   — comparable, but the design context
                                         (netlist/top) or tool version differs;
                                         coverage/trust deltas may reflect that
      PARTIALLY_COMPARABLE             — analysis MODE changed (SDC-only ↔
                                         design-aware) OR the schema version
                                         differs (v1 baseline vs v2 current —
                                         compared via legacy normalized
                                         identity)
      INCOMPATIBLE                     — corrupt/unknown-schema baseline
    """
    reasons: List[str] = []
    be = validate_snapshot(base)
    ce = validate_snapshot(cur)
    if be or ce:
        return INCOMPATIBLE, (be or ce) + (["current"] * bool(ce))
    bv, cv = base.get("schema_version"), cur.get("schema_version")
    if bv != cv:
        # v1 baseline + v2 current: legacy normalized comparison (both
        # snapshots retain legacy full_id/base_id keys), never a silent
        # structured claim.
        return PARTIALLY_COMPARABLE, [
            f"schema version differs ({bv} vs {cv}) — compared via legacy "
            "normalized finding identity (structured identity unavailable in "
            "the older snapshot)"]
    ba, ca = base["analysis"], cur["analysis"]
    if ba.get("mode") != ca.get("mode"):
        return PARTIALLY_COMPARABLE, [
            f"analysis mode changed: {ba.get('mode')} → {ca.get('mode')} — "
            "coverage/trust deltas are only partially meaningful across modes"]
    if (ba.get("top_module") or "") != (ca.get("top_module") or ""):
        reasons.append(f"top module changed: {ba.get('top_module') or '?'} → "
                       f"{ca.get('top_module') or '?'}")
    if ba.get("design_fingerprint") != ca.get("design_fingerprint"):
        reasons.append("design context changed (netlist structure differs)")
    if (base.get("tool_version") or "") != (cur.get("tool_version") or ""):
        reasons.append(f"validator tool version differs: "
                       f"{base.get('tool_version')} vs {cur.get('tool_version')} — "
                       "baseline may be stale; consider regenerating it")
    if reasons:
        return COMPATIBLE_WITH_CONTEXT_CHANGE, reasons
    return COMPATIBLE, ["same analysis mode and design context"]


# ── Finding delta (multiset matching, semantic identity) ─────────────────────

def _key_of(record: dict, full: bool, legacy_only: bool) -> tuple:
    """Pick the matching key for a record.

    Structured keys are preferred unless legacy_only (v1 baseline involved) —
    then the LEGACY keys are used on BOTH sides so a migrated baseline remains
    comparable in the same key space:
      - v2 records expose legacy_full_id/legacy_base_id explicitly;
      - v1 records (Phase 12) store the legacy key directly in full_id/base_id.
    """
    if legacy_only:
        key = record.get("legacy_full_id") if full else record.get("legacy_base_id")
        if key is not None:
            return tuple(key)
        return tuple(record["full_id"] if full else record["base_id"])
    if record.get("identity_strength") == STRENGTH_STRUCTURED:
        key = record.get("full_id") if full else record.get("base_id")
        if key:
            return tuple(key)
    return tuple(record["full_id"] if full else record["base_id"])


def _multiset_delta(base: List[dict], cur: List[dict], legacy_only: bool = False):
    """Diff two finding lists; classify NEW / RESOLVED / UNCHANGED / CHANGED.

    Multiset semantics keep duplicate identical findings distinct.

    Algorithm:
      1. Match identical full keys (structured when available) → UNCHANGED.
      2. Leftover baseline occurrences → candidate RESOLVED.
      3. Leftover current occurrences → candidate NEW.
      4. Pair candidates that share a value-insensitive base key → CHANGED;
         remaining candidates are NEW / RESOLVED.
    """
    b_counts = Counter(_key_of(f, True, legacy_only) for f in base)
    c_counts = Counter(_key_of(f, True, legacy_only) for f in cur)
    matched = b_counts & c_counts
    unchanged = sum(matched.values())

    c_rem: List[dict] = []
    avail = dict(matched)
    for f in cur:
        key = _key_of(f, True, legacy_only)
        if avail.get(key, 0) > 0:
            avail[key] -= 1
        else:
            c_rem.append(f)

    b_rem: List[dict] = []
    avail = dict(matched)
    for f in base:
        key = _key_of(f, True, legacy_only)
        if avail.get(key, 0) > 0:
            avail[key] -= 1
        else:
            b_rem.append(f)

    c_by_base: Dict[tuple, List[dict]] = {}
    for f in c_rem:
        c_by_base.setdefault(_key_of(f, False, legacy_only), []).append(f)
    changed: List[Tuple[dict, dict]] = []
    new: List[dict] = []
    resolved: List[dict] = []
    for bf in b_rem:
        key = _key_of(bf, False, legacy_only)
        cands = c_by_base.get(key, [])
        if cands:
            changed.append((bf, cands.pop(0)))
        else:
            resolved.append(bf)
    for key, cands in c_by_base.items():
        new.extend(cands)
    return {"new": new, "resolved": resolved, "changed": changed,
            "unchanged": unchanged}


def _find_summary(findings: List[dict]) -> Dict[str, int]:
    out = {"error": 0, "warning": 0, "info": 0, "blocked": 0, "review": 0}
    for f in findings:
        sev = f.get("severity", "info")
        out[sev] = out.get(sev, 0) + 1
        if f.get("tier") == BLOCKED:
            out["blocked"] += 1
        elif f.get("tier") == REVIEW_REQUIRED:
            out["review"] += 1
    return out


# ── Debt model (Phase 13) ────────────────────────────────────────────────────

def _debt_buckets(findings: List[dict]) -> Dict[str, int]:
    out = {"blockers": 0, "review": 0, "advisories": 0, "coverage": 0, "trust": 0}
    for f in findings:
        tier = f.get("tier")
        code = f.get("code", "")
        if tier == BLOCKED:
            out["blockers"] += 1
        elif tier == REVIEW_REQUIRED:
            out["review"] += 1
        elif tier == READY_WITH_ADVISORIES:
            out["advisories"] += 1
        if code in DESIGN_CONTEXT_CODES:
            out["coverage"] += 1
        if code.startswith("SCOPE-"):
            out["trust"] += 1
    return out


# ── Coverage delta ───────────────────────────────────────────────────────────

_COV_WORSE = {"UNCONSTRAINED": 3, "UNKNOWN": 2, "PARTIALLY_CONSTRAINED": 1,
              "CONSTRAINED": 0, "EXEMPT": 0, "NOT_APPLICABLE": 0}


def _coverage_delta(b_in: dict, c_in: dict, b_out: dict, c_out: dict) -> dict:
    """Compare per-object coverage status. Object-level evidence, not % only."""
    def _diff(bucket_b: dict, bucket_c: dict) -> dict:
        names = set(bucket_b) | set(bucket_c)
        newly_unconstrained, newly_constrained, new_objects, removed_objects = [], [], [], []
        partial = []
        for n in sorted(names):
            bs, cs = bucket_b.get(n), bucket_c.get(n)
            if bs is None:
                new_objects.append(n)
                continue
            if cs is None:
                removed_objects.append(n)
                continue
            if bs == cs:
                continue
            if _COV_WORSE.get(cs, 0) > _COV_WORSE.get(bs, 0):
                newly_unconstrained.append(n)
            elif _COV_WORSE.get(cs, 0) < _COV_WORSE.get(bs, 0):
                newly_constrained.append(n)
            if cs == "PARTIALLY_CONSTRAINED" or bs == "PARTIALLY_CONSTRAINED":
                partial.append({"name": n, "before": bs, "after": cs})
        return {"newly_unconstrained": newly_unconstrained,
                "newly_constrained": newly_constrained,
                "new_objects": new_objects,
                "removed_objects": removed_objects,
                "partial_changes": partial}

    return {"inputs": _diff(b_in, c_in), "outputs": _diff(b_out, c_out)}


# ── Trust delta ──────────────────────────────────────────────────────────────

def _trust_delta(b_constructs: dict, c_constructs: dict) -> dict:
    """Per-construct level transitions (VALIDATED → PARTIAL = regression).

    A construct ABSENT from a revision carries NO trust problem — it is
    treated like VALIDATED (ord 0). Consequences:
      - adding an unsupported/Tcl construct   → trust REGRESSION (0 → 4)
      - removing an unsupported/Tcl construct → trust IMPROVEMENT (4 → 0)
      - adding/removing a fully-validated construct → neutral (0 → 0)
    """
    cmds = set(b_constructs) | set(c_constructs)
    transitions, regressions, improvements = [], [], []
    for cmd in sorted(cmds):
        b = b_constructs.get(cmd)
        c = c_constructs.get(cmd)
        if b == c:
            continue
        bo = 0 if b is None else _TRUST_ORD.get(b, 5)
        co = 0 if c is None else _TRUST_ORD.get(c, 5)
        entry = {"command": cmd, "from": b or "ABSENT", "to": c or "ABSENT"}
        transitions.append(entry)
        if co > bo:
            regressions.append(entry)
        elif co < bo:
            improvements.append(entry)
    return {"transitions": transitions, "regressions": regressions,
            "improvements": improvements}


# ── Interaction delta ────────────────────────────────────────────────────────

def _interaction_delta(b_int: List[dict], c_int: List[dict]) -> dict:
    d = _multiset_delta(b_int, c_int)
    return {
        "new": [{"code": f["code"], "category": f.get("identity", {}).get("interaction_type", ""),
                 "msg": f.get("msg", "")[:160], "line": f.get("line", 0)}
                for f in d["new"]],
        "resolved": [{"code": f["code"], "category": f.get("identity", {}).get("interaction_type", ""),
                      "msg": f.get("msg", "")[:160], "line": f.get("line", 0)}
                     for f in d["resolved"]],
        "unchanged": d["unchanged"],
    }


# ── Readiness delta ──────────────────────────────────────────────────────────

def _status_delta(a: str, cur: str) -> str:
    """Transition semantics between two status strings."""
    if a == cur:
        return "UNCHANGED"
    oa, ob = _STATUS_ORD.get(a), _STATUS_ORD.get(cur)
    if oa is None or ob is None:
        return "CONTEXT_CHANGE"
    if ob > oa:
        return "REGRESSION"
    return "IMPROVEMENT"


def _readiness_delta(b_rdy: dict, c_rdy: dict) -> dict:
    dims = {}
    keys = set(b_rdy.get("dimensions", {})) | set(c_rdy.get("dimensions", {}))
    for d in sorted(keys):
        a = b_rdy.get("dimensions", {}).get(d, "")
        b = c_rdy.get("dimensions", {}).get(d, "")
        dims[d] = {"baseline": a, "current": b, "delta": _status_delta(a, b)}
    return {
        "baseline": b_rdy.get("overall", ""),
        "current": c_rdy.get("overall", ""),
        "overall_delta": _status_delta(b_rdy.get("overall", ""),
                                       c_rdy.get("overall", "")),
        "dimensions": dims,
    }


# Design-context-dependent finding codes (SDC-055..059 object resolution,
# SDC-064..066 coverage). When the design context itself changed (netlist/top),
# new findings of these classes are attributable to the DESIGN change, not to
# the SDC revision — the diff must not blame the SDC for a design change.
DESIGN_CONTEXT_CODES = {
    "SDC-055", "SDC-056", "SDC-057", "SDC-058", "SDC-059",
    "SDC-064", "SDC-065", "SDC-066",
}


# ── Regression classification ────────────────────────────────────────────────

def classify_regression(diff: dict) -> str:
    """Classify the overall engineering consequence of the delta.

    Priority (most severe first):
      1. Engine failure — evidence incomplete, never a clean verdict.
      2. Design context changed AND every new finding is design-context-
         dependent → CONTEXT_CHANGE (the delta is explained by the netlist/
         top change, not the SDC revision).
      3. New deterministic blocker → BLOCKING_REGRESSION.
      4. New review-tier finding / newly-unconstrained existing object /
         trust regression → REVIEW_REGRESSION.
      5. Only new advisory/info findings → ADVISORY_REGRESSION.
      6. Improvements (blockers/review resolved, readiness improved) →
         IMPROVEMENT.
      7. Context changed with no SDC-side delta → CONTEXT_CHANGE.
      8. Otherwise → NEUTRAL_CHANGE.
    """
    if diff.get("engine_failed"):
        return ENGINE_FAILURE

    new = diff["findings"]["new"]
    resolved = diff["findings"]["resolved"]
    new_blocked = [f for f in new if f.get("tier") == BLOCKED]
    new_review = [f for f in new if f.get("tier") == REVIEW_REQUIRED]
    cov = diff.get("coverage") or {}
    cov_in, cov_out = cov.get("inputs", {}), cov.get("outputs", {})
    newly_unc = cov_in.get("newly_unconstrained", []) + cov_out.get("newly_unconstrained", [])
    trust_reg = diff.get("trust", {}).get("regressions", [])
    context_changed = (diff.get("compatibility", {}).get("status")
                       == COMPATIBLE_WITH_CONTEXT_CHANGE)

    if context_changed and new and not new_blocked:
        if all(f.get("code") in DESIGN_CONTEXT_CODES for f in new):
            return CONTEXT_CHANGE

    if new_blocked:
        return BLOCKING_REGRESSION
    if new_review or newly_unc or trust_reg:
        return REVIEW_REGRESSION
    if new and not resolved:
        return ADVISORY_REGRESSION

    rdy = diff.get("readiness", {})
    improved_rdy = rdy.get("overall_delta") == "IMPROVEMENT"
    any_resolved = bool(resolved) or bool(diff.get("interactions", {}).get("resolved"))
    if improved_rdy or any_resolved or (new and resolved):
        return IMPROVEMENT

    if context_changed:
        return CONTEXT_CHANGE

    return NEUTRAL_CHANGE


# ── Main diff entry point ────────────────────────────────────────────────────

def diff_snapshots(base: dict, cur: dict) -> dict:
    """Compare two readiness snapshots. Returns a machine-readable diff."""
    compat_status, compat_reasons = classify_compatibility(base, cur)
    # v1 baseline involved → compare on legacy normalized keys for BOTH sides.
    legacy_only = (base.get("schema_version") != SCHEMA_VERSION or
                   cur.get("schema_version") != SCHEMA_VERSION)
    fdelta = _multiset_delta(base.get("findings", []), cur.get("findings", []),
                             legacy_only=legacy_only)

    def _brief(f: dict) -> dict:
        return {"code": f.get("code", ""), "severity": f.get("severity", ""),
                "msg": f.get("msg", "")[:160], "line": f.get("line", 0),
                "line2": f.get("line2", 0), "tier": f.get("tier", ""),
                "identity": f.get("identity", {}),
                "identity_strength": f.get("identity_strength", "")}

    new_list = [_brief(f) for f in fdelta["new"]]
    resolved_list = [_brief(f) for f in fdelta["resolved"]]
    changed_list = [{"code": b.get("code", ""),
                     "before": _brief(b), "after": _brief(c)}
                    for b, c in fdelta["changed"]]

    cov = _coverage_delta(base.get("coverage", {}).get("inputs", {}),
                          cur.get("coverage", {}).get("inputs", {}),
                          base.get("coverage", {}).get("outputs", {}),
                          cur.get("coverage", {}).get("outputs", {}))
    trust = _trust_delta(base.get("scope", {}).get("constructs", {}),
                         cur.get("scope", {}).get("constructs", {}))
    ints = _interaction_delta(base.get("interactions", []),
                              cur.get("interactions", []))

    diff = {
        "compatibility": {"status": compat_status, "reasons": compat_reasons,
                          "legacy_normalized": legacy_only,
                          "migration": {
                              "baseline": base.get("migration", {}).get("migration_status", "NATIVE"),
                              "current": cur.get("migration", {}).get("migration_status", "NATIVE")}},
        "engine_failed": bool(cur.get("analysis", {}).get("engine_failed")),
        "readiness": _readiness_delta(base.get("readiness", {}),
                                      cur.get("readiness", {})),
        "findings": {
            "new": new_list, "resolved": resolved_list, "changed": changed_list,
            "unchanged": fdelta["unchanged"],
            "summary": {
                "baseline": _find_summary(base.get("findings", [])),
                "current": _find_summary(cur.get("findings", [])),
            },
            "new_blockers": [f for f in new_list if f.get("tier") == BLOCKED],
            "resolved_blockers": [f for f in resolved_list if f.get("tier") == BLOCKED],
            "new_review": [f for f in new_list if f.get("tier") == REVIEW_REQUIRED],
            "resolved_review": [f for f in resolved_list if f.get("tier") == REVIEW_REQUIRED],
        },
        "debt": {
            "existing": _debt_buckets(base.get("findings", [])),
            "new_debt": _debt_buckets(new_list),
            "resolved_debt": _debt_buckets(resolved_list),
        },
        "coverage": cov,
        "trust": trust,
        "interactions": ints,
        "design": {
            "baseline_top": base.get("analysis", {}).get("top_module", ""),
            "current_top": cur.get("analysis", {}).get("top_module", ""),
            "context_changed": (base.get("analysis", {}).get("design_fingerprint")
                                != cur.get("analysis", {}).get("design_fingerprint")),
        },
    }
    diff["classification"] = classify_regression(diff)
    return diff


# ── CI quality gates ─────────────────────────────────────────────────────────

def evaluate_gate(policy: str, base: Optional[dict], cur: dict, diff: dict,
                  policy_data: Optional[dict] = None) -> dict:
    """Evaluate a CI gate policy against baseline + current + diff.

    Returns: {"policy", "result": PASS|FAIL|NOT_CONFIGURED, "exit_code",
              "reasons": [...], "policy_used": bool}

    Rules:
      - Engine failure in the current run → FAIL, exit 3 (never PASS).
      - Incompatible/corrupt baseline → FAIL, exit 2.
      - BLOCKERS_ONLY            — FAIL if current readiness is BLOCKED
                                   (works without a baseline).
      - NO_READINESS_REGRESSION  — FAIL only if the revision introduces a
                                   blocking or review regression vs baseline.
      - STRICT                   — FAIL on blockers or review regressions.
      - CUSTOM                   — declarative policy evaluated by the
                                   policy engine (policy_data required).
    """
    cur_engine_failed = bool(cur.get("analysis", {}).get("engine_failed"))
    if cur_engine_failed:
        return {"policy": policy, "result": "FAIL", "exit_code": EXIT_ENGINE_FAILURE,
                "policy_used": True,
                "reasons": ["analysis engine failed (SDC-140) — a gate can never "
                            "report PASS on incomplete evidence"]}

    if policy not in GATE_POLICIES:
        return {"policy": policy, "result": "NOT_CONFIGURED",
                "exit_code": EXIT_INVALID, "policy_used": False,
                "reasons": [f"unknown gate policy '{policy}'"]}

    if policy == POLICY_CUSTOM:
        from policy_engine import evaluate_policy, POLICY_NOT_CONFIGURED
        if policy_data is None:
            return {"policy": policy, "result": POLICY_NOT_CONFIGURED,
                    "exit_code": EXIT_INVALID, "policy_used": False,
                    "reasons": ["CUSTOM policy requires a policy file "
                                "(--gate-policy FILE)"]}
        return evaluate_policy(policy_data, base, cur, diff)

    reasons: List[str] = []
    failed = False

    if policy == POLICY_BLOCKERS_ONLY:
        overall = cur.get("readiness", {}).get("overall", "")
        if overall == BLOCKED:
            failed = True
            reasons.append(f"current analysis is BLOCKED "
                           f"({len(cur.get('readiness', {}).get('dimensions', {}))} "
                           f"dimensions evaluated)")
        else:
            reasons.append(f"current analysis is {overall or 'N/A'} — no blockers")
        return {"policy": policy, "result": "FAIL" if failed else "PASS",
                "exit_code": EXIT_GATE_FAILED if failed else EXIT_PASS,
                "policy_used": True, "reasons": reasons}

    if base is None:
        return {"policy": policy, "result": "FAIL", "exit_code": EXIT_INVALID,
                "policy_used": True,
                "reasons": [f"{policy} requires a baseline snapshot (--baseline)"]}

    compat = diff.get("compatibility", {}).get("status")
    if compat == INCOMPATIBLE:
        return {"policy": policy, "result": "FAIL", "exit_code": EXIT_INVALID,
                "policy_used": True,
                "reasons": ["baseline is incompatible with current analysis — "
                            "refusing to gate on an invalid comparison"]}

    classification = diff.get("classification", NEUTRAL_CHANGE)

    if policy == POLICY_NO_REGRESSION:
        if classification in (BLOCKING_REGRESSION, REVIEW_REGRESSION):
            failed = True
            reasons.append(f"revision introduces a {classification} vs baseline")
        else:
            reasons.append(f"no blocking/review regression detected "
                           f"(classification: {classification})")

    elif policy == POLICY_STRICT:
        cur_rdy = cur.get("readiness", {}).get("overall", "")
        if classification in (BLOCKING_REGRESSION, REVIEW_REGRESSION):
            failed = True
            reasons.append(f"revision introduces a {classification} vs baseline")
        elif cur_rdy == BLOCKED:
            failed = True
            reasons.append("current analysis is BLOCKED")
        else:
            reasons.append("no blockers and no review regressions detected")

    return {"policy": policy, "result": "FAIL" if failed else "PASS",
            "exit_code": EXIT_GATE_FAILED if failed else EXIT_PASS,
            "policy_used": True, "reasons": reasons}
