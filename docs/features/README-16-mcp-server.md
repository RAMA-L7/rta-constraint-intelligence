# Ṛta MCP Server — use the engine from any AI coding assistant

The MCP (Model Context Protocol) server exposes the frozen deterministic Ṛta
backend as **tools** that an LLM assistant can call directly. Instead of
copy-pasting SDC files into a chat, your assistant runs `rta_analyze`,
`rta_lint`, `rta_diff` and friends natively — with the same engine, rules,
and evidence guarantees as the CLI and Web UI.

- **What it is** — 8 deterministic tools over stdio (JSON-RPC 2.0)
- **Who it's for** — engineers using OpenCode, Claude Desktop/Code, Cursor,
  or any MCP-capable client
- **Trust boundary** — same frozen backend as `rta check`; no LLM inside the
  engine; offline capable; zero new runtime dependencies

> The MCP server is a **thin adapter**: it imports the JSON serialization
> layer from `rta/api/api_server.py` and never modifies the authority
> modules. Same input → same tool output → same verdict as the CLI.

---

## 1. Requirements

| Requirement | Value |
|---|---|
| Python | ≥ 3.10 |
| Package | `rta-constraint-intelligence` installed (`pip install rta-constraint-intelligence`, or `pip install -e .` from source) |
| Extra dependencies | **None** — pure Python standard library |
| Network | Not required after install (offline capable) |
| EDA tools / licenses | Not required |

Verify it starts:

```bash
python -m rta.api.mcp_server          # waits on stdio; Ctrl+C to exit
# or, after pip install:
rta-mcp
```

---

## 2. Register with your client

### OpenCode

Add to `opencode.json` (project) or `~/.config/opencode/opencode.json` (global):

```json
{
  "mcp": {
    "rta": {
      "type": "local",
      "command": ["python", "-m", "rta.api.mcp_server"]
    }
  }
}
```

Restart opencode, then prompt naturally:

```
use rta_analyze on samples/minimal_sdc.sdc and tell me what blocks signoff
```

### Claude Desktop

Add to `claude_desktop_config.json` (Settings → Developer → Edit Config):

```json
{
  "mcpServers": {
    "rta": {
      "command": "python",
      "args": ["-m", "rta.api.mcp_server"]
    }
  }
}
```

### Claude Code

```bash
claude mcp add rta -- python -m rta.api.mcp_server
```

### Cursor

Settings → MCP Tools → New MCP Server:

```json
{
  "mcpServers": {
    "rta": {
      "command": "python",
      "args": ["-m", "rta.api.mcp_server"]
    }
  }
}
```

> On Windows with multiple Pythons, point at the interpreter that has the
> package installed, e.g.
> `"command": ["C:/Python310/python.exe", "-m", "rta.api.mcp_server"]`.

---

## 3. Tool catalog

All tools are prefixed `rta_` and return JSON text content.

| Tool | Purpose | Key arguments |
|---|---|---|
| `rta_analyze` | Full analysis pipeline: validation issues, readiness verdict, clock relations, category coverage, optional netlist-aware design context, baseline diff + CI gate, custom YAML rules | `sdc` (required), `netlist`, `top`, `baseline`, `gate`, `custom_rules` |
| `rta_lint` | Lint/format an SDC; returns warnings and optionally auto-fixed text | `sdc` (required), `fix` (default true) |
| `rta_convert` | Parse SDC into structured JSON/YAML | `sdc` (required), `format` (`json`\|`yaml`) |
| `rta_generate` | Generate a complete SDC from parameters (clocks, I/O delays, derates…) | `params` (SDCParams-compatible dict) |
| `rta_snapshot` | Build an engine readiness snapshot — usable as a CI baseline | `sdc` (required) |
| `rta_diff` | Diff two SDC versions: NEW/RESOLVED/CHANGED findings, debt, semantic constraint changes | `v1`, `v2` |
| `rta_corners` | Validate PVT corner definitions, build the multi-corner matrix | `corners` (list of dicts) |
| `rta_rules` | List the full rule catalog (all rule codes, severities, fixes) | — |

---

## 4. Example sessions

### Check an SDC before review

> *"Use rta_analyze on my block.sdc. What are the errors and is this design
> ready for pre-STA review?"*

The assistant reads `readiness.overall`, lists blocking issues by rule code,
and can explain each code via `rta_rules`.

### Netlist-aware check

> *"Run rta_analyze on block.sdc with netlist from block_net.v, top module
> `uart_core`. Which get_ports references don't exist?"*

Same pipeline as `rta check --netlist`: structural port/pin resolution, not
name matching.

### Regression check before committing new constraints

> *"Diff old.sdc vs new.sdc with rta_diff. Did anything regress? Was any
> false path removed?"*

Returns readiness NEW/RESOLVED/CHANGED findings plus CHG-* semantic changes
(period shifts, I/O delay edits, false-path removals).

### Build a CI baseline

> *"Use rta_snapshot on golden.sdc"*

Paste the returned JSON into your repo (e.g. `.rta/baseline.json`) and gate
merges with `rta check --baseline .rta/baseline.json --gate STRICT` — see
[CI Quality Gates](README-14-ci-gate.md).

---

## 5. Architecture & trust boundary

```
┌──────────────┐   stdio (JSON-RPC 2.0)   ┌──────────────────────┐
│ MCP client   │ ◄──────────────────────► │  rta.api.mcp_server  │
│ (LLM assist) │   newline-delimited      │  thin adapter only   │
└──────────────┘                          └──────────┬───────────┘
                                                     │ imports
                                          ┌──────────▼───────────┐
                                          │ rta.api.api_server   │
                                          │ JSON serialization   │
                                          └──────────┬───────────┘
                                                     │ calls
                                          ┌──────────▼───────────┐
                                          │ Frozen deterministic │
                                          │ engine (check_sdc …) │
                                          └──────────────────────┘
```

- The engine is **authority** — the MCP layer cannot fake a PASS, skip a
  rule, or mutate backend state. Engine failures surface as `isError`
  responses, never silent successes.
- The LLM decides *when* to call tools and *interprets* results; every
  number comes from the deterministic engine.
- Empty/missing SDC input returns structured errors (P1-6 contract), so an
  integration bug can't produce an empty-but-passing analysis.

---

## 6. Troubleshooting

| Symptom | Fix |
|---|---|
| Client shows no tools | Run `python -m rta.api.mcp_server` manually — you should see the startup line on **stderr** and silence on stdout. A traceback means the package isn't installed in that interpreter. |
| `ModuleNotFoundError: No module named 'rta'` | Install: `pip install rta-constraint-intelligence`, or run from the repo root. |
| UnicodeEncodeError on Windows console startup | Already guarded (UTF-8 reconfigure); ensure you're not wrapping stdout yourself. |
| Tool call returns `engine failure` | The response includes the exception type/message in `content[0].text`; rerun with the CLI (`rta check file.sdc`) to confirm, and report if reproducible. |

---

## 7. Related surfaces

- **[Hands-On Exercises](README-17-mcp-exercises.md)** — guided prompts for all 8 tools using the `samples/` files
- [CLI User Guide](README-11-cli-user-guide.md) — same features from the terminal
- [CI Quality Gates](README-14-ci-gate.md) — gate semantics for baselines/gates used by `rta_snapshot` / `rta_analyze`
- [Rules Registry](README-08-rules-registry.md) — what each rule code means
- Local HTTP API: `python api_server.py` → `POST /api/analyze` etc. (same payloads, for non-LLM integrations)
