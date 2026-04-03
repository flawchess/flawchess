---
phase: 40-static-type-checking
verified: 2026-03-31T22:30:00Z
status: passed
score: 17/17 must-haves verified
re_verification: false
---

# Phase 40: Static Type Checking Verification Report

**Phase Goal:** Backend type errors are caught at CI time, not at runtime
**Verified:** 2026-03-31T22:30:00Z
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

Success Criteria from ROADMAP.md used as primary truths, augmented by plan must_haves.

| #  | Truth                                                                                    | Status     | Evidence                                                                                   |
|----|------------------------------------------------------------------------------------------|------------|--------------------------------------------------------------------------------------------|
| 1  | `ty` runs in CI pipeline and fails the build on type errors                              | VERIFIED   | ci.yml line 46-47: `Type check (ty)` step, `uv run ty check app/ tests/` between ruff and pytest |
| 2  | All backend functions have explicit type annotations on parameters and return values     | VERIFIED   | All repository query functions have typed params and Row[Any] return types; normalization returns NormalizedGame; stats_service uses FilterParams |
| 3  | Untyped `dict` usage replaced with TypedDicts or Pydantic models where semantically meaningful | VERIFIED   | NormalizedGame at normalization boundary (D-01), FilterParams TypedDict in stats_service (D-02), TrieNode class in opening_lookup (D-04) |
| 4  | `ty` passes clean (zero errors) on the backend codebase                                  | VERIFIED   | `uv run ty check app/ tests/` → "All checks passed!" (confirmed live run)                 |
| 5  | ty runs between ruff and pytest steps in CI                                              | VERIFIED   | ci.yml: ruff (line 43), ty (line 46), pytest (line 49) — correct order                    |
| 6  | ty is configured in pyproject.toml with appropriate rule settings                       | VERIFIED   | pyproject.toml lines 41-43: `[tool.ty.rules]`, `unused-ignore-comment = "warn"`           |
| 7  | dev dependencies use the non-deprecated dependency-groups format                        | VERIFIED   | pyproject.toml line 21: `[dependency-groups]`; no `[tool.uv]` section present             |
| 8  | SQLAlchemy forward reference errors suppressed with ty-specific syntax                  | VERIFIED   | game.py:83, game_position.py:84, user.py:28 all use `# ty: ignore[unresolved-reference]`  |
| 9  | Repository return types use Row[Any] instead of tuple                                   | VERIFIED   | analysis_repository: lines 93, 146; endgame_repository: lines 68, 216, 323, 389; stats_repository: lines 35, 77, 123, 200 |
| 10 | FastAPI-Users write_token error is suppressed per D-07                                  | VERIFIED   | auth.py:170 has `# ty: ignore[unresolved-attribute]`; auth.py:139 also suppresses oauth_callback |
| 11 | Real logic bugs (invalid-raise, position_bookmarks hasattr) are fixed                   | VERIFIED   | lichess_client.py:74 initializes `last_attempt_error: Exception = Exception("...")` sentinel; position_bookmarks.py:107 uses `isinstance(data, PositionBookmark)` |
| 12 | NormalizedGame Pydantic model replaces untyped dict returns at normalization boundary   | VERIFIED   | app/schemas/normalization.py: `class NormalizedGame(BaseModel)` with all Literal type aliases |
| 13 | NormalizedGame uses Literal types for fixed-value fields per CLAUDE.md                  | VERIFIED   | Platform, GameResult, Color, Termination, TimeControlBucket all defined as Literal aliases |
| 14 | The opening trie uses a typed TrieNode class instead of bare dict per D-04              | VERIFIED   | opening_lookup.py:16 `class TrieNode`; `_TRIE: TrieNode = _build_trie()` (line 91); no bare `dict` |
| 15 | FilterParams TypedDict eliminates all stats_service **kwargs spread errors              | VERIFIED   | stats_service.py:43 `class FilterParams(TypedDict):`                                       |
| 16 | Repository parameter types accept Sequence[str] to fix Literal list invariance errors  | VERIFIED   | All three repository files (analysis, stats, endgame) use `Sequence[str] | None` for time_control and platform params |
| 17 | All test files have proper None guards for chess.pgn.read_game() and get_job()          | VERIFIED   | test_import_service.py: 5x `assert game is not None`, 1x `assert pov is not None`, `assert job.error is not None`; test_imports_router.py: `assert job is not None` |

**Score:** 17/17 truths verified

### Required Artifacts

| Artifact                                       | Expected                                    | Status     | Details                                           |
|------------------------------------------------|---------------------------------------------|------------|---------------------------------------------------|
| `.github/workflows/ci.yml`                     | ty check step between ruff and pytest       | VERIFIED   | Lines 46-47; ruff on 43, pytest on 49 — ordering confirmed |
| `pyproject.toml`                               | ty configuration and dependency-groups      | VERIFIED   | `[dependency-groups]` on line 21, `[tool.ty.rules]` on line 41 |
| `app/models/game.py`                           | ty-specific suppression for forward ref     | VERIFIED   | Line 83: `# ty: ignore[unresolved-reference]`     |
| `app/repositories/analysis_repository.py`     | Row[Any] return types                       | VERIFIED   | Lines 93, 146 use `-> list[Row[Any]]:`            |
| `app/schemas/normalization.py`                 | NormalizedGame Pydantic model               | VERIFIED   | Created with all Literal type aliases; 5 aliases defined |
| `app/services/opening_lookup.py`              | Typed TrieNode class                        | VERIFIED   | `class TrieNode` at line 16, `_TRIE: TrieNode`    |
| `app/services/stats_service.py`               | FilterParams TypedDict                      | VERIFIED   | `class FilterParams(TypedDict):` at line 43        |
| `app/services/normalization.py`               | Returns NormalizedGame not dict             | VERIFIED   | Both functions return `NormalizedGame | None`; `return NormalizedGame(` at lines 222, 341 |
| `app/services/lichess_client.py`              | last_attempt_error initialized as Exception | VERIFIED   | Line 74: `Exception("Exhausted retries without capturing an error")` |
| `app/schemas/position_bookmarks.py`           | isinstance check instead of hasattr        | VERIFIED   | Line 107: `isinstance(data, PositionBookmark)`    |
| `app/routers/auth.py`                         | ty suppression for FastAPI-Users           | VERIFIED   | Lines 139, 170 both have `# ty: ignore[...]`      |
| `app/repositories/import_job_repository.py`   | rowcount attribute error handled            | VERIFIED   | Line 175: `ty: ignore[unresolved-attribute]` comment |
| `tests/conftest.py`                           | AsyncGenerator return type                  | VERIFIED   | Line 103: `-> AsyncGenerator[AsyncSession, None]` |

### Key Link Verification

| From                          | To                              | Via                                | Status   | Details                                                          |
|-------------------------------|---------------------------------|------------------------------------|----------|------------------------------------------------------------------|
| `.github/workflows/ci.yml`    | `pyproject.toml`                | `uv run ty check` uses `[tool.ty]` | VERIFIED | CI runs `uv run ty check app/ tests/`; pyproject.toml has `[tool.ty.rules]` |
| `app/repositories/*.py`       | `app/services/*.py`             | `Row[Any]` consumed by services    | VERIFIED | Repository functions typed with `list[Row[Any]]`; stats_repository `Sequence[str]` params consumed by stats_service FilterParams |
| `app/services/normalization.py` | `app/schemas/normalization.py` | normalize functions return NormalizedGame | VERIFIED | Both normalize functions import and return `NormalizedGame | None` |
| `app/services/import_service.py` | `app/schemas/normalization.py` | import pipeline consumes NormalizedGame | VERIFIED | import_service.py:26 imports NormalizedGame; batch typed as `list[NormalizedGame]`; `model_dump()` called for DB insert |
| `app/services/stats_service.py` | `app/repositories/stats_repository.py` | FilterParams TypedDict spread | VERIFIED | FilterParams in stats_service; stats_repository uses Sequence[str] params compatible with TypedDict fields |

### Data-Flow Trace (Level 4)

Not applicable for this phase. Phase 40 is a pure tooling/type-annotation phase — it adds type safety infrastructure and fixes type errors. No new dynamic data paths were introduced. All changes are annotation-level or structural (TrieNode replaces bare dict, NormalizedGame replaces dict literals with validated models). The underlying data flow was pre-existing.

### Behavioral Spot-Checks

| Behavior                              | Command                                 | Result                        | Status  |
|---------------------------------------|-----------------------------------------|-------------------------------|---------|
| ty reports zero errors on full scope  | `uv run ty check app/ tests/`           | "All checks passed!"          | PASS    |
| Full test suite passes with no failures | `uv run pytest -q`                    | 473 passed, 37 warnings in 4.91s | PASS |

### Requirements Coverage

| Requirement | Source Plan | Description                                                              | Status    | Evidence                                                        |
|-------------|-------------|--------------------------------------------------------------------------|-----------|-----------------------------------------------------------------|
| TOOL-01     | 40-01-PLAN  | Backend static type checking with astral `ty` integrated into CI/CD pipeline | SATISFIED | ty installed, `[tool.ty.rules]` configured, CI step added; `uv run ty check app/ tests/` runs between ruff and pytest |
| TOOL-02     | 40-02-PLAN  | Backend type safety review — replace untyped dicts with TypedDicts/Pydantic models, add missing type hints | SATISFIED | NormalizedGame Pydantic model with Literal types, FilterParams TypedDict, TrieNode class, Row[Any] repository returns, Sequence[str] params, zero ty errors |

No orphaned requirements: REQUIREMENTS.md traceability table maps both TOOL-01 and TOOL-02 exclusively to Phase 40, and both plans claim them. No Phase 40 requirements appear in REQUIREMENTS.md without plan coverage.

### Anti-Patterns Found

No anti-patterns identified. Scan performed on all phase-modified files:

- No `TODO/FIXME/PLACEHOLDER` comments in modified production code
- No `return null` or empty stubs in modified files
- `# ty: ignore` suppressions are targeted, documented with explanatory comments, and cover legitimate third-party limitations (FastAPI-Users generic typing, SQLAlchemy async DML result types)
- The `isinstance(g, NormalizedGame) else g` branch in import_service.py `_flush_batch` is an intentional backward-compatibility shim documented in SUMMARY.md (tests yield plain dicts); it is not a stub

### Human Verification Required

None. This phase is pure backend tooling — no UI changes, no new user-facing features, no external service integrations. All behavioral claims are verifiable programmatically. The ty and pytest runs above confirm the phase goal.

### Gaps Summary

No gaps. All must-haves from both plans are verified against the actual codebase. The phase goal "Backend type errors are caught at CI time, not at runtime" is fully achieved:

1. ty is installed as a dev dependency in the non-deprecated `[dependency-groups]` format
2. ty is configured in `pyproject.toml` with `[tool.ty.rules]`
3. ty runs in CI between ruff and pytest, blocking the build on errors
4. `uv run ty check app/ tests/` reports zero errors (confirmed live run)
5. All 473 existing tests pass with no regressions
6. Untyped dict returns replaced with NormalizedGame (Pydantic, D-01), FilterParams (TypedDict, D-02), TrieNode (typed class, D-04)
7. Real bugs fixed: invalid-raise in lichess_client, hasattr-to-isinstance in position_bookmarks schema

---

_Verified: 2026-03-31T22:30:00Z_
_Verifier: Claude (gsd-verifier)_
