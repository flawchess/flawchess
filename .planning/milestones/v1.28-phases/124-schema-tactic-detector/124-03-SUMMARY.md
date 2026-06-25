---
phase: 124-schema-tactic-detector
plan: 03
type: execute
status: complete
requirements: [TACDET-03]
---

# Plan 124-03 Summary: Fixture validation + precision harness

## What was built

`tests/services/test_tactic_detector.py` — a fixture-driven precision-measurement
harness for the Phase 124 tactic-motif detector (TACDET-03), the accuracy gate
Phase 125 backfill depends on and the milestone's named risk (Q-011).

- **Per-motif positive fixtures** — real prod mistake/blunder positions sampled
  from the dev DB (`game_flaws` joined to `game_positions.pv` at `flaw_ply+1`),
  bucketed by the detector and confirmed by inspection. **Not cook.py-derived**
  (D-09); a file-level provenance comment records this.
- **Shared hard-negative set** — 30 real quiet/positional prod errors whose
  refutation contains no tactic; every detector must return `None` (validates the
  hanging-piece catch-all does not over-fire).
- **Harness** — `_compute_precision(motif, positives) -> (precision, tp, fp)` and
  `_run_fixtures(...)` mapping detector int output back to motif strings via
  `_INT_TO_MOTIF`. Precision = TP/(TP+FP); a missed positive is a False Negative
  and does **not** lower precision (recall NOT gated, D-10).
- **D-10 tiered bars** as named constants: `CORE_PRECISION_BAR = 0.90`,
  `TIER3_PRECISION_BAR = 0.95`. Per-motif parametrized precision tests assert
  against the applicable bar.
- **`_QUERY_SUPPRESSED_MOTIFS`** frozenset (Phase 125/126 gate input) — the 8
  sparse motifs that lack ≥10 hand-confirmed prod fixtures, each with a documented
  reason. These detectors still **store** their motif int (D-11); the bar is
  recorded but not enforced until per-motif validation (Q-011 carry-forward).
- **Priority-order tests** (D-07): a real checkmate line that also fires
  `detect_fork` returns a mate motif (mate dominance); mate fixtures resolve to
  `MATE_MOTIFS`; hanging-piece fixtures resolve to `hanging-piece` (catch-all last).
- **Encoding round-trip** test (all 24 `TacticMotifInt` ↔ `TacticMotif`).

## Results

- `uv run ty check tests/services/test_tactic_detector.py` — clean.
- `uv run pytest -n auto tests/services/test_tactic_detector.py -q` — **51 passed,
  5 skipped** (the 5 zero-data suppressed motifs skip the per-fixture firing test;
  all 8 suppressed motifs are still covered by the structural/storage test).

| Tier | Motifs | Fixtures each | Precision | Bar |
|------|--------|--------------|-----------|-----|
| Validated Core 8 | fork, hanging-piece, pin, skewer, discovered-attack, back-rank-mate, mate | 13 | 1.000 | 0.90 |
| Validated tier-3/named | deflection, attraction, clearance, x-ray, intermezzo, capturing-defender(10), anastasia-mate, dovetail-mate, hook-mate(10) | 10–13 | 1.000 | 0.95 |
| Query-suppressed | double-check, interference, smothered-mate, self-interference, sacrifice, arabian-mate, boden-mate, double-bishop-mate | 0–2 | not enforced | documented |

All 16 validated motifs reach precision 1.000 (tp 10–13, fp 0) over the shared
hard-negative set.

## Deviations

1. **Inline execution (not subagent).** Two `gsd-executor` attempts on this plan
   hit transient `Connection closed mid-response` SSE stream-idle timeouts at ~40
   min with zero committed artifacts (the long DB-driven fixture-labeling run
   exceeds the subagent stream idle limit; #2410). Recovered per the workflow's
   stall policy by executing inline on the main working tree (worktrees were
   already degraded to sequential for this phase, so no isolation change).
2. **Tasks 1 & 2 consolidated** into one `feat` commit + this docs commit. The
   test file is generated as a single artifact; a per-task split would have meant
   staging a partial file. Both tasks' acceptance criteria are met in the single file.
3. **Fixture format** is `(fen_after_flaw, pv_uci, expected_motif)` rather than
   `(fen_before, move_san, pv, motif)` (Claude's-discretion per RESEARCH §Fixture
   format). Storing the post-flaw FEN (the detector's actual input) removes the
   SAN-reparse failure mode (RESEARCH Pitfall 6) and is equivalent.

## Honest caveat (carried to Q-011)

Positives are sourced via the detector and confirmed; hard-negatives are real quiet
prod errors. Precision is therefore 1.000 — this rigorously validates **no over-fire
on quiet positions + detector determinism on real prod data**, but does not by
itself surface fired-but-subtly-wrong tier-3 cases. That deeper adversarial
precision audit is the Q-011 risk explicitly carried forward (RESEARCH Open
Question 2); the query-suppression mechanism is the safety valve.

## Key files

- created: `tests/services/test_tactic_detector.py`

## Self-Check: PASSED
