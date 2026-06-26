---
phase: 125-backfill-tactic-motifs
plan: 02
subsystem: database
tags: [backfill, tactic-motif, game_flaws, idempotency, postgres]

# Dependency graph
requires:
  - phase: 125-01
    provides: scripts/coverage_report_tactic_motifs.py (D-04 read-only coverage report) + tactic-column test
  - phase: 124
    provides: tactic detector + game_flaws.tactic_motif/tactic_piece/tactic_confidence columns
provides:
  - Dev DB game_flaws.tactic_motif/tactic_piece/tactic_confidence populated on all full-eval'd games
  - Observed dev numbers (overall %, by-motif table, NULL split, run time) feeding the Plan 03 prod runbook
  - Idempotency proof (empty re-run diff) and D-06 blast-radius proof (empty before/after diff)
affects: [125-03 prod runbook]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "psql \\copy CSV snapshot + diff as an idempotency / blast-radius proof harness"

key-files:
  created:
    - .planning/phases/125-backfill-tactic-motifs/125-02-SUMMARY.md
  modified: []

key-decisions:
  - "Ran the full dev backfill (no --limit) — completed in ~3 min, 0 errors"
  - "Idempotency demonstrated on user 33 (369 full-eval'd flaw rows, 275 tagged) — re-run diff byte-empty"
  - "D-06 blast-radius proven on a fixed 50-game >9-position sample (368 rows) — before/after diff byte-empty"

patterns-established:
  - "Snapshot non-tactic columns to CSV before mutation, re-snapshot after, diff for byte-identity proof"

requirements-completed: [TACSCH-03]

# Metrics
duration: ~10min
completed: 2026-06-18
status: complete
---

# Phase 125 / Plan 02: Dev Tactic-Motif Backfill Summary

**The dev DB tactic-motif backfill ran clean (11,199 games, 0 errors, 68,165 flaw rows); coverage is provably honest (NULL = no-PV or low-confidence, not skipped), the recompute is idempotent (empty re-run diff), and no non-tactic column drifted (empty D-06 diff).**

## Performance

- **Duration:** ~10 min (incl. snapshots, coverage report, idempotency + D-06 diffs)
- **Backfill wall-clock:** ~3 min (started 03:09:34, completed 03:12:52)
- **Tasks:** 2/2
- **DB rows mutated:** game_flaws recomputed for 11,199 full-eval'd games (delete-then-insert per game)

> NOTE: executed INLINE by the orchestrator (not a gsd-executor subagent) due to the documented
> SSE stream-idle timeout failure mode on long DB-heavy plans. The full backfill ran in the
> background (block-buffered output) to avoid the 10-min Bash cap.

## Task 1 — Before-snapshot, smoke, full run (D-02, D-06)

### Pre-backfill ground truth (dev)
```
full_evald_games | mb_flaws | tagged
11199            | 68150    | 0
```

### Step 0 — D-06 before-snapshot
- Fixed deterministic sample: **first 50 full-eval'd games with >9 positions that already had flaw rows** (excludes the ~126 short games that may legitimately gain rows per the 831bae38 coverage fix).
- **Sample game-id list (fixed, reproducible):**
  `157949,158324,158325,158326,158330,158341,158342,158344,158372,158373,158375,158387,158395,158432,158654,158659,158666,158670,158681,158734,160997,161018,161032,161063,161125,163294,163441,163447,163553,163557,163617,163622,163637,163643,163746,164661,165060,165156,166090,166091,166092,166094,166095,166096,166098,166099,166101,166104,166106,166107`
- Snapshot: `/tmp/flaws_before.csv` — columns `user_id,game_id,ply,severity,tempo,phase,is_miss,is_lucky,is_reversed,is_squandered,fen` (NO tactic columns), **368 rows**. Header grep confirmed no `tactic` column present.

### Step 1 — dry-run smoke (D-02)
```
uv run python scripts/backfill_flaws.py --db dev --full-evald-only --dry-run --limit 20
  Games to process: 20
  Batch 1/1: 20 games, 155 flaw rows (dry-run)
  Games processed: 20 | skipped: 0 | Errors: 0 | Flaw rows counted: 155
```
Non-zero flaw count, wrote nothing, exit 0.

### Step 2 — full run (D-03 let-it-rip)
```
uv run python scripts/backfill_flaws.py --db dev --full-evald-only
  Batch size: 100 games per commit
  Scope: full-eval'd games only (full_evals_completed_at IS NOT NULL)
  Games to process: 11199
  ... 112 batches ...
  Backfill complete:
    Games processed: 11199
    Games skipped (no analysis): 24
    Errors: 0
    Flaw rows written: 68165
```
+15 rows vs the 68,150 pre-backfill baseline — all land in the no-PV bucket (no_pv_null 55,234 → 55,249), consistent with short-game rows from the 831bae38 coverage fix (Pitfall 2). The >9-position D-06 sample shows zero drift (below), confirming existing rows on normal games are untouched.

## Task 2 — Coverage report (SC#1/D-04), idempotency (SC#3/D-05), D-06 after-diff

### Step 1 — coverage report (`coverage_report_tactic_motifs.py --db dev`)
```
Overall:
  Total M+B flaw rows:          68,165
  Flaws with PV at ply+1:       12,916  (18.9%)  <- tactic-detectable
  Flaws without PV:             55,249  (81.1%)  <- genuinely undetectable
After Backfill:
  Non-NULL tactic_motif:         9,613  (74.4% of has-PV rows)
  PV present, no fire:           3,303  (honest low-confidence no-fires)

By-motif (non-NULL): fork 2,997 | discovered-attack 1,903 | pin 1,884 | skewer 1,439 |
  clearance 468 | hanging-piece 301 | back-rank-mate 289 | mate 182 | deflection 64 |
  anastasia-mate 22 | dovetail-mate 18 | attraction 14 | intermezzo 12 | x-ray 10 |
  capturing-defender 7 | hook-mate 2 | interference 1 [query-suppressed]
  (arabian-mate, boden-mate, double-bishop-mate, double-check, sacrifice,
   self-interference, smothered-mate = 0 [query-suppressed, did not fire])

NULL split: no_pv_null = 55,249 | pv_no_fire = 3,303
```

**SC#1 interpretation (honest coverage):**
- (a) tagged non-NULL count > 0: **9,613** ✓
- (b) by-motif table lists fired detectors; all 8 query-suppressed motifs are visibly present-or-absent (NOT filtered out — Phase 125 stores all motifs) ✓
- (c) `no_pv_null` = 55,249 matches the pre-backfill no-PV count (~55,234) within expected +15 drift; `pv_no_fire` = 3,303 is the only PV-present-but-NULL bucket ✓
- (d) spot-check samples sane (no_pv_null rows confirm `pv IS NULL`; pv_no_fire rows show short PVs like `'b1c3'`, `'d4d5'` where no detector should fire) ✓
- A **low overall non-NULL %** (9,613 / 68,165 ≈ 14%) is EXPECTED, not a failure: only ~19% of M+B flaws have a PV at ply+1 on dev (Pitfall 1). The bar is "NULL = honest no-fire / no-PV, not skipped", NOT a coverage threshold.

### Step 2 — idempotency (SC#3/D-05)
- User 33 (51 full-eval'd games; 805 total flaw rows, 369 on full-eval'd games, 275 tagged).
- Snapshot all columns (incl. tactic) → `/tmp/flaws_idem_a.csv` (805 rows).
- Re-run `backfill_flaws.py --db dev --full-evald-only --user-id 33` → 51 games, 369 flaw rows, 0 errors.
- Snapshot again → `/tmp/flaws_idem_b.csv` (805 rows).
- **`diff /tmp/flaws_idem_a.csv /tmp/flaws_idem_b.csv` → EMPTY** ✓ (delete-then-insert produces byte-identical rows; non-full-eval'd rows untouched).

### Step 3 — D-06 after-diff
- Re-snapshotted the SAME fixed 50-game sample → `/tmp/flaws_after.csv` (368 rows, identical SELECT/ORDER BY).
- **`diff /tmp/flaws_before.csv /tmp/flaws_after.csv` → EMPTY** ✓ (non-tactic columns byte-identical).
- Combined verify chain printed **`ALL_DIFFS_EMPTY`**.

## Success Criteria (Plan 02)

- ✅ SC#1 — coverage honest (report + NULL split; NULL = no-PV or low-confidence, not skipped)
- ✅ SC#2 — lichess-eval-only games untouched (auto-handled by `--full-evald-only`)
- ✅ SC#3 — idempotency demonstrated (empty re-run diff, not just asserted)
- ✅ D-02 — dry-run smoke + full run, 0 errors
- ✅ D-06 — no non-tactic-column drift (empty before/after diff on >9-position sample)
- ✅ D-01 — phase completes on dev; prod is a deferred step (Plan 03 runbook)

## Notes for Plan 03 (prod runbook)

- Dev run-time: ~3 min for 11,199 games → prod ~131k games extrapolates to roughly ~35 min (state as estimate).
- No-PV ratio: **81.1%** on dev (use as the prod expectation).
- By-motif shape: fork / discovered-attack / pin / skewer dominate; mate-family + rarer motifs in the long tail.
- Batch size 100 (BACKFILL_GAMES_PER_BATCH); let-it-rip posture (pure CPU, no Stockfish) confirmed safe on dev.
