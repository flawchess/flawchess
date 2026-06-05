---
phase: 106-games-surface-backend-mistake-filter-per-game-counts-stats-a
verified: 2026-06-05T00:00:00Z
status: passed
score: 5/5 must-haves verified
overrides_applied: 0
---

# Phase 106: Games-surface Backend — Mistake Filter + Per-game Counts + Stats Verification Report

**Phase Goal:** Two server-side endpoints the Library "Games" subtab consumes — a mistake-filtered game archive with per-game B/M/I counts + curated card tag-chips (`GET /api/library/games`), and a mistake-stats aggregate (`GET /api/library/mistake-stats`) — both derived on-the-fly via a SQL window-scan + Python tagging that reuses Phase 105's `mistakes_service` kernel, with NO materialization and NO schema change. Backend only.
**Verified:** 2026-06-05
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
| --- | ----- | ------ | -------- |
| 1 | Game-archive accepts a boolean mistake-type filter as a single user-color-scoped indexed EXISTS over per-ply ES-drop, thresholds as bound params, NO new column/table/migration/backfill; index decision documented | ✓ VERIFIED | `mistake_exists_subquery` (library_repository.py:164) builds a correlated `exists()` over `game_positions`, user-color-restricted via `_user_ply_filter` (:151) matching `Game.user_color`. Thresholds (`MISTAKE_DROP`/`BLUNDER_DROP`) and `LICHESS_K` are imported constants (:40-48), bound `user_id` param (no f-string). `apply_game_filters` gains `mistake_severity`/`user_id` (query_utils.py:24-25). `git diff 460e3703..HEAD -- alembic/versions/ app/models/game_position.py app/models/game.py` is empty — no migration, no model change. EXPLAIN index decision documented in 106-03-SUMMARY.md:98-103 (~11ms service path on PK, no new index). Tests `TestExistsFilter` (incl. opponent-only exclusion) green. |
| 2 | Each game carries per-game B/M/I counts + curated/deduped card chips (game-level dedupe, one chip per type, inaccuracy + phase excluded), reusing the 105 kernel; chess.com/unanalyzed return explicit no_engine_analysis, never false 0/0/0 | ✓ VERIFIED | `count_game_severities` (mistakes_service.py:512) returns `SeverityCounts` (3 tiers, user moves only) or `GameNotAnalyzed`. `_build_card` (library_service.py:86) discriminates on `"reason"` key → `severity_counts=None`/`chips=[]`/`analysis_state="no_engine_analysis"` for unanalyzed. `_curate_chips` (:72) drops `phase-*`, dedupes via `set`, one chip per type in `_CHIP_ORDER`. Tests `test_chesscom_game_card_is_no_engine_analysis`, `test_chips_exclude_phase_and_dedupe`, `test_inaccuracy_only_game_distinct_from_not_analyzed` green. |
| 3 | Stats endpoint computes per-severity counts/rates (per game AND per 100 user-moves), full tag distribution (tempo split, result-changing rate, phase histogram), trend-over-time, over filtered analyzed-only set | ✓ VERIFIED | `get_mistake_stats` (library_service.py:401) → `_compute_rates` (per_game = c/analyzed_n; per_100 = c/total_user_moves*100, W2 user-mover denominator via `_count_user_moves`), `_compute_tag_distribution` (tempo dict, result_changing_rate, phase_histogram), `_compute_trend` (rolling-GAME window, D3). `MistakeStatsResponse` carries all fields (schemas/library.py:117). Tests `test_per_100_moves_and_counts`, `test_result_changing_rate_and_distribution`, `test_trend_point_date_is_window_last_game` assert definite values. |
| 4 | Stats response states explicit % analyzed (≥90%-per-ply-coverage) denominator AND analyzed-game N | ✓ VERIFIED | `count_filtered_and_analyzed` (library_repository.py:344) returns `(total_n, analyzed_n)` via `SUM(CASE WHEN eval non-null...)::float/COUNT(*) >= EVAL_COVERAGE_MIN` GROUP BY game_id; `EVAL_COVERAGE_MIN` imported (no 0.90 literal). Response exposes `analyzed_pct`, `analyzed_n`, `total_n` (schemas:128-130). Test `test_analyzed_denominator_counts_only_covered_games` asserts total_n=2/analyzed_n=1 (analyzed + chess.com seed). |
| 5 | Severity-drop math duplicated in SQL only for the EXISTS filter, cross-checked against Python kernel by a fixture test including the mate branch | ✓ VERIFIED | Single SQL transcription in `_cp_equiv`/`_es_expr`/`_per_ply_drop_subquery` (library_repository.py:65-136), constants imported. Cross-check `test_cross_check_sql_equals_kernel_subset` asserts SQL flags == user-color-filtered M+B kernel subset. **Mate branch:** WR-01 (eval_mate==0 sign() divergence) fixed in commit c7bf028d — `_cp_equiv` now uses kernel's `>0/else` split (:78-84); `test_cross_check_mate_branch_matches_kernel` (test_library_repository.py:264, seeds Mate(0)) GREEN, was red against the buggy sign() code. |

**Score:** 5/5 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
| -------- | -------- | ------ | ------- |
| `app/services/mistakes_service.py` | `count_game_severities` + `SeverityCounts` | ✓ VERIFIED | SeverityCounts:111, count_game_severities:512, user-color-scoped, gated by `_compute_eval_coverage` |
| `app/repositories/query_utils.py` | `mistake_severity` EXISTS param | ✓ VERIFIED | keyword-only `mistake_severity`/`user_id` (:24-25), ValueError if severity set without user_id, lazy import of `mistake_exists_subquery` (:108) |
| `app/repositories/library_repository.py` | SQL ES-drop + EXISTS + analyzed denominator + archive query | ✓ VERIFIED | `mistake_exists_subquery`, `flagged_plies_for_severity`, `query_filtered_games`, `count_filtered_and_analyzed`, `analyzed_game_ids`; WR-01 fix in `_cp_equiv` |
| `app/schemas/library.py` | card + stats schemas, no hash leak | ✓ VERIFIED | GameMistakeCard, LibraryGamesResponse, SeverityRates, TagDistribution, MistakeTrendPoint, MistakeStatsResponse; no `*_hash` field |
| `app/services/library_service.py` | orchestration + chip curation + stats pipeline | ✓ VERIFIED | get_library_games, _curate_chips, get_mistake_stats + stage helpers; sequential kernel re-call (no asyncio.gather) |
| `app/routers/library.py` | thin /games + /mistake-stats handlers | ✓ VERIFIED | prefix="/library", both routes, current_active_user gated, severity Literal-constrained, from_date>to_date 422 guard |
| `app/main.py` | router mounted under /api | ✓ VERIFIED | `library_router` imported (:24) + `include_router(..., prefix="/api")` (:138) → /api/library/games, /api/library/mistake-stats |
| `tests/test_library_repository.py` | EXISTS + cross-check (incl. mate) + denominator | ✓ VERIFIED | TestExistsFilter, TestCrossCheck (incl. mate branch), TestQueryFilteredGames, TestAnalyzedDenominator — 9 tests green |
| `tests/services/test_library_service.py` | counts/chips/no_engine_analysis/stats | ✓ VERIFIED | TestCountGameSeverities, TestCardChips, TestNoEngineAnalysis, TestMistakeStats — 14 tests green |

### Key Link Verification

| From | To | Via | Status |
| ---- | -- | --- | ------ |
| query_utils.apply_game_filters | library_repository.mistake_exists_subquery | EXISTS appended when mistake_severity set | ✓ WIRED (query_utils.py:113) |
| library_repository SQL drop math | mistakes_service constants | imported LICHESS_K/MISTAKE_DROP/BLUNDER_DROP/MATE_CP_EQUIVALENT | ✓ WIRED (library_repository.py:40-48) |
| routers/library | library_service.get_library_games / get_mistake_stats | service call from thin handlers | ✓ WIRED (router:56, :97) |
| library_service | mistakes_service.classify_game_mistakes + count_game_severities | per-game kernel re-call | ✓ WIRED (:98, :111, :279, :283) |
| library_service.get_mistake_stats | library_repository.count_filtered_and_analyzed | analyzed-% denominator | ✓ WIRED (:425) |
| main.py | library_router | include_router prefix="/api" | ✓ WIRED (:138) |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
| -------- | ------- | ------ | ------ |
| Full phase test suite | `pytest tests/test_library_repository.py tests/services/test_library_service.py` | 23 passed | ✓ PASS |
| Mate cross-check (WR-01 guard) | `pytest ...test_cross_check_mate_branch_matches_kernel` | 1 passed | ✓ PASS |
| Type check | `ty check` (5 phase source files) | All checks passed | ✓ PASS |
| No migration added | `git diff 460e3703..HEAD -- alembic/versions/` | empty | ✓ PASS |
| No model schema change | `git diff 460e3703..HEAD -- app/models/game{,_position}.py` | empty | ✓ PASS |
| WR-01 fix present | `git log -1 c7bf028d` | fix(106) SQL mate Option-B parity | ✓ PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
| ----------- | ----------- | ----------- | ------ | -------- |
| LIBG-08 | 106-01, 106-02 | Games-list endpoint: boolean mistake-type EXISTS filter + per-game B/M/I counts + curated/deduped chips, no_engine_analysis state, no materialization/backfill | ✓ SATISFIED | Truths 1, 2, 5; REQUIREMENTS.md:71 marks Complete |
| LIBG-09 | 106-03 | Stats-panel aggregate: per-severity counts/rates (per game + per 100 moves), full tag distribution, trend series, explicit %-analyzed denominator + N | ✓ SATISFIED | Truths 3, 4, 5; REQUIREMENTS.md:72 marks Complete |

No orphaned requirements: REQUIREMENTS.md maps only LIBG-08/LIBG-09 to Phase 106, both claimed by plans.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
| ---- | ---- | ------- | -------- | ------ |
| library_service.py | 114, 284 | `isinstance(flaws_result, list) else []` silent fallback (REVIEW WR-03) | ℹ️ Info | Defensive branch on a currently-unreachable path (count + classify share the coverage gate). Review suggested an assert; not a correctness bug, goal unaffected. |
| library_repository.py | 321 | `_analyzed_game_ids_subquery` groups whole-user before IN-intersection (REVIEW WR-04) | ℹ️ Info | Performance-robustness concern, explicitly out of v1 scope. Service path measured ~11ms (PK nested loop); EXPLAIN documented. Goal unaffected. |

No TBD/FIXME/XXX debt markers in phase files. No false 0/0/0, no `return []` stubs, no console-log-only handlers. The `false()` branch (library_repository.py:179) is documented defensive code unreachable from the live HTTP path (router Literal + service None-coalesce).

### Human Verification Required

None. All five criteria are verifiable programmatically: SQL/kernel parity is guarded by the cross-check fixture (incl. the mate branch), the on-the-fly constraint is git-diff-verifiable, and all endpoint behaviors are covered by DB-backed service/repository tests. The index decision (criterion 1) was a measured EXPLAIN documented in 106-03-SUMMARY.md.

### Gaps Summary

No gaps. The phase goal is fully achieved in the codebase:

- Both endpoints (`GET /api/library/games`, `GET /api/library/mistake-stats`) exist, are mounted under `/api`, gated by `current_active_user`, and call into the service layer.
- The boolean mistake-severity filter is a single user-color-scoped correlated EXISTS over the per-ply ES-drop with imported thresholds as bound parameters.
- Per-game B/M/I counts + curated/deduped chips (phase + inaccuracy excluded) come from re-calling the Phase 105 kernel; chess.com/unanalyzed games surface an explicit `no_engine_analysis` state.
- The stats aggregate returns per-severity counts/rates (per game + per 100 user-moves), the full tag distribution, a rolling-game trend, and the explicit ≥90%-coverage analyzed denominator with N.
- The SQL severity math is the single duplication, cross-checked against the kernel by a fixture test that now includes the mate branch (WR-01 fixed in c7bf028d, regression-guarded by `test_cross_check_mate_branch_matches_kernel`).
- On-the-fly constraint held: zero Alembic migrations, zero model/column changes.

The two remaining REVIEW warnings (WR-03 silent fallback, WR-04 whole-user aggregate) are informational robustness/performance notes the reviewer did not classify as correctness defects; they do not block the phase goal and the performance concern is explicitly deferred per the documented EXPLAIN decision (v1 scope).

---

_Verified: 2026-06-05_
_Verifier: Claude (gsd-verifier)_
