"""Regenerate the top-level import-compat shims for the Ṛta repository migration.

One-shot migration tool (kept for provenance in rta/infrastructure/scripts/).

For every module that moved into the product-first structure (rta/** or
legacy/**), this writes a thin root-level shim that imports the real module
from its new home and aliases it into ``sys.modules`` under the historical
top-level name. That keeps every existing import path working unchanged —
tests, benchmarks, the CLI entry points (``sdc-tools`` / ``rta``), the API
server's lazy ``ui.*`` imports, and the legacy Streamlit ``ui`` package.

When a shim is executed directly (``python cli.py``, ``python -m cli``), the
trailing ``runpy`` fallback re-executes the real module under ``__main__`` so
its entry-point guard still fires.

Shim body (example for checker):

    \"\"\"Ṛta migration shim — implementation moved to rta.engine.rules.checker.\"\"\"
    import runpy as _runpy
    import sys as _sys
    from rta.engine.rules import checker as _impl
    _sys.modules[__name__] = _impl
    if __name__ == "__main__":
        _runpy.run_path(_impl.__file__, run_name="__main__")

Usage:
    python rta/infrastructure/scripts/gen_shims.py
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]  # repository root

# (root shim filename, package path, module name)
SHIMS = [
    # Engine — preprocess
    ("sdc_preprocess", "rta.engine.preprocess", "sdc_preprocess"),
    ("tcl_resolver", "rta.engine.preprocess", "tcl_resolver"),
    # Engine — rules
    ("checker", "rta.engine.rules", "checker"),
    ("rules_registry", "rta.engine.rules", "rules_registry"),
    # Engine — analysis
    ("clock_relations", "rta.engine.analysis", "clock_relations"),
    ("coverage", "rta.engine.analysis", "coverage"),
    ("design_coverage", "rta.engine.analysis", "design_coverage"),
    ("constraint_interactions", "rta.engine.analysis", "constraint_interactions"),
    ("constraint_readiness", "rta.engine.analysis", "constraint_readiness"),
    ("wildcard_analyzer", "rta.engine.analysis", "wildcard_analyzer"),
    # Engine — context
    ("design_context", "rta.engine.context", "design_context"),
    # Engine — diff
    ("constraint_diff", "rta.engine.diff", "constraint_diff"),
    ("readiness_diff", "rta.engine.diff", "readiness_diff"),
    ("finding_identity", "rta.engine.diff", "finding_identity"),
    # Engine — policy
    ("policy_engine", "rta.engine.policy", "policy_engine"),
    ("custom_rules", "rta.engine.policy", "custom_rules"),
    # Engine — trust
    ("support_boundary", "rta.engine.trust", "support_boundary"),
    # Evidence manifest
    ("evidence", "rta.evidence.manifest", "evidence"),
    # Tools
    ("generator", "rta.tools.generate", "generator"),
    ("linter", "rta.tools.lint", "linter"),
    ("converter", "rta.tools.convert", "converter"),
    ("corner_manager", "rta.tools.corners", "corner_manager"),
    ("mmc", "rta.tools.corners", "mmc"),
    ("batch_runner", "rta.tools.batch", "batch_runner"),
    ("reporter", "rta.tools.report", "reporter"),
    # Surfaces
    ("cli", "rta.cli", "cli"),
    ("api_server", "rta.api", "api_server"),
    # ui package — production modules
    ("ui/theme", "rta.branding.tokens", "theme"),
    ("ui/feedback", "rta.workspace.server", "feedback"),
    # ui package — legacy Streamlit modules
    ("ui/components", "legacy.streamlit.ui", "components"),
    ("ui/validator", "legacy.streamlit.ui", "validator"),
    ("ui/state", "legacy.streamlit.ui", "state"),
    ("ui/workspace", "legacy.streamlit.ui", "workspace"),
    ("ui/overview", "legacy.streamlit.ui", "overview"),
    ("ui/clocks", "legacy.streamlit.ui", "clocks"),
    ("ui/context", "legacy.streamlit.ui", "context"),
    ("ui/coverage", "legacy.streamlit.ui", "coverage"),
    ("ui/diff", "legacy.streamlit.ui", "diff"),
    ("ui/interactions", "legacy.streamlit.ui", "interactions"),
    ("ui/readiness", "legacy.streamlit.ui", "readiness"),
    ("ui/reports", "legacy.streamlit.ui", "reports"),
    ("ui/ci", "legacy.streamlit.ui", "ci"),
    ("ui/tab_converter", "legacy.streamlit.ui", "tab_converter"),
    ("ui/tab_corners", "legacy.streamlit.ui", "tab_corners"),
    ("ui/tab_generator", "legacy.streamlit.ui", "tab_generator"),
    ("ui/tab_linter", "legacy.streamlit.ui", "tab_linter"),
    ("ui/tab_mmc", "legacy.streamlit.ui", "tab_mmc"),
    ("ui/tab_rules", "legacy.streamlit.ui", "tab_rules"),
    ("ui/tab_test_drive", "legacy.streamlit.ui", "tab_test_drive"),
]


def main() -> None:
    n = 0
    for fname, pkg, mod in SHIMS:
        target = ROOT / f"{fname}.py"
        target.parent.mkdir(parents=True, exist_ok=True)
        body = (
            f'"""Ṛta migration shim — implementation moved to {pkg}.{mod}."""\n'
            "import runpy as _runpy\n"
            "import sys as _sys\n"
            f"from {pkg} import {mod} as _impl\n"
            "_sys.modules[__name__] = _impl\n"
            'if __name__ == "__main__":\n'
            '    _runpy.run_path(_impl.__file__, run_name="__main__")\n'
        )
        target.write_text(body, encoding="utf-8")
        n += 1
    print(f"wrote {n} shims under {ROOT}")


if __name__ == "__main__":
    main()
