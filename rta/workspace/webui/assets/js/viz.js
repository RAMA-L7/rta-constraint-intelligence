/* ═══════════════════════════════════════════════════════════════════════════
   Ṛta — viz.js
   Technical visualizations:
     - Background canvas (netlist topology, routing arcs, analysis pulses)
     - Clock hierarchy SVG (primary → generated branches, pulse propagation)
     - Clock relation matrix (symbol + label + color)
     - Bus coverage strips (bit-level constrained / partial / missing)
     - Readiness dimension rail
   All labels escaped; reduced-motion respected; animation paused when hidden.
   ═══════════════════════════════════════════════════════════════════════════ */

import { esc } from "./theme.js";

/* ═══════════════════════════════════════════════════════════════════════════
   BACKGROUND CANVAS — sparse netlist topology
   Layer 2 (nodes/edges) + Layer 3 (routing) + Layer 4 (pulses).
   Nodes hold position; only pulses and subtle idle illumination move.
   ═══════════════════════════════════════════════════════════════════════════ */

export function initBackground(container) {
  if (!container) return;
  // container may be a <canvas> directly or a wrapper div; normalize to a canvas
  let canvas = container.tagName === "CANVAS" ? container : null;
  if (!canvas) {
    canvas = document.createElement("canvas");
    canvas.id = "bg-canvas";
    canvas.setAttribute("aria-hidden", "true");
    container.appendChild(canvas);
  }
  const ctx = canvas.getContext("2d");
  if (!ctx) return;
  const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  let w = 0, h = 0, raf = 0, running = true;
  const nodes = [];
  const edges = [];
  const pulses = [];

  function resize() {
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    w = canvas.clientWidth; h = canvas.clientHeight;
    canvas.width = Math.max(1, Math.floor(w * dpr));
    canvas.height = Math.max(1, Math.floor(h * dpr));
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  }

  function build() {
    nodes.length = 0; edges.length = 0; pulses.length = 0;
    const area = w * h;
    const nNodes = Math.min(90, Math.max(28, Math.round(area / 26000)));
    const margin = 60;
    for (let i = 0; i < nNodes; i++) {
      nodes.push({
        x: margin + Math.random() * (w - margin * 2),
        y: margin + Math.random() * (h - margin * 2),
        r: 1.8 + Math.random() * 2.0,
        phase: Math.random() * Math.PI * 2,
        speed: 0.15 + Math.random() * 0.35,
        leaf: Math.random() < 0.35,
      });
    }
    // connect nearby nodes into sparse topology (routing-like arcs)
    for (let i = 0; i < nodes.length; i++) {
      for (let j = i + 1; j < nodes.length; j++) {
        const a = nodes[i], b = nodes[j];
        const d = Math.hypot(a.x - b.x, a.y - b.y);
        if (d < 150 && Math.random() < 0.28) {
          edges.push({ a, b, len: d });
        }
      }
    }
    // occasional pulse travels an edge
    for (const e of edges) {
      if (Math.random() < 0.12) pulses.push({
        e, t: Math.random(), speed: 0.0035 + Math.random() * 0.004,
        life: true,
      });
    }
  }

  // Phase 17 gap fix (VISUAL_IDENTITY_DIRECTION §6): the topology must be
  // *visible when observed* but never compete with data. Opacity/size values
  // below are raised so nodes/arcs/pulses read on the light surface. Colors
  // mirror the light tokens (text_primary #18181B, accent_secondary #2563EB)
  // by design; a future dark-first pass must re-derive these from the tokens.
  let last = 0;
  function frame(ts) {
    if (!running) return;
    if (ts - last > 34) { // ~30fps cap — enough for subtle ambient motion
      last = ts;
      draw(ts);
    }
    raf = requestAnimationFrame(frame);
  }

  function draw(ts) {
    ctx.clearRect(0, 0, w, h);
    const t = ts / 1000;
    // edges (layer 3)
    ctx.lineWidth = 1;
    for (const e of edges) {
      const a = e.a, b = e.b;
      ctx.strokeStyle = "rgba(24,24,27,0.16)";
      ctx.beginPath(); ctx.moveTo(a.x, a.y);
      // slight curve for routing feel
      const mx = (a.x + b.x) / 2, my = (a.y + b.y) / 2 - e.len * 0.08;
      ctx.quadraticCurveTo(mx, my, b.x, b.y); ctx.stroke();
    }
    // pulses (layer 4)
    for (const p of pulses) {
      if (!p.life) continue;
      p.t += p.speed * (1 + Math.sin(t * 0.1) * 0.3);
      if (p.t >= 1) { p.t = 0; }
      const a = p.e.a, b = p.e.b;
      const mx = (a.x + b.x) / 2, my = (a.y + b.y) / 2 - p.e.len * 0.08;
      const u = p.t;
      const uu = 1 - u;
      const x = uu * uu * a.x + 2 * uu * u * mx + u * u * b.x;
      const y = uu * uu * a.y + 2 * uu * u * my + u * u * b.y;
      const fade = Math.sin(p.t * Math.PI);
      ctx.fillStyle = `rgba(37,99,235,${0.62 * fade})`;
      ctx.beginPath(); ctx.arc(x, y, 2.0, 0, Math.PI * 2); ctx.fill();
      // trailing glow
      ctx.fillStyle = `rgba(37,99,235,${0.16 * fade})`;
      ctx.beginPath(); ctx.arc(x, y, 5.5, 0, Math.PI * 2); ctx.fill();
    }
    // nodes (layer 2) — subtle idle illumination
    for (const n of nodes) {
      const glow = 0.35 + 0.3 * Math.sin(t * n.speed + n.phase);
      ctx.fillStyle = n.leaf
        ? `rgba(37,99,235,${0.30 + 0.20 * glow})`
        : `rgba(113,113,122,${0.28 + 0.18 * glow})`;
      ctx.beginPath(); ctx.arc(n.x, n.y, n.r, 0, Math.PI * 2); ctx.fill();
    }
  }

  function pause() { running = false; cancelAnimationFrame(raf); }
  function resume() { if (running) return; running = true; raf = requestAnimationFrame(frame); }

  resize();
  if (!reduced) {
    build();
    raf = requestAnimationFrame(frame);
  } else {
    // static grid only — draw one frame of faint nodes/edges
    build();
    draw(performance.now());
  }
  window.addEventListener("resize", () => { resize(); if (reduced) draw(performance.now()); });
  document.addEventListener("visibilitychange", () => {
    if (document.hidden) pause(); else resume();
  });
}

/* ═══════════════════════════════════════════════════════════════════════════
   CLOCK HIERARCHY — SVG tree with explanatory pulse propagation
   ═══════════════════════════════════════════════════════════════════════════ */

export function clockTreeHtml(clocks) {
  if (!clocks || !clocks.length) {
    return '<div class="empty"><div class="e-mark">// clocks</div><div class="e-title">No clocks discovered</div><p class="e-meaning">No create_clock / create_generated_clock commands were found in this constraint set.</p><p class="e-next">Add primary clocks first, then generated clocks derived from them.</p></div>';
  }
  // build parent→children map
  const byName = {};
  clocks.forEach(c => byName[c.name] = c);
  const children = {};
  clocks.forEach(c => { children[c.name] = []; });
  const roots = [];
  clocks.forEach(c => {
    const parentName = c.master_clock || c.master || "";
    if (parentName && byName[parentName]) children[parentName].push(c);
    else roots.push(c);
  });
  if (!roots.length && clocks.length) roots.push(clocks[0]);

  const ROWS = 56, COLS = 220, GAP_X = 30;
  const positions = {};
  let y = 40;
  function place(node, depth, maxDepth) {
    positions[node.name] = { x: 30 + depth * COLS, y };
    const kids = children[node.name] || [];
    if (kids.length) {
      const firstY = y;
      const childYs = [];
      kids.forEach(k => { y += ROWS; childYs.push(y); place(k, depth + 1, maxDepth); });
      positions[node.name].childYs = childYs;
      y = Math.max(y, firstY);
    }
  }
  roots.forEach(r => { place(r, 0, 0); y += ROWS; });
  const H = Math.max(220, y + 40);

  let svg = `<svg viewBox="0 0 900 ${H}" role="img" aria-label="Clock hierarchy">`;
  // edges
  for (const c of clocks) {
    const pos = positions[c.name];
    if (!pos) continue;
    const kids = children[c.name] || [];
    for (const k of kids) {
      const kp = positions[k.name];
      if (!kp) continue;
      const parentName = c.name;
      const isDerived = k.master_clock === parentName;
      svg += `<path class="ct-edge${isDerived ? " derived" : ""}" d="M${pos.x + 60} ${pos.y} C ${pos.x + 90} ${pos.y}, ${kp.x - 90} ${kp.y}, ${kp.x - 60} ${kp.y}"/>`;
      // pulse along derived edges
      if (isDerived) {
        svg += `<path class="ct-pulse" d="M${pos.x + 60} ${pos.y} C ${pos.x + 90} ${pos.y}, ${kp.x - 90} ${kp.y}, ${kp.x - 60} ${kp.y}"/>`;
      }
    }
  }
  // nodes
  for (const c of clocks) {
    const pos = positions[c.name];
    if (!pos) continue;
    const isRoot = !c.master_clock && !c.is_generated;
    const period = c.period != null ? `${Number(c.period).toFixed(2)} ns` : "—";
    const freq = c.period ? `${(1000 / c.period).toFixed(2)} MHz` : "";
    const meta = c.is_generated
      ? (c.divide_by ? `÷${c.divide_by}` : c.multiply_by ? `×${c.multiply_by}` : "gen") + " · " + period
      : period + (freq ? " · " + freq : "");
    svg += `<g class="ct-node${isRoot ? " primary" : ""}" data-clock="${esc(c.name)}" tabindex="0" role="button" aria-label="Clock ${esc(c.name)}">
      <rect class="n-glow" x="${pos.x - 66}" y="${pos.y - 14}" width="136" height="30" rx="6" opacity="0"/>
      <rect x="${pos.x - 60}" y="${pos.y - 11}" width="124" height="24" rx="5"/>
      <text class="n-name" x="${pos.x}" y="${pos.y + 1}" text-anchor="middle">${esc(c.name)}</text>
      <text class="n-meta" x="${pos.x}" y="${pos.y + 13}" text-anchor="middle">${esc(meta)}</text>
    </g>`;
  }
  svg += "</svg>";
  return `<div class="clock-tree">${svg}</div>`;
}

/* ═══════════════════════════════════════════════════════════════════════════
   RELATION MATRIX — symbol + label + color
   ═══════════════════════════════════════════════════════════════════════════ */

export function matrixHtml(clocks, pairs) {
  if (!clocks || clocks.length < 2) {
    return '<div class="empty"><div class="e-mark">// relations</div><div class="e-title">Relation matrix needs 2+ clocks</div><p class="e-meaning">Add at least two clocks to see inferred relationships.</p></div>';
  }
  const names = clocks.map(c => c.name);
  const lookup = {};
  (pairs || []).forEach(p => {
    const k1 = [p.clock_a, p.clock_b].sort().join("::");
    const k2 = [p.clock_b, p.clock_a].sort().join("::");
    lookup[k1] = p; lookup[k2] = p;
  });
  const relClass = {
    synchronous: "mx-sync", asynchronous: "mx-async",
    physically_exclusive: "mx-excl", logically_exclusive: "mx-excl",
  };
  const relLabel = {
    synchronous: "Synchronous", asynchronous: "Asynchronous",
    physically_exclusive: "Physically exclusive", logically_exclusive: "Logically exclusive",
  };
  let html = '<div class="matrix-wrap"><table class="matrix" role="grid"><thead><tr><th class="corner">Clock</th>';
  names.forEach(n => html += `<th>${esc(n)}</th>`);
  html += "</tr></thead><tbody>";
  names.forEach((a, i) => {
    html += `<tr><th class="corner">${esc(a)}</th>`;
    names.forEach((b, j) => {
      if (i === j) { html += `<td class="cell"><span style="opacity:.35">—</span></td>`; return; }
      const p = lookup[[a, b].sort().join("::")];
      if (!p) { html += `<td class="cell mx-unknown" title="Unknown relationship">·</td>`; return; }
      const cls = relClass[p.inferred_relation] || "mx-unknown";
      const label = relLabel[p.inferred_relation] || "Unknown";
      html += `<td class="cell ${cls}" title="${esc(p.reason || label)}" role="gridcell" aria-label="${esc(label)}">${esc(label)}</td>`;
    });
    html += "</tr>";
  });
  html += "</tbody></table></div>";
  html += '<div class="bus-legend"><span><span class="mx-sync">◆</span> Synchronous</span><span><span class="mx-async">✕</span> Asynchronous</span><span><span class="mx-excl">◈</span> Exclusive</span><span><span class="mx-unknown">·</span> Unknown</span></div>';
  return html;
}

/* ═══════════════════════════════════════════════════════════════════════════
   BUS COVERAGE — bit-level strips
   ═══════════════════════════════════════════════════════════════════════════ */

export function busStripHtml(name, msb, lsb, ranges) {
  // ranges: list of {lo, hi, status} where status ∈ c/p/u/x
  const width = Math.abs(msb - lsb) + 1;
  if (width > 256) {
    return `<div class="bus"><div class="bus-head"><span class="b-name">${esc(name)}</span><span class="b-status">${esc(width)} bits — aggregate view</span></div>
      <div class="bus-strip">${ranges.map(r => {
        const seg = (Math.abs(r.hi - r.lo) + 1) / width * 100;
        return `<div class="bus-bit ${r.status}" style="width:${seg}%" title="${esc(`${name}[${r.hi}:${r.lo}] — ${statusWord(r.status)}`)}"></div>`;
      }).join("")}</div></div>`;
  }
  const bits = new Array(width).fill("u");
  (ranges || []).forEach(r => {
    for (let b = Math.min(r.hi, r.lo); b <= Math.max(r.hi, r.lo); b++) {
      const idx = msb > lsb ? b - lsb : lsb - b;
      if (idx >= 0 && idx < width) bits[idx] = r.status;
    }
  });
  // compact: render runs of equal status
  const runs = [];
  let cur = { status: bits[0], lo: 0 };
  for (let i = 1; i <= bits.length; i++) {
    if (i === bits.length || bits[i] !== cur.status) { cur.hi = i - 1; runs.push(cur); cur = { status: bits[i], lo: i }; }
  }
  const segW = 100 / width;
  return `<div class="bus">
    <div class="bus-head"><span class="b-name">${esc(name)}</span>
    <span class="b-status mono">[${msb}:${lsb}]</span>
    <span class="b-status">${esc(width)} bits</span></div>
    <div class="bus-strip" aria-label="Bus coverage for ${escAttr(name)}">
      ${runs.map(r => {
        const w = (r.hi - r.lo + 1) * segW;
        return `<div class="bus-bit ${r.status}" style="width:${w}%" title="${esc(`${name}[${r.hi}:${r.lo}] — ${statusWord(r.status)}`)}"></div>`;
      }).join("")}
    </div>
  </div>`;
}

function statusWord(s) {
  return { c: "constrained", p: "partial", u: "unconstrained", x: "unknown" }[s] || s;
}

function escAttr(v) {
  return String(v == null ? "" : v).replace(/"/g, "&quot;").replace(/</g, "&lt;");
}

/* ═══════════════════════════════════════════════════════════════════════════
   READINESS RAIL — signature dimension stack
   ═══════════════════════════════════════════════════════════════════════════ */

export function readinessRail(readiness) {
  const dims = readiness.dimensions || {};
  const names = ["CLOCKS", "I/O", "EXCEPTIONS", "COVERAGE", "CONSISTENCY", "ANALYSIS_TRUST", "DESIGN_CONTEXT"];
  const cells = names.map(n => {
    const key = Object.keys(dims).find(k => k.toUpperCase() === n);
    const d = key ? dims[key] : null;
    const status = d ? d.status : "NOT_APPLICABLE";
    const color = { READY: "#34D399", READY_WITH_ADVISORIES: "#34D399", REVIEW_REQUIRED: "#FBBF24", BLOCKED: "#F87171", INSUFFICIENT_CONTEXT: "#94A3B8", NOT_APPLICABLE: "#475569" }[status] || "#68738A";
    const fill = { READY: 1, READY_WITH_ADVISORIES: 0.85, REVIEW_REQUIRED: 0.5, BLOCKED: 0.25, INSUFFICIENT_CONTEXT: 0.1, NOT_APPLICABLE: 0.05 }[status] || 0.1;
    const summary = d && d.summary ? d.summary : "";
    return `<div class="rdy-dim" data-dim="${esc(n)}" tabindex="0" role="button" title="${escAttr(summary)}">
      <div class="rd-name">${esc(n)}</div>
      <div class="rd-status"><span class="sdc-status sev-${color === "#34D399" ? "success" : color === "#FBBF24" ? "warning" : color === "#F87171" ? "error" : color === "#94A3B8" ? "unknown" : "muted"}"><span class="sh ${status === "REVIEW_REQUIRED" ? "tri" : status === "READY" ? "circ" : ""}"></span>${esc(status.replace(/_/g, " "))}</span></div>
      <div class="rd-bar"><div class="rd-fill" style="width:${fill * 100}%;background:${color}"></div></div>
    </div>`;
  }).join("");
  return `<div class="rdy-rail">${cells}</div>`;
}
