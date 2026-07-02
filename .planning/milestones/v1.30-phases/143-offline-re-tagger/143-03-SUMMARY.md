---
phase: 143-offline-re-tagger
plan: "03"
subsystem: backend
tags: [offline-retagger, git-mv, blob-loading, margin-tuning, dry-run-report, idempotency, sc1, sc4, retag-01, retag-02]
dependency_graph:
  requires: [143-01, 143-02, 141-forcing-line-gate, 142-multipv-engine-pass]
  provides: [offline-re-tagger-cli, per-motif-delta-report, retag-idempotency-proof]
  affects:
    - scripts/retag_flaws.py
    - app/repositories/game_flaws_repository.py
    - reports/retag/
    - tests/scripts/test_retag_flaws.py
tech_stack:
  added: []
  patterns: [git-mv-history-preserve, jsonb-explicit-column-select, picklable-worker-payload, dry-run-report-writer, change-only-update-idempotency, session-maker-injection-tests]
key_files:
  created:
    - scripts/retag_flaws.py (git mv from scripts/backfill_tactic_tags.py — history preserved)
    - reports/retag/.gitkeep
    - tests/scripts/test_retag_flaws.py
  modified:
    - app/repositories/game_flaws_repository.py (two docstring refs updated)
decisions:
  - "D-01: git mv scripts/backfill_tactic_tags.py scripts/retag_flaws.py preserves git history; gate-free refresh tool no longer coherent once gate wired into live classify path"
  - "_FlawWork.margin carries the threshold across spawn-worker IPC boundary (no global mutation, D-03, worker-pool-safe)"
  - "_fetch_flaw_page selects GameFlaw.allowed_pv_lines + missed_pv_lines explicitly (bypasses deferred=True; asyncpg auto-deserializes JSONB)"
  - "_worker_recompute calls _classify_tactic_gated (single classify path from Plan 02, SC4 no-drift)"
  - "Report written only on --dry-run; re-runnable for Phase 144 margin sweep"
  - "pre_flaw_eval_cp sourced from work.cur.eval_cp (A1 assumption: same for both orientations)"
metrics:
  duration: "~10min"
  completed: "2026-06-30"
  tasks: 3
  files: 4
status: complete
---

# Phase 143 Plan 03: Offline Re-tagger CLI — SUMMARY

Delivered the offline re-tagger by extending `scripts/backfill_tactic_tags.py` with JSONB blob loading, `--margin` flag, and `_classify_tactic_gated` classify path, then `git mv` to `scripts/retag_flaws.py` (D-01). Added a per-motif tag-delta report writer (D-04) and a pytest proving dry-run + idempotency against the per-run test DB.

## Tasks Completed

| # | Task | Commit | Files |
|---|------|--------|-------|
| 1 | Extend backfill_tactic_tags.py in-place + git mv to retag_flaws.py (D-01) | 48b07427 | scripts/retag_flaws.py, app/repositories/game_flaws_repository.py, reports/retag/.gitkeep |
| 2 | Per-motif tag-delta report writer (D-04, RETAG SC1) | 48b07427 | scripts/retag_flaws.py (inline, same commit) |
| 3 | Re-tagger pytest — dry-run delta + idempotency against per-run test DB (SC1, SC4) | 543343e3 | tests/scripts/test_retag_flaws.py |

## What Was Built

### Task 1 — `scripts/retag_flaws.py` (D-01, git mv)

**`git mv scripts/backfill_tactic_tags.py scripts/retag_flaws.py`** — git history preserved.

**Module docstring updated** to reflect:
- New role: re-derive tactic tags from stored MultiPV-2 JSONB blobs, applying the forcing-line gate (no engine pass)
- Why gate-free refresh no longer exists (D-01: once gate wired into live classify path, a gate-free backfill diverges from prod)
- `--margin` flag and RETAG-01 goal (tunable engine-free re-derivation)
- T-143-05 note: `--db prod` writes require running on the prod server

**`_PosRow` extended**: `eval_cp: int | None` added for gate's already-winning reject.

**`_FlawWork` extended**: `allowed_pv_blob`, `missed_pv_blob` (`list[Any] | None`), `margin: float` added. All picklable — cross spawn-worker IPC boundary safely (D-03, worker-pool-safe).

**`_fetch_flaw_page` extended**: Projects `GameFlaw.allowed_pv_lines` and `GameFlaw.missed_pv_lines` explicitly. Deferred status on the ORM entity is irrelevant for explicit column selects; asyncpg auto-deserializes JSONB to `list[dict]`.

**`_load_positions_for_page` extended**: Projects `GamePosition.eval_cp` for `pre_flaw_eval_cp`.

**`_make_works` updated**: passes blobs and `margin` from `run_backfill` arg into `_FlawWork`.

**`_worker_recompute` updated**: replaces `_detect_tactic_for_flaw` calls with `_classify_tactic_gated` for both orientations (single classify path, SC4 no-drift). `pre_flaw_eval_cp` derived from `work.cur.eval_cp`. `margin` flows via `work.margin` (no global mutation).

**CLI `--margin` arg added**: `type=float`, default `ONLY_MOVE_WIN_PROB_MARGIN`. `--db` choices `["dev","benchmark","prod"]` (Literal-typed in `run_backfill` signature, `argparse.choices` for the CLI gate).

**`run_backfill` updated**: `margin: float = ONLY_MOVE_WIN_PROB_MARGIN` param added; threaded to `_make_works`. Sentry context key renamed from `tactic_tag_backfill` to `retag_flaws`.

**Docstring refs in `game_flaws_repository.py`** updated: two references to `backfill_tactic_tags.py` updated to `retag_flaws.py`; `bulk_update_tactic_tags` docstring notes gate margin change as a trigger.

### Task 2 — Per-motif delta report writer (D-04, inline in Task 1 commit)

**`_accumulate_motif_counts`**: accumulates per-motif removed/survived counts from a page of results. Decodes tactic motif ints to names via `TacticMotifInt`. Old/new tuples compared to classify "removed" vs "survived".

**`_write_retag_report`**: writes `reports/retag/retag-YYYY-MM-DD.md` when `dry_run=True`. Creates `reports/retag/` directory with `mkdir(parents=True, exist_ok=True)`. Report content:
- Header: Generated/Margin/Scope/Mode/Flaws-examined/Flaw-rows-that-would-change
- "Allowed-orientation tag changes" pipe table (Motif, Previously tagged, Gate suppressed, Survived, Suppression %)
- "Missed-orientation tag changes" pipe table (same columns)
- Summary totals

**`reports/retag/.gitkeep`**: committed as placeholder for the directory.

### Task 3 — `tests/scripts/test_retag_flaws.py`

6 tests in 3 classes, using session-maker injection against the per-run test DB:

**`retag_fixture`**: commits User + Game + 3 GamePosition rows + 1 GameFlaw at ply 1 with:
- `allowed_pv_lines` = FORCING_BLOB (gap=800, passes gate at any margin)
- `missed_pv_lines` = NON_FORCING_BLOB (gap≈20 cp, fails gate at margin=0.35)
- Both `allowed_tactic_motif` and `missed_tactic_motif` seeded to HANGING_PIECE (int=2)
- Teardown deletes committed rows (finally block, lottery-test leakage guard)

**`TestRetagDryRun`** (SC1 / RETAG-01):
- `test_dry_run_writes_zero_db_rows`: baseline tags unchanged after `dry_run=True` run
- `test_dry_run_writes_report_file`: `reports/retag/retag-*.md` exists after dry-run
- `test_dry_run_report_contains_per_motif_counts`: report contains "HANGING_PIECE" (motif name decoded via TacticMotifInt)

**`TestRetagIdempotency`** (SC4 / RETAG-02):
- `test_second_run_changes_zero_rows`: first run changes tags; second run at same margin produces identical output (change-only UPDATE makes it a no-op)
- `test_first_run_suppresses_non_forcing_missed_tag`: `missed_tactic_motif` is None after first real run at `ONLY_MOVE_WIN_PROB_MARGIN`

**`TestRetagMarginSensitivity`** (RETAG-01 tunability):
- `test_larger_margin_suppresses_more_tags`: intermediate blob (gap≈0.122) passes at margin=0.1 but is suppressed at margin=0.5 — confirms `--margin` threads correctly

## Verification Results

```
test ! -f scripts/backfill_tactic_tags.py && test -f scripts/retag_flaws.py   → RENAME OK
uv run ty check scripts/retag_flaws.py app/repositories/... tests/scripts/...  → All checks passed!
uv run pytest tests/scripts/test_retag_flaws.py tests/test_backfill_flaws.py -q → 13 passed
```

## Deviations from Plan

**[Rule 2 - Minor addition] Task 1 and Task 2 implemented in a single commit**

The plan separated Task 1 (script changes) and Task 2 (report writer) as distinct tasks, but the report writer was a natural part of the script extension and adding it in a second pass would have required re-reading and re-editing the same file. Both were implemented together in the Task 1 commit (48b07427). No functional impact; the acceptance criteria for both tasks are fully met.

## Known Stubs

None — this plan delivers a CLI script and tests. No UI or data rendering stubs.

## Threat Surface Scan

No new network endpoints, auth paths, or schema changes. The script writes to `game_flaws` tactic columns (operator-only access, `--db` Literal allowlist T-143-05). The `reports/retag/` directory is a new local write path but contains no sensitive data. T-143-04 through T-143-07 addressed as designed.

## Self-Check: PASSED

- FOUND: scripts/retag_flaws.py
- FOUND: scripts/backfill_tactic_tags.py GONE (git mv confirmed)
- FOUND: reports/retag/.gitkeep
- FOUND: tests/scripts/test_retag_flaws.py
- FOUND: commit 48b07427 (Task 1+2: feat — script extension + git mv)
- FOUND: commit 543343e3 (Task 3: test — retag pytest)
- 13 tests pass (6 new + 7 existing test_backfill_flaws.py unaffected)
