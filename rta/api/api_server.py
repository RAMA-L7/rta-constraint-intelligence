"""
Ṛta — local API server.

Serves the static product workspace (``rta/workspace/webui/``) and exposes the frozen
deterministic backend over HTTP as JSON. Pure Python standard library only:
``http.server.ThreadingHTTPServer`` — no new runtime dependencies, offline
capable, CI and clean-room safe.

Architecture contract (docs/product/PHASE17_FRONTEND_ARCHITECTURE_DECISION.md):
  - The backend modules are AUTHORITY and are never modified here.
  - This module only imports them and serializes their results to JSON.
  - All responses are structured data; the frontend escapes at render time.
  - Deterministic: same input → same JSON.

Endpoints:
    GET  /api/health                 version + status
    GET  /api/design                 design tokens + status metadata
    GET  /api/rules                  rule catalog
    POST /api/analyze                full analysis pipeline (SDC + optional
                                     netlist/baseline/gate/custom rules)
    POST /api/lint                   lint an SDC
    POST /api/convert                SDC → JSON / YAML
    POST /api/generate               generate an SDC from parameters
    POST /api/corners                validate corners / build matrix
    POST /api/mmc                    multi-corner SDC generation
    POST /api/mmc/zip                per-corner SDCs bundled as a ZIP archive
    POST /api/feedback               record feedback
    GET  /*                          static workspace assets (SPA)

Run:
    python rta/api/api_server.py     # serves on http://127.0.0.1:8501
"""

from __future__ import annotations

import io
import json
import mimetypes
import os
import re
import sys
import tempfile
import threading
import traceback
import zipfile
from dataclasses import asdict, is_dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

# The visible brand is Ṛta (U+1E5A). On Windows the console defaults to the
# legacy ANSI codepage (e.g. cp1252), so printing the brand directly can raise
# UnicodeEncodeError. Force UTF-8 on stdout/stderr where supported (same guard
# as cli.py) so `python -m api_server` works without PYTHONIOENCODING.
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

# ── Paths ────────────────────────────────────────────────────────────────────
ROOT = os.path.dirname(os.path.abspath(__file__))   # rta/api/
REPO_ROOT = os.path.dirname(os.path.dirname(ROOT))   # repository root (compat shims live there)
WEBUI_DIR = os.path.join(REPO_ROOT, "rta", "workspace", "webui")
DATA_DIR = os.path.join(REPO_ROOT, "rta", "workspace", "data")

# Make the repository root importable so the top-level compat shims resolve
# (also works from a clean wheel install, where the shims and rta/ ship
# together inside site-packages).
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

try:
    from rules_registry import APP_VERSION, get_all_rules, get_rule
except Exception:  # pragma: no cover - defensive for partial installs
    APP_VERSION = "1.5.1"


# ═══════════════════════════════════════════════════════════════════════════
# SERIALIZATION — dataclasses → JSON-safe dicts
# ═══════════════════════════════════════════════════════════════════════════

def _jsonable(obj):
    """Convert dataclasses/dataclass-lists to JSON-safe structures."""
    if obj is None or isinstance(obj, (str, int, float, bool)):
        return obj
    if isinstance(obj, (list, tuple)):
        return [_jsonable(x) for x in obj]
    if isinstance(obj, dict):
        return {str(k): _jsonable(v) for k, v in obj.items()}
    if is_dataclass(obj):
        return _jsonable(asdict(obj))
    return str(obj)


def serialize_issues(issues) -> list:
    out = []
    for it in issues:
        out.append({
            "sev": getattr(it, "sev", "info"),
            "code": getattr(it, "code", ""),
            "msg": getattr(it, "msg", ""),
            "line": int(getattr(it, "line", 0) or 0),
            "line2": int(getattr(it, "line2", 0) or 0),
            "identity": _jsonable(getattr(it, "identity", None)),
        })
    return out


def serialize_info(info) -> list:
    return [{"code": getattr(x, "code", ""), "msg": getattr(x, "msg", "")}
            for x in (info or [])]


def serialize_clock_relations(text: str) -> dict:
    """Run clock-relation analysis and return a JSON-safe summary."""
    from clock_relations import analyze_clock_relations
    r = analyze_clock_relations(text)
    return {
        "stats": r.stats,
        "clocks": [_jsonable(c) for c in r.clocks],
        "pairs": [_jsonable(p) for p in r.pairs],
        "mismatches": [_jsonable(m) for m in r.mismatches],
        "existing_groups": _jsonable(r.existing_groups),
    }


# ═══════════════════════════════════════════════════════════════════════════
# ANALYSIS PIPELINE — mirrors ui/validator.render() stage order
# ═══════════════════════════════════════════════════════════════════════════

def _parse_netlist(netlist_text: str, top: str = "") -> dict:
    """Parse a Verilog netlist into a live design-context summary.

    Returns {"context": DesignContext|None, "serialized": dict|None,
             "error": str|None, "mode_note": str}.
    ``context`` is the LIVE object for the analysis pipeline; ``serialized``
    is the JSON-safe copy for the API payload.
    """
    from design_context import parse_verilog
    try:
        outcome = parse_verilog(netlist_text, top=(top or "").strip())
        if outcome.errors:
            return {"context": None, "serialized": None, "error": outcome.errors[0],
                    "mode_note": "SDC only (netlist rejected)"}
        ctx = outcome.context
        counts = ctx.object_counts()
        return {
            "context": ctx,
            "serialized": _jsonable(ctx),
            "error": None,
            "mode_note": (f"SDC + Design Context (top={ctx.top_module}, "
                          f"{counts['ports']} ports, {counts['instances']} instances)"),
        }
    except Exception as exc:  # pragma: no cover - honest failure surface
        return {"context": None, "serialized": None, "error": str(exc),
                "mode_note": "SDC only (netlist parse failed)"}


def _run_custom_rules(sdc_text: str, rules_yaml: str, filename: str = "rules.yaml"):
    """Run a YAML custom-ruleset over the SDC. Returns list or error marker."""
    from custom_rules import load_ruleset, apply_rules
    tmp = os.path.join(tempfile.gettempdir(), f"sdc_cr_{abs(hash(filename))}.yaml")
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(rules_yaml)
    rs = load_ruleset(tmp)
    results = apply_rules(sdc_text, rs)
    return [{
        "id": getattr(r.rule, "id", ""),
        "name": getattr(r.rule, "name", ""),
        "severity": getattr(r.rule, "severity", ""),
        "description": getattr(r.rule, "description", ""),
        "passed": bool(r.passed),
        "msg": getattr(r, "msg", ""),
    } for r in results]


def analyze(sdc_text: str, netlist: str = "", top: str = "",
            baseline: str = "", gate: str = "", custom_rules: str = "",
            rules_filename: str = "rules.yaml") -> dict:
    """Run the full deterministic analysis pipeline. Never mutates backend state."""
    from checker import check_sdc

    stages = []
    stages.append("parse")

    # 1. Optional design context
    design_context = None
    context_payload = None
    mode_note = "SDC only"
    nl_error = None
    if netlist and netlist.strip():
        parsed = _parse_netlist(netlist, top)
        if parsed["context"] is not None:
            design_context = parsed["context"]
            context_payload = parsed["serialized"]
        nl_error = parsed["error"]
        mode_note = parsed["mode_note"]
    stages.append("context")

    # 2. Custom rules
    custom_rule_results = None
    custom_rule_err = None
    if custom_rules and custom_rules.strip():
        try:
            custom_rule_results = _run_custom_rules(sdc_text, custom_rules, rules_filename)
        except Exception as exc:  # pragma: no cover
            custom_rule_results = None
            custom_rule_err = str(exc)
    stages.append("validate")

    # 3. Core check (authority)
    try:
        result = check_sdc(sdc_text, context=design_context)
        engine_error = None
    except Exception as exc:  # pragma: no cover - must never fake a PASS
        engine_error = f"{type(exc).__name__}: {exc}"
        result = None
    stages.append("clocks")
    stages.append("readiness")

    payload = {
        "stages": stages,
        "mode_note": mode_note,
        "nl_error": nl_error,
        "engine_error": engine_error,
        "context": context_payload,
        "custom_rules": custom_rule_results,
        "custom_rule_err": custom_rule_err,
    }
    if result is None:
        payload["ok"] = False
        return payload
    payload["ok"] = True

    # 4. Serialize core evidence
    payload["issues"] = serialize_issues(result.issues)
    payload["info"] = serialize_info(result.info)
    payload["stats"] = result.stats
    payload["scope"] = result.scope or {}
    payload["coverage"] = result.coverage or {}
    payload["interactions"] = result.interactions or {}
    payload["readiness"] = result.readiness or {}

    # 5. Clock relations (inventory / hierarchy / matrix evidence)
    try:
        payload["clock_relations"] = serialize_clock_relations(sdc_text)
    except Exception as exc:  # pragma: no cover
        payload["clock_relations"] = {"error": str(exc), "stats": {},
                                      "clocks": [], "pairs": [],
                                      "mismatches": [], "existing_groups": []}

    # 6. Optional baseline diff + CI gate
    if baseline and baseline.strip():
        try:
            from readiness_diff import (load_snapshot, build_snapshot,
                                        diff_snapshots, evaluate_gate)
            bl_snap, bl_errs = load_snapshot(baseline)
            if bl_snap is None:
                payload["baseline"] = {"error": "; ".join(bl_errs or ["invalid snapshot"])}
            else:
                cur_snap = build_snapshot(result, context=design_context,
                                          source_name="analyzed.sdc")
                diff = diff_snapshots(bl_snap, cur_snap)
                if gate and gate.strip():
                    try:
                        diff["gate"] = evaluate_gate(gate, bl_snap, cur_snap, diff)
                    except Exception as exc2:  # pragma: no cover
                        diff["gate"] = {"result": "ERROR",
                                        "exit_code": 3,
                                        "reasons": [f"gate evaluation failed: {exc2}"]}
                payload["baseline"] = _jsonable(diff)
        except Exception as exc:  # pragma: no cover
            payload["baseline"] = {"error": f"baseline diff unavailable: {exc}"}
    else:
        payload["baseline"] = None

    return payload


# ═══════════════════════════════════════════════════════════════════════════
# TOOL ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════

def lint_sdc_json(text: str, fix: bool = True) -> dict:
    from linter import lint_sdc
    r = lint_sdc(text, fix=fix)
    return {
        "line_count_original": r.line_count_original,
        "line_count_formatted": r.line_count_formatted,
        "warnings": r.warnings,
        "fixed": r.fixed,
        "issues": list(r.issues),
        "formatted_text": r.formatted_text,
    }


def convert_sdc_json(text: str, fmt: str = "json") -> dict:
    from converter import parse_sdc, sdc_to_json, sdc_to_yaml
    parsed = parse_sdc(text)
    data = parsed.to_dict()
    if fmt == "yaml":
        return {"format": "yaml", "data": data,
                "text": sdc_to_yaml(text)}
    return {"format": "json", "data": data,
            "text": sdc_to_json(text)}


def generate_sdc_json(params: dict) -> dict:
    from generator import SDCParams, generate_sdc
    import generator as _gen

    def _clock(d):
        return _gen.ClockDef(
            name=str(d.get("name", "clk_core")),
            port=str(d.get("port", "clk")),
            period=float(d.get("period", 5.0)),
            uncertainty=float(d.get("uncertainty", 0.15)),
            clk_type=str(d.get("clk_type", "primary")),
            master_port=str(d.get("master_port", "")),
            divide_by=int(d.get("divide_by", 2)),
            multiply_by=int(d.get("multiply_by") or 0) or None,
        )

    defaults = SDCParams()
    p = SDCParams(
        design_name=str(params.get("design_name", "MY_DESIGN")),
        sdc_version=str(params.get("sdc_version", "2.2")),
        add_units=bool(params.get("add_units", True)),
        time_unit=str(params.get("time_unit", "ns")),
        cap_unit=str(params.get("cap_unit", "pF")),
        res_unit=str(params.get("res_unit", "kOhm")),
        clocks=[_clock(d) for d in (params.get("clocks") or [{
            "name": "clk_core", "port": "clk", "period": 5.0,
            "uncertainty": 0.15, "clk_type": "primary"}])],
        add_clk_jitter=bool(params.get("add_clk_jitter", defaults.add_clk_jitter)),
        clk_jitter_val=float(params.get("clk_jitter_val", defaults.clk_jitter_val)),
        add_clk_transition=bool(params.get("add_clk_transition", defaults.add_clk_transition)),
        clk_transition_val=float(params.get("clk_transition_val", defaults.clk_transition_val)),
        add_clk_gating=bool(params.get("add_clk_gating", defaults.add_clk_gating)),
        clk_gate_setup=float(params.get("clk_gate_setup", defaults.clk_gate_setup)),
        clk_gate_hold=float(params.get("clk_gate_hold", defaults.clk_gate_hold)),
        add_latency=bool(params.get("add_latency", defaults.add_latency)),
        latency_val=float(params.get("latency_val", defaults.latency_val)),
        add_propagated=bool(params.get("add_propagated", defaults.add_propagated)),
        in_delay_max=float(params.get("in_delay_max", defaults.in_delay_max)),
        in_delay_min=float(params.get("in_delay_min", defaults.in_delay_min)),
        out_delay_max=float(params.get("out_delay_max", defaults.out_delay_max)),
        out_delay_min=float(params.get("out_delay_min", defaults.out_delay_min)),
        add_drive_cell=bool(params.get("add_drive_cell", defaults.add_drive_cell)),
        drive_cell_name=str(params.get("drive_cell_name", "BUF_X4")),
        add_input_transition=bool(params.get("add_input_transition", defaults.add_input_transition)),
        input_transition_val=float(params.get("input_transition_val", defaults.input_transition_val)),
        add_load=bool(params.get("add_load", defaults.add_load)),
        load_val=float(params.get("load_val", defaults.load_val)),
        max_fanout=int(params.get("max_fanout", defaults.max_fanout)),
        max_transition=float(params.get("max_transition", defaults.max_transition)),
        max_cap=float(params.get("max_cap", defaults.max_cap)),
        max_area=float(params["max_area"]) if params.get("max_area") else None,
        min_cap=float(params["min_cap"]) if params.get("min_cap") else None,
        add_oper_cond=bool(params.get("add_oper_cond", defaults.add_oper_cond)),
        oper_cond_name=str(params.get("oper_cond_name", "WORST")),
        add_derate=bool(params.get("add_derate", defaults.add_derate)),
        derate_cell_late=float(params.get("derate_cell_late", defaults.derate_cell_late)),
        derate_cell_early=float(params.get("derate_cell_early", defaults.derate_cell_early)),
        derate_net_late=float(params.get("derate_net_late", defaults.derate_net_late)),
        derate_net_early=float(params.get("derate_net_early", defaults.derate_net_early)),
        add_ideal_rst=bool(params.get("add_ideal_rst", defaults.add_ideal_rst)),
        rst_port=str(params.get("rst_port", "rst_n")),
        add_scan=bool(params.get("add_scan", defaults.add_scan)),
        scan_port=str(params.get("scan_port", "scan_en")),
        add_min_pulse=bool(params.get("add_min_pulse", defaults.add_min_pulse)),
        min_pulse_val=float(params.get("min_pulse_val", defaults.min_pulse_val)),
        add_group_path=bool(params.get("add_group_path", defaults.add_group_path)),
        path_groups=[_gen.PathGroup(name=str(g.get("name", "reg2reg")))
                     for g in (params.get("path_groups") or [])],
        add_wire_load=bool(params.get("add_wire_load", defaults.add_wire_load)),
        wire_load_mode=str(params.get("wire_load_mode", "top")),
        wire_load_model=str(params.get("wire_load_model", "")),
        add_power=bool(params.get("add_power", defaults.add_power)),
        max_dyn_power=float(params.get("max_dyn_power", defaults.max_dyn_power)),
        max_leak_power=float(params.get("max_leak_power", defaults.max_leak_power)),
        dont_use=[str(x) for x in (params.get("dont_use") or [])],
    )
    return {"sdc": generate_sdc(p)}


def corners_json(corners: list) -> dict:
    from corner_manager import (Corner, validate_corner, corner_matrix)

    def _corner(d):
        return Corner(
            name=str(d.get("name", "CORNER")),
            operating_condition=str(d.get("operating_condition", "")),
            voltage=float(d.get("voltage", 0.72)),
            temperature=float(d.get("temperature", -40.0)),
            process_type=str(d.get("process_type", "SSG")),
            derate_cell_early=float(d.get("derate_cell_early", 1.08)),
            derate_cell_late=float(d.get("derate_cell_late", 0.92)),
            derate_net_early=float(d.get("derate_net_early", 1.0)),
            derate_net_late=float(d.get("derate_net_late", 1.0)),
            uncertainty_scale=float(d.get("uncertainty_scale", 1.0)),
        )
    cs = [_corner(d) for d in corners]
    errors = []
    for c in cs:
        for e in validate_corner(c):
            errors.append({"corner": c.name, "error": e})
    return {"corners": [_jsonable(c) for c in cs],
            "errors": errors,
            "matrix": corner_matrix(cs)}


def mmc_json(template: dict, corners: list) -> dict:
    from corner_manager import Corner
    from generator import SDCParams
    import generator as _gen
    from mmc import generate_corner_sdcs, diff_corners, check_sdc_multi

    def _clock(d):
        return _gen.ClockDef(
            name=str(d.get("name", "clk_core")),
            port=str(d.get("port", "clk")),
            period=float(d.get("period", 5.0)),
            uncertainty=float(d.get("uncertainty", 0.15)),
            clk_type=str(d.get("clk_type", "primary")),
            master_port=str(d.get("master_port", "")),
            divide_by=int(d.get("divide_by", 2)),
            multiply_by=int(d.get("multiply_by") or 0) or None,
        )

    t = SDCParams(
        design_name=str(template.get("design_name", "MY_DESIGN")),
        sdc_version=str(template.get("sdc_version", "2.2")),
        clocks=[_clock(d) for d in (template.get("clocks") or [])],
        in_delay_max=float(template.get("in_delay_max", 1.2)),
        in_delay_min=float(template.get("in_delay_min", 0.4)),
        out_delay_max=float(template.get("out_delay_max", 1.5)),
        out_delay_min=float(template.get("out_delay_min", 0.5)),
    )
    cs = [Corner(
        name=str(d.get("name", "C")),
        operating_condition=str(d.get("operating_condition", "")),
        voltage=float(d.get("voltage", 0.72)),
        temperature=float(d.get("temperature", -40.0)),
        process_type=str(d.get("process_type", "SSG")),
        derate_cell_early=float(d.get("derate_cell_early", 1.08)),
        derate_cell_late=float(d.get("derate_cell_late", 0.92)),
        derate_net_early=float(d.get("derate_net_early", 1.0)),
        derate_net_late=float(d.get("derate_net_late", 1.0)),
        uncertainty_scale=float(d.get("uncertainty_scale", 1.0)),
    ) for d in corners]
    sdcs = generate_corner_sdcs(t, cs)
    names = list(sdcs.keys())
    diffs = []
    for i in range(1, len(names)):
        diffs.append({
            "pair": [names[i - 1], names[i]],
            "lines": _jsonable(diff_corners(sdcs[names[i - 1]], sdcs[names[i]],
                                             names[i - 1], names[i])),
        })
    result = check_sdc_multi(sdcs)
    return {
        "sdcs": sdcs,
        "diffs": _jsonable(diffs),
        "names": names,
        "check": {
            "errors": len(getattr(result, "errors", [])),
            "warnings": len(getattr(result, "warnings", [])),
        },
    }


def mmc_zip_bytes(template: dict, corners: list) -> bytes:
    """Bundle the per-corner SDCs into an in-memory ZIP archive.

    Reuses ``mmc_json`` so the archive always matches what the MMC page
    rendered (same template/corners → same corner names and content).
    Returns raw bytes for a binary ``application/zip`` response.
    """
    sdcs = mmc_json(template, corners)["sdcs"]
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, text in sdcs.items():
            safe = re.sub(r"[^A-Za-z0-9._-]", "_", name) or "corner"
            zf.writestr(f"{safe}.sdc", text)
    return buf.getvalue()


def diff_sdc_json(v1: str, v2: str) -> dict:
    """V1 vs V2 SDC regression diff (readiness_diff authority)."""
    from checker import check_sdc
    from readiness_diff import build_snapshot, diff_snapshots
    base = build_snapshot(check_sdc(v1), source_name="v1")
    cur = build_snapshot(check_sdc(v2), source_name="v2")
    return diff_snapshots(base, cur)


def report_html_json(analysis: dict, sdc: str) -> dict:
    """Render the standalone HTML report from an analysis payload.

    The reporter is the authority; we rebuild a lightweight CheckResult-like
    object from the serialized payload so reporter.generate_check_report
    keeps its tested code path.
    """
    from checker import Issue, InfoItem, CheckResult
    res = CheckResult()
    for it in (analysis.get("issues") or []):
        res.issues.append(Issue(
            sev=it.get("sev", "info"), code=it.get("code", ""),
            msg=it.get("msg", ""), line=int(it.get("line") or 0),
            line2=int(it.get("line2") or 0), identity=it.get("identity"),
        ))
    for i in (analysis.get("info") or []):
        res.info.append(InfoItem(code=i.get("code", ""), msg=i.get("msg", "")))
    res.stats = analysis.get("stats") or {}
    res.scope = analysis.get("scope") or {}
    res.coverage = analysis.get("coverage") or {}
    res.interactions = analysis.get("interactions") or {}
    res.readiness = analysis.get("readiness") or {}
    from reporter import generate_check_report
    html = generate_check_report(res, filename="analyzed.sdc", verbose=False)
    return {"html": html}


def feedback_json(entry: dict) -> dict:
    from rta.workspace.server.feedback import FeedbackEntry, save_feedback
    e = FeedbackEntry(
        timestamp=str(entry.get("timestamp", "")),
        feature=str(entry.get("feature", "")),
        rating=int(entry.get("rating", 0)),
        comment=str(entry.get("comment", "")),
        sdc_file=str(entry.get("sdc_file", "")),
        results_summary=str(entry.get("results_summary", "")),
    )
    save_feedback(e)
    return {"ok": True}


def design_meta() -> dict:
    """Design tokens + status metadata — single source of truth for the UI."""
    from rta.branding.tokens import theme
    return {
        "version": APP_VERSION,
        "colors": theme.COLORS,
        "fonts": {"ui": theme.FONT_UI, "mono": theme.FONT_MONO},
        "spacing": theme.SPACING,
        "radius": theme.RADIUS,
        "motion": theme.MOTION,
        "severity": theme.SEVERITY,
        "trust": theme.TRUST,
        "readiness": theme.READINESS,
        "diff": theme.DIFF,
        "pass_fail": theme.PASS_FAIL,
    }


def rules_json() -> dict:
    rules = get_all_rules()
    return {
        "count": len(rules),
        "rules": [{
            "code": r.code, "severity": r.severity, "short_name": r.short_name,
            "description": r.description, "why_matters": r.why_matters,
            "fix": r.fix, "reference_url": r.reference_url,
            "module": r.module, "added_version": r.added_version,
        } for r in rules],
    }


# ═══════════════════════════════════════════════════════════════════════════
# HTTP HANDLER
# ═══════════════════════════════════════════════════════════════════════════

_MIME = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "application/javascript; charset=utf-8",
    ".svg": "image/svg+xml",
    ".json": "application/json; charset=utf-8",
    ".png": "image/png",
    ".ico": "image/x-icon",
    ".woff2": "font/woff2",
}


class Handler(BaseHTTPRequestHandler):
    server_version = "rta/1.3"

    # ── helpers ──────────────────────────────────────────────────────────
    def _send(self, code: int, body: bytes, ctype: str = "application/json"):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        try:
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):  # pragma: no cover
            pass

    def _json(self, code: int, obj):
        body = json.dumps(obj, ensure_ascii=False, default=str).encode("utf-8")
        self._send(code, body, "application/json; charset=utf-8")

    def _read_body(self) -> dict:
        length = int(self.headers.get("Content-Length") or 0)
        if length <= 0:
            return {}
        raw = self.rfile.read(length)
        try:
            data = json.loads(raw.decode("utf-8", errors="replace"))
            return data if isinstance(data, dict) else {}
        except json.JSONDecodeError:
            return {}

    def _serve_static(self, path: str):
        rel = path.lstrip("/")
        if not rel or rel.endswith("/"):
            rel = os.path.join(rel, "index.html")
        # prevent path traversal
        full = os.path.normpath(os.path.join(WEBUI_DIR, rel))
        if not full.startswith(os.path.normpath(WEBUI_DIR)):
            self._json(403, {"error": "forbidden"})
            return
        if not os.path.isfile(full):
            # SPA fallback
            full = os.path.join(WEBUI_DIR, "index.html")
        if not os.path.isfile(full):
            self._json(404, {"error": "not found"})
            return
        ext = os.path.splitext(full)[1].lower()
        ctype = _MIME.get(ext, "application/octet-stream")
        with open(full, "rb") as f:
            body = f.read()
        self._send(200, body, ctype)

    # ── routing ──────────────────────────────────────────────────────────
    def do_GET(self):  # noqa: N802
        parsed = urlparse(self.path)
        path = parsed.path
        if path == "/api/health":
            return self._json(200, {
                "ok": True, "version": APP_VERSION,
                "status": "RC_READY_WITH_KNOWN_LIMITATIONS",
                "backend": "frozen-deterministic",
            })
        if path == "/api/design":
            try:
                return self._json(200, design_meta())
            except Exception as exc:  # pragma: no cover
                return self._json(500, {"error": str(exc)})
        if path == "/api/rules":
            try:
                return self._json(200, rules_json())
            except Exception as exc:  # pragma: no cover
                return self._json(500, {"error": str(exc)})
        if path.startswith("/api/"):
            return self._json(404, {"error": "unknown api endpoint"})
        return self._serve_static(path)

    def do_POST(self):  # noqa: N802
        parsed = urlparse(self.path)
        path = parsed.path
        body = self._read_body()
        try:
            if path == "/api/analyze":
                return self._json(200, analyze(
                    sdc_text=body.get("sdc", ""),
                    netlist=body.get("netlist", ""),
                    top=body.get("top", ""),
                    baseline=body.get("baseline", ""),
                    gate=body.get("gate", ""),
                    custom_rules=body.get("custom_rules", ""),
                    rules_filename=body.get("rules_filename", "rules.yaml"),
                ))
            if path == "/api/lint":
                return self._json(200, lint_sdc_json(body.get("sdc", ""),
                                                     fix=bool(body.get("fix", True))))
            if path == "/api/convert":
                return self._json(200, convert_sdc_json(body.get("sdc", ""),
                                                        fmt=body.get("format", "json")))
            if path == "/api/generate":
                return self._json(200, generate_sdc_json(body.get("params", {})))
            if path == "/api/corners":
                return self._json(200, corners_json(body.get("corners", [])))
            if path == "/api/mmc":
                return self._json(200, mmc_json(body.get("template", {}),
                                                body.get("corners", [])))
            if path == "/api/mmc/zip":
                return self._send(200, mmc_zip_bytes(body.get("template", {}),
                                                     body.get("corners", [])),
                                  "application/zip")
            if path == "/api/diff":
                return self._json(200, diff_sdc_json(body.get("v1", ""),
                                                     body.get("v2", "")))
            if path == "/api/report/html":
                return self._json(200, report_html_json(body.get("analysis", {}),
                                                        body.get("sdc", "")))
            if path == "/api/feedback":
                return self._json(200, feedback_json(body))
            return self._json(404, {"error": "unknown api endpoint"})
        except Exception as exc:  # noqa: BLE001 - never leak a raw traceback to UI
            tb = traceback.format_exc()[-2000:]
            print(f"[api_server] {path} failed: {tb}", file=sys.stderr)
            return self._json(500, {
                "error": "engine failure",
                "detail": f"{type(exc).__name__}: {exc}",
            })

    def log_message(self, fmt, *args):  # quieter logs
        pass


def run(host: str = "127.0.0.1", port: int = 8501):
    print(f"Ṛta — serving on http://{host}:{port}  (Ctrl+C to stop)")
    srv = ThreadingHTTPServer((host, port), Handler)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        srv.server_close()


if __name__ == "__main__":
    port = 8501
    if len(sys.argv) > 1:
        port = int(sys.argv[1])
    run(port=port)
