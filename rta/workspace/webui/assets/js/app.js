/* ═══════════════════════════════════════════════════════════════════════════
   Ṛta — app.js
   Shell bootstrap · hash router · nav · top-bar context · status rail ·
   page event wiring · background canvas init.
   ═══════════════════════════════════════════════════════════════════════════ */

import { esc, statusBadge, setStatusMeta, setTokens } from "./theme.js";
import { emptyState, accordion } from "./components.js";
import { initBackground } from "./viz.js";
import {
  App, PAGES, navGroupsHtml, toast, openInspector, closeInspector,
  findingObj, findingClk, findingLoc, locLines,
} from "./pages.js";

// The pre-loaded sample (PDS §1): a real block-level constraint set with
// clocks, delays, exceptions and two intentional defects — SDC-008 (input
// delay >= clock period) and SDC-030 (no set_propagated_clock). SDC-020
// (suspicious false path) is a natural consequence of the false-path example.
const SAMPLE = `set sdc_version 2.2
set_units -time ns -capacitance pF

create_clock -name clk_core -period 5.0 [get_ports clk]
create_clock -name clk_io -period 10.0 [get_ports clk_io]
create_generated_clock -name clk_div2 -source [get_ports clk] -divide_by 2 [get_pins u0/clkout]

set_clock_uncertainty -setup 0.15 -hold 0.08 [get_clocks clk_core]
set_clock_groups -asynchronous -group [get_clocks clk_core] -group [get_clocks clk_io]
set_false_path -from [get_clocks clk_io] -to [get_clocks clk_core]

set_input_delay -max 6.0 -min 0.3 -clock clk_core [get_ports data_in]
set_output_delay -max 1.5 -min 0.5 -clock clk_core [all_outputs]
`;

const SAMPLE_NETLIST = `module top(input clk, input clk_io, input [3:0] din, output [3:0] dout);
  reg [3:0] q;
  always @(posedge clk) q <= din;
  assign dout = q;
endmodule
`;

let current = "overview";
let rulesCache = null;

const $ = (sel) => document.querySelector(sel);

/* Shared client-side download helper (blob → <a download>) — used by every
   tool page's Download/Export button (Linter, Converter, Corners, MMC, Rules,
   Test Drive, Reports, Export). */
function dl(name, content, mime) {
  const b = new Blob([content], { type: mime });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(b); a.download = name; a.click();
  // Revoke on the next tick — revoking synchronously can drop the download
  // in Chrome/Firefox before the click is processed.
  setTimeout(() => URL.revokeObjectURL(a.href), 1000);
  toast(`Downloaded ${name}`);
}

/* ── Bootstrap ──────────────────────────────────────────────────────────── */
async function boot() {
  initBackground($("#bg"));
  try {
    const design = await fetch("/api/design").then(r => r.json());
    setStatusMeta(design);
    setTokens(design);
    if (design.version) $("#ver").textContent = `v${design.version}`;
  } catch (e) { /* fallback metadata used */ }
  try {
    rulesCache = (await fetch("/api/rules").then(r => r.json())).rules || [];
    App.state.rules = rulesCache;
  } catch (e) { App.state.rules = []; }

  // PDS §4 — the sample SDC is the default starting point for every session.
  if (!App.state.sdc) {
    App.state.sdc = SAMPLE;
    App.state.filename = "sample_block.sdc";
  }

  window.addEventListener("hashchange", route);
  $("#inspector-close").addEventListener("click", closeInspector);
  $("#inspector-backdrop").addEventListener("click", closeInspector);
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") { closeInspector(); closeMenus(); }
    // "/" focuses the command-bar search from anywhere
    if (e.key === "/" && !/^(INPUT|TEXTAREA|SELECT)$/.test(document.activeElement.tagName)) {
      e.preventDefault();
      const s = $("#cmd-search");
      if (s) s.focus();
    }
  });

  wireCommandBar();
  // brand mark returns to the New Analysis landing (primary action)
  const brand = $(".cmdbar-brand");
  if (brand) brand.addEventListener("click", () => { location.hash = "#/new_analysis"; });

  route();
}

function closeMenus() {
  ["menu-session", "menu-quick", "menu-settings"].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.hidden = true;
  });
}

function currentView() {
  const h = location.hash.replace(/^#\/?/, "");
  if (PAGES[h]) return h;
  // Pre-analysis the product IS the input screen (New Analysis, no sidebar).
  // After analysis the engineer lands on Findings — "what did Ṛta find?"
  return App.state.analysis ? "validator" : "new_analysis";
}

/* ── Routing ────────────────────────────────────────────────────────────── */
async function route() {
  const view = currentView();
  current = view;
  // No sidebar before an analysis exists — the input screen is the product.
  document.body.classList.toggle("no-analysis", !App.state.analysis);
  renderNav();
  const main = $("#main");
  // page transition: fade out is skipped (Streamlit-free instant DOM); the
  // .page class animates in on each route — restrained 220ms entrance.
  main.innerHTML = "";
  const page = PAGES[view];
  if (!page) { main.innerHTML = emptyState("Unknown page", "That workspace page does not exist."); return; }
  try {
    const html = await page.render();
    main.innerHTML = html;
    wirePage(view);
    updateContext();
  } catch (e) {
    main.innerHTML = `
      <div class="page">
        <p class="page-eyebrow">ERROR</p>
        <h1 class="page-title">Page failed to render</h1>
        <div class="err err-engine"><span class="e-kind">Engine failure</span><span class="err-msg">${esc(e.message || String(e))}</span></div>
      </div>`;
  }
}

function renderNav() {
  $("#nav-groups").innerHTML = navGroupsHtml(current);
  $("#nav-groups").querySelectorAll(".nav-item").forEach(btn => {
    btn.addEventListener("click", () => {
      const action = btn.dataset.action;
      if (action === "new-session") { newSession(); return; }
      if (action === "recent-sessions") { showRecentSessions(); return; }
      if (action === "settings") { const s = $("#cmd-settings"); if (s) s.click(); return; }
      if (btn.dataset.view) location.hash = `#/${btn.dataset.view}`;
    });
  });
}

/* ── Session-first architecture ────────────────────────────────────────── */
function currentSessionName() {
  const s = App.state.session;
  return s && s.name ? s.name : "Untitled session";
}

function newSession() {
  App.state.session = { id: null, name: "Untitled session", status: "EMPTY", createdAt: null,
                        sdc: SAMPLE, netlist: "", filename: "sample_block.sdc", analysis: null };
  App.state.analysis = null;
  App.state.sdc = SAMPLE;
  App.state.filename = "sample_block.sdc";
  App.state.filters = { sev: "All", rule: "All", q: "" };
  App.state.diffResult = null;
  App.state.ruleFilter = "All";
  toast("New session started — sample SDC loaded");
  // Re-render even when the hash is already the landing (no hashchange fires),
  // so the body class and sidebar always reflect the cleared analysis.
  if (location.hash !== "#/new_analysis") location.hash = "#/new_analysis";
  route();
}

function pushRecentSession() {
  const s = App.state.session;
  if (!s || !s.id) return;
  const prev = App.state.recentSessions.find(x => x.id === s.id);
  const entry = { id: s.id, name: s.name, createdAt: s.createdAt, status: s.status,
                  readiness: (s.analysis || {}).readiness ? (s.analysis.readiness.overall || "") : "" };
  if (prev) Object.assign(prev, entry);
  else { App.state.recentSessions.unshift(entry); App.state.recentSessions = App.state.recentSessions.slice(0, 8); }
}

// Adopt an analysis result into the current session. A fresh session id is
// minted when the analyzed file differs from the session's file; re-running
// the same file updates the same session row (current-session model).
function adoptAnalysis(res, opts = {}) {
  const prev = App.state.session || {};
  const file = opts.filename || App.state.filename || "pasted.sdc";
  const fileChanged = !!(opts.filename) && opts.filename !== (prev.filename || "");
  const id = prev.id && !fileChanged ? prev.id : `sess-${Date.now()}`;
  App.state.session = {
    id,
    name: opts.name || file.replace(/\.[^.]+$/, ""),
    status: "ANALYZED",
    createdAt: prev.createdAt && !fileChanged ? prev.createdAt : new Date().toISOString(),
    sdc: opts.sdc || "", netlist: opts.netlist || "",
    filename: file,
    analysis: res,
  };
  if (opts.filename) App.state.filename = opts.filename;
  pushRecentSession();
}

function restoreSession(entry) {
  const s = App.state.session;
  if (!s || s.id !== entry.id) {
    toast("Session context is in-memory for this tab — re-run the analysis to restore evidence.", true);
    return;
  }
  location.hash = "#/overview";
  updateContext();
}

function showRecentSessions() {
  const list = App.state.recentSessions;
  if (!list.length) {
    openInspector("Recent Sessions",
      `<div class="insp-section"><div class="insp-v">No sessions yet in this browser tab.</div></div>
       <div class="insp-section"><div class="insp-k">Note</div><div class="insp-v">Sessions are held in memory for the current tab; re-analyzing restores full evidence.</div></div>`);
    return;
  }
  const cur = App.state.session ? App.state.session.id : null;
  const html = list.map((e, i) => `
    <button class="insp-row" data-sess="${i}" type="button">
      <span class="insp-k">${esc(e.name)}</span>
      <span class="insp-v mono">${esc(new Date(e.createdAt).toLocaleTimeString())} · ${esc(e.status)}${e.readiness ? " · " + esc(e.readiness) : ""}${e.id !== cur ? " · re-run to restore" : ""}</span>
    </button>`).join("");
  openInspector("Recent Sessions", html);
  document.querySelectorAll("#inspector-body [data-sess]").forEach(btn => {
    btn.addEventListener("click", () => restoreSession(list[+btn.dataset.sess]));
  });
}

/* ── Command bar ───────────────────────────────────────────────────────── */
function wireCommandBar() {
  const search = $("#cmd-search");
  if (search) {
    const apply = () => {
      const q = search.value.trim().toLowerCase();
      let visible = 0;
      document.querySelectorAll("#nav-groups .nav-group").forEach(g => {
        let gv = 0;
        g.querySelectorAll(".nav-item").forEach(it => {
          const hit = !q || it.textContent.toLowerCase().includes(q);
          it.hidden = !hit;
          if (hit) gv++;
        });
        g.hidden = gv === 0;
        visible += gv;
      });
      const empty = $("#nav-empty");
      if (empty) empty.hidden = visible !== 0;
    };
    search.addEventListener("input", apply);
    search.addEventListener("keydown", e => { if (e.key === "Escape") { search.value = ""; apply(); search.blur(); } });
  }

  const toggleMenu = (id) => {
    const el = document.getElementById(id);
    if (!el) return;
    const was = !el.hidden; // open before toggling
    closeMenus();
    el.hidden = was; // re-open if it was closed; close if it was open
  };

  const openBtn = $("#cmd-open-session");
  if (openBtn) openBtn.addEventListener("click", () => {
    const s = App.state.session;
    const menu = $("#menu-session");
    if (!menu) return;
    const list = App.state.recentSessions;
    toggleMenu("menu-session");
    if (menu.hidden) return;
    menu.innerHTML = `<div class="cmd-menu-label">Current session</div>
      <button class="cmd-menu-item" data-m="cur" type="button"><span class="mono">${esc(currentSessionName())}</span><span class="m-sub">${esc(s && s.status ? s.status : "EMPTY")}</span></button>
      <div class="cmd-menu-label">Recent sessions (this tab)</div>`
      + (list.length
        ? list.map((e, i) => `<button class="cmd-menu-item" data-m="r${i}" type="button"><span class="mono">${esc(e.name)}</span><span class="m-sub">${esc(new Date(e.createdAt).toLocaleTimeString())}${e.readiness ? " · " + esc(e.readiness) : ""}</span></button>`).join("")
        : `<div class="cmd-menu-item disabled">no sessions yet</div>`)
      + `<div class="cmd-menu-label">Actions</div>
         <button class="cmd-menu-item" data-m="new" type="button">New Session</button>`;
    menu.querySelectorAll("[data-m]").forEach(b => b.addEventListener("click", () => {
      const m = b.dataset.m;
      closeMenus();
      if (m === "new") newSession();
      else if (m === "cur") { location.hash = "#/overview"; }
      else if (m.startsWith("r")) restoreSession(list[+m.slice(1)]);
    }));
  });

  const impBtn = $("#cmd-import");
  if (impBtn) impBtn.addEventListener("click", () => {
    const inp = document.createElement("input");
    inp.type = "file"; inp.accept = ".sdc,.txt,.tcl";
    inp.addEventListener("change", async () => {
      const f = inp.files && inp.files[0];
      if (!f) return;
      const text = await f.text();
      App.state.sdc = text;
      App.state.filename = f.name || "pasted.sdc";
      toast(`Imported ${f.name}`);
      location.hash = "#/validator";
      // pageValidator renders the textarea from App.state.sdc — no push needed
    });
    inp.click();
  });

  const quickBtn = $("#cmd-quick");
  if (quickBtn) quickBtn.addEventListener("click", () => {
    const menu = $("#menu-quick");
    if (!menu) return;
    const has = !!App.state.analysis;
    menu.innerHTML = `<div class="cmd-menu-label">Quick actions</div>
      <button class="cmd-menu-item" data-q="sample" type="button">Load sample SDC</button>
      <button class="cmd-menu-item" data-q="validate" type="button">Go to Findings</button>
      <button class="cmd-menu-item" data-q="overview" type="button">Go to Summary</button>
      <button class="cmd-menu-item${has ? "" : " disabled"}" data-q="json" type="button">${has ? "Download analysis JSON" : "Download analysis JSON (run analysis first)"}</button>
      <button class="cmd-menu-item${has ? "" : " disabled"}" data-q="new" type="button">New Session</button>`;
    toggleMenu("menu-quick");
    if (menu.hidden) return;
    menu.querySelectorAll("[data-q]").forEach(b => b.addEventListener("click", () => {
      const q = b.dataset.q;
      closeMenus();
      if (q === "sample") { location.hash = "#/validator"; setTimeout(() => { const b2 = $("#val-load-sample"); if (b2) b2.click(); }, 80); }
      else if (q === "validate") location.hash = "#/validator";
      else if (q === "overview") location.hash = "#/overview";
      else if (q === "json" && has) {
        const blob = new Blob([JSON.stringify(App.state.analysis, null, 2)], { type: "application/json" });
        const a = document.createElement("a"); a.href = URL.createObjectURL(blob); a.download = "analysis_result.json"; a.click();
        URL.revokeObjectURL(a.href); toast("Downloaded analysis_result.json");
      }
      else if (q === "new") newSession();
    }));
  });

  const setBtn = $("#cmd-settings");
  if (setBtn) setBtn.addEventListener("click", () => {
    const menu = $("#menu-settings");
    if (!menu) return;
    menu.innerHTML = `<div class="cmd-menu-label">Workspace</div>
      <div class="cmd-menu-item"><span class="m-sub">Motion: ${window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches ? "reduced (system preference respected)" : "ambient (respects system reduced-motion preference)"}</span></div>
      <div class="cmd-menu-item"><span class="m-sub">Engine: deterministic · local · offline · no LLM</span></div>
      <div class="cmd-menu-item"><span class="m-sub">Sessions: in-memory for this browser tab</span></div>
      <div class="cmd-menu-label">About</div>
      <div class="cmd-menu-item"><span class="mono">Ṛta — Constraint Intelligence for Digital Design</span></div>`;
    toggleMenu("menu-settings");
  });

  // click-away closes command menus
  document.addEventListener("click", (e) => {
    if (!e.target.closest(".cmdbar")) closeMenus();
  });
}

function updateContext() {
  const a = App.state.analysis;
  const sess = App.state.session;
  const ctx = {
    file: a ? App.state.filename : (sess.filename || "—"),
    mode: a ? (a.mode_note || "SDC_ONLY").split(" (")[0] : "—",
    netlist: (a && a.context) ? "netlist: loaded" : (sess.netlist ? "netlist: loaded" : "no netlist"),
  };
  const fEl = document.querySelector('[data-ctx="file"]');
  if (fEl) fEl.textContent = ctx.file;
  const mEl = document.querySelector('[data-ctx="mode"]');
  if (mEl) mEl.textContent = ctx.mode;
  const nEl = document.querySelector('[data-ctx="netlist"]');
  if (nEl) nEl.textContent = ctx.netlist;
  const nameEl = $("#session-name");
  if (nameEl) nameEl.textContent = currentSessionName();
  const timeEl = $("#session-time");
  if (timeEl) timeEl.textContent = sess.createdAt ? new Date(sess.createdAt).toLocaleTimeString() : "";
  const scopeEl = $("#session-scope");
  const statEl = $("#session-status");
  const trustEl = $("#ctx-trust"), rdyEl = $("#ctx-readiness");
  if (a) {
    const issues = a.issues || [];
    const errs = issues.filter(i => i.sev === "error").length;
    const warns = issues.filter(i => i.sev === "warning").length;
    const clk = ((a.clock_relations || {}).clocks || []).length;
    if (scopeEl) scopeEl.textContent = `${errs}E · ${warns}W · ${clk} clk`;
    if (statEl) statEl.textContent = sess.status || "ANALYZED";
    trustEl.innerHTML = statusBadge("trust", (a.scope || {}).status || "NOT_VALIDATED");
    rdyEl.innerHTML = statusBadge("readiness", (a.readiness || {}).overall || "—");
  } else {
    if (scopeEl) scopeEl.textContent = "";
    if (statEl) statEl.textContent = sess.status || "EMPTY";
    trustEl.innerHTML = ""; rdyEl.innerHTML = "";
  }
  // status rail
  const rail = $("#rail");
  if (!a) {
    rail.innerHTML = `<span class="rail-item"><span class="rail-label">status</span><span>no analysis loaded</span></span>
      <span class="rail-item"><span class="rail-label">engine</span><span class="mono">deterministic · offline</span></span>`;
    return;
  }
  const issues = a.issues || [];
  const errs = issues.filter(i => i.sev === "error").length;
  const warns = issues.filter(i => i.sev === "warning").length;
  const infos = issues.filter(i => i.sev === "info").length;
  // The Validate rail reports the checker's unique-clock count (the number the
  // findings/readiness engine reasons about); the Clocks page shows the full
  // parsed inventory (which may include duplicates flagged by SDC-002).
  const clocks = (a.stats && a.stats.Clocks != null)
    ? a.stats.Clocks : ((a.clock_relations || {}).clocks || []).length;
  rail.innerHTML = `
    <span class="rail-item"><span class="rail-label">errors</span><span class="rail-num" style="color:${errs ? "var(--error)" : "var(--success)"}">${errs}</span></span>
    <span class="rail-item"><span class="rail-label">warnings</span><span class="rail-num" style="color:${warns ? "var(--warning)" : "var(--text-primary)"}">${warns}</span></span>
    <span class="rail-item"><span class="rail-label">info</span><span class="rail-num">${infos}</span></span>
    <span class="rail-item"><span class="rail-label">clocks</span><span class="rail-num">${clocks}</span></span>
    <span class="rail-item"><span class="rail-label">mode</span><span class="mono" style="color:var(--text-secondary)">${esc(a.mode_note || "SDC only")}</span></span>
  `;
}

/* ═══════════════════════════════════════════════════════════════════════════
   PAGE EVENT WIRING
   ═══════════════════════════════════════════════════════════════════════════ */

async function wirePage(view) {
  const main = $("#main");
  if (view === "new_analysis") wireNewAnalysis(main);
  else if (view === "validator") wireValidator(main);
  else if (view === "diff") wireDiff(main);
  else if (view === "reports") wireReports(main);
  else if (view === "export") wireExport(main);
  else if (view === "generator") wireGenerator(main);
  else if (view === "linter") wireLinter(main);
  else if (view === "converter") wireConverter(main);
  else if (view === "corners") wireCorners(main);
  else if (view === "mmc") wireMMC(main);
  else if (view === "rules") wireRules(main);
  else if (view === "test_drive") wireTestDrive(main);
  else if (view === "feedback") wireFeedback(main);
  else if (view === "clocks") wireClocks(main);
  else if (view === "overview" || view === "readiness" || view === "coverage"
           || view === "interactions" || view === "context") wireCrossLinks(main);
}

/* ── New Analysis (guided entry) ───────────────────────────────────────── */
function wireNewAnalysis(main) {
  const sdcEl = $("#na-sdc");
  const netEl = $("#na-netlist");
  if (sdcEl) sdcEl.addEventListener("input", () => { App.state.sdc = sdcEl.value; });
  const readFile = (inp, cb) => inp.addEventListener("change", async () => {
    const f = inp.files && inp.files[0];
    if (f) cb(await f.text(), f.name);
  });
  const sdcPick = document.createElement("input");
  sdcPick.type = "file"; sdcPick.accept = ".sdc,.txt,.tcl";
  readFile(sdcPick, (text, name) => {
    App.state.sdc = text; App.state.filename = name;
    sdcEl.value = text; const fEl = $("#na-file"); if (fEl) fEl.textContent = name;
    toast(`Loaded ${name}`);
  });
  const p1 = $("#na-pick"); if (p1) p1.addEventListener("click", () => sdcPick.click());
  const netPick = document.createElement("input");
  netPick.type = "file"; netPick.accept = ".v,.sv,.verilog,.txt";
  readFile(netPick, (text, name) => {
    netEl.value = text; const nEl = $("#na-net-file"); if (nEl) nEl.textContent = name;
    toast(`Netlist ${name} loaded`);
  });
  const p2 = $("#na-net-pick"); if (p2) p2.addEventListener("click", () => netPick.click());
  const samp = $("#na-sample");
  if (samp) samp.addEventListener("click", () => {
    App.state.sdc = SAMPLE; App.state.filename = "sample_block.sdc";
    sdcEl.value = SAMPLE;
    const fEl = $("#na-file"); if (fEl) fEl.textContent = "sample_block.sdc";
    netEl.value = SAMPLE_NETLIST;
    const nEl = $("#na-net-file"); if (nEl) nEl.textContent = "sample_top.v";
    toast("Sample loaded — includes intentional SDC-008 and SDC-030 defects");
  });
  const clear = $("#na-clear");
  if (clear) clear.addEventListener("click", () => {
    App.state.sdc = ""; sdcEl.value = ""; App.state.filename = "pasted.sdc";
    const fEl = $("#na-file"); if (fEl) fEl.textContent = "pasted.sdc";
  });
  const nclear = $("#na-net-clear");
  if (nclear) nclear.addEventListener("click", () => {
    netEl.value = ""; const nEl = $("#na-net-file"); if (nEl) nEl.textContent = "no netlist";
  });
  const run = $("#na-analyze");
  if (run) run.addEventListener("click", async () => {
    const sdc = sdcEl.value.trim();
    if (!sdc) { toast("Load or paste an SDC file first", true); return; }
    App.state.sdc = sdc;
    await runAnalyze({
      sdc, filename: App.state.filename,
      netlist: netEl.value, baseline: $("#na-baseline") ? $("#na-baseline").value : "",
      gate: $("#na-gate") ? $("#na-gate").value : "",
      custom_rules: $("#na-rules") ? $("#na-rules").value : "",
    }, "validator");
  });
}

/* ── Validator ──────────────────────────────────────────────────────────── */
function wireValidator(main) {
  const sdcEl = $("#val-sdc");
  const netEl = $("#val-netlist");
  const baseEl = $("#val-baseline");
  const gateEl = $("#val-gate");
  sdcEl.addEventListener("input", () => App.state.sdc = sdcEl.value);

  $("#val-load-sample").addEventListener("click", () => {
    App.state.sdc = SAMPLE;
    App.state.filename = "sample_top.sdc";
    sdcEl.value = SAMPLE;
    $("#val-file").textContent = App.state.filename;
    if (netEl) netEl.value = SAMPLE_NETLIST;
  });
  $("#val-clear").addEventListener("click", () => {
    App.state.sdc = ""; sdcEl.value = ""; App.state.filename = "pasted.sdc";
    $("#val-file").textContent = App.state.filename;
    if (netEl) netEl.value = "";
    if (baseEl) baseEl.value = "";
    if (gateEl) gateEl.value = "";
  });
  $("#val-analyze").addEventListener("click", async () => {
    const sdc = sdcEl.value.trim();
    if (!sdc) { toast("Paste or upload an SDC file first", true); return; }
    App.state.sdc = sdc;
    App.state.filename = App.state.filename || "pasted.sdc";
    await runAnalyze({ sdc, filename: App.state.filename, netlist: netEl ? netEl.value : "", baseline: baseEl ? baseEl.value : "", gate: gateEl ? gateEl.value : "", custom_rules: $("#val-rules") ? $("#val-rules").value : "" });
  });

  // filters
  const fq = $("#f-q");
  if (fq) {
    fq.addEventListener("input", () => { App.state.filters.q = fq.value; route(); });
  }
  main.querySelectorAll("#f-rule").forEach(sel => {
    sel.addEventListener("change", () => { App.state.filters.rule = sel.value; route(); });
  });
  main.querySelectorAll("[data-seg]").forEach(btn => {
    btn.addEventListener("click", () => { App.state.filters.sev = btn.dataset.seg; route(); });
  });
  const fc = $("#f-clear");
  if (fc) fc.addEventListener("click", () => {
    App.state.filters = { sev: "All", rule: "All", q: "" }; route();
  });

  // finding rows → inspector
  main.querySelectorAll(".tbl tbody tr.row-click").forEach(tr => {
    tr.addEventListener("click", () => {
      const i = +tr.dataset.idx;
      const a = App.state.analysis;
      if (!a) return;
      const it = (a.issues || [])[i];
      if (!it) return;
      const rule = rulesCache ? rulesCache.find(r => r.code === it.code) : null;
      openInspector(`${it.code} — Finding`, findingDetail(it, rule));
    });
  });
}

const STAGES = ["parse", "clocks", "context", "coverage", "interactions", "readiness", "result"];

async function runAnalyze(payload, after = null) {
  const main = $("#main");
  // Honest stage timeline (PDS §8): checkpoints complete only when the real
  // deterministic pipeline returns; the first stage pulses while in flight.
  main.innerHTML = `
    <div class="page">
      <p class="page-eyebrow">ANALYZE</p>
      <h1 class="page-title">Analyzing constraints</h1>
      <div class="analyzing"><div class="spinner" aria-hidden="true"></div>
        <div class="stage-track">
          ${STAGES.map((s, i) => `<span class="stage${i === 0 ? " active" : ""}">${s}</span>`).join("")}
        </div>
        <span class="mono" style="font-size:11.5px;color:var(--text-muted)">running the deterministic pipeline locally…</span>
      </div>
    </div>`;
  const track = main.querySelector(".stage-track");
  const advance = (idx) => {
    const stages = track.querySelectorAll(".stage");
    stages.forEach((s, i) => {
      s.classList.toggle("done", i < idx);
      s.classList.toggle("active", i === idx);
    });
  };
  try {
    const res = await post("/api/analyze", payload);
    advance(STAGES.length);
    App.state.analysis = res;
    // session-first: adopt this run's evidence into the current session
    adoptAnalysis(res, { sdc: payload.sdc, netlist: payload.netlist,
                         filename: payload.filename || App.state.filename });
    await new Promise(r => setTimeout(r, 350)); // brief final-stage presentation
    if (after) {
      // First-run flow: auto-transition into the workspace — Overview landing.
      location.hash = `#/${after}`;
    } else {
      // Validate flow: re-render the current page so findings are visible now.
      route();
    }
  } catch (e) {
    main.innerHTML = `
      <div class="page">
        <p class="page-eyebrow">ANALYZE</p>
        <h1 class="page-title">Validate</h1>
        <div class="err err-engine"><span class="e-kind">Engine failure</span><span class="err-msg">${esc(e.message || String(e))}</span></div>
      </div>`;
    toast("Analysis failed", true);
  }
}

import { findingDetailHtml } from "./components.js";
function findingDetail(it, rule) {
  return findingDetailHtml({
    sev: it.sev, code: it.code, msg: it.msg, obj: findingObj(it), clk: findingClk(it),
    loc: findingLoc(it), line: it.line, line2: it.line2, requires_sta: (it.code === "SDC-070" || ((it.identity || {}).interaction_type || "").includes("sta")),
  }, rule);
}

async function post(path, body) {
  const r = await fetch(path, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
  if (!r.ok) { let d = `HTTP ${r.status}`; try { d = (await r.json()).detail || d; } catch (e) {} throw new Error(d); }
  return r.json();
}

/* ── Clocks (inspector on node/row click) ───────────────────────────────── */
function wireClocks(main) {
  main.querySelectorAll(".ct-node").forEach(n => {
    n.addEventListener("click", () => {
      const a = App.state.analysis;
      const clocks = ((a || {}).clock_relations || {}).clocks || [];
      const c = clocks.find(x => x.name === n.dataset.clock);
      if (!c) return;
      openInspector(`Clock — ${c.name}`, `
        <div class="insp-section"><div class="insp-k">Period</div><div class="insp-v mono">${esc(Number(c.period).toFixed(2))} ns · ${esc((1000 / c.period).toFixed(2))} MHz</div></div>
        <div class="insp-section"><div class="insp-k">Type</div><div class="insp-v">${c.is_generated ? "generated" : c.is_virtual ? "virtual" : "primary"}</div></div>
        <div class="insp-section"><div class="insp-k">Source</div><div class="insp-v mono">${esc(c.source_port || c.source_node || "—")}</div></div>
        <div class="insp-section"><div class="insp-k">Master</div><div class="insp-v mono">${esc(c.master_clock || "—")}</div></div>
        <div class="insp-section"><div class="insp-k">Definition</div><pre class="mono" style="font-size:11px;color:var(--text-secondary);white-space:pre-wrap;margin:0">${esc(c.raw_text || "")}</pre></div>`);
    });
    n.addEventListener("keydown", e => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); n.click(); } });
  });
  main.querySelectorAll(".tbl tbody tr.row-click").forEach(tr => {
    tr.addEventListener("click", () => {
      const a = App.state.analysis;
      const clocks = ((a || {}).clock_relations || {}).clocks || [];
      const c = clocks.find(x => x.name === tr.dataset.key);
      if (c) { n.click ? null : null; openInspector(`Clock — ${c.name}`, clockDetail(c)); }
    });
  });
}
function clockDetail(c) {
  return `
    <div class="insp-section"><div class="insp-k">Period</div><div class="insp-v mono">${esc(Number(c.period).toFixed(2))} ns · ${esc((1000 / c.period).toFixed(2))} MHz</div></div>
    <div class="insp-section"><div class="insp-k">Type</div><div class="insp-v">${c.is_generated ? "generated" : c.is_virtual ? "virtual" : "primary"}</div></div>
    <div class="insp-section"><div class="insp-k">Source</div><div class="insp-v mono">${esc(c.source_port || c.source_node || "—")}</div></div>
    <div class="insp-section"><div class="insp-k">Master</div><div class="insp-v mono">${esc(c.master_clock || "—")}</div></div>
    <div class="insp-section"><div class="insp-k">Definition</div><pre class="mono" style="font-size:11px;color:var(--text-secondary);white-space:pre-wrap;margin:0">${esc(c.raw_text || "")}</pre></div>`;
}

/* ── Diff ───────────────────────────────────────────────────────────────── */
function wireDiff(main) {
  const v1 = $("#diff-v1"), v2 = $("#diff-v2");
  v1.addEventListener("input", () => App.state.diffV1 = v1.value);
  v2.addEventListener("input", () => App.state.diffV2 = v2.value);
  $("#diff-run").addEventListener("click", async () => {
    if (!v1.value.trim() || !v2.value.trim()) { toast("Enter both V1 and V2 SDC text", true); return; }
    try {
      const res = await post("/api/analyze", { sdc: v2.value.trim() });
      // build snapshots server-side: call analyze twice and diff via a dedicated flow
      const d = await post("/api/diff", { v1: v1.value.trim(), v2: v2.value.trim() });
      App.state.diffResult = d.diff || d;
      App.state.diffFilter = "new";
      route();
    } catch (e) { toast("Diff failed: " + (e.message || e), true); }
  });
  main.querySelectorAll("#diff-seg [data-seg]").forEach(btn => {
    btn.addEventListener("click", () => { App.state.diffFilter = btn.dataset.seg; route(); });
  });
}

/* ── Reports ────────────────────────────────────────────────────────────── */
function wireReports(main) {
  $("#rep-json").addEventListener("click", () => {
    dl("analysis_result.json", JSON.stringify(App.state.analysis, null, 2), "application/json");
  });
  $("#rep-html").addEventListener("click", async () => {
    try {
      const res = await post("/api/report/html", { analysis: App.state.analysis, sdc: App.state.sdc });
      dl("sdc_report.html", res.html, "text/html");
    } catch (e) { toast("Report generation failed", true); }
  });
}

/* ── Export ─────────────────────────────────────────────────────────────── */
function wireExport(main) {
  const jb = $("#exp-json");
  if (jb) jb.addEventListener("click", () => {
    dl("analysis_result.json", JSON.stringify(App.state.analysis, null, 2), "application/json");
  });
  const rb = $("#exp-html");
  if (rb) rb.addEventListener("click", async () => {
    try {
      const res = await post("/api/report/html", { analysis: App.state.analysis, sdc: App.state.sdc });
      dl("sdc_report.html", res.html, "text/html");
    } catch (e) { toast("Report generation failed", true); }
  });
  const rdy = $("#exp-rdy");
  if (rdy) rdy.addEventListener("click", () => {
    const r = (App.state.analysis || {}).readiness || {};
    dl("readiness_evidence.json", JSON.stringify(r, null, 2), "application/json");
  });
}

/* ── Generator ──────────────────────────────────────────────────────────── */
function wireGenerator(main) {
  $("#gen-run").addEventListener("click", async () => {
    const design = ($("#gen-design").value || "MY_DESIGN").trim();
    const clk = ($("#gen-clock").value || "clk_core clk 5.0").trim().split(/\s+/);
    const ind = ($("#gen-in").value || "1.2 0.4").trim().split(/\s+/);
    const outd = ($("#gen-out").value || "1.5 0.5").trim().split(/\s+/);
    const params = {
      design_name: design,
      clocks: [{ name: clk[0], port: clk[1] || "clk", period: parseFloat(clk[2] || 5.0), uncertainty: 0.15, clk_type: "primary" }],
      in_delay_max: parseFloat(ind[0] || 1.2), in_delay_min: parseFloat(ind[1] || 0.4),
      out_delay_max: parseFloat(outd[0] || 1.5), out_delay_min: parseFloat(outd[1] || 0.5),
    };
    try {
      const res = await post("/api/generate", { params });
      $("#gen-out-area").innerHTML = `
        <div class="section-title">Generated SDC <span class="st-note">from the real generate_sdc backend</span></div>
        <div style="margin:8px 0;display:flex;gap:8px;flex-wrap:wrap">
          <button class="btn btn-sm" id="gen-copy" type="button">Copy</button>
          <button class="btn btn-sm" id="gen-dl" type="button">Download .sdc</button>
          <button class="btn btn-sm btn-primary" id="gen-validate" type="button">Open in Validator</button>
        </div>
        <pre class="mono" style="font-size:12px;color:var(--text-secondary);background:var(--bg-secondary);border:1px solid var(--border-subtle);border-radius:var(--radius-md);padding:14px;overflow-x:auto;white-space:pre-wrap">${esc(res.sdc)}</pre>`;
      const gc = $("#gen-copy");
      if (gc) gc.addEventListener("click", () => {
        navigator.clipboard.writeText(res.sdc).then(() => toast("SDC copied to clipboard"), () => toast("Clipboard unavailable", true));
      });
      const gd = $("#gen-dl");
      if (gd) gd.addEventListener("click", () => {
        const b = new Blob([res.sdc], { type: "text/plain" });
        const a = document.createElement("a");
        a.href = URL.createObjectURL(b); a.download = `${design}.sdc`; a.click();
        URL.revokeObjectURL(a.href); toast(`Downloaded ${design}.sdc`);
      });
      const gv = $("#gen-validate");
      if (gv) gv.addEventListener("click", () => {
        App.state.sdc = res.sdc;
        App.state.filename = `${design}.sdc`;
        toast(`Loaded ${design}.sdc into the workspace`);
        location.hash = "#/validator";
      });
    } catch (e) { toast("Generation failed", true); }
  });
}

/* ── Linter ─────────────────────────────────────────────────────────────── */
function wireLinter(main) {
  const inp = $("#lint-in");
  inp.addEventListener("input", () => App.state.lintIn = inp.value);
  $("#lint-run").addEventListener("click", async () => {
    if (!inp.value.trim()) { toast("Paste SDC to lint", true); return; }
    try {
      const res = await post("/api/lint", { sdc: inp.value });
      $("#lint-out").innerHTML = `
        <div style="margin:8px 0"><button class="btn btn-sm" id="lint-dl" type="button">Download formatted SDC</button></div>
        ${`<div class="metric-row"><div class="metric"><div class="m-num">${res.warnings}</div><div class="m-label">warnings</div></div>
        <div class="metric"><div class="m-num">${res.fixed}</div><div class="m-label">fixed</div></div>
        <div class="metric"><div class="m-num">${res.line_count_original}</div><div class="m-label">lines in</div></div>
        <div class="metric"><div class="m-num">${res.line_count_formatted}</div><div class="m-label">lines out</div></div></div>`}
        <pre class="mono" style="font-size:12px;color:var(--text-secondary);background:var(--bg-secondary);border:1px solid var(--border-subtle);border-radius:var(--radius-md);padding:14px;overflow-x:auto;white-space:pre-wrap">${esc(res.formatted_text)}</pre>`;
      const ld = $("#lint-dl");
      if (ld) ld.addEventListener("click", () => dl("linted.sdc", res.formatted_text, "text/plain"));
    } catch (e) { toast("Lint failed", true); }
  });
}

/* ── Converter ──────────────────────────────────────────────────────────── */
function wireConverter(main) {
  const inp = $("#conv-in");
  inp.addEventListener("input", () => App.state.convIn = inp.value);
  let last = null; // last successful conversion {fmt, text}
  const run = async (fmt) => {
    if (!inp.value.trim()) { toast("Paste SDC to convert", true); return; }
    try {
      const res = await post("/api/convert", { sdc: inp.value, format: fmt });
      const text = res.text || JSON.stringify(res.data, null, 2);
      $("#conv-out").textContent = text;
      last = { fmt, text };
      const cdl = $("#conv-dl");
      if (cdl) cdl.disabled = false;
    } catch (e) { toast("Conversion failed", true); }
  };
  $("#conv-run").addEventListener("click", () => run("json"));
  $("#conv-run-yaml").addEventListener("click", () => run("yaml"));
  const cdl = $("#conv-dl");
  if (cdl) cdl.addEventListener("click", () => {
    if (!last) { toast("Convert an SDC first", true); return; }
    dl(`sdc_converted.${last.fmt}`, last.text,
       last.fmt === "yaml" ? "application/x-yaml" : "application/json");
  });
}

/* ── Corners ────────────────────────────────────────────────────────────── */
const CORNER_PRESETS = {
  CLASSIC_3: [
    { name: "WORST_SSG_0P72V_M40C", operating_condition: "SSG_0P72V_M40C", voltage: 0.72, temperature: -40.0, process_type: "SSG", derate_cell_early: 1.08, derate_cell_late: 0.92, derate_net_early: 1.02, derate_net_late: 0.98, uncertainty_scale: 1.2 },
    { name: "TYPICAL_TT_0P80V_25C", operating_condition: "TT_0P80V_25C", voltage: 0.80, temperature: 25.0, process_type: "TT", derate_cell_early: 1.04, derate_cell_late: 0.96, derate_net_early: 1.01, derate_net_late: 0.99, uncertainty_scale: 1.0 },
    { name: "BEST_FFG_0P88V_125C", operating_condition: "FFG_0P88V_125C", voltage: 0.88, temperature: 125.0, process_type: "FFG", derate_cell_early: 1.02, derate_cell_late: 0.98, derate_net_early: 1.0, derate_net_late: 1.0, uncertainty_scale: 0.8 },
  ],
  INDUSTRIAL_5: [
    { name: "WORST_SSG_0P72V_M40C", operating_condition: "SSG_0P72V_M40C", voltage: 0.72, temperature: -40.0, process_type: "SSG", derate_cell_early: 1.08, derate_cell_late: 0.92, derate_net_early: 1.02, derate_net_late: 0.98, uncertainty_scale: 1.2 },
    { name: "TYPICAL_TT_0P80V_25C", operating_condition: "TT_0P80V_25C", voltage: 0.80, temperature: 25.0, process_type: "TT", derate_cell_early: 1.04, derate_cell_late: 0.96, derate_net_early: 1.01, derate_net_late: 0.99, uncertainty_scale: 1.0 },
    { name: "BEST_FFG_0P88V_125C", operating_condition: "FFG_0P88V_125C", voltage: 0.88, temperature: 125.0, process_type: "FFG", derate_cell_early: 1.02, derate_cell_late: 0.98, derate_net_early: 1.0, derate_net_late: 1.0, uncertainty_scale: 0.8 },
    { name: "SSG_0P65V_M40C", operating_condition: "SSG_0P65V_M40C", voltage: 0.65, temperature: -40.0, process_type: "SSG", derate_cell_early: 1.10, derate_cell_late: 0.90, derate_net_early: 1.03, derate_net_late: 0.97, uncertainty_scale: 1.3 },
    { name: "FFG_0P95V_125C", operating_condition: "FFG_0P95V_125C", voltage: 0.95, temperature: 125.0, process_type: "FFG", derate_cell_early: 1.01, derate_cell_late: 0.99, derate_net_early: 1.0, derate_net_late: 1.0, uncertainty_scale: 0.7 },
  ],
  FULL_8: [
    { name: "WORST_SSG_0P72V_M40C", operating_condition: "SSG_0P72V_M40C", voltage: 0.72, temperature: -40.0, process_type: "SSG", derate_cell_early: 1.08, derate_cell_late: 0.92, derate_net_early: 1.02, derate_net_late: 0.98, uncertainty_scale: 1.2 },
    { name: "TYPICAL_TT_0P80V_25C", operating_condition: "TT_0P80V_25C", voltage: 0.80, temperature: 25.0, process_type: "TT", derate_cell_early: 1.04, derate_cell_late: 0.96, derate_net_early: 1.01, derate_net_late: 0.99, uncertainty_scale: 1.0 },
    { name: "BEST_FFG_0P88V_125C", operating_condition: "FFG_0P88V_125C", voltage: 0.88, temperature: 125.0, process_type: "FFG", derate_cell_early: 1.02, derate_cell_late: 0.98, derate_net_early: 1.0, derate_net_late: 1.0, uncertainty_scale: 0.8 },
    { name: "SSG_0P65V_M40C", operating_condition: "SSG_0P65V_M40C", voltage: 0.65, temperature: -40.0, process_type: "SSG", derate_cell_early: 1.10, derate_cell_late: 0.90, derate_net_early: 1.03, derate_net_late: 0.97, uncertainty_scale: 1.3 },
    { name: "FFG_0P95V_125C", operating_condition: "FFG_0P95V_125C", voltage: 0.95, temperature: 125.0, process_type: "FFG", derate_cell_early: 1.01, derate_cell_late: 0.99, derate_net_early: 1.0, derate_net_late: 1.0, uncertainty_scale: 0.7 },
    { name: "SS_0P72V_125C", operating_condition: "SS_0P72V_125C", voltage: 0.72, temperature: 125.0, process_type: "SS", derate_cell_early: 1.06, derate_cell_late: 0.94, derate_net_early: 1.02, derate_net_late: 0.98, uncertainty_scale: 1.1 },
    { name: "FF_0P88V_M40C", operating_condition: "FF_0P88V_M40C", voltage: 0.88, temperature: -40.0, process_type: "FF", derate_cell_early: 1.03, derate_cell_late: 0.97, derate_net_early: 1.0, derate_net_late: 1.0, uncertainty_scale: 0.9 },
    { name: "TT_0P80V_0C", operating_condition: "TT_0P80V_0C", voltage: 0.80, temperature: 0.0, process_type: "TT", derate_cell_early: 1.04, derate_cell_late: 0.96, derate_net_early: 1.01, derate_net_late: 0.99, uncertainty_scale: 1.0 },
  ],
};

function wireCorners(main) {
  $("#corner-load").addEventListener("click", async () => {
    const preset = CORNER_PRESETS[$("#corner-preset").value] || [];
    try {
      const res = await post("/api/corners", { corners: preset });
      const errs = (res.errors || []).length;
      $("#corner-out").innerHTML = `
        ${errs ? `<div class="err err-invalid"><span class="e-kind">Invalid</span><span class="err-msg">${esc(errs)} corner(s) failed validation</span></div>` : ""}
        <div class="metric-row"><div class="metric"><div class="m-num">${res.corners.length}</div><div class="m-label">corners</div></div></div>
        <div style="margin:8px 0"><button class="btn btn-sm" id="corner-dl" type="button">Export JSON</button></div>
        <table class="tbl"><thead><tr><th>Name</th><th>Op cond</th><th>V</th><th>T</th><th>Process</th><th>U-scale</th></tr></thead><tbody>
        ${res.corners.map(c => `<tr><td class="mono">${esc(c.name)}</td><td class="mono">${esc(c.operating_condition)}</td><td class="num">${c.voltage}</td><td class="num">${c.temperature}</td><td>${esc(c.process_type)}</td><td class="num">${c.uncertainty_scale}</td></tr>`).join("")}
        </tbody></table>`;
      const cdl = $("#corner-dl");
      if (cdl) cdl.addEventListener("click", () => dl("corners.json", JSON.stringify(res.corners, null, 2), "application/json"));
    } catch (e) { toast("Corner validation failed", true); }
  });
}

/* ── MMC ────────────────────────────────────────────────────────────────── */
function wireMMC(main) {
  const cornersPayload = () => CORNER_PRESETS.CLASSIC_3.map(c => ({ name: c.name, operating_condition: c.operating_condition, voltage: c.voltage, temperature: c.temperature, process_type: c.process_type, derate_cell_early: c.derate_cell_early, derate_cell_late: c.derate_cell_late, derate_net_early: c.derate_net_early, derate_net_late: c.derate_net_late, uncertainty_scale: c.uncertainty_scale }));
  $("#mmc-run").addEventListener("click", async () => {
    const clk = ($("#mmc-clock").value || "clk_core clk 5.0").trim().split(/\s+/);
    const design = ($("#mmc-design").value || "MY_DESIGN").trim();
    const template = () => ({ design_name: design, clocks: [{ name: clk[0], port: clk[1] || "clk", period: parseFloat(clk[2] || 5.0) }] });
    try {
      const res = await post("/api/mmc", { template: template(), corners: cornersPayload() });
      let h = `<div class="metric-row"><div class="metric"><div class="m-num">${res.names.length}</div><div class="m-label">corners</div></div>
        <div class="metric"><div class="m-num">${res.check.errors}</div><div class="m-label">errors</div></div>
        <div class="metric"><div class="m-num">${res.check.warnings}</div><div class="m-label">warnings</div></div></div>
        <div style="margin:8px 0"><button class="btn btn-sm" id="mmc-zip" type="button">📦 Download all (.zip)</button></div>`;
      res.names.forEach((name, i) => {
        h += accordion(`SDC — ${name}`,
          `<div style="margin-bottom:6px"><button class="btn btn-sm" data-cdl="${i}" type="button">Download .sdc</button></div>
           <pre class="mono" style="font-size:11.5px;white-space:pre-wrap;color:var(--text-secondary);margin:0">${esc(res.sdcs[name])}</pre>`);
      });
      if (res.diffs && res.diffs.length) {
        h += `<div class="section-title">Corner diffs</div>`;
        res.diffs.forEach(d => {
          const changed = d.lines.filter(l => l.line_type === "changed").length;
          const added = d.lines.filter(l => l.line_type === "added").length;
          const removed = d.lines.filter(l => l.line_type === "removed").length;
          h += accordion(`${d.pair[0]} vs ${d.pair[1]} — ${changed} changed, ${added} added, ${removed} removed`,
            `<pre class="mono" style="font-size:11px;white-space:pre-wrap;color:var(--text-secondary);margin:0">${esc(d.lines.map(l => `${l.line_type === "removed" ? "-" : l.line_type === "added" ? "+" : l.line_type === "changed" ? "~" : " "} ${l.text_a || l.text_b || ""}`).join("\n"))}</pre>`);
        });
      }
      $("#mmc-out").innerHTML = h;
      const z = $("#mmc-zip");
      if (z) z.addEventListener("click", async () => {
        try {
          const r = await fetch("/api/mmc/zip", { method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ template: template(), corners: cornersPayload() }) });
          if (!r.ok) { toast("ZIP generation failed", true); return; }
          const b = await r.blob();
          const a = document.createElement("a");
          a.href = URL.createObjectURL(b); a.download = `${design}_corners.zip`; a.click();
          setTimeout(() => URL.revokeObjectURL(a.href), 1000);
          toast(`Downloaded ${design}_corners.zip`);
        } catch (e2) { toast("ZIP generation failed", true); }
      });
      main.querySelectorAll("[data-cdl]").forEach(btn => {
        btn.addEventListener("click", () => {
          const name = res.names[+btn.dataset.cdl];
          if (name) dl(`${name}.sdc`, res.sdcs[name], "text/plain");
        });
      });
    } catch (e) { toast("MMC generation failed", true); }
  });
}

/* ── Rules ──────────────────────────────────────────────────────────────── */
function wireRules(main) {
  main.querySelectorAll("[data-seg]").forEach(btn => {
    btn.addEventListener("click", () => { App.state.ruleFilter = btn.dataset.seg; route(); });
  });
  const rj = $("#rules-dl-json");
  if (rj) rj.addEventListener("click", () => {
    dl("sdc_rules.json", JSON.stringify(App.state.rules || [], null, 2), "application/json");
  });
  const rm = $("#rules-dl-md");
  if (rm) rm.addEventListener("click", () => {
    const md = (App.state.rules || []).map(r =>
      `### ${r.code} — ${r.short_name} (${r.severity})\n\n${r.description}${r.why_matters ? `\n\nWhy: ${r.why_matters}` : ""}`).join("\n\n");
    dl("sdc_rules.md", md, "text/markdown");
  });
}

/* ── Test Drive ─────────────────────────────────────────────────────────── */
const TD_SAMPLES = {
  good: "set sdc_version 2.2\ncreate_clock -name clk_core -period 5.0 [get_ports clk]\nset_clock_uncertainty -setup 0.15 [get_clocks clk_core]\nset_input_delay -max 1.0 -min 0.3 -clock clk_core [all_inputs]\nset_output_delay -max 1.5 -min 0.5 -clock clk_core [all_outputs]\n",
  bad: "set_input_delay -max 6.0 -clock missing_clk [get_ports din]\ncreate_clock -name dupe -period 5.0 [get_ports a]\ncreate_clock -name dupe -period 10.0 [get_ports b]\ncreate_generated_clock -name bad_gen -divide_by 2 [get_pins g/A]\n",
  multi: "create_clock -name clk_a -period 5.0 [get_ports clk_a]\ncreate_clock -name clk_b -period 7.5 [get_ports clk_b]\nset_clock_groups -asynchronous -group [get_clocks clk_a] -group [get_clocks clk_b]\n",
  generated: "create_clock -name clk -period 5.0 [get_ports clk]\ncreate_generated_clock -name div2 -divide_by 2 -master_clock clk [get_pins u0/o]\ncreate_generated_clock -name div4 -divide_by 2 -master_clock div2 [get_pins u0/o2]\n",
};
function wireTestDrive(main) {
  $("#td-run").addEventListener("click", async () => {
    const sdc = TD_SAMPLES[$("#td-sample").value] || "";
    try {
      const res = await post("/api/analyze", { sdc });
      App.state.sdc = sdc;
      App.state.filename = `sample_${$("#td-sample").value}.sdc`;
      App.state.analysis = res;
      adoptAnalysis(res, { sdc, netlist: "", filename: App.state.filename,
                           name: `sample_${$("#td-sample").value}` });
      App.state.filters = { sev: "All", rule: "All", q: "" };
      route();
    } catch (e) { toast("Analysis failed", true); }
  });
  const tdl = $("#td-dl");
  if (tdl) tdl.addEventListener("click", () => {
    if (!App.state.analysis) { toast("Run a sample first", true); return; }
    dl("sample_results.json", JSON.stringify(App.state.analysis, null, 2), "application/json");
  });
}

/* ── Feedback ───────────────────────────────────────────────────────────── */
function wireFeedback(main) {
  $("#fb-submit").addEventListener("click", async () => {
    const entry = {
      timestamp: new Date().toISOString(),
      feature: $("#fb-feature").value,
      rating: +$("#fb-rating").value,
      comment: $("#fb-comment").value || "",
      sdc_file: App.state.filename || "",
      results_summary: App.state.analysis ? `${(App.state.analysis.issues || []).filter(i => i.sev === "error").length} errors, ${(App.state.analysis.issues || []).filter(i => i.sev === "warning").length} warnings` : "no analysis",
    };
    try {
      await post("/api/feedback", entry);
      $("#fb-comment").value = "";
      toast("Feedback recorded — thank you");
    } catch (e) { toast("Could not save feedback", true); }
  });
}

/* ── Cross-page links (overview → clocks / validator) ──────────────────── */
function wireCrossLinks(main) {
  main.querySelectorAll('a[href^="#/"]').forEach(a => { /* default hash nav works */ });
}

boot();
