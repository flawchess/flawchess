# Phase 244: Train SR Ladder Rework, Calculation Not Recall - Pattern Map

**Mapped:** 2026-11-02
**Files analyzed:** 13 (new/modified)
**Analogs found:** 13 / 13 (most edits are in-place; the two new files have exact analogs)

**Alembic head:** `b7e4c2a9f013` (`alembic/versions/20261031_120000_b7e4c2a9f013_opening_out_metrics_and_percentile_color.py`, down_revision `5448f030de58`). New revision sets `down_revision = "b7e4c2a9f013"`. Re-check with `uv run alembic heads` at execution time.

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `app/services/train_scheduler.py` (modify) | service (pure) | transform | itself (`apply_result` lines 264-362) | exact |
| `app/repositories/train_repository.py` (modify, ~3125 call site, ~443 note) | repository | CRUD | itself | exact |
| `app/models/drill_item.py` (docstring only, lines 1-8) | model | n/a | itself | exact |
| `alembic/versions/<ts>_<rev>_phase_244_sr_ladder_due_date_push.py` (NEW) | migration (data-only) | batch | `alembic/versions/20260614_130000_wipe_eval_only_residue.py` | exact (data-only, no-op downgrade, literal constants) |
| `tests/test_migration_244_sr_ladder_due_dates.py` (NEW) | test (integration, DB) | batch | `tests/test_migration_wipe_eval_only_residue.py` (+ idempotency re-run from `tests/test_migration_suppress_ungated_tactic_tags.py:196-225`) | exact |
| `tests/services/test_train_scheduler.py` (modify) | test (unit, pure) | transform | itself (`TestApplyResultCorrect` lines 84-160, Door B tests 200-295) | exact |
| `tests/routers/test_train.py` (check, ~1650 `test_solve_masters_item_at_three`, docstring line 42) | test (integration) | request-response | itself | exact |
| `frontend/src/pages/Home.tsx:69` | component copy | n/a | itself | exact |
| `frontend/src/lib/trainBotCopy.ts:521` `MASTERED_TAIL` | utility copy | n/a | itself | exact |
| `frontend/src/components/train/TrainStatsCard.tsx:33-41` | component copy | n/a | itself | exact |
| `README.md:36` | docs | n/a | itself | exact |
| `app/core/dev_clock.py:4-8` | docstring | n/a | itself (wording is generic "ladder spaces repeats out by days"; likely no change) | exact |
| `CHANGELOG.md` `[Unreleased]` | docs | n/a | existing entries | exact |

## Pattern Assignments

### `app/services/train_scheduler.py` (service, pure transform)

Current constants (lines 43-61) to replace:
```python
LADDER_DAYS: dict[int, int] = {0: 0, 1: 3, 2: 10}
MASTERY_STREAK_THRESHOLD: int = 3
PARK_FAIL_THRESHOLD: int = 3
# Door B: 6 LIFETIME lapses ... 6, not Anki's leech default of 8 ... (rationale to rewrite per D-04)
LEECH_FAIL_THRESHOLD: int = 6
```
Keep the existing convention: each constant has a typed annotation and a comment block above it explaining the "why".

Signature to change (lines 264-266):
```python
def apply_result(
    state: ItemState, *, correct_move: bool, today: datetime.date, weekday_mask: int
) -> ItemState:
```
Correct branch due date (lines 325-330): `ideal_due = today + timedelta(days=LADDER_DAYS[new_streak])` then `next_scheduled_day(ideal_due, weekday_mask)` -> becomes `today + timedelta(days=CORRECT_RETRY_DAYS)` (D-02). Mastery check at line 315 `if new_streak >= MASTERY_STREAK_THRESHOLD:` stays structurally. Fail branch final return (lines 356-362) `due_date=next_scheduled_day(today, weekday_mask)` -> `today + timedelta(days=FAIL_RETRY_DAYS)`. Preserve the two "Bug fix"/"Silent-corruption trap" comments (fail_count carry-through, ever_correct propagation).

Docs to rewrite: module docstring lines 21-26 (Door B "6", "3 consecutive", "alternation caps the streak at 1"); `apply_result` docstring lines 269-307 (`weekday_mask` arg, "due-date snapping", `LADDER_DAYS` reference, "re-snap"); `next_scheduled_day` docstring cross-ref lines 231-234 ("`apply_result` calls this to snap..." must go; `session_window` stays). Note D-11/owner correction: do not call first attempts "no memory possible".

`__all__` (line 641+): remove `"LADDER_DAYS"`, add `"CORRECT_RETRY_DAYS"`, `"FAIL_RETRY_DAYS"` (alphabetical order is the existing convention).

**Import sites of `LADDER_DAYS` (complete grep of app/ tests/ scripts/):** only `tests/services/test_train_scheduler.py:38` (+ uses at 96, 107). No app/ or scripts/ importer.

**Callers of `apply_result`:** only `app/repositories/train_repository.py:3125` (plus docstring mentions at 3105, 3481, 3483 and `tests/routers/test_train.py:42` docstring) and the unit tests.

### `app/repositories/train_repository.py` (repository)

Call site (lines 3124-3127):
```python
new_state = apply_result(
    state, correct_move=correct_move, today=today, weekday_mask=settings_row.weekday_mask
)
```
-> drop `weekday_mask=`. `settings_row` is still needed for `local_today(settings_row.timezone, now_utc)` (line 3108), so `get_or_create_settings` stays.

New-item creation (lines 2295-2306) already pins "due immediately": `DrillItem(..., status=DrillStatus.ACTIVE, streak=0, due_date=today, fail_count=0, ever_correct=False)`. No change; a test should pin it (CONTEXT Established Patterns).

Mask-change note (lines 443-444): "Deliberately does NOT re-snap existing `drill_items.due_date` values when `weekday_mask` changes." Still true; optionally add "(due dates are schedule-independent since Phase 244)".

### `app/models/drill_item.py` (docstring lines 1-8)
```
interval-ladder "streak" state machine tracks progress toward MASTERED (3
spaced-correct solves) or PARKED (two doors: 3 never-correct fails, or 6
lifetime fails regardless of ever_correct); `due_date` drives session
composition (snapped to a scheduled session day by
`app.services.train_scheduler.next_scheduled_day`).
```
-> 2 consecutive correct, Door B 4, and remove the "snapped ... next_scheduled_day" clause (D-02).

Schema facts for the migration: `drill_items` PK `(user_id, game_id, ply)`; `status` SMALLINT (`ACTIVE=0, MASTERED=1, PARKED=2`, CHECK `status IN (0,1,2)`); `streak`, `fail_count` SMALLINT >= 0; `due_date` DATE; `ever_correct` bool. `drill_solves` (`app/models/drill_solve.py`): PK `(session_id, position)`, `user_id`, `game_id` (nullable), `ply`, `source` SMALLINT (`DrillSource.SR_ITEM = 0`), `correct_move` bool nullable, `solved_at` timestamptz nullable. `train_settings.timezone` is an IANA string (default `'UTC'`).

### NEW `alembic/versions/<ts>_<rev>_phase_244_sr_ladder_due_date_push.py` (data-only migration)

**Analog:** `alembic/versions/20260614_130000_wipe_eval_only_residue.py` (data-only, single gated statement, literal snapshot constants, no-op downgrade). Header layout/`Sequence, Union` typing follows the phase 240 revision (`20261015_194346_5448f030de58_phase_240_reveal_tour_stage.py` lines 1-40: long docstring with D-refs, one-way data note, "constant is a literal, not imported from app" rationale).

Constants pattern (analog lines 48-50):
```python
# Library "analyzed" coverage threshold (flaws_service.EVAL_COVERAGE_MIN). Snapshotted
# here as a literal — migrations are point-in-time and must not import app constants.
_COVERAGE_MIN = 0.90
```
-> `_CORRECT_RETRY_DAYS = 10`, `_FAIL_RETRY_DAYS = 4`, `_SR_SOURCE = 0`, `_ACTIVE = 0`, same comment.

Upgrade pattern (analog lines 53-72): one `op.execute(f"""WITH ... UPDATE ...""")`. For 244: CTE selecting the latest SR solve per `(user_id, game_id, ply)` from `drill_solves` (`source = 0 AND game_id IS NOT NULL AND solved_at IS NOT NULL`, `DISTINCT ON (...) ORDER BY ... solved_at DESC`), then `UPDATE drill_items di SET due_date = GREATEST(di.due_date, <solve local date> + N)` with `di.status = 0` and two cases: `streak >= 1 AND last.correct_move` -> +10; `streak = 0 AND last.correct_move = false` -> +4. Local date option (Claude's discretion): `(ls.solved_at AT TIME ZONE COALESCE(ts.timezone, 'UTC'))::date` with `LEFT JOIN train_settings ts ON ts.user_id = di.user_id`. Note: an invalid stored tz name makes `AT TIME ZONE` raise in Postgres (unlike `local_today`'s fallback), so either use UTC `solved_at::date` or guard via `pg_timezone_names`.

Downgrade pattern (analog lines 75-81):
```python
def downgrade() -> None:
    """No-op: the eval-only residue wipe is irreversible (SEED-044 follow-up).
    ...
    """
    pass
```

Note phase 191 (`b1724dc27de8`, lines 47-48) also shows plain `op.execute("UPDATE ...")` data backfills inside a revision, and its downgrade docstring explicitly explains why the data half is not reversed.

### NEW `tests/test_migration_244_sr_ladder_due_dates.py`

**Analog:** `tests/test_migration_wipe_eval_only_residue.py` (whole file, 110 lines). Pattern:
- Module docstring listing each seeded case and its expected outcome, ending with "Mirrors the gated SQL in `alembic/versions/<file>::upgrade`; keep in sync."
- Module-level `_TEST_USER_ID = 994xx` (pick an unused id; 99478/99479 taken) and a `_PUSH_SQL = """..."""` mirror string.
- Async test taking `db_session: AsyncSession`, seeding via ORM + `await db_session.flush()`, then `await db_session.execute(text(_PUSH_SQL))`, then assertions with explanatory messages.
- Use `ensure_test_user(db_session, _TEST_USER_ID)` from `tests/conftest.py:575` (as `test_migration_suppress_ungated_tactic_tags.py` does) instead of adding `User` manually.
- Idempotency re-run (`test_migration_suppress_ungated_tactic_tags.py:223`): `rerun = await db_session.execute(text(_SQL))` then assert nothing changes.

Seeding `drill_solves` needs a `DrillSession` parent: copy `tests/repositories/test_train_medals_finalization.py:84-110`:
```python
drill_session = DrillSession(
    user_id=user_id, session_date=day, status="completed",
    puzzle_count=count, expires_on=day + datetime.timedelta(days=1),
)
db.add(drill_session); await db.flush()
db.add(DrillSolve(session_id=drill_session.id, position=position, user_id=user_id,
                  game_id=..., ply=..., source=int(DrillSource.SR_ITEM), ...,
                  correct_move=True, solved_at=...))
```
`drill_items`/`drill_solves.game_id` FK to `games`; seed a bare game like `_seed_bare_game` in `tests/repositories/test_train_repository.py` (used at ~1732). Cases: streak1 recent correct (pushed), streak2 old correct (floor in past, unchanged, D-09), streak0 recent fail (pushed +4), streak0 never attempted (untouched), MASTERED/PARKED (untouched), a herring solve (`source != 0`) ignored, multiple solves (latest wins).

### `tests/services/test_train_scheduler.py` (unit tests)

Structure: module docstring "Covers:" list (lines 1-28, update the 0->1->2->MASTERED(3) and "6 lifetime lapses"/"due-date snapping" bullets), imports from `app.services.train_scheduler` (lines 36-57), `_TODAY = date(2026, 7, 27)`, `_EVERY_DAY_MASK = 0`, `_fresh_state()` helper (lines 78-81), one `class TestApplyResult*` per concern with plain asserts.

Every `apply_result(...)` call passes `weekday_mask=_EVERY_DAY_MASK` (lines 90, 103, 120, 136, 150, 162, 178, 187, 197, 209, 230, 242-245, 262, 281): drop the kwarg everywhere. Rewrite `test_streak_2_correct_masters_at_exactly_3` (line 110) as streak 1 -> MASTERED at 2; `test_streak_1_correct_advances_to_streak_2` becomes the mastery test. Door B tests (200-295) use the constant, so they adapt; the alternation test (~276) comment "capped at 1 by alternation" needs rethinking (with threshold 2, correct-after-correct masters, so alternation still never masters, comment can stay accurate). Add: due date exactly `today + 10` / `today + 4` under a sparse mask (proves no snapping, D-02); correct-first-attempt counts; `apply_result` signature has no `weekday_mask` (pattern: `TestApplyResultNoGuessParameter` lines 297-303 using `inspect.signature`).

### `tests/routers/test_train.py`
`test_solve_masters_item_at_three` (~1651) seeds `streak=2` and asserts `body["streak"] == 3` + mastered; still passes under threshold 2 but the name/docstring is stale. Add or rename to seed `streak=1`. Docstring line 42 mentions `apply_result` generically (fine).

### Frontend / docs copy (prose only; no client logic reads thresholds)

Exact hits (grep for "three", "in a row", "3 days/10 days", "Missed 6"):
- `frontend/src/pages/Home.tsx:69`: `'Spaced repetition brings each position back next session, then after three days, then ten, until you\'ve solved it three times.'`
- `frontend/src/lib/trainBotCopy.ts:521`: `const MASTERED_TAIL = 'Three in a row, so this one is retired.';` (tests `frontend/src/lib/__tests__/trainBotCopy.test.ts:504,514` only `toContain('retired')`, keep the word "retired").
- `frontend/src/components/train/TrainStatsCard.tsx:33-41`: comment "(3) ... (3) ... (6)", `MASTERED_EXPLAINER = 'Solved correctly 3 times in a row. ...'`, `PARKED_EXPLAINER = 'Missed 6 times in total, or 3 times without ever solving it. ...'`.
- `README.md:36`: "missed positions return next session, then after three days, then ten, until solved three times and retired."
- `app/core/dev_clock.py:6`: "the `drill_items.due_date` ladder spaces repeats out by days" (still accurate, no change needed). `frontend/src/components/train/TrainDevClock.tsx:8` same generic wording.
- Reveal tour (`TrainTourOverlay.tsx`) and other bot lines: no hits naming counts or day steps. `trainBotCopy.ts:267,401` "three times" are unrelated comments.

## Shared Patterns

- **No magic numbers:** named, typed module constants with a rationale comment (scheduler lines 39-61); migrations snapshot values as literals, never import app constants (wipe_eval_only_residue lines 48-50, phase 240 docstring lines 23-26).
- **Docstrings cite decisions** (`D-xx`) and explain one-way data changes in the revision docstring (phase 240 lines 18-21).
- **Migration tests mirror SQL** in a module constant with a "keep in sync" note rather than importing the revision module (all `tests/test_migration_*.py`).
- **Bug-fix comments** stay at their sites in `apply_result` (CLAUDE.md).

## No Analog Found

None.

## Metadata

**Analog search scope:** app/services, app/repositories, app/models, alembic/versions, tests/ (services, routers, repositories, test_migration_*), frontend/src (pages, lib, components/train), README.md, app/core/dev_clock.py
**Pattern extraction date:** 2026-11-02
