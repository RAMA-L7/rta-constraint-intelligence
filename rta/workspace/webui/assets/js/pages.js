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
                 "Open the capability catalog and pick Validate, then Analyze.");
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

/* ═══════════════════════════════════════════════════════════════════════════
   FEATURE-FIRST ENTRY — capability catalog (Phase C)
   The first screen answers "what is Ṛta?" and "what can I do with Ṛta?" as
   feature cards. Every card answers: WHAT IS THIS / WHAT INPUT / WHAT ṚTA
   DOES / WHAT I GET / WHAT NEXT. Every card routes to a REAL workflow.
   ═══════════════════════════════════════════════════════════════════════════ */

const CATALOG = [
  { view: "new_analysis", title: "Validate", icon: "◈",
    what: "Run the deterministic rule engine over an SDC file and get every finding with a rule code and source line.",
    input: "SDC required · netlist optional",
    does: "Parses, resolves TCL variables, checks all rules, folds in clock relations, conflicts and readiness.",
    get: "Errors / warnings / advisories, stats, analysis scope — plus Clocks, Coverage, Conflicts and Health views.",
    next: "Inspect Clocks · Coverage · Health",
    route: "#/new_analysis", action: "Validate my SDC" },
  { view: "generator", title: "SDC Generator", icon: "✎",
    what: "Generate a complete synthesis-ready SDC from parameters — no SDC needed to start.",
    input: "Generation parameters (design, clocks, delays, options)",
    does: "Emits a 22-section canonical SDC from the real generate_sdc backend — self-consistent, passes its own linter.",
    get: "Generated SDC text — copy, download, or open straight in the Validator.",
    next: "Open in Validator · Lint · Download",
    route: "#/generator", action: "Generate an SDC" },
  { view: "linter", title: "SDC Linter", icon: "≡",
    what: "Check and normalize SDC formatting — trailing whitespace, tabs, over-long lines, canonical section order.",
    input: "SDC required",
    does: "Checks style issues and reorganizes commands into the canonical 22-section order.",
    get: "Issue list + formatted SDC — download the fixed file.",
    next: "Download formatted SDC",
    route: "#/linter", action: "Lint / format my SDC" },
  { view: "converter", title: "SDC Converter", icon: "⇄",
    what: "Parse an SDC into structured JSON or YAML for tooling and downstream automation.",
    input: "SDC required · target format (json/yaml)",
    does: "Extracts clocks, delays, exceptions, clock groups, derates and case analysis into a structured document.",
    get: "JSON or YAML output — download for your pipeline.",
    next: "Download converted file",
    route: "#/converter", action: "Convert SDC → JSON/YAML" },
  { view: "clocks", title: "Clock Intelligence", icon: "◉",
    what: "Inventory your clocks and their relationships — primary, generated, virtual — and find missing constraints.",
    input: "SDC required (from an analysis)",
    does: "Infers clock relations, classifies pairs, and splits mismatches from missing clock-group constraints.",
    get: "Clock inventory, N×N relation matrix, mismatches and missing constraints.",
    next: "Review missing constraints → add clock groups",
    route: "#/clocks", action: "Analyze clocks & relations" },
  { view: "coverage", title: "Coverage", icon: "▦",
    what: "Gap-analysis of your constraint set — which of the 39 constraint categories are present or missing.",
    input: "SDC required · netlist optional (design-aware)",
    does: "Scores 6 constraint categories; with a netlist adds port-level design coverage. Coverage is NOT correctness.",
    get: "Score, present/total, per-category breakdown, missing items.",
    next: "Fix missing categories",
    route: "#/coverage", action: "Check constraint coverage" },
  { view: "context", title: "Design Context", icon: "▤",
    what: "Verify your SDC against a real netlist — design-object resolution and structural checks (reset trees, ports).",
    input: "SDC + netlist (Verilog) + top module",
    does: "Parses netlist connectivity, resolves SDC object references, detects unconstrained reset trees and ports.",
    get: "Design context summary + netlist-backed findings (SDC-055..066, 151..155).",
    next: "Review reset trees / unconstrained ports",
    route: "#/context", action: "Verify against my netlist" },
  { view: "interactions", title: "Constraint Conflicts", icon: "⇄",
    what: "Find duplicate, overridden and contradictory constraints that silently change timing intent.",
    input: "SDC required (from an analysis)",
    does: "Detects exact duplicates, overrides, contradictions and overlapping exceptions with line pairs.",
    get: "Conflict findings with line pairs (:9 ↔ :8) and what/why/review guidance.",
    next: "Resolve or document conflicts",
    route: "#/interactions", action: "Find conflicts / interactions" },
  { view: "readiness", title: "Readiness", icon: "◫",
    what: "Is this constraint set ready to hand to STA review? A pre-STA review — never a timing signoff.",
    input: "SDC required · netlist optional · baseline optional",
    does: "Aggregates checker, scope, coverage, interactions and context into per-dimension readiness with WHY.",
    get: "BLOCKED / REVIEW_REQUIRED / READY tier + per-dimension reasons + actions.",
    next: "Clear REVIEW / BLOCKED items",
    route: "#/readiness", action: "Is my SDC ready for STA review?" },
  { view: "diff", title: "SDC Diff", icon: "⇔",
    what: "Compare two SDC versions and see exactly what changed and why it matters.",
    input: "V1 SDC + V2 SDC (+ optional linked TCL)",
    does: "Matches constraints by identity (not line number), classifies changes against 21 CHG-* rules.",
    get: "Added / removed / modified constraints with severity and impact text.",
    next: "Review fatal changes · export report",
    route: "#/diff", action: "Compare two SDCs" },
  { view: "corners", title: "Corner Manager", icon: "◇",
    what: "Define and validate multi-corner signoff corners (PVT) for your flow.",
    input: "Preset or custom corner JSON",
    does: "Loads the built-in presets (3/5/8-corner) or your own corners with full validation.",
    get: "Validated corner list — pick corners for MMC.",
    next: "Pick corners → MMC",
    route: "#/corners", action: "Manage PVT corners" },
  { view: "mmc", title: "MMC", icon: "◈",
    what: "Generate per-corner SDCs from a template with per-corner derates, operating conditions and uncertainty.",
    input: "Template or generation params + corners",
    does: "Clones the template per corner, applies corner-specific values, checks cross-corner consistency.",
    get: "Per-corner SDCs + ZIP + cross-corner consistency findings.",
    next: "Open a corner in Validator",
    route: "#/mmc", action: "Generate multi-corner SDCs" },
  { view: "test_drive", title: "Test Drive", icon: "▶",
    what: "See Ṛta on real samples — run the full analysis battery on a sample SDC in one click.",
    input: "Sample picker or your own SDC",
    does: "Runs checker, coverage, clocks, linter and converter through the real backend — no mock data.",
    get: "Unified results dashboard + JSON download.",
    next: "Open a full session on your own SDC",
    route: "#/test_drive", action: "Try Ṛta on a sample" },
  { view: "rules", title: "Rules", icon: "☰",
    what: "Browse the full deterministic rule catalog — what each rule checks, why it matters, and how to fix it.",
    input: "None to browse (SDC only for live execution)",
    does: "Serves the 119-rule registry with search, filter and detail for every code.",
    get: "Searchable, filterable rule reference.",
    next: "Find the rule behind a finding",
    route: "#/rules", action: "Browse the rule catalog" },
  { view: "ci", title: "CI", icon: "⚙",
    what: "Gate SDC changes on constraint quality — the same deterministic standard for every engineer.",
    input: "SDC + baseline snapshot + gate policy",
    does: "Evaluates gate tiers (BLOCKERS_ONLY … STRICT) against findings and readiness regression vs baseline.",
    get: "PASS/FAIL verdict with exit-code semantics and regression detail. CI PASS ≠ timing pass.",
    next: "Wire the gate into your pipeline",
    route: "#/ci", action: "Gate SDC changes in CI" },
  { view: "reports", title: "Reports", icon: "▤",
    what: "Generate self-contained HTML signoff reports from analysis, diff, clock or coverage results.",
    input: "Analysis results (per report type)",
    does: "Renders the reporter's HTML report types — no external assets, shareable files.",
    get: "Self-contained HTML report + JSON evidence.",
    next: "Open / share / archive the report",
    route: "#/reports", action: "Generate signoff reports" },
  { view: "trust", title: "Trust", icon: "◆",
    what: "Read exactly what Ṛta verifies, what it infers, and what still needs an engineer or STA.",
    input: "None",
    does: "States the standing trust disclosures — coverage ≠ correctness, readiness ≠ signoff, CI PASS ≠ timing pass.",
    get: "The honest boundaries of every output.",
    next: "Start validating your SDC",
    route: "#/trust", action: "Read our trust disclosures" },
];

export function catalogCardHtml(c) {
  return `<a class="cat-card" href="${c.route}" data-view="${c.view}" role="button">
    <div class="cat-card-top"><span class="cat-icon">${c.icon}</span><span class="cat-title">${esc(c.title)}</span><span class="cat-go">→</span></div>
    <p class="cat-what">${esc(c.what)}</p>
    <div class="cat-input mono">${esc(c.input)}</div>
    <div class="cat-rows">
      <div class="cat-row"><span class="cat-k">What Ṛta does</span><span class="cat-v">${esc(c.does)}</span></div>
      <div class="cat-row"><span class="cat-k">You get</span><span class="cat-v">${esc(c.get)}</span></div>
      <div class="cat-row"><span class="cat-k">Next</span><span class="cat-v">${esc(c.next)}</span></div>
    </div>
    <span class="cat-action">${esc(c.action)} →</span>
  </a>`;
}

const CATALOG_GROUPS = [
  { label: "Core", views: ["new_analysis", "generator", "linter", "converter"] },
  { label: "Analysis", views: ["clocks", "coverage", "context", "interactions", "readiness", "diff"] },
  { label: "Advanced", views: ["corners", "mmc", "test_drive", "rules", "ci", "reports", "trust"] },
];

/* Feature-first landing: positioning line + every primary capability card. */
export async function pageCatalog() {
  let html = `<div class="page">
    <p class="page-eyebrow">RTA · ENGINEERING WORKSPACE</p>
    <h1 class="page-title">What can I do with Ṛta?</h1>
    <p class="page-purpose">Ṛta is a deterministic constraint-intelligence workspace for block-level digital design — validate, generate, and review SDC before STA. Pick a capability; each one asks only for the input it needs.</p>
    <p class="page-next"><span class="pn-label">New here?</span> Start with <a href="#/test_drive" data-view="test_drive" class="cat-inline">Test Drive</a> to see Ṛta on a real sample, or <a href="#/new_analysis" data-view="new_analysis" class="cat-inline">Validate an SDC</a> directly.</p>`;
  CATALOG_GROUPS.forEach(g => {
    html += `<h2 class="section-title">${esc(g.label)} capabilities</h2><div class="cat-grid">`;
    g.views.forEach(v => { const c = CATALOG.find(x => x.view === v); if (c) html += catalogCardHtml(c); });
    html += `</div>`;
  });
  html += `<p class="callout co-info" style="margin-top:16px"><span><strong>Deterministic · offline · no LLM</strong> — every result comes from the frozen rule engine running locally; the same input always produces the same findings. Readiness is a constraint-quality review, <strong>not an STA timing signoff</strong>.</span></p>`;
  return html + "</div>";
}

/* ═══════════════════════════════════════════════════════════════════════════
   STANDALONE ANALYSIS INPUT (Phase C / Group 2)
   Each analysis capability is independently usable: its page carries its own
   SDC input panel (netlist optional where the backend supports it). Running it
   adopts the result into the session so the RESULTS views (Findings, Clocks,
   Coverage, …) stay in sync — but the user is never forced into a session.
   ═══════════════════════════════════════════════════════════════════════════ */

const ANALYSIS_INPUTS = {
  clocks: {
    what: "What Ṛta does", does: "Parses your clocks and infers every pair relationship — synchronous, asynchronous, physically/logically exclusive — then separates mismatches from missing clock-group constraints.",
    get: "You get", result: "Clock inventory, N×N relationship matrix, hierarchy, mismatches, missing constraints and advisories.",
    netlist: false, note: "Clocks need only the SDC — a netlist is not required for relation inference.",
    input: "SDC required", netlabel: "" },
  coverage: {
    what: "What Ṛta does", does: "Scores all 39 constraint categories (clocks, I/O, exceptions, design rules, derate, power/DFT); with a netlist it adds design-aware port coverage. Coverage is NOT correctness.",
    get: "You get", result: "Coverage score, present/total, per-category breakdown and every missing category.",
    netlist: true, note: "Netlist optional — SDC-only shows the 39-category gap analysis; adding a netlist unlocks design-aware port coverage.",
    input: "SDC required · netlist optional", netlabel: "Netlist (Verilog, optional)" },
  context: {
    what: "What Ṛta does", does: "Parses netlist connectivity (ports, modules, instances, nets) and resolves your SDC objects against it — reset trees, clock fanout, unconstrained ports. Structural inventory only.",
    get: "You get", result: "Design context summary (top, modules, ports, instances, nets) plus netlist-backed findings — only when a netlist is supplied.",
    netlist: true, note: "Netlist REQUIRED for design-object resolution — SDC-only mode cannot verify design objects (honest limitation).",
    input: "SDC + netlist required", netlabel: "Netlist (Verilog, required)" },
  interactions: {
    what: "What Ṛta does", does: "Finds constraints that duplicate, override, or contradict each other — SDC-067 duplicates, SDC-068 overrides, SDC-069 provable conflicts, SDC-070 overlaps that need STA review.",
    get: "You get", result: "Every conflict with its rule, the two source lines, why it matters and what to review.",
    netlist: false, note: "Conflicts are structural — the SDC alone is sufficient; a netlist does not change the analysis.",
    input: "SDC required", netlabel: "" },
  readiness: {
    what: "What Ṛta does", does: "Aggregates checker findings, scope, coverage, interactions and design context into per-dimension readiness with a tier and the WHY behind it. Pre-STA review, not a timing signoff.",
    get: "You get", result: "BLOCKED / REVIEW_REQUIRED / READY tier, per-dimension status, blockers, review items, advisories and recommended actions.",
    netlist: true, note: "Netlist optional — SDC-only readiness is valid; a netlist adds the design-context dimension.",
    input: "SDC required · netlist optional", netlabel: "Netlist (Verilog, optional)" },
};

export function analysisPanelHtml(cap) {
  const m = ANALYSIS_INPUTS[cap];
  const net = m.netlist
    ? `<div class="entry-step"><div class="es-num">2</div><div class="es-main">
        <div class="es-head"><span class="es-title">${esc(m.netlabel)}</span><span class="es-opt">OPTIONAL</span></div>
        <p class="es-why">${esc(m.note)}</p>
        <textarea class="opt-text" id="cap-netlist" rows="3" spellcheck="false" placeholder="module top ( input clk, ... );"></textarea>
      </div></div>`
    : `<div class="entry-step"><div class="es-num">2</div><div class="es-main">
        <div class="es-head"><span class="es-title">Input</span><span class="es-opt">NOT REQUIRED</span></div>
        <p class="es-why">${esc(m.note)}</p>
      </div></div>`;
  const state = App.state.analysis ? `
    <div class="entry-step" style="background:var(--bg-secondary)"><div class="es-num">✓</div><div class="es-main">
      <div class="es-head"><span class="es-title">Analysis loaded</span><span class="es-opt">${esc(App.state.filename || "pasted.sdc")}</span></div>
      <p class="es-why">The results below come from the last run. Paste new SDC and press Analyze to re-run, or Clear to start over.</p>
      <div class="es-actions"><button class="btn btn-sm btn-ghost" id="cap-clear" type="button">Clear</button></div>
    </div></div>` : "";
  return `<div class="input-surface entry">
    ${state}
    <div class="entry-step"><div class="es-num">1</div><div class="es-main">
      <div class="es-head"><span class="es-title">SDC constraint file</span><span class="es-req">REQUIRED</span></div>
      <p class="es-why">${esc(m.input)}. ${esc(m.does)}</p>
      <div class="es-actions">
        <button class="btn btn-sm" id="cap-sample" type="button">Load sample</button>
        <button class="btn btn-sm btn-ghost" id="cap-clear-sdc" type="button">Clear</button>
      </div>
      <textarea class="code-input" id="cap-sdc" rows="8" spellcheck="false" placeholder="set sdc_version 2.2&#10;create_clock -name clk_core -period 5.0 [get_ports clk]&#10;...">${esc(App.state.sdc || "")}</textarea>
    </div></div>
    ${net}
    <div class="entry-foot">
      <button class="btn btn-primary btn-lg" id="cap-analyze" type="button" data-cap="${cap}">Analyze ${esc(cap === "interactions" ? "conflicts" : cap === "readiness" ? "readiness" : cap)}</button>
      <span class="mono" style="font-size:11px;color:var(--text-muted)">runs locally · deterministic · offline · no LLM</span>
    </div>
  </div>`;
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

  let html = pageHead("CAPABILITY", "Clock Intelligence", "Are your clock definitions complete and consistent?",
                      "Next: Coverage · Conflicts · Readiness.");
  html += analysisPanelHtml("clocks");
  if (!a) {
    html += emptyState("No clocks yet", "Paste an SDC above and press Analyze — the clock analysis reads the same SDC evidence.", "You can also run Validate first and open Clocks from the results.");
    return html + "</div>";
  }

  html += `<div class="chips" style="margin-top:14px">`;
  html += `<a class="cat-inline" href="#/coverage" data-view="coverage">Review Coverage →</a>`;
  html += `&nbsp;·&nbsp;<a class="cat-inline" href="#/interactions" data-view="interactions">Review Conflicts →</a>`;
  html += `&nbsp;·&nbsp;<a class="cat-inline" href="#/readiness" data-view="readiness">Readiness →</a></div>`;

  html += metricRow([
    { label: "Clocks", value: clocks.length }, { label: "Synchronous pairs", value: cr.stats.synchronous ?? 0 },
    { label: "Asynchronous", value: cr.stats.asynchronous ?? 0 }, { label: "Exclusive", value: (cr.stats.physically_exclusive ?? 0) + (cr.stats.logically_exclusive ?? 0) },
    { label: "Mismatches", value: cr.stats.mismatches ?? 0 }, { label: "Missing groups", value: cr.stats.missing ?? 0 },
  ]);
  html += `<div style="margin:8px 0"><button class="btn btn-sm" type="button" data-exp="clocks">Download relations JSON</button></div>`;

  // P1-2/P1-7: mismatches, missing constraints and advisories are separate
  // categories — stats.mismatches == mismatches.length always.
  if (mismatches.length) {
    html += sectionTitle("Relation mismatches");
    mismatches.slice(0, 12).forEach(m => {
      html += `<div class="ilink"><span class="il-rule">${esc(m.code)}</span><span class="il-kind" style="color:var(--warning)">${esc(m.severity)}</span><span class="il-a">${esc(m.msg)}</span></div>`;
    });
  }
  const missingConstr = cr.missing_constraints || [];
  if (missingConstr.length) {
    html += sectionTitle("Missing constraints", "no set_clock_groups declared for these pairs");
    missingConstr.slice(0, 12).forEach(m => {
      html += `<div class="ilink"><span class="il-rule">${esc(m.code)}</span><span class="il-kind" style="color:var(--accent-2)">${esc(m.severity)}</span><span class="il-a">${esc(m.msg)}</span></div>`;
    });
  }
  const advisories = cr.advisories || [];
  if (advisories.length) {
    html += sectionTitle("Advisories", "verify these declared relationships");
    advisories.slice(0, 12).forEach(m => {
      html += `<div class="ilink"><span class="il-rule">${esc(m.code)}</span><span class="il-kind" style="color:var(--accent-2)">${esc(m.severity)}</span><span class="il-a">${esc(m.msg)}</span></div>`;
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
  let html = pageHead("CAPABILITY", "Design Context", "The netlist objects behind your constraints — ports, pins, cells, nets.",
                      "Next: Coverage (design-aware) · Validate · Conflicts.");
  html += analysisPanelHtml("context");
  if (!a) {
    html += emptyState("No design context", "Supply SDC + a Verilog netlist above and press Analyze — object resolution needs both.", "SDC-only mode cannot verify design objects (honest limitation — nothing is invented).");
    return html + "</div>";
  }
  const ctx = a.context;
  if (!ctx) {
    html += typedError("insufficient", a.nl_error || "No netlist was supplied for this run — the analysis ran in SDC-only mode.");
    html += emptyState("Netlist not supplied", "Design-object resolution and coverage require a Verilog netlist.", "Paste a netlist in the input above and re-run — or use Validate's input surface.");
    return html + "</div>";
  }
  html += `<div class="chips" style="margin-top:14px"><a class="cat-inline" href="#/coverage" data-view="coverage">Open Coverage (design-aware) →</a>&nbsp;·&nbsp;<a class="cat-inline" href="#/validator" data-view="validator">All findings →</a></div>`;
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
  let html = pageHead("CAPABILITY", "Coverage", "Did you constrain every port the design needs?",
                      "A fully constrained design is not a correct design — review the evidence.");
  html += analysisPanelHtml("coverage");
  if (!a) {
    html += emptyState("No coverage yet", "Paste an SDC above and press Analyze — coverage scores all 39 constraint categories.", "Add a netlist to also see design-aware port coverage.");
    return html + "</div>";
  }

  // P1-5: the SDC constraint category coverage (39-item gap analysis) is
  // computed ALWAYS — netlist or not — and is distinct from design-aware
  // port coverage. SDC-only coverage never implies design-object verification.
  const cat = a.category_coverage || {};
  if (cat.score_pct !== undefined && !cat.error) {
    html += `<p class="callout co-info"><span><strong>Coverage is NOT correctness</strong> — a fully covered SDC can still have timing errors.</span></p>`;
    html += sectionTitle("SDC constraint coverage", "which constraint categories are present or missing in the SDC");
    html += metricRow([
      { label: "Score", value: `${cat.score_pct}%` },
      { label: "Present", value: `${cat.total_present}/${cat.total_items}` },
      { label: "Missing", value: cat.total_missing },
    ]);
    (cat.categories || []).forEach(c => {
      const pct = Math.round(c.score);
      html += `<div class="ilink"><span class="il-rule">${esc(c.icon || "")}</span><span class="il-a"><b>${esc(c.name)}</b> — ${c.covered}/${c.total} covered (${pct}%)</span>` +
        `<span class="il-loc">${c.missing ? c.missing + " missing" : "complete"}</span></div>`;
      c.items.forEach(it => {
        if (!it.present) {
          html += `<div class="mono" style="font-size:11.5px;color:var(--text-muted);margin-left:26px">${it.critical ? "✗" : "·"} ${esc(it.name)}${it.detail ? " — " + esc(it.detail) : ""}</div>`;
        }
      });
    });
    html += `<div class="mono" style="font-size:11.5px;color:var(--text-muted);margin-top:6px">SDC constraint coverage checks constraint presence in the SDC file — it does NOT verify design objects. Supply a netlist for design-aware coverage.</div>`;
  }

  const cov = a.coverage || {};
  const sum = cov.summary || {};
  if (sum.inputs || sum.outputs || sum.clocks) {
    html += sectionTitle("Design-aware coverage (netlist)", "port-level constraint coverage against the supplied design");
    html += `<p class="callout co-info"><span><strong>Coverage is NOT correctness</strong> — a fully constrained object does not prove correct timing intent.</span></p>`;
    html += metricRow([
      { label: "Inputs", value: sum.inputs ? `${sum.inputs.constrained}/${sum.inputs.total}` : "—" },
      { label: "Partial", value: (sum.inputs || {}).partial ?? 0 },
      { label: "Unconstrained", value: ((sum.inputs || {}).unconstrained ?? 0) + ((sum.outputs || {}).unconstrained ?? 0) },
      { label: "Exempt", value: ((sum.inputs || {}).exempt ?? 0) + ((sum.outputs || {}).exempt ?? 0) },
      { label: "Clocks defined", value: (sum.clocks || {}).defined ?? "—" },
      { label: "Exceptions", value: (sum.exceptions || {}).total ?? "—" },
    ]);
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
  }
  html += `<div style="margin:8px 0"><button class="btn btn-sm" type="button" data-exp="coverage">Download coverage JSON</button></div>`;
  return html + "</div>";
}

/* ── Interactions ───────────────────────────────────────────────────────── */
export async function pageInteractions() {
  const a = App.state.analysis;
  let html = pageHead("CAPABILITY", "Constraint Conflicts", "Do any constraints duplicate, override, or contradict each other?",
                      "SDC-070 overlaps need STA review — they cannot be proven structurally.");
  html += analysisPanelHtml("interactions");
  if (!a) {
    html += emptyState("No interactions yet", "Paste an SDC above and press Analyze — conflicts are found structurally, no netlist needed.", "You can also run Validate first and open Conflicts from the results.");
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
  let html = pageHead("CAPABILITY", "Readiness", "Is this constraint set ready to hand to STA?",
                      "Resolve blockers first, then review items — READY is not an STA signoff.");
  html += analysisPanelHtml("readiness");
  if (!a || !a.readiness || !a.readiness.overall) {
    html += emptyState("No readiness yet", "Paste an SDC above and press Analyze — readiness aggregates checker, scope, coverage and interactions evidence.", "You can also run Validate first and open Health from the results.");
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
  let html = pageHead("CAPABILITY", "SDC Diff", "What changed between your baseline and this version?",
                      "Next: review changed constraints · Validate · Report.");
  html += `<div class="chips"><a class="cat-inline" href="#/validator" data-view="validator">Open V2 in Validate →</a>&nbsp;·&nbsp;<a class="cat-inline" href="#/reports" data-view="reports">Report →</a></div>`;
  html += `<div class="input-surface" style="margin-top:12px">
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
  // Phase C / Group 2 — semantic constraint changes (CHG-* engine, additive
  // to the readiness findings above): period changes, I/O delays, exceptions,
  // wildcard risk, additions/removals — with before/after + why it matters.
  const cc = d.constraint_changes || {};
  const cch = (cc.changes || []);
  if (cch.length) {
    html += sectionTitle(`Constraint changes (${cch.length})`, "semantic diff — period, delay, exception, wildcard, add/remove");
    const sevColor = { fatal: "var(--error)", warning: "var(--warning)", info: "var(--accent-2)" };
    cch.slice(0, 60).forEach(x => {
      html += `<div class="ilink"><span class="il-rule">${esc(x.code)}</span><span class="il-kind" style="color:${sevColor[x.severity] || "var(--text-muted)"}">${esc(x.severity)}</span><span class="il-a">${esc(x.description || x.explanation || "")}</span></div>`;
      if (x.explanation) html += `<div class="mono" style="font-size:11.5px;color:var(--text-secondary);margin:2px 0 4px 26px">${esc(x.explanation)}</div>`;
      if (x.v1 || x.v2) {
        html += `<div class="diff-row"><span class="mono" style="color:var(--text-muted)">BEFORE</span><span class="dr-before">${esc(x.v1 || "—")}</span></div><div class="diff-row"><span class="mono" style="color:var(--text-muted)">AFTER</span><span class="dr-after">${esc(x.v2 || "—")}</span></div>`;
      }
    });
    if (cch.length > 60) html += `<div class="mono" style="font-size:11px;color:var(--text-muted)">… ${cch.length - 60} more changes.</div>`;
  } else {
    html += sectionTitle("Constraint changes");
    html += `<div class="mono" style="font-size:11.5px;color:var(--text-muted)">No semantic constraint changes detected between V1 and V2 (periods, delays, exceptions, groups, wildcards all matched).</div>`;
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
    html += emptyState("No analysis to report", "Run a validation first, then export the evidence.", "Open the capability catalog and pick Validate, then Analyze.");
    return html + "</div>";
  }
  // Build snapshot client-side mirroring the backend build
  html += `<div class="ilink"><span class="il-rule">HTML</span><span class="il-kind" style="color:var(--accent-2)">REPORT</span><span class="il-a">Full checker report (errors/warnings/scope) as a standalone HTML file.</span><span class="il-loc"><button class="btn btn-sm" id="rep-html" type="button">Download</button></span></div>`;
  html += `<div class="ilink"><span class="il-rule">JSON</span><span class="il-kind" style="color:var(--accent-2)">RESULT</span><span class="il-a">Complete machine-readable analysis result.</span><span class="il-loc"><button class="btn btn-sm" id="rep-json" type="button">Download</button></span></div>`;
  html += `<div class="ilink"><span class="il-rule">READINESS</span><span class="il-kind" style="color:var(--accent-2)">SNAPSHOT</span><span class="il-a">Serialized readiness object — the CLI baseline format for CI.</span><span class="il-loc"><button class="btn btn-sm" type="button" data-exp="readiness">Download</button></span></div>`;
  html += `<p class="callout co-info"><span><strong>Readiness snapshot</strong> — served by the CLI (\`rta check --save-baseline\`) for CI baselines; the Diff page compares snapshots.</span></p>`;
  return html + "</div>";
}

/* ── CI / Policies ──────────────────────────────────────────────────────── */
export async function pageCI() {
  let html = pageHead("TOOLS", "CI / Policies", "Run a real deterministic gate: compare the current SDC against a baseline snapshot and see the exit code your CI would get.",
                      "A gate PASS means the configured constraint policy held — never a timing pass.");
  html += `<div class="input-surface entry">
    <div class="entry-step"><div class="es-num">1</div><div class="es-main">
      <div class="es-head"><span class="es-title">SDC constraint file (current revision)</span><span class="es-req">REQUIRED</span></div>
      <p class="es-why">Paste the SDC you are about to merge. Ṛta runs the full deterministic check, builds a readiness snapshot, and evaluates the selected gate policy against it.</p>
      <div class="es-actions"><button class="btn btn-sm btn-ghost" id="ci-sample" type="button">Load sample</button></div>
      <textarea class="code-input" id="ci-sdc" rows="7" spellcheck="false" placeholder="set sdc_version 2.2&#10;create_clock -name clk_core -period 5.0 [get_ports clk]&#10;...">${esc(App.state.sdc || "")}</textarea>
    </div></div>
    <div class="entry-step"><div class="es-num">2</div><div class="es-main">
      <div class="es-head"><span class="es-title">Baseline snapshot</span><span class="es-opt">OPTIONAL — blank = baseline built from the same SDC (gate always PASS)</span></div>
      <p class="es-why">A readiness snapshot JSON (from <span class="mono">rta check --save-baseline</span> or the Export page). Without it, the gate compares the revision to itself and passes — paste a real baseline to make the gate meaningful.</p>
      <div class="es-actions"><button class="btn btn-sm" id="ci-mkbase" type="button">Build baseline from this SDC</button><button class="btn btn-sm btn-ghost" id="ci-clrbase" type="button">Clear</button></div>
      <textarea class="code-input" id="ci-baseline" rows="4" spellcheck="false" placeholder='{"schema": "snapshot/v2", ...}'>${esc(App.state.ciBaseline || "")}</textarea>
    </div></div>
    <div class="entry-step"><div class="es-num">3</div><div class="es-main">
      <div class="es-head"><span class="es-title">Gate policy</span><span class="es-req">REQUIRED</span></div>
      <div class="es-actions"><select class="select-input" id="ci-policy" style="max-width:340px">
        <option>BLOCKERS_ONLY</option><option selected>NO_READINESS_REGRESSION</option><option>STRICT</option>
      </select></div>
    </div></div>
    <div class="entry-foot">
      <button class="btn btn-primary btn-lg" id="ci-run" type="button">Run gate</button>
      <span class="mono" style="font-size:11px;color:var(--text-muted)">exit 0 = PASS · 1 = FAIL · 2 = invalid · 3 = engine failure</span>
    </div>
  </div>`;
  html += `<div id="ci-out"></div>`;
  html += sectionTitle("CLI equivalent", "what a CI pipeline actually runs");
  html += `<div class="kv" style="margin:8px 0">`;
  html += `<dt>Save baseline</dt><dd><span class="mono">rta check design.sdc --save-baseline baseline.json</span></dd>`;
  html += `<dt>Gated check</dt><dd><span class="mono">rta check design.sdc --baseline baseline.json --gate NO_READINESS_REGRESSION</span></dd>`;
  html += `<dt>Exit codes</dt><dd><span class="mono">0</span> PASS · <span class="mono">1</span> gate FAIL · <span class="mono">2</span> invalid input/policy · <span class="mono">3</span> engine failure (never a silent PASS)</dd>`;
  html += `</div>`;
  html += `<div class="panel"><div class="panel-head"><span class="panel-title">GitHub Actions example</span></div><pre class="mono" style="font-size:12px;color:var(--text-secondary);overflow-x:auto;margin:0">steps:
  - run: pip install rta-constraint-intelligence
  - run: rta check design.sdc --baseline baseline.json --gate STRICT --junit junit.xml</pre></div>`;
  html += `<p class="callout co-info"><span><strong>CI PASS ≠ timing pass</strong> — the gate only protects against constraint-readiness regressions under the selected policy.</span></p>`;
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
  html += `<dt>Readiness snapshot</dt><dd><span class="mono">rta check design.sdc --save-baseline baseline.json</span></dd>`;
  html += `<dt>Gated check</dt><dd><span class="mono">rta check design.sdc --baseline baseline.json --gate STRICT</span></dd>`;
  html += `<dt>HTML report</dt><dd><span class="mono">rta report check design.sdc -o quality_report.html</span></dd>`;
  html += `</div>`;
  html += `<p class="callout co-info"><span><strong>Snapshot semantics</strong> — the CLI snapshot is the CI baseline format; the Diff page compares snapshots.</span></p>`;
  return html + "</div>";
}

/* ── Trust ──────────────────────────────────────────────────────────────── */
export async function pageTrust() {
  const a = App.state.analysis;
  const scope = (a && a.scope) || {};
  let html = pageHead("TOOLS", "Trust Model", "What Ṛta validates, what it partially validates, and what it does not claim.");
  if (!App.state.evidence) {
    try { App.state.evidence = (await get("/api/evidence")) || {}; }
    catch (e) { App.state.evidence = {}; }
  }
  const ev = App.state.evidence || {};
  html += sectionTitle("Evidence-backed facts", "derived from RELEASE_EVIDENCE.json + the rule registry — not hard-coded");
  html += metricRow([
    { label: "Rules", value: ev.rule_count ?? "—" },
    { label: "Tests", value: ev.test_count ?? "—" },
    { label: "Test files", value: ev.test_files ?? "—" },
    { label: "Golden runners", value: ev.golden_runner_count ?? "—" },
    { label: "Version", value: ev.version ?? "—" },
    { label: "Engine", value: "deterministic" },
  ]);
  html += `<div class="mono" style="font-size:11.5px;color:var(--text-muted);margin:2px 0 10px">evidence updated ${esc(ev.evidence_updated || "—")} · ${esc(ev.release_status || "")} · ${esc(ev.engine || "")}</div>`;
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
  let html = pageHead("TOOLS", "Documentation", "Repository documentation, CLI reference and evidence — real entries only.",
                      "Links open the actual capability pages — this is guidance, not a second catalog.");
  const rules = App.state.rules;
  html += `<div class="kv" style="margin:8px 0">`;
  html += `<dt>Engine</dt><dd class="mono">deterministic · local-first · offline-capable</dd>`;
  html += `<dt>Rules</dt><dd class="mono">${rules ? rules.length + " deterministic rules across all engines" : "loaded on demand"}</dd>`;
  html += `<dt>CLI</dt><dd class="mono">rta check · generate · report · corners · snapshot · diff · lint · convert · batch · web</dd>`;
  html += `</div>`;
  html += sectionTitle("I want to…", "where to go — links open the real capability pages");
  [
    ["Validate an SDC", "validator", "Validate", "Paste SDC (netlist optional) → findings with rule codes and lines."],
    ["Generate an SDC", "generator", "Generator", "Parameters only — no SDC needed. Then Open in Validator."],
    ["Check clock relationships", "clocks", "Clock Intelligence", "Clocks, generated-clock ancestry, relation matrix, missing constraints."],
    ["Check coverage", "coverage", "Coverage", "SDC category coverage (39 categories) + design-aware port coverage with a netlist."],
    ["Compare two SDCs", "diff", "SDC Diff", "Version A vs Version B — readiness findings + semantic CHG-* changes."],
    ["Run a CI policy gate", "ci", "CI", "SDC + baseline + policy → real exit code."],
    ["Review conflicts", "interactions", "Constraint Conflicts", "SDC-067/068/069 with lines and review guidance."],
    ["Check readiness", "readiness", "Readiness", "BLOCKED / REVIEW_REQUIRED / READY with per-dimension WHY."],
  ].forEach(([want, view, label, d]) => html += `<div class="ilink"><span class="il-rule">${esc(want)}</span><span class="il-kind" style="color:var(--accent-2)">${esc(label)}</span><span class="il-a">${esc(d)}</span><span class="il-loc"><a class="cat-inline" href="#/${view}" data-view="${view}">Open →</a></span></div>`);
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
  html += `<div class="ilink"><span class="il-rule">EVIDENCE</span><span class="il-a">rta/evidence/ — release manifest, benchmarks and evidence suites</span></div>`;
  html += `<p class="callout co-info"><span><strong>Trust</strong> — see the Trust page for exactly what Ṛta validates and does not claim.</span></p>`;
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
  let html = pageHead("TOOLS", "Corner Manager", "A corner is a PVT point (process / voltage / temperature) with its own operating condition, derates and uncertainty — signoff runs analyze every corner.",
                      "Next: generate per-corner SDCs in MMC · export JSON for your flow");
  html += `<div class="input-surface entry">
    <div class="entry-step"><div class="es-num">1</div><div class="es-main">
      <div class="es-head"><span class="es-title">Corner preset</span><span class="es-req">REQUIRED</span></div>
      <p class="es-why">Pick a preset and Ṛta validates every corner against the corner_manager backend, then shows the full parameter set (op-cond, V, T, process, derates, uncertainty scale) plus the corner matrix.</p>
      <div class="es-actions"><select class="select-input" id="corner-preset" style="max-width:340px">
        <option value="CLASSIC_3">CLASSIC_3 — 3 corners (SSG/TT/FFG)</option>
        <option value="INDUSTRIAL_5">INDUSTRIAL_5 — 5 corners</option>
        <option value="FULL_8">FULL_8 — 8-corner signoff</option>
      </select>
      <button class="btn btn-primary" id="corner-load" type="button">Load preset</button></div>
    </div></div>
    <div class="entry-step"><div class="es-num">2</div><div class="es-main">
      <div class="es-head"><span class="es-title">Scope</span><span class="es-opt">READ-ONLY INSPECTION</span></div>
      <p class="es-why">This surface inspects and validates the built-in presets and exports them. Corner creation/editing lives in the CLI presets (P2-1 tracked) — this page never fakes an edit capability.</p>
    </div></div>
    <div class="entry-foot">
      <a class="btn btn-ghost btn-lg" href="#/mmc" data-view="mmc">Open MMC → generate per-corner SDCs</a>
    </div>
  </div>
  <div id="corner-out"></div>`;
  return html + "</div>";
}

/* MMC */
export async function pageMMC() {
  let html = pageHead("TOOLS", "MMC SDC", "Generate one SDC per corner from a single template — the corner set you pick really reaches the mmc backend.",
                      "Next: open a generated SDC in Validate · Corner Manager (edit the corner set) · Download .zip");
  html += `<div class="input-surface entry">
    <div class="entry-step"><div class="es-num">1</div><div class="es-main">
      <div class="es-head"><span class="es-title">Corner set</span><span class="es-req">REQUIRED</span></div>
      <p class="es-why">Multi-mode / multi-corner means the same template re-emitted per PVT corner. Pick the preset — CLASSIC_3, INDUSTRIAL_5 or FULL_8 — and Ṛta validates every corner and derives each corner's operating condition, derates and uncertainty scale.</p>
      <div class="es-actions"><select class="select-input" id="mmc-preset" style="max-width:340px">
        <option value="CLASSIC_3">CLASSIC_3 — 3 corners</option>
        <option value="INDUSTRIAL_5">INDUSTRIAL_5 — 5 corners</option>
        <option value="FULL_8">FULL_8 — 8 corners</option>
      </select></div>
    </div></div>
    <div class="entry-step"><div class="es-num">2</div><div class="es-main">
      <div class="es-head"><span class="es-title">Design name</span><span class="es-req">REQUIRED</span></div>
      <input class="opt-input" id="mmc-design" value="MY_DESIGN" style="max-width:340px">
    </div></div>
    <div class="entry-step"><div class="es-num">3</div><div class="es-main">
      <div class="es-head"><span class="es-title">Clock (name port period)</span><span class="es-opt">OPTIONAL — default clk_core clk 5.0</span></div>
      <input class="opt-input" id="mmc-clock" value="clk_core clk 5.0" style="max-width:340px">
    </div></div>
    <div class="entry-foot">
      <button class="btn btn-primary btn-lg" id="mmc-run" type="button">Generate per-corner SDCs</button>
      <span class="mono" style="font-size:11px;color:var(--text-muted)">real mmc backend · every corner validated</span>
    </div>
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

  html += sectionTitle("Test a custom rule", "project-specific policy — affects the real analysis result");
  html += `<div class="input-surface entry" style="margin-top:14px">
    <div class="entry-step"><div class="es-num">1</div><div class="es-main">
      <div class="es-head"><span class="es-title">SDC to test against</span><span class="es-req">REQUIRED</span></div>
      <div class="es-actions"><button class="btn btn-sm btn-ghost" id="cr-sample" type="button">Load sample</button></div>
      <textarea class="code-input" id="cr-sdc" rows="5" spellcheck="false" placeholder="create_clock -name clk -period 12.0 [get_ports clk]&#10;..."></textarea>
    </div></div>
    <div class="entry-step"><div class="es-num">2</div><div class="es-main">
      <div class="es-head"><span class="es-title">Custom rules YAML</span><span class="es-req">REQUIRED</span></div>
      <div class="es-actions"><button class="btn btn-sm btn-ghost" id="cr-example" type="button">Load example ruleset</button></div>
      <textarea class="code-input" id="cr-yaml" rows="6" spellcheck="false" placeholder="rules:
  - id: CUST-001&#10;    command: create_clock&#10;    ..."></textarea>
    </div></div>
    <div class="entry-foot">
      <button class="btn btn-primary btn-lg" id="cr-run" type="button">Run custom rules</button>
      <span class="mono" style="font-size:11px;color:var(--text-muted)">same engine as rta check --custom-rules</span>
    </div>
  </div>
  <div id="cr-out"></div>`;
  return html + "</div>";
}

/* Test Drive */
export async function pageTestDrive() {
  let html = pageHead("TOOLS", "Test Drive", "Run a known SDC through the real Ṛta analysis pipeline and see exactly what comes back.",
                      "Next: open the sample's findings · clocks · coverage — all real backend evidence.");
  html += `<div class="input-surface entry">
    <div class="entry-step"><div class="es-num">1</div><div class="es-main">
      <div class="es-head"><span class="es-title">Sample</span><span class="es-req">REQUIRED</span></div>
      <p class="es-why" id="td-why">A small, known SDC — each one exercises a different part of the analysis.</p>
      <div class="es-actions"><select class="select-input" id="td-sample">
        <option value="good">Good SDC — clean, fully constrained</option>
        <option value="bad">Buggy SDC — undefined clock, duplicate clock, bad generated clock</option>
        <option value="multi">Multi-clock — asynchronous groups</option>
        <option value="generated">Generated clocks — div2/div4 chain</option>
      </select></div>
      <div class="es-head" style="margin-top:10px"><span class="es-title">Sample SDC (read-only, what will be analyzed)</span></div>
      <textarea class="code-input" id="td-sdc" rows="6" spellcheck="false" readonly></textarea>
    </div></div>
    <div class="entry-foot">
      <button class="btn btn-primary btn-lg" id="td-run" type="button">Analyze sample</button>
      <button class="btn btn-sm" id="td-dl" type="button">Download results JSON</button>
      <span class="mono" style="font-size:11px;color:var(--text-muted)">result comes from the real /api/analyze backend — never static</span>
    </div>
  </div>
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

// Phase C — feature-first entry. The capability catalog is the pre-analysis
// navigation; RESULTS pages are phrased as the engineer's questions (Findings,
// Clocks, Coverage, Health, Changes, Conflicts) and appear only after an
// analysis exists. Standalone capabilities are always visible — never hidden.
export const PAGES = {
  // Feature-first entry — the catalog IS the pre-analysis navigation.
  catalog: { label: "Catalog", render: pageCatalog, group: "CATALOG" },
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
  // Standalone capabilities — always visible, never hidden in a disclosure.
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
  // Validator entry — reached via the catalog card and cross-links, never a nav item.
  new_analysis: { label: "New Analysis", render: pageNewAnalysis, group: "HIDDEN" },
};

const GROUP_ORDER = ["RESULTS", "TOOLS"];

function navItemHtml(view, label, current) {
  const active = view === current ? " active" : "";
  return `<button class="nav-item${active}" data-view="${view}" role="tab" aria-selected="${view === current}">
    <span class="ni-icon">${iconFor(view)}</span><span>${label}</span>
  </button>`;
}

// Feature-first navigation (Phase C): RESULTS appear after an analysis exists;
// the standalone capabilities are ALWAYS visible as a TOOLS group — never
// hidden inside a collapsed disclosure. The catalog card links back to the
// full capability catalog.
export function navGroupsHtml(current) {
  const has = !!App.state.analysis;
  const byGroup = {};
  Object.entries(PAGES).forEach(([id, p]) => {
    if (p.group === "HIDDEN") return;
    (byGroup[p.group] = byGroup[p.group] || []).push([id, p.label]);
  });
  const cat = (byGroup["CATALOG"] || []).map(([id, label]) => navItemHtml(id, label, current)).join("");
  const results = (byGroup["RESULTS"] || []).map(([id, label]) => navItemHtml(id, label, current)).join("");
  const tools = (byGroup["TOOLS"] || []).map(([id, label]) => navItemHtml(id, label, current)).join("");
  // Before any analysis the catalog IS the navigation (feature-first entry);
  // the standalone capabilities are still reachable from the catalog cards.
  if (!has) {
    return `<div class="nav-group"><span class="nav-group-label">CAPABILITIES</span>${cat}${tools}</div>`;
  }
  return `<div class="nav-group"><span class="nav-group-label">CAPABILITIES</span>${cat}${tools}</div>
    <div class="nav-group"><span class="nav-group-label">RESULTS</span>${results}</div>`;
}

function iconFor(id) {
  const I = {
    catalog: "⌂", overview: "◧", new_analysis: "＋", validator: "◈", clocks: "◉", context: "▤", coverage: "▦",
    interactions: "⇄", readiness: "◫", diff: "⇔", reports: "▤", export: "⇩",
    ci: "⚙", generator: "✎", linter: "≡", converter: "⇄", corners: "◇",
    mmc: "◈", rules: "☰", trust: "◆", documentation: "❐",
    test_drive: "▶", feedback: "◌", __recent: "◷", __settings: "⚙",
  };
  return I[id] || "·";
}

/* ── Export helpers for event wiring in app.js ─────────────────────────── */
export { findingObj, findingClk, findingLoc, locLines };
