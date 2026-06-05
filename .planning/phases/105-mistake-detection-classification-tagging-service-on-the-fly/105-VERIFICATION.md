---
phase: 105-mistake-detection-classification-tagging-service-on-the-fly
verified: 2026-06-05T15:00:00Z
status: passed
score: 9/9 must-haves verified
overrides_applied: 0
---

# Phase 105: Mistake Detection + Classification + Tagging Service Verification Report

**Phase Goal:** A server-side `mistakes` service derives, on-the-fly from stored per-ply evals, every flaw in a Lichess-analyzed game — severity (inaccuracy / mistake / blunder) plus eight attribution tags — and returns typed per-flaw objects ready for the Games / Flaws / Analysis surfaces and SEED-037 Train to consume. No materialization, no schema change, no UI.
**Verified:** 2026-06-05
**Status:** PASSED
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|---------|
| 1 | `classify_game_mistakes` returns `list[FlawRecord]` for analyzed game (>=90% coverage) and `GameNotAnalyzed` otherwise — inaccuracy-only game returns empty list (distinct from GameNotAnalyzed) | VERIFIED | `TestClassifyGameMistakes::test_zero_coverage_returns_game_not_analyzed`, `test_inaccuracy_only_game_returns_empty_list`, `test_analyzed_game_returns_list` all pass |
| 2 | Severity derives purely from mover-POV ES drop at halved Lichess thresholds (0.05/0.10/0.15); highest band wins; no position guard | VERIFIED | `TestSeverityClassification` (9 tests): boundary-inclusive, highest-band-wins logic confirmed |
| 3 | Mate evals map to ±1000 cp-equivalent via Option B; `eval_mate_to_expected_score` never called in drop math | VERIFIED | `_ply_to_es` uses `MATE_CP_EQUIVALENT=1000`; grep on `eval_mate_to_expected_score` in `mistakes_service.py` returns only comments, zero live calls |
| 4 | chess.com game / <90% coverage returns `GameNotAnalyzed`, never a false zero-flaw game | VERIFIED | `test_zero_coverage_returns_game_not_analyzed`, `test_coverage_gate_below_threshold_returns_not_analyzed` pass |
| 5 | Every emitted flaw carries exactly one tempo tag from {time-pressure, hasty, knowledge-gap} | VERIFIED | `TestTempoTags::test_exactly_one_tempo_tag_per_flaw_in_classify_game` passes; `_classify_tempo` always returns exactly one TempoTag by construction |
| 6 | `miss` and `unpunished` tags work via all-moves pass covering both colors; `unpunished` restricted to blunders only | VERIFIED | `TestAttributionTags::test_miss_tag_when_preceding_opponent_was_blunder`, `test_no_unpunished_tag_on_non_blunder` pass |
| 7 | `from-winning`, `result-changing`, `phase-*` tags all present and correct | VERIFIED | `TestAttributionTags` (10 tests) covers all three; all pass |
| 8 | `fetch_game_positions_ordered` returns positions ply-ASC, ownership-guarded by `user_id`; different `user_id` returns `[]` | VERIFIED | `TestFetchGamePositionsOrdered` (3 DB-backed tests) all pass: empty on unknown, ply-ASC even when inserted out of order, ownership guard enforced |
| 9 | Derived per-game B/M/I counts are within `SANITY_TOLERANCE=2` of synthetic oracle; inaccuracy count from internal all-moves pass | VERIFIED | `TestOracleCloseness::test_derived_counts_close_to_oracle_white` and `test_derived_counts_close_to_oracle_black` pass |

**Score:** 9/9 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `app/services/mistakes_service.py` | Severity engine, ES helpers, TypedDicts, all-moves pass, `classify_game_mistakes` | VERIFIED | 478 lines; contains all required functions; ty/ruff clean |
| `app/repositories/mistakes_repository.py` | `fetch_game_positions_ordered(session, game_id, user_id)` | VERIFIED | 36 lines; SQLAlchemy 2.x `select().where().order_by(GamePosition.ply)` |
| `tests/services/test_mistakes_service.py` | Unit tests for all behaviors (no DB) | VERIFIED | 1027 lines; 64 tests, 64 passed |
| `tests/test_mistakes_repository.py` | DB-backed tests for ply ordering and ownership guard | VERIFIED | 145 lines; 3 tests, 3 passed |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|----|--------|---------|
| `mistakes_service.py::_ply_to_es` | `eval_utils.py::eval_cp_to_expected_score` | direct import + call | WIRED | Line 28 imports it; lines 134/136 call it |
| `mistakes_service.py::classify_game_mistakes` | `GameNotAnalyzed` | coverage gate | WIRED | Line 436 returns `GameNotAnalyzed(...)` when coverage < threshold |
| `mistakes_service.py::classify_game_mistakes` | all-moves pass | `_run_all_moves_pass` call | WIRED | Line 442; used for miss/unpunished adjacency checks |
| `mistakes_service.py` | `derive_user_result` from `openings_service` | imported and called | WIRED | Lines 29, 453 |
| `mistakes_service.py` | `parse_base_and_increment` from `normalization` | imported and called | WIRED | Lines 28, 449 |
| `mistakes_repository.py::fetch_game_positions_ordered` | `GamePosition` | `select().where().order_by(GamePosition.ply)` | WIRED | Lines 30-34 |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| 64 unit tests pass | `uv run pytest tests/services/test_mistakes_service.py` | 64 passed in 3.75s | PASS |
| 3 DB-backed repository tests pass | `uv run pytest tests/test_mistakes_repository.py` | 3 passed in 3.68s | PASS |
| ty type check clean | `uv run ty check [4 files]` | All checks passed | PASS |
| ruff lint clean | `uv run ruff check [4 files]` | All checks passed | PASS |
| ruff format clean | `uv run ruff format --check [4 files]` | 4 files already formatted | PASS |
| `eval_mate_to_expected_score` absent from service | grep | 0 live call sites (only comments) | PASS |
| `board.fen()` absent from service | grep | 0 live call sites (only in docstring comment) | PASS |
| No `session.query` in repository | grep | 0 matches | PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|---------|
| LIBG-02 | 105-01, 105-02 | On-the-fly severity detection from stored evals; mate Option B; no materialization; explicit "no analysis" result | SATISFIED | `classify_game_mistakes` implements all aspects; `fetch_game_positions_ordered` is the no-schema-change data path; DB tests pass |
| LIBG-06 | 105-02 | Eight attribution tags per flaw, exactly one tempo tag | SATISFIED | All 8 tag types implemented and tested in `TestAttributionTags` and `TestTempoTags`; tempo exclusivity proven |
| LIBG-07 | 105-01, 105-02 | Typed flaw objects (ply, FEN, side, severity, tags, eval before/after) as consumption contract | SATISFIED | `FlawRecord` TypedDict has all 8 required fields; `GameMistakesResult = list[FlawRecord] | GameNotAnalyzed` is the contract |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| None | — | No TBD/FIXME/XXX markers, no stub returns, no magic numbers found | — | Clean |

No unresolved debt markers. No stub patterns. The `tags=[]` in `_build_flaw_record` is immediately overwritten at the call site (line 465), not a hollow stub.

### Human Verification Required

None. This phase is backend-only with no UI, no HTTP endpoint, and no external service integration. All behaviors are verifiable from the codebase and test suite.

### Gaps Summary

No gaps. All nine must-have truths are verified by passing tests and direct codebase inspection. The phase goal is fully achieved:

- Severity classification (inaccuracy/mistake/blunder) from mover-POV ES drop at Lichess-aligned halved thresholds — implemented and unit-tested.
- Eight attribution tags per flaw (miss, unpunished, from-winning, result-changing, time-pressure, hasty, knowledge-gap, phase-*) — implemented and tested; tempo exclusivity invariant holds.
- Typed `FlawRecord` / `GameNotAnalyzed` / `GameMistakesResult` output contract — defined with all required fields.
- `fetch_game_positions_ordered` repository helper — ply-ordered, ownership-guarded, no schema change, no SQL in the service layer.
- No materialization, no new DB columns, no UI, no HTTP endpoint — all confirmed by grep and code review.
- All 67 tests (64 unit + 3 DB-backed) pass; ty/ruff/format clean.

---

_Verified: 2026-06-05_
_Verifier: Claude (gsd-verifier)_
