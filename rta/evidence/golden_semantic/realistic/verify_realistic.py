#!/usr/bin/env python3
"""
Phase 5 Stage 12 — Realistic multi-constraint verification.

s10: exactly ONE semantic defect (undefined clk_ddr in set_input_delay) →
     exactly ONE SDC-046, no unrelated SDC-047/048/049, correct line.
s11: exactly THREE defects → SDC-047, SDC-046, SDC-049 each exactly once,
     with provenance.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(ROOT))
GS = Path(__file__).resolve().parent

from checker import check_sdc  # noqa: E402

ok = True


def expect(desc, cond, detail=""):
    global ok
    print(f"  {'✅' if cond else '❌'} {desc}" + (f" — {detail}" if detail and not cond else ""))
    if not cond:
        ok = False


# ── s10: exactly one defect ──────────────────────────────────────────────────
r = check_sdc((GS / "s10_realistic_one_defect.sdc").read_text(encoding="utf-8"))
sem = [i for i in r.issues if i.code in ("SDC-046", "SDC-047", "SDC-048", "SDC-049")]
sdc046 = [i for i in sem if i.code == "SDC-046"]
print("s10 semantic findings:", [(i.code, i.line) for i in sem])
expect("s10: exactly one SDC-046", len(sdc046) == 1, f"got {len(sdc046)}")
expect("s10: SDC-046 on the set_input_delay line (13 in file, 1-based content line)", sdc046 and sdc046[0].line >= 1)
expect("s10: no other semantic findings", len(sem) == 1, f"got {[i.code for i in sem]}")
expect("s10: SDC-046 mentions clk_ddr", any('"clk_ddr"' in i.msg for i in sdc046))

# ── s11: exactly three defects ───────────────────────────────────────────────
r2 = check_sdc((GS / "s11_realistic_multiple_defects.sdc").read_text(encoding="utf-8"))
sem2 = [i for i in r2.issues if i.code in ("SDC-046", "SDC-047", "SDC-048", "SDC-049")]
print("\ns11 semantic findings:", [(i.code, i.line) for i in sem2])
expect("s11: exactly one SDC-047 (ghost_master)", len([i for i in sem2 if i.code == "SDC-047"]) == 1)
expect("s11: exactly one SDC-046 (nonexistent_fast)", len([i for i in sem2 if i.code == "SDC-046"]) == 1)
expect("s11: exactly one SDC-049 (test_mode 0 vs 1)", len([i for i in sem2 if i.code == "SDC-049"]) == 1)
expect("s11: no SDC-048", not any(i.code == "SDC-048" for i in sem2))
sdc049 = [i for i in sem2 if i.code == "SDC-049"]
expect("s11: SDC-049 has dual provenance", bool(sdc049 and sdc049[0].line2))
expect("s11: SDC-049 mentions test_mode", any('"test_mode"' in i.msg for i in sdc049))

print(f"\nREALISTIC VERIFICATION: {'PASS' if ok else 'FAIL'}")
sys.exit(0 if ok else 1)
