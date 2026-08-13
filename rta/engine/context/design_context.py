"""
Optional design-aware validation — structural Verilog / design-object context.

Phase 8. Answers questions SDC-only analysis cannot answer safely:

  - does ``[get_ports foo]`` actually resolve against the supplied design?
  - are ``[get_pins a/b/D]`` hierarchy references valid?
  - do wildcard collections match anything, or resolve empty?
  - which real ports are left unconstrained?

Design context is OPTIONAL. When absent, the validator behaves exactly as in
SDC-only mode (NETLIST_REQUIRED trust status). When present, only *provable*
references are upgraded — anything the resolver does not understand stays
NETLIST_REQUIRED. Uploaded Verilog is DATA: this module only does lexical
scanning — no eval, no exec, no shell, no includes, no synthesis tools.

Supported structural Verilog subset (documented — this is NOT a Verilog
compiler):

  - ``module name (ports);`` ANSI and non-ANSI port lists
  - ``input/output/inout`` declarations with optional ``[msb:lsb]`` ranges
  - ``wire``/``tri`` net declarations with ranges and comma lists
  - module instances: ``type inst (.pin(expr), ...);`` named connections,
    basic positional connections, multi-instance ``,`` lists, ``\escaped``
    identifiers, scalar and ``name[msb:lsb]`` instance arrays (base-name match)
  - ``assign`` / ``parameter`` / ``localparam`` / ``generate`` / ``specify``
    statements are skipped safely (begin/end balanced)
  - ``always`` / ``initial`` blocks are skipped safely (begin/end balanced)

Not supported (degraded, never executed, surfaced transparently):

  - behavioral RTL semantics, functions/tasks internals, ``defparam``,
    ``macromodule``, ``ifdef``/``include`` (directives treated as comments),
    user-defined primitives, netlist synthesis/elaboration.

No timing engine. No placement. No library data. This is a name/hierarchy
inventory, per the Phase 7 proposal.
"""

import fnmatch
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple


# ── Parse result / warnings ───────────────────────────────────────────────────

@dataclass
class ParseOutcome:
    """Result of parsing a Verilog file (never raises on bad input)."""
    context: Optional["DesignContext"] = None   # None when no usable top found
    top: str = ""
    top_candidates: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    modules_seen: List[str] = field(default_factory=list)


# ── Design object model ───────────────────────────────────────────────────────

@dataclass
class DesignPort:
    name: str
    direction: str          # input | output | inout
    msb: Optional[int] = None
    lsb: Optional[int] = None

    def is_bus(self) -> bool:
        return self.msb is not None and self.lsb is not None


@dataclass
class DesignInstance:
    path: str               # full hierarchical path "u_core/u_reg"
    name: str               # leaf name
    module: str             # module type instantiated
    parent: str             # "" for top-level instances


@dataclass
class DesignContext:
    """Name/hierarchy inventory derived from a structural netlist.

    Phase 9 adds a lightweight CONNECTIVITY layer (structural only — no
    timing semantics):

      module_port_dirs: module → {port name → direction} (drivers vs loads)
      pin_nets:         "path/pin" → set of net base names it connects to
      net_pins:         net name → set of "path/pin" connected to it

    This lets the coverage analyzer classify a top-level port structurally
    (e.g. an input whose net drives instance CLK pins is a clock port) without
    pretending to propagate timing.
    """
    top_module: str = ""
    modules: Set[str] = field(default_factory=set)
    ports: Dict[str, DesignPort] = field(default_factory=dict)   # TOP-level ports
    module_ports: Dict[str, List[str]] = field(default_factory=dict)  # module → ordered port names
    module_port_dirs: Dict[str, Dict[str, str]] = field(default_factory=dict)  # module → {port: dir}
    instances: Dict[str, DesignInstance] = field(default_factory=dict)  # path → instance
    nets: Dict[str, Tuple[Optional[int], Optional[int]]] = field(default_factory=dict)  # name → (msb,lsb)
    pins: Set[str] = field(default_factory=set)   # "path/pin"
    pin_nets: Dict[str, Set[str]] = field(default_factory=dict)  # "path/pin" → nets
    net_pins: Dict[str, Set[str]] = field(default_factory=dict)  # net → "path/pin"
    # index of instance paths containing each leaf, for wildcard speed
    _instance_leaves: Set[str] = field(default_factory=set)

    # ── connectivity queries (indexed) ─────────────────────────────────────
    def net_drivers(self, net: str) -> Set[str]:
        """Instance pins that DRIVE ``net`` (module output/inout ports)."""
        out = set()
        for pin_path in self.net_pins.get(net, set()):
            path, _, pname = pin_path.rpartition('/')
            inst = self.instances.get(path)
            if inst:
                d = self.module_port_dirs.get(inst.module, {}).get(pname, "")
                if d in ("output", "inout"):
                    out.add(pin_path)
        return out

    def net_loads(self, net: str) -> Set[str]:
        """Instance pins that LOAD ``net`` (module input/inout ports)."""
        out = set()
        for pin_path in self.net_pins.get(net, set()):
            path, _, pname = pin_path.rpartition('/')
            inst = self.instances.get(path)
            if inst:
                d = self.module_port_dirs.get(inst.module, {}).get(pname, "")
                if d in ("input", "inout"):
                    out.add(pin_path)
        return out

    def pin_direction(self, pin_path: str) -> str:
        """Direction of an instance pin (input/output/inout) or ""."""
        path, _, pname = pin_path.rpartition('/')
        inst = self.instances.get(path)
        if not inst:
            return ""
        return self.module_port_dirs.get(inst.module, {}).get(pname, "")

    def pin_name(self, pin_path: str) -> str:
        """Leaf pin name (last path component)."""
        return pin_path.rsplit('/', 1)[-1]

    # ── counts ──────────────────────────────────────────────────────────────
    def object_counts(self) -> Dict[str, int]:
        return {
            "modules": len(self.modules),
            "ports": len(self.ports),
            "instances": len(self.instances),
            "nets": len(self.nets),
            "pins": len(self.pins),
        }

    def connectivity_counts(self) -> Dict[str, int]:
        return {
            "nets_with_connections": len(self.net_pins),
            "pins_with_connections": len(self.pin_nets),
        }

    def to_dict(self) -> dict:
        return {
            "top_module": self.top_module,
            "analysis_mode": "design_aware",
            **self.object_counts(),
        }

    @classmethod
    def from_inventory(cls, data: dict) -> "DesignContext":
        """Build a DesignContext from an explicit JSON/YAML inventory.

        Accepts keys: top_module, modules, ports [{name, direction, msb, lsb}],
        instances [{path, name, module, parent}], nets [{name, msb, lsb}],
        pins [strings], plus optional Phase 9 connectivity:
        module_port_dirs {module: {port: dir}}, pin_nets {"path/pin": [nets]},
        net_pins {net: ["path/pin"]}. This is the Phase 7 proposal's
        lightweight format.
        """
        ctx = cls(top_module=str(data.get("top_module", "")))
        for m in data.get("modules", []):
            ctx.modules.add(str(m))
        for p in data.get("ports", []):
            port = DesignPort(str(p["name"]), str(p.get("direction", "input")),
                              p.get("msb"), p.get("lsb"))
            ctx.ports[port.name] = port
        for i in data.get("instances", []):
            path = str(i["path"])
            ctx.instances[path] = DesignInstance(path, str(i.get("name", path.split("/")[-1])),
                                                 str(i.get("module", "")), str(i.get("parent", "")))
            ctx._instance_leaves.add(ctx.instances[path].name)
        for n in data.get("nets", []):
            ctx.nets[str(n["name"])] = (n.get("msb"), n.get("lsb"))
        for pin in data.get("pins", []):
            ctx.pins.add(str(pin))
        # optional Phase 9 connectivity
        ctx.module_port_dirs = {str(m): {str(k): str(v) for k, v in dirs.items()}
                                for m, dirs in data.get("module_port_dirs", {}).items()}
        for p, nets in data.get("pin_nets", {}).items():
            ctx.pin_nets[str(p)] = set(nets)
        for n, pins in data.get("net_pins", {}).items():
            ctx.net_pins[str(n)] = set(pins)
        return ctx

    # ── lookups (indexed, no full scans for exact names) ────────────────────
    def port_exists(self, name: str) -> bool:
        return name in self.ports

    def cell_exists(self, path: str) -> bool:
        return path in self.instances

    def pin_exists(self, path: str) -> bool:
        return path in self.pins

    def net_exists(self, name: str) -> bool:
        return name in self.nets


# ── Verilog lexical helpers ───────────────────────────────────────────────────

_IDENT = r"(?:\\\S+|[A-Za-z_$][\w$]*)"      # escaped or plain identifier

def _strip_comments(text: str) -> str:
    """Remove Verilog comments (// and /* */) and string literals safely."""
    out = []
    i, n = 0, len(text)
    while i < n:
        c = text[i]
        if c == '"':                       # string literal — keep as opaque token
            # Walk to the closing quote honoring \\-escapes, so strings
            # containing \" do not truncate mid-string.
            j = i + 1
            while j < n:
                if text[j] == '\\' and j + 1 < n:
                    j += 2
                    continue
                if text[j] == '"':
                    break
                j += 1
            if j >= n:
                out.append(text[i:])
                break
            out.append(text[i:j + 1])
            i = j + 1
            continue
        if c == '/' and i + 1 < n and text[i + 1] == '/':   # line comment
            j = text.find('\n', i)
            out.append(' ' * ((j - i) if j != -1 else (n - i)))
            i = j if j != -1 else n
            continue
        if c == '/' and i + 1 < n and text[i + 1] == '*':   # block comment
            j = text.find('*/', i + 2)
            if j == -1:
                break
            out.append(' ' * (j + 2 - i))
            i = j + 2
            continue
        out.append(c)
        i += 1
    return ''.join(out)


def _split_statements(code: str) -> List[Tuple[str, int]]:
    """Split into (statement, lineno) chunks at top-level ';' or endmodule.

    Respects parens/brackets/braces and preserves approximate line numbers.
    A standalone ``endmodule`` (with or without ``;``) is always its own
    statement, so following module headers are never merged into it.
    """
    stmts: List[Tuple[str, int]] = []
    cur: List[str] = []
    start_line = 1
    line = 1
    depth_p = depth_b = depth_c = 0
    in_quote = None            # None | '"' — keywords/; inside strings are literal
    i, n = 0, len(code)
    while i < n:
        ch = code[i]
        if ch == '\n':
            line += 1
        if in_quote:
            cur.append(ch)
            if ch == '\\' and i + 1 < n:
                cur.append(code[i + 1])
                i += 2
                continue
            if ch == '"':
                in_quote = None
            i += 1
            continue
        if ch == '"':
            in_quote = '"'
            cur.append(ch)
            i += 1
            continue
        if ch == '(':
            depth_p += 1
        elif ch == ')':
            depth_p = max(depth_p - 1, 0)
        elif ch == '[':
            depth_b += 1
        elif ch == ']':
            depth_b = max(depth_b - 1, 0)
        elif ch == '{':
            depth_c += 1
        elif ch == '}':
            depth_c = max(depth_c - 1, 0)

        # 'endmodule' at top level always terminates the statement. A top-level
        # 'module' flushes any leading garbage (shebangs, NUL bytes, stray
        # python) so it cannot corrupt the header — Verilog forbids nested
        # modules, so a top-level 'module' is always a boundary. The keyword
        # itself is NOT consumed here; it starts the next statement. String
        # contents never trigger these keywords. (Uses startswith + boundary
        # check instead of slicing code[i:] to keep this O(n).)
        if depth_p == 0 and depth_b == 0 and depth_c == 0:
            if code.startswith('endmodule', i) and _is_word_boundary(code, i + len('endmodule')):
                s = ''.join(cur).strip()
                if s:
                    stmts.append((s, start_line))
                stmts.append(('endmodule', line))
                cur, start_line = [], line + 1
                i += len('endmodule')
                continue
            if code.startswith('module', i) and _is_word_boundary(code, i + len('module')):
                s = ''.join(cur).strip()
                if s:
                    stmts.append((s, start_line))
                cur, start_line = [], line
                # 'module' — do not consume; it begins the header statement

        if ch == ';' and depth_p == 0 and depth_b == 0 and depth_c == 0:
            s = ''.join(cur).strip()
            if s:
                stmts.append((s, start_line))
            cur, start_line = [], line + 1
            i += 1
            continue

        if not cur:
            start_line = line
        cur.append(ch)
        i += 1
    s = ''.join(cur).strip()
    if s:
        stmts.append((s, start_line))
    return stmts


def _is_word_boundary(s: str, idx: int) -> bool:
    """True when position idx is a word boundary (end of string or non-word)."""
    return idx >= len(s) or not (s[idx].isalnum() or s[idx] == '_')


def _balanced_parens(s: str, start: int) -> int:
    """Return index just past the matching ')' for '(' at s[start] (or -1)."""
    depth = 0
    i = start
    while i < len(s):
        if s[i] == '(':
            depth += 1
        elif s[i] == ')':
            depth -= 1
            if depth == 0:
                return i + 1
        i += 1
    return -1


def _parse_range(tok: str) -> Tuple[Optional[int], Optional[int]]:
    """Parse '[7:0]' or '[0:7]' → (msb, lsb). Returns (None,None) if not a
    plain constant range (expressions degrade to scalar)."""
    m = re.fullmatch(r'\s*\[\s*(\d+)\s*:\s*(\d+)\s*\]\s*', tok)
    if m:
        return int(m.group(1)), int(m.group(2))
    return None, None


def _split_conns(inner: str) -> List[str]:
    """Split a connection list on top-level commas (keeps {a,b} together)."""
    out = []
    cur = []
    depth_p = depth_c = 0
    for ch in inner:
        if ch == '(':
            depth_p += 1
        elif ch == ')':
            depth_p = max(depth_p - 1, 0)
        elif ch == '{':
            depth_c += 1
        elif ch == '}':
            depth_c = max(depth_c - 1, 0)
        if ch == ',' and depth_p == 0 and depth_c == 0:
            out.append(''.join(cur).strip())
            cur = []
            continue
        cur.append(ch)
    out.append(''.join(cur).strip())
    return [c for c in out if c]


# ── Verilog parser ────────────────────────────────────────────────────────────

def parse_verilog(text: str, top: str = "") -> ParseOutcome:
    """Parse structural Verilog into a DesignContext (never executes anything)."""
    out = ParseOutcome()
    code = _strip_comments(text)
    # Treat compiler directives (`` `include``, `` `define``) as inert text.
    code = re.sub(r'(?m)^\s*`\w+.*$', ' ', code)

    modules: Dict[str, dict] = {}           # name → parsed module
    order: List[str] = []
    instantiated: Set[str] = set()          # module types instantiated by others
    cur: Optional[dict] = None
    in_block = 0                            # begin/end nesting for behavioral blocks
    block_stmts = 0

    for stmt, _ln in _split_statements(code):
        s = stmt.strip()
        if not s:
            continue

        # ── module header ────────────────────────────────────────────────────
        m = re.match(r'module\s+(' + _IDENT + r')\b', s)
        if m:
            if in_block:
                out.warnings.append(f"module '{m.group(1)}' declared inside a behavioral block — skipped")
                continue
            if cur is not None:
                out.warnings.append(f"module '{cur['name']}' missing endmodule")
            name = m.group(1).replace('\\', '')
            cur = {"name": name, "ports": [], "instances": [], "nets": {},
                   "parents": []}
            modules[name] = cur
            order.append(name)
            # Port list: between first '(' and its matching ')'
            lp = s.find('(')
            if lp != -1:
                rp = _balanced_parens(s, lp)
                if rp == -1:
                    out.errors.append(f"module '{name}': unbalanced port list")
                    cur = None
                    continue
                portlist = s[lp + 1:rp - 1]
                _parse_ansi_or_named_ports(cur, portlist)
            continue

        # ── endmodule ────────────────────────────────────────────────────────
        if s.startswith('endmodule'):
            if in_block:
                in_block = 0
            cur = None
            continue

        if cur is None:
            # statement outside any module — ignore (e.g. `timescale remnants)
            continue

        # ── behavioral block management ──────────────────────────────────────
        if in_block:
            in_block += s.count('begin') - s.count('end')
            if s.count('end') > s.count('begin'):
                in_block = max(in_block, 0)
                # possibly a standalone `end` closing the block
            block_stmts += 1
            if in_block <= 0:
                in_block = 0
            continue

        low = s.lower()
        # ── skip directives that never carry SDC-visible objects ────────────
        if re.match(r'(assign|parameter|localparam|specify|defparam|generate|'
                    r'endgenerate|primitive|endprimitive|typedef|import|package|'
                    r'endpackage|function|endfunction|task|endtask)\b', low):
            continue
        if re.match(r'(always|initial|final|fork)\b', low):
            if 'begin' in low and s.count('begin') > s.count('end'):
                in_block = 1
            continue

        # ── direction declarations ───────────────────────────────────────────
        dm = re.match(r'\s*(input|output|inout)\b(.*)', s, re.IGNORECASE)
        if dm:
            _parse_port_decl(cur, dm.group(1).lower(), dm.group(2))
            continue

        # ── net declarations ─────────────────────────────────────────────────
        nm = re.match(r'\s*(wire|tri|trireg|supply0|supply1|uwire)\b(.*)', s, re.IGNORECASE)
        if nm:
            _parse_net_decl(cur, nm.group(2))
            continue

        # ── module instance ──────────────────────────────────────────────────
        for mt in _instance_types(s):
            instantiated.add(mt)
        _parse_instances(cur, s, out)

    if cur is not None:
        out.warnings.append(f"module '{cur['name']}' missing endmodule")

    # ── Resolve positional connections against the INSTANTIATED module's port
    # order (post-pass: the module body may be declared before the instance).
    for name, md in modules.items():
        for inst in md.get("instances", []):
            tgt = modules.get(inst["module"], {})
            port_names = [p["name"] for p in tgt.get("ports", [])]
            resolved_conns = []
            for pin, expr in inst.get("conns", []):
                if pin.startswith("__pos") and pin.endswith("__"):
                    idx = int(pin[5:-2])
                    resolved_conns.append((
                        port_names[idx] if idx < len(port_names) else pin,
                        expr))
                else:
                    resolved_conns.append((pin, expr))
            inst["conns"] = resolved_conns

    out.modules_seen = order

    # ── Top module detection: a module is a top candidate only if it is never
    # instantiated by another module in this netlist.
    tops = [n for n in order if n not in instantiated]
    if not order:
        out.errors.append("no module declarations found — not a structural Verilog netlist")
        return out
    if top:
        if top not in modules:
            out.errors.append(f"requested top module '{top}' not found in netlist "
                              f"(modules: {', '.join(order) or 'none'})")
            return out
        chosen = top
    elif len(tops) == 1:
        chosen = tops[0]
    else:
        out.top_candidates = tops
        out.errors.append("multiple candidate top modules ("
                          + ", ".join(tops)
                          + ") — specify --top explicitly")
        return out

    ctx = DesignContext(top_module=chosen)
    ctx.modules = set(order)
    mod = modules[chosen]
    for p in mod["ports"]:
        ctx.ports[p["name"]] = DesignPort(p["name"], p["direction"], p["msb"], p["lsb"])
    for mn, md in modules.items():
        ctx.module_ports[mn] = [p["name"] for p in md["ports"]]
    ctx.nets = dict(mod["nets"])
    # Phase 9: per-module port directions (for driver/load classification)
    for mn, md in modules.items():
        ctx.module_port_dirs[mn] = {p["name"]: p["direction"] for p in md["ports"]}

    # ── flatten hierarchy (index by full path) ───────────────────────────────
    # Recursively expand each instance's module body so nested objects like
    # 'u_core/u_reg0/D' resolve: u_core instantiates module 'core' which in
    # turn instantiates flop 'u_reg0'. Children are indexed by parent ONCE so
    # the walk is O(instances), not O(instances²) on flat netlists.
    by_module: Dict[str, list] = {name: md.get("instances", []) for name, md in modules.items()}

    def _build(module_name: str, parent_path: str):
        for inst in by_module.get(module_name, []):
            path = (parent_path + "/" + inst["name"]) if parent_path else inst["name"]
            di = DesignInstance(path=path, name=inst["name"], module=inst["module"],
                                parent=parent_path)
            ctx.instances[path] = di
            ctx._instance_leaves.add(inst["name"])
            # pins on this instance from its connections; also record the
            # net each pin connects to (Phase 9 structural connectivity).
            for pin, expr in inst.get("conns", []):
                pin_path = path + "/" + pin
                ctx.pins.add(pin_path)
                leaf = _net_base(expr)
                if leaf:
                    ctx.pin_nets.setdefault(pin_path, set()).add(leaf)
                    ctx.net_pins.setdefault(leaf, set()).add(pin_path)
                if leaf and leaf not in ctx.nets:
                    ctx.nets[leaf] = (None, None)
            if inst["module"] in modules:
                _build(inst["module"], path)

    _build(chosen, "")
    out.context = ctx
    return out


def _parse_ansi_or_named_ports(mod: dict, portlist: str) -> None:
    """Parse a module port list — ANSI ('input a, output [3:0] b') or named
    ('a, b'). Bare names get direction resolved later from body declarations."""
    for item in _split_conns(portlist):
        item = item.strip()
        if not item:
            continue
        dm = re.match(r'\s*(input|output|inout)\b(.*)', item, re.IGNORECASE)
        if dm:
            dirn = dm.group(1).lower()
            rest = _strip_kw(dm.group(2))
            names, msb, lsb = _parse_name_list(rest)
            for nm in names:
                mod["ports"].append({"name": nm, "direction": dirn, "msb": msb, "lsb": lsb})
        else:
            nm, msb, lsb = _first_name(item)
            mod["ports"].append({"name": nm, "direction": "", "msb": msb, "lsb": lsb})


def _strip_kw(s: str) -> str:
    """Remove leading wire/reg/logic/signed keywords from a decl tail."""
    s = s.strip()
    while True:
        m = re.match(r'\s*(wire|reg|logic|signed|unsigned|integer|real)\b', s, re.IGNORECASE)
        if not m:
            break
        s = s[m.end():].strip()
    return s


def _parse_name_list(rest: str) -> Tuple[List[str], Optional[int], Optional[int]]:
    """Parse 'rest' of a declaration into (names, msb, lsb) honoring [r:r]."""
    msb = lsb = None
    rm = re.match(r'\s*\[.*?\]\s*', rest)
    if rm:
        msb, lsb = _parse_range(rm.group(0))
        rest = rest[rm.end():]
    names = []
    for tok in _split_conns(rest):
        tok = tok.strip()
        tok = re.sub(r'\s*=.*$', '', tok)   # strip '= init'
        if not tok:
            continue
        # strip bit selects on the port name itself (rare)
        tok = re.sub(r'\[.*?\]$', '', tok)
        if tok:
            names.append(tok.replace('\\', ''))
    return names, msb, lsb


def _first_name(s: str) -> Tuple[str, Optional[int], Optional[int]]:
    names, msb, lsb = _parse_name_list(s)
    if not names:
        return "", None, None
    return names[0], msb, lsb


def _parse_port_decl(mod: dict, dirn: str, rest: str) -> None:
    rest = _strip_kw(rest)
    names, msb, lsb = _parse_name_list(rest)
    for nm in names:
        # resolve direction for non-ANSI ports declared in body
        for p in mod["ports"]:
            if p["name"] == nm and not p["direction"]:
                p["direction"] = dirn
                p["msb"], p["lsb"] = msb, lsb
                break
        else:
            mod["ports"].append({"name": nm, "direction": dirn, "msb": msb, "lsb": lsb})


def _parse_net_decl(mod: dict, rest: str) -> None:
    names, msb, lsb = _parse_name_list(rest)
    for nm in names:
        mod["nets"][nm] = (msb, lsb)
        mod.setdefault("net_order", []).append(nm)


def _net_base(expr: str) -> str:
    """Extract the base net name from a connection expression."""
    e = expr.strip()
    e = re.sub(r'^\{.*\}$', '', e)          # concatenation → no single net
    e = re.sub(r'\[.*?\]$', '', e)          # bit-select → base
    e = re.sub(r"['\"]?[0-9]+'[bodh][0-9a-fA-FxXzZ_]*$", '', e)  # literal
    if not e or not re.match(r'^' + _IDENT + r'$', e):
        return ""
    return e.replace('\\', '')


# Declaration keywords that share the IDENT IDENT shape but are not module
# instances. Single source of truth for _parse_instances and _instance_types.
_NON_INSTANCE_TYPES = frozenset({
    "input", "output", "inout", "wire", "tri", "trireg", "supply0",
    "supply1", "uwire", "assign", "reg", "logic", "integer", "real",
    "time", "genvar", "always", "initial", "parameter", "localparam",
})


def _parse_instances(mod: dict, s: str, out: ParseOutcome) -> None:
    """Parse one statement as a module instance or list of instances."""
    # multi-instance: 'type u1(...), u2(...);' → split on top-level commas at
    # paren depth 0, where each chunk matches 'name(...)'.
    chunks = _split_conns(s)
    for chunk in chunks:
        chunk = chunk.strip()
        if not chunk:
            continue
        m = re.match(r'^(' + _IDENT + r')\s+(' + _IDENT + r')\s*(?:\((.*)\))?$',
                     chunk, re.DOTALL)
        if not m:
            continue
        mtype = m.group(1).replace('\\', '')
        iname = m.group(2).replace('\\', '')
        inner = m.group(3) or ""
        # declarations that share the IDENT IDENT shape but are not instances
        if mtype.lower() in _NON_INSTANCE_TYPES:
            continue
        inst = {"name": iname, "module": mtype, "parent": "", "conns": []}
        # determine connections: named .pin(expr) or positional
        conns = _split_conns(inner)
        pos_idx = 0
        for conn in conns:
            conn = conn.strip()
            if not conn:
                continue
            cm = re.match(r'^\.(' + _IDENT + r')\s*(?:\((.*)\))?$', conn, re.DOTALL)
            if cm:
                inst["conns"].append((cm.group(1).replace('\\', ''),
                                      (cm.group(2) or "").strip()))
            else:
                # positional — resolved against the module port order in a
                # post-pass (ports may be declared after the instance)
                pin = f"__pos{pos_idx}__"
                inst["conns"].append((pin, conn))
                pos_idx += 1
        mod["instances"].append(inst)


def _instance_types(s: str) -> List[str]:
    """Return the module types instantiated in one statement.

    Used to detect which modules are NOT top candidates. Conservative: any
    ``IDENT IDENT (...)`` pattern that is not a known declaration keyword.
    """
    types = []
    for chunk in _split_conns(s):
        chunk = chunk.strip()
        m = re.match(r'^(' + _IDENT + r')\s+(' + _IDENT + r')\s*(?:\(.*\))?$',
                     chunk, re.DOTALL)
        if m:
            t = m.group(1).replace('\\', '')
            if t.lower() not in _NON_INSTANCE_TYPES:
                types.append(t)
    return types


# ── Collection resolution ─────────────────────────────────────────────────────

RESOLVED = "RESOLVED"
EMPTY = "EMPTY"
UNDEFINED = "UNDEFINED"
UNSUPPORTED = "UNSUPPORTED"

# Matches [get_ports expr] where expr may contain nested bit-selects like
# 'data_in[9]' or braces '{a b}' — one level of nesting is supported.
_COLL_RE = re.compile(
    r'\[(get_ports|get_pins|get_cells|get_nets|all_inputs|all_outputs|all_ports|'
    r'all_registers|all_cells|all_nets|all_clocks)'
    r'\s*((?:[^\[\]]|\[[^\[\]]*\])*)\]', re.IGNORECASE)


@dataclass
class Resolution:
    kind: str                       # RESOLVED | EMPTY | UNDEFINED | UNSUPPORTED
    matches: List[str] = field(default_factory=list)
    expr: str = ""
    message: str = ""


def resolve_collection(kind: str, args: str, ctx: DesignContext) -> Resolution:
    """Resolve one SDC collection expression against the design context.

    ``kind``: get_ports | get_pins | get_cells | get_nets | all_inputs |
              all_outputs | all_ports. ``args`` is the inner collection text,
              e.g. 'clk', '{a b}', 'data_*', 'u_core/*', 'data_in[3]'.
    """
    args = args.strip()
    kind_l = kind.lower()

    # dynamic all_* collections — always resolvable when design loaded (an
    # empty instance/net pool is a degenerate but valid design; all_* still
    # resolves as a class). all_clocks is SDC-defined (not netlist-resolvable)
    # and is handled/skipped by the caller.
    if kind_l in ("all_inputs", "all_outputs", "all_ports"):
        if kind_l == "all_inputs":
            return Resolution(RESOLVED, sorted(p for p, dp in ctx.ports.items()
                                               if dp.direction == "input"), expr=args)
        if kind_l == "all_outputs":
            return Resolution(RESOLVED, sorted(p for p, dp in ctx.ports.items()
                                               if dp.direction == "output"), expr=args)
        return Resolution(RESOLVED, sorted(ctx.ports), expr=args)
    if kind_l in ("all_registers", "all_cells"):
        return Resolution(RESOLVED, sorted(ctx.instances), expr=args)
    if kind_l == "all_nets":
        return Resolution(RESOLVED, sorted(ctx.nets), expr=args)
    if kind_l == "all_clocks":
        return Resolution(UNSUPPORTED, expr=args,
                          message="all_clocks is SDC-defined, not netlist-resolvable")

    exprs = _expand_collection_args(args)
    if not exprs:
        return Resolution(EMPTY, expr=args, message="empty collection expression")

    matches: List[str] = []
    unresolved: List[str] = []
    for e in exprs:
        base, bit = _split_bit_select(e)
        if any(ch in base for ch in '*?['):
            # wildcard
            if kind_l == "get_cells":
                hits = _glob_cells(base, ctx)
            elif kind_l == "get_pins":
                hits = _glob_pins(base, ctx)
            else:
                hits = _glob_names(base, _kind_pool(kind_l, ctx))
            matches.extend(hits)
            if not hits:
                unresolved.append(("EMPTY", e))
            continue
        # explicit name
        found, why = _exact_lookup(kind_l, base, bit, ctx)
        if found:
            matches.append(found)
        else:
            unresolved.append(("UNDEFINED" if why == "missing" else "EMPTY", e))

    if matches and not unresolved:
        return Resolution(RESOLVED, sorted(set(matches)), expr=args)
    if matches:
        return Resolution(RESOLVED, sorted(set(matches)), expr=args,
                          message="partially resolved")
    if unresolved:
        worst = unresolved[0][0]
        return Resolution(worst, expr=args,
                          message=f"{worst}: {', '.join(u[1] for u in unresolved)}")
    return Resolution(UNSUPPORTED, expr=args, message="unsupported expression")


def _expand_collection_args(args: str) -> List[str]:
    """'{a b}', 'a b', '[get_ports {a b}]' → ['a', 'b']."""
    a = args.strip()
    if a.startswith('{') and a.endswith('}'):
        a = a[1:-1]
    a = re.sub(r'^\[.*?\]', '', a)          # strip wrapped bracket expr
    return [t for t in a.split() if t]


def _split_bit_select(name: str):
    """Split 'data_in', 'data_in[3]', 'data_in[*]', 'data_in[3:0]'.

    Returns ``(base, spec)`` where ``spec`` is:
      None   — whole object (scalar or whole bus)
      int    — single bit
      '*'    — all bits
      (lo, hi) — inclusive bit range (lo <= hi)
    """
    m = re.match(r'^(.*?)(?:\[([^\]]*)\])?$', name)
    base = m.group(1)
    inner = m.group(2)
    if inner is None or inner == '':
        return base, None
    if inner == '*':
        return base, '*'
    rm = re.match(r'^\s*(\d+)\s*:\s*(\d+)\s*$', inner)
    if rm:
        a, b = int(rm.group(1)), int(rm.group(2))
        return base, (min(a, b), max(a, b))
    dm = re.match(r'^\s*(\d+)\s*$', inner)
    if dm:
        return base, int(dm.group(1))
    return base, None


def _kind_pool(kind: str, ctx: DesignContext):
    if kind == "get_ports":
        return set(ctx.ports)
    if kind == "get_cells":
        return set(ctx.instances)
    if kind == "get_pins":
        return ctx.pins
    if kind == "get_nets":
        return set(ctx.nets)
    return set()


def _glob_names(pattern: str, pool: Set[str]) -> List[str]:
    out = []
    for name in pool:
        if fnmatch.fnmatchcase(name, pattern):
            out.append(name)
    return out


def _glob_cells(pattern: str, ctx: DesignContext) -> List[str]:
    """get_cells wildcard — supports hierarchical 'u_core/*' patterns."""
    out = []
    if '/' in pattern:
        for path in ctx.instances:
            if fnmatch.fnmatchcase(path, pattern):
                out.append(path)
    else:
        leaf_pat = pattern
        if '*' in pattern or '?' in pattern:
            for path, inst in ctx.instances.items():
                if fnmatch.fnmatchcase(inst.name, leaf_pat):
                    out.append(path)
        else:
            # bare name — exact instance path OR leaf name
            if pattern in ctx.instances:
                out.append(pattern)
            elif pattern in ctx._instance_leaves:
                out.extend(p for p, i in ctx.instances.items() if i.name == pattern)
    return out


def _glob_pins(pattern: str, ctx: DesignContext) -> List[str]:
    out = []
    if '/' in pattern:
        for pin in ctx.pins:
            if fnmatch.fnmatchcase(pin, pattern):
                out.append(pin)
    else:
        for pin in ctx.pins:
            if fnmatch.fnmatchcase(pin.rsplit('/', 1)[-1], pattern):
                out.append(pin)
    return out


def _exact_lookup(kind: str, base: str, bit, ctx: DesignContext):
    """Return (match_or_None, why) where why ∈ {'missing','empty','unsupported'}.

    ``bit`` may be None (whole), int, '*', or (lo, hi) range. A range/star is
    valid when it overlaps the declared bus (or the object is scalar).
    """
    if kind == "get_ports":
        if base not in ctx.ports:
            return None, "missing"
        dp = ctx.ports[base]
        if bit is not None and bit != '*' and dp.is_bus():
            lo, hi = min(dp.lsb, dp.msb), max(dp.lsb, dp.msb)
            if isinstance(bit, tuple):
                if bit[1] < lo or bit[0] > hi:
                    return None, "missing"      # range fully outside bus
            elif bit < lo or bit > hi:
                return None, "missing"          # bit out of range
        return base, "ok"
    if kind == "get_cells":
        if base in ctx.instances:
            return base, "ok"
        if base in ctx._instance_leaves:
            return base, "ok"
        return None, "missing"
    if kind == "get_pins":
        if base in ctx.pins:
            return base, "ok"
        return None, "missing"
    if kind == "get_nets":
        if base in ctx.nets:
            msb, lsb = ctx.nets[base]
            if bit is not None and bit != '*' and msb is not None and lsb is not None:
                lo, hi = min(lsb, msb), max(lsb, msb)
                if isinstance(bit, tuple):
                    if bit[1] < lo or bit[0] > hi:
                        return None, "missing"
                elif bit < lo or bit > hi:
                    return None, "missing"
            return base, "ok"
        return None, "missing"
    return None, "unsupported"


# ── SDC reference validation (design-aware) ───────────────────────────────────

@dataclass
class RefFinding:
    sev: str            # error | warning
    code: str
    msg: str
    line: int = 0


def validate_design_references(text: str, ctx: DesignContext) -> List[RefFinding]:
    """Resolve every supported collection in the SDC against ``ctx``.

    Called ONLY when design context is present. Produces:
      SDC-055 — explicit design object not found (error)
      SDC-056 — wildcard collection matched nothing (warning)
      SDC-057 — invalid hierarchy reference (error)
      SDC-058 — top module issue is reported by the parser, not here
      SDC-059 — data-pattern port left unconstrained (warning, conservative)

    Any expression outside the supported resolver subset is silently left
    NETLIST_REQUIRED (never flagged, never claimed resolved).
    """
    from sdc_preprocess import preprocess_sdc

    findings: List[RefFinding] = []
    logical = preprocess_sdc(text)

    for cmd in logical:
        ctext = cmd.text
        for m in _COLL_RE.finditer(ctext):
            kind = m.group(1).lower()
            args = m.group(2).strip()
            res = resolve_collection(kind, args, ctx)
            if res.kind == RESOLVED:
                continue
            if res.kind == UNDEFINED:
                findings.append(RefFinding(
                    "error", "SDC-055",
                    f"[{kind} {args}] does not resolve — no matching "
                    f"{'port' if kind == 'get_ports' else 'cell' if kind == 'get_cells' else 'pin' if kind == 'get_pins' else 'net'} "
                    f"exists in design '{ctx.top_module}'.",
                    line=cmd.start_line))
            elif res.kind == EMPTY:
                findings.append(RefFinding(
                    "warning", "SDC-056",
                    f"[{kind} {args}] wildcard matched nothing in design "
                    f"'{ctx.top_module}' — the collection is empty.",
                    line=cmd.start_line))
        # hierarchy sanity for pin/cell paths (SDC-057)
        for pm in re.finditer(r'\[(get_pins|get_cells)\s+([^\]]*)\]', ctext):
            args = _expand_collection_args(pm.group(2).strip())
            for a in args:
                if '*' in a or '?' in a:
                    continue
                base = re.sub(r'\[.*?\]$', '', a)
                if '/' in base:
                    parent = '/'.join(base.split('/')[:-1])
                    if parent and parent not in ctx.instances:
                        findings.append(RefFinding(
                            "error", "SDC-057",
                            f"invalid hierarchy reference '{base}': instance "
                            f"'{parent}' does not exist in design '{ctx.top_module}'.",
                            line=cmd.start_line))

    # ── SDC-059 unconstrained data-pattern ports (conservative) ──────────────
    constrained_in = set()
    constrained_out = set()
    for cmd in logical:
        for dm in re.finditer(r'set_input_delay[^;]*\[get_ports\s+([^\]]*)\]', cmd.text):
            for nm in _expand_collection_args(dm.group(1)):
                constrained_in.add(nm)
        for dm in re.finditer(r'set_output_delay[^;]*\[get_ports\s+([^\]]*)\]', cmd.text):
            for nm in _expand_collection_args(dm.group(1)):
                constrained_out.add(nm)
        for cm in re.finditer(r'create_clock[^;]*\[get_ports\s+([^\]]*)\]', cmd.text):
            for nm in _expand_collection_args(cm.group(1)):
                constrained_in.add(nm)   # clock ports are exempt

    for pname, dp in ctx.ports.items():
        if not _looks_like_data_port(pname):
            continue
        # Phase 9: structural evidence overrides the name heuristic — a port
        # whose net provably drives/loads instance clock/reset/scan/control
        # pins is EXEMPT even when the name suggests data (kills false
        # positives without suppressing genuine data ports).
        pclass, _sev = classify_port_structure(pname, ctx)
        if pclass in ("CLOCK", "RESET", "SCAN", "TEST", "CONSTANT",
                      "CONTROL", "INOUT"):
            continue
        # A port with STRUCTURAL data evidence (its net connects to instance
        # D/Q/DIN/… pins) is owned by the Phase 9 coverage engine (SDC-064/
        # SDC-065). SDC-059 remains the NAME-heuristic fallback for data-named
        # ports whose intent is only inferred from the name — never both, so
        # one unconstrained port never produces duplicate findings.
        if _has_data_pin_evidence(pname, ctx):
            continue
        if dp.direction == "input" and pname not in constrained_in:
            findings.append(RefFinding(
                "warning", "SDC-059",
                f"input port '{pname}' has no set_input_delay — external "
                f"setup/hold at this boundary is unconstrained.",
                line=0))
        elif dp.direction == "output" and pname not in constrained_out:
            findings.append(RefFinding(
                "warning", "SDC-059",
                f"output port '{pname}' has no set_output_delay — external "
                f"setup/hold at this boundary is unconstrained.",
                line=0))

    return findings


def _has_data_pin_evidence(name: str, ctx: "DesignContext") -> bool:
    """True when the port's net connects to an instance data-role pin.

    D/Q/DIN/DOUT/… pins are the structural data indicator the coverage engine
    (SDC-064/065) relies on. Used to keep SDC-059 (name heuristic) and the
    structural rules from both firing on the same port.
    """
    for pin_path in ctx.net_pins.get(name, set()):
        if _pin_role(ctx.pin_name(pin_path)) == "DATA":
            return True
    return False


def _looks_like_data_port(name: str) -> bool:
    """Conservative heuristic: is this port a data/address boundary port?

    Excludes clock/reset/scan/test/control-ish names to avoid false positives.
    """
    low = name.lower()
    if any(k in low for k in ("clk", "clock", "rst", "reset", "scan", "test",
                              "mode", "en", "pwr", "vdd", "vss", "gnd")):
        return False
    tokens = re.split(r'[_\[\]{}./]+', low)
    for tok in tokens:
        stem = re.sub(r'\d+$', '', tok)
        if stem in ("data", "addr", "bus", "wdata", "rdata", "din", "dout",
                    "in", "out", "input", "output", "i", "o", "q", "d"):
            return True
    return False


# ── Phase 9: structural port classification ──────────────────────────────────

# Pin-name role hints used to classify a top-level port from the instance pins
# its net connects to. Names are EVIDENCE, never authoritative — a port with
# contradictory evidence stays UNKNOWN rather than guessing.
_PIN_ROLE = {
    # CLK/CK/CLOCK pins: input ports feeding these are clock ports
    "clk": "CLOCK", "ck": "CLOCK", "clock": "CLOCK", "clkin": "CLOCK",
    "gclk": "CLOCK", "pclk": "CLOCK",
    # reset pins
    "rst": "RESET", "rstn": "RESET", "reset": "RESET", "resetn": "RESET",
    "rn": "RESET", "arstn": "RESET", "arst": "RESET",
    "rst_n": "RESET", "reset_n": "RESET", "arst_n": "RESET",
    # scan / test pins
    "se": "SCAN", "si": "SCAN", "so": "SCAN", "scan_in": "SCAN",
    "scan_out": "SCAN", "scanen": "SCAN", "te": "TEST", "test": "TEST",
    "testen": "TEST", "test_mode": "TEST", "testmode": "TEST",
    # data pins (input-side: D/DIN; output-side: Q/QN/DOUT)
    "d": "DATA", "din": "DATA", "di": "DATA", "data": "DATA",
    "a": "DATA", "b": "DATA",
    "q": "DATA", "qn": "DATA", "dout": "DATA", "do": "DATA",
    "o": "DATA", "out": "DATA", "y": "DATA",
    # control pins
    "en": "CONTROL", "enable": "CONTROL", "oe": "CONTROL",
    "sel": "CONTROL", "s": "CONTROL", "cs": "CONTROL", "we": "CONTROL",
    "cfg": "CONTROL", "config": "CONTROL",
    # constant / config pins
    "tie": "CONSTANT", "tiehi": "CONSTANT", "tielo": "CONSTANT",
    "strap": "CONSTANT", "const": "CONSTANT",
}


def _pin_role(pin_name: str) -> str:
    """Role hint for an instance pin name (case-insensitive suffix match)."""
    low = pin_name.lower()
    if low in _PIN_ROLE:
        return _PIN_ROLE[low]
    for suffix, role in (("clk", "CLOCK"), ("rstn", "RESET"), ("rst", "RESET"),
                         ("rst_n", "RESET"), ("reset_n", "RESET"), ("arst_n", "RESET"),
                         ("scan", "SCAN"), ("test", "TEST"), ("din", "DATA"),
                         ("dout", "DATA"), ("data", "DATA"), ("enable", "CONTROL"),
                         ("mode", "CONTROL"), ("sel", "CONTROL"), ("tie", "CONSTANT"),
                         ("strap", "CONSTANT")):
        # The suffix must start at a boundary so 'contest' is not a 'test' pin
        # and 'sclk' is not silently treated as 'clk'. Underscore/digit
        # prefixes (u_test, clk_sel, en1) are valid boundaries.
        if low.endswith(suffix) and (
                len(low) == len(suffix)
                or not (low[-len(suffix) - 1].isalnum())):
            return role
    return ""


# Role precedence: a port that drives a CLOCK pin AND a D pin is a clock
# (clock nets legitimately also load nothing else; keep the strictest hint).
_ROLE_PRECEDENCE = ("CLOCK", "RESET", "SCAN", "TEST", "CONSTANT", "CONTROL", "DATA")


def _name_class(name: str) -> str:
    """Name-only class hint ('' when inconclusive). Evidence, not authority.

    Keywords match as TOKENS (start/end or `_`/digit delimiters), never as
    substrings: 'en' must not match 'open'/'den'/'length', and 'rst' must not
    match 'burster'. 'data_en' still matches 'en' (enable token).
    """
    low = name.lower()
    for key, cls in (("clk", "CLOCK"), ("clock", "CLOCK"), ("rst", "RESET"),
                     ("reset", "RESET"), ("scan", "SCAN"), ("test", "TEST"),
                     ("jtag", "TEST"), ("tck", "TEST"), ("trst", "TEST"),
                     ("mode", "CONTROL"), ("cfg", "CONTROL"), ("en", "CONTROL"),
                     ("tie", "CONSTANT"), ("strap", "CONSTANT"),
                     ("pwr", "CONSTANT"), ("vdd", "CONSTANT"), ("vss", "CONSTANT"),
                     ("gnd", "CONSTANT")):
        if re.search(r'(?:^|[_0-9])' + re.escape(key) + r'(?:[_0-9]|$)', low):
            return cls
    if _looks_like_data_port(name):
        return "DATA"
    return ""


def classify_port_structure(name: str, ctx: "DesignContext") -> tuple:
    """Classify a top-level port from structural evidence + name fallback.

    Returns ``(port_class, evidence)`` where port_class ∈ {CLOCK, RESET,
    SCAN, TEST, CONSTANT, CONTROL, DATA, INOUT, UNKNOWN}.

    Evidence precedence (safest-first):
      1. inout declaration → INOUT
      2. SPECIFIC structural role from instance pins (CLOCK/RESET/SCAN/TEST/…
         from pins named CLK/RST/SE/…; DATA from D/DIN/Q/DOUT/…) — strongest
      3. EXEMPT-CLASS name hint — overrides *generic* DATA structural evidence
         (a constant/strap port named ``strap_0`` connected to a mux ``b`` pin
         is a strap, not data) but NOT a specific structural role
      4. name hint (DATA / other)
      5. UNKNOWN
    """
    dp = ctx.ports.get(name)
    if dp is not None and dp.direction == "inout":
        return "INOUT", "inout port"

    # Structural evidence: pins connected to the net of the same name.
    roles: List[str] = []
    for pin_path in ctx.net_pins.get(name, set()):
        role = _pin_role(ctx.pin_name(pin_path))
        if role:
            roles.append(role)
    specific = next((r for r in _ROLE_PRECEDENCE if r != "DATA" and r in roles), "")
    if specific:
        return specific, f"net drives/loads instance {specific.lower()} pin(s)"

    # Exempt-class name hint overrides generic-pin DATA structural evidence:
    # a port named like a strap/test/control port is that, even when it feeds
    # a mux a/b pin (which is not a reliable data indicator).
    name_cls = _name_class(name)
    if name_cls in ("CLOCK", "RESET", "SCAN", "TEST", "CONSTANT", "CONTROL", "INOUT"):
        return name_cls, f"name suggests {name_cls.lower()}"
    if "DATA" in roles:
        return "DATA", "net drives/loads instance data pin(s)"
    if name_cls == "DATA":
        return "DATA", "name suggests data"
    return "UNKNOWN", "no structural or name evidence"
