"""
Ṛta — Command-line interface
Wrap checker, generator, diff, corners, clock relations, and rules into
a Unix-style CLI for terminal use, CI/CD, and script automation.

Usage:
    rta check sample.sdc
    rta check sample.sdc --json
    rta check sample.sdc --junit --output report.xml
    rta generate --design MY_CHIP --clock clk=5.0:sys_clk > output.sdc
    rta diff old.sdc new.sdc
    rta corners list
    rta corners show "Classic 3-corner (Worst/Typ/Best)"
    rta analyze clock-relations input.sdc
    rta rules list
    rta rules show SDC-060
"""

import argparse
import json
import sys
import os
import textwrap

from rules_registry import APP_VERSION, get_all_rules, get_rule, get_rules_by_module


# ── Output helpers ───────────────────────────────────────────────────────────

class OutputWriter:
    """Collect output lines and optionally write to file."""

    def __init__(self, output_file: str = ""):
        self.lines: list[str] = []
        self.output_file = output_file
        self._json_written = False

    def write(self, text: str = "") -> None:
        self.lines.append(text)

    def writeln(self, text: str = "") -> None:
        self.lines.append(text)

    def flush(self) -> None:
        # When json_out() already wrote the file directly (--json --output), a
        # trailing flush() must NOT clobber it with the (empty) text lines.
        if self._json_written:
            return
        text = "\n".join(self.lines)
        if self.output_file:
            _write_output_file(self.output_file, text)
        else:
            sys.stdout.reconfigure(encoding="utf-8") if hasattr(sys.stdout, "reconfigure") else None
            print(text)

    def json_out(self, obj) -> None:
        text = json.dumps(obj, indent=2, default=str)
        if self.output_file:
            _write_output_file(self.output_file, text)
        else:
            print(text)
        # Guard BOTH modes: a later flush() must never emit an empty artifact
        # (file mode) or a trailing empty line (stdout mode) after JSON output.
        self._json_written = True


def _write_output_file(path: str, text: str) -> None:
    """Write output to ``path``, failing cleanly (exit 2) instead of a traceback.

    Bad output paths (missing directory, permission denied) are invalid
    invocations per the CLI exit-code contract, so they must produce a clear
    diagnostic and exit 2 — never an uncaught exception.
    """
    try:
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
    except OSError as e:
        fatal(f"cannot write output file '{path}': {e}", code=2)


def fatal(msg: str, code: int = 1):
    print(f"Error: {msg}", file=sys.stderr)
    sys.exit(code)    # CI gate exit codes (Phase 12) — used only when --gate is requested.
EXIT_GATE_FAILED = 1


def _load_policy_file(path: str) -> dict:
    """Load + validate a declarative CUSTOM policy file. Fails safely (exit 2)."""
    from policy_engine import load_policy
    try:
        with open(path, "r", encoding="utf-8") as f:
            raw = f.read()
    except Exception as e:
        fatal(f"cannot read policy '{path}': {e}", code=2)
    pol, errs = load_policy(raw)
    if pol is None:
        fatal(f"policy '{path}' is invalid: {'; '.join(errs)}", code=2)
    return pol


def _fmt_cov_bucket(b: dict) -> str:
    """Format a coverage bucket dict like '7 constrained, 1 unconstrained'."""
    parts = []
    if b.get("constrained"):
        parts.append(f"{b['constrained']} constrained")
    if b.get("unconstrained"):
        parts.append(f"{b['unconstrained']} unconstrained")
    if b.get("partial"):
        parts.append(f"{b['partial']} partial")
    if b.get("exempt"):
        parts.append(f"{b['exempt']} exempt")
    if b.get("unknown"):
        parts.append(f"{b['unknown']} unknown")
    if b.get("not_applicable"):
        parts.append(f"{b['not_applicable']} n/a")
    if not parts:
        parts.append("0 total")
    return f"{b.get('total', 0)} ports — " + ", ".join(parts)


# ── Subcommand: check ────────────────────────────────────────────────────────

def _read_baseline(path: str) -> dict:
    """Load + validate a readiness baseline snapshot. Fails safely (exit 2)."""
    from readiness_diff import load_snapshot
    try:
        with open(path, "r", encoding="utf-8") as f:
            raw = f.read()
    except Exception as e:
        fatal(f"cannot read baseline '{path}': {e}", code=2)
    snap, errs = load_snapshot(raw)
    if snap is None:
        fatal(f"baseline '{path}' is invalid: {'; '.join(errs)}", code=2)
    return snap


def _render_readiness_diff(diff: dict) -> list[str]:
    """Human-readable READINESS DIFF section (kept concise)."""
    lines: list[str] = []
    compat = diff.get("compatibility", {}).get("status", "?")
    rdy = diff.get("readiness", {})
    lines.append(f"  Readiness diff: {rdy.get('baseline', '?')} → {rdy.get('current', '?')} "
                 f"({rdy.get('overall_delta', '?')}, classification: {diff.get('classification', '?')})")
    lines.append(f"    compatibility: {compat}")
    if diff.get("compatibility", {}).get("reasons"):
        for r_ in diff["compatibility"]["reasons"][:4]:
            lines.append(f"      reason: {r_}")
    nb = diff.get("findings", {}).get("new_blockers", [])
    rb = diff.get("findings", {}).get("resolved_blockers", [])
    nr = diff.get("findings", {}).get("new_review", [])
    rr = diff.get("findings", {}).get("resolved_review", [])
    lines.append(f"    new blockers: {len(nb)}  resolved blockers: {len(rb)}  "
                 f"new review: {len(nr)}  resolved review: {len(rr)}")
    debt = diff.get("debt", {}) or {}
    ex = debt.get("existing") or {}
    nd = debt.get("new_debt") or {}
    rd = debt.get("resolved_debt") or {}
    if ex or nd or rd:
        lines.append("    debt: existing="
                     f"{ex.get('blockers', 0)}B/{ex.get('review', 0)}R/{ex.get('advisories', 0)}A "
                     f"new={nd.get('blockers', 0)}B/{nd.get('review', 0)}R/{nd.get('advisories', 0)}A "
                     f"resolved={rd.get('blockers', 0)}B/{rd.get('review', 0)}R/{rd.get('advisories', 0)}A")
    for b in nb[:6]:
        ln = f" :{b['line']}" if b.get("line") else ""
        lines.append(f"    NEW BLOCKER [{b['code']}]{ln} {b['msg'][:90]}")
    for b in rb[:6]:
        ln = f" :{b['line']}" if b.get("line") else ""
        lines.append(f"    RESOLVED BLOCKER [{b['code']}]{ln} {b['msg'][:90]}")
    for c in diff.get("findings", {}).get("changed", [])[:6]:
        lines.append(f"    CHANGED [{c['code']}] {c['before']['msg'][:60]} → {c['after']['msg'][:60]}")
    cov = diff.get("coverage", {}) or {}
    for side in ("inputs", "outputs"):
        b = (cov.get(side) or {}).get("newly_unconstrained", [])
        if b:
            lines.append(f"    coverage: {len(b)} {side} newly unconstrained: {', '.join(b[:8])}")
    trust_regs = diff.get("trust", {}).get("regressions", [])
    if trust_regs:
        trust_str = "; ".join(
            "{} {}→{}".format(t.get("command", ""), t.get("from", ""), t.get("to", ""))
            for t in trust_regs[:5])
        lines.append(f"    trust regressions: {trust_str}")
    int_new = diff.get("interactions", {}).get("new", [])
    if int_new:
        lines.append(f"    interaction regressions: {len(int_new)}")
    gate = diff.get("gate")
    if gate:
        lines.append(f"    gate [{gate.get('policy')}]{' (' + gate.get('policy_name', '') + ')' if gate.get('policy_name') else ''}: "
                     f"{gate.get('result')} (exit {gate.get('exit_code')})")
        for g_ in gate.get("reasons", [])[:4]:
            lines.append(f"      {g_}")
    return lines


def cmd_check(args):
    """Validate an SDC file and report errors / warnings / info."""
    from checker import check_sdc

    try:
        text = args.file.read()
    except Exception as e:
        fatal(f"cannot read {args.file.name}: {e}")
    finally:
        args.file.close()

    # Optional design context (Phase 8): --netlist FILE [--top NAME]
    context = None
    design_note = ""
    if getattr(args, "netlist", None):
        try:
            v_text = args.netlist.read()
        except Exception as e:
            fatal(f"cannot read netlist {args.netlist.name}: {e}")
        finally:
            args.netlist.close()
        from design_context import parse_verilog
        outcome = parse_verilog(v_text, top=getattr(args, "top", "") or "")
        if outcome.errors:
            fatal(f"netlist: {outcome.errors[0]}")
        context = outcome.context
        design_note = (f"Design context: {context.top_module} "
                       f"({context.object_counts()['ports']} ports, "
                       f"{context.object_counts()['instances']} instances)")

    result = check_sdc(text, context=context)

    # ── Readiness baseline / diff / CI gate (Phase 12) ──────────────────────
    # --save-baseline writes a snapshot; --baseline compares against a
    # previously saved snapshot; --gate evaluates an opt-in CI policy and
    # overrides the exit code per the documented contract:
    #   0 = pass, 1 = gate failed, 2 = invalid invocation/input, 3 = engine fail.
    # Without --gate, existing exit behavior (1 if errors else 0) is preserved.
    baseline_snap = None
    readiness_diff = None
    gate_result = None
    if getattr(args, "save_baseline", ""):
        from readiness_diff import build_snapshot, snapshot_to_json
        snap = build_snapshot(result, context=context, source_name=args.file.name)
        try:
            with open(args.save_baseline, "w", encoding="utf-8") as f:
                f.write(snapshot_to_json(snap))
        except Exception as e:
            fatal(f"cannot write baseline '{args.save_baseline}': {e}", code=2)
    if getattr(args, "baseline", ""):
        from readiness_diff import build_snapshot, diff_snapshots
        baseline_snap = _read_baseline(args.baseline)
        cur_snap = build_snapshot(result, context=context, source_name=args.file.name)
        readiness_diff = diff_snapshots(baseline_snap, cur_snap)
    # --gate is ALWAYS evaluated when requested — even without --baseline, so a
    # baseline-dependent policy (NO_READINESS_REGRESSION / STRICT) correctly
    # fails with exit 2 (invalid invocation) instead of silently passing.
    if getattr(args, "gate", ""):
        from readiness_diff import build_snapshot, evaluate_gate
        policy_data = None
        if args.gate == "CUSTOM":
            if not getattr(args, "gate_policy", ""):
                fatal("--gate CUSTOM requires --gate-policy FILE", code=2)
            policy_data = _load_policy_file(args.gate_policy)
        if readiness_diff is None:
            cur_snap = build_snapshot(result, context=context, source_name=args.file.name)
            readiness_diff = {}
        gate_result = evaluate_gate(args.gate, baseline_snap, cur_snap, readiness_diff,
                                    policy_data=policy_data)
        readiness_diff["gate"] = gate_result

    # Custom rules
    custom_results: list = []
    custom_rulesets: list = []
    if args.custom_rules:
        from custom_rules import load_ruleset, apply_rules
        for rules_path in args.custom_rules:
            try:
                rs = load_ruleset(rules_path)
                custom_rulesets.append(rs)
                custom_results.extend(apply_rules(text, rs))
            except Exception as e:
                print(f"Warning: cannot load custom rules '{rules_path}': {e}", file=sys.stderr)

    out = OutputWriter(args.output)

    if args.format == "csv":
        out.writeln("code,severity,line,message")
        for i in result.issues:
            msg = i.msg.replace('"', '""')
            out.writeln(f'{i.code},{i.sev},{i.line or ""},"{msg}"')
        if args.verbose:
            for i in result.info:
                msg = i.msg.replace('"', '""')
                out.writeln(f'{i.code},info,{i.line or ""},"{msg}"')

    elif args.format == "markdown":
        out.writeln("# SDC Check Results")
        out.writeln(f"\n**File:** `{args.file.name}`")
        out.writeln(f"\n| Code | Severity | Line | Message |")
        out.writeln(f"|------|----------|------|---------|")
        for i in result.issues:
            ln = str(i.line) if i.line else ""
            msg = i.msg[:80]
            out.writeln(f"| {i.code} | {i.sev} | {ln} | {msg} |")
        if args.verbose:
            for i in result.info:
                ln = str(i.line) if i.line else ""
                out.writeln(f"| {i.code} | info | {ln} | {i.msg[:80]} |")

    elif args.json:
        data = {
            "version": APP_VERSION,
            "file": args.file.name,
            "errors": [{"code": i.code, "msg": i.msg} for i in result.errors],
            "warnings": [{"code": i.code, "msg": i.msg} for i in result.warnings],
            "info": [{"code": i.code, "msg": i.msg} for i in result.info],
            "stats": result.stats,
            "summary": {
                "errors": len(result.errors),
                "warnings": len(result.warnings),
                "info": len(result.info),
                "clocks": result.stats.get("Clocks", 0),
            },
            "analysis_scope": result.scope,
            "constraint_coverage": result.coverage,
            "constraint_interactions": getattr(result, "interactions", {}) or {},
            "constraint_readiness": getattr(result, "readiness", {}) or {},
        }
        if readiness_diff:
            data["readiness_diff"] = readiness_diff
        if custom_results:
            data["custom_rules"] = [
                {"id": r.rule.id, "name": r.rule.name, "severity": r.rule.severity,
                 "passed": r.passed, "message": r.msg}
                for r in custom_results
            ]
            data["summary"]["custom_rules_total"] = len(custom_results)
            data["summary"]["custom_rules_failed"] = sum(1 for r in custom_results if not r.passed)
        out.json_out(data)

    elif args.junit:
        _write_junit(out, result, args.file.name)

    else:
        # Text table output
        sep = "-" * 60
        out.writeln(f"Ṛta v{APP_VERSION} — Checker Results")
        out.writeln(f"File: {args.file.name}")
        out.writeln()
        if design_note:
            out.writeln(f"  {design_note}")
            out.writeln(sep)

        # Summary row
        err_c = len(result.errors)
        warn_c = len(result.warnings)
        info_c = len(result.info)
        clk_c = result.stats.get("Clocks", 0) or result.stats.get("clocks", 0)
        out.writeln(f"  {'Errors:':<16} {err_c}")
        out.writeln(f"  {'Warnings:':<16} {warn_c}")
        out.writeln(f"  {'Info:':<16} {info_c}")
        out.writeln(f"  {'Clocks:':<16} {clk_c}")
        out.writeln(sep)

        # ── Analysis scope / trust disclosure (Phase 7) ────────────────────
        # A "no errors" result must never read as "everything proven correct".
        _scope = getattr(result, "scope", {}) or {}
        if _scope:
            _qual = {"NETLIST_REQUIRED": " (object refs need design context)",
                     "PARTIALLY_VALIDATED": " (some options not value-analyzed)",
                     "UNSUPPORTED": " (unsupported constructs present)",
                     "TCL_EXECUTION_REQUIRED": " (Tcl execution constructs present)"}.get(
                _scope.get("status"), "")
            out.writeln(f"  Analysis scope: {_scope.get('status', 'NOT_VALIDATED')}{_qual}")
            out.writeln(f"    commands={_scope.get('commands_found', 0)} "
                        f"full={_scope.get('fully_analyzed', 0)} "
                        f"partial={_scope.get('partially_analyzed', 0)} "
                        f"netlist={_scope.get('netlist_required', 0)} "
                        f"unsupported={_scope.get('unsupported', 0) + _scope.get('tcl_execution_required', 0)}")
            if _scope.get("ignored_options"):
                out.writeln(f"    ignored options: {', '.join(sorted(set(_scope['ignored_options']))[:8])}")
            if _scope.get("unknown_options"):
                out.writeln(f"    unknown options: {', '.join(sorted(set(_scope['unknown_options']))[:8])}")
            out.writeln(sep)

        # ── Design constraint coverage (Phase 9) ───────────────────────────
        # Coverage answers "was something constrained?", NOT "was it
        # constrained correctly?" — shown only in design-aware mode.
        _cov = getattr(result, "coverage", None) or {}
        if _cov.get("summary"):
            s = _cov["summary"]
            out.writeln("  Constraint coverage (design-aware):")
            out.writeln(f"    inputs:  {_fmt_cov_bucket(s['inputs'])}")
            out.writeln(f"    outputs: {_fmt_cov_bucket(s['outputs'])}")
            out.writeln(f"    clocks:  {s['clocks']['defined']} defined, "
                        f"{s['clocks']['structurally_resolved']} structurally resolved, "
                        f"{s['clocks']['no_structural_fanout']} with no structural fanout")
            exc = s["exceptions"]
            out.writeln(f"    exceptions: {exc['total']} total "
                        f"(resolved={exc['objects_resolved']}, "
                        f"empty={exc['empty_collection']}, "
                        f"partial={exc['partially_resolved']})")
            out.writeln("    coverage is NOT correctness — a fully covered design can still have timing errors.")
            out.writeln(sep)

        # ── Constraint interactions (Phase 10) ─────────────────────────────
        # Semantic interactions: exact duplicates, silent overrides, provable
        # conflicts (SDC-069) and exception overlaps needing STA (SDC-070).
        _int = getattr(result, "interactions", None) or {}
        if _int.get("summary"):
            s = _int["summary"]
            out.writeln("  Constraint interactions:")
            out.writeln(f"    analyzed={s.get('constraints_analyzed', 0)} "
                        f"duplicates={s.get('exact_duplicates', 0)} "
                        f"overrides={s.get('overrides', 0)} "
                        f"conflicts={s.get('definite_conflicts', 0)} "
                        f"need-sta={s.get('possible_conflicts', 0)} "
                        f"legal-multiples={s.get('legal_multiples', 0)}")
            for f in _int.get("findings", []):
                ln = f" :{f['line']}" if f.get("line") else ""
                ln2 = f" ↔:{f['line2']}" if f.get("line2") else ""
                out.writeln(f"  [{f['code']}]{ln}{ln2} {f['msg']}")
            out.writeln(sep)

        # ── Readiness diff vs baseline (Phase 12) ──────────────────────────
        # Semantic comparison against a saved readiness snapshot: what became
        # better/worse/unchanged, and the optional CI gate verdict.
        if readiness_diff:
            out.writeln("  READINESS DIFF (vs baseline):")
            for _l in _render_readiness_diff(readiness_diff):
                out.writeln(_l)
            out.writeln("    CI PASS ≠ timing pass — the gate only checks for disallowed "
                        "constraint-readiness regressions under the selected policy.")
            out.writeln(sep)

        # ── Constraint readiness (Phase 11) ────────────────────────────────
        # Handoff-oriented verdict aggregated from checker + scope + coverage +
        # interactions. READY never means "timing passes".
        _rdy = getattr(result, "readiness", None) or {}
        if _rdy.get("overall"):
            out.writeln(f"  Constraint readiness: {_rdy['overall']} "
                        f"(mode={_rdy.get('mode', 'SDC_ONLY')})")
            for dim, ev in sorted(_rdy.get("dimensions", {}).items()):
                out.writeln(f"    {dim.replace('_', ' '):<18} {ev.get('status', '—')}")
                if ev.get("summary"):
                    out.writeln(f"      {ev['summary']}")
            for b in _rdy.get("blockers", []):
                ln = f" :{b['line']}" if b.get("line") else ""
                ln2 = f" ↔:{b['line2']}" if b.get("line2") else ""
                out.writeln(f"    BLOCKER [{b['code']}]{ln}{ln2} {b['msg'][:90]}")
            for r in _rdy.get("review_items", [])[:6]:
                ln = f" :{r['line']}" if r.get("line") else ""
                ln2 = f" ↔:{r['line2']}" if r.get("line2") else ""
                out.writeln(f"    REVIEW  [{r['code']}]{ln}{ln2} {r['msg'][:90]}")
            if _rdy.get("actions"):
                acts = ", ".join(f"{a['priority']} {a['category']}"
                                 for a in _rdy["actions"][:5])
                out.writeln(f"    actions: {acts}")
            if _rdy.get("limited_design_verification"):
                out.writeln("    limited design verification (SDC-only mode) — upload a netlist to verify object references")
            out.writeln("    NOTE: constraint-readiness review, NOT an STA timing signoff — READY does not mean setup/hold passes.")
            out.writeln(sep)

        # Errors
        if result.errors:
            if args.verbose:
                out.writeln(f"\n  ERRORS  ({len(result.errors)}):")
            for i in result.errors:
                ln = f" :{i.line}" if i.line else ""
                out.writeln(f"  [{i.code}]{ln} {i.msg}")

        # Warnings
        if result.warnings:
            if args.verbose:
                out.writeln(f"\n  WARNINGS  ({len(result.warnings)}):")
            for i in result.warnings:
                ln = f" :{i.line}" if i.line else ""
                out.writeln(f"  [{i.code}]{ln} {i.msg}")

        # Info
        if result.info and args.verbose:
            out.writeln(f"\n  INFO  ({len(result.info)}):")
            for i in result.info:
                out.writeln(f"  [{i.code}] {i.msg}")

        # Stats
        if result.stats and args.verbose:
            out.writeln(f"\n  Stats:")
            for k, v in sorted(result.stats.items()):
                out.writeln(f"    {k}: {v}")

        # Custom rules (text output)
        if custom_results:
            out.writeln(f"\n  Custom Rules ({len(custom_results)} rules):")
            for r in custom_results:
                status = "PASS" if r.passed else "FAIL"
                out.writeln(f"    [{status}] {r.rule.id} — {r.msg}")
            fail_count = sum(1 for r in custom_results if not r.passed)
            out.writeln(f"  Custom rules: {fail_count} failed / {len(custom_results)} total")

    out.flush()

    # CI gate exit-code contract (only when --gate requested).
    if gate_result is not None:
        sys.exit(gate_result.get("exit_code", EXIT_GATE_FAILED))
    sys.exit(1 if result.errors else 0)


def _write_junit(out: OutputWriter, result, filename: str):
    """Write JUnit XML for CI integration."""
    import xml.sax.saxutils as saxutils

    total = len(result.errors) + len(result.warnings) + len(result.info)
    out.writeln('<?xml version="1.0" encoding="UTF-8"?>')
    out.writeln(f'<testsuite name="sdc-tools" tests="{total}" errors="{len(result.errors)}" failures="{len(result.warnings)}">')
    out.writeln(f'  <properties><property name="file" value="{saxutils.escape(filename)}"/></properties>')

    for i in result.errors:
        out.writeln(f'  <testcase classname="checker" name="{saxutils.escape(i.code)}">')
        out.writeln(f'    <error message="{saxutils.escape(i.msg)}"/>')
        out.writeln('  </testcase>')

    for i in result.warnings:
        out.writeln(f'  <testcase classname="checker" name="{saxutils.escape(i.code)}">')
        out.writeln(f'    <failure message="{saxutils.escape(i.msg)}"/>')
        out.writeln('  </testcase>')

    for i in result.info:
        out.writeln(f'  <testcase classname="checker" name="{saxutils.escape(i.code)}"/>')

    out.writeln('</testsuite>')


# ── Subcommand: generate ─────────────────────────────────────────────────────

def cmd_generate(args):
    """Generate a complete SDC file from CLI parameters."""
    from generator import SDCParams, ClockDef, generate_sdc

    clocks: list[ClockDef] = []
    for clk_str in args.clock or []:
        parts = clk_str.split("=", 1)
        name = parts[0]
        rest = parts[1] if len(parts) > 1 else "5.0"
        period = 5.0
        port = ""
        if ":" in rest:
            period_str, port = rest.split(":", 1)
            period = float(period_str)
        else:
            period = float(rest)

        clocks.append(ClockDef(
            name=name,
            clk_type="primary",
            port=port or name,
            period=period,
            uncertainty=args.uncertainty,
        ))

    p = SDCParams(
        design_name=args.design,
        sdc_version=args.sdc_version,
        clocks=clocks,
        add_units=True,
        add_oper_cond=args.operating_condition is not None,
        oper_cond_name=args.operating_condition or "",
        add_derate=args.derate,
        derate_cell_early=1.08,
        derate_cell_late=0.92,
        add_ideal_rst=args.ideal_reset,
        rst_port=args.reset_port,
        add_propagated=args.propagated,
        add_scan=args.scan,
        scan_port=args.scan_port,
    )

    sdc_text = generate_sdc(p)

    if args.output:
        _write_output_file(args.output, sdc_text)
        print(f"Written to {args.output}")
    else:
        sys.stdout.reconfigure(encoding="utf-8") if hasattr(sys.stdout, "reconfigure") else None
        print(sdc_text)


# ── Subcommand: diff ─────────────────────────────────────────────────────────

def cmd_diff(args):
    """Compare two SDC files semantically."""
    from constraint_diff import analyze_constraint_changes

    try:
        v1_text = args.v1.read()
        v2_text = args.v2.read()
    except Exception as e:
        fatal(f"cannot read: {e}")
    finally:
        args.v1.close()
        args.v2.close()

    linked_v1 = _load_linked_files(args.linked_v1) if args.linked_v1 else None
    linked_v2 = _load_linked_files(args.linked_v2) if args.linked_v2 else None

    result = analyze_constraint_changes(v1_text, v2_text, linked_v1, linked_v2)
    out = OutputWriter(args.output)

    if args.json:
        data = {
            "version": APP_VERSION,
            "files": {"v1": args.v1.name, "v2": args.v2.name},
            "stats": result.stats,
            "changes": [
                {
                    "rule": c.rule.rule_id,
                    "severity": c.rule.severity,
                    "type": c.constraint_type,
                    "category": c.category,
                    "explanation": c.explanation,
                    "v1_text": c.v1_text,
                    "v2_text": c.v2_text,
                }
                for c in result.changes
            ],
        }
        out.json_out(data)
    else:
        out.writeln(f"Ṛta v{APP_VERSION} — Constraint Change Analysis")
        out.writeln(f"  V1: {args.v1.name}")
        out.writeln(f"  V2: {args.v2.name}")
        out.writeln()
        out.writeln(f"  {'Constraints V1:':<20} {result.stats.get('v1_constraints', 0)}")
        out.writeln(f"  {'Constraints V2:':<20} {result.stats.get('v2_constraints', 0)}")
        out.writeln(f"  {'Added:':<20} {result.stats.get('added', 0)}")
        out.writeln(f"  {'Removed:':<20} {result.stats.get('removed', 0)}")
        out.writeln(f"  {'Modified:':<20} {result.stats.get('modified', 0)}")
        out.writeln(f"  {'Fatal:':<20} {result.stats.get('fatal', 0)}")
        out.writeln(f"  {'Warnings:':<20} {result.stats.get('warnings', 0)}")
        out.writeln(f"  {'Info:':<20} {result.stats.get('info', 0)}")
        out.writeln()

        for c in result.changes:
            label = f"[{c.rule.rule_id}]"
            out.writeln(f"  {c.rule.severity.upper():>7} {label:<15} {c.explanation}")
            if args.verbose and c.v1_text:
                out.writeln(f"           V1: {c.v1_text[:80]}")
            if args.verbose and c.v2_text:
                out.writeln(f"           V2: {c.v2_text[:80]}")

    out.flush()


def _load_linked_files(paths: list[str]):
    """Load linked TCL files by reading each path directly.

    paths may be specified multiple times: --linked-v1 file1.tcl --linked-v1 file2.tcl
    Returns {filename: content} dict for the constraint_diff API.
    """
    files = {}
    for path in paths:
        try:
            with open(path, "r", encoding="utf-8") as f:
                files[os.path.basename(path)] = f.read()
        except Exception as e:
            print(f"Warning: cannot load linked file '{path}': {e}", file=sys.stderr)
    return files


# ── Subcommand: corners ──────────────────────────────────────────────────────

def cmd_corners(args):
    """Manage and inspect PVT corner presets."""
    from corner_manager import CORNER_PRESETS, corner_matrix, validate_corner

    out = OutputWriter(args.output)

    if args.action == "list":
        out.writeln(f"Available corner presets ({len(CORNER_PRESETS)}):")
        out.writeln()
        for name, corners in CORNER_PRESETS.items():
            if not corners:
                out.writeln(f"  {name}")
            else:
                out.writeln(f"  {name}  ({len(corners)} corners)")

    elif args.action == "show":
        name = args.preset_name
        corners = CORNER_PRESETS.get(name)
        if corners is None:
            # Try partial match
            matches = [k for k in CORNER_PRESETS if name.lower() in k.lower()]
            if len(matches) == 1:
                corners = CORNER_PRESETS[matches[0]]
                name = matches[0]
            elif len(matches) > 1:
                fatal(f"'{name}' matches multiple presets: {matches}")
            else:
                fatal(f"preset '{name}' not found. Use 'corners list' to see available.")

        out.writeln(f"Preset: {name}")
        out.writeln(f"Corners: {len(corners)}")
        out.writeln()

        for c in corners:
            out.writeln(f"  {c.name}")
            out.writeln(f"    Process: {c.process_type}  V={c.voltage:.2f}V  T={c.temperature:.0f}°C")
            out.writeln(f"    Op Cond: {c.operating_condition or '(none)'}")
            out.writeln(f"    Derate:  cell_early={c.derate_cell_early:.3f}  cell_late={c.derate_cell_late:.3f}")
            out.writeln(f"             net_early={c.derate_net_early:.3f}   net_late={c.derate_net_late:.3f}")
            out.writeln(f"    Uncertainty scale: {c.uncertainty_scale:.2f}")
            errors = validate_corner(c)
            if errors:
                for e in errors:
                    out.writeln(f"    ⚠  {e}")
            out.writeln()

    out.flush()


# ── Subcommand: analyze ──────────────────────────────────────────────────────

def cmd_analyze(args):
    """Analyze an SDC file (clock relations, or `all` for the full E2E run)."""
    if args.analysis_type == "clock-relations":
        _analyze_clock_relations(args)
    elif args.analysis_type == "all":
        _analyze_all(args)
    else:
        fatal(f"unknown analysis type: {args.analysis_type}")


def _analyze_all(args):
    """One-shot E2E: check + coverage + clock relations + interactions + readiness.

    Runs every deterministic engine over the same SDC (+ optional netlist) and
    emits a single combined result. Purely orchestration — the engine modules
    themselves are unchanged.
    """
    from checker import check_sdc
    import clock_relations as cr
    from coverage import parse_sdc_coverage

    try:
        text = args.file.read()
    except Exception as e:
        fatal(f"cannot read {args.file.name}: {e}")
    finally:
        args.file.close()

    ctx, design_note = _load_design_context(args)

    # 1. Checker (includes scope, interactions, readiness, coverage when ctx)
    check = check_sdc(text, context=ctx)
    # 2. Coverage (category gap analysis)
    cov = parse_sdc_coverage(text, args.file.name)
    # 3. Clock relations
    clock = cr.analyze_clock_relations(text)

    out = OutputWriter(args.output)

    if args.output.lower().endswith(".html"):
        _write_analyze_all_html(args, text, check, cov, clock, ctx)
        sys.exit(1 if check.errors else 0)

    if args.json:
        data = {
            "version": APP_VERSION,
            "file": args.file.name,
            "check": {
                "errors": [{"code": i.code, "msg": i.msg, "line": i.line} for i in check.errors],
                "warnings": [{"code": i.code, "msg": i.msg, "line": i.line} for i in check.warnings],
                "info": [{"code": i.code, "msg": i.msg} for i in check.info],
                "stats": check.stats,
                "analysis_scope": check.scope,
            },
            "coverage": {
                "score_pct": round(cov.score, 1),
                "total_present": cov.total_present,
                "total_items": cov.total_items,
                "missing": cov.total_missing,
            },
            "clock_relations": {
                "stats": clock.stats,
                "mismatches": [
                    {"code": m.code, "severity": m.severity, "clock_a": m.clock_a,
                     "clock_b": m.clock_b, "message": m.msg}
                    for m in clock.mismatches
                ],
            },
            "constraint_interactions": getattr(check, "interactions", {}) or {},
            "constraint_readiness": getattr(check, "readiness", {}) or {},
        }
        if ctx is not None:
            from design_coverage import analyze_coverage as analyze_design_coverage
            data["design_aware_coverage"] = analyze_design_coverage(text, ctx).summary()
        out.json_out(data)
    else:
        sep = "-" * 60
        out.writeln(f"Ṛta v{APP_VERSION} — Full Analysis (E2E)")
        out.writeln(f"File: {args.file.name}")
        if design_note:
            out.writeln(f"  {design_note}")
        out.writeln(sep)

        out.writeln(f"  Checker:    {len(check.errors)} errors, {len(check.warnings)} warnings, "
                    f"{len(check.info)} info")
        out.writeln(f"  Coverage:   {cov.score:.1f}%  ({cov.total_present}/{cov.total_items} items, "
                    f"{cov.total_missing} missing)")
        out.writeln(f"  Clocks:     {clock.stats.get('clocks', 0)} defined, "
                    f"{clock.stats.get('pairs', 0)} pairs, "
                    f"{clock.stats.get('mismatches', 0)} mismatches")
        _int = getattr(check, "interactions", {}) or {}
        _is = _int.get("summary", {})
        if _is:
            out.writeln(f"  Interactions: {_is.get('constraints_analyzed', 0)} analyzed, "
                        f"{_is.get('exact_duplicates', 0)} duplicates, "
                        f"{_is.get('overrides', 0)} overrides, "
                        f"{_is.get('definite_conflicts', 0)} conflicts")
        _rdy = getattr(check, "readiness", {}) or {}
        if _rdy.get("overall"):
            out.writeln(f"  Readiness:  {_rdy['overall']} (mode={_rdy.get('mode', 'SDC_ONLY')})")
            for dim, ev in sorted(_rdy.get("dimensions", {}).items()):
                out.writeln(f"    {dim.replace('_', ' '):<18} {ev.get('status', '—')}")
        out.writeln(sep)

        # Findings (most severe first)
        if check.errors:
            out.writeln("\nErrors:")
            for i in check.errors:
                ln = f" :{i.line}" if i.line else ""
                out.writeln(f"  [{i.code}]{ln} {i.msg}")
        if check.warnings:
            out.writeln("\nWarnings:")
            for i in check.warnings:
                ln = f" :{i.line}" if i.line else ""
                out.writeln(f"  [{i.code}]{ln} {i.msg}")
        if clock.mismatches:
            out.writeln("\nClock relation mismatches:")
            for m in clock.mismatches:
                out.writeln(f"  [{m.code}] {m.clock_a} vs {m.clock_b}: {m.msg}")
        out.writeln("\n  NOTE: constraint-readiness review, NOT an STA timing signoff.")

    out.flush()
    sys.exit(1 if check.errors else 0)


def _write_analyze_all_html(args, text, check, cov, clock, ctx):
    """Compose the one-shot E2E HTML report for `rta analyze all -o x.html`.

    Reuses the reporter's existing section helpers — this is presentation
    only; every number comes from the same engines the text/JSON paths use.
    """
    from reporter import esc, _page, _summary_metrics, _badge, _table, _issue_rows

    err_c, warn_c, info_c = len(check.errors), len(check.warnings), len(check.info)
    total = err_c + warn_c + info_c
    stats = check.stats or {}

    body = _summary_metrics([
        (str(total), "Total Issues", "blue"),
        (str(err_c), "Errors", "red"),
        (str(warn_c), "Warnings", "yellow"),
        (f"{cov.score:.0f}%", "Coverage", "green"),
    ])
    body += _badge(err_c, "Errors", "red") + _badge(warn_c, "Warnings", "yellow")

    # ── Issues ────────────────────────────────────────────────────────────────
    rows = _issue_rows(check.errors, "error", "ERROR")
    rows += _issue_rows(check.warnings, "warn", "WARNING")
    if args.verbose:
        rows += _issue_rows(check.info, "info", "INFO")
    table = _table(["Code", "Severity", "Message", "Rule"], rows) if rows else ""
    body += f"""<div class="section">
<div class="section-title">Issues</div>
{table if table else '<div class="empty-state">No issues found.</div>'}
</div>"""

    # ── Coverage (SDC category gaps) ─────────────────────────────────────────
    cat_rows = ""
    for cat in getattr(cov, "categories", []) or []:
        name = getattr(cat, "name", cat.get("name", "") if isinstance(cat, dict) else str(cat))
        present = getattr(cat, "present", cat.get("present", 0) if isinstance(cat, dict) else 0)
        total_c = getattr(cat, "total", cat.get("total", 0) if isinstance(cat, dict) else 0)
        cat_rows += f"<tr><td>{esc(str(name))}</td><td>{present}/{total_c}</td></tr>\n"
    body += f"""<div class="section">
<div class="section-title">Coverage — {cov.score:.1f}% ({cov.total_present}/{cov.total_items} items, {cov.total_missing} missing)</div>
{_table(["Category", "Present"], cat_rows) if cat_rows else '<div class="empty-state">No categories.</div>'}
</div>"""

    # ── Clock relations ──────────────────────────────────────────────────────
    mm = clock.mismatches or []
    mm_rows = "".join(
        f"<tr><td>{esc(m.clock_a)}</td><td>{esc(m.clock_b)}</td><td><code>{esc(m.code)}</code></td><td>{esc(m.msg)}</td></tr>\n"
        for m in mm
    )
    body += f"""<div class="section">
<div class="section-title">Clock Relations — {clock.stats.get('clocks', 0)} clocks, {clock.stats.get('pairs', 0)} pairs, {len(mm)} mismatches</div>
{_table(["Clock A", "Clock B", "Code", "Message"], mm_rows) if mm_rows else '<div class="empty-state">No clock relation mismatches.</div>'}
</div>"""

    # ── Constraint interactions ──────────────────────────────────────────────
    _int = getattr(check, "interactions", {}) or {}
    _is = _int.get("summary", {}) or {}
    if _is:
        stat_rows = "".join(
            f'<div class="stat-item"><span class="stat-key">{esc(str(k).replace("_", " ").title())}</span><span class="stat-val">{esc(v)}</span></div>'
            for k, v in sorted(_is.items())
        )
        body += f"""<div class="section">
<div class="section-title">Constraint Interactions</div>
<div class="stats-grid">{stat_rows}</div>
</div>"""

    # ── Constraint readiness ─────────────────────────────────────────────────
    _rdy = getattr(check, "readiness", {}) or {}
    if _rdy.get("overall"):
        dim_rows = "".join(
            f'<div class="stat-item"><span class="stat-key">{esc(d.replace("_", " ").title())}</span><span class="stat-val">{esc(ev.get("status", "—"))}</span></div>'
            for d, ev in sorted(_rdy.get("dimensions", {}).items())
        )
        body += f"""<div class="section">
<div class="section-title">Constraint Readiness — {esc(_rdy['overall'])} (mode={esc(_rdy.get('mode', 'SDC_ONLY'))})</div>
<div class="stats-grid">{dim_rows}</div>
</div>"""

    # ── Design-aware coverage (netlist given) ───────────────────────────────
    if ctx is not None:
        from design_coverage import analyze_coverage as analyze_design_coverage
        dc = analyze_design_coverage(text, ctx).summary()
        dc_rows = "".join(
            f'<div class="stat-item"><span class="stat-key">{esc(k.replace("_", " ").title())}</span><span class="stat-val">{esc(v)}</span></div>'
            for k, v in sorted(dc.items())
        )
        body += f"""<div class="section">
<div class="section-title">Design-Aware Coverage (top={esc(ctx.top_module)})</div>
<div class="stats-grid">{dc_rows}</div>
</div>"""

    html = _page(
        f"Full Analysis — {os.path.basename(args.file.name)}",
        f"Ṛta v{APP_VERSION} — check + coverage + clock relations + interactions + readiness",
        body,
    )
    with open(args.output, "w", encoding="utf-8") as fh:
        fh.write(html)
    print(f"Written to {args.output}")
    _print_report_open_hint(args.output)


def _analyze_clock_relations(args):
    """Analyze clock pairs and detect set_clock_groups mismatches."""
    import clock_relations as cr

    try:
        text = args.file.read()
    except Exception as e:
        fatal(f"cannot read {args.file.name}: {e}")
    finally:
        args.file.close()

    ctx, design_note = _load_design_context(args)

    result = cr.analyze_clock_relations(text)

    # Netlist cross-check: reference-resolution findings on lines that define
    # a clock are the ones that matter most here (a broken clock source port).
    clock_net_findings = []
    if ctx is not None:
        from design_context import validate_design_references
        net_findings = validate_design_references(text, ctx)
        text_lines = text.splitlines()
        clock_net_findings = [
            f for f in net_findings
            if f.line and 0 < f.line <= len(text_lines)
            and "create_" in text_lines[f.line - 1] and "clock" in text_lines[f.line - 1]
        ]

    out = OutputWriter(args.output)

    if args.json:
        data = {
            "version": APP_VERSION,
            "file": args.file.name,
            "stats": result.stats,
            "clocks": [
                {"name": c.name, "period": c.period, "source": c.source_port,
                 "generated": c.is_generated, "virtual": c.is_virtual}
                for c in result.clocks
            ],
            "mismatches": [
                {"code": m.code, "severity": m.severity, "clock_a": m.clock_a,
                 "clock_b": m.clock_b, "specified": m.specified, "expected": m.expected,
                 "message": m.msg}
                for m in result.mismatches
            ],
            "pairs": [
                {"clock_a": p.clock_a, "clock_b": p.clock_b,
                 "inferred": p.inferred_relation, "reason": p.reason}
                for p in result.pairs
            ],
        }
        if clock_net_findings:
            data["netlist_check"] = {
                "top": ctx.top_module,
                "clock_source_issues": [
                    {"code": f.code, "line": f.line, "msg": f.msg}
                    for f in clock_net_findings
                ],
            }
        out.json_out(data)
    else:
        out.writeln(f"Ṛta v{APP_VERSION} — Clock Relations Analysis")
        out.writeln(f"File: {args.file.name}")
        if design_note:
            out.writeln(f"  {design_note}")
        out.writeln()
        out.writeln(f"  {'Clocks:':<24} {result.stats.get('clocks', 0)}")
        out.writeln(f"  {'Pairs:':<24} {result.stats.get('pairs', 0)}")
        out.writeln(f"  {'Synchronous:':<24} {result.stats.get('synchronous', 0)}")
        out.writeln(f"  {'Asynchronous:':<24} {result.stats.get('asynchronous', 0)}")
        out.writeln(f"  {'Physically Exclusive:':<24} {result.stats.get('physically_exclusive', 0)}")
        out.writeln(f"  {'Mismatches:':<24} {result.stats.get('mismatches', 0)}")
        out.writeln(f"  {'Missing Constraints:':<24} {result.stats.get('missing', 0)}")
        out.writeln()

        if result.mismatches:
            out.writeln("Mismatches:")
            for m in result.mismatches:
                sev_label = "WARN" if m.severity == "warning" else "INFO"
                out.writeln(f"  [{m.code}] {sev_label}  {m.clock_a} vs {m.clock_b}")
                out.writeln(f"          Specified: {m.specified}")
                out.writeln(f"          Expected:  {m.expected}")
                out.writeln(f"          {m.msg}")
                out.writeln()

        # Netlist cross-check of clock source ports (only when a netlist was given)
        if clock_net_findings:
            out.writeln("Netlist check — clock source ports:")
            for f in clock_net_findings:
                ln = f" :{f.line}" if f.line else ""
                out.writeln(f"  [{f.code}]{ln} {f.msg}")
            out.writeln()

        if result.pairs and args.verbose:
            out.writeln("All Clock Pairs:")
            for p in result.pairs:
                out.writeln(f"  {p.clock_a:<20}  {p.clock_b:<20}  {p.inferred_relation:<22}  ({p.reason[:50]})")

        # Clock definitions
        if args.verbose:
            out.writeln("\nClock Definitions:")
            for c in result.clocks:
                gen = f"  gen={c.master_clock}/{c.divide_by}" if c.is_generated else ""
                virt = "  VIRTUAL" if c.is_virtual else ""
                out.writeln(f"  {c.name:<20}  period={c.period:<8}  port={c.source_port}{gen}{virt}")

    out.flush()


# ── Subcommand: rules ────────────────────────────────────────────────────────

def cmd_rules(args):
    """Look up rule codes from the Rules Registry."""
    out = OutputWriter(args.output)

    if args.action == "list":
        rules = get_all_rules()

        # Filter by module
        if args.module:
            rules = [r for r in rules if r.module == args.module]

        # Filter by severity
        if args.severity:
            rules = [r for r in rules if r.severity == args.severity]

        # Search
        if args.search:
            q = args.search.lower()
            rules = [r for r in rules if q in r.code.lower() or q in r.short_name.lower() or q in r.description.lower()]

        if args.json:
            data = [
                {"code": r.code, "severity": r.severity, "name": r.short_name,
                 "module": r.module, "description": r.description, "added": r.added_version}
                for r in rules
            ]
            out.json_out(data)
        else:
            out.writeln(f"Ṛta v{APP_VERSION} — Rules Registry ({len(rules)} rules)")
            if args.module or args.severity or args.search:
                filters = []
                if args.module:
                    filters.append(f"module={args.module}")
                if args.severity:
                    filters.append(f"severity={args.severity}")
                if args.search:
                    filters.append(f"search='{args.search}'")
                out.writeln(f"  Filters: {', '.join(filters)}")
            out.writeln()
            out.writeln(f"  {'Code':<16} {'Sev':>7} {'Module':<18} {'Name'}")
            out.writeln(f"  {'-'*16} {'-'*7} {'-'*18} {'-'*40}")
            for r in rules:
                out.writeln(f"  {r.code:<16} {r.severity:>7} {r.module:<18} {r.short_name}")

    elif args.action == "show":
        code = args.code.upper()
        rule = get_rule(code)
        if not rule:
            fatal(f"rule '{code}' not found. Use 'rules list' to see available.")
        if args.json:
            out.json_out({
                "code": rule.code,
                "severity": rule.severity,
                "name": rule.short_name,
                "description": rule.description,
                "why_matters": rule.why_matters,
                "fix": rule.fix,
                "module": rule.module,
                "added_version": rule.added_version,
                "reference_url": rule.reference_url,
            })
        else:
            out.writeln(f"  Code:       {rule.code}")
            out.writeln(f"  Severity:   {rule.severity}")
            out.writeln(f"  Name:       {rule.short_name}")
            out.writeln(f"  Module:     {rule.module}")
            out.writeln(f"  Added:      v{rule.added_version}")
            out.writeln(f"  Description: {rule.description}")
            out.writeln(f"  Why:        {rule.why_matters}")
            out.writeln(f"  Fix:        {rule.fix}")
            if rule.reference_url:
                out.writeln(f"  Reference:  {rule.reference_url}")

    out.flush()


# ── Subcommand: coverage ─────────────────────────────────────────────────────

def _load_design_context(args):
    """Parse an optional --netlist into a DesignContext; returns (ctx, note).

    Shared by coverage / analyze clock-relations / report check so the
    netlist flag behaves identically across commands (additive — the core
    parser module is never touched here).
    """
    if not getattr(args, "netlist", None):
        return None, ""
    try:
        v_text = args.netlist.read()
    except Exception as e:
        fatal(f"cannot read netlist {args.netlist.name}: {e}")
    finally:
        args.netlist.close()
    from design_context import parse_verilog
    outcome = parse_verilog(v_text, top=getattr(args, "top", "") or "")
    if outcome.errors:
        fatal(f"netlist: {outcome.errors[0]}")
    ctx = outcome.context
    counts = ctx.object_counts()
    note = (f"Design context: {ctx.top_module} "
            f"({counts['ports']} ports, {counts['instances']} instances)")
    return ctx, note


def cmd_coverage(args):
    """Analyze constraint coverage in an SDC file."""
    from coverage import parse_sdc_coverage

    try:
        text = args.file.read()
    except Exception as e:
        fatal(f"cannot read {args.file.name}: {e}")
    finally:
        args.file.close()

    ctx, design_note = _load_design_context(args)

    result = parse_sdc_coverage(text, args.file.name)
    # Optional design-aware port coverage (SDC-064..066) when a netlist is given.
    design_cov = None
    if ctx is not None:
        from design_coverage import analyze_coverage as analyze_design_coverage
        design_cov = analyze_design_coverage(text, ctx)

    out = OutputWriter(args.output)

    if args.json:
        data = {
            "version": APP_VERSION,
            "file": args.file.name,
            "score_pct": round(result.score, 1),
            "total_items": result.total_items,
            "total_present": result.total_present,
            "total_missing": result.total_missing,
            "categories": [
                {
                    "name": cat.name,
                    "score": round(cat.score, 1),
                    "covered": cat.covered,
                    "total": cat.total,
                    "missing": cat.missing,
                    "items": [
                        {"name": it.name, "present": it.present, "critical": it.is_critical, "detail": it.detail}
                        for it in cat.items
                    ],
                }
                for cat in result.categories
            ],
        }
        if design_cov is not None:
            data["design_aware"] = design_cov.summary()
            data["design_context"] = {
                "top": ctx.top_module,
                "ports": ctx.object_counts()["ports"],
                "instances": ctx.object_counts()["instances"],
            }
        out.json_out(data)
    else:
        out.writeln(f"Ṛta v{APP_VERSION} — Constraint Coverage Analysis")
        out.writeln(f"File: {args.file.name}")
        if design_note:
            out.writeln(f"  {design_note}")
        out.writeln()
        out.writeln(f"  Overall Coverage: {result.score:.1f}%  ({result.total_present}/{result.total_items} items)")
        out.writeln(f"  Missing: {result.total_missing}")
        out.writeln("-" * 60)

        if args.missing_only:
            # Compact: only show missing items
            for cat in result.categories:
                missing = [it for it in cat.items if not it.present]
                if missing:
                    out.writeln(f"\n  {cat.icon} {cat.name}: {cat.score:.0f}%  ({cat.covered}/{cat.total})")
                    for item in missing:
                        crit = " *" if item.is_critical else ""
                        out.writeln(f"    [N] {item.name}{crit}")
                        if item.detail:
                            out.writeln(f"         {item.detail}")
        else:
            # Full output: show all categories
            for cat in result.categories:
                bar = _bar_chart(cat.score)
                out.writeln(f"\n  {cat.icon} {cat.name}: {cat.score:.0f}%  {bar}  ({cat.covered}/{cat.total})")
                for item in cat.items:
                    mark = "Y" if item.present else "N"
                    crit = " *" if item.is_critical and not item.present else ""
                    out.writeln(f"    [{mark}] {item.name}{crit}")
                    if item.detail:
                        out.writeln(f"         {item.detail}")

        # Design-aware port coverage (only when a netlist was supplied)
        if design_cov is not None:
            out.writeln("-" * 60)
            out.writeln("Design-aware port coverage (netlist supplied):")
            s = design_cov.summary()
            out.writeln(f"    inputs:  {_fmt_cov_bucket(s['inputs'])}")
            out.writeln(f"    outputs: {_fmt_cov_bucket(s['outputs'])}")
            out.writeln(f"    clocks:  {s['clocks']['defined']} defined, "
                        f"{s['clocks']['structurally_resolved']} structurally resolved")
            exc = s["exceptions"]
            out.writeln(f"    exceptions: {exc['total']} total "
                        f"(resolved={exc['objects_resolved']}, empty={exc['empty_collection']})")
            out.writeln("    coverage is NOT correctness — a fully covered design can still have timing errors.")

    out.flush()


def _bar_chart(pct: float, width: int = 20) -> str:
    """Simple ASCII bar chart: [████████░░░░░░░░░░░░]"""
    filled = int(pct / 100 * width)
    return "[" + "#" * filled + "." * (width - filled) + "]"


# ── Subcommand: web ───────────────────────────────────────────────────────────

def cmd_web(args):
    """Launch the local Ṛta workspace.

    Starts the stdlib-only API server that serves the static product frontend
    (``rta/workspace/webui/``) and exposes the frozen deterministic backend over
    HTTP. No new runtime dependencies; works offline.
    """
    import subprocess
    import sys
    import webbrowser

    port = int(getattr(args, "port", None) or 8501)
    # Resolve api_server.py relative to this file so `rta web` works from any cwd.
    server_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                               "api", "api_server.py")
    if not os.path.exists(server_path):
        sys.exit(f"error: cannot find api_server.py at {server_path} — is the repository intact?")
    url = f"http://127.0.0.1:{port}"
    print(f"Ṛta — opening {url}")
    threading_timer = None
    try:
        webbrowser.open(url)
    except Exception:  # pragma: no cover - headless environments
        pass
    subprocess.run([sys.executable, server_path, str(port)])


# ── Subcommand: report ───────────────────────────────────────────────────────

def cmd_report(args):
    """Generate formatted signoff reports (HTML)."""
    from reporter import generate_check_report, generate_diff_report, generate_clock_report, generate_coverage_report

    if args.report_type == "check":
        from checker import check_sdc
        try:
            text = args.file.read()
        except Exception as e:
            fatal(f"cannot read {args.file.name}: {e}")
        finally:
            args.file.close()

        ctx, _ = _load_design_context(args)
        result = check_sdc(text, context=ctx)
        # Phase 12: optional readiness-diff section in the report when a
        # baseline snapshot is supplied (--baseline).
        diff_for_report = None
        if getattr(args, "baseline", ""):
            baseline_snap = _read_baseline(args.baseline)
            from readiness_diff import build_snapshot, diff_snapshots
            cur_snap = build_snapshot(result, context=ctx, source_name=args.file.name)
            diff_for_report = diff_snapshots(baseline_snap, cur_snap)
            if getattr(args, "gate", ""):
                from readiness_diff import evaluate_gate
                policy_data = None
                if args.gate == "CUSTOM":
                    if not getattr(args, "gate_policy", ""):
                        fatal("--gate CUSTOM requires --gate-policy FILE", code=2)
                    policy_data = _load_policy_file(args.gate_policy)
                diff_for_report["gate"] = evaluate_gate(
                    args.gate, baseline_snap, cur_snap, diff_for_report,
                    policy_data=policy_data)
        html = generate_check_report(result, args.file.name, verbose=args.verbose,
                                     readiness_diff=diff_for_report)
        _write_report(html, args.output)

    elif args.report_type == "diff":
        from constraint_diff import analyze_constraint_changes

        linked_v1 = _load_linked_files(getattr(args, "linked_v1", [])) if getattr(args, "linked_v1", None) else None
        linked_v2 = _load_linked_files(getattr(args, "linked_v2", [])) if getattr(args, "linked_v2", None) else None
        v1_name = getattr(args, "v1_name", None) or (getattr(args, "v1", None) and args.v1.name)
        v2_name = getattr(args, "v2_name", None) or (getattr(args, "v2", None) and args.v2.name)

        try:
            v1_text = args.v1.read()
            v2_text = args.v2.read()
        except Exception as e:
            fatal(f"cannot read diff files: {e}")
        finally:
            args.v1.close()
            args.v2.close()

        result = analyze_constraint_changes(v1_text, v2_text, linked_v1, linked_v2)
        html = generate_diff_report(result, v1_name or "", v2_name or "")
        _write_report(html, args.output)

    elif args.report_type == "clock-relations":
        import clock_relations as cr

        try:
            text = args.cr_file.read()
        except Exception as e:
            fatal(f"cannot read {args.cr_file.name}: {e}")
        finally:
            args.cr_file.close()

        result = cr.analyze_clock_relations(text)
        html = generate_clock_report(result, args.cr_file.name)
        _write_report(html, args.output)

    elif args.report_type == "coverage":
        from coverage import parse_sdc_coverage

        try:
            text = args.cov_file.read()
        except Exception as e:
            fatal(f"cannot read {args.cov_file.name}: {e}")
        finally:
            args.cov_file.close()

        result = parse_sdc_coverage(text, args.cov_file.name)
        html = generate_coverage_report(result, args.cov_file.name)
        _write_report(html, args.output)

    else:
        fatal(f"unknown report type: {args.report_type}")


def _print_report_open_hint(output_path: str):
    """Print how to open a generated HTML report on the current platform."""
    if os.name == "nt":
        hint = f"start {output_path}"
    else:
        hint = f"open {output_path}"
    print(f"Open with: {hint}")


def _write_report(html: str, output_path: str):
    """Write HTML to file or stdout."""
    if output_path:
        try:
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(html)
        except OSError as e:
            fatal(f"cannot write report '{output_path}': {e}", code=2)
        print(f"Written to {output_path}")
        _print_report_open_hint(output_path)
    else:
        sys.stdout.reconfigure(encoding="utf-8") if hasattr(sys.stdout, "reconfigure") else None
        print(html)


# ── Subcommand: lint ─────────────────────────────────────────────────────────────

def cmd_lint(args):
    """Lint / reformat an SDC file."""
    from linter import lint_sdc_file

    filepath = args.file
    if not os.path.exists(filepath):
        fatal(f"file not found: {filepath}")

    output_path = args.output or (filepath if args.fix else "")

    result = lint_sdc_file(filepath, fix=not args.check, output_path=output_path or None)

    if args.check:
        for issue in result.issues:
            print(f"  {issue}")
        if result.warnings > 0:
            print(f"  {result.warnings} issue(s) found")
            sys.exit(1)
        print("  SDC file is lint-clean")
        return

    if args.output:
        print(f"Formatted SDC written to {args.output}")
    elif not args.fix:
        # stdout
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except AttributeError:
            pass
        print(result.formatted_text or result.original_text)

    if result.issues:
        print(f"\n  Lint: {result.warnings} warning(s), {result.fixed} fix(es)", file=sys.stderr)


# ── Subcommand: convert ──────────────────────────────────────────────────────────

def cmd_convert(args):
    """Convert SDC to JSON or YAML."""
    from converter import sdc_to_json, sdc_to_yaml

    try:
        text = args.file.read()
    except Exception as e:
        fatal(f"cannot read {args.file.name}: {e}")
    finally:
        args.file.close()

    if args.format == "yaml":
        output = sdc_to_yaml(text, args.file.name)
    else:
        output = sdc_to_json(text, args.file.name)

    if args.output:
        _write_output_file(args.output, output)
        print(f"Written to {args.output}")
    else:
        print(output)


# ── Subcommand: batch ────────────────────────────────────────────────────────────

def cmd_batch(args):
    """Batch process SDC files in a directory."""
    from batch_runner import batch_check, batch_report, batch_lint

    if args.batch_command == "check":
        summary = batch_check(args.directory, verbose=args.verbose)
    elif args.batch_command == "report":
        summary = batch_report(args.directory, args.report_type, output_dir=args.output_dir)
    elif args.batch_command == "lint":
        summary = batch_lint(args.directory, fix=args.fix)
    else:
        fatal(f"unknown batch command: {args.batch_command}")

    print(summary.print_summary())

    if summary.errors > 0:
        for r in summary.results:
            if r.status == "error":
                print(f"  ✗ {r.filepath}: {r.message}")
    sys.exit(1 if summary.errors > 0 else 0)


# ── Main CLI ─────────────────────────────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    # `rta` is the Ṛta entry point (the legacy `sdc-tools` name was dropped in
    # the rebrand). Help text follows the invoked name when run as `rta`.
    _invoked = os.path.basename(sys.argv[0]).replace(".exe", "")
    prog = _invoked if _invoked == "rta" else "rta"
    parser = argparse.ArgumentParser(
        prog=prog,
        description="Ṛta — deterministic SDC constraint verification toolkit",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent("""\
            Examples:
              rta check sample.sdc
              rta check sample.sdc --json
              rta check sample.sdc --junit --output results.xml
              rta generate --design MY_CHIP --clock clk=10.0:sys_clk > output.sdc
              rta diff old.sdc new.sdc
              rta corners list
              rta corners show "Classic 3-corner"
              rta analyze clock-relations input.sdc
              rta rules list --module checker
              rta rules show SDC-060
        """),
    )
    parser.add_argument("--version", action="version", version=f"Ṛta v{APP_VERSION}")

    sub = parser.add_subparsers(dest="command", help="Available commands")

    # ── check ──
    p_check = sub.add_parser("check", help="Validate an SDC file", description="Parse and validate an SDC file, reporting errors, warnings, and best-practice suggestions.")
    p_check.add_argument("file", type=argparse.FileType("r", encoding="utf-8"), help="Path to .sdc file")
    p_check.add_argument("--json", action="store_true", help="Output JSON")
    p_check.add_argument("--junit", action="store_true", help="Output JUnit XML (for CI)")
    p_check.add_argument("--output", "-o", default="", help="Write output to file instead of stdout")
    p_check.add_argument("--verbose", "-v", action="store_true", help="Show info items and stats")
    p_check.add_argument("--custom-rules", action="append", default=[], metavar="YAML", help="Path to custom rules YAML file (repeatable)")
    p_check.add_argument("--format", "-f", choices=["text", "csv", "markdown"], default="text", help="Output format (default: text)")
    p_check.add_argument("--netlist", "-n", type=argparse.FileType("r", encoding="utf-8"), default=None,
                         help="Optional Verilog netlist for design-aware validation (SDC-055..059) and constraint coverage (SDC-064..066)")
    p_check.add_argument("--top", default="", help="Top module name (required if netlist has multiple candidates)")
    # ── Readiness baseline / CI gate (Phase 12) ──
    p_check.add_argument("--save-baseline", default="", metavar="JSON",
                         help="Write a machine-readable readiness snapshot to this JSON file")
    p_check.add_argument("--baseline", default="", metavar="JSON",
                         help="Compare against a previously saved readiness baseline snapshot")
    p_check.add_argument("--gate", choices=["BLOCKERS_ONLY", "NO_READINESS_REGRESSION", "STRICT", "CUSTOM"],
                         default="", help="Opt-in CI quality gate. Exit codes: 0=pass, 1=gate failed, "
                         "2=invalid input, 3=engine failure. Never enabled by default.")
    p_check.add_argument("--gate-policy", default="", metavar="FILE",
                         help="Declarative CUSTOM policy file (JSON or YAML) — required when --gate CUSTOM. "
                         "Policies are inert data: they select which existing diff evidence fails the gate.")

    # ── generate ──
    p_gen = sub.add_parser("generate", help="Generate an SDC file", description="Generate a complete synthesis-ready SDC file from CLI parameters.")
    p_gen.add_argument("--design", "-d", default="MY_DESIGN", help="Design name (default: MY_DESIGN)")
    p_gen.add_argument("--clock", "-c", action="append", default=[], metavar="NAME=PERIOD[:PORT]", help="Add a clock, e.g. clk=10.0:sys_clk")
    p_gen.add_argument("--uncertainty", "-u", type=float, default=0.15, help="Clock uncertainty in ns (default: 0.15)")
    p_gen.add_argument("--sdc-version", default="2.2", help="SDC version (default: 2.2)")
    p_gen.add_argument("--operating-condition", default="", help="Operating condition name")
    p_gen.add_argument("--derate", action="store_true", help="Add AOCV timing derate")
    p_gen.add_argument("--ideal-reset", action="store_true", help="Add set_ideal_network + set_false_path on reset")
    p_gen.add_argument("--reset-port", default="rst_n", help="Reset port name (default: rst_n)")
    p_gen.add_argument("--propagated", action="store_true", help="Add set_propagated_clock")
    p_gen.add_argument("--scan", action="store_true", help="Add DFT scan mode case analysis")
    p_gen.add_argument("--scan-port", default="scan_mode", help="Scan port name (default: scan_mode)")
    p_gen.add_argument("--output", "-o", default="", help="Output file path")

    # ── diff ──
    p_diff = sub.add_parser("diff", help="Compare two SDC files (semantic diff)", description="Detect hidden changes between SDC versions with semantic constraint comparison, TCL variable resolution, and wildcard drift detection.")
    p_diff.add_argument("v1", type=argparse.FileType("r", encoding="utf-8"), help="First (older) SDC file")
    p_diff.add_argument("v2", type=argparse.FileType("r", encoding="utf-8"), help="Second (newer) SDC file")
    p_diff.add_argument("--linked-v1", action="append", default=[], metavar="FILE", help="TCL file with V1 variable definitions (repeatable)")
    p_diff.add_argument("--linked-v2", action="append", default=[], metavar="FILE", help="TCL file with V2 variable definitions (repeatable)")
    p_diff.add_argument("--json", action="store_true", help="Output JSON")
    p_diff.add_argument("--output", "-o", default="", help="Write output to file")
    p_diff.add_argument("--verbose", "-v", action="store_true", help="Show V1/V2 text for changes")

    # ── corners ──
    p_corners = sub.add_parser("corners", help="List / inspect PVT corner presets", description="Manage and inspect predefined PVT timing corner collections.")
    p_corners.add_argument("action", choices=["list", "show"], help="list: available presets; show: preset details")
    p_corners.add_argument("preset_name", nargs="?", default="", help="Preset name to show (partial match OK)")
    p_corners.add_argument("--output", "-o", default="", help="Write output to file")

    # ── analyze ──
    p_analyze = sub.add_parser("analyze", help="Analyze clock relations / constraints", description="Deep analysis of SDC content such as clock relation inference and mismatch detection.")
    p_analyze.add_argument("analysis_type", choices=["clock-relations", "all"], help="Type of analysis: clock-relations, or all (full E2E run)")
    p_analyze.add_argument("file", type=argparse.FileType("r", encoding="utf-8"), help="SDC file to analyze")
    p_analyze.add_argument("--json", action="store_true", help="Output JSON")
    p_analyze.add_argument("--output", "-o", default="", help="Write output to file")
    p_analyze.add_argument("--verbose", "-v", action="store_true", help="Show all clock pairs and definitions")
    p_analyze.add_argument("--netlist", "-n", type=argparse.FileType("r", encoding="utf-8"), default=None,
                           help="Optional Verilog netlist — cross-checks clock source ports against real design objects")
    p_analyze.add_argument("--top", default="", help="Top module name (required if netlist has multiple candidates)")

    # ── rules ──
    p_rules = sub.add_parser("rules", help="Look up rule codes from the Rules Registry", description="Search, list, and inspect all SDC-NNN, CHG-XXX-NNN rule codes with descriptions and engineering context.")
    p_rules.add_argument("action", choices=["list", "show"], help="list: all rules; show: single rule details")
    p_rules.add_argument("code", nargs="?", default="", help="Rule code, e.g. SDC-060 (for show)")
    p_rules.add_argument("--module", "-m", default="", help="Filter by module: checker, mmc, clock_relations, constraint_diff, design_context, design_coverage")
    p_rules.add_argument("--severity", "-s", default="", help="Filter by severity: error, warning, info, fatal")
    p_rules.add_argument("--search", default="", help="Search text in code, name, description")
    p_rules.add_argument("--json", action="store_true", help="Output JSON")
    p_rules.add_argument("--output", "-o", default="", help="Write output to file")

    # ── web ──
    sub.add_parser("web", help="Launch the Streamlit web UI",
                   description="Launch the Ṛta workspace in your browser.")

    # ── coverage ──
    p_cov = sub.add_parser("coverage", help="Analyze constraint coverage", description="Measure which constraint categories are covered vs. missing in an SDC file — gap analysis for signoff readiness.")
    p_cov.add_argument("file", type=argparse.FileType("r", encoding="utf-8"), help="SDC file to analyze")
    p_cov.add_argument("--json", action="store_true", help="Output JSON")
    p_cov.add_argument("--missing-only", action="store_true", help="Show only missing items")
    p_cov.add_argument("--output", "-o", default="", help="Write output to file")
    p_cov.add_argument("--netlist", "-n", type=argparse.FileType("r", encoding="utf-8"), default=None,
                       help="Optional Verilog netlist — design-aware port-level coverage (SDC-064..066) in addition to the category gap analysis")
    p_cov.add_argument("--top", default="", help="Top module name (required if netlist has multiple candidates)")

    # ── report ──
    p_report = sub.add_parser("report", help="Generate HTML signoff reports", description="Generate professional HTML signoff reports from checker, diff, or analysis results.")
    rsub = p_report.add_subparsers(dest="report_type", help="Report type")

    # report check
    p_rcheck = rsub.add_parser("check", help="SDC quality report")
    p_rcheck.add_argument("file", type=argparse.FileType("r", encoding="utf-8"), help="SDC file to report on")
    p_rcheck.add_argument("--verbose", "-v", action="store_true", help="Include info-level items in report")
    p_rcheck.add_argument("--output", "-o", default="", help="Output HTML file")
    p_rcheck.add_argument("--baseline", default="", metavar="JSON",
                          help="Optional readiness baseline snapshot to include a Readiness Diff section")
    p_rcheck.add_argument("--netlist", "-n", type=argparse.FileType("r", encoding="utf-8"), default=None,
                          help="Optional Verilog netlist — report includes design-aware findings (SDC-055..066)")
    p_rcheck.add_argument("--top", default="", help="Top module name (required if netlist has multiple candidates)")
    p_rcheck.add_argument("--gate", choices=["BLOCKERS_ONLY", "NO_READINESS_REGRESSION", "STRICT", "CUSTOM"],
                          default="", help="Optional CI gate verdict included in the report (requires --baseline)")
    p_rcheck.add_argument("--gate-policy", default="", metavar="FILE",
                          help="Declarative CUSTOM policy file — required when --gate CUSTOM")

    # report diff
    p_rdiff = rsub.add_parser("diff", help="SDC change impact report")
    p_rdiff.add_argument("v1", type=argparse.FileType("r", encoding="utf-8"), help="First (older) SDC file")
    p_rdiff.add_argument("v2", type=argparse.FileType("r", encoding="utf-8"), help="Second (newer) SDC file")
    p_rdiff.add_argument("--v1-name", default="", help="Label for V1 (default: filename)")
    p_rdiff.add_argument("--v2-name", default="", help="Label for V2 (default: filename)")
    p_rdiff.add_argument("--linked-v1", action="append", default=[], metavar="FILE", help="TCL file with V1 variable definitions (repeatable)")
    p_rdiff.add_argument("--linked-v2", action="append", default=[], metavar="FILE", help="TCL file with V2 variable definitions (repeatable)")
    p_rdiff.add_argument("--output", "-o", default="", help="Output HTML file")

    # report clock-relations
    p_rcr = rsub.add_parser("clock-relations", help="Clock relations analysis report")
    p_rcr.add_argument("cr_file", metavar="file", type=argparse.FileType("r", encoding="utf-8"), help="SDC file to analyze")
    p_rcr.add_argument("--output", "-o", default="", help="Output HTML file")

    # report coverage
    p_rcov = rsub.add_parser("coverage", help="Constraint coverage analysis report")
    p_rcov.add_argument("cov_file", metavar="file", type=argparse.FileType("r", encoding="utf-8"), help="SDC file to analyze")
    p_rcov.add_argument("--output", "-o", default="", help="Output HTML file")

    # ── lint ──
    p_lint = sub.add_parser("lint", help="Lint / reformat SDC file",
                            description="Reorganize and clean up SDC constraint files — consistent section ordering, spacing, and formatting.")
    p_lint.add_argument("file", help="SDC file path")
    p_lint.add_argument("--check", action="store_true", help="Check mode: exit 1 if not lint-clean (no output)")
    p_lint.add_argument("--fix", action="store_true", help="Fix in-place (overwrite file)")
    p_lint.add_argument("--output", "-o", default="", help="Write formatted output to file")

    # ── convert ──
    p_conv = sub.add_parser("convert", help="Convert SDC to JSON/YAML",
                            description="Parse an SDC file and output structured JSON or YAML for tool integration.")
    p_conv.add_argument("file", type=argparse.FileType("r", encoding="utf-8"), help="SDC file path")
    p_conv.add_argument("--format", "-f", default="json", choices=["json", "yaml"], help="Output format (default: json)")
    p_conv.add_argument("--output", "-o", default="", help="Write output to file instead of stdout")

    # ── batch ──
    p_batch = sub.add_parser("batch", help="Batch process SDC files",
                             description="Run a command across all .sdc files in a directory.")
    bsub = p_batch.add_subparsers(dest="batch_command", help="Batch operation")

    p_batch_check = bsub.add_parser("check", help="Check all .sdc files in directory")
    p_batch_check.add_argument("directory", help="Directory containing .sdc files")
    p_batch_check.add_argument("--verbose", "-v", action="store_true", help="Show per-file details")

    p_batch_report = bsub.add_parser("report", help="Generate reports for all .sdc files")
    p_batch_report.add_argument("report_type", choices=["check", "coverage"], help="Report type")
    p_batch_report.add_argument("directory", help="Directory containing .sdc files")
    p_batch_report.add_argument("--output-dir", "-o", default="", help="Directory for generated reports")

    p_batch_lint = bsub.add_parser("lint", help="Lint all .sdc files in directory")
    p_batch_lint.add_argument("directory", help="Directory containing .sdc files")
    p_batch_lint.add_argument("--fix", action="store_true", help="Fix files in-place")

    return parser


def main(argv: list[str] | None = None):
    # Force UTF-8 on stdout/stderr so the Unicode brand (Ṛta) survives Windows
    # consoles and pipes with a non-UTF-8 locale (cp1252 etc.).
    for _stream in (sys.stdout, sys.stderr):
        if hasattr(_stream, "reconfigure"):
            try:
                _stream.reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass
    parser = build_parser()
    args = parser.parse_args(argv)

    if not args.command:
        parser.print_help()
        sys.exit(0)

    # Dispatch
    dispatch = {
        "check": cmd_check,
        "generate": cmd_generate,
        "diff": cmd_diff,
        "corners": cmd_corners,
        "analyze": cmd_analyze,
        "rules": cmd_rules,
        "coverage": cmd_coverage,
        "report": cmd_report,
        "web": cmd_web,
        "lint": cmd_lint,
        "convert": cmd_convert,
        "batch": cmd_batch,
    }
    dispatch[args.command](args)


if __name__ == "__main__":
    main()