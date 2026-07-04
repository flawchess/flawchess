---
phase: 148-pipeline-tactic-correctness-fixes-code-review-2026-07-02
verified: 2026-07-04T09:18:15Z
status: passed
score: 7/7 must-haves verified
behavior_unverified: 0
overrides_applied: 0
---

# Phase 148: Pipeline & tactic correctness fixes (code-review 2026-07-02) Verification Report

**Phase Goal:** Fix five silent-data-loss / production-only-correctness defects from the
2026-07-02 code review, each with tests + a verify loop: (1) tactic `has_forced_mate`
no-op → deep mates never tag + `fen_map` `board_fen()` drops ep/castling state; (2)
entry-ply drain stamps `evals_completed_at` even on a dead pool → mirror the WR-05
all-fail circuit breaker; (3) quintile significance test treats overlapping cohorts as
independent → add the covariance term; (4) one malformed platform game aborts the whole
import → per-game try/except + skip + aggregated Sentry; (5) entry-submit batch-scoping
minimum guard `entry_eval_lease_expiry > now()`.

**Verified:** 2026-07-04T09:18:15Z
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Traceability Spine (ITEM-1..5, per CONTEXT.md / D-06)

No `REQUIREMENTS.md` mapping exists for Phase 148 (`phase_req_ids null`) and the phase
does not carry ROADMAP `success_criteria` bullets beyond the prose Goal line, so the
todo-derived ITEM-1..5 spine (locked in 148-CONTEXT.md) is the traceability substitute
per the phase brief. Every plan's `requirements:` frontmatter was cross-checked against
this spine:

| Item | Plan | Files | Status |
|------|------|-------|--------|
| ITEM-1 | 148-01 | `tactic_detector.py`, `flaws_service.py` | ✓ present, plus CR-01 post-review fix |
| ITEM-2 | 148-02 | `eval_drain.py`, `engine.py` | ✓ present |
| ITEM-3 | 148-03 | `endgame_service.py`, `score_confidence.py` | ✓ present |
| ITEM-4 | 148-04 | `chesscom_client.py`, `lichess_client.py` | ✓ present |
| ITEM-5 | 148-02 | `eval_remote.py` | ✓ present |

All five items accounted for across the 4 plans (D-06 seam: (a) tactics=1, (b)
eval-lease=2+5, (c) stats=3, (d) import=4). No orphaned item.

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Item 1a (D-01): a truncated forced-mate PV (`has_forced_mate=True`, PV capped at `PV_CAP_PLIES`) tags generic `TacticMotifInt.MATE` instead of silently returning `None`; the same PV with the flag off still returns `None` | ✓ VERIFIED | `app/services/tactic_detector.py:2504` (`if has_forced_mate and not boards[-1].is_checkmate():`); `tests/services/test_tactic_detector.py::TestHasForcedMateFallback` (`test_truncated_mate_with_flag_tags_mate`, `test_truncated_mate_without_flag_returns_none`) — both pass in the full suite run |
| 2 | Item 1b (D-02): `fen_map` stores full `board.fen()` (side-to-move, castling, en-passant), not `board_fen()`; ep-capture flaws replay without a parse error; Zobrist/position-comparison call sites untouched | ✓ VERIFIED | `app/services/flaws_service.py:334,338` (`board.fen()`, was `board.board_fen()`); `TestFenMapEpCapture` (2 tests) pass; `grep -n "board.board_fen()"` shows no remaining call inside `_recompute_fen_map`; persisted `FlawRecord.fen`/`game_flaws.fen` column preserved piece-placement-only via split-back at construction site (line ~131) |
| 3 | CR-01 post-review fix: `has_forced_mate` derivation converts `eval_mate` to the correct POV side (`_pov_mate`/`_solver_color_for`) before the sign test, instead of comparing the raw white-perspective-absolute value against 0 | ✓ VERIFIED | `app/services/flaws_service.py:496-500` (missed) and `:525-530` (allowed) use `_pov_mate(...)`/`_solver_color_for(...)`, not a raw `eval_mate > 0` test; commit `729f7961`; `tests/services/test_flaws_service.py::TestDetectTacticForFlawForcedMatePov` (3 tests: black-mover Black-mate→True, black-mover White-mate→False, black-refuter case) present and passing |
| 4 | Item 2: a non-empty entry-ply batch where every engine eval returns `(None, None)` is NOT stamped `evals_completed_at`; one aggregated Sentry event fires; the D-09 zero-eval-target invariant (`test_engine_none_marks_complete`) still stamps complete | ✓ VERIFIED | `app/services/eval_drain.py:2372-2382` — gate is `if eval_targets and all(cp is None and mt is None ...)`, emits one `capture_message` (no interpolated variables), `sleep` + `continue`, skips `_mark_evals_completed` entirely; `TestDeadPoolAllFailLeavesPending::test_dead_pool_all_fail_leaves_batch_pending` and `TestEngineNoneMarksComplete::test_engine_none_marks_complete` both pass |
| 5 | Item 3: shared-quintile cohorts widen the reported SE via the covariance-correction term `+2·shared_n·v/(n_u·n_o)`; `shared_n=0` is byte-identical to the pre-fix formula; point estimates unchanged; wrong-independence docstrings corrected | ✓ VERIFIED | `app/services/score_confidence.py:182,244-246` (`shared_n: int = 0`, `cov_correction` term); `app/services/endgame_service.py` threads `tc_shared_quintile_count`/`shared_wdl_count` through `_iterate_clock_rows`→`_build_quintile_bullets`; `test_shared_n_widens_se_matching_covariance_correction` (100/100/100 worked example, SE 0.0707→0.10) and `test_shared_n_default_zero_is_byte_identical_to_pre_fix_formula` both pass; docstrings at both sites corrected (no longer claim independence) |
| 6 | Item 4: one malformed chess.com or lichess game (unguarded `normalize_*_game` `KeyError`) is skipped; remaining games are yielded; import completes; one aggregated Sentry capture per skipped game with no message-text variables | ✓ VERIFIED | `app/services/chesscom_client.py:331-337` and `app/services/lichess_client.py:191-201` — per-game `try/except Exception`, `logger.warning` (lazy `%s`, not Sentry message interpolation), `sentry_sdk.set_context`/`capture_exception`, `continue`; pre-existing `json.JSONDecodeError` line guard in lichess left untouched (lines 178-182); `test_malformed_game_skipped_and_continues` and `test_normalization_failure_skipped_and_continues` both pass |
| 7 | Item 5 (D-05): `entry_submit_eval` excludes a leased-but-expired game from stamping via `entry_eval_lease_expiry > now()`, minimum-guard scope only (no echoed-`game_ids` intersection) | ✓ VERIFIED | `app/routers/eval_remote.py:906` (`Game.entry_eval_lease_expiry > sa.func.now()` as third predicate alongside `entry_eval_leased_by` and `evals_completed_at.is_(None)`); `test_entry_submit_excludes_expired_lease` passes |

**Score:** 7/7 truths verified (0 present-but-behavior-unverified)

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `app/services/tactic_detector.py` | New `has_forced_mate` mate-fallback branch | ✓ VERIFIED | Present at line 2504, wired into `detect_tactic_motif`'s Tier-1 mate cascade, exercised by `TestHasForcedMateFallback` |
| `app/services/flaws_service.py` | `_recompute_fen_map` storing full `board.fen()`; POV-corrected `has_forced_mate` wiring | ✓ VERIFIED | Both present, wired, tested |
| `app/services/eval_drain.py` | Inline WR-05-mirror circuit breaker | ✓ VERIFIED | Present at line 2372, gated correctly, tested |
| `app/services/engine.py` | Corrected `EnginePool` docstring | ✓ VERIFIED | Docstring at lines 371-388 describes never-dropped-slot / near-instant `(None,None)` behavior and references Phase 148 item 2 |
| `app/routers/eval_remote.py` | `entry_eval_lease_expiry > now()` guard predicate | ✓ VERIFIED | Present at line 906, wired into `entry_submit_eval`'s guard query, tested |
| `app/services/endgame_service.py` | Shared-quintile count threading + docstring fix | ✓ VERIFIED | `_iterate_clock_rows`/`_build_quintile_bullets` thread `tc_shared_quintile_count`/`shared_wdl_count`; both docstrings corrected |
| `app/services/score_confidence.py` | `compute_score_difference_test` covariance term | ✓ VERIFIED | `shared_n` param + `cov_correction` term present, tested |
| `app/services/chesscom_client.py` / `lichess_client.py` | Per-game try/except + skip + Sentry | ✓ VERIFIED | Both present, symmetric, tested; lichess JSON-decode guard untouched |
| `tests/services/test_tactic_detector.py` | `TestHasForcedMateFallback` | ✓ VERIFIED | 2 tests present, pass |
| `tests/services/test_flaws_service.py` | `TestFenMapEpCapture`, `TestDetectTacticForFlawForcedMatePov` | ✓ VERIFIED | Both classes present, pass |
| `tests/services/test_eval_drain.py` | `TestDeadPoolAllFailLeavesPending` | ✓ VERIFIED | Present, passes, coexists with D-09 invariant test |
| `tests/test_eval_worker_endpoints.py` | `test_entry_submit_excludes_expired_lease` | ✓ VERIFIED | Present, passes |
| `tests/services/test_score_confidence.py` | Shared-n widening + byte-identical regression | ✓ VERIFIED | Both present, pass |
| `tests/services/test_time_pressure_service.py` | Shared-cohort CI-widening test + updated 6-tuple destructures | ✓ VERIFIED | `TestSharedQuintileCovarianceWidening` present, passes |
| `tests/test_chesscom_client.py` / `test_lichess_client.py` | Malformed-game-skipped tests | ✓ VERIFIED | Both present, pass |

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| `detect_tactic_motif(has_forced_mate=...)` | new fallback branch | direct parameter gate after Tier-1 mate cascade | ✓ WIRED | Branch is unreachable unless every prior mate detector already failed (confirmed by 148-REVIEW.md and re-confirmed here) |
| `_recompute_fen_map` full FEN | `_detect_tactic_for_flaw` parse_san/PV replay | detector-internal `fen_map` dict | ✓ WIRED | ep-capture fixture test replays through the full path and passes |
| `eval_targets and all((None,None))` | skip `_mark_evals_completed` | inline gate + `continue` before Step 5 | ✓ WIRED | Confirmed by reading the surrounding code; Step 5 (write session) is unreachable on this path |
| `Game.entry_eval_lease_expiry > sa.func.now()` | `leased_game_ids` selection | third predicate in `entry_submit_eval`'s guard `select()` | ✓ WIRED | Confirmed in-context; excluded games implicitly drop out |
| `_iterate_clock_rows` shared count | `_build_quintile_bullets` → `compute_score_difference_test(shared_n=m)` | tuple threading (6th return element → param → kwarg) | ✓ WIRED | All 3 hops confirmed by grep + read; single production call site updated |
| `try/except` around `normalize_*_game` | `continue` (skip) → generator keeps yielding | inline per-game guard inside the `for game in games` / `async for line in ...` loops | ✓ WIRED | Confirmed for both chess.com and lichess; existing JSON-decode guard is a separate, untouched try/except upstream |

### Behavioral Spot-Checks / Test Execution

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Full backend suite | `uv run pytest -n auto -q` | 3203 passed, 18 skipped | ✓ PASS |
| Type check | `uv run ty check app/ tests/` | All checks passed! | ✓ PASS |
| Tactic precision gate (D-03 regression check, `--ignore`'d by default) | `uv run pytest tests/scripts/tagger/test_detector_precision.py -q` | 1 passed | ✓ PASS |
| Debt-marker scan on all 9 modified source files | `grep -n -E "TBD\|FIXME\|XXX\|TODO\|HACK\|PLACEHOLDER"` | no matches | ✓ PASS |

The full suite (3203 passed) matches every plan SUMMARY's independently-claimed count
exactly, giving strong end-to-end confirmation that no plan's claims are stale or
contradicted by a later plan's changes.

### Anti-Patterns Found

None. All 9 modified files scanned for debt markers, placeholder returns, and stub
patterns — clean.

### Requirements Coverage

No `REQUIREMENTS.md` entries map to Phase 148 (confirmed via grep — no hits). The
ITEM-1..5 spine (locked in 148-CONTEXT.md, per phase-brief instruction) is the
traceability substitute and is fully covered per the table above. No orphaned
requirements.

### CR-01 Blocker Resolution (post-review)

148-REVIEW.md flagged **CR-01** (critical): the item-1 `has_forced_mate` wiring in
`flaws_service.py` compared the raw white-perspective-absolute `eval_mate` against 0
without converting to the POV side, silently inverting the result for ~half of all
flaw plies (black POV). Verified fixed in commit `729f7961`:
- Both derivation sites (`missed` and `allowed` orientations) now route through
  `_pov_mate()`/`_solver_color_for()` — the same helpers used everywhere else in the
  file for this exact sign convention — instead of a raw `> 0` test.
- `TestDetectTacticForFlawForcedMatePov` regression class (3 tests) exercises the
  black-POV case in both directions (false-negative guard and false-positive guard)
  plus the black-refuter "allowed" orientation. All pass.
- The two WARNING-level doc caveats (WR-01: `FlawRecord.fen` split-back
  cross-reference; WR-02: truncated-mate `tactic_depth` approximation caveat) were
  also folded into the same commit and are present in the code (`flaws_service.py:128-131`,
  `tactic_detector.py:2437-2440`).
- IN-01 (info-level, lease-expiry NULL edge case) required no code change per the
  review's own disposition — confirmed no code change was made for it, consistent with
  the review's "no code change required now" recommendation.

### Human Verification Required

None. All must-haves were verifiable via passing automated tests plus direct code
inspection; no visual, real-time, or external-service-dependent behavior in scope for
this phase.

### Gaps Summary

No gaps. All five phase-brief items (ITEM-1..5) are present in the codebase, wired
correctly, and covered by passing regression tests. The one BLOCKER surfaced by the
phase's own code review (CR-01) was fixed in a follow-up commit with its own regression
test class, verified present here. Full backend suite green (3203 passed, 18 skipped),
type check clean, tactic precision gate green, no debt markers in any modified file.

---

*Verified: 2026-07-04T09:18:15Z*
*Verifier: Claude (gsd-verifier)*
