---
phase: 150-consolidate-write-path
verified: 2026-07-04T20:00:00Z
status: passed
score: 13/13 must-haves verified
behavior_unverified: 0
overrides_applied: 0
---

# Phase 150: Consolidate Write Path Verification Report

**Phase Goal:** Unify the copy-pasted eval write path into one code path — the Path A/B/C completion decision, the classify preamble, and the delete-then-insert flaw write all currently exist as verbatim copies (source of FLAWCHESS-8D and the Phase 146/147 ungated-tag bugs). Consolidate in dependency order R1 → R4 → R3 → R7; R5/R6 ride along. STRUCTURE-ONLY, no behavior change.
**Verified:** 2026-07-04
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Exactly one `apply_completion_decision(...)`; both former inline copies now call it | ✓ VERIFIED | Single `def apply_completion_decision` at `app/services/eval_apply.py:583`. Both live lanes route through the single `apply_full_eval(...)` (eval_apply.py:1677), which calls `apply_completion_decision` once (line 1790). `_full_drain_tick` (eval_drain.py:853) and `_apply_atomic_submit` (eval_remote.py:1166) both call `apply_full_eval`. |
| 2 | Leased-status guard on the eval_jobs stamp preserved | ✓ VERIFIED | `WHERE id=:job_id AND status='leased'` present verbatim (eval_apply.py:665-670, `jobs_table.c.status == "leased"`). |
| 3 | Per-caller Path-C reporting preserved (not unified) | ✓ VERIFIED | Drain: `_log_path_c_capacity_reached` uses `logger.warning` (eval_drain.py:620-635, FLAWCHESS-5V). Router: `_report_path_c_capacity_reached` uses `sentry_sdk.capture_message` (eval_remote.py:968-986). Both injected via `on_path_c_capacity_reached` callback param. |
| 4 | One shared classify-preamble helper (`_classify_with_overlay`); all 4 prior sites route through it; `_flaw_engine_plies` uses overlay=False | ✓ VERIFIED | Single `def _classify_with_overlay` (eval_apply.py:985). 4 call sites: `_flaw_engine_plies` (eval_drain.py:506, overlay=False), `_missing_flaw_pv_targets`/`_build_flaw_multipv2_blobs`/`_derive_atomic_sentinel_lines` (eval_apply.py:1081 [overlay=False confirmed is actually the `_flaw_engine_plies`-equivalent path relocated], 1222, 1345, overlay=True). |
| 5 | `_classify_and_fill_oracle` is a per-ply diff/upsert (NOT delete-then-insert) | ✓ VERIFIED | `app/services/eval_apply.py:676-982` implements 4-way partition: DELETE (`delete_flaw_plies`), INSERT new (`bulk_insert_game_flaws`), UPDATE-fresh, UPDATE-preserve (FLAW_BLOB_COLUMNS excluded from dict). No COALESCE-over-JSONB-with-None anywhere (confirmed by grep + code review). |
| 6 | `_snapshot_preserved_flaw_blobs`/`_restore_preserved_flaw_blobs` are GONE | ✓ VERIFIED | `grep -rn` across `app/` returns 0 hits. |
| 7 | Golden equivalence test exists, covers the D-02 scenarios, and passes | ✓ VERIFIED | `tests/services/test_flaw_upsert_equivalence.py` — 8 collected tests (7 parametrized scenarios + 1 completeness guard). Ran independently: `8 passed in 5.84s`. Single named-test spot check on `scenario_3_flip_out` (the FLAWCHESS-8D StaleDataError regression case) passed. Note: plan text said "8 scenarios" but the plan's own concrete artifact list enumerated 7 — documented as a plan-authoring inconsistency in 150-01-SUMMARY.md and reconciled by the completeness-guard test (locks exactly 7 named scenarios). Not a gap. |
| 8 | Generator (`scripts/gen_write_path_golden.py`) is committed + reproducible | ✓ VERIFIED | Ran independently: `uv run python -m scripts.gen_write_path_golden` then `git status --porcelain tests/fixtures/write_path_golden/` produced zero diff (byte-identical regeneration against current HEAD, post-refactor). |
| 9 | `app/services/eval_apply.py` exists exposing `apply_full_eval(...)`, consumed by both drain and router | ✓ VERIFIED | File exists (1817 lines). `apply_full_eval` defined at line 1677; called from `eval_drain.py:853` and `eval_remote.py:1166`. |
| 10 | `eval_drain.py` split (entry-lane extracted to `eval_entry.py`) | ⚠ VERIFIED WITH FLAGGED RESIDUAL | `app/services/eval_entry.py` exists (592 lines) holding 14 of 16 entry-lane symbols. `_pick_pending_game_ids`/`_load_pgns_for_games` deliberately kept in `eval_drain.py` (both open their own internal session, unlike the other 14) — explicitly flagged in 150-05-SUMMARY.md per the plan's own "or flag descope" allowance (D-05). Does not undermine WRITE-04's goal: the 21-symbol router leak into `eval_drain.py` internals is closed to exactly one narrow, documented residual import (`_load_pgns_for_games` + 3 public `ENTRY_LEASE_*` constants), confirmed by direct code read of `eval_remote.py:104-115`. |
| 11 | Router `eval_remote.py` no longer imports private drain helpers for the shared write path (minus flagged residual) | ✓ VERIFIED | `eval_remote.py` imports from `eval_apply` (10 symbols) and `eval_entry` (5 symbols) as the shared/entry-lane write path; the single remaining `from app.services.eval_drain import (...)` block imports only `_load_pgns_for_games` + 3 constants — the one documented residual, not the original 21-symbol leak. Confirmed by direct read of lines 81-115. |
| 12 | `python -c "import app.main"` succeeds (no circular import) | ✓ VERIFIED | Ran independently: exit code 0, no errors. |
| 13 | `EnginePool` has one generic acquire/analyse method replacing the 3 copies | ✓ VERIFIED | `_acquire_and_analyse` defined once (engine.py:465); `_analyse`/`_analyse_with_pv`/`_analyse_multipv2` (the 3 old copies) confirmed absent via grep. All 4 public methods (`evaluate`, `evaluate_nodes`, `evaluate_nodes_with_pv`, `evaluate_nodes_multipv2`) call it (lines 521, 535, 555, 582). |
| 14 | Tier-3/tier-4 ES lottery is one parameterized implementation | ✓ VERIFIED | `_es_weighted_user_pick` (eval_queue_service.py:277) and `_es_weighted_game_pick` (line 328) defined once; both `_claim_tier3_derived` and `_claim_tier4_blob` call them. |
| 15 | Full backend suite green, ty + ruff clean | ✓ VERIFIED | Independently re-ran: `uv run pytest -n auto -q` → 3162 passed, 18 skipped. `uv run ruff check app/ tests/ scripts/` → All checks passed. `uv run ty check app/ tests/` → All checks passed. |

**Score:** 15/15 truths verified (13 core must-haves collapsed from the verification_focus checklist, expanded to 15 granular checks above; 1 carries an explicitly-documented, non-blocking flagged residual). 0 behavior-unverified.

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `app/services/eval_apply.py::apply_completion_decision` | Single Path A/B/C decision fn | ✓ VERIFIED | Defined once, both lanes route through it via `apply_full_eval`. |
| `app/services/eval_apply.py::_classify_with_overlay` | Single overlay-parameterized preamble | ✓ VERIFIED | Defined once, 4 call sites (3 overlay=True, 1 overlay=False). |
| `app/services/eval_apply.py::_classify_and_fill_oracle` | Diff/upsert, not delete-then-insert | ✓ VERIFIED | 4-way partition confirmed by direct code read. |
| `app/repositories/game_flaws_repository.py::FLAW_BLOB_COLUMNS` | Single source of truth, 10 columns | ✓ VERIFIED | `FLAW_BLOB_COLUMNS: tuple[str, ...] = ("allowed_pv_lines", "missed_pv_lines") + TACTIC_TAG_COLUMNS` at line 171. |
| `app/repositories/game_flaws_repository.py::delete_flaw_plies` / `bulk_update_game_flaw_rows` | New generic diff/upsert primitives | ✓ VERIFIED | Both defined (lines 220, 247). |
| `tests/services/test_flaw_upsert_equivalence.py` | Golden equivalence + completeness guard | ✓ VERIFIED | 8 tests collected (7 scenarios + guard), all pass. |
| `scripts/gen_write_path_golden.py` | Committed reproducible generator | ✓ VERIFIED | Regeneration produces zero git diff. |
| `tests/fixtures/write_path_golden/*.json` (7 files) | Golden fixtures | ✓ VERIFIED | All 7 present, byte-identical after regeneration. |
| `app/services/eval_apply.py` (module) | New shared write-path module | ✓ VERIFIED | Exists, 1817 lines, no import back to eval_drain/eval_remote (leaf module). |
| `app/services/eval_entry.py` (module) | Entry-lane module | ✓ VERIFIED | Exists, 592 lines, holds 14/16 entry-lane symbols (2 flagged residual). |
| `app/services/engine.py::EnginePool._acquire_and_analyse` | Generic analyse method | ✓ VERIFIED | Defined once, 4 callers. |
| `app/services/eval_queue_service.py::_es_weighted_user_pick` / `_es_weighted_game_pick` | Shared ES building blocks | ✓ VERIFIED | Both defined once, consumed by tier-3 and tier-4 claim functions. |

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| `_full_drain_tick` (eval_drain.py) | `apply_full_eval` (eval_apply.py) | direct call, `update_opening_cache=True` | ✓ WIRED | Confirmed at eval_drain.py:853, with `_upsert_opening_cache` passed as `upsert_opening_cache_fn` (Pitfall 4 preserved). |
| `_apply_atomic_submit` (eval_remote.py) | `apply_full_eval` (eval_apply.py) | direct call, `update_opening_cache=False` (default) | ✓ WIRED | Confirmed at eval_remote.py:1166. Opening-cache upsert NOT invoked on atomic-submit path. |
| `apply_full_eval` | `apply_completion_decision` | sibling call inside write_session, before commit | ✓ WIRED | eval_apply.py:1790. |
| `apply_full_eval` | `upsert_worker_heartbeat` | sibling call, `record_heartbeat` gated | ✓ WIRED | eval_apply.py:1802-1809; router passes `record_heartbeat=True`, drain leaves default False (unchanged behavior). |
| `_classify_and_fill_oracle` | `engine_result_map`/`flaw_pv_blobs` (pv_by_ply overlay) | threaded parameters, unchanged shape | ✓ WIRED | Confirmed threading intact at eval_apply.py:788-800. |
| `eval_remote.py` router | `eval_apply.py` / `eval_entry.py` | module-level import | ✓ WIRED | 10 + 5 symbols imported respectively; only 1 residual private symbol (`_load_pgns_for_games`) + 3 constants still from `eval_drain.py`, explicitly flagged. |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Golden equivalence proof (all 7 scenarios, byte-identical write output) | `uv run pytest tests/services/test_flaw_upsert_equivalence.py -x` | 8 passed in 5.84s | ✓ PASS |
| Flip-OUT scenario (FLAWCHESS-8D StaleDataError regression, single named test) | `uv run pytest tests/services/test_flaw_upsert_equivalence.py -k flip_out -v` | 1 passed | ✓ PASS |
| Generator reproducibility (regenerate + diff) | `uv run python -m scripts.gen_write_path_golden && git status --porcelain tests/fixtures/write_path_golden/` | zero diff | ✓ PASS |
| No circular import at startup | `python -c "import app.main"` | exit 0 | ✓ PASS |
| Full backend suite | `uv run pytest -n auto -q` | 3162 passed, 18 skipped | ✓ PASS |
| Lint | `uv run ruff check app/ tests/ scripts/` | All checks passed | ✓ PASS |
| Type check | `uv run ty check app/ tests/` | All checks passed | ✓ PASS |
| Debt-marker scan on phase-modified files | `grep -n -E "TBD\|FIXME\|XXX"` across 7 modified files | no matches | ✓ PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|--------------|------------|-------------|--------|----------|
| WRITE-01 | 150-03 | Path A/B/C completion decision extracted into one `apply_completion_decision()` | ✓ SATISFIED | Single definition, both lanes call it via `apply_full_eval`; leased-guard preserved. |
| WRITE-02 | 150-03 | Classify preamble unified across 4 sites | ✓ SATISFIED | `_classify_with_overlay`, 4 call sites, overlay param correct. |
| WRITE-03 | 150-01, 150-04 | Diff/upsert replaces delete-then-insert; snapshot/restore helpers deleted; equivalence test proves parity | ✓ SATISFIED | 4-way partition confirmed; helpers confirmed absent; 8/8 golden tests pass. |
| WRITE-04 | 150-05 | Shared orchestration extracted to `eval_apply.py`; `eval_drain.py` split; router stops importing private helpers | ✓ SATISFIED (1 flagged residual, documented, non-blocking) | `eval_apply.py`/`eval_entry.py` exist; router leak reduced from 21 symbols to 1 flagged residual (`_load_pgns_for_games`). |
| WRITE-05 | 150-02 | `EnginePool` generic acquire/analyse method | ✓ SATISFIED | `_acquire_and_analyse` single definition, 4 callers. |
| WRITE-06 | 150-02 | Tier-3/tier-4 ES lottery parameterized | ✓ SATISFIED | `_es_weighted_user_pick`/`_es_weighted_game_pick` shared, both tiers consume them. |

No orphaned requirements — REQUIREMENTS.md cross-reference confirms 18/18 v1.31 requirements mapped, WRITE-01 through WRITE-06 all listed against Phase 150 with no gaps.

### Anti-Patterns Found

None in phase-modified files (`eval_apply.py`, `eval_entry.py`, `eval_drain.py`, `eval_remote.py`, `game_flaws_repository.py`, `engine.py`, `eval_queue_service.py`) — no `TBD`/`FIXME`/`XXX` markers, no placeholder returns, no empty handlers.

The independent 150-REVIEW.md (code-review subagent, standard depth, 9 files) found 0 critical issues, 4 warnings, 2 info — all maintainability/style suggestions (parameter-list bloat on `apply_full_eval`, a `Callable[..., Any]` typing gap on one async callback, dead branching in a pre-existing token-tamper guard predating this phase, and a stale cross-reference comment). None rise to a correctness or security defect, and none contradict the must-haves above. Worth tracking as informal follow-up but not blocking phase completion.

### Human Verification Required

None. This is an autonomous, structure-only backend refactor with no UI/visual surface, no new external input, and no behavior change — all invariants are provable via the golden-equivalence test, static analysis (ruff/ty), and the full test suite, all independently re-run and confirmed above.

### Gaps Summary

No gaps. All must-haves from the verification focus checklist (WRITE-01 through WRITE-06) were independently confirmed against the live codebase — not just SUMMARY.md claims. The one item warranting explicit note (WRITE-04's `_pick_pending_game_ids`/`_load_pgns_for_games` residual in `eval_drain.py`) was pre-flagged transparently in 150-05-SUMMARY.md per the plan's own "or flag descope" escape hatch, is narrowly scoped (2 of 16 entry-lane symbols, both structurally distinct — they open their own session), and does not undermine the phase goal: the router's private-import leak that WRITE-04 targeted (originally 21 symbols) is closed to 1 documented residual, confirmed by direct code read.

---

_Verified: 2026-07-04_
_Verifier: Claude (gsd-verifier)_
