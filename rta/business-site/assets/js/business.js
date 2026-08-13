/* ═══════════════════════════════════════════════════════════════════════════
   Ṛta | Business Site JS
   Shared chrome injection · glass nav scroll state · scroll reveals ·
   animated counters · hero terminal typing · install-copy buttons ·
   lightbox-free page transitions
   ═══════════════════════════════════════════════════════════════════════════ */

(function () {
  "use strict";

  document.documentElement.classList.add("js");

  var REDUCED = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  // Depth-aware base: feature pages live in features/ so shared chrome links
  // need a ../ prefix; every other page lives at the site root.
  var BASE = (window.location.pathname.indexOf("/features/") !== -1) ? "../" : "";

  function rel(path) {
    if (path.indexOf("http") === 0 || path.charAt(0) === "#") return path;
    return BASE + path;
  }

  /* ── Live product facts (keep in sync with rta/evidence/manifest) ─────── */
  var FACTS = {
    version: "1.5.7",
    rules: 119,
    tests: 824,
    suites: 42,
    runners: 9,
    app: "https://rta-constraint-intelligence-294wudzqxdnhluyqk6eskp.streamlit.app/",
  };

  /* ── Shared nav / footer ───────────────────────────────────────────────── */
  var NAV_LINKS = [
    ["Features", "index.html#features"],
    ["Platform", "index.html#platform"],
    ["Why Ṛta", "index.html#why"],
    ["Install", "index.html#install"],
    ["Rules", "features/rules.html"],
  ];
  var FOOTER_GROUPS = [
    ["Capabilities", [
      ["SDC Validation", "features/validation.html"],
      ["Clock Intelligence", "features/clocks.html"],
      ["Design Context", "features/context.html"],
      ["Coverage", "features/coverage.html"],
      ["Interactions", "features/interactions.html"],
      ["Readiness & Gates", "features/readiness.html"],
    ]],
    ["Tools", [
      ["Generator", "features/generator.html"],
      ["Linter", "features/linter.html"],
      ["Converter", "features/converter.html"],
      ["Diff", "features/diff.html"],
      ["Batch", "features/batch.html"],
      ["Corners / MMC", "features/corners.html"],
    ]],
    ["Resources", [
      ["Rules Reference", "features/rules.html"],
      ["Advanced Rules", "features/advanced-rules.html"],
      ["GitHub", "https://github.com/RAMA-L7/rta-constraint-intelligence"],
      ["Docs", "https://github.com/RAMA-L7/rta-constraint-intelligence/tree/main/rta/docs"],
    ]],
  ];

  // Lockup logo in nav/footer; the square mark stays as the app icon / favicon.
  function brandImg(cls) {
    return '<img class="' + (cls || "brand-img") + '" src="' + rel("assets/img/rta-lockup.png") + '" alt="Ṛta logo">';
  }

  function renderHeader() {
    var el = document.getElementById("site-header");
    if (!el) return;
    var links = NAV_LINKS.map(function (l) {
      return '<a href="' + rel(l[1]) + '">' + l[0] + "</a>";
    }).join("");
    el.innerHTML =
      '<div class="nav-wrap" id="nav-wrap">'
      + '<div class="container-wide nav">'
      + '<a class="brand" href="' + rel("index.html") + '" aria-label="Ṛta home" title="Ṛta">' + brandImg() + "</a>"
      + '<button class="nav-burger" aria-label="Toggle navigation" aria-expanded="false" aria-controls="nav-links">☰</button>'
      + '<nav class="nav-links" id="nav-links">' + links
      + '<a class="btn btn--primary btn--sm nav-cta" href="' + FACTS.app + '" target="_blank" rel="noopener">Launch App ↗</a>'
      + "</nav></div></div>";
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
      '<div class="footer">'
      + '<div class="container">'
      + '<div class="footer-grid">'      + '<div><a class="brand" href="' + rel("index.html") + '" title="Ṛta">' + brandImg("brand-img brand-img--lg") + "</a>"
      +     '<p style="color:var(--text-secondary);font-size:13.5px;max-width:38ch;margin-top:14px">'
      +     "Ṛta brings order to timing intent, transforming constraints into trusted engineering knowledge through deterministic precision.</p>"
      +     '<div class="chip-row" style="margin-top:16px">'
      +       '<span class="badge badge--success"><span class="sq"></span>Deterministic</span>'
      +       '<span class="badge badge--accent"><span class="sq"></span>Offline-capable</span>'
      +       '<span class="badge badge--info"><span class="sq"></span>No LLM required</span>'
      +     "</div></div>"
      +   cols
      + "</div>"
      + '<div class="footer-bottom">'
      +   '<span>Ṛta v' + FACTS.version + ' · MIT License</span>'
      +   '<span>Validates SDC constraint quality, not an STA timing signoff tool.</span>'
      + "</div></div></div>";
  }

  /* ── Glass nav scroll state ───────────────────────────────────────────── */
  function initNavScroll() {
    var wrap = document.getElementById("nav-wrap");
    if (!wrap) return;
    function onScroll() {
      wrap.classList.toggle("scrolled", window.scrollY > 12);
    }
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
  }

  /* ── Scroll reveals ───────────────────────────────────────────────────── */
  function initReveals() {
    var els = document.querySelectorAll(".reveal, .reveal-scale, .reveal-left, .reveal-right, .reveal-zoom, .reveal-blur, .uline");
    if (REDUCED || !("IntersectionObserver" in window)) {
      els.forEach(function (el) { el.classList.add("in"); });
      return;
    }
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (en) {
        if (en.isIntersecting) { en.target.classList.add("in"); io.unobserve(en.target); }
      });
    }, { threshold: 0.12, rootMargin: "0px 0px -40px 0px" });
    els.forEach(function (el) { io.observe(el); });
  }

  /* ── Animated counters ────────────────────────────────────────────────── */
  function initCounters() {
    var els = document.querySelectorAll("[data-count]");
    if (!els.length) return;
    function animate(el) {
      var target = parseInt(el.getAttribute("data-count"), 10) || 0;
      if (REDUCED) { el.textContent = target.toLocaleString(); return; }
      var dur = 1400;
      var start = null;
      function frame(now) {
        if (!start) start = now;
        var t = Math.min((now - start) / dur, 1);
        var eased = 1 - Math.pow(1 - t, 3);
        el.textContent = Math.round(target * eased).toLocaleString();
        if (t < 1) requestAnimationFrame(frame);
      }
      requestAnimationFrame(frame);
    }
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (en) {
        if (en.isIntersecting) { animate(en.target); io.unobserve(en.target); }
      });
    }, { threshold: 0.4 });
    els.forEach(function (el) { io.observe(el); });
  }

  /* ── Hero terminal typing ─────────────────────────────────────────────── */
  var HERO_LINES = [
    '<span class="t-cmd">$ rta check design.sdc --netlist top.v --top soc_top</span>',
    '<span class="t-dim">preprocess · 43 constraints · tcl vars resolved</span>',
    '<span class="t-ok">✓ clocks: 4 (2 primary, 2 generated)</span>',
    '<span class="t-ok">✓ references: 61/61 resolved against netlist</span>',
    '<span class="t-dim">clock relations: 6 pairs · coverage: 94% inputs</span>',
    '<span class="t-warn">▲ SDC-151  reset tree rst_n has no timing exception</span>',
    '<span class="t-err">✗ SDC-008  input delay 9.0ns ≥ clock period</span>',
    '<span class="t-dim">readiness: REVIEW_REQUIRED · 2 errors · 1 warning</span>',
    '<span class="t-acc">CONSTRAINT QUALITY ASSESSED - exit 1</span>',
  ];

  function initHeroTerminal() {
    var body = document.getElementById("hero-terminal-body");
    if (!body) return;
    if (REDUCED) {
      body.innerHTML = HERO_LINES.map(function (l) {
        return '<div class="term-line">' + l + "</div>";
      }).join("");
      return;
    }
    var li = 0;
    body.innerHTML = "";
    function typeLine() {
      if (li >= HERO_LINES.length) {
        var cur = document.createElement("div");
        cur.className = "term-line term-cursor";
        body.appendChild(cur);
        return;
      }
      var line = HERO_LINES[li];
      var div = document.createElement("div");
      div.className = "term-line";
      div.style.animationDelay = "0ms";
      body.appendChild(div);
      var plain = line.replace(/<[^>]+>/g, "");
      var i = 0;
      var t = setInterval(function () {
        i++;
        div.innerHTML = renderPartial(line, i);
        if (i >= plain.length) { clearInterval(t); li++; setTimeout(typeLine, 320); }
      }, 12);
    }
    function renderPartial(line, count) {
      var re = /<span class="([^"]+)">([^<]*)<\/span>/g;
      var m, acc = 0;
      var html = "";
      while ((m = re.exec(line)) !== null) {
        var cls = m[1], text = m[2];
        var segStart = acc;
        acc += text.length;
        if (acc <= count) { html += '<span class="' + cls + '">' + text + "</span>"; }
        else {
          var keep = count - segStart;
          if (keep > 0) html += '<span class="' + cls + '">' + text.slice(0, keep) + "</span>";
          return html;
        }
      }
      return html;
    }
    setTimeout(typeLine, 400);
  }

  /* ── Install-copy buttons ─────────────────────────────────────────────── */
  function initInstallCopy() {
    document.querySelectorAll("[data-copy]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        var text = btn.getAttribute("data-copy");
        function done() {
          btn.classList.add("copied");
          btn.textContent = "Copied ✓";
          setTimeout(function () {
            btn.classList.remove("copied");
            btn.textContent = "Copy";
          }, 1600);
        }
        if (navigator.clipboard && navigator.clipboard.writeText) {
          navigator.clipboard.writeText(text).then(done, done);
        } else {
          var ta = document.createElement("textarea");
          ta.value = text;
          document.body.appendChild(ta);
          ta.select();
          try { document.execCommand("copy"); } catch (e) {}
          document.body.removeChild(ta);
          done();
        }
      });
    });
  }

  /* ── Page transition on internal links (progressive enhancement) ──────── */
  function initPageTransitions() {
    document.body.classList.add("page-enter");
    if (REDUCED || !("requestAnimationFrame" in window)) return;
    document.querySelectorAll("a[href]").forEach(function (a) {
      var href = a.getAttribute("href") || "";
      if (href.indexOf("http") === 0 || href.charAt(0) === "#" || href.indexOf("mailto:") === 0) return;
      a.addEventListener("click", function (e) {
        if (e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
        e.preventDefault();
        var target = href;
        document.body.style.transition = "opacity 220ms var(--ease-out)";
        document.body.style.opacity = "0";
        setTimeout(function () { window.location.href = target; }, 220);
      });
    });
  }

  document.addEventListener("DOMContentLoaded", function () {
    renderHeader();
    renderFooter();
    initNavScroll();
    initReveals();
    initCounters();
    initHeroTerminal();
    initInstallCopy();
    initPageTransitions();
  });
})();
