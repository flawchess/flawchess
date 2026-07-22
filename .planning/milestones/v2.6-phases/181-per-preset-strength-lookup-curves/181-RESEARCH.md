# Phase 181: Per-preset strength lookup curves - Research

**Researched:** 2026-07-21
**Domain:** Offline data-processing / codegen (Python stdlib fitting + generated TS artifact) — no runtime backend/frontend surface
**Confidence:** HIGH

## Summary

Phase 181 is a pure offline data-transformation phase: take the 15 measured cells already
landed in `reports/data/bot-curves-internal-scale.json` (Phase 180) and turn them into a
shipping lookup artifact. There is no new library, no new external dependency, no UI, no DB, and
no API surface — everything needed already exists in the codebase as an established pattern
(`scripts/gen_*.py` → committed `frontend/src/generated/*.ts` → CI drift check) and an
established math precedent (`scripts/calibration_anchor_fit.py`'s per-cell/per-preset fit
output). Nearly every open question in `181-CONTEXT.md` resolves directly from reading existing
code and the landed data file, which is why this research carries HIGH confidence with zero
`[ASSUMED]` external-library claims.

The one genuinely new piece of logic this phase must write is a hand-rolled isotonic
regression (Pool Adjacent Violators Algorithm, PAVA) in Python stdlib — matching the
`calibration_anchor_fit.py` D-07 "no numpy/scipy" convention CONTEXT.md already flags. PAVA is
short (~20-30 lines), well-understood, and is exactly the right tool for D-07's "monotone
fit... lowest-bot_elo-wins inversion" requirement. This research verifies the algorithm against
public references and against a hand-computed run over the real Phase-180 data (see Code
Examples / Validation), confirming isotonic fitting produces sensible non-monotone corrections
for Light (bot_elo 1100→1300 dip) and Deep (bot_elo 2300→2600 dip) exactly where CONTEXT.md's
`## Specifics` section says they occur.

The `beyond_ladder=true` flag on the Human bot_elo=700/1100 cells (D-08's open question) is
**not** related to Maia-3's validated policy-input ELO band (1100–2000, `maiaEncoding.ts`) at
all — it is a property of the internal-scale **anchor ladder's own floor/ceiling**
(`sf0=1069.33`, the lowest-rated anchor on the internal scale). Both Human cells' measured
strength (`rating_vs_maia` 882 and 1006) sits below every anchor in the ladder, so
`bracketBeyondLadder()` (`scripts/lib/calibration-bot-cell-schedule.mjs`) correctly flags them
as "no anchor rated below the estimate." This is a boundary condition of the measurement
methodology, not a bug and not related to Maia-3's input-conditioning validity. D-08's decision
to keep these cells in the fit stands unchanged; the flag's *meaning* for the findings note is
now precisely known.

**Primary recommendation:** write one new stdlib-only Python script
(`scripts/gen_bot_strength_curves.py`) that (1) loads `bot-curves-internal-scale.json`, (2) fits
each preset's `internal_rating = f_preset(bot_elo)` via hand-rolled PAVA over `rating_vs_maia`,
(3) applies `− G_preset_combined + C` (C=40 named constant), (4) inverts into a 100-ELO-step
`target_blitz_elo → bot_elo` lookup with inward-rounded per-preset ranges, and (5) emits both a
JSON artifact (`reports/data/bot-strength-lookup.json`) and a generated TS module
(`frontend/src/generated/botStrengthCurves.ts`) following `gen_flaw_thresholds_ts.py`'s exact
`--check`-mode / CI-drift-check pattern, plus a knip exception. A second, much smaller piece —
a confirmation-cell prediction generator — writes 6-9 off-grid `(bot_elo, blend, target_blitz,
predicted_internal_ci)` rows for the operator's HUMAN-UAT run.

## Architectural Responsibility Map

This phase has no live application tiers (browser/SSR/API/DB) in the conventional sense — it
produces a **build-time artifact** consumed by a future phase. Mapped onto the project's actual
architecture:

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Isotonic curve fit (`internal_rating = f_preset(bot_elo)`) | CLI tooling (`scripts/`, Python) | — | Pure offline computation over a frozen JSON input; mirrors `calibration_anchor_fit.py`'s existing bot-cell fit path, never `app/` |
| Offset conversion (`− G_preset + C`) | CLI tooling (`scripts/`) | — | Named-constant arithmetic, no I/O beyond reading the same input JSON |
| Inversion → `target_blitz_elo → bot_elo` lookup | CLI tooling (`scripts/`) | — | Deterministic table build from the fitted curve |
| Lookup JSON artifact | Static file (`reports/data/`) | — | Research-tooling output, not served by the API |
| Generated TS module | Frontend static asset (build-time codegen) | — | Same `gen_*.py` → `frontend/src/generated/*.ts` pattern as `endgameZones.ts`/`flawThresholds.ts`; bundled at Vite build time, not fetched at runtime |
| Confirmation-cell prediction file | CLI tooling (`scripts/`) | — | Written by the same gen script or a small sibling; consumed by the operator running `calibration-harness.mjs` by hand (HUMAN-UAT, off critical path) |
| Confirmation-cell measurement run | Operator-run harness (`scripts/calibration-harness.mjs` + `calibration_anchor_fit.py --bot-input`) | — | Existing Phase-180 machinery, invoked at new off-grid cells; no new harness code |

No browser, SSR, API router, or database work is in scope for this phase (CONTEXT.md's explicit
boundary: "No UI, API, schema, or shipped-bot (`selectBotMove`) change").

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python 3.13 stdlib (`math`, `json`, `argparse`, `dataclasses`, `typing`) | bundled | fit, offset math, inversion, JSON/TS emission | Matches `calibration_anchor_fit.py`'s own D-07 "no numpy/scipy" convention (verified: `pyproject.toml` has no scipy/numpy in `[project.dependencies]`; only the isolated `maia-inference` group pulls numpy, unrelated to this script) `[VERIFIED: pyproject.toml]` |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pytest (already a dev dep) | ≥8.0.0 | unit tests for the new gen script | `tests/scripts/test_gen_bot_strength_curves.py`, mirroring `tests/scripts/test_calibration_anchor_fit.py`'s existing style |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Hand-rolled PAVA (stdlib) | `scipy.optimize.isotonic_regression` (scipy ≥1.15) | Scipy is not a project dependency anywhere in `app/` or `scripts/`; adding it for one ~25-line algorithm would violate the established stdlib-only convention for this tooling family and add an unused-elsewhere dependency. Not recommended. |
| Hand-rolled PAVA | `sklearn.isotonic.IsotonicRegression` | Same objection, heavier dependency, and sklearn is not used anywhere in the repo. Not recommended. |

**Installation:** none — no new packages.

**Version verification:** N/A — no external packages are introduced by this phase. Package
Legitimacy Gate is skipped per its own scope note ("required whenever this phase installs
external packages" — it does not).

## Package Legitimacy Audit

**Skipped.** This phase installs zero external packages (Python stdlib only, matching the
established `calibration_anchor_fit.py` convention). Nothing to verify against a registry.

## Architecture Patterns

### System Architecture Diagram

```
reports/data/bot-curves-internal-scale.json   (Phase 180 output — FROZEN input)
        │  (per-cell rating_vs_maia / rating_vs_sf / g_preset / beyond_ladder,
        │   per_preset[blend].g_preset_combined)
        ▼
scripts/gen_bot_strength_curves.py
        │
        ├─ 1. group cells by bot_blend (preset) ─────────────────────┐
        │                                                            │
        ├─ 2. PAVA isotonic fit over rating_vs_maia, sorted by       │
        │     bot_elo, per preset  ──►  fitted_internal(bot_elo)     │
        │                                                            │
        ├─ 3. offset: approx_blitz(bot_elo) =                        │
        │     fitted_internal(bot_elo) − G_preset_combined + C       │
        │     (C = BLITZ_OFFSET_C = 40, named constant)               │
        │                                                            │
        ├─ 4. invert: for target in range(floor_100, ceil_100, 100): │
        │     bot_elo = lowest bot_elo whose approx_blitz >= target  │
        │     (lowest-wins on flat/plateau segments — D-07)          │
        │                                                            │
        ├─ 5. round range endpoints inward (floor UP, ceiling DOWN   │
        │     to next 100 — D-10)                                    │
        │                                                            │
        └─ 6. write outputs:
              │
              ├──► reports/data/bot-strength-lookup.json
              │     (components: fit points, G_preset, C, band;
              │      derived: target_blitz_elo → bot_elo per preset)
              │
              └──► frontend/src/generated/botStrengthCurves.ts
                    (GENERATED — CI drift-checks against this script's
                     output, same pattern as flawThresholds.ts)

scripts/gen_bot_strength_confirmation_cells.py  (or a 2nd mode of the same script)
        │  picks 2-3 off-grid target_blitz_elo per preset (near each
        │  range endpoint + 1 mid-range), inverts to predicted bot_elo,
        │  computes the interpolated 95% CI band at that bot_elo
        ▼
reports/data/bot-strength-confirmation-predictions.json  (prediction file — D-11)
        │
        │  (HUMAN-UAT, off critical path)
        ▼
operator runs: scripts/calibration-harness.mjs --elo <predicted_bot_elo>
               --blends <blend> --games-per-cell 24-30 --out-dir <cell-dir>
        │
        ▼
scripts/calibration_anchor_fit.py --bot-input <cell-dir>/*-cells.tsv
               --out-bot-curves <cell-dir>/confirmation-fit.json
        │
        ▼
compare measured rating_vs_maia against the prediction file's recorded
95% CI band → PASS/FAIL per D-13; on FAIL, fold the games into the fit
dataset and re-run steps 1-6 (D-14, no hand-tuning)
```

### Recommended Project Structure
```
scripts/
├── gen_bot_strength_curves.py            # NEW — fit + offset + invert + emit JSON/TS
├── calibration_anchor_fit.py             # UNCHANGED — do not extend (D-05)
reports/data/
├── bot-curves-internal-scale.json        # UNCHANGED — frozen Phase-180 input
├── bot-strength-lookup.json              # NEW — this phase's shipped lookup artifact
├── bot-strength-confirmation-predictions.json  # NEW — the D-11 prediction file
frontend/src/generated/
├── botStrengthCurves.ts                  # NEW — generated TS module, CI drift-checked
tests/scripts/
├── test_gen_bot_strength_curves.py       # NEW — unit tests (PAVA, offset math, inversion, rounding)
.github/workflows/ci.yml                  # MODIFY — add a drift-check step (see Code Examples)
frontend/knip.json                        # MODIFY — add botStrengthCurves.ts to `ignore` (D-04)
```

### Pattern 1: `gen_*.py` → committed TS → CI drift check
**What:** A Python script is the single source of truth; it renders a full TS file as a string,
writes it, and supports a `--check` flag that exits 1 if the committed file differs from a fresh
render. CI runs the script unconditionally, then `git diff --exit-code` on the generated path.
**When to use:** Any time a Python-computed constant/table needs a TypeScript mirror with zero
drift risk. This is exactly D-04/D-05's requirement.
**Example (from `scripts/gen_flaw_thresholds_ts.py`, verbatim structure to follow):**
```python
# Source: scripts/gen_flaw_thresholds_ts.py (existing, read in full)
_OUTPUT = _REPO_ROOT / "frontend" / "src" / "generated" / "flawThresholds.ts"

def _render() -> str:
    return (
        "// AUTO-GENERATED — do not edit by hand.\n"
        "// Source: scripts/gen_bot_strength_curves.py\n"
        "// Regenerate with: uv run python scripts/gen_bot_strength_curves.py\n"
        ...
    )

def main() -> None:
    check_mode = "--check" in sys.argv
    content = _render()
    if check_mode:
        if not _OUTPUT.exists() or _OUTPUT.read_text(encoding="utf-8") != content:
            print(f"DRIFT: {_OUTPUT} is out of date. Run ...", file=sys.stderr)
            sys.exit(1)
        print(f"OK: {_OUTPUT} is up to date.")
    else:
        _OUTPUT.write_text(content, encoding="utf-8")
```
CI step to add to `.github/workflows/ci.yml` (mirrors the two existing steps at lines 50-58):
```yaml
      - name: Bot strength curves drift check
        run: |
          uv run python scripts/gen_bot_strength_curves.py
          git diff --exit-code frontend/src/generated/botStrengthCurves.ts \
                                 reports/data/bot-strength-lookup.json
```

### Pattern 2: Hand-rolled PAVA (isotonic regression), stdlib only
**What:** Pool Adjacent Violators Algorithm — given a sequence of `(x, y)` points sorted by `x`,
produces the non-decreasing step function that best fits `y` in a least-squares sense. Scans
left-to-right; whenever the running block average would decrease, it merges ("pools") the
current block with the previous one and re-averages, repeating the merge backward until
monotonicity holds, then continues rightward. O(n) with a simple stack implementation.
`[CITED: web search cross-referencing SciPy/CRAN isotonic-regression documentation and the
maxdan94/pava reference implementation]`
**When to use:** D-07's "monotone (isotonic) fit... over the ~5 measured points" — this is the
textbook algorithm for exactly that requirement, and it is what CONTEXT.md's own
`code_context` section anticipates ("hand-rolled PAVA is ~20 lines").
**Example (stack-of-blocks implementation, ~25 lines, verified by hand against the real Human/
Light/Deep data below):**
```python
from dataclasses import dataclass

@dataclass
class _Block:
    x_lo: float  # smallest bot_elo in this block (for lookup/inversion)
    x_hi: float  # largest bot_elo in this block
    weight: float  # number of points pooled (equal-weight here: 1 per measured cell)
    value: float  # pooled mean internal rating for this block


def isotonic_fit(points: list[tuple[float, float]]) -> list[_Block]:
    """Pool-Adjacent-Violators, ascending. `points` must be pre-sorted by x (bot_elo)."""
    blocks: list[_Block] = []
    for x, y in points:
        block = _Block(x_lo=x, x_hi=x, weight=1.0, value=y)
        blocks.append(block)
        # Merge backward while monotonicity is violated.
        while len(blocks) >= 2 and blocks[-2].value > blocks[-1].value:
            b2 = blocks.pop()
            b1 = blocks.pop()
            total_weight = b1.weight + b2.weight
            merged = _Block(
                x_lo=b1.x_lo,
                x_hi=b2.x_hi,
                weight=total_weight,
                value=(b1.value * b1.weight + b2.value * b2.weight) / total_weight,
            )
            blocks.append(merged)
    return blocks
```
**Hand-verified against the real Phase-180 data** (bot_elo, `rating_vs_maia`), confirming this
produces exactly the plateau/dip corrections CONTEXT.md's `## Specifics` section describes:
- **Light** (blend 0.05): raw `[(1100,1638.9),(1300,1512.8),(1500,1605.0),(1700,1608.3),
  (1900,1783.5)]` → PAVA pools `1100` and `1300` into one block valued `1575.8` (since
  `1638.9 > 1512.8` is a violation), leaving `1500/1700/1900` as their own singleton blocks. The
  fitted curve is flat across `bot_elo` 1100-1300, confirming the CONTEXT.md-flagged
  non-monotonicity is real and handled correctly by PAVA (not an implementation bug to "fix"
  with a smoothed spline — D-07 explicitly forbids that).
- **Deep** (blend 0.5): raw `[(1100,1783.5),(1500,1966.5),(1900,1992.0),(2300,2118.3),
  (2600,2064.3)]` → PAVA pools `2300` and `2600` into one block valued `2091.3` (since
  `2118.3 > 2064.3`), which becomes Deep's **plateau/ceiling** — exactly the "Deep dips at 2600...
  and plateaus" behavior CONTEXT.md flags, and exactly the mechanism behind D-07's "each preset's
  ceiling is its plateau value."
- **Human** (blend 0.0): raw `[(700,882.2),(1100,1006.2),(1500,1143.0),(1900,1405.0),
  (2300,1474.5)]` is already fully non-decreasing — PAVA is a no-op, every point stays its own
  block.

### Pattern 3: Offset model + lowest-bot_elo-wins inversion (D-01, D-07)
**What:** After PAVA, convert each block's `value` to approximate blitz via
`approx_blitz = value − G_preset_combined + C`; since `G_preset_combined` and `C` are constants
(not functions of `bot_elo`), the resulting `approx_blitz(bot_elo)` step function is monotone
non-decreasing wherever the internal fit is. Inversion for a `target_blitz_elo` then walks the
blocks in ascending `bot_elo` order and returns the **first** block whose `approx_blitz >=
target` — its `x_lo` (smallest `bot_elo` in that block) is the answer. This is what makes a flat
PAVA block map to its *lowest* `bot_elo`, satisfying D-07 literally ("never claim a higher
setting buys strength it doesn't").
**When to use:** Step 3 of `SEED-104-iso-strength-inversion-table.md`'s method.
**Example:**
```python
GRID_STEP = 100  # ELO lookup granularity (D-C "100-ELO steps")

def invert_lookup(blocks: list[_Block], g_preset_combined: float, c: float) -> dict[int, int]:
    """Returns {target_blitz_elo: bot_elo} for every 100-step target inside the fitted range."""
    approx = [(b.x_lo, b.value - g_preset_combined + c) for b in blocks]  # (bot_elo, blitz)
    floor = math.ceil(approx[0][1] / GRID_STEP) * GRID_STEP   # round UP (D-10)
    ceiling = math.floor(approx[-1][1] / GRID_STEP) * GRID_STEP  # round DOWN (D-10)
    lookup: dict[int, int] = {}
    for target in range(floor, ceiling + GRID_STEP, GRID_STEP):
        for bot_elo, blitz in approx:  # ascending bot_elo order — first hit wins (lowest-wins)
            if blitz >= target:
                lookup[target] = bot_elo
                break
    return lookup
```

### Anti-Patterns to Avoid
- **Refitting a smooth curve (spline/polynomial) through the plateaus:** D-07 explicitly forbids
  this — "No smoothed/spline slope invented inside measured plateaus." A polynomial fit would
  invent strength the measured data doesn't show (e.g., implying Deep keeps improving past
  bot_elo 2300, when the data shows it *falling* to 2064 at 2600 before PAVA flattens it).
- **Using `rating_vs_sf` or averaging the two families:** D-01 is explicit — fit on
  `rating_vs_maia` only, subtract the pooled `G_preset_combined`. `rating_vs_maia − g_preset
  (per-cell) == rating_vs_sf` is an *identity* in the data (verified: e.g. Human bot_elo=1500:
  `1143.05 − 6.36 = 1136.69` ≈ `rating_vs_sf 1136.69`), so accidentally starting from
  `rating_vs_sf` and adding `C` alone would silently reintroduce per-cell noise the pooled
  `G_preset_combined` was designed to smooth away.
- **Extending `calibration_anchor_fit.py`:** D-05 requires a clean new script. The existing
  fitter already exports everything this phase needs to *read* (`bot-curves-internal-scale.json`
  as its own defined output schema) — no import/reuse of its internals is needed beyond `json`.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Bradley-Terry / bootstrap CI refit for confirmation cells | A new rating-fit algorithm | `scripts/calibration_anchor_fit.py --bot-input ... --out-bot-curves ...` (existing `--bot-input` mode) | Already handles the fixed-anchor single-parameter MLE fit + bootstrap CI exactly as needed for a confirmation cell; it is a CLI flag away, not new code |
| Confirmation-cell game generation | A new harness | `scripts/calibration-harness.mjs --elo <predicted_bot_elo> --blends <blend>` | Existing two-pass locate/measure scheduler already handles off-grid `bot_elo` values (it does not require the value to be one of the original sweep's 5 grid points) |
| Interpolated CI band at an off-grid `bot_elo` | A new statistical interpolation library | Linear interpolation of the two bracketing measured cells' `ci_vs_maia` bounds (see Open Questions — this is new logic this phase must write, but it is arithmetic, not a library problem) | No existing helper does this; it is simple enough to hand-write and unit-test directly |

**Key insight:** every piece of statistical machinery this phase needs (rating fit, bootstrap CI,
harness scheduling) already exists from Phase 173/180. The only genuinely new algorithm is PAVA,
which is intentionally simple by design (isotonic regression is the standard, minimal tool for
"monotone fit over few points" — reaching for scipy here would be over-engineering for a
25-line algorithm the project's own convention already rejects).

## Common Pitfalls

### Pitfall 1: Confusing `beyond_ladder`'s meaning
**What goes wrong:** Assuming `beyond_ladder=true` on the Human bot_elo=1100 cell means
`bot_elo=1100` is outside Maia-3's validated policy-conditioning range (1100-2000,
`maiaEncoding.ts`), and therefore treating the whole cell as untrustworthy or excluding it.
**Why it happens:** The names are easy to conflate — "ladder" appears in both `MAIA_ELO_LADDER`
(the Maia-3 policy input range) and the internal-scale anchor ladder (`maia700...sf10`, fixed
at Phase 173).
**How to avoid:** `beyond_ladder` is set in `scripts/lib/calibration-bot-cell-schedule.mjs`'s
`bracketBeyondLadder()`: true when the cell's *measured internal rating* (not its `bot_elo`
label) falls outside the internal-scale anchor ladder's range (`sf0=1069.33` floor,
`sf10=1907.93` ceiling, from `calibration-internal-scale.mjs`). Human bot_elo=1100's `rating_vs_
maia=1006.2` is below `sf0=1069.33` (the lowest anchor) — that's the entire mechanism. D-08's
decision (keep these cells, flag as extrapolated) is correct as written; just document the *real*
mechanism (internal-scale floor, not Maia-3 input validity) in the findings note so a future
reader doesn't "fix" the wrong thing.
**Warning signs:** Any explanation of `beyond_ladder` that cites `1100–2000` or
`maiaEncoding.ts` is describing the wrong mechanism.

### Pitfall 2: PAVA tie-breaking on the inversion, not just the fit
**What goes wrong:** Implementing PAVA correctly (producing flat blocks) but then inverting with
a "closest bot_elo" or "highest bot_elo in the block" search instead of "lowest bot_elo in the
block reaching the target" — silently violating D-07's core promise.
**Why it happens:** Most inversion approaches naturally reach for "closest match" or iterate in
an unspecified order; PAVA's block structure makes "lowest x in the winning block" a
one-line change (`x_lo`) but it's easy to instead store/return the block's midpoint or last `x`.
**How to avoid:** Keep `x_lo` (not `x_hi` or a midpoint) as the per-block inversion answer, and
unit-test it explicitly: build a synthetic 2-point plateau and assert the lookup returns the
lower `bot_elo` for a target inside the plateau.
**Warning signs:** A unit test that only checks "the returned bot_elo achieves the target
strength" without also checking "no lower bot_elo also achieves it" will pass a broken
tie-break silently.

### Pitfall 3: False precision in the "interpolated 95% CI" (D-13)
**What goes wrong:** D-13's pass criterion needs an "interpolated 95% CI at that bot_elo" for
*any* target `bot_elo` (including off-grid confirmation cells), but the only real CIs in the
input data (`ci_vs_maia`) exist at the 5 *measured* grid points per preset. Inventing a
narrow/precise-looking CI at an interpolated point risks a confirmation cell "failing" for
noise reasons, or "passing" spuriously.
**Why it happens:** No existing code in the repo computes an interpolated CI — this is new
logic (see Open Questions below) and the natural instinct is to linearly interpolate the CI
*width* the same way the point estimate is interpolated, which understates uncertainty inside a
PAVA-merged block (where the true uncertainty is the pooled block's, not a naive lerp of the
original un-pooled cells' CIs).
**How to avoid:** For an interpolated `bot_elo` that falls **inside a PAVA block** (a plateau),
use the **widest** of the two/more merged cells' CI bounds (not their average) — the pooled
block value is less certain than either input point alone. For a point that falls **between two
distinct blocks** (not merged), linearly interpolate the CI bounds between the two neighboring
blocks' own bounds, consistent with the point-estimate interpolation. Document the exact
mechanism used in the gen script's docstring since D-13's pass/fail is only as trustworthy as
this rule is honest.
**Warning signs:** A confirmation cell passing/failing right at the boundary with no
documented CI-interpolation rule to audit against.

### Pitfall 4: Regenerating from a stale or hand-edited `bot-curves-internal-scale.json`
**What goes wrong:** D-08 requires the Human `beyond_ladder` cells stay IN the fit; if a future
maintainer treats `beyond_ladder=true` as "exclude this row" (a reasonable-sounding but wrong
instinct), the Human floor silently rises from ~900 to ~1100+ approx-blitz, contradicting the
seed's explicit product goal ("the product wants genuinely weak bots").
**Why it happens:** `beyond_ladder` reads as a data-quality flag in isolation; only CONTEXT.md's
D-08 states the opposite intent.
**How to avoid:** Assert in the gen script (and cover in a unit test) that all 15 cells from the
input JSON are consumed by the fit — none silently dropped on `beyond_ladder`. Only the
*extrapolated* flag/annotation propagates into the output artifact.
**Warning signs:** Output lookup JSON has fewer than 5 fit points per preset, or the Human
floor rounds to something noticeably above 900.

### Pitfall 5: Frontend build breaking on the un-consumed generated module
**What goes wrong:** knip (run in CI per CLAUDE.md) flags `botStrengthCurves.ts` as dead code
since D-04 explicitly says "no consumer imports it yet," failing CI.
**Why it happens:** `frontend/knip.json`'s `ignore` array already has exactly this precedent
(`src/generated/endgameZones.ts`) but it's easy to forget the new file needs the same entry —
note `flawThresholds.ts` is NOT in that list because it already has a real consumer
(`tagDefinitions.ts`), which `botStrengthCurves.ts` will not have this phase.
**How to avoid:** Add `"src/generated/botStrengthCurves.ts"` to `frontend/knip.json`'s `ignore`
array in the same commit that creates the file, remove it in the future consumer phase.
**Warning signs:** `npm run knip` failing in the pre-merge gate with an unused-export warning
on the new file.

## Code Examples

### Confirmation-cell operator invocation (D-11/D-12)
```bash
# Source: scripts/calibration-harness.mjs usage (existing flags, verified against
# bin/run_bot_curves_sweep.sh's per-preset invocation pattern) + calibration_anchor_fit.py
# --bot-input mode (existing, verified in scripts/calibration_anchor_fit.py)

# One off-grid confirmation cell, e.g. Deep preset, predicted bot_elo=2050 for target 1700 blitz:
node --import ./scripts/lib/frontend-alias-hook.mjs scripts/calibration-harness.mjs \
  --elo 2050 --blends 0.5 --games-per-cell 24 --stockfish-procs 4 \
  --out-dir reports/data/confirmation-deep-2050

# Fit the single cell against the SAME fixed anchor ladder used by the original sweep:
uv run python scripts/calibration_anchor_fit.py \
  --bot-input reports/data/confirmation-deep-2050/*-cells.tsv \
  --out-bot-curves reports/data/confirmation-deep-2050-fit.json
  # --internal-scale-json defaults to reports/data/anchor-ladder-internal-scale.json (unchanged)

# Compare confirmation-deep-2050-fit.json's rating_vs_maia against the band recorded for
# (bot_elo=2050, blend=0.5) in bot-strength-confirmation-predictions.json (D-13 pass criterion).
```

### `--check`-mode drift test (unit test pattern to add)
```python
# Source: mirrors tests/scripts/test_calibration_anchor_fit.py's existing style
def test_gen_bot_strength_curves_is_deterministic(tmp_path: Path) -> None:
    """Running the generator twice on the same frozen input produces byte-identical output —
    the same invariant CI's drift check relies on."""
    first = _render_lookup_json(FROZEN_FIXTURE_PATH)
    second = _render_lookup_json(FROZEN_FIXTURE_PATH)
    assert first == second
```

## State of the Art

Not applicable — no external library/framework is used or upgraded in this phase. The relevant
"state of the art" is entirely internal: Phase 180 (2026-07-21) is the most recent prior work
and its output format is the frozen input this phase builds on.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | The "interpolated 95% CI" rule for D-13 (widest-of-merged-block CI inside a PAVA block; linear interpolation between distinct blocks) is a reasonable, defensible choice but is **new logic with no existing precedent in the codebase** — it is a research recommendation, not a verified/established pattern. | Common Pitfalls (Pitfall 3), Open Questions | If the planner picks a different (e.g. narrower) interpolation rule, some confirmation cells could pass/fail differently under D-13; low product risk (only affects the confirmation gate, not the shipped lookup values), but should be a locked decision the plan writes down explicitly rather than left implicit in code. |
| A2 | Exact final range endpoints (e.g. "Human floor rounds to 900, Deep ceiling rounds to 1800") shown in Pattern 2/3's worked examples are **hand-computed by this research** from the raw JSON for illustration and pitfall-verification purposes — the actual gen script's output is authoritative once written; these numbers should not be hard-coded anywhere as expected values beyond a sanity-check unit test range. | Architecture Patterns (Pattern 2 worked examples) | If hand-arithmetic here has a rounding slip, a unit test that hardcodes "expect 900" instead of testing the *rounding rule* (`ceil`/`floor` to 100) would be brittle; tests should assert the rule, not a specific number, wherever practical. |

**If this table is empty:** N/A — see above; both entries are LOW risk to the shipped product,
MEDIUM risk to test-writing precision.

## Open Questions

1. **Exact interpolated-CI algorithm for D-13's pass criterion (confirmation cells)**
   - What we know: 5 measured points per preset each carry a real bootstrap `ci_vs_maia` (from
     `calibration_anchor_fit.py`'s existing `bootstrap_bot_cell_ci`); PAVA merges some of them
     into blocks; the confirmation targets are deliberately off-grid (D-12), so no existing CI
     exists at the exact `bot_elo` being confirmed.
   - What's unclear: whether to use "widest of merged-block members" vs. "recompute a pooled CI
     via inverse-variance weighting" (the same technique `combine_preset_g_preset` already uses
     for `G_preset_combined`) vs. plain linear interpolation of the CI bounds between neighboring
     points.
   - Recommendation: use the inverse-variance-weighted pooling technique already established in
     `calibration_anchor_fit.py`'s `combine_preset_g_preset` (same file, same phase family) for
     points inside a merged PAVA block — this reuses an already-reviewed pattern instead of
     inventing a new one, and is more principled than "widest of two" while staying simple. For
     genuinely between-block interpolation, linear-interpolate the two blocks' pooled bounds.
     This should become an explicit locked decision at plan time (small enough to decide in
     planning, not worth another discuss-phase round).

2. **Exact confirmation-cell target values (explicitly Claude's Discretion per CONTEXT.md)**
   - What we know: D-12 wants "one target near each range endpoint plus one mid-range, 2-3 per
     preset," off-grid.
   - What's unclear: the literal numbers — this research computed illustrative approximate
     ranges (Human ~900-1400, Light ~1500-1600, Deep ~1600-1800 approx-blitz, all hand-computed
     estimates pending the actual script's precise output) that the planner/gen-script author
     should use as a starting point, but the real gen script's output is authoritative.
   - Recommendation: defer exact values to the gen script's actual computed lookup table (plan
     should have the executor pick concrete targets AFTER running the fit, not hardcode them
     into the plan document).

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.13 + uv | gen script, tests | ✓ | 3.13 (per `pyproject.toml`) | — |
| Node.js (for `calibration-harness.mjs`) | Operator confirmation-cell run (HUMAN-UAT, off critical path) | ✓ (already used throughout Phase 180) | — | — |
| Stockfish WASM / Maia-3 ONNX assets | Operator confirmation-cell run | ✓ (vendored, already used by Phase 180's harness) | — | — |

**Missing dependencies with no fallback:** none.

**Missing dependencies with fallback:** none — everything needed is already present and
exercised by Phase 180's shipped machinery.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest ≥8.0.0 (existing project dependency) |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` (existing, no phase-specific change needed) |
| Quick run command | `uv run pytest tests/scripts/test_gen_bot_strength_curves.py -x` |
| Full suite command | `uv run pytest -n auto` |

### Phase Requirements → Test Map

No formal `REQUIREMENTS.md` exists for milestone v2.6 (per `.planning/STATE.md`: "No
`/gsd-new-milestone` requirements cycle run — this was a lightweight ROADMAP regroup"). The
phase's own CONTEXT.md decisions (D-01 through D-14) function as the acceptance criteria; the
planner should assign working IDs (e.g. `STRENGTH-01`) at plan time if desired, or reference
`D-XX` directly. Mapped here as `D-XX` for traceability:

| Decision | Behavior | Test Type | Automated Command | File Exists? |
|----------|----------|-----------|-------------------|-------------|
| D-01 | Fit uses `rating_vs_maia` minus pooled `G_preset_combined` (not per-cell G, not `rating_vs_sf`) | unit | `pytest tests/scripts/test_gen_bot_strength_curves.py::test_offset_uses_pooled_g -x` | ❌ Wave 0 |
| D-07 | PAVA produces a non-decreasing fit; inversion returns the LOWEST `bot_elo` in a matching block | unit | `pytest tests/scripts/test_gen_bot_strength_curves.py::test_pava_monotone_and_lowest_wins -x` | ❌ Wave 0 |
| D-08 | All 5 cells per preset (including `beyond_ladder=true` Human cells) are consumed by the fit | unit | `pytest tests/scripts/test_gen_bot_strength_curves.py::test_all_cells_retained -x` | ❌ Wave 0 |
| D-10 | Range floor rounds UP, ceiling rounds DOWN to the nearest 100 | unit | `pytest tests/scripts/test_gen_bot_strength_curves.py::test_range_rounds_inward -x` | ❌ Wave 0 |
| D-02 | Lookup JSON stores components (fit points, `G_preset`, `C`) AND the derived blitz lookup separately | unit | `pytest tests/scripts/test_gen_bot_strength_curves.py::test_json_has_components_and_derived -x` | ❌ Wave 0 |
| D-04/D-05 | Generated TS drift-checks cleanly; script is a new standalone file, `calibration_anchor_fit.py` untouched | integration (CI-equivalent) | `uv run python scripts/gen_bot_strength_curves.py --check` (after a real run) | ❌ Wave 0 |
| D-06 | Disclaimer string exported as a named constant in the generated TS, mirrored in JSON | unit | `pytest tests/scripts/test_gen_bot_strength_curves.py::test_disclaimer_present_both_outputs -x` | ❌ Wave 0 |
| D-11/D-12 | Prediction file has 2-3 off-grid cells per preset, each with a predicted `bot_elo` NOT equal to any of the 5 measured grid points | unit | `pytest tests/scripts/test_gen_bot_strength_curves.py::test_confirmation_cells_off_grid -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/scripts/test_gen_bot_strength_curves.py -x`
- **Per wave merge:** `uv run pytest -n auto`
- **Phase gate:** Full suite green before `/gsd-verify-work`. The operator confirmation run
  (D-11) is explicitly HUMAN-UAT and out of the automated gate, per the D-01/split-delivery
  precedent from Phase 180.

### Wave 0 Gaps
- [ ] `tests/scripts/test_gen_bot_strength_curves.py` — covers D-01, D-02, D-04/D-05, D-06, D-07,
      D-08, D-10, D-11/D-12 (new file, no existing test to extend)
- [ ] `scripts/gen_bot_strength_curves.py` — the script itself does not exist yet
- [ ] `frontend/knip.json` `ignore` entry for `src/generated/botStrengthCurves.ts` (D-04) — must
      land in the same commit as the new generated file, not a follow-up
- [ ] `.github/workflows/ci.yml` drift-check step for the new gen script — CI currently only
      checks `endgameZones.ts` and `flawThresholds.ts`; a silent-drift gap exists until this is
      added

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | No auth surface — offline CLI tooling, no network, no user session |
| V3 Session Management | no | N/A |
| V4 Access Control | no | N/A |
| V5 Input Validation | yes (minimal) | Fail-loud on malformed/missing keys when reading `bot-curves-internal-scale.json` (mirror `calibration_anchor_fit.py`'s existing `ValueError`/`RuntimeError` fail-loud pattern — e.g. `load_fixed_ratings`'s check for a non-empty `internal_rating` object) |
| V6 Cryptography | no | N/A — no secrets, no crypto |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Silent malformed-input tolerance (e.g. a truncated/edited `bot-curves-internal-scale.json` producing a plausible-looking but wrong lookup) | Tampering | Fail loud with an explicit exception on any missing/malformed required field, exactly as `calibration_anchor_fit.py`'s existing `fit_bot_cell_rating`/`load_fixed_ratings` already do — never coerce to a default or NaN |
| Generated TS silently diverging from its Python source over time | Tampering (of the artifact, not an attacker) | CI drift check (`--check` mode + `git diff --exit-code`), same as the two existing `gen_*.py` scripts |

This phase's threat surface is effectively nil (no network input, no user data, no auth,
build-time-only artifact) — the two rows above are the only ones worth stating, included for
completeness per the protocol rather than because there is meaningful residual risk.

## Sources

### Primary (HIGH confidence)
- `reports/data/bot-curves-internal-scale.json` — read in full; the actual measured Phase-180
  data this phase consumes `[VERIFIED: file read]`
- `scripts/calibration_anchor_fit.py` — read in full; existing fit/CI/pooling machinery and
  established stdlib-only convention `[VERIFIED: file read]`
- `scripts/lib/calibration-bot-cell-schedule.mjs` — read in full; resolves D-08's
  `beyond_ladder` open question definitively `[VERIFIED: file read]`
- `scripts/lib/calibration-internal-scale.mjs` — read in full; the 10 fixed anchor ratings
  (`sf0=1069.33` is the ladder floor) `[VERIFIED: file read]`
- `scripts/gen_flaw_thresholds_ts.py`, `scripts/gen_endgame_zones_ts.py` — read in full; the
  `gen_*.py` pattern this phase's new script must follow `[VERIFIED: file read]`
- `.github/workflows/ci.yml` — read; existing drift-check step pattern to extend
  `[VERIFIED: file read]`
- `frontend/knip.json` — read; existing `ignore`-list exception pattern (`endgameZones.ts`)
  `[VERIFIED: file read]`
- `frontend/src/lib/maiaEncoding.ts` — read; confirms the Maia-3 validated ELO band (1100-2000)
  is a distinct concept from the internal-scale anchor ladder `[VERIFIED: file read]`
- `pyproject.toml` — read; confirms no scipy/numpy in base dependencies `[VERIFIED: file read]`
- `.planning/seeds/SEED-104-iso-strength-inversion-table.md` — read in full; the authoritative
  phase spec `[VERIFIED: file read]`
- `.planning/phases/180-three-preset-bot-strength-curves/180-CONTEXT.md`,
  `180-04-SUMMARY.md` — read; upstream decisions and pilot findings `[VERIFIED: file read]`
- `tests/scripts/test_calibration_anchor_fit.py` — read (function names); existing test-style
  precedent to mirror `[VERIFIED: file read]`

### Secondary (MEDIUM confidence)
- Web search cross-referencing SciPy's `isotonic_regression` docs, CRAN `isotone` package
  vignette, and the `maxdan94/pava` reference implementation for the standard PAVA algorithm
  description `[CITED: web search, multiple corroborating sources]`

### Tertiary (LOW confidence)
- None.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — zero new dependencies, entire toolchain already verified in the repo
- Architecture: HIGH — the `gen_*.py` pattern is read in full from two existing examples; the
  offset/inversion math is hand-verified against the real Phase-180 data
- Pitfalls: HIGH — five of five pitfalls are grounded in a specific, cited code read (not
  speculation), including the `beyond_ladder` mechanism resolution CONTEXT.md explicitly asked
  the researcher to verify

**Research date:** 2026-07-21
**Valid until:** Stable — no external library versions or moving targets involved. Re-verify
only if `bot-curves-internal-scale.json` is regenerated with different measured values (would
change the illustrative numbers in Pattern 2/3, not the methodology).
