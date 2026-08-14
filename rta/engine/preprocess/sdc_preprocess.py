"""
Shared SDC/Tcl lexical preprocessing.

Normalizes raw SDC text so all consumers (checker, converter, clock relations,
etc.) interpret the same logical commands instead of each module maintaining its
own regexes over raw text.

Provides:
  - preprocess_sdc()   : comment stripping + backslash-newline joining + provenance
  - LogicalCommand     : (text, start_line, end_line) dataclass
  - parse_number()     : full numeric literal parsing (incl. scientific notation)
  - NUM_PATTERN        : regex fragment used by consumers for -flag <number>
  - parse_collection() : braced / bracketed Tcl collection → list of names
  - Bounded Tcl scalar variable support: ``set NAME VALUE`` assignments with
    order-aware ``$NAME`` / ``${NAME}`` substitution

Scope is deliberately limited to verified lexical requirements. This is NOT a
Tcl interpreter. Only plain scalar ``set`` assignments are evaluated; no
procedures, expressions, command substitution, or file/exec access.
"""

import re
from dataclasses import dataclass

# ── Numeric literals ──────────────────────────────────────────────────────────
# Covers: 10, 10.0, 0.25, .25, 2.5e-1, 1e-3, 1E+2, -0.25 (all forms used by SDC)
_NUM_FRAG = r'[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?'
NUM_PATTERN = _NUM_FRAG
_NUM_RE = re.compile(_NUM_FRAG)
_FLAG_NUM_RE = re.compile(r'(-\w+)\s+(' + _NUM_FRAG + r')')


def parse_number(text: str) -> float:
    """Parse the first complete numeric literal in ``text`` (or 0.0 if none).

    Handles integer, decimal, and scientific-notation forms. ``2.5e-1`` → 0.25.
    """
    m = _NUM_RE.search(text)
    return float(m.group(0)) if m else 0.0


def extract_flag_numbers(text: str):
    """Return list of (flag, value) pairs for every '-flag <number>' in text.

    e.g. '-setup 100.0 -hold 50.0' → [('-setup', 100.0), ('-hold', 50.0)].
    Values are parsed with full numeric semantics (scientific notation safe).
    """
    out = []
    for fm in _FLAG_NUM_RE.finditer(text):
        flag = fm.group(1)
        try:
            out.append((flag, float(fm.group(2))))
        except ValueError:
            continue
    return out


# ── Bounded Tcl scalar variables ─────────────────────────────────────────────
# Supported subset (documented in PHASE4 report):
#   set NAME VALUE            scalar assignment (NAME = [A-Za-z_][A-Za-z0-9_]*)
#   $NAME  /  ${NAME}         substitution, order-aware, only for known names
# NOT supported: expressions, arrays, namespaces, procs, command substitution.
# Unresolved $TOKENS are preserved verbatim so downstream rules can flag them.
_VAR_NAME = r'[A-Za-z_][A-Za-z0-9_]*'
# Matches $NAME or ${NAME} (longest identifier wins, so $CLK2 != $CLK + '2')
_VAR_REF = re.compile(r'\$(' + _VAR_NAME + r'|\{' + _VAR_NAME + r'\})')
# Only the bare Tcl 'set' command (not set_input_delay, set_clock_groups, ...)
_SET_CMD = re.compile(r'^set\s+(' + _VAR_NAME + r')\s+(.+?)\s*$')


def _clean_set_value(value: str) -> str:
    """Strip one layer of surrounding braces or double quotes from a set value.

    ``{core clk}`` → ``core clk``; ``"2.5e-1"`` → ``2.5e-1``; ``2.5`` → ``2.5``.
    """
    v = value.strip()
    if len(v) >= 2 and ((v[0] == '{' and v[-1] == '}') or (v[0] == '"' and v[-1] == '"')):
        return v[1:-1].strip()
    return v


def _substitute_vars(text: str, env: dict) -> str:
    """Substitute ``$NAME``/``${NAME}`` in ``text`` using ``env``.

    Follows Tcl substitution rules for the supported subset:
      - ``$`` inside ``{...}`` braces is literal (braces suppress substitution).
      - ``$`` inside double quotes IS substituted (as in Tcl).
      - A backslash escapes the next char (``\$`` is a literal dollar).
      - Unknown names are left untouched (deterministic, no silent 0/empty).
    """
    out: list = []
    if '$' not in text:          # fast path — no variables in this command
        return text
    i, n = 0, len(text)
    brace_depth = 0
    in_quote = None              # None | '"' | "'" — braces inside quotes are literal
    while i < n:
        ch = text[i]
        if ch == '\\' and i + 1 < n:
            out.append(text[i:i + 2])
            i += 2
            continue
        if in_quote:
            # Inside double/single quotes: braces are literal characters and
            # '\' escapes were already consumed above; '$' IS still substituted
            # (Tcl substitutes variables inside double-quoted strings).
            if ch == in_quote:
                in_quote = None
                out.append(ch)
                i += 1
                continue
            if ch == '$':
                m = _VAR_REF.match(text, i)
                if m:
                    name = m.group(1)
                    if name.startswith('{'):
                        name = name[1:-1]
                    if name in env:
                        out.append(env[name])
                        i += m.end() - m.start()
                        continue
            out.append(ch)
            i += 1
            continue
        if ch in ('"', "'"):
            in_quote = ch
            out.append(ch)
            i += 1
            continue
        if ch == '{':
            brace_depth += 1
            out.append(ch)
            i += 1
            continue
        if ch == '}':
            brace_depth = max(brace_depth - 1, 0)
            out.append(ch)
            i += 1
            continue
        if ch == '$' and brace_depth == 0:
            m = _VAR_REF.match(text, i)
            if m:
                name = m.group(1)
                if name.startswith('{'):
                    name = name[1:-1]
                if name in env:
                    out.append(env[name])
                    i += m.end() - m.start()
                    continue
        out.append(ch)
        i += 1
    return ''.join(out)


def _resolve_variables(commands: list) -> list:
    """Order-aware bounded Tcl scalar variable resolution over logical commands.

    Walks commands in file order; a ``set NAME VALUE`` assignment only affects
    subsequent commands. ``set`` commands are kept in the output (they are inert
    to the SDC consumers) so provenance and line numbers are preserved.
    """
    env: dict = {}
    resolved: list = []
    for cmd in commands:
        new_text = _substitute_vars(cmd.text, env)
        m = _SET_CMD.match(new_text)
        if m:
            env[m.group(1)] = _clean_set_value(m.group(2))
        resolved.append(LogicalCommand(new_text, cmd.start_line, cmd.end_line,
                                       list(cmd.diagnostics or [])))
    return resolved


# ── Tcl collections ───────────────────────────────────────────────────────────
_GET_CLOCK_PAT = re.compile(r'\[(?:get_clocks|get_ports|get_pins|get_cells)\s+([^\]]*)\]')


def parse_collection(text: str):
    """Parse a Tcl collection token into a list of names.

    Handles: ``clk_a`` → ['clk_a']; ``{clk_a clk_b}`` → ['clk_a','clk_b'];
    ``[get_clocks {clk_a clk_b}]`` → ['clk_a','clk_b'];
    ``[get_clocks clk_a]`` → ['clk_a'].
    """
    inner = text.strip()
    m = _GET_CLOCK_PAT.search(inner)
    if m:
        inner = m.group(1).strip()
    if inner.startswith('{') and inner.endswith('}'):
        inner = inner[1:-1]
    return [tok for tok in inner.split() if tok]


# ── Logical command model ─────────────────────────────────────────────────────

@dataclass
class LogicalCommand:
    """One logical SDC command with original source provenance."""
    text: str       # command text (comments removed, continuations joined)
    start_line: int  # 1-based first physical line
    end_line: int    # 1-based last physical line
    diagnostics: list = None  # lexical diagnostics attached during preprocessing

    def __post_init__(self):
        if self.diagnostics is None:
            self.diagnostics = []


def preprocess_sdc(text: str) -> list:
    """Split raw SDC text into logical commands.

    Steps (per Tcl(n) rules 9/10):
      1. Strip comments. A '#' begins a comment only at the start of a command
         (start of line, or after whitespace/';'). '#' inside braces or square
         brackets is literal. Trailing inline comments are removed.
      2. Join backslash-newline continuations into one logical command (a
         backslash-newline is replaced by a single space).
      3. Attach start/end physical-line provenance to every logical command.

    Returns a list of LogicalCommand. A blank result list means "no commands".

    Lexical diagnostics (``LogicalCommand.diagnostics``): when the file ends
    inside an unclosed Tcl bracket/brace (or with a dangling backslash
    continuation), the affected logical command carries an explicit diagnostic
    naming the opening line so the malformed construct is never silently
    merged away. This mirrors Tcl(n) rule 10: an unclosed bracket/brace is a
    syntax error, and the preprocessor reports it instead of hiding it.
    """
    commands: list = []
    cur_buf: list = []
    cur_start: int = 0
    in_brace = 0
    in_bracket = 0
    open_brace_line = 0   # physical line where the current { ... } span opened
    open_bracket_line = 0  # physical line where the current [ ... ] span opened
    dangling_cont = False  # a continuation backslash is pending when EOF hits

    lines = text.split('\n')
    for idx, raw in enumerate(lines):
        lineno = idx + 1
        line = raw
        # ── Track brace/bracket depth across the physical line ─────────────
        # (used only to decide whether '#' is a comment; braces can span lines)
        stripped = line.lstrip()
        if stripped.startswith('#') and in_brace == 0 and in_bracket == 0:
            # Full-line comment terminates the current logical command.
            if cur_buf:
                commands.append(LogicalCommand(
                    ' '.join(cur_buf).strip(), cur_start, lineno - 1))
                cur_buf, cur_start = [], 0
            dangling_cont = False
            continue

        # Remove comments on this physical line (respecting braces/brackets),
        # then detect continuation on the cleaned line so a backslash that
        # precedes a trailing comment is not mistaken for a continuation.
        cleaned = _strip_line_comment(line, in_brace, in_bracket)
        cont = bool(re.search(r'\\\s*$', cleaned))

        if not cur_buf:
            cur_start = lineno
        # Per Tcl rule 9, a backslash-newline is replaced by a single space:
        # drop the trailing backslash (and any trailing whitespace) when the
        # line is a continuation line.
        cleaned = cleaned.rstrip()
        if cont:
            cleaned = cleaned.rstrip('\\')
        cur_buf.append(cleaned.strip())
        dangling_cont = cont

        # Update depth after collecting tokens (opening/closing chars).
        in_brace += cleaned.count('{') - cleaned.count('}')
        in_bracket += cleaned.count('[') - cleaned.count(']')
        # Remember the physical line where the current unbalanced span opened.
        if in_brace > 0 and open_brace_line == 0:
            open_brace_line = lineno
        if in_bracket > 0 and open_bracket_line == 0:
            open_bracket_line = lineno
        in_brace = max(in_brace, 0)
        in_bracket = max(in_bracket, 0)

        if cont and in_brace == 0 and in_bracket == 0:
            continue

        # Command boundary: logical command ends at a non-continued line when
        # we are not inside an open brace/bracket.
        if not cont and in_brace == 0 and in_bracket == 0:
            commands.append(LogicalCommand(
                ' '.join(cur_buf).strip(), cur_start, lineno))
            cur_buf, cur_start = [], 0
            open_brace_line = 0
            open_bracket_line = 0
            dangling_cont = False

    if cur_buf:
        diags = []
        if in_bracket > 0:
            diags.append(
                f"unclosed '[' opened at line {open_bracket_line} — the bracket "
                f"never closes, so lines {open_bracket_line}..{len(lines)} were "
                f"merged into this command; add the missing ']'")
        if in_brace > 0:
            diags.append(
                f"unclosed '{{' opened at line {open_brace_line} — the brace "
                f"never closes, so lines {open_brace_line}..{len(lines)} were "
                f"merged into this command; add the missing '}}'")
        if dangling_cont and not in_brace and not in_bracket:
            diags.append(
                f"dangling backslash continuation at line {len(lines)} — the "
                f"line ends with '\\' but the file ends; the command is incomplete")
        commands.append(LogicalCommand(
            ' '.join(cur_buf).strip(), cur_start, len(lines), diags))

    # Keep only non-empty logical commands.
    commands = [c for c in commands if c.text.strip()]
    # Bounded Tcl variable resolution (order-aware; inert if no 'set' present).
    return _resolve_variables(commands)


def collect_diagnostics(commands) -> list:
    """Return every lexical diagnostic attached to a preprocessed command set.

    A convenience for consumers that want to surface preprocessing issues
    (e.g. an unclosed bracket at EOF) without threading diagnostics through
    each analysis module.
    """
    out: list = []
    for c in commands:
        out.extend(c.diagnostics or [])
    return out


def _strip_line_comment(line: str, in_brace: int, in_bracket: int) -> str:
    """Remove a trailing Tcl comment from a physical line.

    '#' starts a comment when it appears at the start of the command or after
    whitespace (and not inside braces/brackets/quotes). Returns the cleaned line.
    """
    depth_brace = in_brace
    depth_bracket = in_bracket
    in_quote = None   # None | '"' | "'" — a quote char inside which '#' is literal
    i = 0
    n = len(line)
    while i < n:
        ch = line[i]
        if in_quote:
            if ch == '\\' and i + 1 < n:   # skip escaped char
                i += 2
                continue
            if ch == in_quote:
                in_quote = None
        elif ch in ('"', "'"):
            in_quote = ch
        elif ch == '{':
            depth_brace += 1
        elif ch == '}':
            depth_brace = max(depth_brace - 1, 0)
        elif ch == '[':
            depth_bracket += 1
        elif ch == ']':
            depth_bracket = max(depth_bracket - 1, 0)
        elif ch == '#' and depth_brace == 0 and depth_bracket == 0:
            # Comment if at start of command or preceded by whitespace/';'.
            if i == 0 or line[i - 1] in ' \t;':
                return line[:i].rstrip()
        i += 1
    return line


def logical_text(text: str) -> str:
    """Return joined logical-command text (one command per line).

    Includes bounded Tcl variable substitution (order-aware).
    """
    return '\n'.join(c.text for c in preprocess_sdc(text))


def find_line(commands: list, needle: str) -> int:
    """Return the original start line of the logical command containing needle.

    Returns 0 if not found (matching the checker's unknown-line convention).
    """
    for c in commands:
        if needle in c.text:
            return c.start_line
    return 0
