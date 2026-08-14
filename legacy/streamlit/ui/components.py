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
    --rta-ink-dim:  #44403c;
    --rta-muted:    #78716c;
    --rta-bg:       #ffffff;
    --rta-panel:    #fafaf9;
    --rta-border:   #e7e5e4;
    --rta-border-strong: #d6d3d1;
    --rta-accent:   #15803d;
    --rta-accent-soft: #ecfdf3;
    --rta-accent-2: #0a0a0a;
    --rta-radius:   14px;
    --rta-radius-sm: 10px;
    --rta-shadow-sm: 0 1px 2px rgba(16,24,40,0.04), 0 1px 3px rgba(16,24,40,0.06);
    --rta-shadow-md: 0 4px 8px -2px rgba(16,24,40,0.06), 0 2px 4px -2px rgba(16,24,40,0.08);
    --rta-shadow-lg: 0 12px 24px -6px rgba(16,24,40,0.12), 0 4px 8px -4px rgba(16,24,40,0.08);
    --rta-focus-ring: 0 0 0 3px rgba(21,128,61,0.18);
}

/* ── Base Typography — clear hierarchy, engineering readability ─ */
html, body, [class*="css"] {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    color: var(--rta-ink);
    -webkit-font-smoothing: antialiased;
    text-rendering: optimizeLegibility;
}
h1, h2, h3, h4 { letter-spacing: -0.02em; font-weight: 700; }
h1 { font-size: 1.9rem; line-height: 1.15; }
h2 { font-size: 1.45rem; line-height: 1.2; }
h3 { font-size: 1.15rem; line-height: 1.25; }
h4 { font-size: 1rem; line-height: 1.3; }
.stMarkdown p, .stMarkdown li { color: var(--rta-ink-dim); line-height: 1.6; }
.stMarkdown strong { color: var(--rta-ink); }
.stCaption, [data-testid="stCaptionContainer"] { color: var(--rta-muted) !important; }

/* Tabular figures for engineering numbers stay crisp */
.metric-card .mc-value, .progress-bar + span, code, pre, .code-block {
    font-variant-numeric: tabular-nums;
}

/* Give the whole app a touch more breathing room, docs-style */
.block-container { padding-top: 1.6rem; max-width: 1280px; }

/* ── Feature-page layout — consistent input panel + results ──── */
[data-testid="stVerticalBlock"] > [data-testid="stVerticalBlock"] {
    gap: 0.4rem;
}
.stTabs [data-testid="stTab"] > div {
    padding-top: 1.1rem;
}
/* Input rows sit in a quiet panel so upload/paste/run read as one unit */
.stTabs [data-testid="stTab"] [data-testid="stFileUploader"],
.stTabs [data-testid="stTab"] [data-testid="stTextArea"],
.stTabs [data-testid="stTab"] [data-testid="stTextInput"] {
    margin-bottom: 0.25rem;
}
/* Result sections get breathing room below the primary action */
.stTabs [data-testid="stTab"] [data-testid="stExpander"] {
    margin: 0.5rem 0;
}

/* ── Tab Styling — quiet pill nav, not a debugger strip ─────── */
.stTabs [data-baseweb="tab-list"] {
    gap: 4px;
    background: var(--rta-panel);
    border: 1px solid var(--rta-border);
    border-radius: 12px;
    padding: 4px;
    width: fit-content;
    max-width: 100%;
    overflow-x: auto;
}
.stTabs [data-baseweb="tab"] {
    font-size: 13.5px;
    font-weight: 600;
    padding: 8px 14px;
    border-radius: 9px;
    border: none;
    color: var(--rta-muted);
    transition: all 0.15s ease;
    white-space: nowrap;
}
.stTabs [data-baseweb="tab"]:hover {
    color: var(--rta-ink);
    background: rgba(0,0,0,0.04);
}
.stTabs [aria-selected="true"] {
    background: var(--rta-bg) !important;
    color: var(--rta-ink) !important;
    box-shadow: var(--rta-shadow-sm) !important;
    font-weight: 700 !important;
}

/* ── Header Banner — compact command bar, brand left / nav right ─ */
.sdc-header {
    background: linear-gradient(180deg, var(--rta-bg) 0%, var(--rta-panel) 130%);
    padding: 10px 0 18px 0;
    border-bottom: 1px solid var(--rta-border);
    margin-bottom: 24px;
    color: var(--rta-ink);
}
.sdc-header-row {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 24px;
    flex-wrap: wrap;
}
.sdc-brand .rta-eyebrow {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    font-size: 11px;
    font-weight: 700;
    color: var(--rta-accent);
    text-transform: uppercase;
    letter-spacing: 0.08em;
    margin-bottom: 4px;
}
.sdc-brand .rta-eyebrow::before {
    content: "";
    width: 6px; height: 6px; border-radius: 50%;
    background: var(--rta-accent);
    display: inline-block;
    box-shadow: 0 0 0 3px var(--rta-accent-soft);
}
.sdc-title-row {
    display: flex;
    align-items: center;
    gap: 12px;
}
.sdc-header h1 {
    font-size: 28px;
    font-weight: 800;
    margin: 0;
    color: var(--rta-ink);
    letter-spacing: -0.03em;
    line-height: 1.1;
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
    font-family: 'JetBrains Mono', monospace;
    box-shadow: var(--rta-shadow-sm);
    margin-top: 2px;
}
.sdc-tagline {
    font-size: 14px;
    color: var(--rta-ink-dim);
    margin: 10px 0 0 0;
    font-weight: 400;
    max-width: 640px;
    line-height: 1.55;
}
.sdc-nav {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
    justify-content: flex-end;
    max-width: 480px;
}
.sdc-nav a {
    font-size: 13px;
    font-weight: 600;
    color: var(--rta-ink-dim);
    text-decoration: none;
    letter-spacing: 0.01em;
    padding: 6px 12px;
    border-radius: 8px;
    border: 1px solid transparent;
    transition: all 0.15s ease;
}
.sdc-nav a:hover {
    color: var(--rta-ink);
    background: var(--rta-bg);
    border-color: var(--rta-border);
}

/* ── Sidebar capability rail ──────────────────────────────────── */
.nav-group-label {
    font-size: 11px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: var(--rta-muted);
    margin: 14px 0 6px 0;
}
.nav-subgroup-label {
    font-size: 11px;
    font-weight: 600;
    color: var(--rta-ink-dim);
    margin: 10px 0 4px 0;
}
.nav-link {
    display: block;
    font-size: 13px;
    font-weight: 500;
    color: var(--rta-ink-dim);
    text-decoration: none;
    padding: 5px 10px;
    border-radius: 7px;
    border: 1px solid transparent;
    transition: all 0.15s ease;
}
.nav-link:hover {
    color: var(--rta-ink);
    background: var(--rta-bg);
    border-color: var(--rta-border);
}
[data-testid="stSidebar"] .stButton > button {
    font-size: 13px !important;
    padding: 6px 10px !important;
    justify-content: flex-start !important;
    text-align: left !important;
}

/* ── Metric Cards — flat, bordered, docs-tile style ──────────── */
.metric-card {
    background: var(--rta-bg);
    border: 1px solid var(--rta-border);
    border-radius: var(--rta-radius);
    padding: 18px 20px;
    text-align: left;
    box-shadow: var(--rta-shadow-sm);
    transition: border-color 0.15s ease, transform 0.15s ease, box-shadow 0.15s ease;
    position: relative;
    overflow: hidden;
}
.metric-card:hover {
    border-color: var(--rta-border-strong);
    transform: translateY(-2px);
    box-shadow: var(--rta-shadow-md);
}
.metric-card .mc-icon { font-size: 17px; margin-bottom: 8px; opacity: 0.75; }
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
    letter-spacing: 0.07em;
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
    box-shadow: var(--rta-shadow-sm);
}
.status-banner .sb-icon {
    font-size: 15px;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 24px; height: 24px;
    border-radius: 6px;
    background: rgba(255,255,255,0.55);
}
.sb-success { background: #f0fdf4; color: #166534; border-color: #bbf7d0; }
.sb-error   { background: #fef2f2; color: #991b1b; border-color: #fecaca; }
.sb-warning { background: #fffbeb; color: #92400e; border-color: #fde68a; }
.sb-info    { background: #f4f4f5; color: #3f3f46; border-color: #e4e4e7; }

/* ── Issue Cards — flat card, colored left rule only ─────────── */
.issue-card {
    background: var(--rta-bg);
    border: 1px solid var(--rta-border);
    border-radius: var(--rta-radius-sm);
    padding: 14px 18px;
    margin: 8px 0;
    border-left: 3px solid var(--rta-border);
    box-shadow: var(--rta-shadow-sm);
    transition: border-color 0.15s ease, box-shadow 0.15s ease;
}
.issue-card:hover {
    border-color: var(--rta-border-strong);
    box-shadow: var(--rta-shadow-md);
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
.issue-card .ic-line {
    font-size: 11px; color: var(--rta-muted); font-weight: 500;
    margin-left: auto;
    font-family: 'JetBrains Mono', monospace;
}
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
    box-shadow: var(--rta-shadow-sm);
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

/* ── Result surfaces — tables / dataframes stay crisp ────────── */
[data-testid="stTable"] table {
    font-size: 13px;
    border-collapse: collapse;
}
[data-testid="stTable"] th {
    font-size: 12px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: var(--rta-muted);
    background: var(--rta-panel);
    border-bottom: 1px solid var(--rta-border);
    padding: 8px 12px;
}
[data-testid="stTable"] td {
    padding: 8px 12px;
    border-bottom: 1px solid var(--rta-border);
    color: var(--rta-ink);
}
[data-testid="stTable"] tr:hover td { background: var(--rta-panel); }
[data-testid="stDataFrame"] { border: 1px solid var(--rta-border); border-radius: var(--rta-radius-sm); overflow: hidden; }

/* ── Section headers — crisp left-rule accent ─────────────────── */
.stMarkdown div:has(> div[style*="width:3px"]) { }


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
    border: 1px solid var(--rta-ink) !important;
    border-radius: 8px !important;
    font-weight: 600 !important;
    font-size: 14px !important;
    padding: 10px 22px !important;
    box-shadow: var(--rta-shadow-sm) !important;
    transition: all 0.15s ease !important;
}
.stButton > button[kind="primary"]:hover {
    background: #1c1c1c !important;
    box-shadow: var(--rta-shadow-md) !important;
    transform: translateY(-1px);
}
.stButton > button[kind="primary"]:active {
    transform: translateY(0);
    box-shadow: var(--rta-shadow-sm) !important;
}
.stButton > button[kind="primary"]:focus-visible {
    box-shadow: var(--rta-focus-ring) !important;
}
.stButton > button[kind="secondary"] {
    border-radius: 8px !important;
    border: 1px solid var(--rta-border-strong) !important;
    background: var(--rta-bg) !important;
    color: var(--rta-ink) !important;
    font-weight: 600 !important;
    font-size: 14px !important;
    transition: all 0.15s ease !important;
}
.stButton > button[kind="secondary"]:hover {
    border-color: var(--rta-ink) !important;
    background: var(--rta-panel) !important;
}
.stDownloadButton > button {
    border-radius: 8px !important;
    font-weight: 600 !important;
    border: 1px solid var(--rta-border-strong) !important;
    transition: all 0.15s ease !important;
}
.stDownloadButton > button:hover {
    border-color: var(--rta-ink) !important;
    background: var(--rta-panel) !important;
}

/* ── Native input surfaces — consistent, readable ────────────── */
.stTextArea textarea,
.stTextInput input,
[data-testid="stTextInput"] input,
[data-testid="stTextArea"] textarea {
    background: var(--rta-bg) !important;
    border: 1px solid var(--rta-border) !important;
    border-radius: var(--rta-radius-sm) !important;
    font-family: 'JetBrains Mono', 'Inter', monospace !important;
    font-size: 13px !important;
    color: var(--rta-ink) !important;
    line-height: 1.6 !important;
    transition: border-color 0.15s ease, box-shadow 0.15s ease !important;
}
.stTextArea textarea:focus,
.stTextInput input:focus,
[data-testid="stTextInput"] input:focus,
[data-testid="stTextArea"] textarea:focus {
    border-color: var(--rta-accent) !important;
    box-shadow: var(--rta-focus-ring) !important;
}
.stTextArea textarea::placeholder,
.stTextInput input::placeholder,
[data-testid="stTextInput"] input::placeholder,
[data-testid="stTextArea"] textarea::placeholder {
    color: var(--rta-muted) !important;
    opacity: 0.75;
}

.stSelectbox [data-baseweb="select"] > div {
    border: 1px solid var(--rta-border) !important;
    border-radius: var(--rta-radius-sm) !important;
    background: var(--rta-bg) !important;
    font-size: 13.5px !important;
    min-height: 38px;
}
.stSelectbox [data-baseweb="select"] > div:focus-within {
    border-color: var(--rta-accent) !important;
    box-shadow: var(--rta-focus-ring) !important;
}

.stNumberInput [data-baseweb="input"] {
    border: 1px solid var(--rta-border) !important;
    border-radius: var(--rta-radius-sm) !important;
    background: var(--rta-bg) !important;
    font-size: 13.5px !important;
}

[data-testid="stFileUploader"] section {
    background: var(--rta-panel) !important;
    border: 1px dashed var(--rta-border-strong) !important;
    border-radius: var(--rta-radius-sm) !important;
}
[data-testid="stFileUploader"] section:hover {
    border-color: var(--rta-accent) !important;
}
[data-testid="stFileUploader"] button {
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
    box-shadow: var(--rta-shadow-sm) !important;
}
.streamlit-expanderHeader {
    font-weight: 600 !important;
    font-size: 14px !important;
    padding: 4px 2px !important;
}

/* ── Metrics (native st.metric) styled as flat tiles ─────────── */
[data-testid="stMetric"] {
    background: var(--rta-bg);
    border: 1px solid var(--rta-border);
    border-radius: 12px;
    padding: 14px 16px;
    box-shadow: var(--rta-shadow-sm);
}
[data-testid="stMetric"] [data-testid="stMetricValue"] {
    font-weight: 800;
    font-variant-numeric: tabular-nums;
}

/* ── Tool home / capability catalog ──────────────────────────── */
.home-hero { padding: 6px 0 2px 0; }
.home-hero .hh-eyebrow {
    font-size: 12px; font-weight: 700;
    color: var(--rta-accent); text-transform: uppercase;
    letter-spacing: 0.08em; margin-bottom: 8px;
}
.home-hero h2 {
    font-size: 26px; font-weight: 800;
    margin: 0 0 8px 0; letter-spacing: -0.02em;
    color: var(--rta-ink);
}
.home-hero p { font-size: 15px; color: var(--rta-ink-dim); margin: 0; max-width: 680px; line-height: 1.6; }
.home-group { margin-top: 30px; }
.home-group .hg-label {
    font-size: 12.5px; font-weight: 700; text-transform: uppercase;
    letter-spacing: 0.09em; color: var(--rta-muted); margin-bottom: 12px;
}
/* Equal-height rows: columns stretch, card fills, button anchors bottom.
   Scoped via :has(.home-card) so only the catalog grid is affected —
   regular tool columns (upload rows, metric tiles) keep their layout. */
[data-testid="stColumn"]:has(.home-card) { display: flex; flex-direction: column; }
[data-testid="stColumn"]:has(.home-card) > div { flex: 1 1 auto; display: flex; flex-direction: column; min-height: 0; }
/* The markdown wrapper chain grows so the card fills the row height… */
[data-testid="stColumn"]:has(.home-card) > div > div:has(.home-card) { flex: 1 1 auto; display: flex; flex-direction: column; min-height: 0; }
[data-testid="stColumn"]:has(.home-card) > div > div:has(.home-card) > div { flex: 1 1 auto; display: flex; flex-direction: column; min-height: 0; }
[data-testid="stColumn"]:has(.home-card) > div > div:has(.home-card) > div > div { flex: 1 1 auto; display: flex; flex-direction: column; min-height: 0; }
[data-testid="stColumn"]:has(.home-card) [data-testid="stMarkdownContainer"] { flex: 1 1 auto; display: flex; flex-direction: column; min-height: 0; }
[data-testid="stColumn"]:has(.home-card) [data-testid="stMarkdownContainer"] .home-card { flex: 1 1 auto; min-height: 0; }
/* …while the button wrapper keeps natural height; the button anchors bottom.
   URL cards use st.link_button (stLinkButton) — same treatment. */
[data-testid="stColumn"]:has(.home-card) > div > div:has(.stButton),
[data-testid="stColumn"]:has(.home-card) > div > div:has(.stLinkButton) { flex: 0 0 auto; display: flex; flex-direction: column; min-height: 0; }
[data-testid="stColumn"]:has(.home-card) .stButton,
[data-testid="stColumn"]:has(.home-card) .stLinkButton { margin-top: auto; padding-top: 8px; }
[data-testid="stColumn"]:has(.home-card) [data-testid="stMarkdownContainer"] .home-card {
    flex: 1 1 auto;
}
[data-testid="stColumn"]:has(.home-card) .stButton {
    margin-top: auto;
    padding-top: 8px;
}
.home-card {
    background: var(--rta-bg);
    border: 1px solid var(--rta-border);
    border-radius: 14px;
    padding: 18px 20px;
    flex: 1;
    display: flex;
    flex-direction: column;
    box-shadow: var(--rta-shadow-sm);
    transition: border-color .15s ease, box-shadow .15s ease, transform .15s ease;
}
.home-card:hover {
    border-color: var(--rta-accent);
    box-shadow: var(--rta-shadow-md);
    transform: translateY(-2px);
}
.home-card .hc-meta { flex: 1; }
.home-card .hc-title {
    display: flex; align-items: center; gap: 8px;
    font-size: 15px; font-weight: 700;
    color: var(--rta-ink); margin-bottom: 6px;
}
.home-card .hc-what {
    font-size: 13px; color: var(--rta-ink-dim);
    line-height: 1.55; margin-bottom: 10px;
}
.home-card .hc-meta { font-size: 12px; color: var(--rta-muted); line-height: 1.75; }
.home-card .hc-meta b { color: var(--rta-ink-dim); font-weight: 600; }
.home-card .hc-next {
    font-size: 12px; color: var(--rta-accent);
    margin-top: 8px; font-weight: 500;
}
.trust-line {
    margin-top: 30px; padding: 12px 16px;
    background: var(--rta-panel);
    border: 1px solid var(--rta-border);
    border-radius: 12px;
    font-size: 13px; color: var(--rta-ink-dim);
    line-height: 1.6;
    box-shadow: var(--rta-shadow-sm);
}
.trust-line b { color: var(--rta-ink-dim); }

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
    --rta-border-strong: #3f3f46;
    --rta-accent: #4ade80;
    --rta-accent-soft: rgba(74,222,128,0.10);
    --rta-shadow-sm: 0 1px 2px rgba(0,0,0,0.4);
    --rta-shadow-md: 0 4px 10px -2px rgba(0,0,0,0.5);
    --rta-shadow-lg: 0 12px 24px -6px rgba(0,0,0,0.6);
    --rta-focus-ring: 0 0 0 3px rgba(74,222,128,0.25);

    .stTabs [data-baseweb="tab-list"] { background: #131314; border-color: #26262a; }
    .stTabs [data-baseweb="tab"] { color: #a8a29e; }
    .stTabs [data-baseweb="tab"]:hover { color: #f5f5f4; background: rgba(255,255,255,0.06); }
    .stTabs [aria-selected="true"] { color: #f5f5f4 !important; background: #0c0c0d !important; box-shadow: 0 1px 3px rgba(0,0,0,0.5) !important; }

    .sdc-header { background: linear-gradient(180deg, #0c0c0d 0%, #101012 130%); border-bottom-color: #26262a; }
    .sdc-header h1 { color: #f5f5f4; }
    .sdc-tagline { color: #a8a29e; }
    .sdc-version-badge { background: #131314; border-color: #26262a; color: #a8a29e; box-shadow: 0 1px 2px rgba(0,0,0,0.4); }
    .sdc-nav a { color: #a8a29e; }
    .sdc-nav a:hover { color: #f5f5f4; background: #0c0c0d; border-color: #26262a; }
    .nav-subgroup-label { color: #a8a29e; }
    .nav-link { color: #a8a29e; }
    .nav-link:hover { color: #f5f5f4; background: #0c0c0d; border-color: #26262a; }

    .metric-card { background: #131314; border-color: #26262a; box-shadow: 0 1px 2px rgba(0,0,0,0.4); }
    .metric-card:hover { border-color: #3f3f46; box-shadow: 0 4px 10px -2px rgba(0,0,0,0.5); }
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

    .status-banner { box-shadow: 0 1px 2px rgba(0,0,0,0.3); }
    .issue-card { box-shadow: 0 1px 2px rgba(0,0,0,0.3); }
    .issue-card:hover { border-color: #3f3f46; box-shadow: 0 4px 10px -2px rgba(0,0,0,0.5); }

    .stTextArea textarea, .stTextInput input,
    [data-testid="stTextInput"] input, [data-testid="stTextArea"] textarea {
        background: #0c0c0d !important;
        border-color: #26262a !important;
        color: #f5f5f4 !important;
    }
    .stTextArea textarea:focus, .stTextInput input:focus,
    [data-testid="stTextInput"] input:focus, [data-testid="stTextArea"] textarea:focus {
        border-color: #4ade80 !important;
    }
    .stSelectbox [data-baseweb="select"] > div { background: #0c0c0d !important; border-color: #26262a !important; }
    .stNumberInput [data-baseweb="input"] { background: #0c0c0d !important; border-color: #26262a !important; }
    [data-testid="stFileUploader"] section { background: #131314 !important; border-color: #3f3f46 !important; }
    [data-testid="stTable"] th { background: #131314; color: #78716c; }
    [data-testid="stTable"] td { color: #f5f5f4; }
    [data-testid="stTable"] tr:hover td { background: #131314; }
    [data-testid="stMetric"] { box-shadow: 0 1px 2px rgba(0,0,0,0.3); }
    [data-testid="stExpander"] { box-shadow: 0 1px 2px rgba(0,0,0,0.3) !important; }

    .stButton > button[kind="secondary"] { background: #0c0c0d !important; color: #f5f5f4 !important; border-color: #3f3f46 !important; }
    .stButton > button[kind="secondary"]:hover { border-color: #f5f5f4 !important; }
    .stDownloadButton > button { border-color: #3f3f46 !important; }

    .home-card { background: #131314; border-color: #26262a; box-shadow: 0 1px 2px rgba(0,0,0,0.4); }
    .home-card:hover { border-color: #3f3f46; box-shadow: 0 4px 10px -2px rgba(0,0,0,0.5); }

    .home-hero h2 { color: #f5f5f4; }
    .home-hero p { color: #a8a29e; }
    .home-group .hg-label { color: #78716c; }
    .home-card { background: #131314; border-color: #26262a; }
    .home-card:hover { border-color: #3f3f46; }
    .home-card .hc-title { color: #f5f5f4; }
    .home-card .hc-what { color: #a8a29e; }
    .home-card .hc-meta { color: #78716c; }
    .home-card .hc-meta b { color: #a8a29e; }
    .home-card .hc-next { color: #4ade80; }
    .trust-line { background: #131314; border-color: #26262a; color: #a8a29e; }
    .trust-line b { color: #a8a29e; }

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

/* ── Dark: full-app surface + native widget text ─────────────────────────────
   data-theme is set on <html> by the in-app toggle, so these target the whole
   app — including the native app background and widget labels that Streamlit
   paints itself (they would otherwise stay light on a dark surface). */
html[data-theme="dark"] {
    --background-color: #0c0c0d !important;
    --secondary-background-color: #131314 !important;
    --text-color: #f5f5f4 !important;
    --sidebar-background-color: #0a0a0a !important;
}
html[data-theme="dark"] body,
html[data-theme="dark"] .stApp,
html[data-theme="dark"] .appview-container,
html[data-theme="dark"] [data-testid="stAppViewContainer"] {
    background-color: #0c0c0d !important;
}
html[data-theme="dark"] [data-testid="stHeader"] {
    background-color: transparent !important;
}
html[data-theme="dark"] [data-testid="stWidgetLabel"],
html[data-theme="dark"] [data-testid="stWidgetLabel"] p {
    color: #a8a29e !important;
}
html[data-theme="dark"] [data-testid="stRadio"] label p,
html[data-theme="dark"] [data-testid="stCheckbox"] label p,
html[data-theme="dark"] [data-testid="stSelectbox"] [data-baseweb="select"] span {
    color: #d4d4d8 !important;
}
html[data-theme="dark"] .stAlert {
    color: #d4d4d8 !important;
}
html[data-theme="dark"] [data-testid="stExpander"] summary,
html[data-theme="dark"] .streamlit-expanderHeader {
    color: #f5f5f4 !important;
}
html[data-theme="dark"] [data-testid="stCode"] pre,
html[data-theme="dark"] [data-testid="stCodeBlock"] pre {
    background-color: #131314 !important;
    color: #e7e5e4 !important;
    border: 1px solid #26262a !important;
}
html[data-theme="dark"] .stButton > button:not([kind="primary"]):not([kind="secondary"]),
html[data-theme="dark"] [data-testid="stSidebar"] .stButton > button {
    background: #131314 !important;
    color: #f5f5f4 !important;
    border: 1px solid #26262a !important;
}
html[data-theme="dark"] .stButton > button:not([kind="primary"]):not([kind="secondary"]):hover,
html[data-theme="dark"] [data-testid="stSidebar"] .stButton > button:hover {
    background: #1a1a1b !important;
    border-color: #3f3f46 !important;
}
html[data-theme="dark"] .stDownloadButton > button {
    background: #131314 !important;
    color: #f5f5f4 !important;
    border-color: #3f3f46 !important;
}
</style>
"""


MODULE_ICONS = {
    "checker": "🛡",
    "mmc": "🔲",
    "clock_relations": "🕐",
    "constraint_diff": "🔍",
}

# Tab order in app.py (must match the st.tabs(...) list)
TAB_INDEX = {
    "validate": 0, "generator": 1, "linter": 2, "converter": 3,
    "corners": 4, "mmc": 5, "diff": 6, "clock": 7, "coverage": 8,
    "interactions": 9, "readiness": 10, "rules": 11,
}

BUSINESS_URL = "https://rama-l7.github.io/rta-constraint-intelligence/rta/business-site/"
DOCS_URL = "https://github.com/RAMA-L7/rta-constraint-intelligence/tree/main/rta/docs"

# Sidebar capability rail — mirrors the business-site order. target is
# ("tab", key) | ("view", name) | ("url", url)
NAV_GROUPS = [
    ("Analysis capabilities", [
        ("🛡 SDC Validation", ("tab", "validate")),
        ("🕐 Clock Intelligence", ("tab", "clock")),
        ("🧬 Design Context", ("tab", "validate")),
        ("📊 Constraint Coverage", ("tab", "coverage")),
        ("🔗 Constraint Interactions", ("tab", "interactions")),
        ("✅ Readiness", ("tab", "readiness")),
        ("🤖 CI Quality Gates", ("url", BUSINESS_URL + "features/ci.html")),
    ]),
    ("Engineering tools", [
        ("⚙️ Generator", ("tab", "generator")),
        ("📝 Linter", ("tab", "linter")),
        ("🔄 Converter", ("tab", "converter")),
        ("🔍 Diff", ("tab", "diff")),
        ("🔲 Corners / MMC", ("tab", "corners")),
        ("📋 Rules Reference", ("tab", "rules")),
        ("🧪 Test Drive", ("view", "test_drive")),
    ]),
    ("Output & Knowledge", [
        ("📄 Reports", ("url", DOCS_URL)),
        ("🛡️ Trust", ("url", BUSINESS_URL)),
        ("📚 Documentation", ("url", DOCS_URL)),
        ("💬 Feedback", ("view", "feedback")),
    ]),
]


def inject_css():
    """Inject the Ṛta theme (light, flat, single-accent — Arcade-docs DNA).

    Also honors the in-app dark-mode toggle: when ``force_dark`` is set in
    session state, a tiny script flips the app's ``data-theme`` attribute on
    the main document so the theme's dark-mode block applies regardless of the
    OS/browser theme.

    The script runs inside a Streamlit component iframe (``st.components.v1.html``
    — the component sandbox includes ``allow-same-origin``, which lets it reach
    ``window.parent.document``). ``st.html(unsafe_allow_javascript=True)`` is not
    used here because Streamlit 1.56's sanitizer strips ``<script>`` before it
    mounts, so the script would never run. The script is idempotent: it always
    sets or removes ``data-theme`` explicitly, so toggling back to light reliably
    clears the attribute.
    """
    st.markdown(CSS, unsafe_allow_html=True)
    force_dark = bool(st.session_state.get("force_dark"))
    # Theme is set/removed explicitly every run so the toggle reliably returns
    # to light mode (the attribute otherwise sticks in the browser DOM).
    theme_js = (
        "d.documentElement.setAttribute('data-theme','dark');"
        if force_dark
        else "d.documentElement.removeAttribute('data-theme');"
    )
    # Auto-hide the sidebar on page load (once per page load, guarded by a
    # marker on the parent window so it never fights the user after they open it).
    sidebar_js = (
        "if(!window.parent.__rtaSidebarOnce){window.parent.__rtaSidebarOnce=1;"
        "(function r(n){var sb=d.querySelector('[data-testid=\"stSidebar\"]');"
        "if(sb&&sb.getAttribute('aria-expanded')==='true'){"
        "var b=d.querySelector('[data-testid=\"stSidebarCollapseButton\"]');"
        "if(b){b.click();return;}}"
        "if(n<30){setTimeout(function(){r(n+1);},300);}})(0);}"
    )
    from streamlit.components.v1 import html as _component_html
    _component_html(
        f"<script>(function(){{var d=window.parent.document;{theme_js}{sidebar_js}}})();</script>",
        height=0,
    )


def render_header():
    """Render a compact command bar: brand block (eyebrow + title + version)
    on the left, business-site navigation on the right."""
    st.markdown(f"""
<div class="sdc-header">
    <div class="sdc-header-row">
        <div class="sdc-brand">
            <div class="rta-eyebrow">Constraint Intelligence</div>
            <div class="sdc-title-row">
                <h1>Ṛta</h1>
                <span class="sdc-version-badge">v{APP_VERSION}</span>
            </div>
        </div>
        <nav class="sdc-nav">
            <a href="{BUSINESS_URL}index.html#features" target="_blank" rel="noopener">Features</a>
            <a href="{BUSINESS_URL}index.html#why" target="_blank" rel="noopener">Why Ṛta</a>
            <a href="{BUSINESS_URL}features/rules.html" target="_blank" rel="noopener">Rules</a>
            <a href="{BUSINESS_URL}index.html#install" target="_blank" rel="noopener">Install</a>
            <a href="https://github.com/RAMA-L7/rta-constraint-intelligence" target="_blank" rel="noopener">Docs</a>
        </nav>
    </div>
    <p class="sdc-tagline">Ṛta brings order to timing intent, transforming constraints into
    trusted engineering knowledge through deterministic precision.</p>
</div>
""", unsafe_allow_html=True)


def render_sidebar():
    """Render the sidebar — minimal: brand, quick actions, What's New.

    Features live once, in the home catalog (feature-first entry); the
    sidebar intentionally does not duplicate them.
    """
    with st.sidebar:
        st.markdown(f"""
<div class="sidebar-brand">
    <h3>Ṛta</h3>
    <p>v{APP_VERSION} · Constraint Intelligence Platform</p>
</div>
""", unsafe_allow_html=True)

        # ── Home ───────────────────────────────────────────────────────
        if st.button("🏠 Home",
                     use_container_width=True,
                     key="sidebar_home"):
            st.session_state.app_view = "home"
            st.rerun()

        # ── Quick actions ──────────────────────────────────────────────
        if st.button("🧪 Test Drive",
                     use_container_width=True,
                     key="sidebar_testdrive"):
            st.session_state.app_view = "test_drive"
            st.rerun()

        if st.button("💬 Feedback",
                     use_container_width=True,
                     key="sidebar_feedback"):
            st.session_state.app_view = "feedback"
            st.rerun()

        # ── Dark mode toggle ───────────────────────────────────────────
        dark = st.session_state.get("force_dark", False)
        if st.button("🌙 Dark mode" if not dark else "☀️ Light mode",
                     use_container_width=True,
                     key="sidebar_dark"):
            st.session_state["force_dark"] = not dark
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
