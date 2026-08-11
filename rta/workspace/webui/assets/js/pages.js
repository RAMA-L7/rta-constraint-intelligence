/* ═══════════════════════════════════════════════════════════════════════════
   Ṛta — pages.js
   All workspace page renderers. Every page consumes REAL backend evidence
   through the API — no mock data, no invented counts. All user-controlled
   content is escaped via theme.esc.
   ═══════════════════════════════════════════════════════════════════════════ */

import { esc, statusBadge, severityClass } from "./theme.js";
import { pageHead, sectionTitle, metricRow, chips, emptyState, typedError,
         callout, sourceViewer, sourceExcerpt, table, accordion, kvList,
         segFilter, findingRow, findingDetailHtml } from "./components.js";
import { clockTreeHtml, matrixHtml, busStripHtml, readinessRail } from "./viz.js";

export const App = {
  state: {
    analysis: null,      // last /api/analyze payload
    sdc: "",             // current sdc text in editor
    filename: "pasted.sdc",
    filters: { sev: "All", rule: "All", q: "" },
    inspector: null,     // {title, html}
    clockSel: null,
    rules: null,
    // Sprint 3B — session-first architecture. The shell consumes the current
    // session; pages keep reading the flat fields above (they are kept in
    // sync by app.js) so page logic is unchanged.
    session: {
      id: null, name: "Untitled session", status: "EMPTY", createdAt: null,
      sdc: "", netlist: "", filename: "pasted.sdc", analysis: null,
    },
    recentSessions: [],  // in-memory history, this browser tab only
    diffV1: "", diffV2: "", diffResult: null, diffFilter: "new",
    ruleFilter: "All", lintIn: "", convIn: "",
  },
};

/* ── API helpers ────────────────────────────────────────────────────────── */
async function post(path, body) {
  const r = await fetch(path, {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!r.ok) {
    let detail = `HTTP ${r.status}`;
    try { detail = (await r.json()).detail || detail; } catch (e) { /* ignore */ }
    throw new Error(detail);
  }
  return r.json();
}
async function get(path) {
  const r = await fetch(path);
  if (!r.ok) throw new Error(`HTTP ${r.status}`);
  return r.json();
}

export function toast(msg, isErr = false) {
  const t = document.getElementById("toast");
  t.textContent = msg;
  t.className = "toast show" + (isErr ? " err" : "");
  clearTimeout(t._h);
  t._h = setTimeout(() => t.classList.remove("show"), 2600);
}

export function openInspector(title, html) {
  App.state.inspector = { title, html };
  document.getElementById("inspector-title").textContent = title;
  document.getElementById("inspector-body").innerHTML = html;
  document.getElementById("inspector").classList.add("open");
  document.getElementById("inspector").setAttribute("aria-hidden", "false");
  document.getElementById("inspector-backdrop").hidden = false;
}
export function closeInspector() {
  document.getElementById("inspector").classList.remove("open");
  document.getElementById("inspector").setAttribute("aria-hidden", "true");
  document.getElementById("inspector-backdrop").hidden = true;
  App.state.inspector = null;
}

/* ── Shared: finding helpers ────────────────────────────────────────────── */
function findingObj(it) {
  const id = it.identity || {};
  const p = id.primary_object, s = id.secondary_object;
  if (p && s && s !== p) return `${p} ↔ ${s}`;
  return p || "";
}
function findingClk(it) { return (it.identity || {}).clock || ""; }
function findingLoc(it) {
  const parts = [];
  if (it.line) parts.push(`L${it.line}`);
  if (it.line2) parts.push(`L${it.line2}`);
  return parts.join(" ↔ ");
}
function requiresSta(it) {
  if (it.code === "SDC-070") return true;
  const t = ((it.identity || {}).interaction_type || "").toLowerCase();
  return (t.includes("overlap") || t.includes("possible") || t.includes("conflict")) && t.includes("sta");
}
function locLines(it) {
  const out = [];
  if (it.line) out.push(it.line);
  if (it.line2) out.push(it.line2);
  return out;
}

/* ── Overview ───────────────────────────────────────────────────────────── */
export async function pageOverview() {
  const a = App.state.analysis;
  if (!a) {    return pageHead("RESULTS", "Summary", "Run an analysis first — the summary is built from real analysis evidence.")
    + emptyState("No analysis yet", "Run a validation on an SDC file to populate the overview.",
                 "Open New Analysis, load an SDC file, then press Analyze.");
  }
  const rdy = a.readiness || {};
  const issues = a.issues || [];
  const clocks = (a.clock_relations || {}).clocks || [];
  const errs = issues.filter(i => i.sev === "error").length;
  const warns = issues.filter(i => i.sev === "warning").length;
  const infos = issues.filter(i => i.sev === "info").length;
  const blockers = (rdy.blockers || []).slice(0, 6);
  const cov = a.coverage || {};
  const covSum = cov.summary || {};
  const int = a.interactions || {};
  const intSum = int.summary || {};

  let html = pageHead("RESULTS", "Summary", "The executive view — verdict, trust, blockers, clocks, coverage.",
                      "Start with the verdict, then open Findings for the detail.");
  html += `<div class="rdy-overall">
    <div><div class="ro-label">Overall readiness</div><div class="ro-value">${statusBadge("readiness", rdy.overall || "INSUFFICIENT_CONTEXT")}</div></div>
    <div style="margin-left:auto;text-align:right"><div class="ro-label">Analysis mode</div><div class="mono" style="font-size:13px;color:var(--text-secondary)">${esc((a.mode_note || "SDC only").split(" (")[0])}</div></div>
  </div>`;
  html += readinessRail(rdy);

  html += metricRow([
    { label: "Errors", value: errs }, { label: "Warnings", value: warns },
    { label: "Advisories", value: infos }, { label: "Clocks", value: clocks.length },
    { label: "Inputs", value: (covSum.inputs || {}).total ?? "—" },
    { label: "Outputs", value: (covSum.outputs || {}).total ?? "—" },
  ]);

  html += sectionTitle("Trust / analysis scope");
  html += `<div class="chips">${statusBadge("trust", (a.scope || {}).status || "NOT_VALIDATED")}</div>`;
  const sc = a.scope || {};
  html += `<div class="mono" style="font-size:12px;color:var(--text-secondary);margin-top:4px">${esc(sc.commands_found ?? 0)} commands · ${esc(sc.fully_analyzed ?? 0)} fully analyzed · ${esc(sc.partially_analyzed ?? 0)} partial · ${esc((sc.netlist_required ?? 0) + (sc.tcl_execution_required ?? 0))} netlist/Tcl dependent · ${esc(sc.unsupported ?? 0)} unsupported</div>`;

  if (blockers.length) {
    html += sectionTitle(`Blockers (${blockers.length})`);
    html += blockers.map(b => `<div class="ilink"><span class="il-rule">${esc(b.code)}</span><span class="il-kind" style="color:var(--error)">BLOCKER</span><span class="il-a">${esc(b.msg)}</span>${b.line ? `<span class="il-loc">L${b.line}${b.line2 ? " ↔ L" + b.line2 : ""}</span>` : ""}</div>`).join("");
  }

  if (clocks.length) {
    html += sectionTitle("Clock health", `${clocks.length} clock(s)`);
    html += `<div class="ilink"><span class="il-rule">→</span><span class="il-a">${esc(clocks.map(c => c.name).join(", "))}</span><span class="il-loc"><a href="#/clocks">Open Clock Intelligence →</a></span></div>`;
  }

  if (covSum.inputs || covSum.outputs) {
    html += sectionTitle("Coverage", "coverage ≠ correctness");
    html += `<div class="mono" style="font-size:12px;color:var(--text-secondary)">inputs ${esc(JSON.stringify(covSum.inputs || {}))}</div>`;
    html += `<div class="mono" style="font-size:12px;color:var(--text-secondary)">outputs ${esc(JSON.stringify(covSum.outputs || {}))}</div>`;
    html += `<p class="callout co-info" style="margin-top:6px"><span><strong>Coverage is not correctness</strong> — a fully covered design can still have timing errors.</span></p>`;
  }

  if (intSum.constraints_analyzed) {
    html += sectionTitle("Interactions");
    html += metricRow([
      { label: "Analyzed", value: intSum.constraints_analyzed ?? 0 },
      { label: "Duplicates", value: intSum.exact_duplicates ?? 0 },
      { label: "Overrides", value: intSum.overrides ?? 0 },
      { label: "Conflicts", value: intSum.definite_conflicts ?? 0 },
      { label: "Need STA", value: intSum.possible_conflicts ?? 0 },
    ]);
  }

  if ((rdy.actions || []).length) {
    html += sectionTitle("Recommended actions");
    html += rdy.actions.slice(0, 6).map(act =>
      `<div class="ilink"><span class="il-rule">${esc(act.priority || "P3")}</span><span class="il-kind" style="color:var(--accent-2)">${esc(act.category || "")}</span><span class="il-a">×${esc(act.count ?? 1)} — ${esc((act.evidence || []).slice(0, 2).join(", "))}</span></div>`
    ).join("");
  }

  html += `<p class="callout co-warning" style="margin-top:16px"><span><strong>READY ≠ STA signoff</strong> — this is a constraint-quality review, not a timing signoff.</span></p>`;
  return html + "</div>";
}

/* ── New Analysis (first-run entry) ────────────────────────────────────── */
export async function pageNewAnalysis() {
  const has = !!App.state.analysis;
  let html = pageHead("ṚTA", "Check your SDC before STA",
    "Drop in your SDC constraint file — Ṛta runs a deterministic check for the issues that surface at STA, before they cost you a run.",
    has ? "Analysis loaded — load a new SDC to re-run, or explore the results."
        : "The sample is loaded — press Analyze, or load your own SDC.");
  html += `<div class="input-surface entry">
    <div class="entry-step">
      <div class="es-num">1</div>
      <div class="es-main">
        <div class="es-head"><span class="es-title">SDC constraint file</span><span class="es-req">REQUIRED</span></div>
        <div class="es-actions">
          <button class="btn btn-sm" id="na-pick" type="button">Choose file…</button>
          <button class="btn btn-sm btn-ghost" id="na-sample" type="button">Load sample</button>
          <button class="btn btn-sm btn-ghost" id="na-clear" type="button">Clear</button>
          <span class="is-file mono" id="na-file">${esc(App.state.filename)}</span>
        </div>
        <textarea class="code-input" id="na-sdc" rows="9" spellcheck="false" placeholder="set sdc_version 2.2&#10;create_clock -name clk -period 5.0 [get_ports clk]&#10;...">${esc(App.state.sdc)}</textarea>
      </div>
    </div>
    <div class="entry-step">
      <div class="es-num">2</div>
      <div class="es-main">
        <div class="es-head"><span class="es-title">Netlist (Verilog)</span><span class="es-opt">OPTIONAL</span></div>
        <p class="es-why">Optional — SDC-only mode validates syntax, semantics, clocks and readiness without a netlist. Adding a netlist unlocks design-object resolution and constraint coverage.</p>
        <div class="es-actions">
          <button class="btn btn-sm" id="na-net-pick" type="button">Choose file…</button>
          <button class="btn btn-sm btn-ghost" id="na-net-clear" type="button">Clear</button>
          <span class="is-file mono" id="na-net-file">no netlist</span>
        </div>
        <textarea class="opt-text" id="na-netlist" rows="4" spellcheck="false" placeholder="module top ( input clk, ... );"></textarea>
      </div>
    </div>
    <details class="entry-adv"><summary>Advanced options — baseline snapshot · CI gate policy · custom rules</summary>
      <div class="optional-panel">
        <div><label class="opt-label">Baseline snapshot (JSON, optional)</label><textarea class="opt-text" id="na-baseline" rows="2" spellcheck="false" placeholder='{"version": 2, ...}'></textarea></div>
        <div><label class="opt-label">CI gate policy</label><select class="opt-select" id="na-gate"><option value="">None</option><option>BLOCKERS_ONLY</option><option>NO_READINESS_REGRESSION</option><option>STRICT</option></select></div>
        <div><label class="opt-label">Custom rules (YAML, optional)</label><textarea class="opt-text" id="na-rules" rows="3" spellcheck="false" placeholder="name: my-team&#10;rules:&#10;  - id: CUST-001&#10;    command: create_clock&#10;    condition: present&#10;    severity: error&#10;    message: clocks required"></textarea></div>
      </div>
    </details>
    <div class="entry-foot">
      <button class="btn btn-primary btn-lg" id="na-analyze" type="button">Analyze</button>
      <span class="mono" style="font-size:11px;color:var(--text-muted)">runs locally · deterministic · offline · no LLM</span>
    </div>
  </div>`;
  return html + "</div>";
}

/* ── Validator ──────────────────────────────────────────────────────────── */
export async function pageValidator() {
  const a = App.state.analysis;
  const sdc = App.state.sdc;

  let html = pageHead("RESULTS", "Findings", "What did Ṛta find in your SDC? Every finding traces to a rule and a source line.",
                      "Click a finding to inspect its rule, evidence and source line.");
  html += `<div class="input-surface">
    <div class="input-surface-head">
      <span class="is-title">Constraint input</span>
      <span class="is-file" id="val-file">${esc(App.state.filename)}</span>
      <button class="btn btn-sm" id="val-load-sample" type="button">Load sample</button>
      <button class="btn btn-sm btn-ghost" id="val-clear" type="button">Clear</button>
    </div>
    <textarea class="code-input" id="val-sdc" spellcheck="false" placeholder="set sdc_version 2.2&#10;create_clock -name clk_core -period 5.0 [get_ports clk]&#10;set_clock_uncertainty -setup 0.15 [get_clocks clk_core]&#10;...">${esc(sdc)}</textarea>
    <div class="optional-panel">
      <div>
        <label class="opt-label" for="val-netlist">Netlist (Verilog, optional)</label>
        <textarea class="opt-text" id="val-netlist" rows="3" spellcheck="false" placeholder="module top ( input clk, ... );"></textarea>
      </div>
      <div>
        <label class="opt-label" for="val-baseline">Baseline snapshot (JSON, optional)</label>
        <textarea class="opt-text" id="val-baseline" rows="3" spellcheck="false" placeholder='{"version": 2, ...}'></textarea>
      </div>
      <div>
        <label class="opt-label" for="val-gate">CI gate policy</label>
        <select class="opt-select" id="val-gate">
          <option value="">None</option>
          <option value="BLOCKERS_ONLY">BLOCKERS_ONLY</option>
          <option value="NO_READINESS_REGRESSION">NO_READINESS_REGRESSION</option>
          <option value="STRICT">STRICT</option>
        </select>
      </div>
      <div>
        <label class="opt-label" for="val-rules">Custom rules (YAML, optional)</label>
        <textarea class="opt-text" id="val-rules" rows="3" spellcheck="false" placeholder="name: my-team&#10;rules:&#10;  - id: CUST-001&#10;    command: create_clock&#10;    condition: present&#10;    severity: error&#10;    message: clocks required"></textarea>
      </div>
    </div>
    <div style="padding:10px 14px;display:flex;gap:10px;align-items:center;border-top:1px solid var(--border-subtle)">
      <button class="btn btn-primary" id="val-analyze" type="button">Analyze</button>
      <span class="mono" style="font-size:11px;color:var(--text-muted)">runs locally · deterministic · offline</span>
    </div>
  </div>`;

  if (!a) {
    html += emptyState("Ready to analyze", "Paste or upload SDC text above, then press Analyze.", "Findings, scope, readiness and provenance render here after the run.");
    return html + "</div>";
  }

  const issues = (a.issues || []).map((it, i) => ({ ...it, _i: i, obj: findingObj(it), clk: findingClk(it), loc: findingLoc(it), requires_sta: requiresSta(it) }));
  const errs = issues.filter(i => i.sev === "error").length;
  const warns = issues.filter(i => i.sev === "warning").length;
  const infos = issues.filter(i => i.sev === "info").length;

  html += `<div class="mono" style="font-size:12px;color:var(--text-secondary);margin:8px 0">analysis mode: ${esc(a.mode_note || "SDC only")} · ${esc((a.stages || []).join(" → "))}</div>`;
  html += chips([statusBadge("trust", (a.scope || {}).status || "NOT_VALIDATED"), statusBadge("readiness", (a.readiness || {}).overall || "—")]);
  if (a.engine_error) html += typedError("engine", a.engine_error);
  if (a.nl_error) html += typedError("insufficient", `Design context not loaded: ${a.nl_error}`);

  html += metricRow([
    { label: "Errors", value: errs }, { label: "Warnings", value: warns },
    { label: "Info", value: infos }, { label: "Clocks", value: (a.stats || {}).Clocks ?? 0 },
  ]);

  if (errs) html += callout(`${errs} error(s) must be reviewed before synthesis. A clean check is not an STA timing signoff.`, "error");
  else if (warns) html += callout(`No errors — ${warns} warning(s) need review.`, "warning");
  else html += callout("No errors or warnings within scope. See the analysis scope for what was verified — this is not an STA signoff.", "info");

  // filters
  html += `<div class="filters">
    <div class="f-field"><label>Severity</label>${segFilter("sev", ["All", "error", "warning", "info"], App.state.filters.sev)}</div>
    <div class="f-field"><label>Rule</label><select class="select-input" id="f-rule"><option>All</option>${[...new Set(issues.map(i => i.code))].sort().map(c => `<option${c === App.state.filters.rule ? " selected" : ""}>${esc(c)}</option>`).join("")}</select></div>
    <div class="f-field"><label>Search</label><input class="search-input" id="f-q" placeholder="object, clock, message…" value="${esc(App.state.filters.q)}"></div>
    <button class="btn btn-sm btn-ghost" id="f-clear" type="button">Clear filters</button>
  </div>`;

  const f = App.state.filters;
  const ql = f.q.trim().toLowerCase();
  const filtered = issues.filter(it => {
    if (f.sev !== "All" && it.sev !== f.sev) return false;
    if (f.rule !== "All" && it.code !== f.rule) return false;
    if (ql && ![it.msg, it.code, it.obj, it.clk].some(v => (v || "").toLowerCase().includes(ql))) return false;
    return true;
  });

  if (!issues.length) html += emptyState("No issues found", "No findings within the supported analysis scope.", "Review the analysis scope — a clean check is not an STA timing signoff.");
  else if (!filtered.length) html += emptyState("No matching findings", "No findings match the current severity / rule / search filters.", "Clear or loosen filters to see the full finding list.");
  else {
    html += `<div class="mono" style="font-size:11px;color:var(--text-muted);margin:6px 0">${filtered.length} of ${issues.length} findings shown</div>`;
    html += table(
      [{ label: "Severity" }, { label: "Rule" }, { label: "Finding" }, { label: "Object" }, { label: "Clock" }, { label: "Loc" }],
      filtered.map(it => ({ key: `${it.code}-${it.line}-${it._i}`, cells: [
        { html: statusBadge("severity", it.sev) },
        { html: `<span class="mono">${esc(it.code)}</span>` },
        { html: `<span class="msg">${esc(it.msg)}</span>` },
        { html: `<span class="mono">${esc(it.obj)}</span>` },
        { html: `<span class="mono">${esc(it.clk)}</span>` },
        { html: `<span class="mono">${esc(it.loc)}</span>` },
      ] })),
      { clickable: true }
    );
    html += `<div style="margin-top:10px">`;
    html += filtered.slice(0, 12).map(it => accordion(`${it.code} — ${it.msg.length > 80 ? it.msg.slice(0, 80) + "…" : it.msg}`,
      findingDetailHtml(it, App.state.rules ? App.state.rules.find(r => r.code === it.code) : null)
      + sourceExcerpt(App.state.sdc.split("\n"), locLines(it)), {})).join("");
    if (filtered.length > 12) html += `<div class="mono" style="font-size:11px;color:var(--text-muted)">… ${filtered.length - 12} more details; all findings are in the table above.</div>`;
    html += `</div>`;
  }

  // source viewer
  html += sectionTitle("Source", "line numbers · finding highlights · dual-line marked ↔");
  const hl = {};
  issues.forEach(it => {
    const cls = it.sev === "warning" ? "hl-warn" : "hl";
    if (it.line) hl[it.line] = (hl[it.line] || "") + " " + cls;
    if (it.line2) hl[it.line2] = (hl[it.line2] || "") + " hl";
  });
  html += sourceViewer(App.state.sdc.split("\n"), hl);

  // secondary panels
  html += renderScope(a);
  html += renderCoverage(a);
  html += renderInteractions(a);
  html += renderReadiness(a);
  html += renderBaseline(a);
  html += renderCustomRules(a);
  return html + "</div>";
}

function renderScope(a) {
  const sc = a.scope || {};
  if (!sc.commands_found && !sc.status) return "";
  let h = sectionTitle("Analysis coverage", "what was actually checked");
  h += `<div class="chips">${statusBadge("trust", sc.status || "NOT_VALIDATED")}</div>`;
  h += metricRow([
    { label: "Commands", value: sc.commands_found ?? 0 }, { label: "Fully analyzed", value: sc.fully_analyzed ?? 0 },
    { label: "Partial", value: sc.partially_analyzed ?? 0 }, { label: "Netlist-dep", value: sc.netlist_required ?? 0 },
    { label: "Unsupported", value: (sc.unsupported ?? 0) + (sc.tcl_execution_required ?? 0) },
  ]);
  if (sc.ignored_options && sc.ignored_options.length) h += `<div class="mono" style="font-size:11.5px;color:var(--text-muted);margin-top:4px">options present but not value-analyzed: ${esc([...new Set(sc.ignored_options)].slice(0, 12).join(", "))}</div>`;
  if (sc.netlist_required) h += `<p class="callout co-info" style="margin-top:6px"><span><strong>Netlist-dependent references</strong> — object references require design context to fully verify in SDC-only mode.</span></p>`;
  if (sc.unsupported || sc.tcl_execution_required) h += `<p class="callout co-warning"><span><strong>Unsupported constructs present</strong> — outside the analysis scope; review manually.</span></p>`;
  return h;
}

function renderCoverage(a) {
  const cov = a.coverage || {};
  const sum = cov.summary || {};
  if (!sum.inputs && !sum.outputs && !sum.clocks) return "";
  let h = sectionTitle("Constraint coverage", "how completely the SDC describes timing intent");
  h += `<p class="callout co-info"><span><strong>Coverage is NOT correctness</strong> — a fully covered design can still have timing errors.</span></p>`;
  h += metricRow([
    { label: "Inputs", value: sum.inputs ? `${sum.inputs.constrained}/${sum.inputs.total}` : "—" },
    { label: "Outputs", value: sum.outputs ? `${sum.outputs.constrained}/${sum.outputs.total}` : "—" },
    { label: "Clocks defined", value: (sum.clocks || {}).defined ?? "—" },
    { label: "Exceptions", value: (sum.exceptions || {}).total ?? "—" },
  ]);
  // port detail
  const ports = [...(cov.inputs || []), ...(cov.outputs || [])];
  if (ports.length) {
    h += table([{ label: "Port" }, { label: "Dir" }, { label: "Class" }, { label: "Status" }, { label: "Evidence" }],
      ports.map(p => ({ key: p.name, cells: [
        { html: `<span class="mono">${esc(p.name)}</span>` }, p.direction, p.class,
        { html: statusBadge("trust", p.status) }, { html: `<span class="msg">${esc(p.evidence)}</span>` },
      ] })));
  }
  // bus visualization
  const buses = ports.filter(p => p.name.includes("["));
  if (buses.length) {
    h += sectionTitle("Bus coverage", "bit-level ranges");
    h += buses.map(b => {
      const m = b.name.match(/\[(\d+):(\d+)\]/);
      if (!m) return "";
      const msb = +m[1], lsb = +m[2];
      const statusMap = { constrained: "c", partial: "p", unconstrained: "u", unknown: "x", exempt: "x", not_applicable: "x" };
      const range = b.line ? [{ lo: lsb, hi: msb, status: statusMap[b.status] || "u" }] : [];
      return busStripHtml(b.name, msb, lsb, range);
    }).join("");
    h += `<div class="bus-legend"><span class="bus-bit c" style="width:10px;height:10px;display:inline-block"></span> constrained <span class="bus-bit u" style="width:10px;height:10px;display:inline-block"></span> missing <span class="bus-bit p" style="width:10px;height:10px;display:inline-block"></span> partial</div>`;
  }
  return h;
}

function renderInteractions(a) {
  const int = a.interactions || {};
  const sum = int.summary || {};
  const findings = int.findings || [];
  if (!findings.length && !sum.constraints_analyzed) return "";
  let h = sectionTitle("Constraint interactions", "do the constraints tell a coherent story?");
  h += metricRow([
    { label: "Analyzed", value: sum.constraints_analyzed ?? 0 }, { label: "Duplicates", value: sum.exact_duplicates ?? 0 },
    { label: "Overrides", value: sum.overrides ?? 0 }, { label: "Conflicts", value: sum.definite_conflicts ?? 0 },
    { label: "Need STA", value: sum.possible_conflicts ?? 0 },
  ]);
  findings.slice(0, 30).forEach(f => {
    const kind = f.category || "";
    const kindColor = f.severity === "error" ? "var(--error)" : f.severity === "warning" ? "var(--warning)" : "var(--accent-2)";
    h += `<div class="ilink" data-rule="${esc(f.code)}"><span class="il-rule">${esc(f.code)}</span><span class="il-kind" style="color:${kindColor}">${esc(kind)}</span><span class="il-a">${esc(f.msg)}</span>${f.line ? `<span class="il-loc">L${f.line}${f.line2 ? " ↔ L" + f.line2 : ""}</span>` : ""}</div>`;
  });
  return h;
}

function renderReadiness(a) {
  const rdy = a.readiness || {};
  if (!rdy.overall) return "";
  let h = sectionTitle("Constraint readiness", "ready for engineering handoff?");
  h += `<div class="rdy-overall"><div><div class="ro-label">Overall</div><div class="ro-value">${statusBadge("readiness", rdy.overall)}</div></div><div style="margin-left:auto" class="mono" style="font-size:12px;color:var(--text-muted)">mode: ${esc((rdy.mode || "SDC_ONLY").replace(/_/g, " "))}</div></div>`;
  h += readinessRail(rdy);
  if (rdy.limited_design_verification) h += `<p class="callout co-info"><span><strong>Limited design verification</strong> — SDC-only mode: object references were not verified against a netlist. This alone does not block readiness.</span></p>`;
  (rdy.blockers || []).slice(0, 10).forEach(b => {
    h += `<div class="ilink"><span class="il-rule">${esc(b.code)}</span><span class="il-kind" style="color:var(--error)">BLOCKER</span><span class="il-a">${esc(b.msg)}</span>${b.line ? `<span class="il-loc">L${b.line}${b.line2 ? " ↔ L" + b.line2 : ""}</span>` : ""}</div>`;
  });
  (rdy.review_items || []).slice(0, 10).forEach(r => {
    h += `<div class="ilink"><span class="il-rule">${esc(r.code)}</span><span class="il-kind" style="color:var(--warning)">REVIEW</span><span class="il-a">${esc(r.msg)}</span>${r.line ? `<span class="il-loc">L${r.line}${r.line2 ? " ↔ L" + r.line2 : ""}</span>` : ""}</div>`;
  });
  if ((rdy.actions || []).length) {
    h += sectionTitle("Recommended actions");
    h += rdy.actions.slice(0, 10).map(act =>
      `<div class="ilink"><span class="il-rule">${esc(act.priority || "P3")}</span><span class="il-kind" style="color:var(--accent-2)">${esc(act.category || "")}</span><span class="il-a">×${esc(act.count ?? 1)} — ${esc((act.evidence || []).slice(0, 3).join(", "))}</span></div>`
    ).join("");
  }
  h += `<p class="callout co-warning"><span><strong>READY ≠ STA signoff</strong> — this is a constraint-readiness review, not a timing signoff.</span></p>`;
  return h;
}

function renderBaseline(a) {
  const bl = a.baseline;
  if (!bl) return "";
  let h = sectionTitle("Readiness diff vs baseline");
  if (bl.error) { h += typedError("incompatible", bl.error); return h; }
  const r = bl.readiness || {};
  h += `<div class="diff-head"><span class="dh-side">Baseline <b>${esc(r.baseline || "?")}</b></span><span class="dh-arrow">→</span><span class="dh-side">Current <b>${esc(r.current || "?")}</b></span><span class="dh-side mono" style="color:var(--accent)">${esc(bl.classification || "")}</span></div>`;
  const f = bl.findings || {};
  h += metricRow([
    { label: "New", value: (f.new || []).length }, { label: "Resolved", value: (f.resolved || []).length },
    { label: "Changed", value: (f.changed || []).length }, { label: "Unchanged", value: (f.unchanged || []).length },
  ]);
  if (bl.gate) {
    const g = bl.gate;
    h += `<div class="ilink"><span class="il-rule">GATE</span><span class="il-kind" style="color:${g.result === "PASS" ? "var(--success)" : "var(--error)"}">${esc(g.result)}</span><span class="il-a">exit ${esc(g.exit_code)}</span><span class="il-loc mono">${esc((g.reasons || []).slice(0, 2).join(" · "))}</span></div>`;
  }
  const covd = bl.coverage || {};
  ["inputs", "outputs"].forEach(side => {
    const newly = (covd[side] || {}).newly_unconstrained || [];
    if (newly.length) h += `<div class="ilink"><span class="il-rule">Δ</span><span class="il-kind" style="color:var(--warning)">${esc(side)} newly unconstrained</span><span class="il-a mono">${esc(newly.slice(0, 8).join(", "))}</span></div>`;
  });
  (bl.trust || {}).regressions || [];
  const tr = bl.trust || {};
  (tr.regressions || []).slice(0, 4).forEach(t => {
    h += `<div class="ilink"><span class="il-rule">TRUST</span><span class="il-kind" style="color:var(--warning)">regression</span><span class="il-a mono">${esc(t.command || "")} ${esc(t.from || "")}→${esc(t.to || "")}</span></div>`;
  });
  h += `<p class="callout co-info"><span><strong>CI PASS ≠ timing pass</strong> — the gate only checks for disallowed constraint-readiness regressions.</span></p>`;
  return h;
}

function renderCustomRules(a) {
  const cr = a.custom_rules;
  if (cr === null) {
    if (a.custom_rule_err) return sectionTitle("Custom rules") + typedError("invalid", `Custom rules not loaded: ${a.custom_rule_err}`);
    return "";
  }
  if (!cr || !cr.length) return "";
  let h = sectionTitle(`Custom rules (${cr.length})`);
  const passed = cr.filter(r => r.passed).length;
  h += `<div class="mono" style="font-size:12px;color:var(--text-secondary);margin-bottom:6px">${passed} passed, ${cr.length - passed} failed</div>`;
  cr.forEach(r => h += `<div class="ilink"><span class="il-rule">${esc(r.id)}</span><span class="il-kind" style="color:${r.passed ? "var(--success)" : "var(--error)"}">${r.passed ? "PASS" : "FAIL"}</span><span class="il-a">${esc(r.msg)}</span></div>`);
  return h;
}

/* ── Clocks ─────────────────────────────────────────────────────────────── */
export async function pageClocks() {
  const a = App.state.analysis;
  const cr = (a && a.clock_relations) || {};
  const clocks = cr.clocks || [];
  const pairs = cr.pairs || [];
  const mismatches = cr.mismatches || [];

  let html = pageHead("RESULTS", "Clocks", "Are your clock definitions complete and consistent?",
                      "Select a clock to inspect it; open the matrix for relationships.");
  if (!a) {
    html += emptyState("No clocks yet", "Run a validation first — the clock analysis reads the same SDC evidence.", "Open New Analysis and press Analyze.");
    return html + "</div>";
  }

  html += metricRow([
    { label: "Clocks", value: clocks.length }, { label: "Synchronous pairs", value: cr.stats.synchronous ?? 0 },
    { label: "Asynchronous", value: cr.stats.asynchronous ?? 0 }, { label: "Exclusive", value: (cr.stats.physically_exclusive ?? 0) + (cr.stats.logically_exclusive ?? 0) },
    { label: "Mismatches", value: cr.stats.mismatches ?? 0 }, { label: "Missing groups", value: cr.stats.missing ?? 0 },
  ]);
  html += `<div style="margin:8px 0"><button class="btn btn-sm" type="button" data-exp="clocks">Download relations JSON</button></div>`;

  if (mismatches.length) {
    html += sectionTitle("Relation mismatches");
    mismatches.slice(0, 12).forEach(m => {
      html += `<div class="ilink"><span class="il-rule">${esc(m.code)}</span><span class="il-kind" style="color:${m.severity === "warning" ? "var(--warning)" : "var(--accent-2)"}">${esc(m.severity)}</span><span class="il-a">${esc(m.msg)}</span></div>`;
    });
  }

  html += sectionTitle("Clock inventory", "select a clock to inspect");
  html += table(
    [{ label: "Clock" }, { label: "Type" }, { label: "Period" }, { label: "Frequency" }, { label: "Source" }, { label: "Master" }, { label: "Divide" }, { label: "Status" }],
    clocks.map(c => ({ key: c.name, cells: [
      { html: `<span class="mono">${esc(c.name)}</span>` },
      c.is_generated ? "generated" : (c.is_virtual ? "virtual" : "primary"),
      { html: `<span class="num">${Number(c.period).toFixed(2)} ns</span>` },
      { html: `<span class="num">${(1000 / c.period).toFixed(2)} MHz</span>` },
      { html: `<span class="mono">${esc(c.source_port || c.source_node || "—")}</span>` },
      { html: `<span class="mono">${esc(c.master_clock || "—")}</span>` },
      c.divide_by && c.divide_by !== 1 ? `÷${c.divide_by}` : c.multiply_by ? `×${c.multiply_by}` : "—",
      { html: statusBadge("trust", "VALIDATED") },
    ] })),
    { clickable: true }
  );

  html += sectionTitle("Clock hierarchy", "primary → generated branches (explanatory, not timing simulation)");
  html += clockTreeHtml(clocks);

  html += sectionTitle("Relationship matrix");
  html += matrixHtml(clocks, pairs);

  return html + "</div>";
}

/* ── Design Context ─────────────────────────────────────────────────────── */
export async function pageContext() {
  const a = App.state.analysis;
  let html = pageHead("RESULTS", "Design", "The netlist objects behind your constraints — ports, pins, cells, nets.",
                      "Add a Verilog netlist in New Analysis to unlock object resolution.");
  if (!a) {
    html += emptyState("No design context", "Add a Verilog/netlist to enable design-object resolution.", "Open New Analysis, paste a netlist, and re-run the analysis.");
    return html + "</div>";
  }
  const ctx = a.context;
  if (!ctx) {
    html += typedError("insufficient", a.nl_error || "No netlist was supplied for this run — the analysis ran in SDC-only mode.");
    html += emptyState("Netlist not supplied", "Design-object resolution and coverage require a Verilog netlist.", "Add the netlist in the Validate input surface and re-analyze.");
    return html + "</div>";
  }
  html += metricRow([
    { label: "Top module", value: ctx.top_module || "—" }, { label: "Modules", value: ctx.modules ? ctx.modules.length : 0 },
    { label: "Ports", value: ctx.ports ? Object.keys(ctx.ports).length : 0 },
    { label: "Instances", value: ctx.instances ? Object.keys(ctx.instances).length : 0 },
    { label: "Nets", value: ctx.nets ? Object.keys(ctx.nets).length : 0 },
    { label: "Pins", value: ctx.pins ? ctx.pins.length : 0 },
  ]);
  html += `<div style="margin:8px 0"><button class="btn btn-sm" type="button" data-exp="context">Download design JSON</button></div>`;
  if (ctx.modules && ctx.modules.length) {
    html += sectionTitle("Hierarchy", "from the parsed netlist");
    html += `<div class="src" style="padding:10px 0">`;
    html += `<div class="src-line"><span class="src-no"></span><span class="src-text">${esc(ctx.top_module || "top")}</span></div>`;
    (ctx.modules || []).slice(0, 40).forEach(m => {
      if (m === ctx.top_module) return;
      html += `<div class="src-line"><span class="src-no"></span><span class="src-text">├── ${esc(m)}</span></div>`;
    });
    html += `</div>`;
  }
  html += `<p class="callout co-info"><span><strong>Structural inventory only</strong> — this is not a schematic and implies no timing propagation.</span></p>`;
  return html + "</div>";
}

/* ── Coverage ───────────────────────────────────────────────────────────── */
export async function pageCoverage() {
  const a = App.state.analysis;
  let html = pageHead("RESULTS", "Coverage", "Did you constrain every port the design needs?",
                      "A fully constrained design is not a correct design — review the evidence.");
  if (!a || !a.coverage || !a.coverage.summary) {
    html += emptyState("Design-aware coverage requires design context", "Coverage analysis runs when a Verilog netlist is supplied with the SDC.", "Open New Analysis, add the netlist, and re-analyze.");
    return html + "</div>";
  }
  const cov = a.coverage;
  const sum = cov.summary;
  html += `<p class="callout co-info"><span><strong>Coverage is NOT correctness</strong> — a fully constrained object does not prove correct timing intent.</span></p>`;
  html += metricRow([
    { label: "Inputs", value: sum.inputs ? `${sum.inputs.constrained}/${sum.inputs.total}` : "—" },
    { label: "Partial", value: (sum.inputs || {}).partial ?? 0 },
    { label: "Unconstrained", value: ((sum.inputs || {}).unconstrained ?? 0) + ((sum.outputs || {}).unconstrained ?? 0) },
    { label: "Exempt", value: ((sum.inputs || {}).exempt ?? 0) + ((sum.outputs || {}).exempt ?? 0) },
    { label: "Clocks defined", value: (sum.clocks || {}).defined ?? "—" },
    { label: "Exceptions", value: (sum.exceptions || {}).total ?? "—" },
  ]);
  html += `<div style="margin:8px 0"><button class="btn btn-sm" type="button" data-exp="coverage">Download coverage JSON</button></div>`;
  const ports = [...(cov.inputs || []), ...(cov.outputs || [])];
  html += sectionTitle("Port detail", `${ports.length} ports`);
  html += table([{ label: "Port" }, { label: "Dir" }, { label: "Class" }, { label: "Status" }, { label: "Evidence" }],
    ports.map(p => ({ key: p.name, cells: [
      { html: `<span class="mono">${esc(p.name)}</span>` }, p.direction, p.class,
      { html: statusBadge("trust", p.status) }, { html: `<span class="msg">${esc(p.evidence)}</span>` },
    ] })));
  const buses = ports.filter(p => /\[\d+:\d+\]/.test(p.name));
  if (buses.length) {
    html += sectionTitle("Bus coverage", "bit-level ranges");
    buses.forEach(b => {
      const m = b.name.match(/\[(\d+):(\d+)\]/);
      if (!m) return;
      const statusMap = { constrained: "c", partial: "p", unconstrained: "u", unknown: "x", exempt: "x", not_applicable: "x" };
      html += busStripHtml(b.name, +m[1], +m[2], [{ lo: +m[2], hi: +m[1], status: statusMap[b.status] || "u" }]);
    });
  }
  (cov.notes || []).forEach(n => html += `<div class="mono" style="font-size:11.5px;color:var(--text-muted);margin-top:3px">— ${esc(n)}</div>`);
  return html + "</div>";
}

/* ── Interactions ───────────────────────────────────────────────────────── */
export async function pageInteractions() {
  const a = App.state.analysis;
  let html = pageHead("RESULTS", "Conflicts", "Do any constraints duplicate, override, or contradict each other?",
                      "SDC-070 overlaps need STA review — they cannot be proven structurally.");
  if (!a) {
    html += emptyState("No interactions yet", "Run a validation first.", "Open New Analysis and press Analyze.");
    return html + "</div>";
  }
  const int = a.interactions || {};
  const findings = int.findings || [];
  const sum = int.summary || {};
  html += metricRow([
    { label: "Analyzed", value: sum.constraints_analyzed ?? 0 }, { label: "Duplicates", value: sum.exact_duplicates ?? 0 },
    { label: "Overrides", value: sum.overrides ?? 0 }, { label: "Conflicts", value: sum.definite_conflicts ?? 0 },
    { label: "Need STA", value: sum.possible_conflicts ?? 0 },
  ]);
  html += `<div style="margin:8px 0"><button class="btn btn-sm" type="button" data-exp="interactions">Download interactions JSON</button></div>`;
  html += `<p class="callout co-info"><span><strong>Interactions are a separate dimension from correctness</strong> — a duplicate is redundant, an override silently replaces an earlier value, SDC-069 is a provable conflict, SDC-070 needs STA/path analysis.</span></p>`;
  if (!findings.length) {
    html += emptyState("No interactions found", "No duplicate, override, contradiction or overlap findings in this constraint set.");
  } else {
    findings.forEach(f => {
      const kindColor = f.severity === "error" ? "var(--error)" : f.severity === "warning" ? "var(--warning)" : "var(--accent-2)";
      const cmd = f.command || "";
      html += `<div class="ilink"><span class="il-rule">${esc(f.code)}</span><span class="il-kind" style="color:${kindColor}">${esc(f.category || "")}</span><span class="il-a">${esc(f.msg)}</span>${f.line ? `<span class="il-loc">L${f.line}${f.line2 ? " ↔ L" + f.line2 : ""}</span>` : ""}</div>`;
      if (f.code === "SDC-070" || ((f.identity || {}).interaction_type || "").includes("sta")) {
        html += `<p class="callout co-warning" style="margin:2px 0 8px 16px"><span><strong>REQUIRES STA / PATH ANALYSIS</strong> — cannot be proven by structural analysis alone.</span></p>`;
      }
    });
  }
  return html + "</div>";
}

/* ── Readiness ──────────────────────────────────────────────────────────── */
export async function pageReadiness() {
  const a = App.state.analysis;
  let html = pageHead("RESULTS", "Health", "Is this constraint set ready to hand to STA?",
                      "Resolve blockers first, then review items — READY is not an STA signoff.");
  if (!a || !a.readiness || !a.readiness.overall) {
    html += emptyState("No readiness yet", "Run a validation first — readiness aggregates checker, scope, coverage and interactions evidence.", "Open New Analysis and press Analyze.");
    return html + "</div>";
  }
  const rdy = a.readiness;
  html += `<div class="rdy-overall"><div><div class="ro-label">Overall readiness</div><div class="ro-value">${statusBadge("readiness", rdy.overall)}</div></div><div style="margin-left:auto" class="mono" style="font-size:12px;color:var(--text-muted)">mode: ${esc((rdy.mode || "SDC_ONLY").replace(/_/g, " "))} · not_timing_signoff: true</div></div>`;
  html += readinessRail(rdy);
  html += `<div style="margin:8px 0"><button class="btn btn-sm" type="button" data-exp="readiness">Download readiness JSON</button></div>`;
  if (rdy.limited_design_verification) html += `<p class="callout co-info"><span><strong>Limited design verification</strong> — SDC-only mode.</span></p>`;
  if (rdy.engine_failed) html += typedError("engine", "One or more analysis engines failed — readiness is incomplete.");
  if (rdy.blockers && rdy.blockers.length) {
    html += sectionTitle(`Blockers (${rdy.blockers.length})`);
    rdy.blockers.forEach(b => html += `<div class="ilink"><span class="il-rule">${esc(b.code)}</span><span class="il-kind" style="color:var(--error)">${esc(b.tier || "BLOCKED")}</span><span class="il-a">${esc(b.msg)}</span>${b.line ? `<span class="il-loc">L${b.line}${b.line2 ? " ↔ L" + b.line2 : ""}</span>` : ""}</div>`);
  }
  if (rdy.review_items && rdy.review_items.length) {
    html += sectionTitle(`Review items (${rdy.review_items.length})`);
    rdy.review_items.forEach(r => html += `<div class="ilink"><span class="il-rule">${esc(r.code)}</span><span class="il-kind" style="color:var(--warning)">${esc(r.tier || "REVIEW")}</span><span class="il-a">${esc(r.msg)}</span>${r.line ? `<span class="il-loc">L${r.line}</span>` : ""}</div>`);
  }
  if (rdy.advisories && rdy.advisories.length) {
    html += sectionTitle(`Advisories (${rdy.advisories.length})`);
    rdy.advisories.forEach(ad => html += `<div class="ilink"><span class="il-rule">${esc(ad.code || "ADV")}</span><span class="il-kind" style="color:var(--accent-2)">ADVISORY</span><span class="il-a">${esc(ad.msg)}</span></div>`);
  }
  if (rdy.actions && rdy.actions.length) {
    html += sectionTitle("Recommended actions", "deterministic backend recommendations");
    html += table([{ label: "Priority" }, { label: "Category" }, { label: "Count" }, { label: "Evidence" }],
      rdy.actions.map((act, i) => ({ key: `act-${i}`, cells: [
        { html: `<span class="mono">${esc(act.priority || "P3")}</span>` },
        esc(act.category || ""), esc(act.count ?? 1),
        { html: `<span class="msg mono">${esc((act.evidence || []).slice(0, 3).join(", "))}</span>` },
      ] })));
  }
  (rdy.notes || []).forEach(n => html += `<div class="mono" style="font-size:11.5px;color:var(--text-muted)">— ${esc(n)}</div>`);
  html += `<p class="callout co-warning"><span><strong>READY ≠ STA signoff</strong> — READY means the constraint set satisfies the validator's supported, evidence-backed criteria for the stated mode. It does not mean setup/hold timing passes.</span></p>`;
  return html + "</div>";
}

/* ── Diff ───────────────────────────────────────────────────────────────── */
export async function pageDiff() {
  let html = pageHead("RESULTS", "Changes", "What changed between your baseline and this version?",
                      "Paste V1 and V2, then Compare — findings match by identity, not line number.");
  html += `<div class="input-surface">
    <div class="input-surface-head"><span class="is-title">V1 · Baseline SDC</span></div>
    <textarea class="code-input" id="diff-v1" spellcheck="false" placeholder="set sdc_version 2.2&#10;create_clock -name clk -period 5.0 [get_ports clk]&#10;">${esc(App.state.diffV1 || "")}</textarea>
    <div class="input-surface-head" style="border-top:1px solid var(--border-subtle)"><span class="is-title">V2 · Current SDC</span></div>
    <textarea class="code-input" id="diff-v2" spellcheck="false" placeholder="set sdc_version 2.2&#10;create_clock -name clk -period 6.0 [get_ports clk]&#10;">${esc(App.state.diffV2 || "")}</textarea>
    <div style="padding:10px 14px;display:flex;gap:10px;align-items:center;border-top:1px solid var(--border-subtle)">
      <button class="btn btn-primary" id="diff-run" type="button">Compare</button>
      <span class="mono" style="font-size:11px;color:var(--text-muted)">readiness diff · structured finding identity</span>
    </div>
  </div>`;
  if (!App.state.diffResult) {
    html += emptyState("No comparison yet", "Enter a baseline (V1) and current (V2) SDC, then press Compare.", "The diff uses structured finding identity — never line-number matching.");
    return html + "</div>";
  }
  const d = App.state.diffResult;
  const r = d.readiness || {};
  html += `<div class="diff-head"><span class="dh-side">Baseline <b>${esc(r.baseline || "?")}</b></span><span class="dh-arrow">→</span><span class="dh-side">Current <b>${esc(r.current || "?")}</b></span><span class="dh-side mono" style="color:var(--accent)">${esc(d.classification || "")}</span><span class="dh-side mono" style="color:var(--text-muted)">Δ ${esc(r.overall_delta || "")}</span></div>`;
  html += `<div style="margin:8px 0"><button class="btn btn-sm" type="button" data-exp="diff">Download diff JSON</button></div>`;
  if (d.gate) {
    const g = d.gate;
    html += `<div class="ilink"><span class="il-rule">GATE</span><span class="il-kind" style="color:${g.result === "PASS" ? "var(--success)" : "var(--error)"}">${esc(g.result)}</span><span class="il-a mono">exit ${esc(g.exit_code)}</span><span class="il-loc mono">${esc((g.reasons || []).slice(0, 2).join(" · "))}</span></div>`;
  }
  const f = d.findings || {};
  const cats = [["new", "NEW", "var(--success)"], ["resolved", "RESOLVED", "var(--info)"], ["changed", "CHANGED", "var(--warning)"], ["unchanged", "UNCHANGED", "var(--text-muted)"]];
  html += `<div class="filters"><div class="f-field"><label>Filter</label><div class="seg" id="diff-seg">${cats.map(([k, l]) => `<button type="button" data-seg="${k}" class="${k === App.state.diffFilter ? "active" : ""}">${l} (${(f[k] || []).length})</button>`).join("")}</div></div></div>`;
  const shown = (f[App.state.diffFilter] || []);
  if (!shown.length) {
    html += emptyState(`No ${App.state.diffFilter} findings`, `No findings classified as ${App.state.diffFilter} in this comparison.`);
  } else {
    shown.slice(0, 60).forEach(x => {
      html += `<div class="ilink"><span class="il-rule">${esc(x.code || "")}</span><span class="il-kind" style="color:${cats.find(c => c[0] === App.state.diffFilter)[1] === "UNCHANGED" ? "var(--text-muted)" : "var(--accent-2)"}">${esc(App.state.diffFilter.toUpperCase())}</span><span class="il-a">${esc(x.msg || "")}</span>${x.line ? `<span class="il-loc mono">L${x.line}</span>` : ""}</div>`;
      if (x.before !== undefined && x.after !== undefined) {
        html += `<div class="diff-row"><span class="mono" style="color:var(--text-muted)">BEFORE</span><span class="dr-before">${esc(x.before)}</span><span></span></div><div class="diff-row"><span class="mono" style="color:var(--text-muted)">AFTER</span><span></span><span class="dr-after">${esc(x.after)}</span></div>`;
      }
    });
  }
  const dbt = d.debt || {};
  html += sectionTitle("Debt");
  html += metricRow([
    { label: "Existing", value: `${(dbt.existing || {}).blockers ?? 0}B / ${(dbt.existing || {}).review ?? 0}R` },
    { label: "New debt", value: `${(dbt.new_debt || {}).blockers ?? 0}B / ${(dbt.new_debt || {}).review ?? 0}R` },
    { label: "Resolved", value: `${(dbt.resolved_debt || {}).blockers ?? 0}B / ${(dbt.resolved_debt || {}).review ?? 0}R` },
  ]);
  html += `<p class="callout co-info"><span><strong>CI PASS ≠ timing pass</strong> — the gate only checks for disallowed readiness regressions.</span></p>`;
  return html + "</div>";
}

/* ── Reports ────────────────────────────────────────────────────────────── */
export async function pageReports() {
  let html = pageHead("RESULTS", "Report", "Export the evidence — HTML report, JSON result, readiness snapshot.",
                      "Download the HTML report for sharing, or JSON for pipelines.");
  const a = App.state.analysis;
  if (!a) {
    html += emptyState("No analysis to report", "Run a validation first, then export the evidence.", "Open New Analysis and press Analyze.");
    return html + "</div>";
  }
  // Build snapshot client-side mirroring the backend build
  html += `<div class="ilink"><span class="il-rule">HTML</span><span class="il-kind" style="color:var(--accent-2)">REPORT</span><span class="il-a">Full checker report (errors/warnings/scope) as a standalone HTML file.</span><span class="il-loc"><button class="btn btn-sm" id="rep-html" type="button">Download</button></span></div>`;
  html += `<div class="ilink"><span class="il-rule">JSON</span><span class="il-kind" style="color:var(--accent-2)">RESULT</span><span class="il-a">Complete machine-readable analysis result.</span><span class="il-loc"><button class="btn btn-sm" id="rep-json" type="button">Download</button></span></div>`;
  html += `<div class="ilink"><span class="il-rule">READINESS</span><span class="il-kind" style="color:var(--accent-2)">SNAPSHOT</span><span class="il-a">Serialized readiness object — the CLI baseline format for CI.</span><span class="il-loc"><button class="btn btn-sm" type="button" data-exp="readiness">Download</button></span></div>`;
  html += `<p class="callout co-info"><span><strong>Readiness snapshot</strong> — served by the CLI (\`sdc-tools snapshot\`) for CI baselines; the Diff page compares snapshots.</span></p>`;
  return html + "</div>";
}

/* ── CI / Policies ──────────────────────────────────────────────────────── */
export async function pageCI() {
  let html = pageHead("TOOLS", "CI / Policies", "Deterministic gate policies for regression protection.");
  html += `<div class="filters"><div class="f-field"><label>Policy</label><select class="select-input" id="ci-policy">
    <option>BLOCKERS_ONLY</option><option>NO_READINESS_REGRESSION</option><option>STRICT</option>
  </select></div></div>`;
  html += `<div class="kv" style="margin:8px 0">`;
  html += `<dt>What it does</dt><dd>Evaluates the current run against a saved baseline snapshot and exits non-zero when disallowed readiness regressions occur.</dd>`;
  html += `<dt>Engine failure</dt><dd>Any analysis-engine failure fails the gate (exit 3) — never a silent PASS.</dd>`;
  html += `<dt>CLI</dt><dd><span class="mono">sdc-tools check design.sdc --baseline baseline.json --gate NO_READINESS_REGRESSION</span></dd>`;
  html += `</div>`;
  html += `<p class="callout co-info"><span><strong>CI PASS ≠ timing pass</strong> — the gate only protects against constraint-readiness regressions under the selected policy.</span></p>`;
  html += `<div class="panel"><div class="panel-head"><span class="panel-title">GitHub Actions example</span></div><pre class="mono" style="font-size:12px;color:var(--text-secondary);overflow-x:auto;margin:0">steps:
  - run: pip install sdc-tools
  - run: sdc-tools check design.sdc --baseline baseline.json --gate STRICT</pre></div>`;
  return html + "</div>";
}

/* ── Export ─────────────────────────────────────────────────────────────── */
export async function pageExport() {
  let html = pageHead("RESULTS", "Export", "Real exportable evidence — JSON, HTML report, readiness snapshot (CLI).");
  const a = App.state.analysis;
  if (!a) {
    html += emptyState("Nothing to export", "Run a validation first, then export the evidence.", "Open Validation and press Analyze.");
    return html + "</div>";
  }
  html += `<div class="ilink"><span class="il-rule">JSON</span><span class="il-kind" style="color:var(--accent-2)">RESULT</span><span class="il-a">Complete machine-readable analysis result (issues, scope, clocks, readiness).</span><span class="il-loc"><button class="btn btn-sm" id="exp-json" type="button">Download</button></span></div>`;
  html += `<div class="ilink"><span class="il-rule">HTML</span><span class="il-kind" style="color:var(--accent-2)">REPORT</span><span class="il-a">Standalone checker report — shareable, self-contained.</span><span class="il-loc"><button class="btn btn-sm" id="exp-html" type="button">Download</button></span></div>`;
  html += `<div class="ilink"><span class="il-rule">READINESS</span><span class="il-kind" style="color:var(--accent-2)">EVIDENCE</span><span class="il-a">Serialized readiness object for the current run (JSON, client-side from real evidence).</span><span class="il-loc"><button class="btn btn-sm" type="button" data-exp="readiness">Download</button></span></div>`;
  html += sectionTitle("CLI equivalents", "canonical snapshot & baseline flow");
  html += `<div class="kv" style="margin:8px 0">`;
  html += `<dt>Readiness snapshot</dt><dd><span class="mono">sdc-tools snapshot design.sdc --output baseline.json</span></dd>`;
  html += `<dt>Gated check</dt><dd><span class="mono">sdc-tools check design.sdc --baseline baseline.json --gate STRICT</span></dd>`;
  html += `<dt>HTML report</dt><dd><span class="mono">sdc-tools report check design.sdc -o quality_report.html</span></dd>`;
  html += `</div>`;
  html += `<p class="callout co-info"><span><strong>Snapshot semantics</strong> — the CLI snapshot is the CI baseline format; the Diff page compares snapshots.</span></p>`;
  return html + "</div>";
}

/* ── Trust ──────────────────────────────────────────────────────────────── */
export async function pageTrust() {
  const a = App.state.analysis;
  const scope = (a && a.scope) || {};
  let html = pageHead("TOOLS", "Trust Model", "What Ṛta validates, what it partially validates, and what it does not claim.");
  html += `<div class="chips">${statusBadge("trust", scope.status || "NOT_VALIDATED")}</div>`;
  if (scope.commands_found) {
    html += `<div class="mono" style="font-size:12px;color:var(--text-secondary);margin:4px 0 8px">current run: ${esc(scope.commands_found)} commands · ${esc(scope.fully_analyzed)} fully analyzed · ${esc(scope.partially_analyzed)} partial · ${esc((scope.netlist_required || 0) + (scope.tcl_execution_required || 0))} netlist/Tcl dependent · ${esc(scope.unsupported || 0)} unsupported</div>`;
  }
  html += sectionTitle("Boundary statements");
  [
    ["READY ≠ STA SIGNOFF", "READY means the constraint set satisfies the validator's supported, evidence-backed criteria for the stated mode — not that setup/hold timing passes."],
    ["COVERAGE ≠ CORRECTNESS", "A fully constrained object does not prove correct timing intent."],
    ["CI PASS ≠ TIMING CLOSURE", "A green gate only proves no disallowed readiness regression under the selected policy."],
    ["OBJECT RESOLUTION ≠ PATH EXISTENCE", "Resolving a get_ports/get_pins reference against a netlist does not prove the timing path exists or is valid."],
  ].forEach(([t, d]) => html += `<div class="ilink"><span class="il-rule">≠</span><span class="il-kind" style="color:var(--warning)">${esc(t)}</span><span class="il-a">${esc(d)}</span></div>`);
  html += sectionTitle("What Ṛta validates");
  [
    "SDC syntax and semantic validity for supported constructs",
    "Clock extraction, generated-clock ancestry and relation inference",
    "Constraint interactions: duplicates, overrides, provable conflicts",
    "Design-object resolution and constraint coverage (with a netlist)",
    "Readiness across seven dimensions with deterministic actions",
    "Baseline diffing and CI gates over structured finding identity",
  ].forEach(t => html += `<div class="ilink"><span class="il-rule">✓</span><span class="il-a">${esc(t)}</span></div>`);
  html += sectionTitle("What requires design context or STA");
  [
    "Object-reference verification and coverage → requires a Verilog netlist",
    "SDC-070 overlaps / possible conflicts → requires STA or path analysis",
    "Timing closure, setup/hold margins, skew and crosstalk → requires STA",
  ].forEach(t => html += `<div class="ilink"><span class="il-rule">△</span><span class="il-a">${esc(t)}</span></div>`);
  html += `<p class="callout co-info"><span><strong>Deterministic engine</strong> — no LLM, no model inference, no external AI APIs. Analysis is local, reproducible and offline-capable.</span></p>`;
  return html + "</div>";
}

/* ── Documentation ──────────────────────────────────────────────────────── */
export async function pageDocumentation() {
  let html = pageHead("TOOLS", "Documentation", "Repository documentation, CLI reference and evidence — real entries only.");
  const rules = App.state.rules;
  html += `<div class="kv" style="margin:8px 0">`;
  html += `<dt>Engine</dt><dd class="mono">deterministic · local-first · offline-capable</dd>`;
  html += `<dt>Rules</dt><dd class="mono">${rules ? rules.length + " deterministic rules across all engines" : "loaded on demand"}</dd>`;
  html += `<dt>CLI</dt><dd class="mono">sdc-tools check · generate · report · corners · snapshot · diff · web</dd>`;
  html += `</div>`;
  html += sectionTitle("Feature documentation", "docs/features/");
  [
    ["README-01-checker.md", "Validation rules, severity, CLI check"],
    ["README-02-generator.md", "SDC generation parameters"],
    ["README-03-diff.md", "Semantic diff and baseline snapshots"],
    ["README-04-clock-relations.md", "Clock relation inference"],
    ["README-05-mmc.md", "Corner manager and MMC generation"],
    ["README-06-coverage.md", "Constraint coverage semantics"],
    ["README-07-custom-rules.md", "YAML custom policy rules"],
    ["README-08-rules-registry.md", "Rule registry and codes"],
    ["README-09-reports.md", "Report formats (HTML / JSON / JUnit)"],
    ["README-10-web-ui.md", "Workspace architecture"],
  ].forEach(([f, d]) => html += `<div class="ilink"><span class="il-rule mono">${esc(f)}</span><span class="il-a">${esc(d)}</span></div>`);
  html += sectionTitle("Reference");
  html += `<div class="ilink"><span class="il-rule">ROOT</span><span class="il-a">README.md — product overview and quick start</span></div>`;
  html += `<div class="ilink"><span class="il-rule">GUIDE</span><span class="il-a">docs/rta/ — brand foundation, taxonomy, capability map, trust model</span></div>`;
  html += `<div class="ilink"><span class="il-rule">BENCH</span><span class="il-a">benchmarks/ — evidence suites and release manifests</span></div>`;
  return html + "</div>";
}

/* ── Tools ──────────────────────────────────────────────────────────────── */

/* Generator */
export async function pageGenerator() {
  let html = pageHead("TOOLS", "SDC Generator", "Generate a constraint file from parameters — real generate_sdc backend.",
                      "Generate, then validate the output directly in the workspace.");
  html += `<div class="input-surface"><div class="optional-panel" style="grid-template-columns:1fr 1fr">
    <div><label class="opt-label">Design name</label><input class="opt-input" id="gen-design" value="MY_DESIGN"></div>
    <div><label class="opt-label">Clock (name port period ns)</label><input class="opt-input" id="gen-clock" value="clk_core clk 5.0"></div>
    <div><label class="opt-label">Input delay max/min</label><input class="opt-input" id="gen-in" value="1.2 0.4"></div>
    <div><label class="opt-label">Output delay max/min</label><input class="opt-input" id="gen-out" value="1.5 0.5"></div>
  </div>
  <div style="padding:10px 14px;display:flex;gap:10px;align-items:center;border-top:1px solid var(--border-subtle)">
    <button class="btn btn-primary" id="gen-run" type="button">Generate</button></div></div>`;
  html += `<div id="gen-out-area"></div>`;
  return html + "</div>";
}

/* Linter */
export async function pageLinter() {
  let html = pageHead("TOOLS", "SDC Linter", "Format and normalize an SDC file — real lint_sdc backend.");
  html += `<div class="input-surface">
    <textarea class="code-input" id="lint-in" spellcheck="false" placeholder="create_clock -name clk -period 5.0 [get_ports clk]&#10;">${esc(App.state.lintIn || "")}</textarea>
    <div style="padding:10px 14px;display:flex;gap:10px;align-items:center;border-top:1px solid var(--border-subtle)">
      <button class="btn btn-primary" id="lint-run" type="button">Lint</button></div>
  </div>
  <div id="lint-out"></div>`;
  return html + "</div>";
}

/* Converter */
export async function pageConverter() {
  let html = pageHead("TOOLS", "SDC Converter", "Parse an SDC and export JSON or YAML — real converter backend.");
  html += `<div class="input-surface">
    <textarea class="code-input" id="conv-in" spellcheck="false" placeholder="create_clock -name clk -period 5.0 [get_ports clk]&#10;">${esc(App.state.convIn || "")}</textarea>
    <div style="padding:10px 14px;display:flex;gap:10px;align-items:center;border-top:1px solid var(--border-subtle)">
      <button class="btn btn-primary" id="conv-run" type="button" data-fmt="json">→ JSON</button>
      <button class="btn" id="conv-run-yaml" type="button" data-fmt="yaml">→ YAML</button>
      <button class="btn btn-sm" id="conv-dl" type="button" disabled>Download converted file</button></div>
  </div>
  <pre class="mono" id="conv-out" style="font-size:11.5px;color:var(--text-secondary);background:var(--bg-secondary);border:1px solid var(--border-subtle);border-radius:var(--radius-md);padding:12px;overflow-x:auto;white-space:pre-wrap"></pre>`;
  return html + "</div>";
}

/* Corner Manager */
export async function pageCorners() {
  let html = pageHead("TOOLS", "Corner Manager", "Define multi-corner signoff corners — real corner_manager backend.");
  html += `<div class="filters"><div class="f-field"><label>Preset</label><select class="select-input" id="corner-preset">
    <option value="CLASSIC_3">Classic 3-corner</option><option value="INDUSTRIAL_5">Industrial 5-corner</option>
    <option value="FULL_8">Full 8-corner signoff</option>
  </select></div><button class="btn btn-primary" id="corner-load" type="button">Load preset</button></div>`;
  html += `<div id="corner-out"></div>`;
  return html + "</div>";
}

/* MMC */
export async function pageMMC() {
  let html = pageHead("TOOLS", "MMC SDC", "Generate per-corner SDCs from a template — real mmc backend.");
  html += `<div class="input-surface">
    <div class="optional-panel" style="grid-template-columns:1fr 1fr">
      <div><label class="opt-label">Design name</label><input class="opt-input" id="mmc-design" value="MY_DESIGN"></div>
      <div><label class="opt-label">Clock (name port period)</label><input class="opt-input" id="mmc-clock" value="clk_core clk 5.0"></div>
    </div>
    <div style="padding:10px 14px;display:flex;gap:10px;align-items:center;border-top:1px solid var(--border-subtle)">
      <button class="btn btn-primary" id="mmc-run" type="button">Generate per-corner SDCs</button></div>
  </div>
  <div id="mmc-out"></div>`;
  return html + "</div>";
}

/* Rules */
export async function pageRules() {
  let html = pageHead("TOOLS", "Rules Registry", `${App.state.rules ? App.state.rules.length : "…"} deterministic rules across all engines.`);
  if (!App.state.rules) {
    try { App.state.rules = (await get("/api/rules")).rules || []; }
    catch (e) { App.state.rules = []; }
    html = pageHead("TOOLS", "Rules Registry", `${App.state.rules.length} deterministic rules across all engines.`);
  }
  const sev = App.state.ruleFilter || "All";
  const rules = sev === "All" ? App.state.rules : App.state.rules.filter(r => r.severity === sev);
  html += `<div class="filters"><div class="f-field"><label>Severity</label>${segFilter("rule-sev", ["All", "error", "warning", "info", "fatal"], sev)}</div>
    <div style="margin-left:auto;display:flex;gap:8px;align-items:center">
      <button class="btn btn-sm" id="rules-dl-json" type="button">Download JSON</button>
      <button class="btn btn-sm" id="rules-dl-md" type="button">Download Markdown</button>
    </div></div>`;
  rules.slice(0, 120).forEach(r => {
    html += `<div class="rule-row"><span class="rule-code">${esc(r.code)}</span> <span class="rule-name">${esc(r.short_name)}</span> ${statusBadge("severity", r.severity)}<div class="rule-desc">${esc(r.description)}</div>
      ${r.why_matters ? `<div class="rule-desc" style="color:var(--text-muted)">Why: ${esc(r.why_matters)}</div>` : ""}</div>`;
  });
  if (rules.length > 120) html += `<div class="mono" style="font-size:11px;color:var(--text-muted)">… ${rules.length - 120} more rules.</div>`;
  return html + "</div>";
}

/* Test Drive */
export async function pageTestDrive() {
  let html = pageHead("TOOLS", "Test Drive", "Run the checker against sample SDC files to see the analysis.");
  html += `<div class="filters"><div class="f-field"><label>Sample</label><select class="select-input" id="td-sample">
    <option value="good">Good SDC</option><option value="bad">Buggy SDC</option><option value="multi">Multi-clock</option>
    <option value="generated">Generated clocks</option>
  </select></div><button class="btn btn-primary" id="td-run" type="button">Analyze sample</button>
  <button class="btn btn-sm" id="td-dl" type="button">Download results JSON</button></div>
  <div id="td-out"></div>`;
  return html + "</div>";
}

/* Feedback */
export async function pageFeedback() {
  let html = pageHead("TOOLS", "Feedback", "Report a problem or suggest an improvement — stored locally in data/feedback.json.");
  html += `<div class="input-surface">
    <div class="optional-panel" style="grid-template-columns:1fr 1fr 1fr">
      <div><label class="opt-label">Feature</label><select class="opt-select" id="fb-feature">
        <option>validator</option><option>clocks</option><option>coverage</option><option>readiness</option>
        <option>diff</option><option>generator</option><option>linter</option><option>other</option></select></div>
      <div><label class="opt-label">Rating</label><select class="opt-select" id="fb-rating"><option value="1">👍 Helpful</option><option value="-1">👎 Not helpful</option><option value="0">Neutral</option></select></div>
    </div>
    <textarea class="code-input" id="fb-comment" style="min-height:90px" placeholder="What happened? What did you expect?"></textarea>
    <div style="padding:10px 14px;border-top:1px solid var(--border-subtle)"><button class="btn btn-primary" id="fb-submit" type="button">Submit feedback</button></div>
  </div>`;
  return html + "</div>";
}

/* ═══════════════════════════════════════════════════════════════════════════
   Page registry + event wiring
   ═══════════════════════════════════════════════════════════════════════════ */

// Sprint 3C2 — results-led navigation. Pages are phrased as the engineer's
// questions (Findings, Clocks, Coverage, Health, Changes, Conflicts) under a
// single RESULTS group; utilities live in a collapsed "More tools" disclosure.
// Pre-analysis there is NO navigation at all — the product is the input screen.
export const PAGES = {
  overview: { label: "Summary", render: pageOverview, group: "RESULTS" },
  validator: { label: "Findings", render: pageValidator, group: "RESULTS" },
  clocks: { label: "Clocks", render: pageClocks, group: "RESULTS" },
  coverage: { label: "Coverage", render: pageCoverage, group: "RESULTS" },
  context: { label: "Design", render: pageContext, group: "RESULTS" },
  interactions: { label: "Conflicts", render: pageInteractions, group: "RESULTS" },
  readiness: { label: "Health", render: pageReadiness, group: "RESULTS" },
  diff: { label: "Changes", render: pageDiff, group: "RESULTS" },
  reports: { label: "Report", render: pageReports, group: "RESULTS" },
  export: { label: "Export", render: pageExport, group: "RESULTS" },
  generator: { label: "Generator", render: pageGenerator, group: "TOOLS" },
  linter: { label: "Linter", render: pageLinter, group: "TOOLS" },
  converter: { label: "Converter", render: pageConverter, group: "TOOLS" },
  corners: { label: "Corner Manager", render: pageCorners, group: "TOOLS" },
  mmc: { label: "MMC", render: pageMMC, group: "TOOLS" },
  test_drive: { label: "Test Drive", render: pageTestDrive, group: "TOOLS" },
  rules: { label: "Rules", render: pageRules, group: "TOOLS" },
  ci: { label: "CI", render: pageCI, group: "TOOLS" },
  trust: { label: "Trust", render: pageTrust, group: "TOOLS" },
  documentation: { label: "Documentation", render: pageDocumentation, group: "TOOLS" },
  feedback: { label: "Feedback", render: pageFeedback, group: "TOOLS" },
  // Landing only — reached via the brand mark and Quick Actions, never a nav item.
  new_analysis: { label: "New Analysis", render: pageNewAnalysis, group: "HIDDEN" },
};

const GROUP_ORDER = ["RESULTS", "TOOLS"];

function navItemHtml(view, label, current) {
  const active = view === current ? " active" : "";
  return `<button class="nav-item${active}" data-view="${view}" role="tab" aria-selected="${view === current}">
    <span class="ni-icon">${iconFor(view)}</span><span>${label}</span>
  </button>`;
}

// Results-led navigation — appears only after an analysis exists. RESULTS holds
// the engineer's questions in order; utilities hide inside a collapsed
// "More tools" disclosure so they never compete for attention.
export function navGroupsHtml(current) {
  const has = !!App.state.analysis;
  if (!has) return ""; // no nav before analysis — the product is the input screen
  const byGroup = {};
  Object.entries(PAGES).forEach(([id, p]) => {
    if (p.group === "HIDDEN") return;
    (byGroup[p.group] = byGroup[p.group] || []).push([id, p.label]);
  });
  const results = (byGroup["RESULTS"] || []).map(([id, label]) => navItemHtml(id, label, current)).join("");
  const tools = (byGroup["TOOLS"] || []).map(([id, label]) => navItemHtml(id, label, current)).join("");
  return `<div class="nav-group"><span class="nav-group-label">RESULTS</span>${results}</div>
    <details class="nav-group nav-tools"><summary class="nav-group-label nav-tools-summary">More tools</summary>${tools}</details>`;
}

function iconFor(id) {
  const I = {
    overview: "◧", new_analysis: "＋", validator: "◈", clocks: "◉", context: "▤", coverage: "▦",
    interactions: "⇄", readiness: "◫", diff: "⇔", reports: "▤", export: "⇩",
    ci: "⚙", generator: "✎", linter: "≡", converter: "⇄", corners: "◇",
    mmc: "◈", rules: "☰", trust: "◆", documentation: "❐",
    test_drive: "▶", feedback: "◌", __recent: "◷", __settings: "⚙",
  };
  return I[id] || "·";
}

/* ── Export helpers for event wiring in app.js ─────────────────────────── */
export { findingObj, findingClk, findingLoc, locLines };
