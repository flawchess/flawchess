---
phase: 78
plan: 05
type: execute
wave: 1
depends_on: []
files_modified:
  - app/repositories/endgame_repository.py
  - app/services/endgame_service.py
  - app/models/game_position.py
  - alembic/versions/<new_revision>_reshape_ix_gp_user_endgame_game_for_eval.py
  - tests/test_endgame_repository.py
  - tests/test_endgame_service.py
  - tests/test_aggregation_sanity.py
autonomous: true
requirements: [REFAC-01, REFAC-02, REFAC-03, REFAC-04, REFAC-05]
tags: [refactor, repository, service-layer, alembic, atomic-cutover, hard-cutover]

must_haves:
  truths:
    - "REFAC plan covers BOTH `app/repositories/endgame_repository.py` AND `app/services/endgame_service.py` — `_MATERIAL_ADVANTAGE_THRESHOLD` is defined in the service layer too (per RESEARCH.md Architectural Responsibility Map). Atomic refactor or service misclassifies."
    - "All three queries (`query_endgame_entry_rows`, `query_endgame_bucket_rows`, `query_endgame_elo_timeline_rows`) project `eval_cp` and `eval_mate` (white-perspective from DB) at the span-entry ply via `array_agg(... ORDER BY ply)[1]`; sign flip happens at read time in the service helper (REFAC-02)."
    - "All three service-layer call sites (`_aggregate_endgame_stats`, `_compute_score_gap_material`, `_endgame_skill_from_bucket_rows`) use the new `_classify_endgame_bucket(eval_cp, eval_mate, user_color)` helper."
    - "`_MATERIAL_ADVANTAGE_THRESHOLD`, `PERSISTENCE_PLIES`, `imbalance_after_persistence_agg`, `raw_imbalance_after`, `ply_at_persistence`, and the contiguity case-expression are deleted entirely (REFAC-03 grep gate)."
    - "Alembic migration drops + recreates `ix_gp_user_endgame_game` with `INCLUDE(eval_cp, eval_mate)`; downgrade restores `INCLUDE(material_imbalance)`. Migration uses `op.drop_index` + `op.create_index` symmetric pattern (D-12)."
    - "`material_imbalance` column on `game_positions` is preserved — `app/models/game_position.py` still declares it, `app/services/zobrist.py` still populates it (REFAC-05)."
    - "Existing repository / service tests are updated in this same plan — `tests/test_endgame_repository.py` (`_seed_game_position` adds `eval_cp` / `eval_mate` params), `tests/test_endgame_service.py` (`_FakeRow` field rename), `tests/test_aggregation_sanity.py` (helper update)."
    - "EXPLAIN (ANALYZE, BUFFERS) on the new queries against the benchmark DB shows `Index Only Scan using ix_gp_user_endgame_game` with `Heap Fetches` near zero (REFAC-04 acceptance — operator-verified in Plan 78-06)."
  artifacts:
    - path: "app/repositories/endgame_repository.py"
      provides: "Three eval-thresholded queries; PERSISTENCE_PLIES + contiguity expression deleted"
      contains: "array_agg.*eval_cp"
    - path: "app/services/endgame_service.py"
      provides: "`_classify_endgame_bucket` helper + EVAL_ADVANTAGE_THRESHOLD; three call sites refactored"
      contains: "_classify_endgame_bucket"
    - path: "app/models/game_position.py"
      provides: "Index `ix_gp_user_endgame_game` with `INCLUDE(eval_cp, eval_mate)`"
      contains: "eval_cp.*eval_mate"
    - path: "alembic/versions/<new_revision>_reshape_ix_gp_user_endgame_game_for_eval.py"
      provides: "Symmetric drop+recreate migration (D-12)"
      contains: "postgresql_include=\\['eval_cp', 'eval_mate'\\]"
  key_links:
    - from: "app/repositories/endgame_repository.py"
      to: "app/services/endgame_service.py"
      via: "row tuple shape (game_id, endgame_class, result, user_color, eval_cp, eval_mate)"
      pattern: "row destructuring"
    - from: "app/services/endgame_service.py"
      to: "_classify_endgame_bucket"
      via: "function call"
      pattern: "_classify_endgame_bucket\\("
---

<objective>
Atomic refactor: rewrite the three endgame repository queries to threshold on `eval_cp` / `eval_mate` at the span-entry ply, update all three service-layer call sites simultaneously, ship the Alembic migration that reshapes `ix_gp_user_endgame_game` for index-only scans, delete every trace of `_MATERIAL_ADVANTAGE_THRESHOLD` / `PERSISTENCE_PLIES` / contiguity-checked persistence patterns from the codebase, and update all dependent tests.

This plan is **inherently atomic** per RESEARCH.md "Risks & Landmines" Risk 1: the classification logic is duplicated across `endgame_repository.py` AND `endgame_service.py`, and the row tuple shape changes from `(user_material_imbalance, user_material_imbalance_after)` to `(eval_cp, eval_mate)`. Splitting repository and service into separate plans would leave the codebase in a misclassifying state mid-wave. Atomic refactor or nothing.

Purpose: REFAC-01..05 — the SPEC's hard cutover. After this plan, the proxy is gone (no fallback, no feature flag), and the eval-based classification is the only path. Plans 78-03 / 78-04 ship the eval data; this plan ships the consumers.

Output: Modified `endgame_repository.py` (three queries rewritten), modified `endgame_service.py` (`_classify_endgame_bucket` helper + three call sites refactored + `_MATERIAL_ADVANTAGE_THRESHOLD` deleted), modified `game_position.py` Index, new Alembic migration, updated `tests/test_endgame_repository.py` / `tests/test_endgame_service.py` / `tests/test_aggregation_sanity.py`.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@.planning/milestones/v1.15-phases/78-stockfish-eval-cutover-for-endgame-classification/78-CONTEXT.md
@.planning/milestones/v1.15-phases/78-stockfish-eval-cutover-for-endgame-classification/78-SPEC.md
@.planning/milestones/v1.15-phases/78-stockfish-eval-cutover-for-endgame-classification/78-RESEARCH.md
@.planning/milestones/v1.15-phases/78-stockfish-eval-cutover-for-endgame-classification/78-PATTERNS.md
@.planning/milestones/v1.15-phases/78-stockfish-eval-cutover-for-endgame-classification/78-VALIDATION.md
@CLAUDE.md
@app/repositories/endgame_repository.py
@app/services/endgame_service.py
@app/models/game_position.py
@alembic/versions/20260327_093252_befacc0fce23_add_covering_index_for_endgame_queries.py

<interfaces>
<!-- New service-layer classification helper signature -->
```python
# app/services/endgame_service.py — NEW helper, replaces _MATERIAL_ADVANTAGE_THRESHOLD logic
from typing import Literal

EVAL_ADVANTAGE_THRESHOLD = 100  # centipawns; replaces _MATERIAL_ADVANTAGE_THRESHOLD


def _classify_endgame_bucket(
    eval_cp: int | None,
    eval_mate: int | None,
    user_color: str,
) -> Literal["conversion", "parity", "recovery"]:
    """Apply user-color sign flip, then threshold (REFAC-02).

    Mate at any non-zero value counts as max conversion / recovery.
    NULL eval (engine error / row not yet backfilled) → parity (safe default).
    """
    if eval_cp is None and eval_mate is None:
        return "parity"
    sign = 1 if user_color == "white" else -1
    if eval_mate is not None:
        user_mate = eval_mate * sign
        if user_mate > 0:
            return "conversion"
        if user_mate < 0:
            return "recovery"
        return "parity"  # mate_in_0 edge case
    assert eval_cp is not None
    user_cp = eval_cp * sign
    if user_cp >= EVAL_ADVANTAGE_THRESHOLD:
        return "conversion"
    if user_cp <= -EVAL_ADVANTAGE_THRESHOLD:
        return "recovery"
    return "parity"
```

<!-- New repository span_subq pattern (replaces lines 181-222 / 310-340 / 849-870) -->
```python
# app/repositories/endgame_repository.py — apply identically across all three queries
entry_eval_cp_agg = type_coerce(
    func.array_agg(aggregate_order_by(GamePosition.eval_cp, GamePosition.ply.asc())),
    ARRAY(SmallIntegerType),
)[1]
entry_eval_mate_agg = type_coerce(
    func.array_agg(aggregate_order_by(GamePosition.eval_mate, GamePosition.ply.asc())),
    ARRAY(SmallIntegerType),
)[1]

span_subq = (
    select(
        GamePosition.game_id.label("game_id"),
        GamePosition.endgame_class.label("endgame_class"),
        entry_eval_cp_agg.label("entry_eval_cp"),
        entry_eval_mate_agg.label("entry_eval_mate"),
    )
    .where(GamePosition.user_id == user_id, GamePosition.endgame_class.isnot(None))
    .group_by(GamePosition.game_id, GamePosition.endgame_class)
    .having(func.count(GamePosition.ply) >= ENDGAME_PLY_THRESHOLD)
    .subquery("span")
)
```

<!-- Output row shape: project eval columns directly (no SQL color flip — service layer handles) -->
```python
stmt = (
    select(
        Game.id.label("game_id"),
        span_subq.c.endgame_class,
        Game.result,
        Game.user_color,
        span_subq.c.entry_eval_cp.label("eval_cp"),
        span_subq.c.entry_eval_mate.label("eval_mate"),
    )
    .join(span_subq, Game.id == span_subq.c.game_id)
    .where(Game.user_id == user_id)
)
```

<!-- Alembic migration analog -->
```python
# alembic/versions/20260327_093252_befacc0fce23_add_covering_index_for_endgame_queries.py:25-39
op.create_index(
    'ix_gp_user_endgame_game',
    'game_positions',
    ['user_id', 'game_id', 'endgame_class', 'ply'],
    unique=False,
    postgresql_where=sa.text('endgame_class IS NOT NULL'),
    postgresql_include=['material_imbalance'],
)
```

<!-- Index model definition target (app/models/game_position.py:26-31) -->
```python
# CURRENT
Index(
    "ix_gp_user_endgame_game",
    "user_id", "game_id", "endgame_class", "ply",
    postgresql_where=text("endgame_class IS NOT NULL"),
    postgresql_include=["material_imbalance"],
),

# TARGET (D-12)
Index(
    "ix_gp_user_endgame_game",
    "user_id", "game_id", "endgame_class", "ply",
    postgresql_where=text("endgame_class IS NOT NULL"),
    postgresql_include=["eval_cp", "eval_mate"],
),
```

<!-- Existing alembic head — get the down_revision for the new migration -->
```bash
uv run alembic current  # prints current head, e.g. <hex>
uv run alembic heads    # confirms single head
```
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Update test fixtures + write classification rule tests (RED)</name>
  <files>tests/test_endgame_repository.py, tests/test_endgame_service.py, tests/test_aggregation_sanity.py</files>
  <read_first>
    - tests/test_endgame_repository.py (full file — `_seed_game_position` at lines 95-128, `TestQueryEndgameEntryRows` at 136-230)
    - tests/test_endgame_service.py (full file — `_FakeRow` NamedTuple at 48-63, classification tests)
    - tests/test_aggregation_sanity.py (`_make_endgame_row` at lines 112+)
    - .planning/milestones/v1.15-phases/78-stockfish-eval-cutover-for-endgame-classification/78-RESEARCH.md "REFAC-02: Classification Rule Unit Tests" (lines 821-850)
    - .planning/milestones/v1.15-phases/78-stockfish-eval-cutover-for-endgame-classification/78-PATTERNS.md "tests/test_endgame_*.py" sections
    - .planning/milestones/v1.15-phases/78-stockfish-eval-cutover-for-endgame-classification/78-VALIDATION.md
  </read_first>
  <behavior>
    - `_seed_game_position` in `tests/test_endgame_repository.py` accepts `eval_cp: int | None = None`, `eval_mate: int | None = None` parameters and writes them to the GamePosition row.
    - All conversion / recovery tests in `tests/test_endgame_repository.py` are updated to seed `eval_cp` (or `eval_mate`) values instead of `material_imbalance` and assert on the new row tuple shape `(game_id, endgame_class, result, user_color, eval_cp, eval_mate)`.
    - `_FakeRow` in `tests/test_endgame_service.py` is renamed/refactored: fields are `(game_id, endgame_class, result, user_color, eval_cp, eval_mate)` — `user_material_imbalance_after` is dropped.
    - New test class `TestClassifyEndgameBucket` in `tests/test_endgame_service.py` covers the cases listed in RESEARCH.md lines 826-850:
      - `_classify("white", eval_cp=150, eval_mate=None) == "conversion"`
      - `_classify("black", eval_cp=-300, eval_mate=None) == "conversion"`
      - `_classify("white", eval_cp=None, eval_mate=3) == "conversion"` (white mates in 3)
      - `_classify("white", eval_cp=None, eval_mate=-3) == "recovery"` (white being mated)
      - `_classify("white", eval_cp=50, eval_mate=None) == "parity"` (below threshold)
      - `_classify("white", eval_cp=None, eval_mate=None) == "parity"` (NULL eval)
      - `_classify("white", eval_cp=-200, eval_mate=None) == "recovery"`
    - `tests/test_aggregation_sanity.py` `_make_endgame_row` helper is updated to take `eval_cp` / `eval_mate` instead of `material_imbalance` (or in addition, depending on what other fields the helper still needs).
  </behavior>
  <action>
    Make all test changes in this single task. Tests should fail (RED) until Task 2 lands the production refactor. The fixture / helper updates here are mechanical renames and parameter additions; the new `TestClassifyEndgameBucket` class is genuinely new behavior.

    1. **`tests/test_endgame_repository.py`:**
       - Modify `_seed_game_position` to add `eval_cp: int | None = None`, `eval_mate: int | None = None` parameters and pass them to `GamePosition(...)`.
       - Update every existing test that asserts on conversion / recovery — change seeded `material_imbalance=N` to `eval_cp=N` (preserving the 1:1 numeric semantics, since the threshold is the same `100`).
       - Update row-tuple destructuring from `(game_id, endgame_class, result, user_color, user_material_imbalance, user_material_imbalance_after)` to `(game_id, endgame_class, result, user_color, eval_cp, eval_mate)`.
       - Keep `material_imbalance` parameter on `_seed_game_position` (default = 0) — the column still exists per REFAC-05, and other tests may still pass it for orthogonal reasons.
       - For tests that originally seeded both `material_imbalance` at entry AND at entry+4 to test the contiguity proxy: collapse to a single `eval_cp` seed; the persistence requirement is gone.

    2. **`tests/test_endgame_service.py`:**
       - Rename `_FakeRow` fields: drop `user_material_imbalance_after`; rename `user_material_imbalance` → `eval_cp` and add `eval_mate: Any`. Final field order: `(game_id, endgame_class, result, user_color, eval_cp, eval_mate)`.
       - Add new test class:
         ```python
         from app.services.endgame_service import _classify_endgame_bucket

         class TestClassifyEndgameBucket:
             def test_white_positive_cp_above_threshold_is_conversion(self):
                 assert _classify_endgame_bucket(eval_cp=150, eval_mate=None, user_color="white") == "conversion"

             def test_black_user_with_white_negative_cp_is_conversion(self):
                 assert _classify_endgame_bucket(eval_cp=-300, eval_mate=None, user_color="black") == "conversion"

             def test_user_mate_for_white_is_conversion(self):
                 assert _classify_endgame_bucket(eval_cp=None, eval_mate=3, user_color="white") == "conversion"

             def test_user_being_mated_is_recovery(self):
                 assert _classify_endgame_bucket(eval_cp=None, eval_mate=-3, user_color="white") == "recovery"

             def test_below_threshold_is_parity(self):
                 assert _classify_endgame_bucket(eval_cp=50, eval_mate=None, user_color="white") == "parity"

             def test_null_eval_is_parity(self):
                 assert _classify_endgame_bucket(eval_cp=None, eval_mate=None, user_color="white") == "parity"

             def test_white_negative_cp_is_recovery(self):
                 assert _classify_endgame_bucket(eval_cp=-200, eval_mate=None, user_color="white") == "recovery"

             def test_threshold_boundary_inclusive_at_100(self):
                 assert _classify_endgame_bucket(eval_cp=100, eval_mate=None, user_color="white") == "conversion"

             def test_threshold_boundary_exclusive_at_99(self):
                 assert _classify_endgame_bucket(eval_cp=99, eval_mate=None, user_color="white") == "parity"
         ```
       - Update existing tests that consume `_FakeRow` to use the new field names.

    3. **`tests/test_aggregation_sanity.py`:**
       - `_make_endgame_row` helper at line ~112: replace the `material_imbalance` parameter with `eval_cp` / `eval_mate` (or rename, depending on how the helper assembles the row).
       - If existing tests import `_MATERIAL_ADVANTAGE_THRESHOLD` from `endgame_service`, replace with `EVAL_ADVANTAGE_THRESHOLD`.
  </action>
  <verify>
    <automated>
      uv run pytest tests/test_endgame_service.py::TestClassifyEndgameBucket -x 2>&1 | tail -20
      # Expected RED: ImportError on _classify_endgame_bucket from app.services.endgame_service.
      grep -rn "user_material_imbalance_after" tests/ | wc -l
      # Should drop to 0 after this task; if non-zero, search and remove remaining references.
    </automated>
  </verify>
  <acceptance_criteria>
    - `grep -n "TestClassifyEndgameBucket" tests/test_endgame_service.py` returns a match.
    - `grep -rn "user_material_imbalance_after" tests/` returns 0 matches.
    - `grep -rn "_MATERIAL_ADVANTAGE_THRESHOLD" tests/` returns 0 matches (or matches only `EVAL_ADVANTAGE_THRESHOLD`).
    - `_seed_game_position` signature includes `eval_cp` and `eval_mate` parameters (`grep -A3 "def _seed_game_position" tests/test_endgame_repository.py`).
    - `_FakeRow` field list includes `eval_cp` and `eval_mate`, NOT `user_material_imbalance_after` (`grep -A8 "class _FakeRow" tests/test_endgame_service.py`).
    - Pytest output shows `ImportError` or `AttributeError` on `_classify_endgame_bucket` (RED phase confirmed).
  </acceptance_criteria>
  <done>Test fixtures updated; new classification rule tests added; suite is RED on missing `_classify_endgame_bucket` import.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Refactor repository + service layer + index model + Alembic migration (GREEN)</name>
  <files>app/repositories/endgame_repository.py, app/services/endgame_service.py, app/models/game_position.py, alembic/versions/&lt;new_revision&gt;_reshape_ix_gp_user_endgame_game_for_eval.py</files>
  <read_first>
    - app/repositories/endgame_repository.py (full file — three queries at 145-258, 261-386, 800-956; `_MATERIAL_ADVANTAGE_THRESHOLD` if present, `PERSISTENCE_PLIES` at line 71)
    - app/services/endgame_service.py (full file — `_MATERIAL_ADVANTAGE_THRESHOLD` at 164, `_aggregate_endgame_stats` at 176-266, `_compute_score_gap_material` at 638-755, `_endgame_skill_from_bucket_rows` at 884-960)
    - app/models/game_position.py (full file — index at 26-31, columns)
    - alembic/versions/20260327_093252_befacc0fce23_add_covering_index_for_endgame_queries.py (precedent recipe)
    - .planning/milestones/v1.15-phases/78-stockfish-eval-cutover-for-endgame-classification/78-RESEARCH.md "Repository Query Refactor" (lines 533-665) AND "Index INCLUDE Migration" (lines 668-752)
    - .planning/milestones/v1.15-phases/78-stockfish-eval-cutover-for-endgame-classification/78-PATTERNS.md sections for endgame_repository.py, endgame_service.py, game_position.py, alembic
    - tests/test_endgame_repository.py / tests/test_endgame_service.py / tests/test_aggregation_sanity.py (the contracts from Task 1)
  </read_first>
  <action>
    Atomic refactor — all four file changes ship in this single task / commit so the codebase is never in a misclassifying intermediate state.

    **Step A: `app/repositories/endgame_repository.py`** (the three queries):

    For each of `query_endgame_entry_rows`, `query_endgame_bucket_rows`, `query_endgame_elo_timeline_rows`:
    1. Replace the `entry_imbalance_agg` / `raw_imbalance_after` / `ply_at_persistence` / `imbalance_after_persistence_agg` block with the new `entry_eval_cp_agg` / `entry_eval_mate_agg` pair (see `<interfaces>` block above).
    2. Update the `span_subq` `.select(...)` projection to label `entry_eval_cp` and `entry_eval_mate` (drop `entry_imbalance_after`).
    3. Update the main `stmt` projection to drop the `color_sign` multiplication on the eval columns — project `eval_cp` and `eval_mate` raw (white-perspective). Service layer applies the sign flip per REFAC-02 / RESEARCH.md recommendation.
    4. Drop `PERSISTENCE_PLIES = 4` constant at line 71 entirely.
    5. Update the index-only-scan comments at lines 177 and 302 to reference `eval_cp` / `eval_mate` rather than `material_imbalance`.

    **Step B: `app/services/endgame_service.py`**:

    1. Define new constant near the existing `_MATERIAL_ADVANTAGE_THRESHOLD` location (line ~164): `EVAL_ADVANTAGE_THRESHOLD = 100`. Delete `_MATERIAL_ADVANTAGE_THRESHOLD`.
    2. Add `_classify_endgame_bucket` helper (signature in `<interfaces>` block) above `_aggregate_endgame_stats`.
    3. Update three call sites:
       - `_aggregate_endgame_stats` (lines 176-266): change tuple destructuring from `(game_id, ec, result, user_color, user_material_imbalance, user_material_imbalance_after)` to `(game_id, ec, result, user_color, eval_cp, eval_mate)`. Replace the double-threshold `if` blocks (240-248 conversion, 250-266 recovery) with:
         ```python
         bucket = _classify_endgame_bucket(eval_cp=eval_cp, eval_mate=eval_mate, user_color=user_color)
         if bucket == "conversion":
             conv[endgame_class]["games"] += 1
             # ... existing conversion accumulation logic
         elif bucket == "recovery":
             recov[endgame_class]["games"] += 1
             # ... existing recovery accumulation logic
         # parity → no accumulator update (existing behavior)
         ```
       - `_compute_score_gap_material` (lines 638-755): same pattern. Note the existing `TestScoreGapMaterialInvariant` test at line 691 — this test must be updated in tandem (Task 1 covers this but verify the executor's helper updates landed).
       - `_endgame_skill_from_bucket_rows` (lines 884-960): same pattern. Already uses tuple unpacking so the update is just field rename + helper call.
    4. Audit for any other reference to `user_material_imbalance` or `user_material_imbalance_after` and remove.

    **Step C: `app/models/game_position.py`**:

    1. Update `Index("ix_gp_user_endgame_game", ...)` at lines 26-31 to set `postgresql_include=["eval_cp", "eval_mate"]`.
    2. Update the surrounding comment block (lines 22-25) to mention `eval_cp` / `eval_mate` instead of `material_imbalance` for index-only scans of `array_agg(eval_cp ORDER BY ply)` / `array_agg(eval_mate ORDER BY ply)`.
    3. **Do NOT remove the `material_imbalance` column declaration** (REFAC-05). Verify it's still in the model.

    **Step D: New Alembic migration** at `alembic/versions/<rev>_reshape_ix_gp_user_endgame_game_for_eval.py`:

    Generate the migration via:
    ```bash
    uv run alembic revision -m "reshape ix_gp_user_endgame_game for eval columns"
    ```
    Then edit the generated file to fill in `upgrade()` and `downgrade()` matching the analog (`befacc0fce23`):

    ```python
    """reshape ix_gp_user_endgame_game for eval columns

    Phase 78 REFAC-04 / D-12: drop+recreate ix_gp_user_endgame_game with
    INCLUDE(eval_cp, eval_mate) so the rewritten endgame queries stay index-only.
    `material_imbalance` is no longer projected by these queries (REFAC-03);
    keeping it in INCLUDE wastes index space.

    Revision ID: <generated>
    Revises: <previous head>
    Create Date: <generated>
    """
    from typing import Sequence, Union

    import sqlalchemy as sa
    from alembic import op


    revision: str = "<generated>"
    down_revision: Union[str, Sequence[str], None] = "<previous head — get via `uv run alembic current`>"
    branch_labels: Union[str, Sequence[str], None] = None
    depends_on: Union[str, Sequence[str], None] = None


    def upgrade() -> None:
        op.drop_index(
            "ix_gp_user_endgame_game",
            table_name="game_positions",
            postgresql_where=sa.text("endgame_class IS NOT NULL"),
        )
        op.create_index(
            "ix_gp_user_endgame_game",
            "game_positions",
            ["user_id", "game_id", "endgame_class", "ply"],
            unique=False,
            postgresql_where=sa.text("endgame_class IS NOT NULL"),
            postgresql_include=["eval_cp", "eval_mate"],
        )


    def downgrade() -> None:
        op.drop_index(
            "ix_gp_user_endgame_game",
            table_name="game_positions",
            postgresql_where=sa.text("endgame_class IS NOT NULL"),
        )
        op.create_index(
            "ix_gp_user_endgame_game",
            "game_positions",
            ["user_id", "game_id", "endgame_class", "ply"],
            unique=False,
            postgresql_where=sa.text("endgame_class IS NOT NULL"),
            postgresql_include=["material_imbalance"],
        )
    ```

    **Migration ordering note:** Operator schedules the migration during low-traffic hours (RESEARCH.md Risk 9 — DROP+CREATE INDEX briefly locks writes). For prod, the migration runs automatically on backend container startup via `deploy/entrypoint.sh` per CLAUDE.md — but Plan 78-06 sequences the prod backfill BEFORE merge+deploy, so the migration runs as part of Plan 78-06's deploy step, not separately.

    **No CONCURRENTLY for now:** stay with the simple symmetric drop+recreate. The partial index covers only endgame rows (~hundreds of thousands, not millions), so the lock window is small. If operator observes lock issues during Plan 78-06's deploy, we revisit with a CONCURRENTLY follow-up — out of scope for this plan.

    **Verify migration applies cleanly:**
    ```bash
    uv run alembic upgrade head            # apply on dev DB
    uv run alembic downgrade -1            # roll back
    uv run alembic upgrade head            # re-apply
    ```
  </action>
  <verify>
    <automated>
      # Step A verification
      grep -n "PERSISTENCE_PLIES" app/repositories/endgame_repository.py app/services/endgame_service.py
      # MUST be 0 matches
      grep -rn "_MATERIAL_ADVANTAGE_THRESHOLD\|PERSISTENCE_PLIES" app/ scripts/ tests/
      # MUST be 0 matches (REFAC-03 grep gate)
      grep -n "imbalance_after_persistence\|raw_imbalance_after\|ply_at_persistence" app/repositories/endgame_repository.py
      # MUST be 0 matches
      grep -cE "array_agg.*eval_cp\|array_agg.*eval_mate" app/repositories/endgame_repository.py
      # MUST be >= 6 (3 queries × 2 columns)
      # Step B
      grep -n "_classify_endgame_bucket\|EVAL_ADVANTAGE_THRESHOLD" app/services/endgame_service.py
      # >= 4 matches (1 const, 1 def, 3 call sites)
      grep -n "user_material_imbalance" app/services/endgame_service.py
      # 0 matches (Step B done)
      # Step C
      grep -n "postgresql_include=\\[.eval_cp.,.*eval_mate.\\]" app/models/game_position.py
      # exactly 1 match
      grep -n "material_imbalance" app/models/game_position.py
      # MUST be >= 1 (column declaration is preserved per REFAC-05)
      # Step D
      ls alembic/versions/ | grep -i "reshape_ix_gp_user_endgame_game" | wc -l
      # exactly 1 file
      grep -rn "postgresql_include=\\[.eval_cp.,.*eval_mate.\\]" alembic/versions/
      # at least 1 match (the new migration)
      # Migration round-trip
      uv run alembic upgrade head
      uv run alembic downgrade -1
      uv run alembic upgrade head
      # Lint + type check + tests
      uv run ruff check app/ tests/ alembic/versions/
      uv run ty check app/ tests/
      uv run pytest tests/test_endgame_repository.py tests/test_endgame_service.py tests/test_aggregation_sanity.py -x
      # All GREEN.
    </automated>
  </verify>
  <acceptance_criteria>
    - `grep -rn "_MATERIAL_ADVANTAGE_THRESHOLD\|PERSISTENCE_PLIES" app/ scripts/ tests/` returns ZERO matches (REFAC-03 grep gate).
    - `grep -n "imbalance_after_persistence\|raw_imbalance_after\|ply_at_persistence" app/repositories/endgame_repository.py` returns ZERO matches.
    - `grep -cE "array_agg.*eval_cp|array_agg.*eval_mate" app/repositories/endgame_repository.py` returns at least 6 (three queries × two columns; the value should match exactly 3 occurrences for `eval_cp` and 3 for `eval_mate`).
    - `grep -n "_classify_endgame_bucket" app/services/endgame_service.py` returns at least 4 matches (1 def + 3 call sites).
    - `grep -n "EVAL_ADVANTAGE_THRESHOLD" app/services/endgame_service.py` returns at least 1 match (constant defined).
    - `grep -n "user_material_imbalance" app/services/endgame_service.py app/repositories/endgame_repository.py` returns ZERO matches.
    - `app/models/game_position.py`: index INCLUDE is `['eval_cp', 'eval_mate']`; `material_imbalance` Column declaration STILL EXISTS (REFAC-05).
    - Exactly one new file under `alembic/versions/` named `*reshape_ix_gp_user_endgame_game_for_eval*.py`.
    - The new migration's `down_revision` matches `uv run alembic current` from before the change.
    - `uv run alembic upgrade head && uv run alembic downgrade -1 && uv run alembic upgrade head` all exit 0.
    - `uv run ty check app/ tests/` exits 0 (zero errors per CLAUDE.md).
    - `uv run pytest tests/test_endgame_repository.py tests/test_endgame_service.py tests/test_aggregation_sanity.py -x` exits 0 (Task 1 RED → GREEN).
    - Full test suite still passes: `uv run pytest -x` (no regressions in adjacent code).
  </acceptance_criteria>
  <done>Repository + service refactor + model index + Alembic migration shipped as one atomic change; all tests pass; proxy constants completely removed.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| Repository SQL → Service classifier | Row tuple shape changes; both layers update atomically or service misclassifies |
| Alembic migration → DB | Brief write lock during `DROP INDEX` + `CREATE INDEX` on `game_positions` |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-78-22 | Tampering | Service consumes old row shape against new query → silent misclassification | mitigate | Atomic refactor: repository, service, and tests change in one task. ty type check will flag tuple-unpack arity mismatches. Wave 0 tests (Task 1) cover the new shape; pre-merge run is the gate. |
| T-78-23 | Tampering | Half-applied refactor leaves a `_MATERIAL_ADVANTAGE_THRESHOLD` reference in dead code | mitigate | REFAC-03 grep gate: `grep -rn "_MATERIAL_ADVANTAGE_THRESHOLD\|PERSISTENCE_PLIES" app/ scripts/ tests/` MUST return 0 in Task 2 acceptance. |
| T-78-24 | DoS | Migration locks `game_positions` writes for too long on prod | mitigate (observe) | Partial index (only `endgame_class IS NOT NULL` rows) limits lock duration. Operator schedules migration during off-peak via Plan 78-06's deploy timing. CONCURRENTLY upgrade is a documented follow-up if needed. |
| T-78-25 | DoS | Index INCLUDE shape regresses to `Heap Fetches > 0` on rewritten queries | mitigate (verify) | EXPLAIN (ANALYZE, BUFFERS) verification is a Plan 78-06 manual step on benchmark DB before prod cutover. If Heap Fetches non-zero, a follow-up migration adjusts INCLUDE. |
| T-78-26 | Repudiation | Downgrade path missing → cannot roll back migration | mitigate | Symmetric `downgrade()` defined; restores `INCLUDE(material_imbalance)`. Tested via `alembic downgrade -1 && alembic upgrade head` round-trip in Task 2 verification. |
| T-78-27 | Tampering | `material_imbalance` column accidentally dropped (REFAC-05 violation) | mitigate | Task 2 acceptance criteria explicitly assert `grep -n "material_imbalance" app/models/game_position.py` returns ≥1 match. Migration only changes INCLUDE clause, never the underlying column. |
</threat_model>

<verification>
- REFAC-03 grep gate: `grep -rn "_MATERIAL_ADVANTAGE_THRESHOLD\|PERSISTENCE_PLIES" app/ scripts/ tests/` returns 0 matches.
- All three queries project `eval_cp` and `eval_mate` (grep test).
- `_classify_endgame_bucket` is the single classification helper, called from all three service-layer sites.
- Alembic migration applies and rolls back cleanly on dev DB.
- `uv run ty check app/ tests/` exits 0.
- Full pytest suite green.
</verification>

<success_criteria>
- Three repository queries threshold on eval, not material; persistence patterns deleted.
- Service layer uses `_classify_endgame_bucket(eval_cp, eval_mate, user_color)`; `_MATERIAL_ADVANTAGE_THRESHOLD` deleted, replaced by `EVAL_ADVANTAGE_THRESHOLD = 100`.
- Index `ix_gp_user_endgame_game` reshaped via Alembic to `INCLUDE(eval_cp, eval_mate)`.
- `material_imbalance` column preserved (REFAC-05).
- All tests updated and passing.
</success_criteria>

<output>
After completion, create `.planning/milestones/v1.15-phases/78-stockfish-eval-cutover-for-endgame-classification/78-05-SUMMARY.md` recording: the new Alembic revision hash, line count delta in `endgame_repository.py` (proxy code removed), confirmation that ty check is clean, summary of test changes.
</output>
