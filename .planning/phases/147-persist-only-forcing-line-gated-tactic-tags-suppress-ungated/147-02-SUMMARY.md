---
phase: 147-persist-only-forcing-line-gated-tactic-tags-suppress-ungated
plan: 02
subsystem: database
tags: [alembic, migration, postgresql, tactic-tagging, forcing-line-gate, data-correctness]

# Dependency graph
requires:
  - phase: 147-01
    provides: "Go-forward blobs_pending suppression at _apply_submit (Part A go-forward threading)"
provides:
  - "Alembic revision eb341e836ee9 suppressing raw ungated cp-based tactic tags on the pre-existing corpus"
  - "tests/test_migration_suppress_ungated_tactic_tags.py locking in every carve-out + idempotency"
affects: [147-03, 147-04, 147-05, 147-06]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Batched Alembic DATA migration: DO $$ ... WHILE rows_updated > 0 LOOP ... GET DIAGNOSTICS, composite-PK WITH batch AS (...) UPDATE ... FROM batch (no id surrogate)"
    - "Per-orientation gating on independent JSONB blob columns joined to a sibling table's PK for the cp-based candidate check"

key-files:
  created:
    - alembic/versions/20260701_190758_eb341e836ee9_suppress_ungated_tactic_tags_old_corpus.py
    - tests/test_migration_suppress_ungated_tactic_tags.py
  modified: []

key-decisions:
  - "Migration predicate joins game_flaws to game_positions on (user_id, game_id, ply=gf.ply-1) since pre_flaw_eval_cp is not a game_flaws column; verified index-driven via the existing ix_game_flaws_blob_backfill partial index (RESEARCH.md EXPLAIN) — no new index created"
  - "Suppression gated per orientation on its OWN blob column (allowed_pv_lines / missed_pv_lines independently), not a combined check, per RESEARCH.md's explicit warning that the NULL-together invariant is empirical, not a DB constraint"
  - "downgrade() is a documented no-op — the raw pre-gate motif is unrecoverable once suppressed (self-heals forward via tier-4's D-07 retag, not via a migration downgrade)"
  - "Batch size 100000 reused from the repo's existing convention (pawnless-reclassify migration), not a new number"

patterns-established:
  - "Migration test mirrors the migration SQL verbatim in a module-level string with an explicit sync comment, per the established test_migration_wipe_eval_only_residue.py template"

requirements-completed: []  # SEED-074 spans all 6 plans in this phase (Part A + Part B); marking deferred to the phase's final plan.

coverage:
  - id: D1
    description: "Batched, index-driven Alembic migration suppresses ungated cp-based tactic tags on the old corpus while preserving mate-adjacent and D-06 [] sentinel rows"
    requirement: "SEED-074"
    verification:
      - kind: integration
        ref: "tests/test_migration_suppress_ungated_tactic_tags.py::test_suppress_carve_outs_and_idempotency"
        status: pass
      - kind: other
        ref: "uv run alembic upgrade head && uv run alembic current"
        status: pass
    human_judgment: false
  - id: D2
    description: "Prod candidate-row-count sizing confirmation for the migration's batch-size adequacy (user_setup)"
    verification: []
    human_judgment: true
    rationale: "Requires bin/prod_db_tunnel.sh + the flawchess-prod-db MCP tool, neither of which is available to this executor session; a non-gating sizing confirmation per the plan's own note ('Batch size 100000 is index-driven and adequate regardless')."

# Metrics
duration: 10min
completed: 2026-07-01
status: complete
---

# Phase 147 Plan 02: Old-Corpus Ungated Tactic Tag Suppression Migration Summary

**Batched, index-driven Alembic DATA migration (`eb341e836ee9`) that suppresses raw ungated cp-based tactic tags on the pre-existing `game_flaws` corpus, joined to `game_positions` for the mate-adjacent carve-out, gated per orientation on its own PV-line blob column.**

## Performance

- **Duration:** ~10 min
- **Tasks:** 2
- **Files modified:** 2 (both new)

## Accomplishments
- New Alembic revision `eb341e836ee9` (down_revision `c3f5d1e8a092`) suppresses `allowed_*`/`missed_*` tactic columns per orientation for cp-based candidate rows, using the repo's established `DO $$ ... WHILE rows_updated > 0 LOOP ...` batched idiom (batch_size 100000) on the composite `(user_id, game_id, ply)` key — no surrogate `id` column exists on `game_flaws`.
- Predicate joins `game_flaws` to `game_positions` on `(user_id, game_id, ply = gf.ply - 1)` to evaluate `pre_flaw_eval_cp`, which is not a `game_flaws` column. This join is index-driven (confirmed via `EXPLAIN` in 147-RESEARCH.md against the existing partial index `ix_game_flaws_blob_backfill`) — no new index was created.
- Mate-adjacent rows (`eval_cp IS NULL`) and D-06 `[]`-sentinel rows (`allowed_pv_lines = '[]'::jsonb`, which is NOT NULL) are preserved automatically by the `IS NULL` predicate structure — no special-case branch needed.
- `downgrade()` is a documented no-op: the raw pre-gate motif is unrecoverable once suppressed, matching the repo's convention for lossy bulk-correctness migrations (e.g. the eval-only-residue wipe).
- New test `tests/test_migration_suppress_ungated_tactic_tags.py` seeds 4 rows covering: (1) cp-based suppression on both orientations, (2) mate-adjacent preservation, (3) D-06 sentinel preservation, and (4) a per-orientation-independence row (allowed already blobbed and preserved, missed still a candidate and suppressed) — proving the gate reads each orientation's own blob column rather than assuming the NULL-together invariant. A second SQL execution asserts zero rows change (idempotency).

## Task Commits

Each task was committed atomically:

1. **Task 1: Write the batched old-corpus suppression migration** - `26f1d55a` (feat)
2. **Task 2: Migration test — carve-outs + idempotency** - `0c0b2a8d` (test)

## Files Created/Modified
- `alembic/versions/20260701_190758_eb341e836ee9_suppress_ungated_tactic_tags_old_corpus.py` - Batched, index-driven DATA migration suppressing ungated cp-based tactic tags
- `tests/test_migration_suppress_ungated_tactic_tags.py` - Carve-out + idempotency test mirroring the migration SQL

## Decisions Made
- Followed RESEARCH.md's tested SQL verbatim (dry-run verified on dev, rolled back during research) — no deviation from the recommended shape.
- Extended the test beyond the plan's minimum 5 seed cases by combining "blobs already populated" (case 4) with "per-orientation independence" into a single row (allowed populated + KEPT, missed candidate + suppressed on the same `game_flaws` row), which more strongly proves the per-orientation gating requirement than two separate single-orientation rows would.

## Deviations from Plan

None - plan executed exactly as written. The migration SQL matches RESEARCH.md's tested reference verbatim; the test covers every carve-out named in the plan's `must_haves.truths` and `acceptance_criteria`.

## Issues Encountered

None. `uv run alembic upgrade head`, `uv run pytest tests/test_migration_suppress_ungated_tactic_tags.py -x`, `uv run ruff check`, and `uv run ty check app/ tests/` all passed on the first attempt.

## User Setup Required

**One item deferred — non-gating.** The plan's `user_setup` section asks for a prod candidate-row-count sizing confirmation via `bin/prod_db_tunnel.sh` + the `flawchess-prod-db` MCP query tool before shipping. This executor session did not have that MCP tool available. Per the plan's own framing ("Batch size 100000 is index-driven and adequate regardless — this is sizing confirmation, not a gate"), this does not block plan completion. Recommended before the phase's final deploy:

```sql
SELECT count(*) FROM game_flaws gf
JOIN game_positions gp ON gp.user_id=gf.user_id AND gp.game_id=gf.game_id AND gp.ply=gf.ply-1
WHERE (gf.allowed_pv_lines IS NULL OR gf.missed_pv_lines IS NULL)
  AND gp.eval_cp IS NOT NULL
  AND (gf.allowed_tactic_motif IS NOT NULL OR gf.missed_tactic_motif IS NOT NULL);
```

RESEARCH.md's rough extrapolation from dev proportions puts this in the ~600K-650K row range on prod (~6-7 batch-size-100000 iterations, expected low single-digit seconds).

## Next Phase Readiness
Part A (go-forward suppression from 147-01 + old-corpus migration from this plan) is now complete — the "no ungated tags anywhere" invariant holds for both new writes and the pre-existing corpus. Ready for 147-03 onward (Part B: upgraded-worker atomic eval+blob pipeline), which is architecturally independent of this migration. SEED-074 requirement completion is deferred to the phase's final plan since it spans all 6 plans.

---
*Phase: 147-persist-only-forcing-line-gated-tactic-tags-suppress-ungated*
*Plan: 02*
*Completed: 2026-07-01*

## Self-Check: PASSED

- FOUND: alembic/versions/20260701_190758_eb341e836ee9_suppress_ungated_tactic_tags_old_corpus.py
- FOUND: tests/test_migration_suppress_ungated_tactic_tags.py
- FOUND: .planning/phases/147-persist-only-forcing-line-gated-tactic-tags-suppress-ungated/147-02-SUMMARY.md
- FOUND commit: 26f1d55a
- FOUND commit: 0c0b2a8d
