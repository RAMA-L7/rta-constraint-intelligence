# Ṛta in 5 minutes — from "I have an SDC" to "this regression is blocked in CI"

This is the shortest honest path from *"I have an SDC"* to *"Ṛta found this
problem, here's why, and here's how I prevent the regression in CI."* Every
command below is real and runs on the sample in the repository
(`engineer_test_kit/18_test_drive/`), so you can follow along exactly.

**The one-line summary:** Ṛta is deterministic constraint intelligence for
block-level design — it tells you what is wrong, what is missing, and what
changed in an SDC, *before* STA, and it can gate merges in CI so the same
standard applies to everyone.

---

## Step 0 — Install + get the sample (45 seconds)

```bash
pip install rta-constraint-intelligence
rta --version        # prints the version
```

That's it — no EDA license, no server, no GUI required. The engine is
offline and deterministic; it does not call any LLM or cloud service.

The sample walkthrough below runs on a small DMA-engine block that ships in
the repository (a realistic design is too large to embed in the wheel). Grab
it once — the rest of the guide runs on your own SDC exactly the same way:

```bash
git clone --depth 1 https://github.com/RAMA-L7/rta-constraint-intelligence
cd rta-constraint-intelligence
```

---

## Step 1 — Validate your SDC (60 seconds)

```bash
rta check my_block.sdc
```

Run it on the realistic sample to see a real result (this is the V2 revision
of a DMA engine block — an engineer's change that dropped an output delay):

```bash
rta check engineer_test_kit/18_test_drive/dma_engine.sdc \
  --netlist engineer_test_kit/18_test_drive/dma_engine_top.v --top dma_engine_top
```

You get back findings with rule IDs, severities, and source lines. On the
sample you should see:

| Finding | Severity | Meaning |
|---|---|---|
| `SDC-059` + `SDC-065` — `stream_out` unconstrained | warning | A data output port has **no output delay** — its external setup/hold is unverified |
| `SDC-020` ×2 — confirm this false path | warning | Exceptions that read like blanket async cuts need an engineer to confirm |
| Analysis scope / design context | info | With the netlist, Ṛta proves object references against the real design |

> **Trust boundary:** "no errors" is not "timing passes." Ṛta is pre-STA
> constraint intelligence — it tells you the constraints are well-formed and
> complete enough to hand to STA, not that setup/hold will pass.

---

## Step 2 — Understand the finding (60 seconds)

Every rule is documented with **why it matters** and **how to fix it**:

```bash
rta rules show SDC-059     # what it checks, why it matters, the fix
rta rules show SDC-065
rta rules list --module checker   # all checker rules
```

In the web tool, every finding is one click away from the rule's
explanation (Rules tab), and the Test Drive sample explains what to expect
before you run it.

---

## Step 3 — See what changed vs the baseline (60 seconds)

```bash
rta diff engineer_test_kit/18_test_drive/dma_engine_v1.sdc \
  engineer_test_kit/18_test_drive/dma_engine.sdc
```

The diff is semantic, not textual. On the sample it reports exactly the two
regressions an engineer introduced:

- `CHG-GEN-002` — **removed** `set_output_delay ... [get_ports stream_out]`
- `CHG-GEN-003` — the async clock group **lost `clk_periph`**

This is the "why you keep using Ṛta" step: it names the change, not just
"something is different."

---

## Step 4 — Prevent the regression in CI (60 seconds)

```bash
# Once, on the known-good state — commit this file to your repo:
rta check engineer_test_kit/18_test_drive/dma_engine_v1.sdc \
  --netlist engineer_test_kit/18_test_drive/dma_engine_top.v --top dma_engine_top \
  --save-baseline baseline.json

# In CI, on every change:
rta check engineer_test_kit/18_test_drive/dma_engine.sdc \
  --netlist engineer_test_kit/18_test_drive/dma_engine_top.v --top dma_engine_top \
  --baseline baseline.json --gate STRICT
echo $?   # 0 = PASS (merge allowed), 1 = FAIL (merge blocked)
```

On the sample this exits **1** — the `stream_out` regression is blocked.
Reverting to V1 exits **0**.

Or add it to any pipeline in one step with the shipped GitHub Action:

```yaml
- uses: ./.github/actions/rta-gate          # see docs/features/README-14-ci-gate.md
  with:
    sdc: constraints/my_block.sdc
    netlist: rtl/my_block.v                 # optional
    top: my_block_top
    baseline: baseline.json                 # from --save-baseline above
    gate: STRICT
```

The gate exit codes are the contract: **0 = pass, 1 = gate failed, 2 =
invalid input, 3 = engine failure.** A gate can never report PASS on
incomplete evidence.

> **CI PASS ≠ timing pass.** The gate checks for disallowed
> constraint-readiness regressions under your chosen policy — it does not
> replace STA.

---

## Step 5 — Share the evidence (60 seconds)

```bash
rta report check engineer_test_kit/18_test_drive/dma_engine.sdc \
  --netlist engineer_test_kit/18_test_drive/dma_engine_top.v --top dma_engine_top \
  --baseline baseline.json --gate STRICT \
  -o report.html        # self-contained HTML: findings + readiness + gate verdict
```

Open `report.html` in any browser and share it with the review. That is the
whole loop:

```
Validate  →  understand the finding  →  diff vs baseline  →  gate in CI  →  report
```

---

## What you now know

1. What is wrong with the SDC (rule IDs + why).
2. What is missing (unconstrained ports, missing clock groups).
3. What changed since the last reviewed state (semantic diff).
4. How to stop the same regression reaching main (CI gate).
5. How to hand the evidence to the review (HTML report).

**Everything else Ṛta does** (generator, linter, converter, clock relations,
coverage, corners/MMC, custom rules, batch) builds on this same engine — the
full CLI guide is `docs/features/README-11-cli-user-guide.md`, the CI gate
contract is `docs/features/README-14-ci-gate.md`, and the complete fixture
library is in `engineer_test_kit/`.
