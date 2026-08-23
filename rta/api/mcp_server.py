"""
Ṛta — Model Context Protocol (MCP) server.

Exposes the frozen deterministic Ṛta backend as MCP tools over stdio
(JSON-RPC 2.0, newline-delimited messages per the MCP stdio transport).
Pure Python standard library only — no new runtime dependencies, offline
capable, CI and clean-room safe (same contract as api_server.py).

Architecture contract:
  - The backend modules are AUTHORITY and are never modified here.
  - This module only imports the JSON serialization layer from
    ``rta.api.api_server`` and forwards results as MCP tool responses.
  - Deterministic: same input → same tool output.

Tools:
    rta_analyze        full analysis pipeline (SDC + optional netlist/baseline)
    rta_lint           lint an SDC
    rta_convert        SDC → JSON / YAML
    rta_generate       generate an SDC from parameters
    rta_snapshot       build an engine readiness snapshot
    rta_diff           V1 vs V2 readiness + constraint diff
    rta_corners        validate corners / build matrix
    rta_rules          rule catalog

Run:
    python -m rta.api.mcp_server

Register with OpenCode (opencode.json):
    { "mcp": { "rta": { "type": "local",
                        "command": ["python", "-m", "rta.api.mcp_server"] } } }
"""

from __future__ import annotations

import json
import sys
import traceback

# The visible brand is Ṛta (U+1E5A). On Windows the console defaults to the
# legacy ANSI codepage, so force UTF-8 on stdout/stderr where supported.
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

from os.path import dirname, abspath   # noqa: E402

ROOT = dirname(abspath(__file__))                    # rta/api/
REPO_ROOT = dirname(dirname(ROOT))                   # repository root
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

SERVER_NAME = "rta-constraint-intelligence"
PROTOCOL_VERSION = "2024-11-05"

try:
    from rules_registry import APP_VERSION as SERVER_VERSION
except Exception:  # pragma: no cover - defensive for partial installs
    SERVER_VERSION = "1.5.9"


# ═══════════════════════════════════════════════════════════════════════════
# TOOL IMPLEMENTATIONS — thin forwarders to the api_server JSON layer
# ═══════════════════════════════════════════════════════════════════════════

def _tool_analyze(args: dict):
    from rta.api.api_server import analyze, require_sdc
    sdc_text, err = require_sdc(args, "tools/call:rta_analyze")
    if err is not None:
        return err
    return analyze(
        sdc_text=sdc_text,
        netlist=args.get("netlist", ""),
        top=args.get("top", ""),
        baseline=args.get("baseline", ""),
        gate=args.get("gate", ""),
        custom_rules=args.get("custom_rules", ""),
        rules_filename=args.get("rules_filename", "rules.yaml"),
    )


def _tool_lint(args: dict):
    from rta.api.api_server import lint_sdc_json, require_sdc
    sdc_text, err = require_sdc(args, "tools/call:rta_lint")
    if err is not None:
        return err
    return lint_sdc_json(sdc_text, fix=bool(args.get("fix", True)))


def _tool_convert(args: dict):
    from rta.api.api_server import convert_sdc_json, require_sdc
    sdc_text, err = require_sdc(args, "tools/call:rta_convert")
    if err is not None:
        return err
    return convert_sdc_json(sdc_text, fmt=args.get("format", "json"))


def _tool_generate(args: dict):
    from rta.api.api_server import generate_sdc_json
    return generate_sdc_json(args.get("params", {}))


def _tool_snapshot(args: dict):
    from rta.api.api_server import snapshot_sdc_json, require_sdc
    sdc_text, err = require_sdc(args, "tools/call:rta_snapshot")
    if err is not None:
        return err
    return snapshot_sdc_json(sdc_text)


def _tool_diff(args: dict):
    from rta.api.api_server import diff_sdc_json
    v1 = args.get("v1")
    v2 = args.get("v2")
    if not isinstance(v1, str) or not v1.strip() or \
       not isinstance(v2, str) or not v2.strip():
        return {"error": "fields 'v1' and 'v2' must be non-empty SDC strings",
                "code": "MISSING_DIFF_INPUT"}
    return diff_sdc_json(v1, v2)


def _tool_corners(args: dict):
    from rta.api.api_server import corners_json
    corners = args.get("corners", [])
    if not isinstance(corners, list) or not corners:
        return {"error": "field 'corners' must be a non-empty list",
                "code": "INVALID_CORNERS"}
    return corners_json(corners)


def _tool_rules(_args: dict):
    from rta.api.api_server import rules_json
    return rules_json()


_SDC_SCHEMA = {
    "type": "object",
    "properties": {
        "sdc": {"type": "string",
                "description": "SDC file contents (TCL text)"},
    },
    "required": ["sdc"],
}

TOOLS = [
    {
        "name": "rta_analyze",
        "description": (
            "Run the full deterministic Ṛta analysis pipeline on an SDC: "
            "validation issues, stats, scope, coverage, interactions, "
            "readiness verdict, clock relations, category coverage, plus "
            "optional netlist-aware design context, baseline diff, CI gate "
            "and custom YAML rules."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "sdc": {"type": "string", "description": "SDC file contents"},
                "netlist": {"type": "string",
                            "description": "Optional Verilog netlist text"},
                "top": {"type": "string",
                        "description": "Optional top module name for the netlist"},
                "baseline": {"type": "string",
                             "description": "Optional baseline snapshot JSON for diff"},
                "gate": {"type": "string",
                         "description": "Optional CI gate expression"},
                "custom_rules": {"type": "string",
                                 "description": "Optional YAML custom ruleset"},
            },
            "required": ["sdc"],
        },
    },
    {
        "name": "rta_lint",
        "description": ("Lint/format an SDC. Returns warnings, issues and "
                        "optionally auto-fixed formatted text."),
        "inputSchema": {
            "type": "object",
            "properties": {
                "sdc": {"type": "string", "description": "SDC file contents"},
                "fix": {"type": "boolean",
                        "description": "Return auto-fixed formatted text "
                                       "(default true)"},
            },
            "required": ["sdc"],
        },
    },
    {
        "name": "rta_convert",
        "description": ("Parse an SDC into structured data and emit it as "
                        "JSON or YAML."),
        "inputSchema": {
            "type": "object",
            "properties": {
                "sdc": {"type": "string", "description": "SDC file contents"},
                "format": {"type": "string",
                           "enum": ["json", "yaml"],
                           "description": "Output format (default json)"},
            },
            "required": ["sdc"],
        },
    },
    {
        "name": "rta_generate",
        "description": ("Generate a complete SDC from parameters (clocks, "
                        "I/O delays, derates, scan/reset handling, ...)."),
        "inputSchema": {
            "type": "object",
            "properties": {
                "params": {"type": "object",
                           "description": "SDCParams-compatible dict; see "
                                          "generator.SDCParams for keys"},
            },
        },
    },
    {
        "name": "rta_snapshot",
        "description": ("Build a genuine engine readiness snapshot (JSON) "
                        "from SDC text — usable as a CI baseline."),
        "inputSchema": _SDC_SCHEMA,
    },
    {
        "name": "rta_diff",
        "description": ("Diff two SDC versions: NEW/RESOLVED/CHANGED "
                        "readiness findings, debt, plus semantic "
                        "constraint-level changes (period/I-O/false-path/...)."),
        "inputSchema": {
            "type": "object",
            "properties": {
                "v1": {"type": "string", "description": "Baseline SDC text"},
                "v2": {"type": "string", "description": "New SDC text"},
            },
            "required": ["v1", "v2"],
        },
    },
    {
        "name": "rta_corners",
        "description": ("Validate PVT corner definitions and build the "
                        "multi-corner matrix."),
        "inputSchema": {
            "type": "object",
            "properties": {
                "corners": {"type": "array",
                            "items": {"type": "object"},
                            "description": "Corner definition dicts "
                                           "(name, voltage, temperature, ...)"},
            },
            "required": ["corners"],
        },
    },
    {
        "name": "rta_rules",
        "description": "List the full Ṛta validation rule catalog.",
        "inputSchema": {"type": "object", "properties": {}},
    },
]

_TOOL_IMPLS = {
    "rta_analyze": _tool_analyze,
    "rta_lint": _tool_lint,
    "rta_convert": _tool_convert,
    "rta_generate": _tool_generate,
    "rta_snapshot": _tool_snapshot,
    "rta_diff": _tool_diff,
    "rta_corners": _tool_corners,
    "rta_rules": _tool_rules,
}


# ═══════════════════════════════════════════════════════════════════════════
# MCP PROTOCOL — JSON-RPC 2.0 over stdio (newline-delimited)
# ═══════════════════════════════════════════════════════════════════════════

def _write_message(msg: dict) -> None:
    """Write one newline-delimited JSON message to stdout.

    The message must contain no embedded newlines per the MCP stdio
    transport spec — json.dumps guarantees that by default.
    """
    sys.stdout.write(json.dumps(msg, ensure_ascii=False, default=str) + "\n")
    sys.stdout.flush()


def _result(req_id, payload) -> dict:
    return {"jsonrpc": "2.0", "id": req_id, "result": payload}


def _error(req_id, code: int, message: str) -> dict:
    return {"jsonrpc": "2.0", "id": req_id,
            "error": {"code": code, "message": message}}


def handle_request(req: dict) -> dict | None:
    """Dispatch one incoming JSON-RPC request/notification."""
    method = req.get("method", "")
    req_id = req.get("id")  # notifications have no id → no response

    # Notifications: acknowledge nothing except logging-side effects.
    if req_id is None:
        return None

    if method == "initialize":
        client_proto = (req.get("params") or {}).get("protocolVersion", "")
        return _result(req_id, {
            # Echo the client's requested version when known (spec §Lifecycle);
            # fall back to the version this server implements.
            "protocolVersion": client_proto or PROTOCOL_VERSION,
            "capabilities": {"tools": {}},
            "serverInfo": {"name": SERVER_NAME, "version": SERVER_VERSION},
        })

    if method == "ping":
        return _result(req_id, {})

    if method == "tools/list":
        return _result(req_id, {"tools": TOOLS})

    if method == "tools/call":
        params = req.get("params") or {}
        name = params.get("name", "")
        args = params.get("arguments") or {}
        impl = _TOOL_IMPLS.get(name)
        if impl is None:
            return _error(req_id, -32602, f"unknown tool: {name}")
        try:
            payload = impl(args)
        except Exception as exc:  # noqa: BLE001 - report as tool error, never crash
            tb = traceback.format_exc()[-2000:]
            print(f"[mcp_server] {name} failed: {tb}", file=sys.stderr)
            return _result(req_id, {
                "content": [{"type": "text",
                             "text": f"engine failure: "
                                     f"{type(exc).__name__}: {exc}"}],
                "isError": True,
            })
        return _result(req_id, {
            "content": [{"type": "text",
                         "text": json.dumps(payload, ensure_ascii=False,
                                            default=str)}],
        })

    return _error(req_id, -32601, f"method not found: {method}")


def serve() -> int:
    print(f"Ṛta MCP server v{SERVER_VERSION} starting on stdio",
          file=sys.stderr)
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
        except json.JSONDecodeError as exc:
            # A parse failure on a request-shaped line gets a parse error
            # response with null id; pure garbage without structure cannot
            # be replied to safely but we still attempt a protocol reply.
            _write_message(_error(None, -32700, f"parse error: {exc}"))
            continue
        if not isinstance(req, dict):
            _write_message(_error(None, -32600, "invalid request envelope"))
            continue
        resp = handle_request(req)
        if resp is not None:
            _write_message(resp)
    return 0


if __name__ == "__main__":
    sys.exit(serve())
