"""
🔄 Converter Tab — EDA-style SDC to JSON/YAML conversion.
"""

import streamlit as st
from ui.components import (
    sdc_upload_area, download_button, section_header,
    metric_cards_row, status_banner, styled_code_block,
)
from ui.feedback import feedback_widget
from converter import sdc_to_json, sdc_to_yaml


def render():
    section_header("🔄 SDC Converter", "Parse SDC files and export structured JSON or YAML for tool integration.")

    sdc_text, filename = sdc_upload_area("conv")

    if not sdc_text:
        status_banner("Upload an SDC file or paste SDC text above to convert.", "info")
        return

    fmt = st.radio("Output format", ["json", "yaml"], horizontal=True, key="conv_fmt")

    if st.button("🔄 Convert", type="primary", use_container_width=True, key="conv_btn"):
        with st.spinner("Parsing SDC..."):
            if fmt == "yaml":
                output = sdc_to_yaml(sdc_text, filename)
                ext, mime = ".yaml", "text/yaml"
            else:
                output = sdc_to_json(sdc_text, filename)
                ext, mime = ".json", "application/json"

        st.divider()

        import json
        data = json.loads(sdc_to_json(sdc_text, filename))
        metric_cards_row([
            ("Clocks", data.get("clocks_count", 0), "🕐", "blue"),
            ("Input Delays", len(data.get("input_delays", [])), "🔌", "green"),
            ("Output Delays", len(data.get("output_delays", [])), "🔌", "yellow"),
            ("Exceptions", len(data.get("false_paths", [])) + len(data.get("multicycle_paths", [])), "⚠️", "purple"),
        ])

        status_banner(f"Successfully parsed {data.get('constraints_count', 0)} constraints", "pass")

        section_header(f"Structured Output ({fmt.upper()})", f"{len(output)} characters")
        with st.expander(f"📄 View {fmt.upper()} output", expanded=True):
            styled_code_block(output[:10000])

        out_filename = filename.rsplit(".", 1)[0] + ext
        download_button(output, out_filename, mime, f"Download {fmt.upper()}", key="conv_dl")

        # Feedback — only after Run was clicked
        feedback_widget(feature="converter", sdc_file=filename or "",
                      results_summary=f"parsed {data.get('constraints_count', 0)} constraints",
                      key_prefix="conv")
