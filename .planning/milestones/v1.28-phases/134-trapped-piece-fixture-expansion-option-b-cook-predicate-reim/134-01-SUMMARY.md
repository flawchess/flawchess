---
phase: 134-trapped-piece-fixture-expansion-option-b-cook-predicate-reim
plan: 01
subsystem: testing
tags: [tactic-tagger, lichess-puzzles, cc0-fixtures, precision-floors, stratified-sampling, python-chess]

# Dependency graph
requires:
  - phase: 127-tagger-validation-harness
    provides: select_tagger_fixtures.py stratified selector + committed train/test fixtures
  - phase: 133-close-suppressed-tactic-gaps
    provides: current PRECISION_FLOOR table + SUPPRESSED_MOTIFS baseline
provides:
  - "--oversample-motifs per-motif cap (Option B / D-EXP-02) on the fixture selector"
  - "Deterministic per-motif RNG re-seed (SHA-1, not salted hash()) — reproducible + isolated"
  - "Expanded trapped-piece ground truth: 28/11 -> 748/317 (~1065 combined) for Plan 02/03"
  - "Re-measured precision floors after full fixture regen (pin/intermezzo/hanging-piece lowered)"
affects: [134-02-cook-predicate-reimplementation, 134-03-conditional-unsuppress]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Per-motif oversample cap with deterministic per-motif re-seed for isolated fixture growth"
    - "Deterministic SHA-1 seed derivation (mirrors _is_test_puzzle) instead of salted builtin hash()"

key-files:
  created:
    - tests/scripts/test_select_tagger_fixtures.py
  modified:
    - scripts/select_tagger_fixtures.py
    - fixtures/tagger/detector_fixture_train.csv
    - fixtures/tagger/detector_fixture_test.csv
    - tests/scripts/tagger/precision_floors.py
    - reports/tactic-tagger/tactic-tagger-2026-06-23.md

key-decisions:
  - "D-EXP-02 byte-identity-vs-HEAD gate OVERRIDDEN: fresh 2026-06 dump shares 0 row-level identity with the older-dump committed fixtures, so byte-identity is unattainable for any re-sample. User approved Option 1 (full regen + re-measure all moved floors)."
  - "trapped-piece cap = 250/stratum (not the plan's literal :1000, which 4x-overshoots the ~1000-combined target across 4 rating bands)."
  - "Fixed a Task 1 bug: builtin hash() of a str-containing tuple is salted per-process; replaced with deterministic SHA-1 so fixtures are reproducible and isolation holds run-to-run."

patterns-established:
  - "Per-motif oversample: raise one motif's per-stratum cap while a per-motif deterministic re-seed keeps every non-co-occurring motif's draw byte-identical between two runs of the selector."
  - "Floor re-measure is lower-only: when a larger/fresher fixture drops a motif's TRAIN precision below its floor, lower the floor ~5-8pp below the new measured TRAIN; never raise."

requirements-completed: []

# Metrics
duration: ~110min
completed: 2026-06-23
status: complete
---

# Phase 134 Plan 01: Trapped-Piece Fixture Expansion (Option B) Summary

**Added a per-motif `--oversample-motifs` cap (with a deterministic per-motif RNG re-seed) to the tagger fixture selector, regenerated the committed CC0 fixtures from the fresh 2026-06 lichess dump so trapped-piece grew from 39 to ~1065 combined ground-truth labels, and re-measured the precision floors the larger fixture moved (pin/intermezzo/hanging-piece lowered, gate green).**

## Performance

- **Duration:** ~110 min (spanning a blocking human-action checkpoint for the ~287MB lichess dump download + a Rule-4 architectural checkpoint)
- **Completed:** 2026-06-23
- **Tasks:** 2 (Task 1 autonomous; Task 2 after a blocking download checkpoint + an architectural decision checkpoint)
- **Files modified:** 5 (1 created, 4 modified)

## Accomplishments

- `--oversample-motifs motif:N` CLI arg on `select_tagger_fixtures.py` implementing D-EXP-02 Option B (per-motif cap; default behavior byte-identical when unused).
- Deterministic per-motif RNG re-seed via SHA-1 (`_per_motif_seed`) — makes the sample reproducible across processes AND makes Option-B isolation exact for non-co-occurring motifs (empirically: 0-line non-trapped diff between a default run and a `trapped-piece:250` run on the same dump).
- New unit test `test_select_tagger_fixtures.py` (2 tests) proving the cap raises the target motif's count while a control motif's selected PuzzleIds stay identical.
- trapped-piece ground truth expanded **28/11 -> 748/317 (39 -> 1065 combined)** in the committed fixtures, plus soft top-ups for the thin move-type motifs.
- Full-sweep floor re-measure after the regen: 3 floors lowered, the rest untouched; CI gate `test_detector_precision.py` GREEN.

## Task Commits

1. **Task 1: --oversample-motifs cap + per-motif re-seed + unit test** - `82e5f412` (feat)
2. **Task 1 bug fix: deterministic per-motif seed (salted hash() -> SHA-1)** - `76c8b848` (fix, Rule 1)
3. **Task 2a: regenerate fixtures from 2026-06 dump** - `4917dbf4` (feat)
4. **Task 2b: re-measure moved floors (lower-only) + report** - `fc7671d5` (test)

**Plan metadata:** _(this SUMMARY + STATE/ROADMAP commit follows)_

## Oversample Run Details (plan `<output>` requirements)

### Achievable pool size per oversampled motif (sizing run, per (motif, rating-band) lt1200/lt1600/lt2000/gt2000)

| Motif | lt1200 | lt1600 | lt2000 | gt2000 | total available | reaches 1000/stratum? |
|-------|-------:|-------:|-------:|-------:|----------------:|-----------------------|
| trapped-piece | 4164 | 22948 | 25616 | 13866 | ~66,594 | yes (huge headroom) |
| en-passant | 38 | 748 | 3171 | 4567 | ~8,524 | partial (2 bands < 1000) |
| promotion | 46773 | 35649 | 29481 | 33333 | ~145,236 | yes (huge headroom) |
| under-promotion | 150 | 123 | 188 | 651 | ~1,112 | no — intrinsically rare (all bands < 1000) |

### Final caps chosen (`--seed 42`)

`trapped-piece:250  en-passant:1000  under-promotion:1000  promotion:1000`

- trapped-piece:250/stratum × 4 bands → **748 train / 317 test = 1065 combined** (hits the binding ~700/~300/~1000 target; the plan's literal `:1000` would 4× overshoot).
- move-type motifs at `min(1000, pool)` per stratum (the rare ones take their full pool; soft-target framing).

### Row-count deltas

| Fixture | old total | new total |
|---------|----------:|----------:|
| train | 11,855 | 18,632 |
| test | 5,164 | 8,017 |

trappedPiece: **train 28 → 748, test 11 → 317** (combined 39 → 1065).

### Isolation diff result

**Byte-identity-vs-HEAD diff was NOT run** — it is unattainable and was explicitly overridden (see Deviations). Empirical proof the diff is meaningless against HEAD: re-running the original pre-Task-1 scheme (global seed 42, no oversample) against the new dump reproduced **0 of HEAD's 11,828 non-trapped train rows** (intersection = 0), confirming the committed fixtures came from an older, smaller dump.

**Internal isolation (the Option-B mechanism) WAS proven:** with the fixed deterministic re-seed, a default-cap run vs a `trapped-piece:250` run on the same dump produced a **0-line diff in non-trapped train rows** while trapped-piece grew 598 → 739. The mechanism works exactly as D-EXP-02 intends — it is only the cross-dump comparison that cannot hold.

## Floors Re-Measured (full-regen sweep, lower-only)

Every shipped motif was re-scored against the regenerated fixture. Three fell below their floor and were lowered ~5-8pp below the new measured TRAIN; all others still pass and were left untouched. **No floor was raised. No detector geometry was changed** (Plan 02 owns that).

| Motif | floor old→new | n(train) old→new | P(train) old→new | TP/FP (new) | P(test) new |
|-------|---------------|------------------|------------------|-------------|-------------|
| pin | 0.90 → 0.85 | 1203 → 1499 | 0.936 → 0.899 | 936 / 105 | 0.916 |
| intermezzo | 0.85 → 0.70 | 702 → 751 | 0.938 → 0.759 | 22 / 7 | 0.750 |
| hanging-piece | 0.90 → 0.68 | 734 → 857 | 0.915 → 0.743 | 625 / 216 | 0.732 |

**Floors left unchanged (still pass on the new fixture):** fork (0.997), skewer (1.000), discovered-attack (0.993), double-check (1.000), discovered-check (0.964), mate (1.000), smothered-mate (1.000), back-rank-mate (1.000), anastasia-mate (1.000), hook-mate (1.000), deflection (0.961), clearance (0.961), interference (0.969), capturing-defender (0.882), x-ray (1.000), promotion (1.000), attraction (1.000), sacrifice (1.000), arabian-mate (1.000), boden-mate (1.000), dovetail-mate (1.000).

**trapped-piece:** measured P(train)=0.249 (75 TP, 226 FP) on the expanded fixture — far below ship bar. **Remains in SUPPRESSED_MOTIFS with NO PRECISION_FLOOR** (detector rewrite = Plan 02, conditional unsuppress = Plan 03). Measurement note in `precision_floors.py` refreshed to the new ~1065-row fixture.

## Decisions Made

- **trapped-piece cap = 250/stratum** (not `:1000`): with 4 rating bands, `:1000` produces ~4000 rows — 4× the repeatedly-asserted ~1000-combined target. `:250` lands at 1065 combined.
- **Floor re-measure granularity:** pin/intermezzo → rounded to 0.05; hanging-piece → 0.68 (within the 0.01-0.05 band, matching the motif's existing 0.01-style neighbors). All set ~5-8pp below the new TRAIN, with each held-out TEST value confirmed above the new floor (no overfit).

## Deviations from Plan

### Approved architectural deviation (Rule 4 → user decision)

**1. [Rule 4 - Architectural] D-EXP-02 byte-identity-vs-HEAD gate overridden; full regen + full floor re-measure**
- **Found during:** Task 2 (isolation verification step)
- **Issue:** The plan's mandatory D-EXP-02 gate (must_have truths #4 byte-identity-vs-HEAD and #5 only-moved-floors) is **unattainable**. The committed fixtures were generated from an older, smaller lichess dump; the fresh 2026-06 dump (the plan itself instructed downloading a fresh dump) shares **zero row-level identity** (0/11,828 non-trapped rows survive even under the identical original scheme). Byte-identity for unchanged motifs is therefore impossible for any re-sample, regardless of seeding scheme.
- **Resolution:** Surfaced as a Rule-4 architectural checkpoint. User chose **Option 1**: full regenerate from the new dump + re-measure ALL moved floors, accepting the wider blast radius. This OVERRIDES must_have truths #4 and #5.
- **Impact:** 3 floors re-measured instead of "only multi-label leakage"; the Option-B *mechanism* is still validated (internal isolation proven). No detector change, no floor raised.
- **Committed in:** `4917dbf4` (fixtures), `fc7671d5` (floors)

### Auto-fixed Issues

**2. [Rule 1 - Bug] Per-motif RNG re-seed used salted builtin `hash()`**
- **Found during:** Task 2 (first regeneration attempt produced a fully reshuffled fixture)
- **Issue:** Task 1's `random.seed(hash((seed, motif)))` relied on Python's builtin `hash()` of a tuple containing a `str`, which is **salted per-process** (`PYTHONHASHSEED`). The seed — and thus the entire sampled fixture — was non-reproducible across runs, and the Option-B isolation guarantee was broken (every run drew a different sample).
- **Fix:** Added `_per_motif_seed(seed, motif)` deriving the seed via SHA-1 over `"seed:motif"` folded into a 32-bit int (mirrors the deterministic SHA-1 in `_is_test_puzzle`). Sample is now reproducible and isolation holds run-to-run.
- **Verification:** Unit tests pass; two same-dump runs with different caps produce a 0-line non-trapped diff.
- **Committed in:** `76c8b848`

---

**Total deviations:** 1 approved architectural override + 1 Rule-1 bug fix.
**Impact on plan:** The override was a genuine planning-premise failure (same-dump assumption broken by the fresh-dump instruction), resolved by explicit user decision. The bug fix was necessary for any reproducible/isolated output. No scope creep; no detector geometry touched (deferred to Plan 02); trapped-piece floor deferred to Plan 03.

## Issues Encountered

- **CRLF line endings on regenerated CSVs:** `csv.DictWriter(newline="")` wrote `\r\n` on this system; the original committed fixtures and the harness expect LF. Git auto-normalized the committed blob to LF (warning only), and I re-materialized the working tree from the LF blob so the harness reads the canonical fixture. Row counts unchanged.
- **Full-suite regeneration is slow (~4-5 min/run, ~287MB stream):** background runs were used for the isolation A/B comparison to avoid foreground timeouts.

## Next Phase Readiness

- Plan 02 (cook `is_trapped` detector reimplementation) now has ~1065 trapped-piece ground-truth labels to iterate against (vs the unusable 39 before).
- trapped-piece stays suppressed with no floor — Plan 03 decides the conditional unsuppress (gated on ~≥0.80 TRAIN holding on TEST).
- The lowered pin/intermezzo/hanging-piece floors reflect honest precision on the larger fixture; if Plan 02's detector work or a future tightening lifts them, those floors can be raised in a later measured pass.

## Self-Check: PASSED

All created/modified files exist on disk and all 4 task commits (`82e5f412`, `76c8b848`, `4917dbf4`, `fc7671d5`) are present in git history. Gate `tests/scripts/tagger/test_detector_precision.py` and selector unit test both green; ruff + ty clean on touched files.

---
*Phase: 134-trapped-piece-fixture-expansion-option-b-cook-predicate-reim*
*Completed: 2026-06-23*
