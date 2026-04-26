---
phase: 69
plan: "06"
subsystem: benchmark-ingestion
tags: [benchmark, ingestion, smoke, resumability, verification, hot-patch]
dependency_graph:
  requires: [69-01, 69-02, 69-03, 69-04, 69-05]
  provides:
    - "reports/benchmark-db-phase69-verification-2026-04-26.md"
    - "Pipeline-correctness evidence for the v1.12 milestone gate"
  affects:
    - "INGEST-06 reduced (eval_depth + eval_source_version columns dropped)"
    - "SEED-006 entry criteria (full-scale ingest + failed-user investigation)"
tech_stack:
  added: []
  patterns:
    - "Verification-from-smoke pattern: pipeline-correctness evidence collected from a small smoke run rather than blocking on a multi-day full ingest"
    - "Hot-patch-mid-plan: discovered API-depth absence post-smoke; dropped dead columns via Alembic migration before shipping the phase"
key_files:
  created:
    - reports/benchmark-db-phase69-verification-2026-04-26.md
    - alembic/versions/20260426_drop_eval_depth_eval_source_version_from_games.py
  modified:
    - app/models/game.py (drop both eval columns)
    - app/schemas/normalization.py (drop both eval fields)
    - app/services/normalization.py (drop hardcoded "lichess-pgn" tag)
    - tests/test_benchmark_ingest.py (remove eval-column wiring tests; centipawn-convention test retained)
    - .planning/REQUIREMENTS.md (INFRA-02 ops-tables carve-out; INGEST-06 reduced)
decisions:
  - "Descoped Task 06-01 (manual dump download) — completed by user mid-plan; recorded in scratch notes."
  - "Descoped Task 06-05 (--per-cell 30 interim ingest) — per the 2026-04-26 v1.12 scope-down, populating the DB at scale is operational, not a milestone gate. Storage projection at full scale (~205 GB at --per-cell 100) flagged for SEED-006 sizing."
  - "Descoped Task 06-06 (centipawn-convention sample) — already covered by the automated test tests/test_benchmark_ingest.py::test_centipawn_convention_signed_from_white. CI runs it on every commit; no separate manual sample needed."
  - "Hot-patched eval_depth + eval_source_version columns out (commit e40b76e + b623da1) after the smoke confirmed the Lichess /api/games/user endpoint emits bare [%eval cp] with no depth field. Both columns were dead weight; reintroduce when an actual second eval source exists."
  - "INFRA-02 wording reworded to allow benchmark-only ops tables (benchmark_selected_users, benchmark_ingest_checkpoints) created via Base.metadata.create_all() — analytical schema (games, game_positions) remains on the canonical Alembic chain."
metrics:
  duration_minutes: 240
  completed_date: "2026-04-26"
  smoke_duration_minutes: 186  # 3h 6min wall-clock for --per-cell 3
  smoke_users: 60
  smoke_games_imported: 274143
  resumability_test: PASS
  hot_patch_commits: 2
---

# Phase 69 Plan 06: Smoke + Resumability + Verification Summary

End-to-end pipeline-correctness evidence for the v1.12 milestone gate: real-dump selection scan, `--per-cell 3` smoke ingest against the live Lichess API, SIGINT + SIGKILL resumability test, and a verification report covering all four Dimension-8 evidence sections.

The plan was scope-reduced mid-execution (2026-04-26 v1.12 scope-down moved Phases 70-73 to SEED-006, demoting full-scale ingest from milestone gate to SEED-006 entry criterion) and surgically hot-patched after the smoke surfaced two dead columns from the original 69-02 migration.

## Tasks Completed / Descoped

| Task | Status | Notes |
|------|--------|-------|
| 06-01 dump download | ✅ done (user) | 2026-03 Lichess monthly dump downloaded to local disk (outside git). |
| 06-02 selection scan | ✅ done | 90M games scanned, 491k qualifying (K=10), 8,628 persisted across 20 cells. 17/20 cells hit 500 cap. |
| 06-03 smoke `--per-cell 3` | ✅ done | 60 terminal rows: 56 completed, 3 over_20k_games skips, 1 unexplained failure (SEED-006 follow-up). 274k games, 19.4M positions imported in 3h 6min. |
| 06-04 SIGINT resumability | ✅ done | SIGINT + SIGKILL both leave in-flight user as `pending`; resume picks up the pending row first; 0 duplicate game rows. PASS. |
| 06-05 `--per-cell 30` interim ingest | 🚫 descoped | v1.12 scope-down: populating DB at scale is operational, not a milestone gate. Storage projection ~205 GB at full scale flagged for SEED-006 disk sizing. |
| 06-06 centipawn-convention sample | 🚫 descoped | Already verified by automated test `test_centipawn_convention_signed_from_white` (asserts `[%eval 2.35]` → +235 cp etc., from white's POV). Runs in CI. |
| 06-07 verification report | ✅ done | `reports/benchmark-db-phase69-verification-2026-04-26.md`. Covers all four Dimension-8 evidence sections + storage budget + hot-patch context. |
| 06-08 cleanup | ⏳ pending (manual) | User to delete the 2026-03 Lichess dump file from local disk per D-03. |

## Hot-Patch Mid-Plan: Drop Dead Eval Columns

After the smoke completed, sampling the imported data revealed both `games.eval_depth` and `games.eval_source_version` (added in plan 69-02 migration `b11018499e4f`) were dead:

- The Lichess `/api/games/user` endpoint's PGN includes only bare `[%eval CP]` annotations — no depth field. Verified by sampling 5 games across the 289k smoke result; every annotation is depth-less.
- `eval_source_version` was hardcoded to `"lichess-pgn"` for every Lichess import regardless of whether the game's PGN actually had any eval annotations (only 17% of position rows actually carry evals). Zero information content.

Both columns dropped via migration `6809b7c79eb3` (commit `e40b76e`). REQUIREMENTS.md INGEST-06 reduced to "centipawn convention verified" (commit `b623da1`). The 289,022 benchmark games are preserved.

This is the kind of design slip that only smoke-vs-spec can catch: the original 69-02 plan + `gsd-discuss-phase` decision context (D-12 etc.) all assumed Lichess API surfaces depth metadata. The hot-patch path was lighter than running a full corrective phase — small surface area (5 source files + 1 migration), straightforward Alembic, no data loss.

## Artifacts Produced

### `reports/benchmark-db-phase69-verification-2026-04-26.md`

End-of-phase verification report. Sections:

1. Scope and verdict (PASS).
2. Selection scan stats (INGEST-01/02/03).
3. Smoke ingest stats (INGEST-04/05/06).
4. Per-cell game counts and eval coverage (Dimension-8).
5. Resumability test transcript (Dimension-8).
6. Storage budget vs INGEST-05 target.
7. Hot-patch context (eval_depth/eval_source_version drop).
8. Requirements coverage table (9/9 met).
9. SEED-006 outstanding work.

### `alembic/versions/20260426_drop_eval_depth_eval_source_version_from_games.py`

Migration `6809b7c79eb3` (revises `b11018499e4f`). Drops both columns from `games`. Applied to dev DB and benchmark DB; will run on prod on next deploy. The original 69-02 migration is left intact in history (standard Alembic pattern: never rewrite applied migrations).

## Requirements Completed

INFRA-01, INFRA-02 (with ops-tables carve-out), INFRA-03, INGEST-01, INGEST-02, INGEST-03, INGEST-04, INGEST-05 (per scope-down), INGEST-06 (with column drop) — 9/9.

## Surprises / Lessons

- **Bare API PGN annotations**: don't trust documentation about "depth available in PGN" — Lichess dump exports include depth (`[%eval cp,depth]`), API exports do not (`[%eval cp]`). Verify with a sample before specifying schema.
- **Smoke catches what discuss-phase can't**: the eval_source_version "tag every Lichess import" pattern looked fine in plan 69-02 but the smoke output (17% eval coverage on positions vs 100% tag on games) made the mismatch visible immediately.
- **Storage projection blew past INGEST-05's 50-100 GB target by 2x** even at modest `--per-cell 100`. The scope-down decision two days before this plan ran turned out to be necessary on operational grounds, not just sequencing.

## Next Steps

- `/gsd-verify-work 69` to validate phase against goal.
- `/gsd-ship 69` to push branch + create PR.
- After merge, queue SEED-006 surfacing for full-scale ingest planning.
