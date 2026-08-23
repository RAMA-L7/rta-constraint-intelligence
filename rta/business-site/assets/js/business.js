/* â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
   á¹šta | Business Site JS
   Shared chrome injection Â· glass nav scroll state Â· scroll reveals Â·
   animated counters Â· hero terminal typing Â· install-copy buttons Â·
   lightbox-free page transitions
   â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â• */

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

  /* â”€â”€ Live product facts (keep in sync with rta/evidence/manifest) â”€â”€â”€â”€â”€â”€â”€ */
  var FACTS = {
    version: "1.5.8",
    rules: 119,
    tests: 824,
    suites: 42,
    runners: 9,
    app: "https://rta-constraint-intelligence-294wudzqxdnhluyqk6eskp.streamlit.app/",
  };

  /* â”€â”€ Shared nav / footer â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ */
  var NAV_LINKS = [
    ["Features", "index.html#features"],
    ["Platform", "index.html#platform"],
    ["Why á¹šta", "index.html#why"],
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
    return '<img class="' + (cls || "brand-img") + '" src="' + rel("assets/img/rta-lockup.png") + '" alt="á¹šta logo">';
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
      + '<a class="brand" href="' + rel("index.html") + '" aria-label="á¹šta home" title="á¹šta">' + brandImg() + "</a>"
      + '<button class="nav-burger" aria-label="Toggle navigation" aria-expanded="false" aria-controls="nav-links">â˜°</button>'
      + '<nav class="nav-links" id="nav-links">' + links
      + '<a class="btn btn--primary btn--sm nav-cta" href="' + FACTS.app + '" target="_blank" rel="noopener">Launch App â†—</a>'
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
      + '<div class="footer-grid">'      + '<div><a class="brand" href="' + rel("index.html") + '" title="á¹šta">' + brandImg("brand-img brand-img--lg") + "</a>"
      +     '<p style="color:var(--text-secondary);font-size:13.5px;max-width:38ch;margin-top:14px">'
      +     "á¹šta brings order to timing intent, transforming constraints into trusted engineering knowledge through deterministic precision.</p>"
      +     '<div class="chip-row" style="margin-top:16px">'
      +       '<span class="badge badge--success"><span class="sq"></span>Deterministic</span>'
      +       '<span class="badge badge--accent"><span class="sq"></span>Offline-capable</span>'
      +       '<span class="badge badge--info"><span class="sq"></span>No LLM required</span>'
      +     "</div></div>"
      +   cols
      + "</div>"
      + '<div class="footer-bottom">'
      +   '<span>á¹šta v' + FACTS.version + ' Â· MIT License</span>'
      +   '<span>Validates SDC constraint quality, not an STA timing signoff tool.</span>'
      + "</div></div></div>";
  }

  /* â”€â”€ Glass nav scroll state â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ */
  function initNavScroll() {
    var wrap = document.getElementById("nav-wrap");
    if (!wrap) return;
    function onScroll() {
      wrap.classList.toggle("scrolled", window.scrollY > 12);
    }
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
  }

  /* â”€â”€ Scroll reveals â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ */
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

  /* â”€â”€ Animated counters â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ */
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

  /* â”€â”€ Hero terminal typing â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ */
  var HERO_LINES = [
    '<span class="t-cmd">$ rta check design.sdc --netlist top.v --top soc_top</span>',
    '<span class="t-dim">preprocess Â· 43 constraints Â· tcl vars resolved</span>',
    '<span class="t-ok">âœ“ clocks: 4 (2 primary, 2 generated)</span>',
    '<span class="t-ok">âœ“ references: 61/61 resolved against netlist</span>',
    '<span class="t-dim">clock relations: 6 pairs Â· coverage: 94% inputs</span>',
    '<span class="t-warn">â–² SDC-151  reset tree rst_n has no timing exception</span>',
    '<span class="t-err">âœ— SDC-008  input delay 9.0ns â‰¥ clock period</span>',
    '<span class="t-dim">readiness: REVIEW_REQUIRED Â· 2 errors Â· 1 warning</span>',
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

  /* â”€â”€ Install-copy buttons â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ */
  function initInstallCopy() {
    document.querySelectorAll("[data-copy]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        var text = btn.getAttribute("data-copy");
        function done() {
          btn.classList.add("copied");
          btn.textContent = "Copied âœ“";
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

  /* â”€â”€ Page transition on internal links (progressive enhancement) â”€â”€â”€â”€â”€â”€â”€â”€ */
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

  /* â•â•â• Audio overview player: language switch + NotebookLM-style waveform â•â•â• */
  function initAudioPlayer() {
    var shell = document.getElementById("audio-player");
    if (!shell) return;

    var audio = new Audio();
    audio.preload = "metadata";

    var playBtn   = document.getElementById("audio-play");
    var iconPlay  = document.getElementById("icon-play");
    var iconPause = document.getElementById("icon-pause");
    var curEl     = document.getElementById("audio-cur");
    var durEl     = document.getElementById("audio-dur");
    var titleEl   = document.getElementById("audio-title");
    var canvas    = document.getElementById("audio-viz");
    var langBtns  = shell.querySelectorAll(".lang-btn");

    var ctx2d = canvas.getContext("2d");
    var rafId = null;
    var dragging = false;

    /* NotebookLM-style full-track waveform: deterministic pseudo-random heights */
    var BARS = 72;
    var heights = [];
    (function seedHeights() {
      var seed = 42;
      function rnd() { seed = (seed * 16807) % 2147483647; return seed / 2147483647; }
      for (var i = 0; i < BARS; i++) {
        var envelope = Math.sin((i / (BARS - 1)) * Math.PI) * 0.55 + 0.45;
        heights.push(0.22 + 0.78 * ((rnd() * 0.6 + rnd() * 0.4) * envelope));
      }
    })();

    function fmt(t) {
      if (!isFinite(t) || t < 0) t = 0;
      var m = Math.floor(t / 60), s = Math.floor(t % 60);
      return m + ":" + (s < 10 ? "0" : "") + s;
    }

    function sizeCanvas() {
      var dpr = window.devicePixelRatio || 1;
      var cw = canvas.clientWidth, ch = canvas.clientHeight;
      if (canvas.width !== Math.round(cw * dpr) || canvas.height !== Math.round(ch * dpr)) {
        canvas.width = Math.round(cw * dpr);
        canvas.height = Math.round(ch * dpr);
        ctx2d.setTransform(dpr, 0, 0, dpr, 0, 0);
      }
    }

    function progress() {
      return (isFinite(audio.duration) && audio.duration > 0)
        ? audio.currentTime / audio.duration : 0;
    }

    function draw(now) {
      sizeCanvas();
      var w = canvas.clientWidth, h = canvas.clientHeight;
      var mid = h / 2;
      var playing = !audio.paused && !audio.ended;
      var prog = progress();
      var gap = 2;
      var bw = Math.max(2, (w - gap * (BARS - 1)) / BARS);

      ctx2d.clearRect(0, 0, w, h);

      for (var i = 0; i < BARS; i++) {
        var x = i * (bw + gap);
        var frac = (i + 0.5) / BARS;
        var bh = heights[i] * (h - 8);

        if (playing) {
          /* gentle organic wobble, strongest near the playhead */
          var near = 1 - Math.min(1, Math.abs(frac - prog) * 9);
          var wob = Math.sin(now / 240 + i * 0.55) * (2.5 + near * 7);
          bh = Math.max(4, Math.min(h - 4, bh + wob));
        }

        var y = mid - bh / 2;
        if (frac <= prog) {
          var g = ctx2d.createLinearGradient(x, y, x, y + bh);
          g.addColorStop(0, "#38BDF8");
          g.addColorStop(1, "#818CF8");
          ctx2d.fillStyle = g;
        } else {
          ctx2d.fillStyle = "rgba(148,163,184,0.20)";
        }
        ctx2d.beginPath();
        if (ctx2d.roundRect) { ctx2d.roundRect(x, y, bw, bh, bw / 2); } else { ctx2d.rect(x, y, bw, bh); }
        ctx2d.fill();
      }

      /* playhead glow */
      if (prog > 0 && prog < 1) {
        var px = prog * w;
        var pg = ctx2d.createLinearGradient(px - 12, 0, px + 12, 0);
        pg.addColorStop(0, "rgba(56,189,248,0)");
        pg.addColorStop(0.5, "rgba(56,189,248," + (playing ? "0.35" : "0.18") + ")");
        pg.addColorStop(1, "rgba(56,189,248,0)");
        ctx2d.fillStyle = pg;
        ctx2d.fillRect(px - 12, 0, 24, h);
      }
    }

    function loop(ts) {
      draw(ts);
      curEl.textContent = fmt(audio.currentTime);
      if (!audio.paused && !audio.ended) {
        rafId = requestAnimationFrame(loop);
      } else {
        rafId = null;
      }
    }

    function startLoop() {
      if (!rafId) rafId = requestAnimationFrame(loop);
    }

    function stopLoopAndDraw() {
      if (rafId) { cancelAnimationFrame(rafId); rafId = null; }
      draw(0);
      curEl.textContent = fmt(audio.currentTime);
    }

    function setLang(btn) {
      var wasPlaying = !audio.paused;
      langBtns.forEach(function (b) {
        var active = b === btn;
        b.classList.toggle("is-active", active);
        b.setAttribute("aria-selected", active ? "true" : "false");
      });
      audio.src = btn.getAttribute("data-src");
      titleEl.textContent = btn.getAttribute("data-title") || btn.textContent;
      curEl.textContent = "0:00";
      durEl.textContent = "0:00";
      draw(0);
      if (wasPlaying) { audio.play().catch(function () {}); }
    }

    function updatePlayIcon() {
      var playing = !audio.paused && !audio.ended;
      iconPlay.style.display = playing ? "none" : "";
      iconPause.style.display = playing ? "" : "none";
      playBtn.classList.toggle("is-playing", playing);
      playBtn.setAttribute("aria-label", playing ? "Pause" : "Play");
      if (playing) { startLoop(); } else { stopLoopAndDraw(); }
    }

    langBtns.forEach(function (b) {
      b.addEventListener("click", function () { setLang(b); });
    });

    playBtn.addEventListener("click", function () {
      if (audio.paused) { audio.play().catch(function () {}); }
      else { audio.pause(); }
    });

    audio.addEventListener("play", updatePlayIcon);
    audio.addEventListener("pause", updatePlayIcon);
    audio.addEventListener("ended", updatePlayIcon);

    audio.addEventListener("loadedmetadata", function () {
      durEl.textContent = fmt(audio.duration);
    });

    /* click or drag on the waveform to seek (NotebookLM behaviour) */
    function seekFromEvent(e) {
      var rect = canvas.getBoundingClientRect();
      var frac = Math.min(1, Math.max(0, (e.clientX - rect.left) / rect.width));
      if (isFinite(audio.duration) && audio.duration > 0) {
        audio.currentTime = frac * audio.duration;
        curEl.textContent = fmt(audio.currentTime);
        draw(0);
      }
    }
    canvas.style.cursor = "pointer";
    canvas.addEventListener("pointerdown", function (e) {
      dragging = true;
      try { canvas.setPointerCapture(e.pointerId); } catch (err) {}
      seekFromEvent(e);
    });
    canvas.addEventListener("pointermove", function (e) {
      if (dragging) seekFromEvent(e);
    });
    canvas.addEventListener("pointerup", function () { dragging = false; });

    window.addEventListener("resize", function () {
      if (!rafId) draw(0);
    });

    // Preload metadata for default language so duration shows immediately.
    audio.src = langBtns[0].getAttribute("data-src");
    draw(0);
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
    initAudioPlayer();
  });
})();
