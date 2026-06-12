---
phase: 113-opponent-flaw-materialization
reviewed: 2026-06-10T06:17:11Z
depth: standard
files_reviewed: 8
files_reviewed_list:
  - app/repositories/query_utils.py
  - app/services/flaws_service.py
  - app/repositories/library_repository.py
  - tests/services/test_flaws_service.py
  - tests/test_flaw_predicate.py
  - tests/test_flaws_materialization.py
  - tests/test_library_repository.py
  - tests/test_library_router.py
findings:
  critical: 0
  warning: 0
  info: 3
  total: 3
status: clean
---

# Phase 113: Code Review Report

**Reviewed:** 2026-06-10T06:17:11Z
**Depth:** standard
**Files Reviewed:** 8
**Status:** clean (no Critical or Warning findings)

## Summary

Phase 113 generalizes the flaw-classification kernel to emit FlawRecords for both
movers, then gates every `game_flaws` read-path in `library_repository.py` to
player-only rows via the centralized `player_only_gate` helper in `query_utils.py`.

**Parity correctness (highest-priority area):** `is_opponent_expr` and
`player_only_gate` are verified correct by hand-tracing all four
(ply parity × user_color) combinations and confirmed by the `TestIsOpponentExpr`
live-SQL test. The parity convention (even ply = white mover) is consistent with
`_run_all_moves_pass`, `library_service.py` line 121, `count_user_ply_total` lines
647-649, and the import-time `process_game_pgn` enumeration. No inline `ply % 2`
math was introduced by Phase 113 — the two pre-existing sites in
`library_repository.py` (count_user_ply_total) and `library_service.py` are
unchanged and out of scope.

**Data-isolation completeness:** All five `game_flaws` read sites in
`library_repository.py` are correctly gated:

| Reader | Gate reference |
|---|---|
| `flaw_exists_from_table` | R1/R6 — `player_only_gate` in correlated EXISTS |
| `query_flaws` | R2 — `player_only_gate` in base WHERE |
| `fetch_page_game_flaws` | R3 — `player_only_gate` after new `join(Game)` |
| `fetch_stats_aggregates` | R4 — `player_only_gate` after new `join(Game)` |
| `fetch_stats_trend` (flaw_counts_subq) | R5 — `player_only_gate` after new `join(Game)` |

`count_game_severities` in `flaws_service.py` is confirmed unchanged — it still
guards with `if mover != user_color: continue`, correctly computing user-only
inaccuracy/mistake/blunder tallies for the Games-tab cards.

**`lucky` per-mover generalization:** The Phase 113 fix (`subject_result =
derive_user_result(game.result, mover)` per flaw, replacing the single pre-resolved
`user_result`) is correct. An opponent end-of-game blunder where the opponent lost
(`subject_result = "loss"`) correctly does NOT receive the `lucky` tag; a player
end-of-game blunder in a drawn game does receive it. The `TestOpponentLuckyTag`
class validates both cases with concrete position math. No remaining code path
passes the player's result for opponent flaws.

**Security:** No new HTTP endpoints, no new user input. The `player_only_gate` gate
correctly uses `GameFlaw.user_id == user_id` alongside the parity gate, so
cross-user data access remains impossible. The correlated EXISTS in
`flaw_exists_from_table` correctly references the outer `Game.user_color` (not a
subquery-internal literal), ensuring the gate is per-game and not per-user-constant.

**SQL parameterization:** All query sites use SQLAlchemy ORM column references
(no string interpolation). No injection risk.

**New JOINs:** `fetch_page_game_flaws`, `fetch_stats_aggregates`, and the
`flaw_counts_subq` inside `fetch_stats_trend` each add one `join(Game, Game.id ==
GameFlaw.game_id)`. With `GameFlaw.user_id == user_id` and `game_id.in_(subq)` also
present, these are 1:1 inner joins — no fan-out / row duplication risk.

**Test coverage:** Thorough. `TestIsOpponentExpr` exercises all four parity
combinations via live SQL. `TestFlawExistsPlayerOnly` (4 cases), `TestPlayerOnlyGate`
(2 cases), `TestPageFlawsPlayerOnly` (2 cases), and `TestStatsAggregatesPlayerOnly`
(2 cases) are concrete no-regression gate tests. `TestBothSidesMaterialization`
verifies the row-count doubles invariant and PK non-collision. `TestOpponentLuckyTag`
validates the per-mover `subject_result` fix from both sides.

**No blockers or warnings found.** Three Info-level observations are noted below.

---

## Info

### IN-01: Test module docstring is now inaccurate ("No DB required")

**File:** `tests/services/test_flaws_service.py:7`
**Issue:** The module-level docstring says "No DB required — all tests construct
GamePosition objects in memory." Phase 113 added `TestIsOpponentExpr`, which uses
`db_session` and issues real SQL against PostgreSQL (four async tests). The claim
is no longer true.
**Fix:** Update the first paragraph to reflect that `TestIsOpponentExpr` requires
a DB session:

```python
"""Unit tests for app.services.flaws_service.
...
No DB required for most tests — GamePosition objects are constructed in memory.
Exception: TestIsOpponentExpr evaluates is_opponent_expr() via live SQL (DB required).
...
"""
```

---

### IN-02: `_build_tags` / `_is_unpunished` parameter name `user_result` is stale after Phase 113

**File:** `app/services/flaws_service.py:357`, `app/services/flaws_service.py:441`
**Issue:** Both `_is_unpunished` and `_build_tags` have a parameter named
`user_result: Literal["win", "draw", "loss"]`. After Phase 113, the caller passes
`subject_result` (the *mover's* result, which may be the opponent's result). The
parameter name `user_result` now misleadingly implies it is always the player's
result. The `_build_tags` docstring still says "one user flaw" and `_is_unpunished`
still says "user BLUNDER."
**Fix:** Rename the parameter to `subject_result` in both private functions and
update the docstrings to say "mover's result" rather than "user's result." This is
a pure cosmetic rename — no behavior changes:

```python
def _is_unpunished(
    n: int,
    all_moves: dict[int, _MoveEntry],
    severity: FlawSeverity,
    subject_result: Literal["win", "draw", "loss"],  # mover's result, not always the player's
) -> bool:
    ...
    return subject_result != "loss"
```

---

### IN-03: `type: ignore[type-arg]` should use `ty: ignore[...]` per project convention

**File:** `tests/test_library_repository.py:465`
**Issue:** The `_flaw_row` helper uses `# type: ignore[type-arg]` to suppress the
bare `dict` return annotation. CLAUDE.md requires `# ty: ignore[rule-name]` (not
`# type: ignore`) for type-checker suppressions. The same pre-existing pattern
appears in `tests/test_flaw_predicate.py:92` (out of this phase's scope).
**Fix:** Replace with the project-convention suppression, or just add the type
argument directly:

```python
) -> dict[str, object]:  # no suppression needed
```

Or if ty flags it:

```python
) -> dict:  # ty: ignore[missing-type-argument]
```

---

_Reviewed: 2026-06-10T06:17:11Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
