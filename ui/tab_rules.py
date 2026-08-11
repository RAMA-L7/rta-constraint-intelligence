"""
📋 Rules Reference Tab — EDA-style SDC code lookup and documentation.
"""

import streamlit as st
import json
from rules_registry import APP_VERSION, get_all_rules
from ui.components import (
    download_button, MODULE_ICONS, section_header,
    metric_cards_row, status_banner,
)
from ui.feedback import feedback_widget


def render():
    all_rules = get_all_rules()
    section_header("📋 SDC Rules Reference", f"All {len(all_rules)} rule codes across 4 modules.")

    col1, col2, col3 = st.columns(3)
    with col1:
        search = st.text_input("🔍 Search", placeholder="SDC-060, clock, derate...", key="rules_search")
    with col2:
        modules = ["All"] + sorted(set(r.module for r in all_rules))
        mod_filter = st.selectbox("Module", modules, key="rules_mod")
    with col3:
        sevs = ["All", "error", "warning", "info", "fatal"]
        sev_filter = st.selectbox("Severity", sevs, key="rules_sev")

    filtered = all_rules
    if search:
        q = search.lower()
        filtered = [r for r in filtered if q in r.code.lower() or q in r.short_name.lower()
                    or q in r.description.lower() or q in r.why_matters.lower()]
    if mod_filter != "All":
        filtered = [r for r in filtered if r.module == mod_filter]
    if sev_filter != "All":
        filtered = [r for r in filtered if r.severity == sev_filter]

    err_count = len([r for r in filtered if r.severity == "error"])
    warn_count = len([r for r in filtered if r.severity == "warning"])
    fatal_count = len([r for r in filtered if r.severity == "fatal"])

    metric_cards_row([
        ("Filtered", len(filtered), "🔍", "blue"),
        ("Errors", err_count, "🔴", "red"),
        ("Warnings", warn_count, "🟡", "yellow"),
        ("Fatal", fatal_count, "💀", "red"),
    ])

    rules_json = json.dumps([{
        "code": r.code, "severity": r.severity, "name": r.short_name,
        "module": r.module, "description": r.description,
        "why_matters": r.why_matters, "fix": r.fix,
    } for r in filtered], indent=2)

    col_d1, col_d2 = st.columns(2)
    with col_d1:
        download_button(rules_json, f"sdc_rules_{'filtered' if search else 'all'}.json",
                        "application/json", "Download JSON", key="rules_json")
    with col_d2:
        md_lines = ["| Code | Severity | Module | Name |", "|------|----------|--------|------|"]
        for r in filtered:
            md_lines.append(f"| {r.code} | {r.severity} | {r.module} | {r.short_name} |")
        download_button("\n".join(md_lines), "sdc_rules.md", "text/markdown", "Download Markdown", key="rules_md")

    st.divider()

    if not filtered:
        status_banner("No rules match your filters.", "info")
        return

    from itertools import groupby
    filtered_sorted = sorted(filtered, key=lambda r: r.module)
    for module, group in groupby(filtered_sorted, key=lambda r: r.module):
        group_list = list(group)
        module_icon = MODULE_ICONS.get(module, "📦")
        with st.expander(f"{module_icon} **{module}** ({len(group_list)} rules)", expanded=True):
            for rule in group_list:
                sev_icon = {"error": "🔴", "warning": "🟡", "info": "🔵", "fatal": "💀"}.get(rule.severity, "⚪")
                with st.expander(f"{sev_icon} **{rule.code}** — {rule.short_name}"):
                    c1, c2 = st.columns([1, 2])
                    with c1:
                        st.markdown(f"**Severity:** `{rule.severity}`")
                        st.markdown(f"**Module:** `{rule.module}`")
                        st.markdown(f"**Added:** v{rule.added_version}")
                    with c2:
                        st.markdown(f"**Description:** {rule.description}")
                    st.markdown(f"**Why it matters:** {rule.why_matters}")
                    st.markdown(f"**Fix:** {rule.fix}")
                    if rule.reference_url:
                        st.markdown(f"📚 [{rule.reference_url}]({rule.reference_url})")

    # Feedback
    feedback_widget(feature="rules", key_prefix="rules")
