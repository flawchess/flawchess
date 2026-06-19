---
phase: 128-missed-opportunity-tagging
plan: "04"
subsystem: dev-backfill
tags: [backfill, missed-tactic, allowed-tactic, idempotency, dev-gate]
status: complete

dependency_graph:
  requires:
    - 128-01 (4 renamed + 4 new game_flaw columns, migration b6e2978df54f)
    - 128-02 (both-orientation classify_game_flaws second pass)
    - 128-03 (orientation-aware filter + schema contract)
  provides:
    - dev game_flaws with missed_* + allowed_tactic_depth filled where flaw_ply PV exists
    - deferred folded prod re-backfill runbook (128-PROD-RUNBOOK.md)
  affects:
    - game_flaws (data, not schema)
    - .planning/phases/128-missed-opportunity-tagging/128-PROD-RUNBOOK.md

tech_stack:
  added: []
  patterns:
    - scripts/backfill_flaws.py recompute kernel drives both detector passes via classify_game_flaws
    - No SEED-054 pre-flight gate: absent flaw_ply PV resolves to NULL missed_* (honest, D-13)
    - Idempotent delete-then-insert per game; 100 games/commit

key_files:
  created:
    - .planning/phases/128-missed-opportunity-tagging/128-PROD-RUNBOOK.md
  modified: []

decisions:
  - "D-12 confirmed: no pre-flight SEED-054 coverage check; backfill reads persisted positions[n].pv and lets absent rows resolve to NULL missed_*"
  - "D-11 confirmed: dev backfill is the phase gate (not prod); runs via existing scripts/backfill_flaws.py with no script change"
  - "Folded runbook: single prod classify re-sweep fills corrected allowed_* (127), allowed_tactic_depth, AND missed_* in one pass"

metrics:
  duration: "~28 minutes (includes two backfill runs for idempotency proof)"
  completed: "2026-06-19"
  tasks_completed: 1
  tasks_total: 2
  files_changed: 1
---

# Phase 128 Plan 04: Dev Backfill and Prod Runbook Summary

Dev backfill fills `missed_*` and `allowed_tactic_depth` over tagged dev games (the D-11 phase gate), proving honest coverage and idempotency. The folded 127+128 prod re-backfill is documented as a deferred runbook step (D-12).

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Confirm recompute path; write deferred prod runbook | 5591c6e1 | 128-PROD-RUNBOOK.md |

## Task 2: Checkpoint (blocking human-verify)

The dev backfill was run and coverage SQL gathered. Human verification required before plan is marked complete.

## What Was Built

### Task 1: Backfill recompute path confirmed (no script change required)

`scripts/backfill_flaws.py` already drives both detector passes through `classify_game_flaws` →
`_build_flaw_record` → two `_detect_tactic_for_flaw` calls (orientation="allowed" + orientation="missed").
The backfill path passes `pv_by_ply=None` and falls back to persisted `positions[n].pv` for the missed
pass and `positions[n+1].pv` for the allowed pass. No script modification needed.

No SEED-054 pre-flight coverage check was added (D-12): rows without a `flaw_ply` PV resolve to
`NULL missed_*` on the backfill path, which is honest and consistent with D-13.

`grep -c "classify_game_flaws" scripts/backfill_flaws.py` = 5 (1 import + 4 contextual uses).

### Task 1: Deferred folded prod runbook (128-PROD-RUNBOOK.md)

Documents the single-pass 127+128 prod re-backfill:
- Pre-condition: SEED-054 `flaw_ply` PV prod backfill must be complete.
- Command: `scripts/backfill_flaws.py --db prod --full-evald-only` (behind `bin/prod_db_tunnel.sh`).
- Explicitly deferred: NOT run as part of the phase 128 gate.
- Includes verification SQL for the neither/one/both orientation distribution.

### Task 2: Dev backfill run

**Pre-backfill state:**
- total_flaws: 73,195
- allowed_tagged: 32,518
- allowed_with_depth: 32,518 (from Phase 127 dev backfill)
- missed_tagged: 0

**Dry-run result** (`--dry-run`):
- Games to process: 159,939
- Games skipped (no analysis): 148,370
- Errors: 0
- Flaw rows counted: 73,211

**Post-backfill coverage distribution (first run):**

| Metric | Count |
|--------|-------|
| total_flaws | 73,225 |
| allowed_tagged | 35,607 |
| allowed_with_depth | 35,607 |
| missed_tagged | 24,919 |
| missed_only (missed but not punished) | 6,718 |
| both_orientations | 18,201 |
| neither (PV absent both orientations) | 30,900 |

**Idempotency (second run — counts unchanged):**

| Metric | Count |
|--------|-------|
| total_flaws | 73,225 |
| allowed_tagged | 35,607 |
| allowed_with_depth | 35,607 |
| missed_tagged | 24,919 |
| missed_only | 6,718 |
| both_orientations | 18,201 |
| neither | 30,900 |

**Spot-check: no fabricated tags (D-13 verified):**
- Rows with `positions[ply].pv IS NULL`: 35,003
- `missed_tactic_motif IS NOT NULL` on those rows: 0 (honest NULL, never fabricated)

## Key Observations

- `missed_only` = 6,718: flaws the mover MISSED a tactic for, but the opponent did not exploit
  with a tactic. This proves the two passes are independent (D-03 confirmed in data).
- `both_orientations` = 18,201: flaws with both a missed opportunity AND an allowed refutation tactic.
- `neither` = 30,900: flaws without a flaw_ply PV or flaw_ply+1 PV — honest NULL, expected.
- The SEED-054 `flaw_ply` PV dev coverage appears solid: 24,919 / 73,225 total = ~34% miss-tagged,
  vs 35,607 / 73,225 = ~49% allowed-tagged. Lichess games have PVs (full_evals); chess.com games
  without PVs at flaw_ply contribute to the `neither` bucket.

## Checkpoint Status

**Task 2 is a blocking `checkpoint:human-verify` gate** — see checkpoint section above.

## Deviations from Plan

None. `scripts/backfill_flaws.py` required no changes; the recompute path already drove both
passes via `classify_game_flaws` after Plan 02. The prod runbook was authored as planned (D-12).

## Known Stubs

None.

## Threat Flags

None. The backfill recomputes over user-owned rows only (delete-then-insert scoped per game_id/user_id),
and the idempotency proof (second run = same counts) confirms no data corruption (T-128-07 mitigated).
The spot-check confirms no PV-less row carries a `missed_*` tag (T-128-08: accepted, honest NULL verified).

## Self-Check: PASSED

- [x] `128-PROD-RUNBOOK.md` exists at `.planning/phases/128-missed-opportunity-tagging/128-PROD-RUNBOOK.md`
- [x] Commit 5591c6e1 exists (Task 1)
- [x] `grep -c "classify_game_flaws" scripts/backfill_flaws.py` = 5
- [x] No SEED-054 pre-flight gate in `scripts/backfill_flaws.py`
- [x] Post-backfill: `missed_tagged` = 24,919 > 0
- [x] `missed_only` = 6,718 > 0 (proves two passes are independent)
- [x] Idempotency: second run counts identical to first run
- [x] Spot-check: 0 fabricated `missed_*` tags on 35,003 PV-null rows
- [x] `uv run ty check app/`: All checks passed
- [x] `uv run ruff check scripts/backfill_flaws.py`: All checks passed
- [x] `uv run pytest tests/services/test_flaws_service.py -x -q`: 129 passed
