---
phase: 150-consolidate-write-path
plan: 04
subsystem: database
tags: [sqlalchemy-async, postgres-jsonb, eval-pipeline, diff-upsert]

requires:
  - phase: 150-consolidate-write-path
    provides: "Golden-snapshot equivalence harness (150-01) driving _apply_atomic_submit across 8 D-02 scenarios"
provides:
  - "FLAW_BLOB_COLUMNS single-source-of-truth constant (game_flaws_repository.py)"
  - "Per-ply 4-way diff/upsert replacing delete-then-insert in _classify_and_fill_oracle"
  - "delete_flaw_plies + bulk_update_game_flaw_rows generic repository functions"
  - "Blob/tactic-tag preservation as a native write property (no caller-side snapshot/restore)"
affects: [150-05, eval_apply.py-module-split-if-planned-later]

tech-stack:
  added: []
  patterns:
    - "Preservation-by-omission: an UPDATE row dict that never mentions a column leaves it untouched by the SQL SET clause — safer than COALESCE-vs-bound-None for JSONB (asyncpg serializes Python None as json null, not SQL NULL)"
    - "Per-ply set-difference partition (existing_plies vs desired_plies) instead of delete-then-insert, mirroring the DELETE/INSERT/UPDATE-fresh/UPDATE-preserve shape recommended in RESEARCH.md"

key-files:
  created: []
  modified:
    - app/repositories/game_flaws_repository.py
    - app/services/eval_drain.py
    - app/routers/eval_remote.py

key-decisions:
  - "already_blobbed_plies (allowed_pv_lines IS NOT NULL) gates preservation, not merely existing_plies — a stale entry-pass row or never-blobbed flaw has nothing to protect and takes this pass's fresh values, matching the deleted snapshot's own IS NOT NULL gate exactly (see Deviations)"
  - "The PV-line blob write (_batch_update_flaw_pv_lines) now runs INSIDE _classify_and_fill_oracle, filtered to skip preserve-plies, instead of the caller invoking a separate _run_multipv2_pass afterward — folds preservation for all 10 FLAW_BLOB_COLUMNS into one self-contained write, avoiding a same-transaction re-clobber of the D-06 [] sentinel over a preserved real blob"
  - "_run_multipv2_pass deleted as dead code once both call sites (eval_drain.py, eval_remote.py) stopped needing it"

patterns-established:
  - "FLAW_BLOB_COLUMNS extends the existing TACTIC_TAG_COLUMNS single-source-of-truth precedent (2-line addition) so a future 11th blob/tactic column cannot be silently nulled by an upsert that forgets to list it"

requirements-completed: [WRITE-03]

coverage:
  - id: D1
    description: "FLAW_BLOB_COLUMNS defined once in game_flaws_repository.py and consumed by the diff/upsert's preserve branch"
    requirement: "WRITE-03"
    verification:
      - kind: unit
        ref: "grep -c '^FLAW_BLOB_COLUMNS' app/repositories/game_flaws_repository.py"
        status: pass
    human_judgment: false
  - id: D2
    description: "_classify_and_fill_oracle executes a 4-way partition (delete/insert-new/update-fresh/update-preserve); flip-OUT is a clean DELETE, never a bulk-update-by-PK"
    requirement: "WRITE-03"
    verification:
      - kind: unit
        ref: "tests/services/test_flaw_upsert_equivalence.py::test_write_path_matches_golden[scenario_3_flip_out] (8 parametrized cases total, all pass)"
        status: pass
    human_judgment: false
  - id: D3
    description: "Golden equivalence test passes all 8 scenarios byte-identical (explicit-NULL blob columns included) against the new diff/upsert"
    requirement: "WRITE-03"
    verification:
      - kind: unit
        ref: "tests/services/test_flaw_upsert_equivalence.py::test_write_path_matches_golden (8/8 pass)"
        status: pass
      - kind: unit
        ref: "uv run python -m scripts.gen_write_path_golden; git diff --exit-code tests/fixtures/write_path_golden/ (fixtures byte-identical after regeneration against the new code)"
        status: pass
    human_judgment: false
  - id: D4
    description: "Snapshot/restore compensation helpers deleted from eval_remote.py; no COALESCE-over-JSONB upsert exists anywhere; fail-closed contract preserved (flaw writes + oracle UPDATE uncaught)"
    requirement: "WRITE-03"
    verification:
      - kind: unit
        ref: "grep -rn '_snapshot_preserved_flaw_blobs|_restore_preserved_flaw_blobs' app/ (0 hits)"
        status: pass
      - kind: unit
        ref: "uv run pytest tests/test_eval_worker_endpoints.py tests/services/test_full_eval_drain.py tests/services/test_flaw_upsert_equivalence.py -x (261 passed)"
        status: pass
      - kind: other
        ref: "uv run ruff check . && uv run ty check app/ tests/ (both clean)"
        status: pass
    human_judgment: false

duration: 40min
completed: 2026-07-04
status: complete
---

# Phase 150 Plan 04: Consolidate Write Path — Diff/Upsert Summary

**`_classify_and_fill_oracle`'s delete-then-insert replaced with a per-ply 4-way diff/upsert driven by one `FLAW_BLOB_COLUMNS` constant — blob/tactic-tag preservation is now native to the write, and the two caller-side snapshot/restore helpers are gone. Golden equivalence test (150-01) passes byte-identical across all 8 scenarios, confirmed via both the parametrized test and a regenerate-and-diff against the committed fixtures.**

## Performance

- **Duration:** ~40 min
- **Tasks:** 2 completed
- **Files modified:** 3 (`app/repositories/game_flaws_repository.py`, `app/services/eval_drain.py`, `app/routers/eval_remote.py`)

## Accomplishments

- `FLAW_BLOB_COLUMNS: tuple[str, ...] = ("allowed_pv_lines", "missed_pv_lines") + TACTIC_TAG_COLUMNS` — single source of truth for the 10 preserved columns (D-04), a 2-line extension of the existing `TACTIC_TAG_COLUMNS` precedent.
- Two new generic repository functions: `delete_flaw_plies` (clean per-ply `DELETE ... WHERE ply IN (...)`, never a bulk-update-by-PK — the exact fix for the FLAWCHESS-8D StaleDataError class) and `bulk_update_game_flaw_rows` (generic ORM bulk-update-by-PK, the vehicle for both the fresh and preserve UPDATE branches).
- `_classify_and_fill_oracle` now partitions plies against `existing_plies` (SELECT before mutating) into 4 buckets: DELETE removed flaws, INSERT new flaws, UPDATE-fresh (freshly-blobbed existing flaws — full row incl. fresh tactic tags), UPDATE-preserve (already-blobbed-but-not-freshly-re-blobbed existing flaws — `FLAW_BLOB_COLUMNS` keys excluded from the dict entirely so they're never mentioned in the SQL `SET` clause).
- The PV-line blob write (`_batch_update_flaw_pv_lines`) now runs *inside* `_classify_and_fill_oracle`, filtered to exclude preserve-plies — a D-06 `[]` sentinel is never even written over an already-real blob, so there's nothing left to restore afterward. This folds the caller-side `_run_multipv2_pass` call into the diff/upsert itself; `_run_multipv2_pass` became dead code and was deleted.
- `_snapshot_preserved_flaw_blobs` and `_restore_preserved_flaw_blobs` (SEED-076, `eval_remote.py`) deleted outright — `_apply_atomic_submit` now calls `_classify_and_fill_oracle` once with no snapshot-before / restore-after dance.
- Golden equivalence test (`tests/services/test_flaw_upsert_equivalence.py`) passes all 8 scenarios byte-identical against the new diff/upsert. The committed generator (`scripts/gen_write_path_golden.py`) was also re-run against the new code and produced a zero-diff regeneration of all 7 fixture files, confirming reproducibility per the plan's D-01 mitigation.
- Full backend suite green: `pytest -n auto` 3162 passed / 18 skipped; `ruff check .`, `ruff format --check`, and `ty check app/ tests/` all clean.

## Task Commits

1. **Task 1: FLAW_BLOB_COLUMNS + 4-way diff/upsert in `_classify_and_fill_oracle`** - `1f752b51` (feat)
2. **Task 2: Delete the snapshot/restore compensation helpers** - `9db5bfa5` (feat)

## Files Created/Modified

- `app/repositories/game_flaws_repository.py` - `FLAW_BLOB_COLUMNS` constant; new `delete_flaw_plies` and `bulk_update_game_flaw_rows` functions.
- `app/services/eval_drain.py` - `_classify_and_fill_oracle` rewritten as a 4-way diff/upsert; `_run_multipv2_pass` deleted (dead after the fold-in); `_full_drain_tick`'s now-redundant separate blob-write call removed.
- `app/routers/eval_remote.py` - `_snapshot_preserved_flaw_blobs`/`_restore_preserved_flaw_blobs` deleted; `_apply_atomic_submit` simplified to one `_classify_and_fill_oracle` call; unused `_run_multipv2_pass`/`Any` imports removed.

## Decisions Made

- **Preservation gate is `already_blobbed_plies` (allowed_pv_lines IS NOT NULL), not merely `existing_plies`.** My first implementation attempt gated "preserve" purely on "existing and not freshly blobbed," which broke scenario 5 (entry-pass rows replaced): a stale pre-seeded row with a NULL blob got its D-06 `[]` sentinel write skipped, leaving it incorrectly `None` instead of `[]`. The deleted `_snapshot_preserved_flaw_blobs` only ever captured rows where `allowed_pv_lines IS NOT NULL` — a ply with nothing worth preserving must take this pass's fresh value (including a fresh `[]` sentinel), same as any other fresh row. Fixed by adding an `already_blobbed_plies` query and intersecting it with `freshly_blobbed` before computing `preserve_plies`, exactly mirroring the deleted helper's own gate. Caught by the golden equivalence test itself (`scenario_5_entry_pass_replaced` failed before the fix, passed after).
- **Blob-line write folded into `_classify_and_fill_oracle` rather than staying a separate caller-side `_run_multipv2_pass` call.** The old ordering (classify/insert → caller calls `_run_multipv2_pass` → caller calls `_restore_preserved_flaw_blobs`) relied on the restore step running *last* to override a `[]` sentinel `_run_multipv2_pass` had just written for a preserve-ply. Since the whole point of R3 is removing the restore step, the blob write itself must be filtered *before* it runs (never write the sentinel over a preserve-ply's real blob in the first place) rather than write-then-undo. This required moving `_batch_update_flaw_pv_lines`'s invocation inside `_classify_and_fill_oracle`, which in turn made the separate `_run_multipv2_pass` wrapper dead code at both of its only two call sites — deleted.
- **`bulk_update_game_flaw_rows` added as a new generic repository function** rather than reusing `bulk_update_tactic_tags` for the fresh/preserve UPDATE branches — `bulk_update_tactic_tags`'s docstring and intended contract are scoped to "ONLY the 8 tactic-tag columns" (used by `retag_flaws.py`); the diff/upsert's UPDATE branches pass full rows (severity/tempo/phase/etc. too), which would have been a docstring/contract mismatch even though the underlying SQLAlchemy call is identical.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Preservation gate corrected from `existing_plies` to `already_blobbed_plies`**
- **Found during:** Task 1, running the golden equivalence test for the first time against the new diff/upsert.
- **Issue:** `scenario_5_entry_pass_replaced` failed — `ply=2 allowed_pv_lines: expected [], got None`. My initial implementation treated ANY existing-and-not-freshly-blobbed ply as "preserve" (skip the blob write and exclude tactic columns from the UPDATE), but a stale pre-seeded row with a NULL blob has nothing to preserve — the deleted `_snapshot_preserved_flaw_blobs` only ever captured rows gated on `allowed_pv_lines IS NOT NULL`, so such a row was always meant to receive this pass's fresh value (including a fresh D-06 `[]` sentinel), never skipped.
- **Fix:** Added an `already_blobbed_plies` query (`SELECT ply WHERE ... AND allowed_pv_lines IS NOT NULL`) and redefined `preserve_plies = already_blobbed_plies - freshly_blobbed`, used consistently for both the tactic-tag UPDATE split and the blob-write filter.
- **Files modified:** `app/services/eval_drain.py`.
- **Verification:** All 8 golden equivalence scenarios pass; full atomic-submit + drain suites green.
- **Committed in:** `1f752b51` (Task 1 commit — fixed before committing, not a separate follow-up commit).

---

**Total deviations:** 1 auto-fixed (Rule 1 — bug caught by the golden equivalence test itself before commit).
**Impact on plan:** No functional impact on the delivered design — the fix refines the preserve-gate condition to exactly match the deleted helper's semantics, which is precisely what the golden-snapshot equivalence proof (D-01) exists to catch. No scope creep.

## Issues Encountered

None beyond the deviation above, which the plan's own verification loop (golden equivalence test) caught and resolved before any commit landed.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- WRITE-03 (R3, the phase's one medium-risk deliverable) is complete. `_classify_and_fill_oracle` is now a fully self-contained diff/upsert; no caller-side compensation layer remains anywhere in the codebase.
- If Plan 05 (R7 module split, `eval_apply.py`) proceeds, `_classify_and_fill_oracle` and its new `delete_flaw_plies`/`bulk_update_game_flaw_rows` dependencies are ready to move as a unit — no further internal restructuring needed first.
- No blockers.

---
*Phase: 150-consolidate-write-path*
*Completed: 2026-07-04*

## Self-Check: PASSED

Verified both commit hashes (`1f752b51`, `9db5bfa5`) present in `git log`. Verified modified files (`app/repositories/game_flaws_repository.py`, `app/services/eval_drain.py`, `app/routers/eval_remote.py`) exist and contain the described changes (`FLAW_BLOB_COLUMNS`, `delete_flaw_plies`, `bulk_update_game_flaw_rows` present in game_flaws_repository.py; `_snapshot_preserved_flaw_blobs`/`_restore_preserved_flaw_blobs`/`_run_multipv2_pass` absent from the whole `app/` tree).
