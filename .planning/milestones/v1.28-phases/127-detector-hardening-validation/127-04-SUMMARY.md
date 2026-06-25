# 127-04 SUMMARY — Dev Re-Backfill Validation + Prod Runbook

**Plan:** 127-04 (Wave 3) — detector-hardening-validation
**Status:** Task 1 complete; Task 2 = blocking human-verify checkpoint (PENDING APPROVAL)
**Date:** 2026-06-19

## What was done

Re-ran the hardened tactic detector (127-01) over the existing **dev** tagged flaws with the
**unmodified** `scripts/backfill_flaws.py --db dev --full-evald-only` — **no DB reset** (project rule).
The script's delete-then-insert flows the corrected detector + `tactic_depth` write path through
`classify_game_flaws` automatically.

Backfill run: **10,405 games processed, 31 skipped (no analysis), 0 errors, 64,875 flaw rows written**,
105 batches of 100, ~2.5 min wall.

## Before / After (dev `game_flaws`, via `mcp__flawchess-db__query`)

| Metric | Before | After | Δ |
|---|---:|---:|---:|
| total flaws | 73,201 | 73,195 | −6 |
| total tagged (motif non-NULL) | 32,712 | 32,518 | −194 (−0.6%) |
| **non-NULL `tactic_depth`** | **0** | **32,518** | **+32,518 (100% of tagged)** |

### Per-motif counts (before → after)

| int | motif | before | after | Δ | avg depth |
|---:|---|---:|---:|---:|---:|
| 1 | fork | 10,083 | 9,314 | **−769 (−7.6%)** | 2.75 |
| 6 | discovered_attack | 6,305 | 6,362 | +57 | 4.85 |
| 3 | pin | 6,299 | 6,312 | **+13 (~flat)** | 2.81 |
| 4 | skewer | 4,778 | 5,145 | +367 | 5.05 |
| 15 | clearance | 1,614 | 1,546 | −68 | 5.18 |
| 7 | back_rank_mate | 1,366 | 1,372 | +6 | 3.34 |
| 2 | hanging_piece | 1,002 | 1,017 | +15 | 0.00 |
| 8 | mate | 669 | 672 | +3 | 4.85 |
| 9 | deflection | 226 | 317 | +91 | 4.01 |
| 19 | anastasia_mate | 100 | 101 | +1 | 4.59 |
| 10 | attraction | 56 | 90 | +34 | 2.82 |
| 12 | x_ray | 55 | 62 | +7 | 3.55 |
| 24 | dovetail_mate | 49 | 49 | 0 | 6.02 |
| 11 | intermezzo | 46 | 91 | +45 | 7.03 |
| 16 | capturing_defender | 21 | 24 | +3 | 3.92 |
| 20 | hook_mate | 20 | 20 | 0 | 2.90 |
| 18 | smothered_mate | 18 | 18 | 0 | 4.89 |
| 5 | double_check | 3 | 4 | +1 | 2.50 |
| 13 | interference | 2 | 2 | 0 | 4.00 |

## Findings against acceptance criteria

- ✅ **`tactic_depth` populated**: 0 → 32,518 — every tagged row now carries a non-NULL depth.
  Depth values are sensible (hanging_piece always 0 = immediate; forks avg 2.75; deep motifs
  like intermezzo avg 7.03). Untouched non-full-eval'd rows remain honestly NULL (all of them
  are untagged, so NULL depth is correct).
- ✅ **fork dropped**: −769 (−7.6%) — the D-01 relevance gate removed false positives. Did NOT
  collapse the motif (9,314 remain).
- ⚠️ **pin did NOT drop**: +13 (~flat). This deviates from the plan's "fork AND pin dropped"
  criterion, but is **consistent with the 127-03 fixture measurement** (pin precision regressed
  −4.7pp; the pin replacement guard is conservative and prunes few real-data pins). Not a
  regression introduced here — it reflects the same conservative-guard behavior 127-03 documented.
- Other motifs redistribute (skewer +367, deflection +91, intermezzo +45) as the min-depth
  dispatcher re-resolves which motif wins per position. No motif collapsed to zero.

## Artifact

- `127-PROD-REBACKFILL-RUNBOOK.md` — deferred prod re-backfill procedure
  (`scripts/backfill_flaws.py --db prod --full-evald-only` behind `bin/prod_db_tunnel.sh`),
  idempotency + batch-100 notes, expected fork/pin direction, D-13 deferral, drains-auto-pick-up note.
  **Prod re-backfill NOT executed** (deferred per D-13).

## Open item for human verify (Task 2)

The pin-flat result is the one thing to adjudicate: is "fork dropped, pin ~flat, tactic_depth
fully populated, 0 errors" an acceptable phase outcome, given 127-03 already documented pin's
conservative guard and set floors from measurement (D-09)? Counts and depths are recorded above
for review.

## Task 2 — Human-verify checkpoint: APPROVED (2026-06-19)

User approved the dev re-backfill result. Note recorded: *"the real test will be precision
and recall against decent puzzle samples from lichess for each tactic tag."* That test is the
authoritative arbiter and is already built in this phase — Plan 127-02's stratified CC0 lichess
puzzle fixture (`fixtures/tagger/detector_fixture.csv`, 4,368 rows) + Plan 127-03's
`tests/scripts/tagger/test_detector_precision.py`, which prints per-motif precision/recall and
sets blocking floors from the measured numbers (D-09). The dev count deltas above are
corroborating real-data evidence; the fixture harness is the source of truth for per-tag
precision/recall.

## Self-Check: PASSED
- [x] Dev re-backfill ran via unmodified script, no DB reset
- [x] `tactic_depth` non-NULL > 0 (32,518) on re-backfilled tagged rows
- [x] fork count dropped vs baseline; no motif collapsed
- [x] Runbook exists, references `backfill_flaws --db prod`, marks prod deferred (D-13)
- [x] Human-verify checkpoint (Task 2) — APPROVED
