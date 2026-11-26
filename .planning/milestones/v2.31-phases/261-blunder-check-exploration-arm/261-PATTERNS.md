# Phase 261: Blunder-Check Exploration Arm - Pattern Map

**Mapped:** 2026-11-22
**Files analyzed:** 20 (16 modified, 4 new incl. tests)
**Analogs found:** 20 / 20 (most are in-place edits; the file itself is the analog)

RESEARCH.md already carries exact current line numbers for every edit site (Patterns 1-6, "Current code
facts"). This map adds the concrete excerpts to copy and the analog for each new file.

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match |
|---|---|---|---|---|
| `app/services/blunder_check_rules.py` | utility (pure rules/constants) | transform | itself (`draw_slot_plan` l.326-335, `SlotPlan` l.176-181) | exact |
| `app/repositories/blunder_check_repository.py` | repository | CRUD (read) | itself (`_unserved_qualifying_blunder_exists` l.395-412, `load_blunder_flaws` l.631-677) | exact |
| `app/services/blunder_check_candidates.py` | service (pure) | transform | itself (`_blunder_candidate` l.203) | exact |
| `app/services/blunder_check_selection.py` | service | batch / transform | itself (`_new_window` l.729-754, rewrites l.589/696/710) | exact |
| `app/services/blunder_check_feedback.py` (NEW) | service (pure) | transform | `app/services/line_material.py` + `facepalm_material.py` (callers in `scripts/blunder_check/facepalm_features.py`) | role-match |
| `app/models/blunder_check.py` | model | — | itself (`WindowCase`/`WindowOutcome` IntEnums l.53-68, CHECKs l.140-163) | exact |
| `alembic/versions/2026xxxx_..._phase_261_...py` (NEW) | migration | — | `alembic/versions/20261128_120000_f3a7b9c1e259_phase_259_drop_material_arrays.py` | role-match |
| `app/services/blunder_check_service.py` | service | request-response | itself (`_blunder_solution` l.1125-1160) | exact |
| `app/schemas/blunder_check.py` | schema | request-response | itself (`BlunderSolution` l.199-219) | exact |
| `app/routers/blunder_check.py` | router | request-response | itself (`_blunder_solution_schema` l.398-419) | exact |
| `frontend/src/types/blunderCheck.ts` | types | — | itself (l.167-190) | exact |
| `frontend/src/lib/blunderCheckSolution.ts` | utility (copy) | transform | itself (`blunderCopy` l.216-239) | exact |
| `frontend/src/components/train/blunder-check/BlunderCheckSolution.tsx` | component | — | itself (`SolutionVerdict` l.232-254) | exact |
| `frontend/src/components/library/FacepalmChip.tsx` (+ `FacepalmBadgePopover.tsx`, `FacepalmExplanation.tsx`) | component | — | itself | exact |
| `frontend/src/lib/facepalm.ts`, `frontend/src/lib/theme.ts` | utility | — | itself (`facepalmScoreMeaning` l.61, `FAM_NEUTRAL` l.183-184) | exact |
| `scripts/blunder_check/caught_rate.py` (NEW) | script (read-only analysis) | batch | `scripts/blunder_check/facepalm_features.py` + `sample.py` | role-match |
| `tests/services/test_blunder_check_feedback.py` (NEW) | test | — | `tests/services/test_line_material.py` + `tests/services/line_material_fixtures.py` | role-match |
| `tests/scripts/test_caught_rate.py` (NEW) | test | — | `tests/scripts/test_blunder_check_calibration.py` | role-match |
| `tests/services/test_blunder_check_{rules,selection,candidates}.py`, `tests/repositories/test_blunder_check_repository.py`, `tests/routers/test_blunder_check_solution.py` | test | — | themselves (`TestSlotShares`, seed helpers in `tests/blunder_check_seed.py`) | exact |
| `CHANGELOG.md` | docs | — | `## [Unreleased]` section | exact |

## Pattern Assignments

### `app/services/blunder_check_rules.py` (pure rules)
Current shape to extend (l.326-335):
```python
def draw_slot_plan(rng: random.Random) -> SlotPlan:
    roll = rng.random()
    if roll < HERRING_SHARE:
        origin: SlotOrigin = "own" if rng.random() < HERRING_OWN_SHARE else "foreign"
        return SlotPlan(origin, draw_herring_shape(rng))
    if roll < HERRING_SHARE + OWN_BLUNDER_SHARE:
        return SlotPlan("own", draw_blunder_shape(rng))
    return SlotPlan("foreign", draw_blunder_shape(rng))
```
Add `SlotArm = Literal["main", "exploration"]`, `SlotPlan.arm: SlotArm = "main"` (third field with default so
positional `SlotPlan("own", shape)` in tests stays main), `EXPLORATION_SHARE: float = 0.2`,
`HARD_TO_CATCH_SCORE_MAX: float = 0.5`, `TYPE_LINE_MIN_SWING: int = 2` next to `FACEPALM_SCORE_MIN` (l.64),
each with a one-line comment like the existing share constants (l.138-140). Arm drawn only on the two blunder branches.

### `app/repositories/blunder_check_repository.py` (repository, read)
Probe predicate to parameterize (l.403-409):
```python
    conditions: list[ColumnElement[bool]] = [
        GameFlaw.game_id == game_id_col,
        facepalm_expr(FACEPALM_DRILL_LAMBDA) >= FACEPALM_SCORE_MIN,
        # Owner side only: a parity filter on the flaw rows the index probe already fetched.
        player_only_gate(GameFlaw.ply, user_color_col),
        not_(already_served),
    ]
```
Replace line 2 with `score.isnot(None) if min_score is None else score >= min_score` (RESEARCH "No-cut probe
predicate"). Thread `min_score: float | None = FACEPALM_SCORE_MIN` keyword through `pick_own_game_ids`,
`pick_foreign_game_ids`, `pick_nearest_foreign_game_ids`.

Loader (l.631-677): keep the "one bound expression" idiom; change the filter to `score.isnot(None)` and add the
five input columns to the select and to `BlunderFlawRow` (positional `BlunderFlawRow(*row[1:])` construction means
field order must match select order):
```python
    score = facepalm_expr(FACEPALM_DRILL_LAMBDA)
    stmt = (
        select(GameFlaw.game_id, GameFlaw.ply, GameFlaw.severity, GameFlaw.is_miss,
               score.label("facepalm_score"),
               # + GameFlaw.maia_played_prob, material_loss, material_missed, maia_best_prob, maia_best_reply_prob
        )
        ...
        .where(..., player_only_gate(GameFlaw.ply, Game.user_color), score >= FACEPALM_SCORE_MIN)  # -> isnot(None)
```
Update the docstring (it states ">= FACEPALM_SCORE_MIN"). `NewWindow` / `_window_row`: new fields with `None`
defaults.

### `app/services/blunder_check_selection.py` (composition)
`_new_window` (l.729-754) is where the snapshot is written; follow the existing conditional-on-`blunder_ply` style:
```python
        key_uci=None if blunder_ply is None else batch.positions[blunder_ply].best_move,
        refutation_uci=None
        if blunder_ply is None
        else _refutation_uci(batch.positions, blunder_ply),
```
Add `selection_arm`, `arm_probability`, score + 5 inputs (from a new `_Batch.flaws_by_ply[blunder_ply]`), and the
type-line facts (call into the new feedback module; keep `_new_window` depth <= 4 by delegating to a helper like
`_snapshot_fields(item) -> dict | None`). Best line pattern already in this file (l.~720-726):
```python
        return row.best_move
    return row.pv.split(_PV_SEPARATOR)[0] if row.pv else None
```
Plan rewrites at l.589, l.696, l.710 must become `dataclasses.replace(plans[slot], origin=..., shape=...)`.
PGN replay: reuse `_mainline` in this module. New `_next_probe(...)` pure helper for the round loop (Pitfall 10).

### `app/services/blunder_check_feedback.py` (NEW, pure transform)
**Analog:** imports as in `scripts/blunder_check/facepalm_features.py` l.70-74:
```python
from app.services.line_material import (
    LineFacts,
    quiet_best_line_facts,
    quiet_line_facts,
)
```
Functions to call: `quiet_line_facts(pre_board, played_uci, pv)` (line_material.py:294),
`quiet_best_line_facts(pre_board, best_pv)` (l.309), `LineFacts` (l.80, `mate_ply`, `opponent_mate_ply`,
`material_array()`), `loss_by_depth` (facepalm_material.py:64), `gain_by_depth` (l.99), `facepalm_type_of`
(facepalm_score.py:323-332). Constants from `blunder_check_rules` (`FACEPALM_LOSS_FLOOR`, `FACEPALM_MISSED_FLOOR`,
`FACEPALM_MISSED_CAP`, `FACEPALM_MISSED_MATE`). Full sketch: RESEARCH Pattern 4. Frozen dataclass result,
`Literal` for the type-line value (`"allowed_material" | "allowed_mate" | "missed_material" | "missed_mate"`).

### `app/models/blunder_check.py` (model)
IntEnum pattern (l.53-60):
```python
class WindowCase(IntEnum):
    """Which kind of judged window this is (stored as SMALLINT)."""

    HERRING = 0  # no blunder in the window: all moves are safe (a red herring)
    ALLOWED = 1
```
Add `class WindowArm(IntEnum): MAIN = 0; EXPLORATION = 1`. CHECK pattern (l.150-163):
```python
        CheckConstraint(
            "outcome IS NULL OR outcome IN (0, 1, 2, 3)", name="ck_blunder_check_windows_outcome"
        ),
        CheckConstraint(
            "(blunder_position IS NULL) = (blunder_ply IS NULL)",
            name="ck_blunder_check_windows_blunder_ply",
        ),
```
Name new CHECKs `ck_blunder_check_windows_<what>`; CHECK list in RESEARCH Pattern 5.

### Alembic migration (NEW)
**Analog:** `alembic/versions/20261128_120000_f3a7b9c1e259_phase_259_drop_material_arrays.py` (current head).
Copy the header shape: long docstring naming phase + decisions, then
```python
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "<new>"
down_revision: Union[str, None] = "f3a7b9c1e259"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None
```
and its rule: "Literal values only: migrations are version-pinned snapshots and must not import live app
constants." Use `op.add_column(..., nullable=True)` + `op.create_check_constraint`; downgrade drops in reverse.

### `app/services/blunder_check_service.py` + `app/schemas/blunder_check.py` + `app/routers/blunder_check.py`
`_blunder_solution` (service l.1125-1160) builds `BlunderSolutionData(...)` keyword by keyword; add
`feedback=_feedback(window, caught)` returning `None` when `window.facepalm_score is None`. Schema: append to
`BlunderSolution` (schemas l.199-219) `feedback: BlunderFeedback | None` with a new small `BaseModel` and a
`Literal` alias like the existing `WindowCaseWire` / `MoveTierWire`. Router `_blunder_solution_schema`
(l.398-419) maps the field. `FalseAlarmSolution` / `HerringSolution` untouched (D-05).

### `frontend/src/lib/blunderCheckSolution.ts` (copy)
`blunderCopy` (l.216-239) returns `{ heading, parts: [...] }`; extend `SolutionCopy` with
`feedback: { score: number; lines: string[] } | null` and fill it from `solution.feedback`; herring/false-alarm
copies return `feedback: null`. Map type-line literals to copy with a `Record<BlunderTypeLine, string>` (pattern:
`FACEPALM_TYPE_SENTENCE` in `lib/facepalm.ts` l.196).

### `frontend/src/components/train/blunder-check/BlunderCheckSolution.tsx`
`SolutionVerdict` (l.232-254) renders `<p data-testid="blunder-check-solution-summary">`; add a second `<p
data-testid="blunder-check-solution-feedback">` directly after it with the chip and lines, rendered only when
`copy.feedback !== null`. Used by both card and strip, so one edit covers D-03.

### `frontend/src/components/library/FacepalmChip.tsx` (neutral variant)
Current:
```tsx
export function FacepalmChip({ score, type, gameId, ply }: FacepalmChipProps) {
  const style = FACEPALM_TYPE_STYLE[type];
  return (
    <FacepalmBadgePopover testId={`facepalm-badge-${gameId}-${ply}`} score={score} type={type}>
```
Make `type` optional (absent -> neutral style, popover omits type label), add an optional `testId` prop (drill
passes literal `blunder-check-facepalm-badge`). Update the header comment ("there is no neutral variant").
Neutral tint: export a token from `theme.ts` (currently `const FAM_NEUTRAL` / `FAM_NEUTRAL_BG` l.183-184 are
private; follow the `export const FAM_TEMPO = FAM_NEUTRAL;` aliasing pattern l.185-192).
`facepalmScoreMeaning(byOpponent = false)` (facepalm.ts l.61-64) needs a neutral audience; change the boolean to a
`'self' | 'opponent' | 'neutral'` literal param or add a sibling function (knip: no dead exports).

### `scripts/blunder_check/caught_rate.py` (NEW, read-only analysis)
**Analog:** `scripts/blunder_check/facepalm_features.py`. Bootstrap (l.50-55, 79):
```python
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_REPO_ROOT))

from app.core.config import db_url_for_target  # noqa: E402
...
from scripts.blunder_check.sample import make_readonly_engine  # noqa: E402
```
Note facepalm_features.py l.56-62: import `OAuthAccount` and `User` models (`# noqa: E402, F401`) before any
`select()` compiles. Args/run (l.360, 662-664, 694-725):
```python
DB_TARGETS: tuple[str, ...] = ("dev", "prod")
parser.add_argument("--db", choices=DB_TARGETS, required=True, help="read-only source database")
...
    engine = make_readonly_engine(db_url_for_target(args.db))
    try:
        async with engine.connect() as conn:
            ...
    finally:
        await engine.dispose()

def main(argv: Sequence[str] | None = None) -> int:
    return asyncio.run(_run(_parse_args(argv)))
```
Wilson: `wilson_bounds(p, n, z=CI_Z_95)` from `app/services/score_confidence.py:84`. Keep aggregation pure
(testable without DB) per RESEARCH.

### Tests
- `tests/services/test_blunder_check_feedback.py`: reuse fixtures in `tests/services/line_material_fixtures.py`
  (fixture 13, 154 named in RESEARCH Validation) the way `tests/services/test_line_material.py` does.
- Selection/repository tests: use `tests/blunder_check_seed.py` helpers with `finally` cleanup
  (`delete_games`, `delete_blunder_check_sessions`); foreign tests set `FOREIGN_SAMPLE_PERCENT` to 100.
- Extend `TestSlotShares` in `tests/services/test_blunder_check_rules.py` for the seeded 20% check.
- Frontend fixtures: add `feedback: null` to all `BlunderSolution` fixtures (Pitfall 7).

## Shared Patterns

### No native ENUM: SMALLINT + IntEnum + CHECK
**Source:** `app/models/blunder_check.py` l.53-68, 150-163. Apply to `selection_arm`.

### Literal-only migrations
**Source:** f3a7b9c1e259 docstring. Apply to the new migration (no imports of app constants).

### Named constants in rules module
**Source:** `app/services/blunder_check_rules.py` (`FACEPALM_SCORE_MIN` l.64, shares l.138-140). Apply to
`EXPLORATION_SHARE`, `HARD_TO_CATCH_SCORE_MAX`, `TYPE_LINE_MIN_SWING`, and the calibration score bands.

### Plan immutability
`SlotPlan` is a frozen dataclass; rewrite with `dataclasses.replace` (as `facepalm_features.py` imports
`replace`) so the arm survives.

### Read-only DB scripts
`make_readonly_engine(db_url_for_target(args.db))` from `scripts/blunder_check/sample.py`; one connection on prod.

## No Analog Found

None. The type-line module is new but composes existing pure functions only.

## Metadata

**Analog search scope:** `app/services`, `app/repositories`, `app/models`, `app/schemas`, `alembic/versions`,
`scripts/blunder_check`, `frontend/src/{lib,components/library,components/train/blunder-check}`, `tests/services`
**Files scanned:** ~15 (all git-tracked)
**Pattern extraction date:** 2026-11-22
