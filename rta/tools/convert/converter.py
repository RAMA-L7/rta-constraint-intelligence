"""
SDC Converter — Convert SDC constraint files to structured JSON or YAML.

Usage:
    from converter import sdc_to_json, sdc_to_yaml
    json_str = sdc_to_json(sdc_text)
    yaml_str = sdc_to_yaml(sdc_text)

CLI:
    sdc-tools convert input.sdc --format json
    sdc-tools convert input.sdc --format yaml --output constraints.yaml
"""

import json
import re
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional, Any

from sdc_preprocess import preprocess_sdc, parse_collection, NUM_PATTERN


# ── Parsed SDC structure ────────────────────────────────────────────────────────

@dataclass
class ParsedClock:
    name: str = ""
    period: float = 0.0
    port: str = ""
    is_generated: bool = False
    is_virtual: bool = False
    master_source: str = ""
    divide_by: Optional[int] = None
    multiply_by: Optional[int] = None
    waveform: List[float] = field(default_factory=list)
    raw: str = ""


@dataclass
class ParsedIODelay:
    command: str             # "set_input_delay" | "set_output_delay"
    value: float = 0.0
    clock: str = ""
    ports: List[str] = field(default_factory=list)
    delay_type: str = "max"  # "max" | "min"
    raw: str = ""


@dataclass
class ParsedException:
    command: str             # "set_false_path", "set_multicycle_path", etc.
    from_: str = ""
    to: str = ""
    through: List[str] = field(default_factory=list)
    setup: Optional[int] = None
    hold: Optional[int] = None
    value: float = 0.0
    raw: str = ""


@dataclass
class ParsedDerate:
    delay_type: str = "cell_delay"   # "cell_delay" | "net_delay"
    timing_type: str = "late"        # "late" | "early"
    value: float = 1.0
    raw: str = ""


@dataclass
class ParsedSDC:
    """Structured representation of an SDC file."""
    filename: str = ""
    sdc_version: str = ""
    units: Dict[str, str] = field(default_factory=dict)
    clocks: List[ParsedClock] = field(default_factory=list)
    input_delays: List[ParsedIODelay] = field(default_factory=list)
    output_delays: List[ParsedIODelay] = field(default_factory=list)
    false_paths: List[ParsedException] = field(default_factory=list)
    multicycle_paths: List[ParsedException] = field(default_factory=list)
    clock_groups: List[Dict[str, Any]] = field(default_factory=list)
    timing_derate: List[ParsedDerate] = field(default_factory=list)
    case_analysis: List[Dict[str, str]] = field(default_factory=list)
    constraints_count: int = 0
    clocks_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ── Parsing helpers ─────────────────────────────────────────────────────────────

def _grab(text: str, pattern: str) -> List[str]:
    return re.findall(pattern, text, re.MULTILINE)


def _extract_ports(text: str) -> List[str]:
    """Extract port/pin/cell names from TCL square bracket notation."""
    ports = re.findall(r'\[get_(?:ports|pins|cells)\s+([^\]]+)\]', text)
    return [p.strip() for p in ports]


def _extract_value(text: str, key: str, default: float = 0.0) -> float:
    """Extract a numeric value for a key like '-period 5.0' (sci-notation safe)."""
    m = re.search(rf'{key}\s+(' + NUM_PATTERN + r')', text)
    return float(m.group(1)) if m else default


# ── Main parse function ─────────────────────────────────────────────────────────

def parse_sdc(text: str, filename: str = "") -> ParsedSDC:
    """Parse SDC text into a structured ParsedSDC object."""
    result = ParsedSDC(filename=filename)
    # Normalize once: strip comments and join backslash-newline continuations
    # so multi-line commands are parsed identically to single-line ones.
    text = '\n'.join(c.text for c in preprocess_sdc(text))
    lines = text.splitlines()

    # SDC version
    for m in re.finditer(r'set\s+sdc_version\s+([\d.]+)', text, re.IGNORECASE):
        result.sdc_version = m.group(1)

    # Units — parse -time ns -capacitance pF -resistance kOhm
    units_match = re.search(r'set_units\s+(.+?)(?:\n|$)', text)
    if units_match:
        unit_text = units_match.group(1)
        # Extract all -flag value pairs
        for m in re.finditer(r'-(\w+)\s+(\S+)', unit_text):
            result.units[m.group(1)] = m.group(2)

    # Clocks
    for c in _grab(text, r'create_clock[^;\n]*'):
        clock = ParsedClock(raw=c)
        nm = re.search(r'-name\s+(\S+)', c)
        if nm:
            clock.name = nm.group(1)
        clock.period = _extract_value(c, "-period")
        pt = _extract_ports(c)
        clock.port = pt[0] if pt else ""
        clock.is_virtual = not bool(pt)
        result.clocks.append(clock)
        result.clocks_count += 1

    # Generated clocks
    for c in _grab(text, r'create_generated_clock[^;\n]*'):
        clock = ParsedClock(raw=c, is_generated=True)
        nm = re.search(r'-name\s+(\S+)', c)
        if nm:
            clock.name = nm.group(1)
        clock.period = _extract_value(c, "-period")
        ms = re.search(r'-source\s+\[(?:get_ports|get_pins|get_cells)\s+([^\]]+)\]', c)
        if ms:
            clock.master_source = ms.group(1).strip()
        dv = re.search(r'-divide_by\s+(\d+)', c)
        if dv:
            clock.divide_by = int(dv.group(1))
        mv = re.search(r'-multiply_by\s+(\d+)', c)
        if mv:
            clock.multiply_by = int(mv.group(1))
        result.clocks.append(clock)
        result.clocks_count += 1

    _derive_generated_periods(result)

    # Input/Output delays
    for d in _grab(text, r'set_input_delay[^;\n]*'):
        parsed = _parse_io_delay(d, "set_input_delay")
        result.input_delays.append(parsed)

    for d in _grab(text, r'set_output_delay[^;\n]*'):
        parsed = _parse_io_delay(d, "set_output_delay")
        result.output_delays.append(parsed)

    # False paths
    for fp in _grab(text, r'set_false_path[^;\n]*'):
        parsed = _parse_exception(fp, "set_false_path")
        result.false_paths.append(parsed)

    # Multicycle paths
    for mc in _grab(text, r'set_multicycle_path[^;\n]*'):
        parsed = _parse_exception(mc, "set_multicycle_path")
        result.multicycle_paths.append(parsed)

    # Clock groups — parse each -group collection (braced lists supported)
    for cg in _grab(text, r'set_clock_groups[^;\n]*'):
        group_type = "asynchronous"
        for t in ("asynchronous", "physically_exclusive", "logically_exclusive"):
            if t in cg:
                group_type = t
                break
        groups = []
        for gm in re.finditer(r'-group\s+(\[[^\]]+\]|\{[^}]*\}|\S+)', cg):
            groups.append(parse_collection(gm.group(1)))
        result.clock_groups.append({
            "type": group_type,
            "groups": groups,
            "raw": cg,
        })

    # Case analysis
    for ca in _grab(text, r'set_case_analysis[^;\n]*'):
        m = re.search(r'set_case_analysis\s+(\S+)\s+(\S+)', ca)
        if m:
            result.case_analysis.append({
                "value": m.group(1),
                "target": m.group(2),
            })

    # Timing derate
    for td in _grab(text, r'set_timing_derate[^;\n]*'):
        delay_t = "cell_delay" if "-cell_delay" in td else "net_delay"
        timing_t = "late" if "-late" in td else "early"
        # Extract the numeric value (last number in the command)
        vm = re.search(r'(' + NUM_PATTERN + r')\s*\[', td)
        if vm:
            value = float(vm.group(1))
        else:
            value = _extract_value(td, "-cell_delay") or _extract_value(td, "-net_delay")
        result.timing_derate.append(ParsedDerate(
            delay_type=delay_t,
            timing_type=timing_t,
            value=value,
            raw=td,
        ))

    # Max/Min delay
    for md in _grab(text, r'set_max_delay[^;\n]*'):
        parsed = _parse_exception(md, "set_max_delay")
        result.multicycle_paths.append(parsed)  # reuse Exception dataclass
    for md in _grab(text, r'set_min_delay[^;\n]*'):
        parsed = _parse_exception(md, "set_min_delay")
        result.multicycle_paths.append(parsed)

    result.constraints_count = (
        result.clocks_count
        + len(result.input_delays) + len(result.output_delays)
        + len(result.false_paths) + len(result.multicycle_paths)
    )

    return result


def _derive_generated_periods(result: ParsedSDC) -> None:
    """Derive periods for generated clocks that declare no explicit -period.

    A generated clock's period is the master clock's period × divide_by
    (frequency division doubles the period), or ÷ multiply_by. The master is
    resolved by -master_clock name first, then by the -source node (port or
    pin) matching another clock's output node. Resolution is iterative so
    multi-level chains (clk → div2 → div4) work.
    """
    for _ in range(len(result.clocks) + 1):
        changed = False
        for clock in result.clocks:
            if not clock.is_generated or clock.period > 0:
                continue
            master = _resolve_master(result, clock)
            if master is None or master.period <= 0:
                continue
            if clock.divide_by and clock.divide_by > 1:
                clock.period = master.period * clock.divide_by
            elif clock.multiply_by and clock.multiply_by > 0:
                clock.period = master.period / clock.multiply_by
            else:
                clock.period = master.period
            changed = True
        if not changed:
            break


def _resolve_master(result: ParsedSDC, clock: ParsedClock) -> Optional[ParsedClock]:
    """Find the master clock for a generated clock.

    Priority: -master_clock name → -source node matching another clock's
    output node (gen node) → -source port matching a primary clock's port.
    """
    by_name = {c.name: c for c in result.clocks if c.name}
    master_name = ""
    mm = re.search(r'-master_clock\s+(\S+)', clock.raw)
    if mm:
        master_name = mm.group(1)
    if master_name and master_name in by_name and by_name[master_name] is not clock:
        return by_name[master_name]

    src = clock.master_source
    if not src:
        return None
    # source is a port or pin name (bracket content already stripped)
    for c in result.clocks:
        if c is clock:
            continue
        # A generated clock's OUTPUT node is its LAST get_ports/get_pins object.
        objs = re.findall(r'\[(?:get_ports|get_pins|get_cells)\s+([^\]]+)\]', c.raw)
        if objs and src == objs[-1].strip():
            return c
        if not c.is_generated and c.port == src:
            return c
    return None


def _parse_io_delay(text: str, command: str) -> ParsedIODelay:
    """Parse an I/O delay command.

    When a statement carries both -max and -min, the -max (setup) value is the
    one kept in ``value`` and ``delay_type`` (matching the checker's SDC-008/009
    semantics); -min-only statements report the -min value.
    """
    max_m = re.search(r'-max\s+(' + NUM_PATTERN + r')', text)
    min_m = re.search(r'-min\s+(' + NUM_PATTERN + r')', text)
    if max_m:
        delay_type, value = "max", float(max_m.group(1))
    elif min_m:
        delay_type, value = "min", float(min_m.group(1))
    else:
        delay_type = "max"
        value = 0.0
        val_m = re.search(rf'{command}[^0-9]*(' + NUM_PATTERN + r')', text)
        if val_m:
            value = float(val_m.group(1))

    clk = ""
    clk_m = re.search(r'-clock\s+(\S+)', text)
    if clk_m:
        clk = clk_m.group(1)

    ports = _extract_ports(text)
    return ParsedIODelay(
        command=command, value=value,
        clock=clk, ports=ports,
        delay_type=delay_type, raw=text,
    )


def _parse_exception(text: str, command: str) -> ParsedException:
    """Parse a timing exception command."""
    fm = re.search(r'-from\s+(\S+)', text)
    tm = re.search(r'-to\s+(\S+)', text)
    sm = re.search(r'-setup\s+(\d+)', text)
    hm = re.search(r'-hold\s+(\d+)', text)
    val = 0.0
    if command == "set_max_delay" or command == "set_min_delay":
        vm = re.search(r'set_(?:max|min)_delay\s+(' + NUM_PATTERN + r')', text)
        if vm:
            val = float(vm.group(1))

    # -through can appear multiple times
    through = re.findall(r'-through\s+(\S+)', text)

    return ParsedException(
        command=command,
        from_=fm.group(1) if fm else "",
        to=tm.group(1) if tm else "",
        through=through,
        setup=int(sm.group(1)) if sm else None,
        hold=int(hm.group(1)) if hm else None,
        value=val,
        raw=text,
    )


# ── Output formats ──────────────────────────────────────────────────────────────

def sdc_to_json(text: str, filename: str = "", indent: int = 2) -> str:
    """Parse SDC text and return formatted JSON string."""
    parsed = parse_sdc(text, filename)
    return json.dumps(parsed.to_dict(), indent=indent, default=str)


def sdc_to_yaml(text: str, filename: str = "") -> str:
    """Parse SDC text and return YAML string."""
    import yaml

    parsed = parse_sdc(text, filename)
    data = parsed.to_dict()
    return yaml.dump(data, default_flow_style=False, sort_keys=False)
