# Phase 141: JSONB Schema + Gate Logic - Pattern Map

**Mapped:** 2026-06-29
**Files analyzed:** 5 (2 modify, 3 create)
**Analogs found:** 5 / 5

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `app/models/game_flaw.py` (MODIFY) | model | transform (write-once blob) | `app/models/llm_log.py` (JSONB cols) + own existing `allowed_*`/`missed_*` tactic cols | exact |
| `alembic/versions/<new>.py` (CREATE) | migration | batch (DDL) | `alembic/versions/20260619_134442_9be5294cfe3c_add_tactic_depth_to_game_flaws.py` | exact (adds nullable col to `game_flaws`) |
| `app/services/forcing_line_gate.py` (NEW) | service (utility) | transform (pure math) | `app/services/eval_utils.py` | exact (pure win-prob math, named constants, no DB/engine) |
| `tests/services/test_forcing_line_gate.py` (NEW) | test | transform | `tests/services/test_eval_utils.py` | exact (pure-unit, no DB/engine fixtures) |
| `tests/test_game_flaws_model.py` (MODIFY/extend) — D-02c deferred-leak regression | test | CRUD | `tests/test_game_flaws_model.py` (existing GameFlaw ORM round-trip) | exact |

## Pattern Assignments

### `app/models/game_flaw.py` (model, write-once JSONB blob)

**Analog:** `app/models/llm_log.py` (JSONB pattern, D-06) + the existing tactic columns already in `game_flaw.py`.

**JSONB import + column pattern** — `app/models/llm_log.py` lines 13-15, 58, 60:
```python
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
# ...
filter_context: Mapped[dict] = mapped_column(JSONB, nullable=False)        # line 58 (NOT NULL variant)
response_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)   # line 60 (nullable variant — copy this)
```
Per D-06: no `MutableDict`/`MutableList` wrapper (write-once blobs), no manual asyncpg codec setup (auto-registered). D-05 blob is a **list** of per-node dicts, so type as `Mapped[list[Any] | None]` (note: `llm_log` used `dict`; the new columns hold a list-of-dicts, so use `list[Any]`). Add `from typing import Any` (the file currently imports only `Optional`).

**Deferred-leak guard (D-02 — NEW pattern, no codebase precedent):** Grep confirmed **zero** existing `deferred=True` mapper usages in `app/`. Apply it as a kwarg on `mapped_column`:
```python
allowed_pv_lines: Mapped[list[Any] | None] = mapped_column(JSONB, nullable=True, deferred=True)
missed_pv_lines: Mapped[list[Any] | None] = mapped_column(JSONB, nullable=True, deferred=True)
```
`deferred` is imported via `mapped_column(..., deferred=True)` (SQLAlchemy 2.x supports the kwarg directly — no separate `deferred()` import needed).

**Existing orientation convention to mirror** — `app/models/game_flaw.py` lines 68-94:
- `allowed_*` = refutation from the **flaw_ply+1** PV (the opponent's punishing line). → `allowed_pv_lines`.
- `missed_*` = best continuation from the **flaw_ply** PV (the engine's best move at the decision position). → `missed_pv_lines`.
The new columns follow the same two-orientation split. Place the two new declarations after the existing `missed_tactic_*` block (line 94) with a comment block matching the existing tactic-family comment style (lines 68-86).

**Column-comment style** — match the existing block comment density at lines 42-50 and 68-86 (every column family gets a `#` rationale; cite D-05 blob shape `{"b","bm","s","sm","su"}`, white-perspective cp).

---

### `alembic/versions/<new>.py` (migration, DDL batch)

**Analog:** `alembic/versions/20260619_134442_9be5294cfe3c_add_tactic_depth_to_game_flaws.py` (full file, 33 lines — adds a nullable col to `game_flaws`).

**Full boilerplate to copy**:
```python
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "<new_id>"
down_revision: Union[str, Sequence[str], None] = "c4d4588ed2b8"   # CURRENT HEAD (verified via `alembic heads`)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.add_column("game_flaws", sa.Column("allowed_pv_lines", postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column("game_flaws", sa.Column("missed_pv_lines", postgresql.JSONB(astext_type=sa.Text()), nullable=True))

def downgrade() -> None:
    op.drop_column("game_flaws", "missed_pv_lines")
    op.drop_column("game_flaws", "allowed_pv_lines")
```
**Down-revision is `c4d4588ed2b8`** — confirmed current head (`uv run alembic heads` → `c4d4588ed2b8 (head)`, file `20260626_074415_c4d4588ed2b8_add_user_activity.py`). Prefer `uv run alembic revision --autogenerate -m "add pv_lines blobs to game_flaws"` (CLAUDE.md command) which fills the revision id and `down_revision` automatically; add `from sqlalchemy.dialects import postgresql` for the JSONB import. No data backfill (STORE-01). Nullable columns → no table rewrite, safe on a populated `game_flaws`.

---

### `app/services/forcing_line_gate.py` (service/utility, pure math)

**Analog:** `app/services/eval_utils.py` (full file, 98 lines).

**Reuse, do not re-implement** — import the existing win-prob math (D-07, no new sigmoid):
```python
from app.services.eval_utils import (
    LICHESS_K,
    eval_cp_to_expected_score,
    eval_mate_to_expected_score,
)
```
`LICHESS_K = 0.00368208` lives at `eval_utils.py:41`; the cp→win-prob sigmoid is `eval_cp_to_expected_score` (lines 44-66); mate→0/1 is `eval_mate_to_expected_score` (lines 69-97). The only-move margin (`p(best) − p(second) > ONLY_MOVE_WIN_PROB_MARGIN`) is computed by calling `eval_cp_to_expected_score` twice; mate-priority (D-01) routes through `eval_mate_to_expected_score`.

**Named-constant pattern** — `eval_utils.py:38-41` (module-level, CLAUDE.md "no magic numbers"):
```python
# Lichess winning-chances sigmoid coefficient (sourced from Lichess accuracy page).
# Kept as a module-level named constant so callers reference the same canonical value.
LICHESS_K: float = 0.00368208
```
Declare every gate threshold the same way (D-07..D-10):
```python
ONLY_MOVE_WIN_PROB_MARGIN: float = 0.35   # D-07, tunable in Phase 144
ALREADY_WINNING_CP_THRESHOLD: int = 300    # D-08
STILL_WINNING_FLOOR_CP: int = 200          # D-09
```
Each constant gets a `#` comment citing its decision id and (for D-07) the lichess-puzzler provenance — AGPL boundary: copy the *value/name only*, no source.

**Module-docstring pattern** — `eval_utils.py:1-33` is the template: one-line summary, the sign convention, the constant provenance, the mate-handling note, and the closing line "No I/O, no DB, stdlib only. The module is unit-testable in isolation; see tests/services/test_<name>.py". Reproduce this structure (it is the load-bearing SC #2 property: zero engine, zero DB).

**Type-safety conventions** (CLAUDE.md ty rules): explicit return types on every function; use a `PvNode` TypedDict (Claude's discretion per CONTEXT) for the D-05 blob node `{"b","bm","s","sm","su"}` rather than `dict[str, Any]`; `Literal["white","black"]` for side-to-side params (mirrors `eval_utils` `user_color: Literal[...]`). White-perspective cp in storage; the gate converts to side-to-move at read time (D-05).

**Function-size discipline** (CLAUDE.md): keep `apply_forcing_line_filter()` an orchestrator; split each rejection rule (only-move margin, already-winning, still-winning floor, trailing-only-move strip, one-mover discard — D-10) into its own small predicate helper (`is_solver_node_forced()` etc.). Nesting hard-cap 4.

---

### `tests/services/test_forcing_line_gate.py` (test, pure unit — NO DB/engine)

**Analog:** `tests/services/test_eval_utils.py` (lines 1-60 read; class-grouped pure tests).

**Structure to copy**:
- Module docstring citing the phase + the decisions covered (mirror `test_eval_utils.py:1-14`).
- Plain `import pytest` + direct imports from the module under test (lines 16-25). **No** `db_session`, no `pytest_asyncio`, no engine fixtures — this is the SC #2 guarantee.
- Group by concern with `class TestXxx:` (e.g. `TestOnlyMoveMargin`, `TestMatePriority`, `TestAlreadyWinning`, `TestLineStripping`) — `test_eval_utils.py` uses `class TestSigmoid` / `class TestMate`.
- Assert the named constant's value directly (lines 31-33 pattern): `assert ONLY_MOVE_WIN_PROB_MARGIN == 0.35`.
- Use `pytest.approx(..., abs=1e-9)` for float comparisons (lines 37, 43).
- **Symmetry coverage** for mate handling — `test_eval_utils.py:56-60` exercises both colors to catch the asymmetric-sign class of bug (Pitfall 1). Apply the same both-sides discipline to the mate-priority hierarchy (D-01: only-best-is-mate, both-mates shorter-distance-wins, mate-in-1 never suppressed).

**Test data**: hand-construct `PvNode`/blob list literals inline (no fixtures, no DB). This is the whole point of the milestone — the gate operates on stored blobs, so tests feed literal blobs.

---

### `tests/test_game_flaws_model.py` — D-02c deferred-leak regression (extend existing file)

**Analog:** the file itself (`tests/test_game_flaws_model.py`, lines 1-94 read) — existing GameFlaw ORM round-trip with `db_session`, `ensure_test_user`, `_seed_game`, `_make_flaw_row` helpers already present. Add a new test (or `class TestDeferredBlobLeak`) reusing those helpers.

**Two assertion strategies for D-02c (pick one or both):**

1. **Unloaded-attribute check** (preferred — runtime proof): after a representative `select(GameFlaw).where(...)` and `scalar_one()`, assert the deferred attrs are NOT in the loaded state. Under SQLAlchemy async an *implicit* deferred access raises `MissingGreenlet` (D-02a), so use the inspection API rather than touching the attribute:
   ```python
   from sqlalchemy import inspect as sa_inspect
   flaw = (await session.execute(select(GameFlaw).where(...))).scalar_one()
   unloaded = sa_inspect(flaw).unloaded
   assert "allowed_pv_lines" in unloaded
   assert "missed_pv_lines" in unloaded
   ```

2. **Compiled-SQL check** (no session needed — pure statement inspection): assert the blob column names do not appear in the default `select(GameFlaw)` SQL. Compiled-SQL string assertions are an established pattern in this repo (`tests/test_query_utils.py`, `tests/test_flaw_predicate.py`, `tests/services/test_canonical_slice_sql.py`):
   ```python
   sql = str(select(GameFlaw).compile(compile_kwargs={"literal_binds": True}))
   assert "allowed_pv_lines" not in sql
   assert "missed_pv_lines" not in sql
   ```

**Seed-helper reuse** — `tests/test_game_flaws_model.py:31-64`: `_create_test_users` autouse fixture (uids 77001/77002), `_seed_game()` (flush to get id), `_make_flaw_row()`. The new regression test seeds one flaw row via these, then asserts the deferred columns stay unloaded on a stats-style select. Also worth an explicit `undefer()` round-trip test (proves the Phase 143 opt-in path works): `select(GameFlaw).options(undefer(GameFlaw.allowed_pv_lines))` then assert the attr loads.

---

## Shared Patterns

### Pure-math module convention (no DB, no engine)
**Source:** `app/services/eval_utils.py` (whole file)
**Apply to:** `forcing_line_gate.py` and its test.
Module-level named constants with provenance comments, `Literal` side params, explicit return types, docstring ending in "No I/O, no DB ... unit-testable in isolation". This is the load-bearing SC #2 property.

### JSONB column declaration
**Source:** `app/models/llm_log.py:13-15, 60`
**Apply to:** both new `game_flaw.py` columns.
```python
from sqlalchemy.dialects.postgresql import JSONB
response_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
```
(For Phase 141 the value type is `list[Any]`, and the two columns add `deferred=True`.)

### Nullable-column migration boilerplate
**Source:** `alembic/versions/20260619_134442_9be5294cfe3c_add_tactic_depth_to_game_flaws.py`
**Apply to:** the new migration. `op.add_column("game_flaws", sa.Column(..., nullable=True))` / `op.drop_column` symmetric down. down_revision = `c4d4588ed2b8`.

### GameFlaw test seeding
**Source:** `tests/test_game_flaws_model.py:31-64`
**Apply to:** the D-02c regression test. `_create_test_users` autouse fixture + `_seed_game` + `_make_flaw_row`.

### The 5 `select(GameFlaw)` audit sites (D-02a — confirm clean, do not rewrite per D-02b)
`deferred=True` makes these safe structurally; the audit confirms none implicitly touch the blob attrs:
- `app/repositories/library_repository.py:737` — `select(GameFlaw.ply)` — **column-projected, safe** (never selects entity).
- `app/repositories/library_repository.py:1017` — `select(GameFlaw, Game, PositionAt, PositionBefore, PositionTwoBefore)` — full entity; deferred cols won't load; downstream consumers read `severity/tempo/phase/is_*/fen/*_tactic_*` only — **confirm no blob access**.
- `app/repositories/library_repository.py:1118` — `select(GameFlaw)` (`fetch_page_game_flaws`, player-gated) — rows appended to a dict; no blob attr read — **safe**.
- `app/repositories/library_repository.py:1151` — `select(GameFlaw)` (`fetch_page_game_flaws_both_colors`) — same shape, no blob read — **safe**.
- `app/repositories/library_repository.py:2255` — `select(GameFlaw).where(user/game/ply)` (single-flaw fetch for tactic-lines detail) — returns one flaw; **this is the most likely future `undefer()` opt-in site (Phase 143), but in 141 it must not touch the blobs** — confirm.

## No Analog Found

None. Every file has a strong existing analog.

## Metadata

**Analog search scope:** `app/models/`, `app/services/`, `app/repositories/`, `alembic/versions/`, `tests/`, `tests/services/`
**Files scanned:** ~12 (3 analogs read in full: `llm_log.py`, `eval_utils.py`, the tactic-depth migration; `game_flaw.py`, `test_game_flaws_model.py`, `test_eval_utils.py`, and the 5 library_repository select sites read at targeted ranges)
**Pattern extraction date:** 2026-06-29
**Notable gap flagged:** `deferred=True` has **no existing usage** in `app/` — it is a new mapper pattern for this codebase (verified via grep). The planner should call this out so the executor adds it deliberately and the D-02c test proves it.
