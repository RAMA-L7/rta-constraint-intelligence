"""
Feedback System for Ṛta.
Thumbs up/down + comment feedback with public dashboard.
"""

import json
import os
from datetime import datetime
from dataclasses import dataclass, field, asdict
from typing import List, Optional

# NOTE: streamlit and ui.components are imported lazily inside the widget/dashboard
# functions. The storage API here (save_feedback/load_feedback/FeedbackEntry) is
# used by the stdlib-only API server (rta/api/api_server.py) and by the
# CLI-level comprehensive test (tests/run_comprehensive_test.py), which do not
# install streamlit — importing this module must never require it.

# ── Storage ────────────────────────────────────────────────────────────────────

FEEDBACK_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
FEEDBACK_FILE = os.path.join(FEEDBACK_DIR, "feedback.json")


def _ensure_dir():
    """Ensure the data directory exists."""
    os.makedirs(FEEDBACK_DIR, exist_ok=True)


# ── Data Model ─────────────────────────────────────────────────────────────────

@dataclass
class FeedbackEntry:
    """A single feedback submission."""
    timestamp: str
    feature: str           # "test_drive" | "checker" | "linter" | etc.
    rating: int            # 1 = thumbs up, -1 = thumbs down, 0 = skip
    comment: str = ""
    sdc_file: str = ""
    results_summary: str = ""


def load_feedback() -> List[FeedbackEntry]:
    """Load all feedback entries from JSON file."""
    _ensure_dir()
    if not os.path.exists(FEEDBACK_FILE):
        return []
    try:
        with open(FEEDBACK_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return [FeedbackEntry(**entry) for entry in data]
    except (json.JSONDecodeError, KeyError, TypeError):
        return []


def save_feedback(entry: FeedbackEntry):
    """Append a feedback entry to the JSON file."""
    _ensure_dir()
    entries = load_feedback()
    entries.append(entry)
    with open(FEEDBACK_FILE, "w", encoding="utf-8") as f:
        json.dump([asdict(e) for e in entries], f, indent=2, ensure_ascii=False)


# ── Feedback Widget ────────────────────────────────────────────────────────────

SAMPLE_SDCS = {
    "✅ Real Design (RISC-V Core)": "samples/real_design_full.sdc",
    "🐛 Buggy — Missing Clocks": "samples/buggy_no_clocks.sdc",
    "⚠️ Warnings — Clock Groups": "samples/warning_heavy.sdc",
    "📝 Malformed SDC": "samples/edge_case_malformed.sdc",
    "📭 Empty SDC": "samples/edge_case_empty.sdc",
    "🔬 Edge Values": "samples/edge_case_extreme_values.sdc",
    # Realistic two-clock block with a matching netlist — the design-aware
    # tier (SDC-055..059, SDC-064..066) is only demonstrable with a netlist,
    # and this sample is the one that teaches the validate -> diff -> gate
    # -> report workflow (see engineer_test_kit/18_test_drive).
    "🔬 DMA Engine Block (realistic, 2 clocks)": "engineer_test_kit/18_test_drive/dma_engine.sdc",
}

# Companion netlist for samples that ship one (design-aware analysis). Keyed
# by the SAMPLE_SDCS display name.
SAMPLE_NETLISTS = {
    "🔬 DMA Engine Block (realistic, 2 clocks)": "engineer_test_kit/18_test_drive/dma_engine_top.v",
}

# Baseline readiness snapshot for the realistic sample (saved from the
# known-good V1 revision), so the CI-gate step of the workflow can run
# out of the box in the Test Drive.
SAMPLE_BASELINES = {
    "🔬 DMA Engine Block (realistic, 2 clocks)": "engineer_test_kit/18_test_drive/baseline.json",
}


def _repo_path(rel: str) -> str:
    """Resolve a repository-relative path from this module (4 dirname levels)."""
    return os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), rel)


def get_sample_sdc(name: str) -> tuple:
    """Load a sample SDC file by display name.

    Returns (text, filename) or (None, None) if not found.
    """
    # 4 dirname() levels: legacy/streamlit/ui/feedback.py -> repo root; the
    # samples/ tree lives at the repository root (unchanged by the Phase 9 move).
    path = _repo_path(SAMPLE_SDCS.get(name, ""))
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read(), os.path.basename(path)
    except (FileNotFoundError, IOError):
        return None, None


def get_sample_netlist(name: str) -> tuple:
    """Load a companion netlist for a sample, if one ships with it.

    Returns (text, filename) or (None, None) when the sample has no netlist.
    """
    rel = SAMPLE_NETLISTS.get(name, "")
    if not rel:
        return None, None
    path = _repo_path(rel)
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read(), os.path.basename(path)
    except (FileNotFoundError, IOError):
        return None, None


def get_sample_baseline(name: str) -> str:
    """Path of a companion readiness baseline for a sample, or "" if none."""
    rel = SAMPLE_BASELINES.get(name, "")
    return _repo_path(rel) if rel else ""


def feedback_widget(
    feature: str = "test_drive",
    sdc_file: str = "",
    results_summary: str = "",
    key_prefix: str = "fb",
):
    """Render a ChatGPT-style feedback widget after results.

    Two lines: [Yes helpful] [No, not helpful]  →  optional comment + submit.
    """
    import streamlit as st
    from .components import status_banner

    st.divider()
    st.caption("How was this analysis?")

    fb_key = f"{key_prefix}_rating"
    if fb_key not in st.session_state:
        st.session_state[fb_key] = 0

    # Row of simple text buttons (ChatGPT style)
    b1, b2, b3 = st.columns([1, 1, 4])
    with b1:
        if st.button("Yes, helpful", key=f"{key_prefix}_up",
                     type="primary" if st.session_state[fb_key] == 1 else "secondary",
                     use_container_width=True):
            st.session_state[fb_key] = 1
    with b2:
        if st.button("No, not helpful", key=f"{key_prefix}_down",
                     type="primary" if st.session_state[fb_key] == -1 else "secondary",
                     use_container_width=True):
            st.session_state[fb_key] = -1

    if st.session_state[fb_key] != 0:
        comment = st.text_area(
            "What could be improved? (optional)",
            key=f"{key_prefix}_comment",
            height=60,
            placeholder="e.g. 'The coverage score helped me identify missing constraints...'",
        )
        if st.button("Submit", key=f"{key_prefix}_submit", use_container_width=True):
            entry = FeedbackEntry(
                timestamp=datetime.now().isoformat(),
                feature=feature,
                rating=st.session_state[fb_key],
                comment=comment.strip(),
                sdc_file=sdc_file,
                results_summary=results_summary,
            )
            save_feedback(entry)
            st.session_state[fb_key] = 0
            st.balloons()
            status_banner("Thank you for your feedback!", "success")
            st.rerun()


# ── Feedback Dashboard ────────────────────────────────────────────────────────

FEATURE_ICONS = {
    "test_drive": "🧪",
    "checker": "🛡",
    "linter": "📝",
    "converter": "🔄",
    "generator": "⚙️",
    "diff": "🔍",
    "coverage": "📊",
}


def render_dashboard():
    """Render the public feedback dashboard."""
    import streamlit as st
    from .components import section_header, status_banner, metric_cards_row

    section_header("📊 Community Feedback", "Transparent — all feedback is visible to every visitor.")

    entries = load_feedback()

    if not entries:
        status_banner("No feedback yet. Use the 🧪 Test Drive tab to try Ṛta and share your thoughts!", "info")
        return

    # ── Summary metrics ──────────────────────────────────────────────────────
    total = len(entries)
    positive = sum(1 for e in entries if e.rating == 1)
    negative = sum(1 for e in entries if e.rating == -1)
    skipped = sum(1 for e in entries if e.rating == 0)
    ratio = f"{positive / total * 100:.0f}%" if total else "N/A"

    metric_cards_row([
        ("Total Responses", total, "💬", "blue"),
        ("Positive", positive, "👍", "green"),
        ("Negative", negative, "👎", "red"),
        ("Satisfaction", ratio, "📈", "green" if positive > negative else "yellow"),
    ])

    # ── Recent comments highlight ────────────────────────────────────────────
    comments = [e for e in entries if e.comment.strip()][-5:]
    if comments:
        st.markdown("### 💬 What Users Are Saying")
        for e in reversed(comments):
            icon = "👍" if e.rating == 1 else "👎" if e.rating == -1 else "⏭️"
            feature_icon = FEATURE_ICONS.get(e.feature, "🔧")
            st.markdown(f"""
<div class="issue-card ic-{'success' if e.rating == 1 else 'error' if e.rating == -1 else 'info'}">
    <div class="ic-header">
        <span>{icon}</span>
        <span class="ic-code">{feature_icon} {e.feature}</span>
        <span style="font-size:11px;color:#94a3b8;margin-left:auto">{e.timestamp[:19].replace('T', ' ')}</span>
    </div>
    <div class="ic-msg">"{e.comment}"</div>
    <div style="font-size:11px;color:#64748b;margin-top:4px">File: {e.sdc_file}</div>
</div>
""", unsafe_allow_html=True)

    # ── All feedback table ───────────────────────────────────────────────────
    st.markdown("### 📋 All Feedback")
    st.caption(f"{total} entries — sorted by newest first")

    fb_data = []
    for e in reversed(entries):
        fb_data.append({
            "Date": e.timestamp[:19].replace("T", " "),
            "Rating": "👍" if e.rating == 1 else "👎" if e.rating == -1 else "⏭️",
            "Feature": e.feature,
            "File": os.path.basename(e.sdc_file) if e.sdc_file else "-",
            "Comment": e.comment[:80] + ("..." if len(e.comment) > 80 else "") if e.comment else "-",
            "Results": e.results_summary[:50] if e.results_summary else "-",
        })

    # Show as expandable table
    with st.expander(f"View all {total} feedback entries", expanded=True):
        for row in fb_data:
            st.markdown(
                f"`{row['Date']}` {row['Rating']} **{row['Feature']}** · {row['File']}  \n"
                f"> _{row['Comment']}_",
                unsafe_allow_html=True,
            )
            st.caption(f"Results: {row['Results']}")
