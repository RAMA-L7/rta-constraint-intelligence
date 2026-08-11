"""
Structured Finding Identity (Phase 13 — production hardening).

Phase 12 identified findings by ``(rule, severity, normalized message)`` — the
message text was part of the identity, so a future rewording of an explanation
could silently turn an UNCHANGED finding into RESOLVED + NEW.

Phase 13 separates three concepts that Phase 12 conflated:

    IDENTITY     — "what engineering condition is this?"  (semantic fields)
    PRESENTATION — "how do we explain it to a human?"     (the message)
    PROVENANCE   — "where did it occur?"                  (line / line2)

This module defines a structured ``FindingIdentity`` with versioned, semantic
fields extracted from the SDC command text (and, for constraint interactions,
from the semantic ConstraintRecord data produced by the Phase 10 engine) — NOT
from the human-readable message.

Identity strength (never fake certainty):

    STRUCTURED          — fields derived from the SDC command text or the
                          interaction engine's semantic records. Rewording the
                          message can never change this identity.
    LEGACY_NORMALIZED   — fallback for findings whose semantic fields cannot be
                          derived from command data (e.g. synthesized
                          SCOPE-* signals, or design-aware findings whose only
                          evidence is a stable template token). Honest label:
                          identity may depend on stable delimiters in the
                          message.

Key design rules:

  - identity version is separate from the snapshot schema version (they answer
    different compatibility questions).
  - severity is part of the full key (a WARNING → ERROR change must surface as
    CHANGED, never as RESOLVED+NEW). The value-insensitive base key excludes
    severity and blanks numeric values → CHANGED detection.
  - symmetric dual-constraint relationships canonicalize pair ordering; the
    order-sensitive OVERRIDE relationship preserves direction.
  - bit-select ranges (data[3:0]) are object identity, never value-blanked.
  - line numbers are provenance, never identity.

The production validator remains fully deterministic — this module is plain
Python regex/parsing, no AI, no LLM, no probabilistic decisions.
"""

import json
import re
from typing import Dict, List, Optional, Tuple

# ── Identity versioning ──────────────────────────────────────────────────────
# Independent from the snapshot schema version: bump this when the SEMANTIC
# identity contract changes (new fields, different canonicalization), bump the
# snapshot schema when the STORED shape changes.
IDENTITY_VERSION = 1

# Identity strength labels.
STRENGTH_STRUCTURED = "STRUCTURED"
STRENGTH_LEGACY = "LEGACY_NORMALIZED"

# ── Rule families (finding_type) ─────────────────────────────────────────────
FT_CLOCK_DEFINITION = "CLOCK_DEFINITION"
FT_CLOCK_REFERENCE = "CLOCK_REFERENCE"
FT_IO_DELAY = "IO_DELAY"
FT_EXCEPTION = "EXCEPTION"
FT_ELECTRICAL = "ELECTRICAL"
FT_CASE_ANALYSIS = "CASE_ANALYSIS"
FT_DESIGN_OBJECT = "DESIGN_OBJECT"
FT_INTERACTION = "CONSTRAINT_INTERACTION"
FT_SCOPE = "ANALYSIS_SCOPE"
FT_RULE = "RULE"

# Rule → finding_type. Rules not listed fall back to FT_RULE (still structured
# when a command is mapped; the command name carries the discrimination).
_RULE_FAMILY: Dict[str, str] = {
    # Clock definitions / references
    "SDC-001": FT_CLOCK_DEFINITION, "SDC-002": FT_CLOCK_DEFINITION,
    "SDC-003": FT_CLOCK_DEFINITION, "SDC-004": FT_CLOCK_DEFINITION,
    "SDC-007": FT_CLOCK_DEFINITION, "SDC-010": FT_CLOCK_DEFINITION,
    "SDC-008": FT_CLOCK_REFERENCE, "SDC-009": FT_CLOCK_REFERENCE,
    "SDC-046": FT_CLOCK_REFERENCE, "SDC-047": FT_CLOCK_REFERENCE,
    "SDC-048": FT_CLOCK_REFERENCE,
    # I/O delay / boundary
    "SDC-005": FT_IO_DELAY, "SDC-006": FT_IO_DELAY,
    "SDC-028": FT_IO_DELAY, "SDC-029": FT_IO_DELAY,
    "SDC-059": FT_IO_DELAY, "SDC-064": FT_IO_DELAY,
    "SDC-065": FT_IO_DELAY, "SDC-066": FT_IO_DELAY,
    # Timing exceptions
    "SDC-020": FT_EXCEPTION, "SDC-021": FT_EXCEPTION,
    "SDC-027": FT_EXCEPTION, "SDC-037": FT_EXCEPTION,
    "SDC-070": FT_EXCEPTION,
    # Electrical / environment
    "SDC-025": FT_ELECTRICAL, "SDC-031": FT_ELECTRICAL,
    "SDC-032": FT_ELECTRICAL, "SDC-033": FT_ELECTRICAL,
    "SDC-034": FT_ELECTRICAL, "SDC-035": FT_ELECTRICAL,
    "SDC-036": FT_ELECTRICAL, "SDC-040": FT_ELECTRICAL,
    "SDC-041": FT_ELECTRICAL, "SDC-042": FT_ELECTRICAL,
    "SDC-043": FT_ELECTRICAL, "SDC-044": FT_ELECTRICAL,
    "SDC-045": FT_ELECTRICAL,
    # Case analysis
    "SDC-011": FT_CASE_ANALYSIS, "SDC-049": FT_CASE_ANALYSIS,
    # Design-aware object resolution
    "SDC-055": FT_DESIGN_OBJECT, "SDC-056": FT_DESIGN_OBJECT,
    "SDC-057": FT_DESIGN_OBJECT, "SDC-058": FT_DESIGN_OBJECT,
    # Constraint interactions (Phase 10)
    "SDC-067": FT_INTERACTION, "SDC-068": FT_INTERACTION,
    "SDC-069": FT_INTERACTION, "SDC-070": FT_INTERACTION,
}

# ── Number / collection token helpers (mirror constraint_interactions) ───────
_NUM = r'[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?'
_NUM_RE = re.compile(r'(?<![\w.])(' + _NUM + r')(ns|ps|fs|us|µs|ms|MHz|GHz|Hz|V)?(?![A-Za-z0-9_.])')
_BIT_SELECT_RE = re.compile(r'\[\s*[-+]?\d+(?:\s*:\s*[-+]?\d+)?\s*\]')

_COLL_RE = re.compile(r'\[(get_ports|get_pins|get_cells|get_nets|get_clocks)\s+([^\]]*)\]')
_ALL_COLL_RE = re.compile(r'\[(all_inputs|all_outputs|all_clocks|all_registers|all_cells|all_nets)\s*\]')
_CLOCK_FLAG_RE = re.compile(r'-(?:clock|master_clock|name)\s+(\S+)')
_SOURCE_FLAG_RE = re.compile(r'-source\s+(\[[^\]]*\]|\S+)')
_IO_FLAG_RE = re.compile(r'-(max|min)\b')
_EDGE_FLAG_RE = re.compile(r'-(rise|fall|clock_fall)\b')
_SH_FLAG_RE = re.compile(r'-(setup|hold)\b')
_CANON_VALUE_RE = re.compile(r'(?<![\w.])(' + _NUM + r')(?![A-Za-z0-9_.])')


def canon_number(num: str) -> str:
    """Canonicalize a numeric literal: 2.0 → '2', 2.5e-1 → '0.25'."""
    try:
        return f"{float(num):g}"
    except ValueError:
        return num


def _protect_ranges(text: str) -> Tuple[str, List[str]]:
    ranges: List[str] = []
    def _keep(m):
        ranges.append(m.group(0))
        return "\x00RANGE\x00"
    return _BIT_SELECT_RE.sub(_keep, text), ranges


def _blank_values(text: str, blank: bool) -> str:
    """Number-blank every standalone numeric literal unless blank is False."""
    if not blank:
        return text

    def _rep(m):
        return "N" + (m.group(2) or "")

    return _NUM_RE.sub(_rep, text)


def _first_value(text: str) -> str:
    """First standalone numeric literal (bit-select ranges excluded)."""
    s, ranges = _protect_ranges(text)
    m = _CANON_VALUE_RE.search(s)
    if not m:
        return ""
    return canon_number(m.group(1))


# ── Command-derived field extraction ─────────────────────────────────────────

def _flag_ref_name(tok: str) -> str:
    """Unwrap a flag argument that may be a bracketed collection."""
    tok = tok.strip()
    if tok.startswith("[") and tok.endswith("]"):
        m = _COLL_RE.match(tok)
        if m:
            args = m.group(2).strip()
            return args.split()[0] if args else ""
        return ""
    return tok.strip('{}')


def _collection_objects(text: str) -> List[str]:
    """Ordered object names referenced by get_*/all_* collections."""
    objs: List[str] = []
    for m in _COLL_RE.finditer(text):
        args = m.group(2).strip()
        if args:
            first = args.split()[0]
            objs.append(first)
        else:
            objs.append("")
    for m in _ALL_COLL_RE.finditer(text):
        objs.append(m.group(1))
    return objs


def extract_command_fields(cmd_text: str) -> Dict[str, str]:
    """Extract bounded semantic fields from one SDC command text.

    Returns: {command, primary_object, secondary_object, clock, value, mode,
              edge, setup_hold}. Missing fields are "". Pure regex — bounded,
    deterministic, never executes anything.
    """
    t = (cmd_text or "").strip()
    if not t:
        return {}
    name = t.split()[0] if t.split() else ""
    objs = _collection_objects(t)
    # The clock field prefers an EXPLICIT clock REFERENCE (-master_clock,
    # -source, -clock). -name declares the clock being defined (create_clock /
    # create_generated_clock) and is used only when no reference exists — that
    # way two clock definitions with different names stay distinct while a
    # generated clock's structural source is preserved.
    ref = re.search(r'-(?:master_clock|source)\s+(\[[^\]]*\]|\S+)', t)
    ck = _CLOCK_FLAG_RE.search(t)
    if ref:
        clock = _flag_ref_name(ref.group(1))
    else:
        clock = ck.group(1).strip('{}') if ck else ""
    modes = sorted(set(_IO_FLAG_RE.findall(t)))
    edges = sorted(set(_EDGE_FLAG_RE.findall(t)))
    sh = sorted(set(_SH_FLAG_RE.findall(t)))
    return {
        "command": name,
        "primary_object": objs[0] if objs else "",
        "secondary_object": objs[1] if len(objs) > 1 else "",
        "clock": clock,
        "value": _first_value(t),
        "mode": ",".join(modes),
        "edge": ",".join(edges),
        "setup_hold": ",".join(sh),
    }


# ── Structured FindingIdentity ───────────────────────────────────────────────

class FindingIdentity:
    """Structured, message-independent identity for one finding."""

    __slots__ = ("version", "rule_id", "finding_type", "command",
                 "primary_object", "secondary_object", "clock", "value",
                 "mode", "edge", "setup_hold", "interaction_type",
                 "endpoint_signature", "strength", "context")

    def __init__(self, rule_id: str, finding_type: str = FT_RULE,
                 command: str = "", primary_object: str = "",
                 secondary_object: str = "", clock: str = "", value: str = "",
                 mode: str = "", edge: str = "", setup_hold: str = "",
                 interaction_type: str = "", endpoint_signature: str = "",
                 strength: str = STRENGTH_STRUCTURED,
                 context: str = "SDC_ONLY"):
        self.version = IDENTITY_VERSION
        self.rule_id = rule_id
        self.finding_type = finding_type
        self.command = command
        self.primary_object = primary_object
        self.secondary_object = secondary_object
        self.clock = clock
        self.value = value
        self.mode = mode
        self.edge = edge
        self.setup_hold = setup_hold
        self.interaction_type = interaction_type
        self.endpoint_signature = endpoint_signature
        self.strength = strength
        self.context = context

    def to_dict(self) -> dict:
        return {
            "identity_version": self.version,
            "rule_id": self.rule_id,
            "finding_type": self.finding_type,
            "command": self.command,
            "primary_object": self.primary_object,
            "secondary_object": self.secondary_object,
            "clock": self.clock,
            "value": self.value,
            "mode": self.mode,
            "edge": self.edge,
            "setup_hold": self.setup_hold,
            "interaction_type": self.interaction_type,
            "endpoint_signature": self.endpoint_signature,
            "strength": self.strength,
            "context": self.context,
        }

    def full_key(self) -> tuple:
        """Identity key INCLUDING severity is added by the caller (severity is
        part of the full key so a severity change surfaces as CHANGED).

        ``context`` (SDC_ONLY vs DESIGN_AWARE) is deliberately NOT part of the
        key: switching analysis modes must not turn every finding into
        NEW+RESOLVED — the mode change is handled by baseline compatibility
        (PARTIALLY_COMPARABLE), not by identity."""
        return (self.version, self.rule_id, self.finding_type, self.command,
                self.primary_object, self.secondary_object, self.clock,
                self.value, self.mode, self.edge, self.setup_hold,
                self.interaction_type, self.endpoint_signature)

    def base_key(self) -> tuple:
        """Value-insensitive key (values blanked, severity excluded) — used to
        detect CHANGED (same finding, value or severity changed)."""
        return (self.version, self.rule_id, self.finding_type, self.command,
                self.primary_object, self.secondary_object, self.clock,
                "", self.mode, self.edge, self.setup_hold,
                self.interaction_type, self.endpoint_signature)


# ── Identity construction ────────────────────────────────────────────────────

def _endpoint_signature(fields_a: dict, fields_b: dict, canonicalize: bool) -> str:
    """Serialize a two-command endpoint signature.

    VALUE-FREE: values are carried in the FindingIdentity.value field so that
    base-key matching (values blanked) can classify a value change as CHANGED.
    Symmetric relationships (duplicates, conflicts, case-analysis
    contradictions) canonicalize pair ordering. Order-sensitive relationships
    (OVERRIDE) preserve direction.
    """
    def _sig(f: dict) -> tuple:
        return (f.get("command", ""), f.get("primary_object", ""),
                f.get("secondary_object", ""), f.get("clock", ""),
                f.get("mode", ""), f.get("edge", ""))
    sa, sb = _sig(fields_a), _sig(fields_b)
    pair = (sa, sb) if not canonicalize or sa <= sb else (sb, sa)
    return json.dumps(list(pair), sort_keys=True)


def identity_from_commands(rule_id: str, cmd_text_a: str,
                           cmd_text_b: str = "",
                           canonicalize_pair: bool = True,
                           interaction_type: str = "",
                           context: str = "SDC_ONLY",
                           strength: str = STRENGTH_STRUCTURED) -> FindingIdentity:
    """Build a STRUCTURED identity from one or two SDC command texts.

    ``cmd_text_b`` is the second command of a dual-constraint finding
    (SDC-049/067/068/069/070). Symmetric relationships canonicalize pair
    ordering; OVERRIDE preserves direction (caller passes the pair already in
    earlier→later order).
    """
    fa = extract_command_fields(cmd_text_a)
    fb = extract_command_fields(cmd_text_b) if cmd_text_b else {}
    sig = _endpoint_signature(fa, fb, canonicalize=canonicalize_pair) if fb else ""
    # Dual-command findings carry BOTH values (order-preserving when the
    # relationship is order-sensitive, canonicalized otherwise) so a value
    # change surfaces as CHANGED rather than NEW+RESOLVED.
    if fb:
        va, vb = fa.get("value", ""), fb.get("value", "")
        if canonicalize_pair:
            # Symmetric relationships: pair order is irrelevant → sort values.
            value = ";".join(sorted(v for v in (va, vb) if v))
        else:
            # Order-sensitive (OVERRIDE): the caller passes earlier→later, so
            # value order IS the semantic direction and must be preserved.
            value = f"{va};{vb}"
    else:
        value = fa.get("value", "")
    return FindingIdentity(
        rule_id=rule_id,
        finding_type=_RULE_FAMILY.get(rule_id, FT_RULE),
        command=fa.get("command", ""),
        primary_object=fa.get("primary_object", ""),
        secondary_object=fa.get("secondary_object", "") or fb.get("primary_object", ""),
        clock=fa.get("clock", "") or fb.get("clock", ""),
        value=value,
        mode=fa.get("mode", ""),
        edge=fa.get("edge", ""),
        setup_hold=fa.get("setup_hold", ""),
        interaction_type=interaction_type,
        endpoint_signature=sig,
        strength=strength,
        context=context,
    )


def identity_from_interaction(rule_id: str, category: str, command: str,
                              objects_a: tuple, objects_b: tuple,
                              clock: str, value_a: str, value_b: str,
                              mode: str, direction_preserved: bool,
                              context: str = "SDC_ONLY") -> FindingIdentity:
    """Build a STRUCTURED identity from the Phase 10 interaction engine's
    semantic ConstraintRecord data — completely independent of the message.

    The endpoint signature is VALUE-FREE (object sets + relationship mode);
    both values live in the ``value`` field (order-preserving for OVERRIDE,
    canonicalized otherwise) so a value change is CHANGED, not NEW+RESOLVED.
    """
    pair = ([sorted(objects_a), sorted(objects_b)] if direction_preserved
            else sorted([sorted(objects_a), sorted(objects_b)]))
    sig = json.dumps([pair, mode], sort_keys=True)
    values = ([value_a, value_b] if direction_preserved
              else sorted([value_a, value_b]))
    value = ";".join(v for v in values if v)
    return FindingIdentity(
        rule_id=rule_id,
        finding_type=FT_INTERACTION,
        command=command,
        primary_object=sorted(objects_a | objects_b)[0] if (objects_a | objects_b) else "",
        clock=clock,
        value=value,
        mode=mode,
        interaction_type=category,
        endpoint_signature=sig,
        strength=STRENGTH_STRUCTURED,
        context=context,
    )


def identity_legacy(rule_id: str, msg: str, context: str = "SDC_ONLY") -> FindingIdentity:
    """LEGACY_NORMALIZED fallback identity (message-derived, honestly labeled).

    Used only for synthesized findings (SCOPE-*) and design-aware findings
    whose only evidence is a stable template token. The message is normalized
    (whitespace collapsed, numbers canonicalized, line refs stripped) so
    formatting changes never affect it — but rewording may. Never labeled
    STRUCTURED.
    """
    s = " ".join(str(msg).split())
    # FROZEN Phase 12 regex — legacy keys must stay byte-identical to what a
    # real v1 baseline stored so v1↔v2 migration never produces false
    # NEW+RESOLVED. Do not "improve" this normalization; structured identity
    # is the forward path.
    s = re.sub(r'\blines?\s+\d+(?:\s+and\s+\d+)?\b', ' ', s)
    s, ranges = _protect_ranges(s)
    s = _NUM_RE.sub(lambda m: canon_number(m.group(1)) + (m.group(2) or ""), s)
    for r in ranges:
        s = s.replace("\x00RANGE\x00", r, 1)
    s = " ".join(s.split())  # collapse whitespace left by substitutions
    return FindingIdentity(
        rule_id=rule_id,
        finding_type=_RULE_FAMILY.get(rule_id, FT_RULE),
        command="",
        primary_object=s[:160],
        strength=STRENGTH_LEGACY,
        context=context,
    )


# ── Convenience for snapshot builders ────────────────────────────────────────

def identity_to_dict(identity: Optional[FindingIdentity]) -> dict:
    return identity.to_dict() if identity is not None else {}


def identity_from_dict(d: dict) -> FindingIdentity:
    """Rebuild a FindingIdentity from a serialized dict (snapshot round-trip).

    Unknown/missing fields are tolerated (defaults preserved) so an identity
    dict never breaks snapshot loading — but every field present is validated
    to a safe scalar so malformed baselines cannot inject structures.
    """
    def _s(key: str) -> str:
        v = d.get(key, "")
        return v if isinstance(v, (str, int, float)) else ""
    ident = FindingIdentity(
        rule_id=_s("rule_id") or "",
        finding_type=_s("finding_type") or FT_RULE,
        command=_s("command"),
        primary_object=_s("primary_object"),
        secondary_object=_s("secondary_object"),
        clock=_s("clock"),
        value=_s("value"),
        mode=_s("mode"),
        edge=_s("edge"),
        setup_hold=_s("setup_hold"),
        interaction_type=_s("interaction_type"),
        endpoint_signature=_s("endpoint_signature"),
        strength=_s("strength") or STRENGTH_STRUCTURED,
        context=_s("context") or "SDC_ONLY",
    )
    return ident


def identity_simple(rule_id: str, primary_object: str = "", command: str = "",
                    finding_type: str = FT_RULE, mode: str = "",
                    strength: str = STRENGTH_STRUCTURED,
                    context: str = "SDC_ONLY") -> FindingIdentity:
    """Direct construction for findings whose semantic fields are known at
    generation time (design-aware coverage / object-resolution rules)."""
    return FindingIdentity(
        rule_id=rule_id,
        finding_type=finding_type,
        command=command,
        primary_object=primary_object,
        mode=mode,
        strength=strength,
        context=context,
    )


def identity_keys(ident: FindingIdentity, severity: str) -> Tuple[list, list]:
    """(full_key, base_key) from an identity + severity.

    Severity is part of the full key (severity change ⇒ CHANGED via the base
    key) but excluded from the base key (which also blanks values).
    """
    return (list(ident.full_key()) + [severity], list(ident.base_key()))


def make_identity_key(code: str, severity: str, msg: str,
                      cmd_text: str = "", cmd_text_b: str = "",
                      canonicalize_pair: bool = True,
                      interaction_type: str = "",
                      context: str = "SDC_ONLY") -> Tuple[list, list, str, str]:
    """Build (full_key, base_key, identity_dict, strength) for one finding.

    Severity is included in the full key (severity change ⇒ CHANGED via the
    base key) but excluded from the base key. Returns list keys (JSON-safe).
    """
    if cmd_text.strip() or interaction_type:
        ident = identity_from_commands(code, cmd_text, cmd_text_b,
                                       canonicalize_pair, interaction_type,
                                       context)
        strength = ident.strength
    else:
        ident = identity_legacy(code, msg, context)
        strength = ident.strength
    full = list(ident.full_key()) + [severity]
    base = list(ident.base_key())
    return full, base, ident.to_dict(), strength
