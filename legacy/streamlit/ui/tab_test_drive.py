"""
🧪 Test Drive Tab — Run all Ṛta features on any SDC file.
Pick a sample or upload your own to see every feature in action.
"""

import json
import os
import streamlit as st
from .components import (
    section_header, status_banner, metric_cards_row,
    progress_bar, styled_code_block,
    sdc_upload_area, download_button,
)
from .feedback import feedback_widget, SAMPLE_SDCS, get_sample_sdc,\
    get_sample_netlist, get_sample_baseline


def _run_analysis(text: str, filename: str, netlist_text: str = None,
                  netlist_name: str = "", top: str = ""):
    """Run all analysis features on the SDC text.

    When ``netlist_text`` is provided the design-aware tier runs: object
    references are resolved against the real design (SDC-055..059) and
    structural coverage (SDC-064..066) becomes provable. The checker results
    then carry the design context instead of NETLIST_REQUIRED.
    """
    results = {"filename": filename, "text": text,
               "netlist_name": netlist_name or ""}

    # Design context (optional netlist) — passed into the checker so the
    # design-aware rules have real objects to resolve against.
    context = None
    design_note = ""
    if netlist_text and netlist_text.strip():
        try:
            from design_context import parse_verilog
            outcome = parse_verilog(netlist_text, top=top)
            if outcome.errors:
                results["netlist_error"] = outcome.errors[0]
            elif outcome.context and outcome.context.top_module:
                context = outcome.context
                design_note = (f"Design context: {context.top_module} "
                               f"({len(context.ports)} ports, "
                               f"{len(context.instances)} instances)")
        except Exception as e:
            results["netlist_error"] = str(e)

    # Checker (design-aware when a netlist was parsed)
    from checker import check_sdc
    check_result = check_sdc(text, context=context)
    results["checker"] = {
        "errors": len(check_result.errors),
        "warnings": len(check_result.warnings),
        "info": len(check_result.info),
        "issues": check_result.issues,
        "info_items": check_result.info,
        "stats": check_result.stats,
        "scope": check_result.scope,
        "coverage": check_result.coverage,
        "design_note": design_note,
        "clean": len(check_result.errors) == 0 and len(check_result.warnings) == 0,
    }

    # Coverage
    from coverage import parse_sdc_coverage
    cov_result = parse_sdc_coverage(text, filename)
    results["coverage"] = {
        "score": round(cov_result.score, 1),
        "present": cov_result.total_present,
        "total": cov_result.total_items,
        "missing": cov_result.total_missing,
        "categories": cov_result.categories,
    }
    # Design-aware coverage summary (only meaningful with a netlist)
    if context is not None:
        cc = (check_result.coverage or {})
        results["coverage"]["design_aware"] = cc.get("summary") or {}

    # Clock Relations
    from clock_relations import analyze_clock_relations
    try:
        cr_result = analyze_clock_relations(text)
        results["clock_relations"] = {
            "clocks": len(cr_result.clocks),
            "pairs": len(cr_result.pairs),
            "mismatches": len(cr_result.mismatches),
            "clock_defs": cr_result.clocks,
            "mismatch_list": cr_result.mismatches,
        }
    except Exception as e:
        results["clock_relations"] = {"error": str(e)}

    # Linter
    from linter import lint_sdc
    lint_result = lint_sdc(text, fix=False)
    results["linter"] = {
        "warnings": lint_result.warnings,
        "issues": lint_result.issues,
        "clean": lint_result.warnings == 0,
    }

    # Convert
    from converter import parse_sdc
    parsed = parse_sdc(text, filename)
    results["converter"] = {
        "clocks_count": parsed.clocks_count,
        "constraints_count": parsed.constraints_count,
        "input_delays": len(parsed.input_delays),
        "output_delays": len(parsed.output_delays),
        "false_paths": len(parsed.false_paths),
        "clock_groups": len(parsed.clock_groups),
    }

    # Summary
    errors = results["checker"]["errors"]
    warnings = results["checker"]["warnings"]
    coverage = results["coverage"]["score"]
    results["summary"] = f"{errors} errors, {warnings} warnings, {coverage}% coverage"

    return results


def _render_analysis(results: dict):
    """Render the unified analysis dashboard."""
    filename = results["filename"]
    summary = results["summary"]

    # ── Summary row ──────────────────────────────────────────────────────────
    check = results["checker"]
    cov = results["coverage"]
    cr = results.get("clock_relations", {})
    lint_r = results["linter"]
    conv = results["converter"]

    status = "success" if check["errors"] == 0 else "error"
    if check["errors"] == 0 and check["warnings"] > 0:
        status = "warning"

    status_banner(
        f"Analysis complete for **{filename}** — "
        f"{check['errors']} errors, {check['warnings']} warnings, "
        f"{cov['score']}% coverage",
        status,
    )

    # Design-aware note (only when a netlist was parsed)
    if check.get("design_note"):
        st.success(f"🧬 {check['design_note']}")

    # ── Metrics ──────────────────────────────────────────────────────────────
    metric_cards_row([
        ("Errors", check["errors"], "🔴", "red" if check["errors"] > 0 else "green"),
        ("Warnings", check["warnings"], "🟡", "yellow" if check["warnings"] > 0 else "green"),
        ("Coverage", f"{cov['score']}%", "📊", "green" if cov['score'] >= 80 else "yellow"),
        ("Clocks", cr.get("clocks", 0), "🕐", "blue"),
        ("Constraints", conv["constraints_count"], "📏", "purple"),
        ("Lint Issues", lint_r["warnings"], "📝", "green" if lint_r["clean"] else "yellow"),
    ])

    # ── Details in expanders ─────────────────────────────────────────────────
    tab_details, tab_raw = st.tabs(["📋 Details", "📄 Raw Results"])

    with tab_details:
        # Checker section
        with st.expander(f"🛡 Checker — {check['errors']} errors, {check['warnings']} warnings", expanded=True):
            if check["issues"]:
                for i in check["issues"]:
                    msg = f"[{i.code}] {i.msg}"
                    if i.line:
                        msg = f"[{i.code}:{i.line}] {i.msg}"
                    if i.sev == "error":
                        st.error(msg)
                    elif i.sev == "warning":
                        st.warning(msg)
                    else:
                        st.info(msg)
            if check["info_items"]:
                st.caption(f"💡 {len(check['info_items'])} best-practice suggestions available")

        # Coverage section
        with st.expander(f"📊 Coverage — {cov['score']}% ({cov['present']}/{cov['total']} items)"):
            progress_bar(cov["score"])
            for cat in cov["categories"]:
                st.markdown(f"**{cat.icon} {cat.name}** — {cat.score:.0f}% ({cat.covered}/{cat.total})")

        # Clock relations section
        cr_title = f"🕐 Clock Relations — {cr.get('clocks', 0)} clocks, {cr.get('pairs', 0)} pairs"
        if cr.get("mismatches"):
            cr_title += f", {cr['mismatches']} mismatches"
        with st.expander(cr_title):
            if cr.get("error"):
                st.info(f"Analysis note: {cr['error']}")
            else:
                st.caption(f"{cr.get('clocks', 0)} clock(s) found · {cr.get('pairs', 0)} pair(s) analyzed")

        # Linter section
        lint_status = f"⚠️ {lint_r['warnings']} issues" if lint_r['warnings'] else "✅ Clean"
        with st.expander(f"📝 Linter — {lint_status}"):
            if lint_r["issues"]:
                for issue in lint_r["issues"]:
                    st.warning(issue)
            else:
                st.success("SDC is lint-clean — no formatting issues detected.")

        # Converter section
        with st.expander(f"🔄 Converter — {conv['clocks_count']} clocks, {conv['constraints_count']} total constraints"):
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("🕐 Clocks", conv["clocks_count"])
            c2.metric("🔌 Input Delays", conv["input_delays"])
            c3.metric("🔌 Output Delays", conv["output_delays"])
            c4.metric("⚠️ False Paths", conv["false_paths"])

    with tab_raw:
        styled_code_block(json.dumps({
            "filename": filename,
            "checker": {"errors": check["errors"], "warnings": check["warnings"]},
            "coverage": {"score": cov["score"], "present": cov["present"], "total": cov["total"]},
            "clock_relations": {"clocks": cr.get("clocks", 0), "pairs": cr.get("pairs", 0)},
            "linter": {"warnings": lint_r["warnings"]},
            "converter": conv,
        }, indent=2))

        # Download button
        full_json = json.dumps({
            "tool": "Ṛta",
            "version": "1.3.0",
            "file": filename,
            "results": {
                "checker": {"errors": check["errors"], "warnings": check["warnings"]},
                "coverage": {"score": cov["score"]},
                "clock_relations": {"clocks": cr.get("clocks", 0)},
                "linter": {"warnings": lint_r["warnings"]},
            },
        }, indent=2)
        download_button(full_json, f"sdc_analysis_{filename}.json", "application/json",
                        "Download Results (JSON)", key="td_dl")

    # ── Feedback ─────────────────────────────────────────────────────────────
    feedback_widget(feature="test_drive", sdc_file=filename, results_summary=summary)


def render():
    """Render the Test Drive tab."""
    section_header(
        "🧪 Ṛta Test Drive",
        "Try every feature on any SDC file. Pick a sample below or upload your own."
    )

    # ── Input selection ──────────────────────────────────────────────────────
    input_mode = st.radio(
        "Select input:",
        ["📂 Use a sample SDC", "📁 Upload my own"],
        horizontal=True,
        key="td_mode",
    )

    text = None
    filename = ""

    if input_mode == "📂 Use a sample SDC":
        sample_names = list(SAMPLE_SDCS.keys())
        selected = st.selectbox("Choose a sample SDC to analyze:", sample_names, key="td_sample")

        # Show expected results for transparency
        expected_map = {
            "✅ Real Design (RISC-V Core)": ("0 errors expected — this is a well-formed design", "pass"),
            "🐛 Buggy — Missing Clocks": ("SDC-005, SDC-006 errors EXPECTED — intentionally missing constraints", "warn"),
            "⚠️ Warnings — Clock Groups": ("SDC-024, SDC-028 warnings EXPECTED — designed to test warning detection", "warn"),
            "📝 Malformed SDC": ("SDC-002, SDC-003, SDC-011 errors EXPECTED — intentionally malformed", "warn"),
            "📭 Empty SDC": ("SDC-001 error EXPECTED — empty file has no clock", "warn"),
            "🔬 Edge Values": ("SDC-005 error EXPECTED — extreme values test boundary handling", "warn"),
            "🔬 DMA Engine Block (realistic, 2 clocks)": ("SDC-059 + SDC-065 on stream_out EXPECTED — a real regression vs the V1 baseline; SDC-020 x2 confirm-false-path", "warn"),
        }

        with st.expander("📄 About this sample — what to expect", expanded=True):
            descriptions = {
                "✅ Real Design (RISC-V Core)": "A complete, realistic SDC for a 28nm RISC-V processor with clocks, I/O, exceptions, derate, and power constraints. This is a clean design — 0 errors expected.",
                "🐛 Buggy — Missing Clocks": "SDC with intentional errors: no clock defined, input delays without -min, bad case analysis values. ✅ The SDC-005, SDC-006 errors you'll see are the TOOL CORRECTLY DETECTING these issues.",
                "⚠️ Warnings — Clock Groups": "SDC designed to trigger warnings: multiple clocks without clock groups, tight uncertainty, missing propagated clock. ✅ These warnings are the tool working correctly.",
                "📝 Malformed SDC": "Edge case with duplicate clock names, generated clocks missing source, contradictory divide/multiply, invalid values. ✅ All errors detected are correct behavior.",
                "📭 Empty SDC": "Empty file — tests that the checker flags completely unconstrained designs. ✅ SDC-001 is expected.",
                "🔬 Edge Values": "Extreme values: 0.05ns clock period, 100ns uncertainty, 9999 fanout limit. ✅ Tests that the tool handles edge cases without crashing.",
                "🔬 DMA Engine Block (realistic, 2 clocks)": "A believable two-clock DMA engine (AHB slave + stream engine, clk_ahb + clk_periph + clk_div2 generated). The V2 revision dropped the stream_out output delay and left the new peripheral-domain exception undocumented. **With its companion netlist auto-loaded, Ṛta proves stream_out is unconstrained (SDC-059 + SDC-065), flags the missing clock group (SDC-062), and the CI gate blocks this regression (exit 1) vs the V1 baseline. This is the realistic workflow sample — run it, then use Diff / Gate / Report below.**",
            }
            desc = descriptions.get(selected, "")
            if desc:
                st.info(desc)

        text, filename = get_sample_sdc(selected)

        # Auto-load the companion netlist + baseline for samples that ship them
        # (the realistic block demonstrates the design-aware tier).
        netlist_text, netlist_name = get_sample_netlist(selected)
        baseline_path = get_sample_baseline(selected)

        if text:
            st.success(f"✅ Loaded **{filename}** ({len(text.splitlines())} lines)")
            if netlist_text:
                st.success(f"🧬 Design-aware: companion netlist **{netlist_name}** auto-loaded.")

    else:
        uploaded = st.file_uploader("Upload an SDC file", type=["sdc", "tcl", "txt"],
                                    key="td_upload")
        netlist_text = None
        netlist_name = ""
        baseline_path = ""
        if uploaded:
            text = uploaded.read().decode("utf-8", errors="replace")
            filename = uploaded.name
            st.success(f"✅ Loaded **{filename}** ({len(text.splitlines())} lines)")
            uploaded_nl = st.file_uploader("🧬 Optional netlist (.v) for design-aware analysis",
                                           type=["v", "vh"], key="td_netlist_upload")
            if uploaded_nl:
                netlist_text = uploaded_nl.read().decode("utf-8", errors="replace")
                netlist_name = uploaded_nl.name
                st.success(f"🧬 Netlist **{netlist_name}** loaded for design-aware analysis.")

    # ── Analysis ─────────────────────────────────────────────────────────────
    if text and st.button("🚀 Run Complete Analysis", type="primary", use_container_width=True,
                          key="td_run"):
        with st.spinner(f"Running all {len(text.splitlines())} lines through every feature..."):
            results = _run_analysis(text, filename, netlist_text=netlist_text,
                                    netlist_name=netlist_name)

        st.divider()
        _render_analysis(results)

        # ── Workflow step for the realistic sample: Diff → Gate → Report ────────
        if baseline_path:
            st.subheader("🔄 The workflow: Diff → CI Gate → Report")
            st.caption(
                "This sample ships with the V1 readiness baseline. See what changed "
                "(Diff), whether the change is allowed to merge (CI Gate), and "
                "produce the review artifact (Report)."
            )
            w1, w2 = st.columns(2)
            with w1:
                if st.button("🔁 Diff V1 → V2", use_container_width=True, key="td_diff"):
                    try:
                        from constraint_diff import analyze_constraint_changes
                        v1_text, _ = get_sample_sdc(
                            "🔬 DMA Engine Block (realistic, 2 clocks)")
                        v1_text = open(
                            os.path.join(os.path.dirname(os.path.dirname(
                                os.path.dirname(os.path.dirname(__file__)))),
                                "engineer_test_kit/18_test_drive/dma_engine_v1.sdc"),
                            encoding="utf-8").read()
                        d = analyze_constraint_changes(v1_text, text)
                        st.markdown(f"**{d.stats.get('total_changes', 0)} changes** "
                                    f"({d.stats.get('removed', 0)} removed, "
                                    f"{d.stats.get('modified', 0)} modified)")
                        for c in (d.changes or [])[:8]:
                            st.markdown(f"- `{c.rule}` — {c.v1_text or '(new)'} "
                                        f"→ {c.v2_text or '(removed)'}")
                    except Exception as e:
                        st.error(f"Diff failed: {e}")
            with w2:
                if st.button("🛡 Run CI Gate (STRICT)", use_container_width=True, key="td_gate"):
                    try:
                        import subprocess, sys
                        env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
                        from pathlib import Path
                        root = Path(__file__).resolve().parent.parent.parent.parent
                        p = subprocess.run(
                            [sys.executable, str(root / "cli.py"),
                             "check", "engineer_test_kit/18_test_drive/dma_engine.sdc",
                             "--netlist", "engineer_test_kit/18_test_drive/dma_engine_top.v",
                             "--top", "dma_engine_top",
                             "--baseline", baseline_path,
                             "--gate", "STRICT"],
                            capture_output=True, timeout=60, env=env,
                            cwd=str(root))
                        code = p.returncode
                        if code == 0:
                            st.success("✅ Gate PASS (exit 0) — merge allowed. "
                                       "CI PASS ≠ timing pass.")
                        else:
                            st.error(f"❌ Gate FAIL (exit {code}) — merge blocked. "
                                     f"The regression vs baseline is rejected.")
                        st.code((p.stdout or b"").decode("utf-8", errors="replace")[-800:],
                                language="text")
                    except Exception as e:
                        st.error(f"Gate failed: {e}")
            st.caption(
                "Equivalent CLI: `rta check engineer_test_kit/18_test_drive/dma_engine.sdc "
                "--netlist engineer_test_kit/18_test_drive/dma_engine_top.v --top dma_engine_top "
                "--baseline engineer_test_kit/18_test_drive/baseline.json --gate STRICT` — "
                "same command your CI pipeline runs."
            )

    elif not text:
        status_banner("Select a sample SDC or upload your own file to begin.", "info")
