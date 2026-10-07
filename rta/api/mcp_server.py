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

Engine tools (AUTHORITY — the frozen deterministic backend; unchanged):
    rta_analyze        full analysis pipeline (SDC + optional netlist/baseline)
    rta_lint           lint an SDC
    rta_convert        SDC → JSON / YAML
    rta_generate       generate an SDC from parameters
    rta_snapshot       build an engine readiness snapshot
    rta_diff           V1 vs V2 readiness + constraint diff
    rta_corners        validate corners / build matrix
    rta_rules          rule catalog

Context-source tools (ADVISORY — they add context, never a verdict):
    rta_sources_health       per-source health, breaker and cache state
    rta_source_docs_search   search the local documentation corpus
    rta_source_issues_search search a GitHub issue tracker
    rta_source_store_query   look up recorded runs and the audit trail
    rta_source_store_record  record an engine run + provenance (mutating)
    rta_investigate          engine analysis + matching docs and issues

Access control: every call passes a role check (``rta/api/access.py``) before
it runs. Roles: ``reader`` (default) < ``engineer`` < ``maintainer``; tools
appear in no role are denied for everybody, and mutating tools additionally
require ``RTA_MCP_ALLOW_MUTATIONS=1``. Denied calls return a tool error with
code ``FORBIDDEN`` and are recorded in the audit trail.

Authority rule: sources are advisory. A verdict is only ever produced by the
engine, and ``rta_investigate`` returns the engine payload verbatim alongside
source context so the two can never be confused.

Run:
    python -m rta.api.mcp_server

Register with OpenCode (opencode.json):
    { "mcp": { "rta": { "type": "local",
                        "command": ["python", "-m", "rta.api.mcp_server"] } } }
"""

from __future__ import annotations

import json
import sys
import time
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
    SERVER_VERSION = "1.5.12"


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
    from rta.api.api_server import convert_sdc_json, require_sdc, _SDCSyntaxError
    sdc_text, err = require_sdc(args, "tools/call:rta_convert")
    if err is not None:
        return err
    try:
        return convert_sdc_json(sdc_text, fmt=args.get("format", "json"))
    except _SDCSyntaxError as syn:
        # Release-gate remediation (B-C08-06): syntactically invalid input is
        # returned as an explicit tool error carrying the diagnostics — the
        # generic handler would only produce a bare engine-failure string.
        return syn.body


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


# ═══════════════════════════════════════════════════════════════════════════
# CONTEXT-SOURCE TOOLS — advisory only; these never produce a verdict
# ═══════════════════════════════════════════════════════════════════════════

def _as_int(value, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _tool_sources_health(_args: dict):
    """Per-source diagnostics. Touches no network — safe to call any time."""
    from rta.api import access
    from rta.sources import health_all
    payload = health_all()
    payload["access"] = access.describe_role(access.resolve_role())
    return payload


def _tool_source_docs_search(args: dict):
    from rta.sources import get_sources
    query = args.get("query", "")
    if not isinstance(query, str) or not query.strip():
        return {"error": "field 'query' must be a non-empty string",
                "code": "MISSING_QUERY"}
    adapter = get_sources()["corpus"]
    return adapter.search(query,
                          limit=_as_int(args.get("limit"), 8),
                          path_filter=str(args.get("path_filter", "")))


def _tool_source_issues_search(args: dict):
    from rta.sources import get_sources
    adapter = get_sources()["github"]
    return adapter.search(
        query=str(args.get("query", "")),
        state=str(args.get("state", "open")),
        labels=str(args.get("labels", "")),
        limit=_as_int(args.get("limit"), 10),
        include_pull_requests=bool(args.get("include_pull_requests", False)),
    )


def _tool_source_store_query(args: dict):
    from rta.sources import get_sources
    store = get_sources()["store"]
    if bool(args.get("audit", False)):
        return store.query_audit(limit=_as_int(args.get("limit"), 20),
                                 tool=str(args.get("tool", "")))
    return store.query_runs(limit=_as_int(args.get("limit"), 10),
                            verdict=str(args.get("verdict", "")),
                            rule_id=str(args.get("rule_id", "")),
                            run_id=str(args.get("run_id", "")))


def _tool_source_store_record(args: dict):
    """Record a run. The engine computes the payload here — the caller cannot
    supply a verdict, so a fabricated PASS can never be persisted."""
    from rta.api import access
    from rta.api.api_server import require_sdc
    from rta.sources import get_sources, new_run_id
    from rta.sources.store import engine_facts

    sdc_text, err = require_sdc(args, "tools/call:rta_source_store_record")
    if err is not None:
        return err
    analysis = _tool_analyze(args)
    if isinstance(analysis, dict) and analysis.get("error"):
        return analysis
    facts = engine_facts(analysis)
    run_id = str(args.get("run_id") or new_run_id("run"))
    store = get_sources()["store"]
    written = store.record_run(
        run_id=run_id, sdc_text=sdc_text, analysis=analysis,
        tool="rta_source_store_record", role=access.resolve_role(),
        engine_version=SERVER_VERSION)
    evidence_written = []
    for item in (args.get("evidence") or []):
        if not isinstance(item, dict) or not item.get("ref"):
            continue
        evidence_written.append(store.record_evidence(
            run_id=run_id,
            source=str(item.get("source", "manual")),
            ref=str(item.get("ref")),
            content_hash=str(item.get("content_hash", "")),
            fetched_at=str(item.get("fetched_at", "")),
            freshness=str(item.get("freshness", "")),
            note=str(item.get("note", ""))))
    return {
        "authority": "engine",
        "run_id": run_id,
        "recorded": written,
        "evidence": evidence_written,
        "engine_facts": facts,
        "note": ("verdict and counts above were computed by the engine, "
                 "not supplied"),
    }


def _tool_investigate(args: dict):
    """The composite: engine verdict + matching local docs + matching issues.

    The engine payload is returned verbatim under ``engine`` so a consumer can
    diff it against a plain ``rta_analyze`` call, and source context lives in a
    separate ``context`` object. Sources are advisory: they can add a
    reference, never change the verdict.
    """
    from rta.sources import SOURCE_NAMES, get_sources

    analysis = _tool_analyze(args)
    if isinstance(analysis, dict) and analysis.get("error"):
        return analysis

    try:
        from rta.sources.store import engine_facts
        facts = engine_facts(analysis)
    except Exception:                                # noqa: BLE001 - advisory
        facts = {"rule_ids": [], "verdict": None}

    rule_ids = [str(r) for r in facts.get("rule_ids", [])][:5]
    query = " ".join(rule_ids)
    doc_limit = max(1, min(_as_int(args.get("context_limit"), 3),
                           get_sources()["policy"].max_items))
    issue_limit = max(1, min(_as_int(args.get("issue_limit"), 3),
                             get_sources()["policy"].max_items))

    corpus = get_sources()["corpus"]
    github = get_sources()["github"]
    docs = corpus.search(query or "signoff readiness", limit=doc_limit)
    issues = github.search(query=query, state="open", limit=issue_limit)

    sources_used = [name for name in SOURCE_NAMES
                    if name != "store"]  # store is queried by its own tool
    degraded = bool(docs.get("degraded")) or bool(issues.get("degraded"))

    return {
        "authority": "engine",
        "engine": analysis,
        "engine_facts": facts,
        "context": {"docs": docs, "issues": issues},
        "sources_used": sources_used,
        "degraded": degraded,
        "advisory_note": (
            "Context sources are advisory. The verdict above was produced "
            "only by the deterministic engine; no source can change it."
        ),
    }


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
    # ── Context sources (advisory; never produce a verdict) ────────────────
    {
        "name": "rta_sources_health",
        "description": (
            "Report per-source health for the advisory context sources "
            "(local docs corpus, GitHub issues, SQLite store): configuration, "
            "circuit-breaker state, cache stats and the active access role. "
            "Makes no network call."
        ),
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "rta_source_docs_search",
        "description": (
            "Search the local Ṛta documentation corpus (feature docs, product "
            "docs, samples, engineer test kit, changelog). Offline, "
            "deterministic, no credential. Advisory context only."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string",
                          "description": "Search terms — a rule id (SDC-068), "
                                         "a feature name, or a phrase"},
                "limit": {"type": "integer",
                          "description": "Maximum matches (default 8)"},
                "path_filter": {"type": "string",
                                "description": "Optional substring the file "
                                               "path must contain"},
            },
            "required": ["query"],
        },
    },
    {
        "name": "rta_source_issues_search",
        "description": (
            "Search a GitHub repository's issue tracker for open reports "
            "matching a query — answers 'has this already been reported?'. "
            "Uses GITHUB_TOKEN when present, otherwise anonymous access "
            "with a small shared quota. Handles rate limits and degrades to "
            "the last cached result."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string",
                          "description": "Search terms (rule id, symptom)"},
                "state": {"type": "string",
                          "enum": ["open", "closed", "all"],
                          "description": "Issue state (default open)"},
                "labels": {"type": "string",
                           "description": "Comma-separated label filter"},
                "limit": {"type": "integer",
                          "description": "Maximum issues (default 10, "
                                         "cap 25)"},
                "include_pull_requests": {
                    "type": "boolean",
                    "description": "Include pull requests (default false)"},
            },
        },
    },
    {
        "name": "rta_source_store_query",
        "description": (
            "Query the local SQLite store: previously recorded engine runs "
            "(verdict, counts, findings, source evidence) or the MCP audit "
            "trail. Read-only. Recorded verdicts were written by the engine."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "description": "Max rows"},
                "verdict": {"type": "string",
                            "description": "Filter runs by engine verdict"},
                "rule_id": {"type": "string",
                            "description": "Only runs containing this "
                                           "rule id"},
                "run_id": {"type": "string", "description": "Exact run id"},
                "audit": {"type": "boolean",
                          "description": "Return the audit trail instead "
                                         "of runs"},
                "tool": {"type": "string",
                         "description": "Audit filter: tool name"},
            },
        },
    },
    {
        "name": "rta_source_store_record",
        "description": (
            "Record one engine run (verdict, counts, findings) plus optional "
            "provenance rows into the local SQLite store. MUTATING: requires "
            "the maintainer role and RTA_MCP_ALLOW_MUTATIONS=1. The engine "
            "computes the analysis — a caller cannot supply a verdict."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "sdc": {"type": "string", "description": "SDC file contents"},
                "netlist": {"type": "string",
                            "description": "Optional Verilog netlist text"},
                "top": {"type": "string", "description": "Top module name"},
                "run_id": {"type": "string",
                           "description": "Optional explicit run id"},
                "evidence": {
                    "type": "array",
                    "items": {"type": "object"},
                    "description": ("Optional provenance rows "
                                    "{source, ref, content_hash, fetched_at, "
                                    "freshness, note}"),
                },
            },
            "required": ["sdc"],
        },
    },
    {
        "name": "rta_investigate",
        "description": (
            "Composite investigation in one call: runs the deterministic "
            "engine on an SDC/module, then attaches matching local "
            "documentation and matching open GitHub issues for the rules that "
            "fired. The engine payload is returned verbatim under 'engine'; "
            "context sources are advisory and can never change the verdict."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "sdc": {"type": "string", "description": "SDC file contents"},
                "netlist": {"type": "string",
                            "description": "Optional Verilog netlist text"},
                "top": {"type": "string", "description": "Top module name"},
                "baseline": {"type": "string",
                             "description": "Optional baseline snapshot JSON"},
                "gate": {"type": "string", "description": "Optional CI gate"},
                "context_limit": {"type": "integer",
                                  "description": "Doc matches (default 3)"},
                "issue_limit": {"type": "integer",
                                "description": "Issue matches (default 3)"},
            },
            "required": ["sdc"],
        },
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
    # Advisory context sources
    "rta_sources_health": _tool_sources_health,
    "rta_source_docs_search": _tool_source_docs_search,
    "rta_source_issues_search": _tool_source_issues_search,
    "rta_source_store_query": _tool_source_store_query,
    "rta_source_store_record": _tool_source_store_record,
    "rta_investigate": _tool_investigate,
}


# ═══════════════════════════════════════════════════════════════════════════
# ACCESS CONTROL + AUDIT
# ═══════════════════════════════════════════════════════════════════════════

def _guard(tool: str) -> dict:
    """Capability check for one tool call (see ``rta/api/access.py``)."""
    from rta.api import access
    return access.check(access.resolve_role(), tool)


def _sources_used(payload) -> list:
    """Best-effort extraction of which sources contributed to a response."""
    if not isinstance(payload, dict):
        return []
    explicit = payload.get("sources_used")
    if isinstance(explicit, list):
        return [str(s) for s in explicit]
    context = payload.get("context")
    if isinstance(context, dict):
        return [str(k) for k in context.keys()]
    if payload.get("source"):
        return [str(payload["source"])]
    return []


def _audit(tool: str, args: dict, payload, started_at=None,
           outcome: str = "OK") -> None:
    """Record an audited call. Never raises, never stores argument values."""
    try:
        from rta.api import access
        degraded = bool(isinstance(payload, dict)
                        and (payload.get("degraded")
                             or (payload.get("sources_used")
                                 and payload.get("degraded"))))
        access.audit(tool, access.resolve_role(), args, outcome=outcome,
                     started_at=started_at, degraded=degraded,
                     sources_used=_sources_used(payload))
    except Exception as exc:                         # noqa: BLE001 - non-fatal
        print(f"[mcp_server] audit failed for {tool}: "
              f"{type(exc).__name__}: {exc}", file=sys.stderr)


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

        # Capability boundary: the role is resolved per call so an operator can
        # widen or narrow it via the environment without restarting the server.
        decision = _guard(name)
        if not decision.get("allowed"):
            _audit(name, args, payload=None, outcome="FORBIDDEN")
            return _result(req_id, {
                "content": [{"type": "text",
                             "text": json.dumps({
                                 "error": "tool not permitted for the "
                                          "configured role",
                                 "code": "FORBIDDEN",
                                 "decision": decision,
                                 "hint": ("set RTA_MCP_ROLE=engineer (or "
                                          "maintainer) to enable source "
                                          "tools"),
                             }, ensure_ascii=False)}],
                "isError": True,
            })

        started_at = time.monotonic()
        try:
            payload = impl(args)
        except Exception as exc:  # noqa: BLE001 - report as tool error, never crash
            tb = traceback.format_exc()[-2000:]
            print(f"[mcp_server] {name} failed: {tb}", file=sys.stderr)
            _audit(name, args, payload=None, started_at=started_at,
                   outcome="ERROR")
            return _result(req_id, {
                "content": [{"type": "text",
                             "text": f"engine failure: "
                                     f"{type(exc).__name__}: {exc}"}],
                "isError": True,
            })
        _audit(name, args, payload=payload, started_at=started_at)
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
