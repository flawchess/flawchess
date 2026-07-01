---
phase: 147-persist-only-forcing-line-gated-tactic-tags-suppress-ungated
verified: 2026-07-01T21:45:00Z
status: human_needed
score: 9/9 must-haves verified (1 item routed to human verification, pre-flagged by the executor as HUMAN-UAT)
behavior_unverified: 0
overrides_applied: 0
human_verification:
  - test: "Run the upgraded worker against a live local dev backend and confirm a real atomic gated-write cycle: `docker compose -f docker-compose.dev.yml -p flawchess-dev up -d` + `uv run uvicorn app.main:app --reload`, queue at least one game for eval (fresh import or existing tier-1 explicit enqueue), then `uv run python scripts/remote_eval_worker.py --base-url http://localhost:8000 --once`."
    expected: "Logs show `Atomic-leased game_id=...` then `Atomic-submitted game_id=...: flaws_written=N, blobs_written=M`. Inspecting `game_flaws`/`game_positions` for that game afterward shows `full_evals_completed_at` and `full_pv_completed_at` both set, and any `tactic_motif` values reflect the forcing-line-gated result (never a raw/ungated value observable between the two markers)."
    why_human: "The current dev DB has zero pending `eval_jobs` rows and `EVAL_AUTO_DRAIN_ENABLED=false` blocks the tier-3 idle path locally, so `/atomic-lease` legitimately 204s end-to-end today — there is no queued tier-1/2/3 game to drive a real 200 lease→submit cycle. Manufacturing one via direct DB seeding would violate the project's 'no dev DB reset/seeding in plans' convention. This is a live network/DB/timing behavior that cannot be proven by static analysis; 147-VALIDATION.md's own Manual-Only Verifications table already lists this exact item."
---

# Phase 147: Persist only forcing-line-gated tactic tags — Verification Report

**Phase Goal:** Ensure `game_flaws.tactic_motif` is never persisted with raw, ungated (pre-forcing-line-gate) values. Part A (data-level): on the remote-submit path where blobs are deferred, write `tactic_motif = NULL` for cp-based flaws whose forcing-line gate can't yet run — keeping mate-adjacent (`pre_flaw_eval_cp IS NULL`) and D-06 `[]`-sentinel raw tags — so values self-heal when the tier-4 gated retag lands. Old-corpus data migration suppresses already-persisted ungated tags. Part B (worker pipeline): a versioned lease+submit endpoint pair and an upgraded fat-app.* fleet worker that submits full-ply evals + MultiPV-2 blobs together; the server runs its own authoritative `classify_game_flaws` with those blobs and writes flaws + forcing-line-gated tags + completion markers in one transaction, eliminating the ungated window at write time.

**Verified:** 2026-07-01T21:45:00Z
**Status:** human_needed
**Re-verification:** No — initial verification (post-code-review-fix)

## Context: prior code review

`147-REVIEW.md` (standard depth, 6 files) found 2 Criticals and 3 Warnings + 1 Info. Both Criticals were fixed in commits `5c1b97ac` (CR-02) and `0ba0c883` (CR-01/IN-01) before this verification ran. This verification independently re-traces both fixes against the reviewer's exact diagnosis and re-runs the relevant tests rather than trusting the fix commits' own claims.

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | A cp-based flaw (deferred blob) submitted through the remote path (`_apply_submit`) persists `tactic_motif = NULL`, not the raw motif | ✓ VERIFIED | `app/services/flaws_service.py:583` suppression predicate `blobs_pending and motif is not None and pv_blob is None and pre_flaw_eval_cp is not None`; `app/routers/eval_remote.py:312` passes `blobs_pending=True` at `_apply_submit`. `tests/services/test_flaws_service.py::TestClassifyTacticGatedBlobsPending` passes. |
| 2 | Mate-adjacent flaws (`pre_flaw_eval_cp IS NULL`) keep their raw tag under `blobs_pending=True` | ✓ VERIFIED | Same predicate requires `pre_flaw_eval_cp is not None`; unit test `test_blobs_pending_true_mate_adjacent_keeps_raw` passes. |
| 3 | D-06 `[]`-sentinel flaws keep their raw tag | ✓ VERIFIED | Predicate uses `pv_blob is None` (not falsy) so `[]` never matches; `test_blobs_pending_true_sentinel_empty_blob_keeps_raw` passes. |
| 4 | A subsequent `/flaw-blob-submit` fills the correctly-gated tag on a previously-suppressed flaw (self-heal) | ✓ VERIFIED | `tests/test_eval_worker_endpoints.py::test_submit_suppresses_cp_flaw_tag_then_blob_submit_self_heals` passes (re-ran: 7/7 atomic-adjacent tests pass; this specific test file collection confirmed green in full-suite run). |
| 5 | Old-corpus migration suppresses already-persisted ungated cp tags while preserving mate-adjacent + `[]`-sentinel rows, and is idempotent | ✓ VERIFIED | `alembic/versions/20260701_190758_eb341e836ee9_...py` — batched `DO $$ ... WHILE rows_updated > 0` on composite PK, joined to `game_positions`, gated per orientation. `tests/test_migration_suppress_ungated_tactic_tags.py` seeds all carve-outs + idempotency re-run; part of the 3099-test green full-suite run. |
| 6 | Fat games (>1024 walkable flaw-blob positions) sentinel cleanly on `/flaw-blob-lease` (204), never 500, reach zero NULL-blob flaws, tags unchanged | ✓ VERIFIED | `app/routers/eval_remote.py:914` `elif len(lease_positions) > MAX_SUBMIT_EVALS:` branch confirmed present and distinct from the empty-lease branch; `test_blob_lease_over_cap_sentinels_all_null_blob_flaws` passes. |
| 7 | New atomic lease/submit schema pair + `/atomic-lease` endpoint exist, operator-token gated, over-cap safe, reuse `claim_eval_job` unchanged | ✓ VERIFIED | `app/schemas/eval_remote.py`: `AtomicLeaseResponse`, `AtomicSubmitEval`, `AtomicBlobNode`, `AtomicSubmitRequest` (incl. `worker_schema_version`, two independently-capped lists, `MAX_SUBMIT_BLOB_NODES=1024`), `AtomicSubmitResponse` all present. `app/routers/eval_remote.py:506` `POST /atomic-lease`. `TestAtomicLeaseEndpoint` (5 tests) passes. |
| 8 | `/atomic-submit` writes evals → server-authoritative `classify_game_flaws`(with worker blobs) → blobs → completion markers in ONE transaction; tags are gated the instant `full_evals_completed_at` is set; skew→NULL; non-flaw blob dropped; foreign token rejected; over-cap can't reach partial write | ✓ VERIFIED | `app/routers/eval_remote.py:1100` `_apply_atomic_submit` — single `write_session`; re-derives valid token range and rejects out-of-range (422); `_classify_and_fill_oracle(blobs_pending=True)` (documented, provably-safe deviation, traced independently — see below). `TestAtomicSubmitEndpoint` (7 tests, re-ran directly: **7 passed**). |
| 9 | Upgraded worker: new atomic rung leases via `/atomic-lease`, evals MultiPV-1 (unchanged `_eval_positions`), computes a correct local flaw-ply hint via `_run_all_moves_pass`, computes MultiPV-2 blobs only for hinted plies, submits atomically; old `/lease`+`/submit` code paths remain in the file unmodified | ✓ VERIFIED | `scripts/remote_eval_worker.py`: `_hint_flaw_plies`, `_build_blob_walk_targets`, `_eval_atomic_blob_nodes`, `_eval_atomic_game`, `_handle_atomic_response`, `WORKER_SCHEMA_VERSION=1` all present; rungs 1/3 rewired to atomic path, `_handle_full_ply_response`/`_eval_positions` left in file unmodified. `tests/test_remote_eval_worker.py` re-ran directly: **24 passed**. |
| 10 | A real end-to-end atomic gated-write cycle (200 lease → eval → blob → submit → observably-gated tags + both completion markers) has been exercised against a live dev backend | ⚠️ ROUTED TO HUMAN | No queued tier-1/2/3 game exists in the current dev DB (`eval_jobs` has zero pending rows, `EVAL_AUTO_DRAIN_ENABLED=false` blocks tier-3 idle locally) — `/atomic-lease` legitimately 204s. Executor already flagged this as HUMAN-UAT in 147-06-SUMMARY.md, consistent with 147-VALIDATION.md's Manual-Only Verifications table and the project's "no dev DB reset/seeding in plans" rule. See Human Verification below. |

**Score:** 9/9 statically/behaviorally verifiable truths verified; 1 truth requires a live human-run e2e check (pre-declared, not a code gap).

### Code Review Fix Verification (independent re-trace, not trusting SUMMARY/fix-commit claims)

**CR-01 (`_apply_atomic_submit` unconditional completion stamping):** Confirmed FIXED. `git show 0ba0c883` shows `failed_ply_count` is now captured from `_apply_full_eval_results` (previously discarded) and branches into the same Path A/B/C SEED-045 bounded-retry structure as `_apply_submit`: Path A (no holes) stamps; Path B (holes, under `MAX_EVAL_ATTEMPTS`) increments `full_eval_attempts` and leaves pending, no stamp; Path C (holes, cap reached) stamps with a `sentry_sdk.capture_message` warning (variable data via `set_context`, not embedded in the message, per CLAUDE.md). `AtomicSubmitResponse` gained `failed_ply_count`/`stamp_complete` fields, closing the observability gap the reviewer flagged. `_signal_flaw_completion` is now gated on `stamp_complete` (closes IN-01 in the same commit). Tests `test_atomic_submit_holed_batch_under_cap_leaves_pending` and `test_atomic_submit_holed_batch_at_cap_stamps_with_sentry_warning` exist and pass (re-ran: `-k atomic_submit` → 7/7 passed, includes these two plus the 5 from 147-05).

**CR-02 (`_hint_flaw_plies` off-by-one):** Confirmed FIXED. `git show 5c1b97ac` shows the exact fix the reviewer proposed: `hint_positions` now loops `for row_ply in range(max_ply)` (one hint row per real move) and reads `eval_by_ply.get(row_ply + 1)` — the `+1` shift the reviewer traced against `_post_move_eval`'s post-move convention. `tests/test_remote_eval_worker.py` re-ran directly: 24/24 pass, including the updated hint-ply tests.

**Full backend suite** (`uv run pytest -n auto`) re-ran directly by this verifier: **3099 passed, 18 skipped**, no failures. `uv run ty check app/ tests/`: zero errors. `uv run ty check app/ tests/ scripts/`: 4 pre-existing, unrelated diagnostics confirmed confined to `scripts/seed_openings.py`/`scripts/seed_cohort_cdf.py` (not touched by this phase). `uv run ruff check app/ tests/ scripts/`: all checks passed. No `TBD`/`FIXME`/`XXX` debt markers found in any of the 6 files this phase touched.

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `app/services/flaws_service.py` | `blobs_pending` param + suppression branch, threaded through `classify_game_flaws`/`_build_flaw_record`/`_classify_tactic_gated` | ✓ VERIFIED | Confirmed at lines 534, 583, 598, 632/645, 907, 983. |
| `app/services/eval_drain.py` | `blobs_pending` param on `_classify_and_fill_oracle`; `_derive_atomic_sentinel_lines` for 147-05 | ✓ VERIFIED | Confirmed at line 683 + forwarded 759; `_derive_atomic_sentinel_lines` present per 147-05-SUMMARY and grep. |
| `app/routers/eval_remote.py` | `_apply_submit` passes `blobs_pending=True`; `/flaw-blob-lease` over-cap `elif`; `/atomic-lease` + `/atomic-submit` routes; `_apply_atomic_submit` Path A/B/C | ✓ VERIFIED | All confirmed present and wired (grep evidence above). |
| `app/schemas/eval_remote.py` | `AtomicLeaseResponse`/`AtomicSubmitRequest`/`AtomicSubmitEval`/`AtomicBlobNode`/`AtomicSubmitResponse`, `MAX_SUBMIT_BLOB_NODES`, `worker_schema_version`, `failed_ply_count`/`stamp_complete` | ✓ VERIFIED | All classes/fields confirmed present via grep. |
| `alembic/versions/20260701_190758_eb341e836ee9_...py` | Batched, index-driven old-corpus suppression migration, no-op downgrade | ✓ VERIFIED | Confirmed; `uv run alembic upgrade head` already applied in this repo's migrated-template DB (part of the green full-suite run's per-run-DB isolation). |
| `scripts/remote_eval_worker.py` | Atomic rung (`_handle_atomic_response`, `_eval_atomic_game`, `_hint_flaw_plies`, `_build_blob_walk_targets`, `_eval_atomic_blob_nodes`), `WORKER_SCHEMA_VERSION` | ✓ VERIFIED | All confirmed present via grep; CR-02 fix confirmed in place. |
| `tests/services/test_flaws_service.py`, `tests/test_eval_worker_endpoints.py`, `tests/test_migration_suppress_ungated_tactic_tags.py`, `tests/test_remote_eval_worker.py` | Unit + integration tests for every must-have | ✓ VERIFIED | Re-ran directly by this verifier (not trusting SUMMARY claims): `-k atomic_submit` → 7/7 pass; `test_remote_eval_worker.py` → 24/24 pass; full suite → 3099 passed, 18 skipped. |

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| `_apply_submit` | `_classify_and_fill_oracle(blobs_pending=True)` → `classify_game_flaws` → `_build_flaw_record` → `_classify_tactic_gated` | direct call chain | ✓ WIRED | Confirmed by grep chain above; behavior proven by passing unit + router tests. |
| `flaw_blob_lease` over-cap branch | `_batch_update_flaw_pv_lines({ply: ([], [])})` for all NULL-blob flaw plies | direct call, own write session | ✓ WIRED | Confirmed at `eval_remote.py:914+`; test proves zero NULL-blob flaws remain after. |
| `atomic_lease_eval_game` | `claim_eval_job` (unchanged tier-1>2>3) → `AtomicLeaseResponse` | direct call | ✓ WIRED | Confirmed; `TestAtomicLeaseEndpoint` passes. |
| `_apply_atomic_submit` | `_apply_full_eval_results` → `_classify_and_fill_oracle` → `_run_multipv2_pass` → Path A/B/C completion stamping | single `write_session`, one commit | ✓ WIRED | CR-01 fix confirmed; `failed_ply_count` now threads through to the branch; `stamp_complete` gates both the completion markers and `_signal_flaw_completion`. |
| worker `_eval_atomic_game` | `_hint_flaw_plies` (CR-02-fixed) → `_build_blob_walk_targets` → `_eval_atomic_blob_nodes` → POST `/atomic-submit` | direct call chain | ✓ WIRED | Confirmed; ply-shift fix in place; 24/24 worker tests pass. |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| SEED-074 | 147-01 through 147-06 (all 6 plans) | Persist only forcing-line-gated tactic tags; suppress ungated writes; atomic worker pipeline | ✓ SATISFIED (9/10 truths; 1 human-verification item) | See Observable Truths table above. Not a REQUIREMENTS.md row — entered via roadmap evolution per task framing; no orphaned requirements (REQUIREMENTS.md has no Phase 147 section to cross-reference against). |

### Anti-Patterns Found

None. No `TBD`/`FIXME`/`XXX`/`HACK`/`PLACEHOLDER` markers, no stub returns, no hardcoded-empty data flowing to persisted state, in any of the 6 files this phase modified.

### Warnings carried forward as tracked debt (not phase-goal blockers, per task framing)

- **WR-01** (migration batch CTE can select-but-not-update rows in an unreachable-today edge case) — confirmed still present in `alembic/versions/20260701_190758_eb341e836ee9_...py` (predicate structure unchanged since the review). Not reachable via any current write path (organic `blob_map` entries are always NULL/NULL or non-NULL/non-NULL together); becomes reachable only if a future write path assembles an asymmetric blob_map entry. Recommend a follow-up ticket, not a phase blocker.
- **WR-02** (`AtomicSubmitResponse.flaws_written` can report a stale snapshot count on the early-return oracle path rather than a delta) — confirmed still present (`flaws_written = await write_session.scalar(...)` at line 1257, unconditional COUNT). Cosmetic/observability issue, not a correctness issue for tag gating.
- **WR-03** (`body.evals` ply values not explicitly range-checked, unlike `blob_nodes` tokens) — confirmed still present; reviewer's own analysis states this is inert by construction (dict `.get()` lookup). Documentation-only fix recommended, not a phase blocker.

## Human Verification Required

### 1. Live dev-first atomic gated-write end-to-end cycle

**Test:** With the dev DB and backend running, queue at least one game for eval (fresh import or existing tier-1 explicit-enqueue flow), then run `uv run python scripts/remote_eval_worker.py --base-url http://localhost:8000 --once`.

**Expected:** Logs show a real 200 `/atomic-lease` → eval → blob computation → `/atomic-submit` cycle (`Atomic-leased game_id=...` then `Atomic-submitted game_id=...: flaws_written=N, blobs_written=M`). Inspecting the game's `game_flaws`/`game_positions` rows afterward confirms `full_evals_completed_at` and `full_pv_completed_at` are both set, and `tactic_motif` values reflect the forcing-line-gated result — never a raw/ungated value observable between the two markers.

**Why human:** The current dev DB has zero pending `eval_jobs` rows and `EVAL_AUTO_DRAIN_ENABLED=false` blocks the tier-3 idle path locally, so `/atomic-lease` legitimately 204s today — there is no queued job to drive a real write cycle. This is live network/timing/DB-state behavior, not something static analysis or the existing unit/integration test suite (which mocks the HTTP layer and seeds synthetic rows directly) can substitute for. Per CLAUDE.md's "no dev DB reset/seeding in plans" rule, manufacturing a queued job via direct seeding was correctly avoided by the executor rather than done here.

## Gaps Summary

No gaps. All 9 statically/behaviorally verifiable must-haves across all 6 plans are confirmed present, correctly wired, and covered by passing tests that this verifier re-ran directly (not merely cited from SUMMARY.md). Both Critical review findings (CR-01, CR-02) are confirmed fixed with code that matches the reviewer's own diagnosis and recommended fix, and the fix-specific tests pass. The 3 open Warnings (WR-01/02/03) are non-blocking tracked debt, unchanged since the review, and do not affect the core "no ungated tag is ever persisted" invariant. The single open item is a pre-declared, legitimately environment-blocked human-run e2e smoke test — not a code or logic gap.

---

_Verified: 2026-07-01T21:45:00Z_
_Verifier: Claude (gsd-verifier)_
