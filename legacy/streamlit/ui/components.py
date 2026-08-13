"""
Shared UI components for Ṛta.
Clean, light, docs-grade theme (Arcade-docs DNA) with dark mode support.
"""

import streamlit as st
from rules_registry import APP_VERSION

# ═══════════════════════════════════════════════════════════════════════════════
# Ṛta THEME — light, spacious, card-grid, single-accent (Arcade-docs DNA)
# ═══════════════════════════════════════════════════════════════════════════════

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap');

:root {
    --rta-ink:      #0a0a0a;
    --rta-ink-dim:  #57534e;
    --rta-muted:    #78716c;
    --rta-bg:       #ffffff;
    --rta-panel:    #fafaf9;
    --rta-border:   #e7e5e4;
    --rta-accent:   #16a34a;
    --rta-accent-2: #0a0a0a;
    --rta-radius:   14px;
}

/* ── Base Typography ─────────────────────────────────────────── */
html, body, [class*="css"] {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    color: var(--rta-ink);
}
h1, h2, h3, h4 { letter-spacing: -0.02em; font-weight: 700; }
.stMarkdown p, .stMarkdown li { color: var(--rta-ink-dim); line-height: 1.6; }
.stCaption, [data-testid="stCaptionContainer"] { color: var(--rta-muted) !important; }

/* Give the whole app a touch more breathing room, docs-style */
.block-container { padding-top: 2rem; max-width: 1180px; }

/* ── Tab Styling — quiet pill nav, not a debugger strip ─────── */
.stTabs [data-baseweb="tab-list"] {
    gap: 4px;
    background: transparent;
    border-bottom: 1px solid var(--rta-border);
    padding: 0 0 0 0;
}
.stTabs [data-baseweb="tab"] {
    font-size: 14px;
    font-weight: 600;
    padding: 10px 16px;
    border-radius: 8px 8px 0 0;
    border: none;
    color: var(--rta-muted);
    transition: all 0.15s ease;
}
.stTabs [data-baseweb="tab"]:hover {
    color: var(--rta-ink);
    background: var(--rta-panel);
}
.stTabs [aria-selected="true"] {
    background: transparent !important;
    color: var(--rta-ink) !important;
    box-shadow: inset 0 -2px 0 var(--rta-accent-2) !important;
}

/* ── Header Banner — minimal, wordmark + tagline, thin rule ─── */
.sdc-header {
    background: var(--rta-bg);
    padding: 8px 0 24px 0;
    border-bottom: 1px solid var(--rta-border);
    margin-bottom: 28px;
    color: var(--rta-ink);
}
.sdc-header .rta-eyebrow {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    font-size: 12px;
    font-weight: 600;
    color: var(--rta-accent);
    text-transform: uppercase;
    letter-spacing: 0.06em;
    margin-bottom: 10px;
}
.sdc-header .rta-eyebrow::before {
    content: "";
    width: 6px; height: 6px; border-radius: 50%;
    background: var(--rta-accent);
    display: inline-block;
}
.sdc-header h1 {
    font-size: 34px;
    font-weight: 800;
    margin: 0 0 6px 0;
    color: var(--rta-ink);
    letter-spacing: -0.03em;
}
.sdc-header p {
    font-size: 15px;
    color: var(--rta-ink-dim);
    margin: 0;
    font-weight: 400;
    max-width: 620px;
}
.sdc-version-badge {
    display: inline-block;
    background: var(--rta-panel);
    border: 1px solid var(--rta-border);
    padding: 4px 12px;
    border-radius: 20px;
    font-size: 12px;
    font-weight: 600;
    color: var(--rta-ink-dim);
    margin-top: 14px;
    font-family: 'JetBrains Mono', monospace;
}
.sdc-nav {
    display: flex;
    flex-wrap: wrap;
    gap: 20px;
    margin-top: 16px;
}
.sdc-nav a {
    font-size: 13.5px;
    font-weight: 600;
    color: var(--rta-accent);
    text-decoration: none;
    letter-spacing: 0.01em;
}
.sdc-nav a:hover {
    text-decoration: underline;
    color: var(--rta-accent-2);
}

/* ── Metric Cards — flat, bordered, docs-tile style ──────────── */
.metric-card {
    background: var(--rta-bg);
    border: 1px solid var(--rta-border);
    border-radius: var(--rta-radius);
    padding: 18px 20px;
    text-align: left;
    box-shadow: none;
    transition: border-color 0.15s ease, transform 0.15s ease;
    position: relative;
    overflow: hidden;
}
.metric-card:hover {
    border-color: #d4d4d4;
    transform: translateY(-1px);
}
.metric-card .mc-icon { font-size: 18px; margin-bottom: 8px; opacity: 0.7; }
.metric-card .mc-value {
    font-size: 30px;
    font-weight: 800;
    line-height: 1.1;
    margin-bottom: 4px;
    color: var(--rta-ink);
}
.metric-card .mc-label {
    font-size: 11px;
    color: var(--rta-muted);
    text-transform: uppercase;
    letter-spacing: 0.06em;
    font-weight: 600;
}
.metric-card.mc-red .mc-value { color: #dc2626; }
.metric-card.mc-green .mc-value { color: #16a34a; }
.metric-card.mc-yellow .mc-value { color: #b45309; }
.metric-card.mc-blue .mc-value { color: #2563eb; }
.metric-card.mc-purple .mc-value { color: #7c3aed; }
.metric-card .mc-accent { position: absolute; top: 0; left: 0; bottom: 0; width: 3px; }
.metric-card.mc-red .mc-accent { background: #dc2626; }
.metric-card.mc-green .mc-accent { background: #16a34a; }
.metric-card.mc-yellow .mc-accent { background: #d97706; }
.metric-card.mc-blue .mc-accent { background: #2563eb; }
.metric-card.mc-purple .mc-accent { background: #7c3aed; }

/* ── Status Banners — flat tinted strips, not glossy gradients ─ */
.status-banner {
    padding: 12px 16px;
    border-radius: 10px;
    font-size: 14px;
    font-weight: 500;
    margin: 12px 0;
    display: flex;
    align-items: center;
    gap: 10px;
    border: 1px solid transparent;
}
.status-banner .sb-icon { font-size: 16px; }
.sb-success { background: #f0fdf4; color: #166534; border-color: #bbf7d0; }
.sb-error   { background: #fef2f2; color: #991b1b; border-color: #fecaca; }
.sb-warning { background: #fffbeb; color: #92400e; border-color: #fde68a; }
.sb-info    { background: #f4f4f5; color: #3f3f46; border-color: #e4e4e7; }

/* ── Issue Cards — flat card, colored left rule only ─────────── */
.issue-card {
    background: var(--rta-bg);
    border: 1px solid var(--rta-border);
    border-radius: 10px;
    padding: 14px 18px;
    margin: 8px 0;
    border-left: 3px solid var(--rta-border);
    box-shadow: none;
}
.issue-card.ic-error   { border-left-color: #dc2626; }
.issue-card.ic-warning { border-left-color: #d97706; }
.issue-card.ic-info    { border-left-color: #2563eb; }
.issue-card .ic-header { display: flex; align-items: center; gap: 8px; margin-bottom: 6px; }
.issue-card .ic-code {
    font-family: 'JetBrains Mono', monospace;
    font-size: 13px;
    font-weight: 700;
    color: var(--rta-ink);
}
.issue-card .ic-line { font-size: 11px; color: var(--rta-muted); font-weight: 500; }
.issue-card .ic-msg { font-size: 13px; color: var(--rta-ink-dim); line-height: 1.5; }

/* ── Badges — quiet pills, one border weight ─────────────────── */
.badge {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    padding: 3px 10px;
    border-radius: 20px;
    font-size: 12px;
    font-weight: 600;
}
.badge-error   { background: #fef2f2; color: #b91c1c; border: 1px solid #fecaca; }
.badge-warning { background: #fffbeb; color: #92400e; border: 1px solid #fde68a; }
.badge-info    { background: #eff6ff; color: #1e40af; border: 1px solid #bfdbfe; }
.badge-success { background: #f0fdf4; color: #166534; border: 1px solid #bbf7d0; }

/* Legacy badges — recolored to match the flat palette */
.err-badge  { background:#fef2f2; color:#b91c1c; border:1px solid #fecaca; padding:3px 10px; border-radius:20px; font-size:12px; font-weight:600; }
.warn-badge { background:#fffbeb; color:#92400e; border:1px solid #fde68a; padding:3px 10px; border-radius:20px; font-size:12px; font-weight:600; }
.info-badge { background:#eff6ff; color:#1e40af; border:1px solid #bfdbfe; padding:3px 10px; border-radius:20px; font-size:12px; font-weight:600; }
.note-badge { background:#f0fdf4; color:#166534; border:1px solid #bbf7d0; padding:3px 10px; border-radius:20px; font-size:12px; font-weight:600; }
.fatal-badge { background:#fef2f2; color:#7f1d1d; border:1px solid #fca5a5; padding:3px 10px; border-radius:20px; font-size:12px; font-weight:600; }
code { font-family: 'JetBrains Mono', monospace; background: var(--rta-panel); color: var(--rta-ink); padding:1px 6px; border-radius:4px; font-size:12px; border: 1px solid var(--rta-border); }

/* ── Sidebar — quiet wordmark card instead of dark gradient ──── */
[data-testid="stSidebar"] { background: var(--rta-panel); border-right: 1px solid var(--rta-border); }
.sidebar-brand {
    background: var(--rta-bg);
    border: 1px solid var(--rta-border);
    border-radius: 12px;
    padding: 16px 18px;
    color: var(--rta-ink);
    margin-bottom: 12px;
}
.sidebar-brand h3 {
    color: var(--rta-ink);
    font-size: 16px;
    font-weight: 800;
    margin: 0 0 4px 0;
    letter-spacing: -0.01em;
}
.sidebar-brand p {
    color: var(--rta-muted);
    font-size: 12px;
    margin: 0;
}

/* ── Progress Bar ─────────────────────────────────────────────── */
.progress-bar { background: var(--rta-border); border-radius: 8px; height: 8px; overflow: hidden; margin: 8px 0; }
.progress-fill { height: 100%; border-radius: 8px; transition: width 0.3s ease; }
.progress-fill.pf-green { background: #16a34a; }
.progress-fill.pf-yellow { background: #d97706; }
.progress-fill.pf-red { background: #dc2626; }

/* ── Code Block ────────────────────────────────────────────────── */
.code-block {
    background: #0a0a0a;
    color: #e7e5e4;
    padding: 16px 20px;
    border-radius: 10px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 13px;
    line-height: 1.6;
    overflow-x: auto;
    white-space: pre;
    border: 1px solid #262626;
}

/* ── Button Overrides — solid black CTA, docs-site style ─────── */
.stButton > button[kind="primary"] {
    background: var(--rta-ink) !important;
    border: none !important;
    border-radius: 8px !important;
    font-weight: 600 !important;
    padding: 10px 22px !important;
    box-shadow: none !important;
}
.stButton > button[kind="primary"]:hover {
    background: #262626 !important;
    box-shadow: 0 2px 8px rgba(0,0,0,0.15) !important;
}
.stButton > button[kind="secondary"] {
    border-radius: 8px !important;
    border-color: var(--rta-border) !important;
    font-weight: 600 !important;
}
.stDownloadButton > button {
    border-radius: 8px !important;
    font-weight: 600 !important;
}

/* ── Divider ───────────────────────────────────────────────────── */
hr { border: none; height: 1px; background: var(--rta-border); margin: 24px 0; }

/* ── Expanders — clean bordered card, no shadow soup ─────────── */
[data-testid="stExpander"] {
    border: 1px solid var(--rta-border) !important;
    border-radius: 12px !important;
    background: var(--rta-bg) !important;
}
.streamlit-expanderHeader { font-weight: 600 !important; font-size: 14px !important; }

/* ── Metrics (native st.metric) styled as flat tiles ─────────── */
[data-testid="stMetric"] {
    background: var(--rta-bg);
    border: 1px solid var(--rta-border);
    border-radius: 12px;
    padding: 14px 16px;
}

/* ── Scrollbar ─────────────────────────────────────────────────── */
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: var(--rta-panel); border-radius: 3px; }
::-webkit-scrollbar-thumb { background: #d4d4d4; border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: #a3a3a3; }

/* ═══════════════════════════════════════════════════════════════
   DARK MODE — activated by Streamlit's dark theme toggle
   Same DNA (flat, bordered, one accent), inverted palette
   ═══════════════════════════════════════════════════════════════ */

[data-theme="dark"], .stApp[data-theme="dark"] {

    --rta-ink: #f5f5f4;
    --rta-ink-dim: #a8a29e;
    --rta-muted: #78716c;
    --rta-bg: #0c0c0d;
    --rta-panel: #131314;
    --rta-border: #26262a;

    .stTabs [data-baseweb="tab-list"] { background: transparent; border-bottom-color: #26262a; }
    .stTabs [data-baseweb="tab"] { color: #a8a29e; }
    .stTabs [data-baseweb="tab"]:hover { color: #f5f5f4; background: #131314; }
    .stTabs [aria-selected="true"] { color: #f5f5f4 !important; box-shadow: inset 0 -2px 0 #f5f5f4 !important; }

    .sdc-header { background: #0c0c0d; border-bottom-color: #26262a; }
    .sdc-header h1 { color: #f5f5f4; }
    .sdc-header p { color: #a8a29e; }
    .sdc-version-badge { background: #131314; border-color: #26262a; color: #a8a29e; }

    .metric-card { background: #131314; border-color: #26262a; }
    .metric-card:hover { border-color: #3f3f46; }
    .metric-card .mc-value { color: #f5f5f4; }
    .metric-card .mc-label { color: #78716c; }
    .metric-card.mc-red .mc-value { color: #f87171; }
    .metric-card.mc-green .mc-value { color: #4ade80; }
    .metric-card.mc-yellow .mc-value { color: #fbbf24; }
    .metric-card.mc-blue .mc-value { color: #60a5fa; }
    .metric-card.mc-purple .mc-value { color: #c084fc; }

    .sb-success { background: rgba(34,197,94,0.10); color: #4ade80; border-color: rgba(34,197,94,0.25); }
    .sb-error   { background: rgba(239,68,68,0.10); color: #f87171; border-color: rgba(239,68,68,0.25); }
    .sb-warning { background: rgba(234,179,8,0.10); color: #fbbf24; border-color: rgba(234,179,8,0.25); }
    .sb-info    { background: rgba(148,163,184,0.10); color: #d4d4d8; border-color: rgba(148,163,184,0.2); }

    .issue-card { background: #131314; border-color: #26262a; }
    .issue-card .ic-code { color: #f5f5f4; }
    .issue-card .ic-msg { color: #a8a29e; }

    .badge-error   { background: rgba(239,68,68,0.12); color: #f87171; border-color: rgba(239,68,68,0.3); }
    .badge-warning { background: rgba(234,179,8,0.12); color: #fbbf24; border-color: rgba(234,179,8,0.3); }
    .badge-info    { background: rgba(96,165,250,0.12); color: #93c5fd; border-color: rgba(96,165,250,0.3); }
    .badge-success { background: rgba(74,222,128,0.12); color: #4ade80; border-color: rgba(74,222,128,0.3); }

    .err-badge  { background: rgba(239,68,68,0.12); color: #f87171; border-color: rgba(239,68,68,0.3); }
    .warn-badge { background: rgba(234,179,8,0.12); color: #fbbf24; border-color: rgba(234,179,8,0.3); }
    .info-badge { background: rgba(96,165,250,0.12); color: #93c5fd; border-color: rgba(96,165,250,0.3); }
    .note-badge { background: rgba(74,222,128,0.12); color: #4ade80; border-color: rgba(74,222,128,0.3); }
    .fatal-badge { background: rgba(239,68,68,0.18); color: #fca5a5; border-color: rgba(239,68,68,0.4); }

    code { background: #131314; color: #93c5fd; border-color: #26262a; }

    [data-testid="stSidebar"] { background: #0a0a0a; border-right-color: #26262a; }
    .sidebar-brand { background: #131314; border-color: #26262a; }
    .sidebar-brand h3 { color: #f5f5f4; }

    .progress-bar { background: #26262a; }
    hr { background: #26262a; }

    [data-testid="stExpander"] { background: #131314 !important; border-color: #26262a !important; }
    [data-testid="stMetric"] { background: #131314; border-color: #26262a; }

    ::-webkit-scrollbar-track { background: #131314; }
    ::-webkit-scrollbar-thumb { background: #3f3f46; }
    ::-webkit-scrollbar-thumb:hover { background: #52525b; }

    h1, h2, h3, h4, h5, h6, .stMarkdown h1, .stMarkdown h2, .stMarkdown h3 { color: #f5f5f4 !important; }
    .stMarkdown p, .stMarkdown li { color: #a8a29e; }
    .stCaption, .stMarkdown small { color: #78716c; }

    .stButton > button[kind="primary"] { background: #f5f5f4 !important; color: #0c0c0d !important; }
    .stButton > button[kind="primary"]:hover { background: #e7e5e4 !important; }
}
</style>
"""


MODULE_ICONS = {
    "checker": "🛡",
    "mmc": "🔲",
    "clock_relations": "🕐",
    "constraint_diff": "🔍",
}


def inject_css():
    """Inject the Ṛta theme (light, flat, single-accent — Arcade-docs DNA)."""
    st.markdown(CSS, unsafe_allow_html=True)


BUSINESS_URL = "https://RAMA-L7.github.io/rta-constraint-intelligence/"


def render_header():
    """Render the wordmark banner: eyebrow + title + tagline + version pill +
    business-site navigation."""
    st.markdown(f"""
<div class="sdc-header">
    <div class="rta-eyebrow">Constraint Intelligence</div>
    <h1>Ṛta</h1>
    <p>Ṛta brings order to timing intent, transforming constraints into trusted
    engineering knowledge through deterministic precision.</p>
    <span class="sdc-version-badge">v{APP_VERSION}</span>
    <nav class="sdc-nav">
        <a href="{BUSINESS_URL}index.html#features" target="_blank" rel="noopener">Features</a>
        <a href="{BUSINESS_URL}index.html#why" target="_blank" rel="noopener">Why Ṛta</a>
        <a href="{BUSINESS_URL}features/rules.html" target="_blank" rel="noopener">Rules</a>
        <a href="{BUSINESS_URL}index.html#install" target="_blank" rel="noopener">Install</a>
        <a href="https://github.com/RAMA-L7/rta-constraint-intelligence" target="_blank" rel="noopener">Docs</a>
    </nav>
</div>
""", unsafe_allow_html=True)


def render_sidebar():
    """Render the sidebar with version card and links."""
    with st.sidebar:
        st.markdown(f"""
<div class="sidebar-brand">
    <h3>Ṛta</h3>
    <p>v{APP_VERSION} · Constraint Intelligence Platform</p>
</div>
""", unsafe_allow_html=True)

        # ── Quick Actions ────────────────────────────────────────────────
        if st.button("🧪 Test Drive — Try All Features",
                     use_container_width=True,
                     type="primary",
                     key="sidebar_testdrive"):
            st.session_state.app_view = "test_drive"
            st.rerun()

        if st.button("📊 Community Feedback",
                     use_container_width=True,
                     key="sidebar_feedback"):
            st.session_state.app_view = "feedback"
            st.rerun()

        if st.session_state.get("app_view", "features") != "features":
            if st.button("← Back to Features",
                         use_container_width=True,
                         key="sidebar_back"):
                st.session_state.app_view = "features"
                st.rerun()

        st.markdown("---")

        with st.expander("📋 What's New", expanded=False):
            st.markdown(f"""
**v{APP_VERSION}**
- 🔗 Interactions — detects duplicate, overriding, and contradictory constraints
  within a single SDC
- ✅ Readiness — aggregates Checker evidence into a 7-dimension signoff-readiness
  verdict (Clocks, I/O, Exceptions, Coverage, Consistency, Analysis Trust, Design Context)
- 🧬 Netlist cross-checks upgraded — structural, connectivity-based resolution
  (not name-matching) for get_ports/get_pins/get_cells, in Checker, Coverage, and
  Clock Relations (block-level; full-chip planned)

**v1.3.0**
- 📝 Linter — Format & reorganize SDC files
- 🔄 Converter — SDC ↔ JSON/YAML conversion
- 📋 Rules Reference — Browse all SDC codes
- 🧪 311 tests — Comprehensive test suite

**v1.2.0**
- 🕐 Clock Relations — detect incorrect clock groups
- 📊 Rule Reference — searchable code documentation

**v1.1.0**
- 🔍 Constraint Change Analyzer — semantic SDC diff
- 📦 MMC SDC Generator — per-corner generation
- 🔲 MMC Corner Manager — PVT corner presets
""")

        st.markdown("---")
        st.markdown("📎 [GitHub](https://github.com/RAMA-L7/rta-constraint-intelligence) · [Docs](https://github.com/RAMA-L7/rta-constraint-intelligence/tree/main/rta/docs)")
        st.caption("© Ṛta · MIT License")


# ═══════════════════════════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

def metric_cards_row(items: list):
    """Render a row of metric cards.

    items: list of (label, value, icon, color) tuples
    """
    cols = st.columns(len(items))
    for col, (label, value, icon, color) in zip(cols, items):
        with col:
            st.markdown(f"""
<div class="metric-card mc-{color}">
    <div class="mc-accent"></div>
    <div class="mc-icon">{icon}</div>
    <div class="mc-value">{value}</div>
    <div class="mc-label">{label}</div>
</div>
""", unsafe_allow_html=True)


def status_banner(message: str, status: str = "info"):
    """Render a colored status banner."""
    icons = {"success": "✅", "error": "❌", "warning": "⚠️", "info": "ℹ️"}
    icon = icons.get(status, "ℹ️")
    st.markdown(f"""
<div class="status-banner sb-{status}">
    <span class="sb-icon">{icon}</span>
    <span>{message}</span>
</div>
""", unsafe_allow_html=True)


def issue_card(code: str, message: str, severity: str, line: int = 0):
    """Render an issue as a styled card with colored border."""
    icons = {"error": "🔴", "warning": "🟡", "info": "🔵", "fatal": "💀"}
    icon = icons.get(severity, "⚪")
    line_html = f'<span class="ic-line">Line {line}</span>' if line else ""
    st.markdown(f"""
<div class="issue-card ic-{severity}">
    <div class="ic-header">
        <span>{icon}</span>
        <span class="ic-code">{code}</span>
        {line_html}
    </div>
    <div class="ic-msg">{message}</div>
</div>
""", unsafe_allow_html=True)


def section_header(title: str, subtitle: str = ""):
    """Render a styled section header."""
    sub_html = f'<p style="font-size:13px;color:var(--rta-muted);margin:0 0 8px 0">{subtitle}</p>' if subtitle else ""
    st.markdown(f"""
<div style="display:flex;align-items:center;gap:8px;margin:24px 0 8px 0">
    <div style="width:3px;height:18px;background:var(--rta-accent-2);border-radius:2px"></div>
    <div style="font-size:17px;font-weight:700;color:var(--rta-ink)">{title}</div>
</div>
{sub_html}
""", unsafe_allow_html=True)


def styled_code_block(code: str, language: str = ""):
    """Render a code block with dark theme."""
    import html as h
    escaped = h.escape(code)
    st.markdown(f'<div class="code-block">{escaped}</div>', unsafe_allow_html=True)


def progress_bar(value: float, label: str = ""):
    """Render a colored progress bar (value 0-100)."""
    color = "green" if value >= 80 else "yellow" if value >= 50 else "red"
    label_html = f' <span style="font-size:12px;color:var(--rta-muted);margin-left:8px">{label}</span>' if label else ""
    st.markdown(f"""
<div style="display:flex;align-items:center;gap:8px">
    <div class="progress-bar" style="flex:1">
        <div class="progress-fill pf-{color}" style="width:{value}%"></div>
    </div>
    <span style="font-size:13px;font-weight:600;min-width:50px;text-align:right">{value:.0f}%</span>
    {label_html}
</div>
""", unsafe_allow_html=True)


def badge(text: str, style: str = "info"):
    """Render a badge."""
    st.markdown(f'<span class="badge badge-{style}">{text}</span>', unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
# UPLOAD / DOWNLOAD
# ═══════════════════════════════════════════════════════════════════════════════

def sdc_upload_area(key_prefix: str = ""):
    """Render SDC upload area (file upload + paste).

    Returns (sdc_text, filename) or (None, None).
    """
    col_up, col_paste = st.columns([1, 2])
    with col_up:
        uploaded = st.file_uploader(
            "📁 Upload .sdc / .tcl / .txt",
            type=["sdc", "tcl", "txt"],
            key=f"{key_prefix}_upload",
        )
    with col_paste:
        pasted = st.text_area(
            "📝 Or paste SDC text here", height=140,
            placeholder=(
                "set sdc_version 2.2\n"
                "set_units -time ns -capacitance pF\n"
                "create_clock -name clk_core -period 5.0 [get_ports clk]\n"
                "..."
            ),
            key=f"{key_prefix}_paste",
        )

    if uploaded:
        return uploaded.read().decode("utf-8", errors="replace"), uploaded.name
    if pasted.strip():
        return pasted, "pasted.sdc"
    return None, None


def download_button(data: str, filename: str, mime: str, label: str = "Download", key: str = ""):
    """Render a download button."""
    st.download_button(
        label=f"📥 {label}",
        data=data,
        file_name=filename,
        mime=mime,
        use_container_width=True,
        key=key or None,
    )


# ═══════════════════════════════════════════════════════════════════════════════
# RULE REFERENCE
# ═══════════════════════════════════════════════════════════════════════════════

def render_rule_reference():
    """Render the rule reference expander (used in Checker tab)."""
    from rules_registry import get_all_rules
    st.divider()
    with st.expander("📋 **Rule Reference** — All SDC Codes", expanded=False):
        all_rules = get_all_rules()
        st.caption(f"{len(all_rules)} rules across 4 modules · Search by code, name, or keyword")

        search = st.text_input("🔍 Search rules", placeholder="SDC-060, clock, derate...", key="rule_ref_search")
        if search:
            q = search.lower()
            all_rules = [r for r in all_rules if q in r.code.lower() or q in r.short_name.lower()
                         or q in r.description.lower() or q in r.why_matters.lower()]

        mod_filter = st.radio(
            "Filter by module",
            ["All", "checker", "design_context", "design_coverage", "constraint_interactions", "mmc", "clock_relations", "constraint_diff"],
            horizontal=True, key="rule_ref_mod",
        )
        if mod_filter != "All":
            all_rules = [r for r in all_rules if r.module == mod_filter]

        if all_rules:
            import json
            rules_json = json.dumps([{
                "code": r.code, "severity": r.severity, "name": r.short_name,
                "module": r.module, "description": r.description,
                "why_matters": r.why_matters, "fix": r.fix,
            } for r in all_rules], indent=2)
            download_button(rules_json, "sdc_rules.json", "application/json", "Download (JSON)")

        st.caption(f"Showing **{len(all_rules)}** rules")
        for rule in all_rules:
            sev_icon = {"error": "🔴", "warning": "🟡", "info": "🔵", "fatal": "💀"}.get(rule.severity, "⚪")
            with st.expander(f"{sev_icon} **{rule.code}** — {rule.short_name}"):
                c1, c2 = st.columns([1, 1])
                with c1:
                    st.markdown(f"**Severity:** {rule.severity}")
                    st.markdown(f"**Module:** {rule.module}")
                    st.markdown(f"**Added in:** v{rule.added_version}")
                with c2:
                    st.markdown(f"**What it detects:** {rule.description}")
                st.markdown(f"**Why it matters:** {rule.why_matters}")
                st.markdown(f"**How to fix:** {rule.fix}")
                if rule.reference_url:
                    st.markdown(f"📚 [{rule.reference_url}]({rule.reference_url})")
