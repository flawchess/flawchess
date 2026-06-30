---
phase: 145-corpus-backfill-rollout
plan: "05"
subsystem: scripts
tags: [backfill, observability, rollout, SC1, SC3, tactic-motif, snapshot, D-01]
dependency_graph:
  requires: [145-02-PLAN.md, 145-04-PLAN.md]
  provides: [backfill_multipv.py, snapshot_tactic_counts.py]
  affects: [scripts/backfill_multipv.py, scripts/snapshot_tactic_counts.py, tests/test_backfill_multipv.py]
tech_stack:
  added: []
  patterns: [thin-observability-CLI, read-only-script, injectable-session-maker, before-after-report]
key_files:
  created:
    - scripts/backfill_multipv.py
    - scripts/snapshot_tactic_counts.py
    - tests/test_backfill_multipv.py
  modified: []
decisions:
  - "D-01 compliance: backfill_multipv.py has no EnginePool — the remote fleet does the bulk MultiPV=2 compute via tier-4 lottery"
  - "SQLAlchemy JSONB None = JSON null bug: GameFlaw constructor must omit allowed_pv_lines (not pass None) to get SQL NULL; omitting lets the DB-level nullable default apply"
  - "before counts embedded as HTML comments in the report so --phase after can compute deltas without a second DB round-trip"
metrics:
  duration: "~60 minutes (resumed from prior session)"
  completed: 2026-06-30
  tasks_completed: 2
  files_modified: 0
  files_created: 3
status: complete
---

# Phase 145 Plan 05: Operator Rollout Scripts — Summary

## One-liner

Thin observability CLI (backfill_multipv.py, SC1) with --status/--dry-run/--dev-validate modes and before/after per-motif tactic chip-count report script (snapshot_tactic_counts.py, SC3), both following the db_url_for_target/--db dev|benchmark|prod convention.

## What Was Built

### Task 1: backfill_multipv.py thin observability/kickoff/dev-validate CLI (SC1)

`scripts/backfill_multipv.py` — a thin operator CLI. No EnginePool. The remote eval-worker fleet does all bulk MultiPV=2 compute via the tier-4 lottery (D-01).

**Modes:**
- `--status`: queries `game_flaws WHERE allowed_pv_lines IS NULL` for overall and engine/lichess split counts. Read-only.
- `--dry-run`: reports tier-4-eligible scope (analyzed + non-guest) without writing anything.
- `--dev-validate`: drives the full tier-4 lottery → flaw-blob lease → blob assembly → batch-write → idempotency assertion pipeline against the dev DB. Uses synthetic evals (cp=0, no second-best) to exercise the write path without a real engine.

**Key design decisions:**
- All runner functions accept injectable `session_maker` and `lease_builder` parameters for testability.
- `--dev-validate` guards `--db dev` only (exits 1 if used with prod).
- Module docstring explicitly reconciles SC1's stale "module-level EnginePool is reused" wording with the remote-fleet D-01 design.

**Tests in `tests/test_backfill_multipv.py`:**
- `TestQueryStatus`: verifies total counts and engine/lichess split against committed fixture data.
- `TestQueryEligible`: verifies guest exclusion from the tier-4 predicate.
- `TestDryRunNoWrites`: verifies `run_dry_run` writes 0 flaw blobs.

**Dev smoke test confirmed (dev DB):**
```
Total games remaining : 10,263
Total flaws remaining : 66,370
  Engine games        :  5,836  (37,343 flaws)
  Lichess %eval games :  4,427  (29,027 flaws)
```

### Task 2: snapshot_tactic_counts.py before/after per-motif report (SC3)

`scripts/snapshot_tactic_counts.py` — read-only report generator.

**Modes:**
- `--phase before`: writes `reports/retag/rollout-YYYY-MM-DD.md` with a per-motif table of allowed/missed chip counts. Embeds machine-readable counts in HTML comments for delta computation.
- `--phase after`: appends a post-drain section with a delta column (after - before per motif). Falls back gracefully if no before baseline found.

**Key design decisions:**
- Before counts embedded as `<!-- snapshot:before:allowed -->` / `<!-- snapshot:before:missed -->` HTML comment blocks so the "after" run can compute deltas without a second DB round-trip or external state file.
- `_build_count_table` accepts optional `before_allowed`/`before_missed` dicts; shows `+N`/`-N` delta column only when both are provided.
- TacticMotifInt.name used for all motif id decoding; unknown ids fall back to the raw integer string.
- Injectable `session_maker` and `report_dir` parameters for testability.

**Tests in `tests/test_backfill_multipv.py`:**
- `TestSnapshotMotifMapping`: verifies all 29 TacticMotifInt values resolve to non-empty name strings; spot-checks FORK=1, HANGING_PIECE=2, PIN=3, BACK_RANK_MATE=7, UNDER_PROMOTION=29.
- `TestSnapshotMarkdownTable`: verifies header/separator format, motif names not raw integers, empty counts produce header-only table, one-orientation motifs get 0 in the other column.

**Dev smoke test confirmed:**
- `--phase before` exits 0, writes `reports/retag/rollout-YYYY-MM-DD.md` with 29 allowed motifs (16,558 flaws) and 27 missed motifs (8,865 flaws).
- `--phase after` exits 0, appends after-section with delta column.

## Verification Results

- `uv run pytest tests/test_backfill_multipv.py -x`: **14 passed**
- `uv run python scripts/backfill_multipv.py --db dev --status`: exits 0, prints counts
- `uv run python scripts/snapshot_tactic_counts.py --db dev --phase before`: exits 0, writes report
- `uv run ruff check scripts/`: All checks passed
- `uv run ty check app/ tests/`: All checks passed (zero errors)
- `grep "EnginePool" scripts/backfill_multipv.py`: only in docstring text ("no EnginePool") — no import or instantiation confirmed

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] SQLAlchemy JSONB None serializes to JSON null, not SQL NULL**
- **Found during:** Task 1 test fixture debugging
- **Issue:** Passing `allowed_pv_lines=None` to `GameFlaw(...)` in test fixtures caused SQLAlchemy to serialize Python `None` to the JSONB value `null` (JSON null), not SQL NULL. This made `WHERE allowed_pv_lines IS NULL` return 0 even though the fixture had committed 4 rows.
- **Fix:** Removed `allowed_pv_lines=None` and `missed_pv_lines=None` from all `GameFlaw` constructor calls in the fixture. The column defaults to SQL NULL when omitted (nullable JSONB with no server_default). Added an explanatory comment to prevent future recurrence.
- **Note:** Production code in `flaw_record_to_row` was already correct — it never sets `allowed_pv_lines` in the insert dict, so production rows get SQL NULL correctly.
- **Files modified:** `tests/test_backfill_multipv.py`
- **Commit:** a6946cf6

## Known Stubs

None. Both scripts are complete operator tooling with no placeholder logic.

## Threat Flags

No new network endpoints or auth paths. Scripts are operator-run local tools; `--db prod` targets the existing SSH-tunneled read-only path.

| Flag | File | Description |
|------|------|-------------|
| dev-validate writes | scripts/backfill_multipv.py | `--dev-validate` writes blob data to dev DB only (gated by `--db dev` check) |

T-145-13 (tampering via dev-validate) addressed: explicit `--db dev` guard; `--db prod` paths are read-only.
T-145-14 (information disclosure) accepted: aggregate per-motif counts only, no PII.

## Self-Check: PASSED

| Item | Status |
|------|--------|
| scripts/backfill_multipv.py | FOUND |
| scripts/snapshot_tactic_counts.py | FOUND |
| tests/test_backfill_multipv.py | FOUND |
| a6946cf6 feat(145-05): add backfill_multipv.py observability script and tests | FOUND |
| 1ec7df02 feat(145-05): add snapshot_tactic_counts.py before/after rollout report (SC3) | FOUND |
