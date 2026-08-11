"""
📝 Linter Tab — EDA-style SDC formatting and reorganization.
"""

import streamlit as st
from .components import (
    sdc_upload_area, download_button, section_header,
    metric_cards_row, status_banner, issue_card, styled_code_block,
)
from .feedback import feedback_widget
from linter import lint_sdc


def render():
    section_header("📝 SDC Linter", "Reorganize SDC files with consistent section ordering, spacing, and formatting.")

    sdc_text, filename = sdc_upload_area("lint")

    if not sdc_text:
        status_banner("Upload an SDC file or paste SDC text above to get started.", "info")
        return

    col1, col2 = st.columns([1, 3])
    with col1:
        fix_mode = st.checkbox("✅ Apply fixes (reorganize)", value=True, key="lint_fix")
        check_mode = st.checkbox("🔍 Check-only (show issues)", value=False, key="lint_check")
    with col2:
        st.caption("Check mode detects issues without modifying. Fix mode reorganizes into standard SDC section order.")

    if st.button("📝 Run Linter", type="primary", use_container_width=True, key="lint_btn"):
        with st.spinner("Linting SDC..."):
            result = lint_sdc(sdc_text, fix=fix_mode and not check_mode)

        st.divider()

        color_w = "red" if result.warnings > 5 else "yellow" if result.warnings > 0 else "green"
        metric_cards_row([
            ("Lines (original)", result.line_count_original, "📏", "blue"),
            ("Warnings", result.warnings, "⚠️", color_w),
            ("Fixes Applied", result.fixed, "🔧", "green" if result.fixed else "blue"),
        ])

        if result.warnings > 0:
            status_banner(f"{result.warnings} formatting issue(s) found", "warn")
        else:
            status_banner("SDC is lint-clean — no formatting issues.", "pass")

        if result.warnings > 0:
            section_header(f"Issues ({result.warnings})")
            for issue in result.issues:
                parts = issue.split(":", 1)
                if len(parts) == 2:
                    issue_card("LINT", parts[1].strip(), "warning")
                else:
                    issue_card("LINT", issue, "warning")

        if result.formatted_text:
            section_header("Formatted SDC Output", f"{result.line_count_formatted} lines")
            with st.expander("📄 View formatted SDC"):
                styled_code_block(result.formatted_text[:5000])

            col_d1, col_d2 = st.columns(2)
            with col_d1:
                download_button(result.formatted_text, f"linted_{filename}", "text/plain",
                                "Download Formatted SDC", key="lint_dl")
            with col_d2:
                if result.original_text != result.formatted_text:
                    import difflib
                    diff = difflib.unified_diff(
                        result.original_text.splitlines(),
                        result.formatted_text.splitlines(),
                        fromfile="original", tofile="formatted", lineterm="",
                    )
                    diff_text = "\n".join(diff)
                    with st.expander("📊 Diff View"):
                        styled_code_block(diff_text[:3000])
                        download_button(diff_text, f"lint_diff_{filename}.diff", "text/plain",
                                        "Download Diff", key="lint_diff_dl")

            # Feedback — only after Run was clicked and result exists
            feedback_widget(
                feature="linter",
                sdc_file=filename or "",
                results_summary=f"{result.warnings} warnings, {result.fixed} fixes",
                key_prefix="lint",
            )
