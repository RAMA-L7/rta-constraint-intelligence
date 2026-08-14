"""
Ṛta — HTML Report Generator
Produces self-contained signoff-quality HTML reports from checker, diff, and
clock-relations results. No external dependencies — all CSS is inline.

Usage:
    from reporter import generate_check_report, generate_diff_report
    html = generate_check_report(check_result, "path/to/file.sdc")
    open("report.html", "w").write(html)
"""

import html
import os
from datetime import date
from typing import Optional

from rules_registry import APP_VERSION, get_rule


def esc(value) -> str:
    """Escape a value for safe HTML interpolation.

    Reports embed user-controlled engineering text (object names, clock names,
    issue messages, file paths). Everything must render as data — never as
    markup — so untrusted SDC/netlist content cannot inject HTML/JS.
    """
    return html.escape(str(value), quote=True)

# ── Base Template ───────────────────────────────────────────────────────────

_CSS = """
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
       max-width: 1000px; margin: 0 auto; padding: 30px 24px; color: #1f2937;
       background: #ffffff; line-height: 1.5; }
h1 { font-size: 26px; font-weight: 700; margin-bottom: 2px; }
h2 { font-size: 16px; font-weight: 400; color: #6b7280; margin-bottom: 20px; }
h3 { font-size: 15px; font-weight: 600; margin: 20px 0 8px 0; }
.metrics { display: flex; gap: 12px; margin: 16px 0 20px 0; flex-wrap: wrap; }
.metric { background: #f9fafb; border: 1px solid #e5e7eb; border-radius: 10px;
           padding: 14px 22px; min-width: 110px; text-align: center; }
.metric .num { font-size: 30px; font-weight: 700; line-height: 1.1; }
.metric .label { font-size: 11px; color: #6b7280; text-transform: uppercase;
                  letter-spacing: 0.06em; margin-top: 2px; }
.metric.green .num { color: #059669; }
.metric.red .num { color: #dc2626; }
.metric.yellow .num { color: #b8860b; }
.metric.blue .num { color: #2563eb; }
.badge-row { margin: 12px 0 16px 0; }
.badge { display: inline-block; padding: 4px 14px; border-radius: 20px;
          font-size: 13px; font-weight: 600; margin-right: 8px; margin-bottom: 4px; }
.badge-red { background: #fef2f2; color: #991b1b; border: 1px solid #fecaca; }
.badge-yellow { background: #fffbeb; color: #92400e; border: 1px solid #fde68a; }
.badge-blue { background: #eff6ff; color: #1e40af; border: 1px solid #bfdbfe; }
table { width: 100%; border-collapse: collapse; margin: 8px 0 16px 0;
         font-size: 13px; }
th { text-align: left; padding: 8px 12px; background: #f3f4f6;
      border-bottom: 2px solid #d1d5db; font-weight: 600; white-space: nowrap; }
td { padding: 7px 12px; border-bottom: 1px solid #e5e7eb; vertical-align: top; }
tr:hover td { background: #fafafa; }
code { font-family: 'Fira Code', 'Cascadia Code', 'Consolas', monospace;
       font-size: 12px; background: #f3f4f6; padding: 1px 6px; border-radius: 4px;
       word-break: break-all; }
tr.error-row td { background: #fff5f5; }
tr.warn-row td { background: #fffdf0; }
.section { border: 1px solid #e5e7eb; border-radius: 8px; padding: 16px 20px;
            margin: 16px 0; }
.section-title { font-size: 14px; font-weight: 600; margin-bottom: 8px;
                  text-transform: uppercase; letter-spacing: 0.04em; color: #374151; }
.empty-state { color: #9ca3af; font-style: italic; padding: 12px 0; }
.stats-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
               gap: 8px; margin: 8px 0; }
.stat-item { background: #f9fafb; border: 1px solid #e5e7eb; border-radius: 6px;
              padding: 8px 12px; display: flex; justify-content: space-between; }
.stat-key { color: #6b7280; font-size: 12px; }
.stat-val { font-weight: 600; font-size: 13px; }
.footer { font-size: 11px; color: #9ca3af; text-align: center; margin-top: 30px;
           border-top: 1px solid #e5e7eb; padding-top: 14px; }
.diff-side { display: grid; grid-template-columns: 1fr 1fr; gap: 0;
             border: 1px solid #e5e7eb; border-radius: 8px; overflow: hidden; }
.diff-col { padding: 12px; font-family: 'Fira Code', 'Consolas', monospace;
             font-size: 12px; line-height: 1.6; }
.diff-col-a { background: #fff5f5; }
.diff-col-b { background: #f5fffa; border-left: 1px solid #e5e7eb; }
.diff-added { color: #065f46; background: #d1fae5; padding: 1px 4px; border-radius: 3px; }
.diff-removed { color: #991b1b; background: #fee2e2; padding: 1px 4px; border-radius: 3px; }
.diff-empty { color: #9ca3af; font-style: italic; }
.change-card { border: 1px solid #e5e7eb; border-radius: 8px; padding: 12px 16px;
                margin: 8px 0; }
.change-card.fatal { border-left: 4px solid #dc2626; }
.change-card.warning { border-left: 4px solid #b8860b; }
.change-card.info { border-left: 4px solid #2563eb; }
.change-sev { font-weight: 600; font-size: 11px; text-transform: uppercase;
               letter-spacing: 0.06em; }
.change-sev.fatal { color: #dc2626; }
.change-sev.warning { color: #b8860b; }
.change-sev.info { color: #2563eb; }
.change-rule { font-weight: 600; font-size: 12px; font-family: monospace; }
.change-text { font-family: monospace; font-size: 11px; background: #f3f4f6;
                padding: 4px 8px; border-radius: 4px; margin: 4px 0; display: block;
                white-space: pre-wrap; word-break: break-all; }
.clock-matrix { overflow-x: auto; }
.clock-matrix table { font-size: 12px; }
.clock-matrix td, .clock-matrix th { padding: 6px 10px; text-align: center; white-space: nowrap; }
.matrix-correct { background: #d1fae5; color: #065f46; }
.matrix-mismatch { background: #fee2e2; color: #991b1b; }
.matrix-missing { background: #fef3c7; color: #92400e; }
.matrix-sync-missing { background: #dbeafe; color: #1e40af; }
.legend { display: flex; gap: 16px; margin: 8px 0 16px 0; flex-wrap: wrap; }
.legend-item { display: flex; align-items: center; gap: 4px; font-size: 12px;
               padding: 2px 8px; border-radius: 4px; }
"""


def _page(title: str, subtitle: str, body: str, extra_css: str = "") -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(title)} — Ṛta</title>
<style>{_CSS}{extra_css}</style>
</head>
<body>
<h1>{esc(title)}</h1>
<h2>{esc(subtitle)}</h2>
{body}
<div class="footer">Generated by <b>Ṛta</b> v{APP_VERSION} &mdash; {date.today()}</div>
</body></html>"""


def _summary_metrics(items: list[tuple[str, str, str]]) -> str:
    """items: [(value, label, css_class), ...]"""
    parts = []
    for val, label, css in items:
        parts.append(f'<div class="metric {css}"><div class="num">{esc(val)}</div><div class="label">{esc(label)}</div></div>')
    return f'<div class="metrics">{"".join(parts)}</div>'


def _badge(count: int, label: str, css: str) -> str:
    if count == 0:
        return ""
    return f'<span class="badge badge-{css}">{count} {esc(label)}</span>'


def _issue_rows(items, sev_class: str, sev_label: str) -> str:
    rows = ""
    for item in items:
        code = item.code
        msg = esc(item.msg)
        rule = get_rule(code)
        tip = f" — {esc(rule.short_name)}" if rule else ""
        code = esc(code)
        # Dual-line provenance: conflict findings carry line2 (the earlier
        # conflicting constraint's location).
        loc = ""
        if getattr(item, "line", 0):
            loc = f"<span style='color:#6b7280;font-size:11px'>L{item.line}</span>"
        if getattr(item, "line2", 0):
            loc += f" <span style='color:#6b7280;font-size:11px'>↔ L{item.line2}</span>"
        rows += f"""<tr class="{sev_class}-row">
  <td><code>{code}</code></td>
  <td><span style="font-weight:600">{sev_label}</span></td>
  <td>{msg}</td>
  <td>{loc} {tip}</td>
</tr>\n"""
    return rows


def _table(headers: list[str], rows: str, col_styles: str = "") -> str:
    hdr = "".join(f"<th>{esc(h)}</th>" for h in headers)
    return f'<table{col_styles}><thead><tr>{hdr}</tr></thead><tbody>{rows}</tbody></table>'


# ── Check Report ────────────────────────────────────────────────────────────

def generate_check_report(result, filename: str, verbose: bool = False,
                          readiness_diff: Optional[dict] = None) -> str:
    """Generate a formatted HTML report from a CheckResult.

    ``readiness_diff`` (optional, Phase 12): a machine-readable diff from
    readiness_diff.diff_snapshots() — rendered as a "Readiness Diff" section.
    """
    err_c = len(result.errors)
    warn_c = len(result.warnings)
    info_c = len(result.info)
    total = err_c + warn_c + info_c
    stats = result.stats or {}

    metrics = _summary_metrics([
        (str(total), "Total Issues", "blue"),
        (str(err_c), "Errors", "red"),
        (str(warn_c), "Warnings", "yellow"),
        (str(stats.get("clocks", stats.get("Clocks", "—"))), "Clocks", "green"),
    ])

    badges = _badge(err_c, "Errors", "red") + _badge(warn_c, "Warnings", "yellow") + _badge(info_c, "Info", "blue")

    # Issues table
    rows = _issue_rows(result.errors, "error", "ERROR")
    rows += _issue_rows(result.warnings, "warn", "WARNING")
    if verbose:
        rows += _issue_rows(result.info, "info", "INFO")
    issues_table = _table(["Code", "Severity", "Message", "Rule"], rows) if rows else '<div class="empty-state">No issues found.</div>'

    issue_section = f"""<div class="section">
<div class="section-title">Issues</div>
{issues_table}
</div>"""

    # Stats table
    if stats:
        stat_rows = "".join(f'<div class="stat-item"><span class="stat-key">{esc(k)}</span><span class="stat-val">{esc(v)}</span></div>' for k, v in sorted(stats.items()))
        stats_section = f"""<div class="section">
<div class="section-title">Statistics</div>
<div class="stats-grid">{stat_rows}</div>
</div>"""
    else:
        stats_section = ""

    # ── Analysis Scope / trust disclosure (Phase 7) ─────────────────────────
    # A "no issues" report must never read as "everything proven correct".
    scope_section = ""
    scope = getattr(result, "scope", None) or {}
    if scope:
        scope_rows = "".join(
            f'<div class="stat-item"><span class="stat-key">{esc(k)}</span><span class="stat-val">{esc(v)}</span></div>'
            for k, v in [
                ("Trust status", scope.get("status", "NOT_VALIDATED")),
                ("Commands found", scope.get("commands_found", 0)),
                ("Fully analyzed", scope.get("fully_analyzed", 0)),
                ("Partially analyzed", scope.get("partially_analyzed", 0)),
                ("Netlist-dependent refs", scope.get("netlist_required", 0)),
                ("Unsupported constructs", scope.get("unsupported", 0) + scope.get("tcl_execution_required", 0)),
            ])
        ignored = scope.get("ignored_options") or []
        unknown = scope.get("unknown_options") or []
        notes = ""
        if ignored:
            ignored_esc = "</code>, <code>".join(esc(x) for x in sorted(set(ignored))[:12])
            notes += f'<p style="font-size:12px;color:#6b7280;margin-top:6px">⚠️ Options present but not value-analyzed: <code>{ignored_esc}</code></p>'
        if unknown:
            unknown_esc = "</code>, <code>".join(esc(x) for x in sorted(set(unknown))[:12])
            notes += f'<p style="font-size:12px;color:#6b7280">❓ Unrecognized options: <code>{unknown_esc}</code></p>'
        if scope.get("netlist_required"):
            notes += '<p style="font-size:12px;color:#6b7280">🔵 Object references (get_ports/get_pins/all_*…) require design/netlist context to fully verify — SDC-only analysis cannot prove they resolve.</p>'
        if scope.get("unsupported") or scope.get("tcl_execution_required"):
            notes += '<p style="font-size:12px;color:#b91c1c">Input contains constructs outside the validator\'s analysis scope — they were NOT checked.</p>'
        # Phase 8: design-aware metadata (only present when a netlist/inventory
        # was supplied). Lets the report disclose which mode produced the scope.
        design = scope.get("design") or {}
        if design.get("analysis_mode") == "design_aware":
            design_rows = "".join(
                f'<div class="stat-item"><span class="stat-key">{esc(k)}</span><span class="stat-val">{esc(v)}</span></div>'
                for k, v in [
                    ("Analysis mode", "SDC + Design Context"),
                    ("Top module", design.get("top_module", "—")),
                    ("Modules", design.get("modules", 0)),
                    ("Ports", design.get("ports", 0)),
                    ("Instances", design.get("instances", 0)),
                    ("Nets", design.get("nets", 0)),
                    ("Pins", design.get("pins", 0)),
                ])
            notes += ('<div style="margin-top:8px"><b>Design Context</b>'
                      f'<div class="stats-grid">{design_rows}</div></div>')
        scope_section = f"""<div class="section">
<div class="section-title">Analysis Scope</div>
<div class="stats-grid">{scope_rows}</div>
{notes}
<p style="font-size:12px;color:#9ca3af;margin-top:6px">A clean result does not prove correctness of constructs requiring design/netlist context.</p>
</div>"""

    # ── Design constraint coverage (Phase 9) ──────────────────────────────
    # Coverage answers "was something constrained?", NOT "was it constrained
    # correctly?". Reported only in design-aware mode; never a pass/fail.
    cov_section = ""
    cov = getattr(result, "coverage", None) or {}
    if cov.get("summary"):
        s = cov["summary"]
        b_in, b_out = s["inputs"], s["outputs"]
        cov_rows = "".join(
            f'<div class="stat-item"><span class="stat-key">{esc(k)}</span><span class="stat-val">{esc(v)}</span></div>'
            for k, v in [
                ("Inputs constrained", f"{b_in['constrained']}/{b_in['total']}"),
                ("Inputs unconstrained", b_in["unconstrained"]),
                ("Inputs partial bus", b_in["partial"]),
                ("Inputs exempt", b_in["exempt"]),
                ("Inputs unknown intent", b_in["unknown"]),
                ("Outputs constrained", f"{b_out['constrained']}/{b_out['total']}"),
                ("Outputs unconstrained", b_out["unconstrained"]),
                ("Outputs partial bus", b_out["partial"]),
                ("Outputs exempt", b_out["exempt"]),
                ("Clocks defined", s["clocks"]["defined"]),
                ("Clocks structurally resolved", s["clocks"]["structurally_resolved"]),
                ("Clocks no structural fanout", s["clocks"]["no_structural_fanout"]),
                ("Exceptions endpoint-resolved", s["exceptions"]["objects_resolved"]),
                ("Exceptions empty collection", s["exceptions"]["empty_collection"]),
            ])
        port_rows = ""
        for p in cov.get("inputs", []) + cov.get("outputs", []):
            port_rows += f"<tr><td><code>{esc(p['name'])}</code></td><td>{esc(p['direction'])}</td>" \
                         f"<td>{esc(p['class'])}</td><td><b>{esc(p['status'])}</b></td>" \
                         f"<td style='color:#6b7280;font-size:12px'>{esc(p['evidence'])}</td></tr>\n"
        cov_section = f"""<div class="section">
<div class="section-title">Constraint Coverage (design-aware)</div>
<div class="stats-grid">{cov_rows}</div>
<p style="font-size:12px;color:#6b7280;margin-top:6px">Coverage answers “was something constrained?” — it does NOT mean timing will close. A covered port can still violate correctness rules; an exempt port is not verified correct.</p>
{_table(["Port", "Dir", "Class", "Status", "Evidence"], port_rows)}
</div>"""

    # ── Constraint interactions (Phase 10) ─────────────────────────────────
    # Semantic interactions between individually-valid constraints: exact
    # duplicates (redundant), silent overrides, provable conflicts (SDC-069),
    # and exception overlaps needing STA review (SDC-070). Separate from
    # correctness and coverage.
    int_section = ""
    interactions = getattr(result, "interactions", None) or {}
    if interactions.get("summary"):
        s = interactions["summary"]
        int_rows = "".join(
            f'<div class="stat-item"><span class="stat-key">{esc(k)}</span><span class="stat-val">{esc(v)}</span></div>'
            for k, v in [
                ("Constraints analyzed", s.get("constraints_analyzed", 0)),
                ("Exact duplicates", s.get("exact_duplicates", 0)),
                ("Overrides", s.get("overrides", 0)),
                ("Definite conflicts", s.get("definite_conflicts", 0)),
                ("Possible conflicts (need STA)", s.get("possible_conflicts", 0)),
                ("Legal multiple groups", s.get("legal_multiples", 0)),
            ])
        f_rows = ""
        for f in interactions.get("findings", []):
            loc = f"L{f['line']}" if f.get("line") else ""
            if f.get("line2"):
                loc += f" ↔ L{f['line2']}"
            sev_cls = {"error": "error-row", "warning": "warn-row"}.get(f["severity"], "")
            f_rows += f"<tr class='{sev_cls}'><td><code>{esc(f['code'])}</code></td>" \
                      f"<td><b>{esc(f['category'])}</b></td>" \
                      f"<td>{esc(f['severity'])}</td>" \
                      f"<td>{loc}</td><td>{esc(f['msg'])}</td></tr>\n"
        int_section = f"""<div class="section">
<div class="section-title">Constraint Interactions</div>
<div class="stats-grid">{int_rows}</div>
<p style="font-size:12px;color:#6b7280;margin-top:6px">Interactions are a separate dimension from correctness and coverage: a duplicate is redundant, an override silently replaces an earlier value, SDC-069 is provable without STA, and SDC-070 requires STA/path analysis to confirm an actual path overlap.</p>
{_table(["Code", "Category", "Severity", "Lines", "Message"], f_rows) if f_rows else '<div class="empty-state">No constraint interactions detected.</div>'}
</div>"""

    # ── Constraint readiness review (Phase 11) ─────────────────────────────
    # Handoff-oriented aggregation of every layer above. READY never means
    # "timing passes" — the disclosure below makes that explicit.
    rdy_section = ""
    rdy = getattr(result, "readiness", None) or {}
    if rdy.get("overall"):
        overall = rdy["overall"]
        sev_cls = {"BLOCKED": "badge-red", "REVIEW_REQUIRED": "badge-yellow",
                   "READY": "badge-blue", "READY_WITH_ADVISORIES": "badge-blue",
                   "INSUFFICIENT_CONTEXT": "badge-blue"}.get(overall, "badge-blue")
        dim_rows = "".join(
            f'<div class="stat-item"><span class="stat-key">{esc(dim)}</span>'
            f'<span class="stat-val">{esc(ev.get("status", "—"))}</span></div>'
            for dim, ev in sorted(rdy.get("dimensions", {}).items()))
        rows_html = ""
        for kind, bucket in (("Blockers", rdy.get("blockers", [])),
                             ("Needs review", rdy.get("review_items", []))):
            for it in bucket:
                loc = f"L{it['line']}" if it.get("line") else ""
                if it.get("line2"):
                    loc += f" ↔ L{it['line2']}"
                sev_c = {"error": "error-row", "warning": "warn-row"}.get(it.get("severity"), "")
                rows_html += f"<tr class='{sev_c}'><td><code>{esc(it['code'])}</code></td>" \
                             f"<td>{esc(kind)}</td><td>{esc(it.get('priority',''))}</td>" \
                             f"<td>{loc}</td><td>{esc(it['msg'])}</td></tr>\n"
        act_list = "".join(
            f'<li><b>{esc(a["priority"])}</b> {esc(a["category"])} (×{esc(a["count"])}) — '
            f'{esc(", ".join(a.get("evidence", [])[:3]))}</li>'
            for a in rdy.get("actions", [])[:8])
        mode_note = ""
        if rdy.get("mode") == "SDC_ONLY":
            mode_note = ('<p style="font-size:12px;color:#6b7280">Analysis mode: <b>SDC only</b> — '
                         'object references (get_ports/get_pins/all_*) were not verified against a '
                         'design. Upload a netlist for design-aware readiness; this limitation does '
                         'not by itself block readiness.</p>')
        if rdy.get("limited_design_verification"):
            mode_note += ('<p style="font-size:12px;color:#6b7280">Limited design verification: '
                          'netlist-dependent references present without design context.</p>')
        rdy_section = f"""<div class="section">
<div class="section-title">Constraint Readiness Review</div>
<div><span class="badge {sev_cls}">{overall}</span> <span style="font-size:13px;color:#6b7280">mode: {rdy.get('mode', 'SDC_ONLY')}</span></div>
<div class="stats-grid">{dim_rows}</div>
{mode_note}
{_table(["Code", "Tier", "Priority", "Lines", "Finding"], rows_html) if rows_html else ''}
{'<h3>Recommended actions</h3><ul>' + act_list + '</ul>' if act_list else ''}
<p style="font-size:12px;color:#374151;margin-top:8px"><b>This is a constraint-readiness review, NOT an STA timing signoff.</b> '
'READY means the constraint set satisfies the validator\'s supported, evidence-backed readiness '
'criteria for the stated analysis mode — it does NOT mean setup/hold timing passes, paths are '
'correct, or physical/library-based behavior is verified.</p>
</div>"""

    # ── Readiness diff vs baseline (Phase 12) ─────────────────────────────
    # Semantic readiness comparison against a saved baseline snapshot. Shows
    # what became better/worse/unchanged and the optional CI gate verdict.
    rdiff_section = ""
    if readiness_diff:
        compat = readiness_diff.get("compatibility", {}).get("status", "?")
        cls = readiness_diff.get("classification", "?")
        rdy = readiness_diff.get("readiness", {}) or {}
        cls_badge = {"BLOCKING_REGRESSION": "badge-red",
                     "REVIEW_REGRESSION": "badge-yellow",
                     "ADVISORY_REGRESSION": "badge-yellow",
                     "IMPROVEMENT": "badge-blue",
                     "CONTEXT_CHANGE": "badge-blue",
                     "NEUTRAL_CHANGE": "badge-blue",
                     "ENGINE_FAILURE": "badge-red"}.get(cls, "badge-blue")
        dim_rows = "".join(
            f'<div class="stat-item"><span class="stat-key">{esc(dim)}</span>'
            f'<span class="stat-val">{esc(v.get("baseline", ""))} → {esc(v.get("current", ""))} '
            f'({esc(v.get("delta", ""))})</span></div>'
            for dim, v in sorted(rdy.get("dimensions", {}).items()))

        f = readiness_diff.get("findings", {}) or {}
        rows_html = ""
        for kind, bucket in (("New blockers", f.get("new_blockers", [])),
                             ("Resolved blockers", f.get("resolved_blockers", [])),
                             ("New review items", f.get("new_review", [])),
                             ("Resolved review items", f.get("resolved_review", []))):
            for it in bucket:
                loc = f"L{it['line']}" if it.get("line") else ""
                if it.get("line2"):
                    loc += f" ↔ L{it['line2']}"
                rows_html += f"<tr><td><code>{esc(it['code'])}</code></td><td>{esc(kind)}</td>" \
                             f"<td>{loc}</td><td>{esc(it['msg'])}</td></tr>\n"
        chg_rows = "".join(
            f"<tr><td><code>{esc(c['code'])}</code></td><td>{esc(c['before']['msg'][:70])}</td>"
            f"<td>{esc(c['after']['msg'][:70])}</td></tr>\n"
            for c in f.get("changed", [])[:8])
        cov_html = ""
        for side in ("inputs", "outputs"):
            b = (readiness_diff.get("coverage", {}).get(side) or {}).get("newly_unconstrained", [])
            if b:
                cov_html += f"<p style='font-size:12px;color:#92400e'>{len(b)} {esc(side)} newly unconstrained: " \
                            f"<code>{esc(', '.join(b[:10]))}</code></p>"
        # ── Phase 13: baseline debt model ─────────────────────────────────
        # Pre-existing debt (blockers/review/advisories already in the
        # baseline) is exposed separately from new debt so the report can
        # never hide a NEW problem behind unchanged old ones — and never
        # blame the revision for debt that already existed.
        debt_html = ""
        debt = readiness_diff.get("debt", {}) or {}
        ex, nd, rde = debt.get("existing") or {}, debt.get("new_debt") or {}, debt.get("resolved_debt") or {}
        debt_items = []
        if any(ex.values()):
            debt_items.append(f"existing {ex.get('blockers',0)}B / {ex.get('review',0)}R / {ex.get('advisories',0)}A")
        if any(nd.values()):
            debt_items.append(f"<b>new {nd.get('blockers',0)}B / {nd.get('review',0)}R / {nd.get('advisories',0)}A</b>")
        if any(rde.values()):
            debt_items.append(f"resolved {rde.get('blockers',0)}B / {rde.get('review',0)}R / {rde.get('advisories',0)}A")
        if debt_items:
            debt_html = ('<p style="font-size:12px;color:#6b7280">Baseline debt: '
                         ' &nbsp;·&nbsp; '.join(debt_items)
                         + '</p>')
        # ── Phase 13: identity strength disclosure ────────────────────────
        # Findings compared on STRUCTURED identity are message-independent;
        # LEGACY_NORMALIZED fallback is honestly labeled.
        idn_html = ""
        all_f = f.get("new", []) + f.get("resolved", []) + \
                [c.get("before", {}) for c in f.get("changed", [])]
        strengths = {x.get("identity_strength", "") for x in all_f if x.get("identity_strength")}
        if strengths:
            idn_html = ("<p style='font-size:12px;color:#6b7280'>Identity: "
                        + ", ".join(sorted(strengths))
                        + " — STRUCTURED identities are message-independent; "
                          "LEGACY_NORMALIZED is a message-derived fallback.</p>")
        gate_html = ""
        gate = readiness_diff.get("gate")
        if gate:
            gate_badge = "badge-red" if gate.get("result") == "FAIL" else "badge-blue"
            gate_html = (f'<p>CI gate <b>{esc(gate.get("policy"))}</b>'
                         + (f' (<i>{esc(gate.get("policy_name"))}</i>)' if gate.get("policy_name") else '')
                         + f': <span class="badge {gate_badge}">{esc(gate.get("result"))}</span> '
                         f'(exit code {esc(gate.get("exit_code"))})</p>'
                         + "".join(f"<li style='font-size:12px'>{esc(g)}</li>"
                                    for g in gate.get("reasons", [])[:5]))
        _chg_table = _table(["Code", "Before", "After"], chg_rows) if chg_rows else ''
        _fnd_table = (_table(["Code", "Change", "Lines", "Finding"], rows_html)
                      if rows_html else '')
        _gate_html = gate_html or ''
        rdiff_section = (
            '<div class="section">'
            '<div class="section-title">Readiness Diff vs Baseline</div>'
            f'<p>Baseline: <b>{rdy.get("baseline", "?")}</b> → Current: '
            f'<b>{rdy.get("current", "?")}</b> '
            f'<span class="badge {cls_badge}">{cls}</span> · compatibility: {compat}</p>'
            f'<div class="stats-grid">{dim_rows}</div>'
            f'{debt_html}'
            f'{idn_html}'
            f'{cov_html}'
            f'{_fnd_table}'
            f'{_chg_table}'
            f'{_gate_html}'
            '<p style="font-size:12px;color:#374151;margin-top:8px"><b>CI PASS ≠ timing pass.</b> '
            'The gate only reports that no disallowed constraint-readiness regression was '
            'detected under the selected policy and stated analysis context — it does not '
            'prove timing closes.</p>'
            '</div>'
        )

    body = f"""{metrics}
<div class="badge-row">{badges}</div>
{issue_section}
{scope_section}
{cov_section}
{int_section}
{rdy_section}
{rdiff_section}
{stats_section}"""

    return _page("SDC Quality Report", os.path.basename(filename), body)


# ── Diff Report ─────────────────────────────────────────────────────────────

def generate_diff_report(result, v1_name: str, v2_name: str) -> str:
    """Generate an HTML report from a ChangeAnalysisResult."""
    stats = result.stats or {}
    n_fatal = stats.get("fatal", 0)
    n_warn = stats.get("warnings", 0)
    n_info = stats.get("info", 0)

    metrics = _summary_metrics([
        (str(stats.get("v1_constraints", 0)), "V1 Constraints", "blue"),
        (str(stats.get("v2_constraints", 0)), "V2 Constraints", "green"),
        (str(stats.get("added", 0)), "Added", "green"),
        (str(stats.get("removed", 0)), "Removed", "red"),
        (str(stats.get("modified", 0)), "Modified", "yellow"),
    ])

    badges = _badge(n_fatal, "Fatal", "red") + _badge(n_warn, "Warnings", "yellow") + _badge(n_info, "Info", "blue")

    # Change cards
    cards = ""
    for c in result.changes:
        sev = c.rule.severity
        cards += f"""<div class="change-card {sev}">
<div><span class="change-sev {sev}">{esc(sev.upper())}</span> <span class="change-rule">[{esc(c.rule.rule_id)}]</span> {esc(c.rule.description)}</div>
<div style="margin-top:4px;font-size:13px;color:#374151">{esc(c.explanation)}</div>"""
        if c.v1_text:
            cards += f'<span class="change-text" style="color:#991b1b">- {esc(c.v1_text)}</span>'
        if c.v2_text:
            cards += f'<span class="change-text" style="color:#065f46">+ {esc(c.v2_text)}</span>'
        cards += "</div>\n"

    changes_section = f"""<div class="section">
<div class="section-title">Changes ({len(result.changes)})</div>
{cards if cards else '<div class="empty-state">No changes detected.</div>'}
</div>"""

    body = f"""{metrics}
<div class="badge-row">{badges}</div>
{changes_section}"""

    return _page("SDC Change Impact Report", f"{os.path.basename(v1_name)} → {os.path.basename(v2_name)}", body)


# ── Clock Relations Report ──────────────────────────────────────────────────

def generate_clock_report(result, filename: str) -> str:
    """Generate an HTML report from a RelationAnalysisResult."""
    stats = result.stats or {}
    n_mismatch = stats.get("mismatches", 0)
    n_missing = stats.get("missing", 0)
    n_adv = stats.get("advisories", 0)

    metrics = _summary_metrics([
        (str(stats.get("clocks", 0)), "Clocks", "blue"),
        (str(stats.get("pairs", 0)), "Pairs", "green"),
        (str(n_mismatch), "Mismatches", "red"),
        (str(n_missing), "Missing", "yellow"),
        (str(n_adv), "Advisories", "blue"),
    ])

    # P1-2: render each semantic category under its own label — SDC-062
    # missing constraints must never appear under a "mismatches" heading.
    def _cards(items):
        out = ""
        for m in items:
            sev_css = "warning" if m.severity == "warning" else "info"
            out += f"""<div class="change-card {sev_css}">
<div><span class="change-sev {sev_css}">{esc(m.severity.upper())}</span> <span class="change-rule">[{esc(m.code)}]</span></div>
<div style="margin:4px 0"><b>{esc(m.clock_a)}</b> vs <b>{esc(m.clock_b)}</b></div>
<div style="font-size:13px;color:#374151">Specified: {esc(m.specified)} | Expected: {esc(m.expected)}</div>
<div style="font-size:13px;color:#374151;margin-top:2px">{esc(m.msg)}</div>
</div>\n"""
        return out

    sections = ""
    if result.mismatches:
        sections += f"""<div class="section">
<div class="section-title">Mismatches ({len(result.mismatches)})</div>
{_cards(result.mismatches)}
</div>"""
    if result.missing_constraints:
        sections += f"""<div class="section">
<div class="section-title">Missing Constraints ({len(result.missing_constraints)})</div>
{_cards(result.missing_constraints)}
</div>"""
    if result.advisories:
        sections += f"""<div class="section">
<div class="section-title">Advisories ({len(result.advisories)})</div>
{_cards(result.advisories)}
</div>"""
    if not sections:
        sections = '<div class="empty-state">No mismatches found.</div>'
    mismatches_section = sections

    # Clock list
    clk_rows = ""
    for c in result.clocks:
        clk_rows += f"<tr><td><code>{esc(c.name)}</code></td><td>{esc(c.period)}</td><td>{esc(c.source_port)}</td>"
        clk_rows += f"<td>{'✓' if c.is_generated else '-'}</td><td>{esc(c.master_clock) if c.is_generated else '-'}</td><td>{'✓' if c.is_virtual else '-'}</td></tr>\n"
    clk_table = _table(["Name", "Period (ns)", "Port", "Generated", "Master", "Virtual"], clk_rows)
    clk_section = f"""<div class="section">
<div class="section-title">Clock Definitions ({len(result.clocks)})</div>
{clk_table}
</div>"""

    # Clock relation matrix
    if result.clocks:
        names = [c.name for c in result.clocks]
        # Build relation lookup
        rel_map: dict[tuple[str, str], str] = {}
        for p in result.pairs:
            rel_map[(p.clock_a, p.clock_b)] = p.inferred_relation
            rel_map[(p.clock_b, p.clock_a)] = p.inferred_relation
        # Build specified lookup
        spec_map: dict[tuple[str, str], str] = {}
        for g in result.existing_groups:
            group_clocks = g.get("clocks", [])
            gtype = g.get("type", "")
            for ca in group_clocks:
                for cb in group_clocks:
                    if ca != cb:
                        spec_map[(ca, cb)] = gtype

        hdr = "<th>Clock</th>" + "".join(f"<th>{esc(n)}</th>" for n in names)
        mat_rows = ""
        for ca in names:
            cells = f"<td><b>{esc(ca)}</b></td>"
            for cb in names:
                cell_class = ""
                text = "—"
                if ca == cb:
                    cell_class = "matrix-correct"
                else:
                    inferred = rel_map.get((ca, cb), "unknown")
                    specified = spec_map.get((ca, cb), "")
                    if specified:
                        if inferred == specified:
                            cell_class = "matrix-correct"
                            text = "✓"
                        elif (inferred == "physically_exclusive" and specified == "asynchronous") or \
                             (inferred == "synchronous" and specified in ("logically_exclusive", "physically_exclusive")):
                            cell_class = "matrix-mismatch"
                            text = "✗"
                        else:
                            cell_class = "matrix-mismatch"
                            text = "⚠"
                    else:
                        if inferred in ("asynchronous", "physically_exclusive"):
                            cell_class = "matrix-missing"
                            text = "?"
                        else:
                            cell_class = "matrix-sync-missing"
                            text = "~"
                cells += f'<td class="{cell_class}">{text}</td>'
            mat_rows += f"<tr>{cells}</tr>\n"

        legend = """<div class="legend">
<span class="legend-item" style="background:#d1fae5">✓ Correct</span>
<span class="legend-item" style="background:#fee2e2">✗ Mismatch</span>
<span class="legend-item" style="background:#fef3c7">? Missing constraint</span>
<span class="legend-item" style="background:#dbeafe">~ Synchronous (no constraint needed)</span>
</div>"""
        matrix_section = f"""<div class="section">
<div class="section-title">Clock Relation Matrix ({len(names)}×{len(names)})</div>
{legend}
<div class="clock-matrix">{_table(["Clock"] + names, mat_rows)}</div>
</div>"""
    else:
        matrix_section = ""

    body = f"""{metrics}
{mismatches_section}
{clk_section}
{matrix_section}"""

    return _page("SDC Clock Relations Report", os.path.basename(filename), body)


# ── Rules Report ────────────────────────────────────────────────────────────

def generate_rules_report(rules, title: str = "Rules Registry") -> str:
    """Generate an HTML report listing rules from the Rules Registry."""
    rows = ""
    for r in rules:
        sev_css = {"error": "red", "warning": "yellow", "info": "blue", "fatal": "red"}
        badge = f'<span class="badge badge-{sev_css.get(r.severity, "blue")}" style="font-size:11px;padding:1px 8px">{esc(r.severity)}</span>'
        rows += f"<tr><td><code>{esc(r.code)}</code></td><td>{badge}</td><td>{esc(r.module)}</td><td>{esc(r.short_name)}</td><td>{esc(r.description[:80])}{'…' if len(r.description) > 80 else ''}</td><td style='font-size:11px;color:#6b7280'>v{esc(r.added_version)}</td></tr>\n"

    table = _table(["Code", "Severity", "Module", "Name", "Description", "Added"], rows)
    body = f"""<div class="section">
<div class="section-title">{title} ({len(rules)} rules)</div>
{table}
</div>"""
    return _page(title, f"Ṛta v{APP_VERSION}", body)


# ── Coverage Report ─────────────────────────────────────────────────────────

_COV_CSS = """
.cov-bar-bg { background: #e5e7eb; border-radius: 6px; height: 14px; width: 100%; position: relative; }
.cov-bar-fill { height: 14px; border-radius: 6px; transition: width 0.3s; }
.cov-bar-fill.good { background: #059669; }
.cov-bar-fill.warn { background: #d97706; }
.cov-bar-fill.bad { background: #dc2626; }
.cov-item-present { color: #059669; font-weight: 600; }
.cov-item-missing { color: #dc2626; font-weight: 600; }
.cov-item-missing.crit { color: #b91c1c; font-weight: 700; }
.cov-cat-header { display: flex; align-items: center; gap: 8px; margin: 16px 0 6px 0; }
.cov-cat-icon { font-size: 18px; }
.cov-cat-title { font-size: 14px; font-weight: 600; }
.cov-cat-score { font-size: 13px; color: #6b7280; }
.cov-score-big { font-size: 48px; font-weight: 800; text-align: center; margin: 10px 0; }
.cov-score-big.good { color: #059669; }
.cov-score-big.warn { color: #d97706; }
.cov-score-big.bad { color: #dc2626; }
.cov-score-label { font-size: 13px; color: #6b7280; text-align: center; margin-bottom: 16px; }
"""


def generate_coverage_report(result, filename: str) -> str:
    """Generate an HTML report from a CoverageResult."""
    # Coverage-specific CSS is passed through _page as extra_css so the
    # coverage bars/status classes are actually styled (Phase 14 audit fix:
    # previously _COV_CSS was assigned but never rendered).
    # Overall score — status derived from the numeric score (80/50 thresholds).
    if result.score >= 80:
        score_cls = "good"
    elif result.score >= 50:
        score_cls = "warn"
    else:
        score_cls = "bad"

    # Summary metrics
    metrics = _summary_metrics([
        (f"{result.score:.0f}%", "Overall Coverage", score_cls),
        (str(result.total_present), "Items Present", "green"),
        (str(result.total_missing), "Items Missing", "red"),
        (str(len(result.categories)), "Categories", "blue"),
    ])

    # Category cards
    cat_cards = ""
    for cat in result.categories:
        bar_cls = cat.status
        bar_pct = cat.score

        items_html = ""
        for item in cat.items:
            if item.present:
                items_html += f'<tr><td><span class="cov-item-present">&#10003;</span></td><td>{esc(item.name)}</td><td style="color:#6b7280;font-size:12px">{esc(item.detail)}</td></tr>\n'
            else:
                crit_cls = "crit" if item.is_critical else ""
                crit_mark = " <b>*</b>" if item.is_critical else ""
                items_html += f'<tr><td><span class="cov-item-missing {crit_cls}">&#10007;</span></td><td>{esc(item.name)}{crit_mark}</td><td style="color:#6b7280;font-size:12px">{esc(item.detail)}</td></tr>\n'

        cat_cards += f"""<div class="section">
<div class="cov-cat-header">
  <span class="cov-cat-icon">{esc(cat.icon)}</span>
  <span class="cov-cat-title">{esc(cat.name)}</span>
  <span class="cov-cat-score">{cat.score:.0f}% ({cat.covered}/{cat.total})</span>
</div>
<div class="cov-bar-bg"><div class="cov-bar-fill {bar_cls}" style="width:{bar_pct:.0f}%"></div></div>
{_table(["", "Constraint", "Detail"], items_html)}
</div>\n"""

    # Missing items summary
    missing_items = ""
    for cat in result.categories:
        for item in cat.items:
            if not item.present:
                crit = " <b>*</b>" if item.is_critical else ""
                missing_items += f'<tr><td><span class="change-sev warning">{esc(cat.name)}</span></td><td>{esc(item.name)}{crit}</td><td style="color:#6b7280;font-size:12px">{esc(item.detail)}</td></tr>\n'

    missing_section = ""
    if missing_items:
        missing_section = f"""<div class="section">
<div class="section-title">Missing Items ({result.total_missing})</div>
{_table(["Category", "Constraint", "Detail"], missing_items)}
</div>"""

    body = f"""{metrics}
<div class="cov-score-big {score_cls}">{result.score:.1f}%</div>
<div class="cov-score-label">Constraint Coverage — {result.total_present} of {result.total_items} items present</div>
{cat_cards}
{missing_section}"""

    return _page("SDC Constraint Coverage Report", os.path.basename(filename), body,
                 extra_css=_COV_CSS)