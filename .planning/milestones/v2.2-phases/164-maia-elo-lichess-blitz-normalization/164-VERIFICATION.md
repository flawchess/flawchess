---
phase: 164-maia-elo-lichess-blitz-normalization
verified: 2026-07-11T13:00:00Z
status: passed
score: 13/13 must-haves verified
behavior_unverified: 0
overrides_applied: 0
re_verification:
  previous_status: gaps_found
  previous_score: 12/13
  gaps_closed:
    - "chess.com ratings no longer mis-condition Maia's move prediction (ROADMAP Phase 164 goal, applied to every reachable (platform, time_control_bucket) combination a real game can have) — Truth #13 / REVIEW.md WR-01"
  gaps_remaining: []
  regressions: []
---

# Phase 164: Maia ELO Lichess-blitz normalization — Verification Report

**Phase Goal:** Normalize player ratings to their Lichess-blitz equivalent (Maia-3's training scale) before setting the analysis-board Maia ELO slider default and per-player Maia ELO, so chess.com and Lichess-non-blitz ratings no longer mis-condition Maia's move prediction.
**Verified:** 2026-07-11 (re-verification, after gap-closure plan 164-04)
**Status:** passed
**Re-verification:** Yes — after gap closure (164-04)

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | `normalize_to_lichess_blitz` returns a Lichess-blitz-equivalent int for every convertible (platform, source_tc) triple | ✓ VERIFIED | Unchanged from prior verification; `app/services/chesscom_to_lichess.py:318-376`, dispatch covers chess.com{blitz,bullet,rapid,**classical→rapid**} + lichess{bullet,rapid,classical}; 56 tests green, ran directly |
| 2 | Every non-convertible input (chess.com daily/correspondence, lichess correspondence, out-of-range) returns `None`, never an extrapolated guess | ✓ VERIFIED | Re-scoped by 164-04: chess.com classical is now CONVERTIBLE (no longer in this truth's set). `test_normalize_to_lichess_blitz_correspondence_returns_none_chesscom`/`_lichess`, out-of-range parametrize — all pass |
| 3 | Inverting Table 2's classical column on rating=1935 returns the lowest tied anchor (1500) | ✓ VERIFIED | Unchanged; `test_invert_table2_column_classical_tie_returns_lowest_anchor`; ran directly, passes |
| 4 | Inverting Table 2's classical column above its last non-None row returns `None` instead of raising | ✓ VERIFIED | Unchanged; `test_invert_table2_column_classical_none_gap_returns_none`; ran directly, passes |
| 5 | `GET /api/library/games/{game_id}` returns a `GameFlawCard` carrying `white_rating_lichess_blitz`/`black_rating_lichess_blitz` alongside unchanged raw `white_rating`/`black_rating` | ✓ VERIFIED | Unchanged; `app/schemas/library.py:106-107`; `_build_card` (`library_service.py:530-564`) computes and passes them |
| 6 | A chess.com blitz game's normalized field holds the Lichess-blitz-equivalent (higher) value while the raw field still holds the original rating | ✓ VERIFIED | Unchanged; `test_chesscom_blitz_card_has_higher_normalized_rating` (1500 → 1780); ran directly, passes |
| 7 | A chess.com daily / lichess correspondence game gets `None` for both normalized fields | ✓ VERIFIED | Unchanged; `test_correspondence_game_card_has_none_normalized_ratings` (chess.com Daily, `"1/172800"`, classical bucket) still asserts `None`/`None` — confirms the `is_correspondence` guard still runs FIRST and is untouched by the classical→rapid fix; ran directly, passes |
| 8 | A game with NULL ratings or NULL `time_control_bucket` gets `None` for the normalized fields without raising | ✓ VERIFIED | Unchanged; `test_null_rating_card_has_none_normalized_ratings`; ran directly, passes |
| 9 | In game mode, `deriveRawDefault` returns the mover-color's `*_lichess_blitz` value when present | ✓ VERIFIED | Unchanged; `useMaiaEloDefault.ts:83-87`; vitest 11/11 pass (ran directly) |
| 10 | When the mover-color's `*_lichess_blitz` value is null/absent, `deriveRawDefault` falls back to raw `white_rating`/`black_rating` | ✓ VERIFIED | Unchanged; `??` fallback at same lines; vitest null-fallback case passes. Fallback still exists as designed — it is now reached far less often (only true correspondence/daily games), which is exactly the intended narrowing |
| 11 | Free-play behavior and the ladder clamp/`userOverrodeRef` are unchanged | ✓ VERIFIED | Unchanged; `git diff` for 164-04 touches zero frontend files (confirmed: `git diff --stat c8e07345..ea5249a2 -- app/ tests/ frontend/` shows only 3 backend files) |
| 12 | Lichess non-blitz (bullet/rapid/classical) ratings no longer mis-condition Maia's move prediction | ✓ VERIFIED | Unchanged; all 3 lichess non-blitz paths invert through `_invert_table2_column` then `_interp_blitz_to_lichess`; dedicated tests pass |
| 13 | chess.com ratings no longer mis-condition Maia's move prediction, across **every** real-world `(platform, time_control_bucket)` combination a game can have | ✓ VERIFIED (gap closed) | `app/services/chesscom_to_lichess.py:362-369` — chess.com `classical` (non-correspondence) now maps to `effective_tc = "rapid"` before calling `convert_chesscom_to_lichess(rating, effective_tc, "blitz")`, returning a non-None converted value instead of `None`. Read the function body directly (not SUMMARY claims). Confirmed by 3 independent evidence points: (1) unit test `test_normalize_to_lichess_blitz_chesscom_classical_maps_to_rapid` (renamed from `_returns_none`, asserts `result == convert_chesscom_to_lichess(1500, "rapid", "blitz")` and `is not None`) passes; (2) new integration test `test_chesscom_classical_noncorrespondence_card_has_normalized_rating` (seeds `time_control_bucket="classical"`, `time_control_str="1800+30"` — no Daily `/` separator) asserts both card fields equal the rapid-scale conversion, not raw 1500; (3) sibling correspondence test `test_normalize_to_lichess_blitz_correspondence_returns_none_chesscom` and integration test `test_correspondence_game_card_has_none_normalized_ratings` (chess.com Daily `"1/172800"`) still assert `None`, proving the `is_correspondence` guard at line 360 still runs first and chess.com Daily is unaffected |

**Score:** 13/13 truths verified (0 partial/failed — the single prior gap is closed)

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `app/services/chesscom_to_lichess.py::normalize_to_lichess_blitz` | chess.com classical (non-correspondence) maps to rapid-scale conversion via typed `effective_tc` | ✓ VERIFIED | Lines 362-369; `effective_tc: ChessComSourceTC = "rapid" if source_tc == "classical" else source_tc` then `return convert_chesscom_to_lichess(rating, effective_tc, "blitz")`. Docstring (lines 335-344) updated to describe the new behavior and rationale |
| `tests/services/test_chesscom_to_lichess.py` | Renamed test asserting classical→rapid conversion | ✓ VERIFIED | Lines 444-451, `test_normalize_to_lichess_blitz_chesscom_classical_maps_to_rapid`; old name `chesscom_classical_returns_none` confirmed absent (`grep -c` returns 0). Sibling correspondence test at 454-460 unchanged |
| `tests/services/test_library_service.py::TestGetLibraryGame` | New integration test for chess.com classical-bucket, non-correspondence game | ✓ VERIFIED | Lines 1113-1156, `test_chesscom_classical_noncorrespondence_card_has_normalized_rating`; asserts converted (non-raw) values for both `white_rating_lichess_blitz`/`black_rating_lichess_blitz`, raw ratings unchanged |

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| `normalize_to_lichess_blitz`'s classical→rapid mapping | `_BUCKET_TO_SOURCE_TC` convention | Same `{"classical": "rapid", ...}` mapping now used on both the SQL composed-grid path and the Maia-normalization path | ✓ WIRED | Confirmed by code read: `effective_tc` mirrors the existing convention referenced in the docstring; both paths now agree |
| `is_correspondence` short-circuit (line 360) | chess.com classical→rapid branch (line 362) | Guard runs first, unconditionally, before the platform branch | ✓ WIRED | Confirmed by code read (line order) and by both correspondence tests (unit + integration) still passing with `None` |
| `_build_card` (`library_service.py`) | `normalize_to_lichess_blitz` fix | New card fields for a classical, non-correspondence chess.com game now carry the converted value, reaching the frontend | ✓ WIRED | `test_chesscom_classical_noncorrespondence_card_has_normalized_rating` exercises the full path from DB row → `get_library_game` → `GameFlawCard`, asserting non-raw converted values |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Backend converter unit suite | `uv run pytest tests/services/test_chesscom_to_lichess.py -q` | `56 passed in 3.72s` | ✓ PASS |
| Library service integration tests (`TestGetLibraryGame`, incl. new classical→rapid test) | `uv run pytest tests/services/test_library_service.py -k "TestGetLibraryGame" -q` | `7 passed, 32 deselected` | ✓ PASS |
| Backend type check | `uv run ty check app/services/chesscom_to_lichess.py` | `All checks passed!` | ✓ PASS |
| Full backend suite (regression check) | `uv run pytest -n auto -q` | `3203 passed, 18 skipped` | ✓ PASS |
| Frontend hook tests (regression check, no files touched by 164-04) | `npx vitest run src/hooks/__tests__/useMaiaEloDefault.test.ts` | `11 passed (11)` | ✓ PASS |
| Old test name removed | `grep -c 'chesscom_classical_returns_none' tests/services/test_chesscom_to_lichess.py` | `0` (only `_maps_to_rapid` present) | ✓ PASS |
| Commits exist | `git show --stat c4b6d0b3 914e896c db41a079` | All 3 commits present with expected file diffs | ✓ PASS |
| Scope confinement | `git diff --stat c8e07345..ea5249a2 -- app/ tests/ frontend/` | Only `app/services/chesscom_to_lichess.py`, `tests/services/test_chesscom_to_lichess.py`, `tests/services/test_library_service.py` touched (+ SUMMARY docs) | ✓ PASS |

All commands above were re-run directly by the verifier in this session, not taken from SUMMARY.md claims.

### Requirements Coverage

| Requirement | Source Plan(s) | Description | Status | Evidence |
|-------------|----------------|--------------|--------|----------|
| SEED-093 | 164-01, 164-02, 164-03, 164-04 | Normalize player ratings to Lichess-blitz equivalent before seating Maia's ELO default/slider | ✓ SATISFIED | Fully satisfied across all platforms and TC buckets: lichess (all TCs), chess.com blitz/bullet/rapid, and now chess.com classical (non-correspondence, via 164-04's rapid mapping). Only true correspondence/Daily games (both platforms) intentionally return `None` and fall back to raw — this is the correct, narrow residual scope, not a gap |

No orphaned requirements. `.planning/seeds/SEED-093-maia-elo-lichess-blitz-normalization.md` is the seed of record.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `app/services/chesscom_to_lichess.py:525-534` (`_invert_table2_column`) | — | Relies on unasserted dict-iteration order + column monotonicity for `bisect` correctness (no `assert`, unlike sibling `_invert_intra_tc`) | ℹ️ Info (164-REVIEW.md WR-02, carried forward, not addressed by 164-04 — out of this gap-closure plan's scope) | Not a live defect for the current snapshot; latent fragility if a future ChessGoals refit reorders rows or dips non-monotonically. Does not affect current goal achievement. |
| `app/services/chesscom_to_lichess.py:362-363` (lichess-blitz identity branch) | — | Returns `rating` unbounded, breaking the module's "refuse rather than guess" range-check convention | ℹ️ Info (164-REVIEW.md IN-01, carried forward) | Mitigated downstream by `clampToLadderBounds` and `nearestByElo`; not a live defect. |
| `app/schemas/library.py:164-165` (`FlawListItem`) | — | Carries raw ratings only, no normalized fields | ℹ️ Info (164-REVIEW.md IN-03, carried forward) | Consistent with current design; flagged for future awareness only. |

No `TBD`/`FIXME`/`XXX`/`TODO`/`HACK`/`PLACEHOLDER` debt markers found in the 3 files 164-04 modified (scanned directly).

### Human Verification Required

None required. The gap-closure fix is a pure-function conversion-branch change with full unit + integration test coverage; no state-transition, cancellation, or runtime-only behavior is asserted by any truth.

### Gaps Summary

**All 13 observable truths are now fully verified against the actual codebase.** The single gap from the prior verification run (Truth #13 / REVIEW.md WR-01 — chess.com classical-bucketed, non-correspondence games falling back to the raw un-normalized rating) is closed:

- `normalize_to_lichess_blitz`'s chess.com branch (`app/services/chesscom_to_lichess.py:362-369`) now maps `classical` → a typed `effective_tc = "rapid"` before calling `convert_chesscom_to_lichess`, matching the module's own `_BUCKET_TO_SOURCE_TC` convention already used by the SQL composed-grid pipeline. This was confirmed by reading the function body directly, not by trusting 164-04-SUMMARY.md's claims.
- The `is_correspondence` short-circuit (line 360) still runs first and is untouched — chess.com Daily / any correspondence game (either platform) still returns `None`. Confirmed both by code read (guard precedes the platform branch) and by both the pre-existing unit test and the pre-existing integration test for the correspondence case still passing unchanged.
- The renamed/inverted unit test (`test_normalize_to_lichess_blitz_chesscom_classical_maps_to_rapid`) exists; the old `_returns_none` name is confirmed absent via `grep -c`.
- The new integration test (`test_chesscom_classical_noncorrespondence_card_has_normalized_rating`) exists in `TestGetLibraryGame`, seeds a non-correspondence classical-bucket chess.com game (`"1800+30"`), and asserts the serialized card's normalized fields hold the converted (rapid-scale) value rather than `None` or the raw rating.
- Full backend suite (3203 passed, 18 skipped) and `ty check` (clean) re-run directly by the verifier confirm no regressions were introduced. Frontend hook tests (11/11) re-run directly confirm the previously-verified frontend truths (9-11) are unaffected — consistent with 164-04 touching zero frontend files.

No remaining gaps. No new gaps introduced by the fix (chess.com bullet/blitz/rapid paths, lichess paths, and the correspondence guard were all spot-checked and are unchanged).

---

_Verified: 2026-07-11_
_Verifier: Claude (gsd-verifier)_
