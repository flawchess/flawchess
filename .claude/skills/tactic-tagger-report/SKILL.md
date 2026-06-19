---
name: tactic-tagger-report
description: Generate a FlawChess tactic-tagger precision/recall + difficulty report. Scores the tactic-motif detector (app/services/tactic_detector.py) against the committed CC0 lichess puzzle fixture and writes a timestamped markdown report with a per-tactic table (precision, recall, TP/FP/FN, ground-truth difficulty distribution, mean depth), column explanations, and a summary/interpretation section. Use this skill whenever the user asks about tactic-tag accuracy, tactic detector precision or recall, per-motif precision/recall, how good the tactic tagging is, tactic false-positive rates, motif difficulty distribution, or wants a tactic-tagger health/validation report. Trigger on phrases like "tactic tagger report", "tactic-tagger-report", "tactic precision report", "detector precision/recall", "how accurate are the tactic tags", "per-motif precision", "tactic difficulty distribution", or any request to evaluate the tactic-motif detector against the puzzle fixture. Also covers goal-seeking self-improvement: the same script exposes a `--check-goals` mode (editable per-motif precision/recall GOALS, exits non-zero until met) for driving a `/loop` that automatically improves the detector until targets are reached — trigger on "improve the tagger until", "tactic precision/recall goals", "loop to improve the detector". Writes to reports/tactic-tagger/tactic-tagger-YYYY-MM-DD.md.
---

# Tactic-Tagger Report

Generate a precision/recall + difficulty report for the FlawChess tactic-motif detector
(`app/services/tactic_detector.py::detect_tactic_motif`) scored against the committed CC0
lichess puzzle fixture (`fixtures/tagger/detector_fixture.csv`).

This is **read-only and offline**: no database, no network, no DB tunnel. It reuses the
Phase 127 validation-harness modules (`tests/scripts/tagger/`) as the single source of truth
for the motif→theme map, the unvalidated set, and the precision floors, so the
precision / recall / TP / FP / FN numbers match the CI gate
(`tests/scripts/tagger/test_detector_precision.py`) exactly.

**Train/test split (anti-overfitting):** the fixture is two committed files —
`detector_fixture_train.csv` and `detector_fixture_test.csv` — produced by
`scripts/select_tagger_fixtures.py` with a deterministic PuzzleId-hash split (default
200/stratum, 70/30). TRAIN is the floor-gated optimization set the loop improves; TEST is
held out for honest validation and is never used to tune detectors or set floors. The report
shows train-vs-test precision side by side with a ΔP column — a large train-beats-test gap
means overfitting. To re-sample (more puzzles, different split):
`PYTHONPATH=. uv run python scripts/select_tagger_fixtures.py --puzzle-path <dump.csv.zst>
[--samples-per-stratum N] [--test-fraction 0.30]` (the ~300 MB CC0 dump is not committed;
download from database.lichess.org/#puzzles). After re-sampling, re-baseline the floors in
`tests/scripts/tagger/precision_floors.py` from the new TRAIN measurement (D-09).

## How to run

Run the report generator from the project root:

```bash
PYTHONPATH=. uv run python scripts/tactic_tagger_report.py
```

(`PYTHONPATH=.` is needed because the script imports the harness modules under `tests/`.)

It writes `reports/tactic-tagger/tactic-tagger-YYYY-MM-DD.md` (UTC date) and prints the path.
Re-running on the same day overwrites that day's file. The dev DB does **not** need to be
running — the fixture is a committed CSV.

## What the report contains

1. **Header** — generation timestamp, detector path, fixture path, row count.
2. **Columns** — a legend table explaining every column (T, Prec, Rec, TP/FP/FN, n_gt,
   min/Q1/Q2/Q3/max, TP mean R, TP depth, Status).
3. **Per-tactic table** — one row per validated motif, ordered by dispatch tier
   (1 mates → 2 geometric → 3 fuzzy → 4 hanging-piece), rows within a tier in detector
   priority-rank order. Includes precision, recall, TP/FP/FN, the ground-truth puzzle-Rating
   distribution (min/Q1/Q2/Q3/max where Q2 = median), mean Rating and mean `tactic_depth` of
   correct detections, and shipped/suppressed status.
4. **Overall fixture Rating** line and the **depth-vs-Rating Pearson correlation** (D-06).
5. **Summary & interpretation** — data-driven coverage stats (shipped vs suppressed counts,
   micro-averaged precision, lowest-precision motif, biggest FP source) plus stable design
   notes (stratified-difficulty caveat, depth-tracks-difficulty, why `mate` recall looks low,
   the `pin` weak point tracked in SEED-057).

## Goal-seeking mode (drive a `/loop` to improve the tagger)

The script doubles as the **goal driver** for an automated improvement loop. The
`GOALS` table near the top of `scripts/tactic_tagger_report.py` sets a per-motif
precision and/or recall target (aspirational — distinct from the CI `precision_floors.py`,
which only enforce "never regress"). Edit `GOALS` to set the bar before looping.

```bash
PYTHONPATH=. uv run python scripts/tactic_tagger_report.py --check-goals
```

This writes the report, prints a gap table sorted worst-first, prints a `NEXT:` line
naming the single highest-leverage motif+dimension to fix, and **exits 1 while any goal
is unmet, 0 once all are met**. That exit code is the loop's stop signal. By default it
evaluates the **train** set; pass `--eval-set test` for a final held-out check before
declaring the loop done (improvement that only shows on train is overfitting).

### The loop

Start it with the `/loop` skill in model-self-paced mode (no interval):

```
/loop Improve the tactic-motif detector until goals are met. Each iteration:
1. Run: PYTHONPATH=. uv run python scripts/tactic_tagger_report.py --check-goals
2. If it exits 0, STOP — all goals met.
3. Otherwise read the NEXT line, edit app/services/tactic_detector.py to close that
   gap (precision = cut false positives; recall = fire on more true cases).
4. Re-run the fast guard tests AND the precision harness — both must stay green:
   uv run pytest tests/services/test_tactic_detector.py tests/scripts/tagger/test_detector_precision.py -o addopts=""
   (the harness enforces the never-regress floors on TRAIN; do NOT lower a floor to pass.)
5. Commit the improvement atomically, then loop.
Before declaring done, run a held-out check: --check-goals --eval-set test. If a gain shows
on train but not test, it is overfitting — revert or rethink. If a motif's gap does not
shrink across two iterations, stop and report it as needing a redesign rather than churning.
```

### Guardrails (important)

- **Overfitting risk.** The CC0 fixture is BOTH the optimization target and the only
  validation set here. Tightening detectors to fit it can overfit. Prefer changes that are
  principled (correct chess logic) over fixture-specific special-cases. Re-select a fresh
  fixture with `scripts/select_tagger_fixtures.py` if you need an independent check.
- **Never lower a floor to pass.** `precision_floors.py` floors are the regression guard;
  the loop must IMPROVE the detector, not weaken the gate. Goals go up, floors never down.
- **Unreachable goals.** Some targets may need a detector redesign (the script's `NEXT`
  output warns when a gap is stubborn). Lower the goal in `GOALS` or stop — do not churn.
- **Keep the full suite green** before considering the loop done:
  `uv run pytest -n auto -x`.
- The loop edits real source (`tactic_detector.py`); run it on a branch, not `main`.

## After running

- Confirm the script printed `Wrote …` with the expected path, then present the table and the
  summary/interpretation section inline to the user (the file is the durable artifact).
- If the user asks for a specific subset (e.g. just one tier, or just the worst offenders),
  filter the generated table in your reply — do not modify the script for a one-off view.

## Notes / gotchas

- **Difficulty is sampled, not population.** The fixture is stratified by Rating band per
  motif-theme (`scripts/select_tagger_fixtures.py`), so per-motif difficulty distributions are
  intentionally flat. They are NOT the natural lichess-population difficulty of each tactic; say
  so if the user reads them as population difficulty.
- **`suppressed` motifs** are excluded from the floor gate and query-suppressed via the
  `_TACTIC_CHIP_CONFIDENCE_MIN` lever (they have zero or only-false-positive precision). They
  still appear in the table for completeness.
- The script is the source of the numbers — never hand-transcribe the table from a prior run;
  re-run it so the report reflects the current detector.
- If the detector or fixture changes, the floors in `tests/scripts/tagger/precision_floors.py`
  may need re-setting from the new measurement (D-09); that is a code change, not a report change.
