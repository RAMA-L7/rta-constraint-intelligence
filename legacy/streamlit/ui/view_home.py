"""
🏠 Tool Home — Ṛta capability catalog (Phase E UX).

The tool opens here, not on a results dashboard. The user answers three
questions within seconds: what is Ṛta, what can I use it for, which tool
do I need. Each card is a real entry point into the matching feature
workspace (tab or dedicated view).
"""

import streamlit as st
from .components import TAB_INDEX, BUSINESS_URL, DOCS_URL


# ── Capability catalog ────────────────────────────────────────────────────────
# Canonical Phase E grouping (PRODUCT_WORKSPACE_ARCHITECTURE_V2.md §2):
#   CORE    Validate · Generator · Linter · Converter
#   ANALYZE Clock · Coverage · Design Context · Conflicts · Readiness · Diff
#   ADVANCED Corners/MMC · Test Drive · Rules · CI
#   OUTPUT & KNOWLEDGE Reports · Trust · Documentation · Feedback
# Each card: title, code (monogram tile), what, input, does, get, next, target.
# target is ("tab", key) | ("view", name) | ("url", url)
CATALOG = [
    ("Core", [
        {
            "title": "SDC Validation", "code": "SD",
            "what": "Check an SDC for structural and constraint issues before STA.",
            "input": "SDC required · netlist optional",
            "does": "Runs the deterministic rule engine — parse, TCL resolve, all 119 rules.",
            "get": "Findings with rule codes, severity, source lines, engineering context.",
            "next": "Review clocks / coverage / conflicts / readiness.",
            "target": ("tab", "validate"),
        },
        {
            "title": "Generator", "code": "GN",
            "what": "Generate a clean, lint-valid SDC from design parameters.",
            "input": "Generation parameters only — no SDC needed",
            "does": "Builds clocks, I/O delays, exceptions, derates, and corner-aware output.",
            "get": "A complete .sdc ready to lint, check, and download.",
            "next": "Open in Validator · Lint · Download.",
            "target": ("tab", "generator"),
        },
        {
            "title": "Linter", "code": "LN",
            "what": "Format, reorganize, and clean up SDC files.",
            "input": "SDC required",
            "does": "Normalizes whitespace/ordering, detects structural issues, offers fixes.",
            "get": "Formatted SDC + a lint diff to review.",
            "next": "Download formatted SDC.",
            "target": ("tab", "linter"),
        },
        {
            "title": "Converter", "code": "CN",
            "what": "Convert SDC to JSON/YAML and back with full data preservation.",
            "input": "SDC required · target format",
            "does": "Structured lossless conversion of clocks, delays, exceptions, groups.",
            "get": "Converted file ready to download.",
            "next": "Download output.",
            "target": ("tab", "converter"),
        },
    ]),
    ("Analyze", [
        {
            "title": "Clock Intelligence", "code": "CK",
            "what": "Inventory clocks and their relationships.",
            "input": "SDC required",
            "does": "Resolves primary/generated/virtual clocks, relations, groups, hierarchies.",
            "get": "Clock inventory + relationship matrix with mismatches and missing constraints.",
            "next": "Review Coverage · Conflicts · Readiness.",
            "target": ("tab", "clock"),
        },
        {
            "title": "Constraint Coverage", "code": "CV",
            "what": "Measure which constraint categories are covered.",
            "input": "SDC required · netlist optional (design-aware)",
            "does": "39-category gap analysis plus netlist-aware port coverage when supplied.",
            "get": "Score, present/total, missing categories. Coverage is NOT correctness.",
            "next": "Review missing constraints · Validate.",
            "target": ("tab", "coverage"),
        },
        {
            "title": "Design Context", "code": "DX",
            "what": "Cross-check SDC objects against a real netlist.",
            "input": "SDC + netlist (netlist-aware mode)",
            "does": "Structural reference resolution for get_ports/get_pins/get_cells.",
            "get": "Unresolved references and design-aware findings — inside Validate.",
            "next": "Upload a netlist in Validate.",
            "target": ("tab", "validate"),
        },
        {
            "title": "Constraint Interactions", "code": "IX",
            "what": "Detect duplicate, overriding, and contradictory constraints.",
            "input": "SDC required",
            "does": "Interaction analysis across the whole command set.",
            "get": "What conflicts, where, why it matters, and what to review.",
            "next": "All findings · Readiness.",
            "target": ("tab", "interactions"),
        },
        {
            "title": "Readiness", "code": "RD",
            "what": "Aggregate checker evidence into a constraint-readiness verdict.",
            "input": "SDC required · netlist optional",
            "does": "7-dimension evaluation (Clocks, I/O, Exceptions, Coverage, Consistency, Trust, Context).",
            "get": "BLOCKED / REVIEW_REQUIRED / READY with reasons.",
            "next": "Review blockers · Report.",
            "target": ("tab", "readiness"),
        },
        {
            "title": "Diff", "code": "DF",
            "what": "Semantic diff between two SDC versions.",
            "input": "Version A SDC + Version B SDC",
            "does": "Compares clocks, periods, delays, exceptions, groups — additions/removals/modifications.",
            "get": "What changed, why it matters, what to review.",
            "next": "Open V2 in Validate · Review changes.",
            "target": ("tab", "diff"),
        },
    ]),
    ("Advanced", [
        {
            "title": "Corners / MMC", "code": "MM",
            "what": "Manage PVT corners and generate multi-corner SDCs.",
            "input": "Corner preset selection · design · clock",
            "does": "Validates corner parameters, builds the corner matrix, generates per-corner SDCs.",
            "get": "Corner list, matrix, per-corner SDCs + zip download.",
            "next": "Open a corner in Validate.",
            "target": ("tab", "corners"),
        },
        {
            "title": "Test Drive", "code": "TD",
            "what": "Run a known sample through the real Ṛta pipeline.",
            "input": "Sample choice only — no upload needed",
            "does": "Checker, linter, coverage, clocks, converter run on the real backend.",
            "get": "Real result summary — findings, coverage, clocks, readiness.",
            "next": "Open findings · clocks · coverage.",
            "target": ("view", "test_drive"),
        },
        {
            "title": "Rules Reference", "code": "RU",
            "what": "Browse the full SDC rule reference.",
            "input": "None to browse · SDC to execute",
            "does": "Searchable registry of all rules with severity and documentation.",
            "get": "Rule cards + JSON/Markdown downloads.",
            "next": "Validate with rules.",
            "target": ("tab", "rules"),
        },
        {
            "title": "CI Quality Gates", "code": "CI",
            "what": "Gate merges on lint-clean constraints — the same standard for everyone.",
            "input": "SDC + policy in your pipeline",
            "does": "Deterministic gate with exit codes and machine-readable output.",
            "get": "PASS/FAIL gate result. CI PASS ≠ timing pass.",
            "next": "See the CI guide.",
            "target": ("url", BUSINESS_URL + "features/ci.html"),
        },
    ]),
    ("Output & Knowledge", [
        {
            "title": "Reports", "code": "RP",
            "what": "HTML/JSON reports generated from real analysis data.",
            "input": "An analysis (from Validate, Coverage, Diff, …)",
            "does": "Bundles findings, severity, clocks, coverage, readiness with trust disclosures.",
            "get": "Downloadable report with real content.",
            "next": "Download · open in browser.",
            "target": ("url", DOCS_URL),
        },
        {
            "title": "Trust", "code": "TR",
            "what": "What Ṛta guarantees — and what it does not.",
            "input": "None",
            "does": "Evidence-backed facts: deterministic, offline, no LLM; boundaries vs STA.",
            "get": "Clear boundary statements — never marketing language.",
            "next": "Read the trust section.",
            "target": ("url", BUSINESS_URL),
        },
        {
            "title": "Documentation", "code": "DO",
            "what": "Guides, CLI reference, and examples.",
            "input": "None",
            "does": "I want to do X — where do I go (validate, generate, compare, run CI…).",
            "get": "Docs with real links into the product.",
            "next": "Open a capability.",
            "target": ("url", DOCS_URL),
        },
        {
            "title": "Feedback", "code": "FB",
            "what": "Tell the team what to improve.",
            "input": "Rating + comment",
            "does": "Saves feedback to the public dashboard.",
            "get": "Honest confirmation after the backend accepts.",
            "next": "Submit feedback.",
            "target": ("view", "feedback"),
        },
    ]),
]

# ── Navigation helpers ─────────────────────────────────────────────────────────


def _navigate(target):
    kind, key = target
    if kind == "tab":
        st.session_state["_jump_tab"] = TAB_INDEX[key]
        st.session_state["app_view"] = "features"
    elif kind == "view":
        st.session_state["app_view"] = key
    else:  # url
        st.markdown(f"[Open →]({key})", unsafe_allow_html=True)
        return
    st.rerun()


def _input_chips(raw: str) -> str:
    """Split an input string on '·' into styled chips."""
    parts = [p.strip() for p in raw.split("·") if p.strip()]
    return "".join(f'<span class="hc-chip">{p}</span>' for p in parts)


def render():
    """Render the tool home: positioning, CTAs, catalog, trust line."""
    st.markdown(
        """
<div class="home-hero">
    <div class="hh-eyebrow"><span class="hh-pip"></span>Ṛta Engineering Platform</div>
    <h2>Constraint intelligence for block-level design.</h2>
    <p>Validate, generate, lint, convert, and review SDC with a deterministic,
    offline engine — 119 rules, no LLM. Know what's wrong, what's missing, and
    what's covered before STA.</p>
</div>
""",
        unsafe_allow_html=True,
    )

    # ── Entry helpers (beginner path) ──────────────────────────────────────
    c1, c2, c3 = st.columns([1, 1, 1.35])
    if c1.button("Start with Test Drive", type="secondary", use_container_width=True, key="home_testdrive"):
        st.session_state["app_view"] = "test_drive"
        st.rerun()
    if c2.button("Validate an SDC", type="primary", use_container_width=True, key="home_validate"):
        st.session_state["_jump_tab"] = TAB_INDEX["validate"]
        st.session_state["app_view"] = "features"
        st.rerun()
    c3.caption("Every tool runs on the real deterministic engine — no samples faked.")

    # ── Capability catalog ─────────────────────────────────────────────────
    for group, cards in CATALOG:
        st.markdown(
            f'<div class="home-group"><div class="hg-label">{group} <span class="hg-count">{len(cards)}</span></div></div>',
            unsafe_allow_html=True,
        )
        # True 3-per-row grid: chunk cards row-major so each row's cards are
        # equal height and the "Open →" buttons align (a single st.columns(3)
        # with i % 3 cycles cards into fixed columns = masonry, not a grid).
        for row_start in range(0, len(cards), 3):
            cols = st.columns(3)
            for col, card in zip(cols, cards[row_start:row_start + 3]):
                with col:
                    st.markdown(
                        f"""
<div class="home-card">
    <div class="hc-top">
        <span class="hc-tile">{card['code']}</span>
        <span class="hc-title">{card['title']}</span>
    </div>
    <div class="hc-what">{card['what']}</div>
    <div class="hc-inputs">{_input_chips(card['input'])}</div>
    <details class="hc-details">
        <summary>More details</summary>
        <div class="hc-meta">
            <div class="hc-row"><b>Does</b> {card['does']}</div>
            <div class="hc-row"><b>Get</b> {card['get']}</div>
            <div class="hc-row"><b>Next</b> {card['next']}</div>
        </div>
    </details>
</div>
""",
                        unsafe_allow_html=True,
                    )
                    kind, key = card["target"]
                    if kind == "url":
                        st.link_button(
                            f"Open {card['title']} →", key,
                            key=f"open_{card['title'].lower().replace(' ', '_')}",
                            use_container_width=True,
                        )
                    else:
                        if st.button(f"Open {card['title']} →", key=f"open_{card['title'].lower().replace(' ', '_')}",
                                     use_container_width=True):
                            _navigate(card["target"])

    # ── Standing trust line ────────────────────────────────────────────────
    st.markdown(
        """
<div class="trust-line">
    <b>Deterministic · offline · no LLM.</b>
    Readiness is a constraint-quality review, <b>not an STA timing signoff</b> —
    READY does not mean setup/hold passes, and coverage is not correctness.
</div>
""",
        unsafe_allow_html=True,
    )
