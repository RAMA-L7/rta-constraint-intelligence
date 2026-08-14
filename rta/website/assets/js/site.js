/* ═══════════════════════════════════════════════════════════════════════════
   Ṛta — Product Website JS
   Shared chrome injection · scroll reveals · mobile nav · hero terminal
   animation · silicon-graph canvas (Level-1 ambient) · methodology toggles
   ═══════════════════════════════════════════════════════════════════════════ */

(function () {
  "use strict";

  // Add the JS marker immediately so CSS can gate hidden states on it
  // (no-JS fallback keeps content visible).
  document.documentElement.classList.add("js");

  var REDUCED = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  // Depth-aware base: capability pages live in capabilities/ so shared chrome
  // links need a ../ prefix; every other page lives at the site root.
  var BASE = (window.location.pathname.indexOf("/capabilities/") !== -1) ? "../" : "";

  function rel(path) {
    if (path.indexOf("http") === 0 || path.charAt(0) === "#") return path;
    return BASE + path;
  }

  /* ── Shared header / footer injection ─────────────────────────────────── */
  var NAV_LINKS = [
    ["Platform", "platform.html"],
    ["Capabilities", "capabilities.html"],
    ["Benchmarks", "benchmarks.html"],
    ["Trust", "trust.html"],
    ["Docs", "docs.html"],
    ["Release", "release.html"],
  ];
  var FOOTER_GROUPS = [
    ["Product", [
      ["Platform", "platform.html"],
      ["Capabilities", "capabilities.html"],
      ["Benchmarks", "benchmarks.html"],
      ["Release v1.3.0", "release.html"],
    ]],
    ["Engineering", [
      ["Trust Center", "trust.html"],
      ["Docs", "docs.html"],
      ["Support boundary", "trust.html#boundary"],
      ["Known limitations", "trust.html#limitations"],
    ]],
    ["Resources", [
      ["GitHub", "https://github.com/RAMA-L7/rta-constraint-intelligence"],
      ["Architecture", "docs/product/PRODUCT_EXPERIENCE_ARCHITECTURE.md"],
      ["Design system", "docs/product/VISUAL_DESIGN_SYSTEM.md"],
      ["Changelog", "CHANGELOG.md"],
    ]],
  ];

  function brandSvg() {
    return '<svg width="26" height="26" viewBox="0 0 16 16" fill="none" stroke="#38BDF8" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
      + '<path d="M5.5 2.5H4.2A1.7 1.7 0 0 0 2.5 4.2v2.6A1.7 1.7 0 0 1 .8 8a1.7 1.7 0 0 1 1.7 1.2v2.6a1.7 1.7 0 0 0 1.7 1.7h1.3"/>'
      + '<path d="M10.5 2.5h1.3a1.7 1.7 0 0 1 1.7 1.7v2.6A1.7 1.7 0 0 0 15.2 8a1.7 1.7 0 0 0-1.7 1.2v2.6a1.7 1.7 0 0 1-1.7 1.7h-1.3"/>'
      + '<path d="M8 3v2M8 7.2v1.6M8 11v2" opacity="0.5"/></svg>';
  }

  function currentPage() {
    var p = (window.location.pathname.split("/").pop() || "index.html").toLowerCase();
    if (p === "" || p === "/") p = "index.html";
    return p;
  }

  // Capability subpages should keep the Capabilities nav item highlighted.
  function isCapabilitySubpage() {
    return window.location.pathname.indexOf("/capabilities/") !== -1;
  }

  function renderHeader() {
    var el = document.getElementById("site-header");
    if (!el) return;
    var page = currentPage();
    var sub = isCapabilitySubpage();
    var links = NAV_LINKS.map(function (l) {
      var active = (l[1] === page) || (sub && l[0] === "Capabilities")
        ? ' class="active" aria-current="page"' : "";
      return '<a href="' + rel(l[1]) + '"' + active + ">" + l[0] + "</a>";
    }).join("");
    el.innerHTML =
      '<div class="container-wide nav">'
      + '<a class="brand" href="' + rel("index.html") + '" aria-label="Ṛta home">' + brandSvg()
      +   '<span>Ṛta<span class="brand-sub">Bringing order to timing intent with deterministic precision</span></span></a>'
      + '<button class="nav-burger" aria-label="Toggle navigation" aria-expanded="false" aria-controls="nav-links">☰</button>'
      + '<nav class="nav-links" id="nav-links">' + links      + '<a class="btn btn--primary btn--sm nav-cta" href="http://localhost:8501/" title="Run `rta web` (or `rta web`) to start the workspace on port 8501">Launch Ṛta ↗</a>'
      + '</nav></div>';
    var burger = el.querySelector(".nav-burger");
    var navLinks = el.querySelector(".nav-links");
    burger.addEventListener("click", function () {
      var open = navLinks.classList.toggle("open");
      burger.setAttribute("aria-expanded", open ? "true" : "false");
    });
  }

  function renderFooter() {
    var el = document.getElementById("site-footer");
    if (!el) return;
    var cols = FOOTER_GROUPS.map(function (g) {
      var items = g[1].map(function (l) {
        var target = l[1].indexOf("http") === 0 ? ' target="_blank" rel="noopener"' : "";
        return '<a href="' + rel(l[1]) + '"' + target + ">" + l[0] + "</a>";
      }).join("");
      return '<div><h4>' + g[0] + "</h4>" + items + "</div>";
    }).join("");
    el.innerHTML =
      '<div class="container">'
      + '<div class="footer-grid">'
      +   '<div><a class="brand" href="' + rel("index.html") + '">' + brandSvg() + '<span>Ṛta</span></a>'
      +     '<p style="color:var(--text-secondary);font-size:13.5px;max-width:34ch;margin-top:12px">'
      +     "Ṛta brings order to timing intent, transforming constraints into trusted engineering knowledge through deterministic precision.</p>"
      +     '<div style="display:flex;gap:8px;margin-top:14px;flex-wrap:wrap">'
      +       '<span class="badge badge--success"><span class="sq"></span>Deterministic</span>'
      +       '<span class="badge badge--accent"><span class="sq"></span>Offline-capable</span>'
      +       '<span class="badge badge--muted"><span class="sq"></span>No LLM required</span>'
      +     "</div></div>"
      +   cols
      + "</div>"
      + '<div class="footer-bottom">'
      +   '<span>Ṛta v1.5.8 · RC_READY_WITH_KNOWN_LIMITATIONS</span>'
      +   '<span>Validates SDC constraint quality — not an STA timing signoff tool.</span>'
      + "</div></div>";
  }

  /* ── Scroll reveal ────────────────────────────────────────────────────── */
  function initReveals() {
    if (REDUCED || !("IntersectionObserver" in window)) {
      document.querySelectorAll(".reveal").forEach(function (el) { el.classList.add("in"); });
      return;
    }
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (en) {
        if (en.isIntersecting) { en.target.classList.add("in"); io.unobserve(en.target); }
      });
    }, { threshold: 0.12, rootMargin: "0px 0px -40px 0px" });
    document.querySelectorAll(".reveal").forEach(function (el) { io.observe(el); });
  }

  /* ── Methodology expanders ────────────────────────────────────────────── */
  function initMethodology() {
    document.querySelectorAll("[data-method]").forEach(function (btn) {
      btn.setAttribute("aria-controls", btn.getAttribute("data-method"));
      btn.addEventListener("click", function () {
        var target = document.getElementById(btn.getAttribute("data-method"));
        if (!target) return;
        var open = target.classList.toggle("open");
        btn.setAttribute("aria-expanded", open ? "true" : "false");
        btn.textContent = open ? "Hide methodology" : "Methodology";
      });
    });
  }

  /* ── Hero terminal typing animation ───────────────────────────────────── */
  var HERO_LINES = [
    { cls: "cmd", text: "$ rta check design.sdc" },
    { cls: "dim", text: "preprocess · 31 constraints · tcl vars resolved" },
    { cls: "ok", text: "✓ clocks: 3 (1 primary, 2 generated)" },
    { cls: "ok", text: "✓ references: 41/41 resolved" },
    { cls: "dim", text: "clock relations: 3 pairs inferred" },
    { cls: "warn", text: "▲ SDC-030  missing input delay on data_in[7:0]" },
    { cls: "err", text: "✗ SDC-008  input delay ≥ clock period (clk_core)" },
    { cls: "dim", text: "coverage: 86% inputs · 72% outputs" },
    { cls: "dim", text: "readiness: REVIEW_REQUIRED" },
    { cls: "ok", text: "CONSTRAINT QUALITY ASSESSED — 2 errors, 1 warning" },
  ];

  function initHeroTerminal() {
    var body = document.getElementById("hero-terminal-body");
    if (!body) return;
    if (REDUCED) {
      body.innerHTML = HERO_LINES.map(function (l) {
        return '<div class="term-line ' + l.cls + '">' + escapeHtml(l.text) + "</div>";
      }).join("") + '<div class="term-line term-cursor"></div>';
      return;
    }
    var lines = [];
    var li = 0;
    body.innerHTML = "";
    var delay = 260;
    function typeLine() {
      if (li >= HERO_LINES.length) {
        body.appendChild(mkEl('<div class="term-line term-cursor"></div>'));
        return;
      }
      var line = HERO_LINES[li];
      var div = document.createElement("div");
      div.className = "term-line " + line.cls;
      body.appendChild(div);
      var text = line.text, i = 0;
      var t = setInterval(function () {
        div.textContent = text.slice(0, ++i);
        if (i >= text.length) { clearInterval(t); li++; setTimeout(typeLine, delay); }
      }, 16);
    }
    setTimeout(typeLine, 500);
  }

  /* ── Silicon graph canvas (Level-1 ambient topology) ──────────────────── */
  function initSiliconCanvas() {
    var canvas = document.getElementById("silicon-canvas");
    if (!canvas || REDUCED) return;
    var width = canvas.clientWidth || 900;
    var height = canvas.clientHeight || 420;

    // deterministic pseudo-random placement (stable per page load)
    function rng(seed) { return function () { seed = (seed * 9301 + 49297) % 233280; return seed / 233280; }; }
    var rand = rng(7);

    var nodes = [];
    var nodeCount = Math.min(26, Math.max(12, Math.floor(width / 70)));
    for (var i = 0; i < nodeCount; i++) {
      nodes.push({
        x: 8 + rand() * (width - 16),
        y: 10 + rand() * (height - 20),
        kind: rand() < 0.28 ? "primary" : (rand() < 0.5 ? "generated" : "plain"),
        dr: 0.4 + rand() * 0.9,
      });
    }
    var edges = [];
    for (var a = 0; a < nodes.length; a++) {
      for (var b = a + 1; b < nodes.length; b++) {
        var dx = nodes[a].x - nodes[b].x, dy = nodes[a].y - nodes[b].y;
        var d = Math.sqrt(dx * dx + dy * dy);
        if (d < width * 0.24 && rand() < 0.5) {
          // 4th slot: "flow" flag — a subset of edges carry the analysis-flow
          // animation so the topology reads as live constraint routing.
          edges.push([a, b, d, (a * 7 + b * 13) % 3 === 0]);
          if (edges.length > 34) break;
        }
      }
      if (edges.length > 34) break;
    }

    var svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
    svg.setAttribute("viewBox", "0 0 " + width + " " + height);
    svg.setAttribute("preserveAspectRatio", "xMidYMid slice");
    svg.setAttribute("aria-hidden", "true");

    edges.forEach(function (e, i) {
      var p = document.createElementNS("http://www.w3.org/2000/svg", "path");
      var n1 = nodes[e[0]], n2 = nodes[e[1]];
      var mx = (n1.x + n2.x) / 2, my = (n1.y + n2.y) / 2;
      p.setAttribute("d", "M" + n1.x.toFixed(1) + " " + n1.y.toFixed(1) + " Q " + mx.toFixed(1) + " " + (my - 18).toFixed(1) + " " + n2.x.toFixed(1) + " " + n2.y.toFixed(1));
      p.setAttribute("class", e[3] ? "edge-path flow" : "edge-path");
      if (e[3]) p.style.animationDelay = "-" + (i % 16) + "s"; // desynchronize flow streams
      svg.appendChild(p);
    });
    nodes.forEach(function (n, i) {
      var c = document.createElementNS("http://www.w3.org/2000/svg", "circle");
      c.setAttribute("cx", n.x.toFixed(1));
      c.setAttribute("cy", n.y.toFixed(1));
      c.setAttribute("r", n.kind === "primary" ? 4.2 : 3);
      c.setAttribute("class", "node-dot " + n.kind);
      c.style.animationDelay = "-" + ((i * 0.9) % 8).toFixed(1) + "s";
      svg.appendChild(c);
    });
    canvas.appendChild(svg);

    // clock-edge pulses along 2–3 distinct edges (halo + core), paused when the
    // tab is hidden so background motion never burns cycles invisibly.
    if (edges.length) {
      var pulses = [];
      var used = {}, tries = 0;
      while (pulses.length < 3 && tries < 24) {
        tries++;
        var idx = Math.floor(rand() * edges.length);
        if (used[idx]) continue;
        used[idx] = true;
        var e = edges[idx];
        var halo = document.createElementNS("http://www.w3.org/2000/svg", "circle");
        halo.setAttribute("r", "6");
        halo.setAttribute("class", "pulse-halo");
        var core = document.createElementNS("http://www.w3.org/2000/svg", "circle");
        core.setAttribute("r", "2.6");
        core.setAttribute("class", "pulse");
        svg.appendChild(halo);
        svg.appendChild(core);
        pulses.push({
          a: nodes[e[0]], b: nodes[e[1]],
          dur: 6000 + pulses.length * 2200,
          phase: pulses.length * 2400,
          halo: halo, core: core,
        });
      }
      var rafId = 0;
      function renderPulses(now) {
        pulses.forEach(function (p) {
          var t = ((now + p.phase) % p.dur) / p.dur;
          var x = p.a.x + (p.b.x - p.a.x) * t;
          var y = p.a.y + (p.b.y - p.a.y) * t;
          p.halo.setAttribute("cx", x.toFixed(1));
          p.halo.setAttribute("cy", y.toFixed(1));
          p.core.setAttribute("cx", x.toFixed(1));
          p.core.setAttribute("cy", y.toFixed(1));
        });
        rafId = requestAnimationFrame(renderPulses);
      }
      function pausePulses() {
        if (document.hidden) { cancelAnimationFrame(rafId); rafId = 0; }
        else if (!rafId) { rafId = requestAnimationFrame(renderPulses); }
      }
      document.addEventListener("visibilitychange", pausePulses);
      renderPulses(performance.now());
    }
  }

  function escapeHtml(s) {
    return String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  }
  function mkEl(html) {
    var t = document.createElement("template");
    t.innerHTML = html;
    return t.content.firstChild;
  }

  document.addEventListener("DOMContentLoaded", function () {
    renderHeader();
    renderFooter();
    initReveals();
    initMethodology();
    initHeroTerminal();
    initSiliconCanvas();
  });
})();
