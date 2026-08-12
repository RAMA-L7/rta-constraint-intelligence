"""
DFT / scan-mode constraint completeness (F3, SDC-154/155).

Answers: *is scan-mode timing intent provably constrained?* Scan-based DFT
requires ``scan_enable`` / ``test_mode`` to be case-analyzed so STA can
distinguish the three distinct modes — **function, scan shift, scan capture**.
The failure is silent and specific: without mode coverage, STA blends
shift-timing and capture-timing paths into one report.

Rules (both warnings, provable-only, zero-noise on non-DFT designs)
===================================================================
``SDC-154`` — Scan enable without mode coverage (Phase A, SDC-only)
    A scan-enable / test-mode style signal (``scan_en``, ``scan_enable``,
    ``scan_mode``, ``test_mode`` ...) is REFERENCED in the SDC — proving the
    design is DFT — but has NO ``set_case_analysis`` applied to it at all, or
    only a non-mode value (``rising``/``falling``). A single-value mode
    assignment (``set_case_analysis 0`` **or** ``1``) is legitimate: function
    and shift modes are typically constrained in separate corner files
    (verified against the project's own READY fixtures HR01/HR02/HR12). This
    rule fires ONLY on total absence / meaningless values — the genuinely
    silent cases.

``SDC-155`` — Scan false path too broad (Phase A SDC-only + Phase B design-aware)
    A ``set_false_path`` that provably cannot distinguish scan-chain-present
    flops from non-scan flops:
      - **Phase A (no netlist):** the false path is FULLY blanket — both
        ``-from`` and ``-to`` sides are wildcard/``all_*`` classes (e.g.
        ``-from [all_inputs] -to [all_registers]``, ``-from * -to *``) — AND
        the file references a DFT signal. Targeted cuts (``-through
        [get_pins U_SCAN*/scan_en]``, ``-from [get_ports scan_en] -to
        [get_ports data_out]``) are the RECOMMENDED pattern and never fire.
      - **Phase B (netlist):** the netlist shows a **scan-chain shape** (a
        long single-input SI→Q→SI shift chain of >= ``SCAN_CHAIN_MIN_LINKS``
        links, detected from ``net_pins`` connectivity only — zero touch to
        ``design_context.py``), and a false path cuts all flops or uses a
        blanket side. The finding carries the chain evidence and the
        **lock-up latch guard**: never false-path flops present in the scan
        chain, even though they appear in non-scan reports.

DESIGN-AWARE vs SDC-ONLY
========================
Phase A runs in BOTH modes (it needs neither a netlist nor a clock model).
Phase B runs only when ``ctx`` is provided. ``dft_findings(text, ctx=None)``
never raises and never invents evidence.
"""

import re
from dataclasses import dataclass
from typing import Dict, List, Set

from sdc_preprocess import preprocess_sdc

#: A scan chain is a series of flops connected SI→Q. This many consecutive
#: single-input links (>= 3 flops) counts as a provable "long shift chain".
SCAN_CHAIN_MIN_LINKS: int = 2

#: Mode values that count as case-analysis coverage. ``0`` = function/capture,
#: ``1`` = shift. Anything else (rising/falling) is not a mode assignment.
_MODE_VALUES = ("0", "1")

#: Scan-enable / test-mode style signal names — token-boundary matched so
#: 'contest' is not a test signal and 'scan_en0' is. Mirrors the token
#: discipline of design_context._name_class. NOTE: scan_in/scan_out are scan
#: DATA ports, not mode signals — deliberately excluded here.
_SCAN_EN_RE = re.compile(
    r"(?:^|[_0-9])scan[_0-9]*(?:en|enable|se|mode|shift)(?:[_0-9]|$)", re.I)
_TEST_EN_RE = re.compile(
    r"(?:^|[_0-9])test[_0-9]*(?:mode|en|enable|se)(?:[_0-9]|$)", re.I)

#: Any DFT signal (mode signals + scan data ports scan_in/scan_out/...) — used
#: only to prove "this file is a DFT design" for SDC-155 Phase A.
_DFT_TOKEN_RE = re.compile(r"(?:^|[_0-9])(?:scan|test|jtag)(?:[_0-9]|$)", re.I)

#: Blanket / wildcard collection prefixes that are BLANKET (not targeted) cuts.
_BLANKET_PREFIXES = ("[all_inputs]", "[all_ports]", "[all_outputs]",
                     "[all_registers]", "[all_cells]", "[all_nets]")

#: Q-class output pin names (scan-chain links originate here). 'so' (scan
#: out) is the canonical scan-chain Q pin; q/dout/do are the functional ones.
_Q_PIN_SUFFIXES = ("so", "q", "qn", "q_", "dout", "do", "out", "o", "y")
#: D-class input pin names (scan-chain links terminate here). 'si' (scan in)
#: is the canonical scan-chain D pin; d/din are the functional ones.
_D_PIN_SUFFIXES = ("si", "d", "din", "di", "d_", "in", "i", "data", "a", "b")


@dataclass
class Finding:
    """A single DFT/scan finding (SDC-154/155)."""

    sev: str
    code: str
    msg: str
    line: int = 0


def _is_scan_enable(name: str) -> bool:
    """Token-boundary scan-enable / test-mode signal name detection."""
    low = name.lower()
    return bool(_SCAN_EN_RE.search(low) or _TEST_EN_RE.search(low))


def _coll_names(inner: str) -> List[str]:
    """Expand a collection body ('{a b}', 'a b', 'u_core/*') to name tokens,
    skipping the collection kind keyword (get_ports / get_pins / get_cells)."""
    a = inner.strip()
    if a.startswith("{") and a.endswith("}"):
        a = a[1:-1]
    toks = a.split()
    if toks and toks[0].lower() in ("get_ports", "get_pins", "get_cells",
                                    "get_nets", "get_clocks"):
        toks = toks[1:]
    return toks


def _normalized(text: str) -> str:
    """Comments stripped, backslash continuations joined — the same view the
    checker's ``_grab`` uses. Regex-scanning this (not command-start matching)
    is robust to files whose continuation lines merge multiple commands into
    one preprocessed entry (e.g. samples/real_design_full.sdc)."""
    return "\n".join(c.text for c in preprocess_sdc(text))


def _case_analysis_map(text: str) -> Dict[str, "tuple[list, int]"]:
    """signal name -> (list of set_case_analysis values, first source line).

    Only ``0``/``1`` are mode values (the map still records others so the
    caller can see that coverage exists but is not mode coverage). Names are
    collected from get_ports/get_pins/get_cells references in the command's
    target collection. Scans substrings so commands merged by continuation
    lines are still seen.
    """
    out: Dict[str, "tuple[list, int]"] = {}
    norm = _normalized(text)
    for m in re.finditer(
            r"set_case_analysis\s+(0|1|rising|falling|rise|fall)\s+(\[[^\]]*\]|\S+)",
            norm, re.IGNORECASE):
        val = m.group(1).lower()
        ref = m.group(2)
        inner = ref[1:-1] if ref.startswith("[") else ref
        names = _coll_names(inner)
        ln = norm[:m.start()].count("\n") + 1
        for nm in names:
            if nm in out:
                out[nm][0].append(val)
            else:
                out[nm] = ([val], ln)
    return out


def _scan_enable_signals_in_sdc(text: str) -> Dict[str, int]:
    """Every scan-enable / test-mode signal referenced anywhere in the SDC,
    mapped to its first source line. Proves the design is DFT AND names the
    mode signals that must carry case analysis."""
    hits: Dict[str, int] = {}
    norm = _normalized(text)
    for m in re.finditer(r"\[(get_ports|get_pins|get_cells)\s+([^\]]*)\]", norm):
        ln = norm[:m.start()].count("\n") + 1
        for nm in _coll_names(m.group(2)):
            if _is_scan_enable(nm) and nm not in hits:
                hits[nm] = ln
    return hits


def _has_dft_signals(text: str) -> bool:
    """True when the SDC references any scan/test/jtag-named object — the
    provable 'this is a DFT design' evidence for SDC-155 Phase A.

    Token-boundary match over collection names (NOT substring): 'contest' /
    'latest' must not count as 'test', while 'test_mode' and 'scan_in' do.
    """
    norm = _normalized(text)
    for m in re.finditer(r"\[(get_ports|get_pins|get_cells)\s+([^\]]*)\]", norm):
        for nm in _coll_names(m.group(2)):
            if _DFT_TOKEN_RE.search(nm):
                return True
    return False


def _scan_chain_instances(ctx) -> Set[str]:
    """Instances that participate in a scan-chain shape (Phase B).

    A "link" is a net connecting exactly one Q-class output pin (module
    output/inout) to exactly one D-class input pin of a DIFFERENT instance.
    A chain is >= SCAN_CHAIN_MIN_LINKS consecutive links (>= 3 flops in a
    SI→Q→SI→Q... series). Built purely from ``ctx.net_pins`` / ``pin_direction``
    / ``pin_name`` — no new data model, zero touch to design_context.
    """
    links: Dict[str, str] = {}          # flop instance path -> next flop path
    for net, pins in ctx.net_pins.items():
        q_pins: List[str] = []
        d_pins: List[str] = []
        for pin_path in pins:
            pname = ctx.pin_name(pin_path)
            d = ctx.pin_direction(pin_path)
            low = pname.lower()
            if d in ("output", "inout") and any(
                    low == s or (low.endswith(s) and not low[-len(s) - 1].isalnum())
                    for s in _Q_PIN_SUFFIXES):
                q_pins.append(pin_path)
            elif d == "input" and any(
                    low == s or (low.endswith(s) and not low[-len(s) - 1].isalnum())
                    for s in _D_PIN_SUFFIXES):
                d_pins.append(pin_path)
        if len(q_pins) == 1 and len(d_pins) == 1:
            src_inst = q_pins[0].rsplit("/", 1)[0]
            dst_inst = d_pins[0].rsplit("/", 1)[0]
            if src_inst != dst_inst:
                links[src_inst] = dst_inst

    # follow links to find maximal chains
    chain_members: Set[str] = set()
    starts = set(links) - set(links.values())
    if not starts:
        starts = set(links)
    for start in starts:
        path = [start]
        cur = start
        while cur in links and len(path) <= len(links):
            nxt = links[cur]
            if nxt in path:
                break
            path.append(nxt)
            cur = nxt
        if len(path) - 1 >= SCAN_CHAIN_MIN_LINKS:
            chain_members.update(path)
    return chain_members


def _blanket_side(ref: str) -> bool:
    """True when a -from/-to reference is a FULLY blanket class: an all_*
    collection or a bare wildcard. A wildcard *inside* a get_pins pattern
    (U_SCAN*) or a bus bit-select (dout[*]) is TARGETED, not blanket."""
    r = ref.strip().lower()
    if r == "*" or r == "\\*":
        return True
    return any(r.startswith(p) for p in _BLANKET_PREFIXES)


def _fully_blanket_false_path(cmd: str) -> bool:
    """set_false_path whose BOTH -from and -to sides are blanket classes."""
    low = cmd.lower()
    from_m = re.search(r"-from\s+(\[[^\]]*\]|\S+)", low)
    to_m = re.search(r"-to\s+(\[[^\]]*\]|\S+)", low)
    if not (from_m and to_m):
        return False
    return _blanket_side(from_m.group(1)) and _blanket_side(to_m.group(1))


def _cuts_all_flops(cmd: str) -> bool:
    """set_false_path whose -from OR -to side matches all flops
    (all_registers / all_cells / bare *). Phase B trigger: with a chain
    present, either side provably false-paths scan-chain flops (launch or
    capture)."""
    low = cmd.lower()
    for m in re.finditer(r"-(?:from|to)\s+(\[[^\]]*\]|\S+)", low):
        r = m.group(1).strip().lower()
        if r == "*" or r.startswith(("[all_registers]", "[all_cells]")):
            return True
    return False


def _find_line(text: str, needle: str) -> int:
    """1-based line of the first occurrence of ``needle`` (0 if absent)."""
    idx = text.find(needle)
    if idx == -1:
        return 0
    return text[:idx].count("\n") + 1


def dft_findings(text: str, ctx=None) -> List[Finding]:
    """Scan an SDC (+ optional design context) for DFT/scan-mode gaps.

    Phase A (SDC-154/155) runs in both SDC-only and design-aware modes.
    Phase B (SDC-155 chain-shape evidence) runs only when ``ctx`` is provided.

    Returns one ``Finding`` per offending signal / false-path command.
    """
    findings: List[Finding] = []
    ca_map = _case_analysis_map(text)

    # ── SDC-154 — scan enable without mode coverage ─────────────────────────
    # A DFT mode signal referenced in the SDC must carry SOME mode-value case
    # analysis. Total absence (or only rising/falling) is the silent failure.
    for name, ln in sorted(_scan_enable_signals_in_sdc(text).items()):
        vals = ca_map.get(name, ([], ln))[0]
        mode_vals = {v for v in vals if v in _MODE_VALUES}
        if len(mode_vals) >= 1:
            continue  # at least one real mode assignment present
        if vals:
            extra = f" (has non-mode value(s) {sorted(set(vals))})"
        else:
            extra = ""
        findings.append(Finding(
            "warning", "SDC-154",
            f"Scan enable '{name}' is referenced in the SDC but has no "
            f"set_case_analysis mode assignment{extra} — without a case "
            f"analysis value for function/capture (0) and scan shift (1), "
            f"STA blends shift-timing and capture-timing paths into one "
            f"report. Add set_case_analysis 0 [get_ports {name}] "
            f"(function/capture) and set_case_analysis 1 [get_ports {name}] "
            f"(scan shift), or verify the mode is constrained in its own "
            f"corner file.",
            line=ln,
        ))

    # ── SDC-155 — scan false path too broad ─────────────────────────────────
    exception_cmds = re.findall(r"set_false_path[^;\n]*", _normalized(text))
    if not exception_cmds:
        return findings

    chain_insts: Set[str] = set()
    if ctx is not None:
        try:
            chain_insts = _scan_chain_instances(ctx)
        except Exception:
            chain_insts = set()

    dft_design = _has_dft_signals(text)   # hoisted: one preprocess, not per-command
    fired: Set[str] = set()  # dedupe: one finding per offending command
    for cmd in exception_cmds:
        if cmd in fired:
            continue
        ln = _find_line(text, cmd)
        # Phase B: chain shape + a cut that matches all flops → provably wrong
        # (the cut false-paths flops that ARE in the scan chain).
        if chain_insts and _cuts_all_flops(cmd):
            fired.add(cmd)
            chain_txt = ", ".join(sorted(chain_insts)[:4])
            more = "" if len(chain_insts) <= 4 else f" (+{len(chain_insts) - 4} more)"
            findings.append(Finding(
                "warning", "SDC-155",
                f"False path cuts all flops while the netlist shows a scan "
                f"chain ({chain_txt}{more}) — lock-up latch guard: NEVER "
                f"false-path flops present in the scan chain, even though "
                f"they appear in non-scan reports. Restrict the exception to "
                f"genuinely non-scan flops (e.g. -to [get_cells non_scan_*]) "
                f"or use mode-specific set_case_analysis.",
                line=ln,
            ))
            continue
        # Phase A: FULLY blanket cut in a provably-DFT file.
        if dft_design and _fully_blanket_false_path(cmd):
            fired.add(cmd)
            findings.append(Finding(
                "warning", "SDC-155",
                f"Fully-blanket false path in a DFT design — the wildcard "
                f"cut cannot distinguish scan-chain-present flops from "
                f"non-scan flops, so scan paths may be silently exempted. "
                f"Restrict the exception to genuinely non-scan flops or use "
                f"mode-specific set_case_analysis.",
                line=ln,
            ))

    return findings
