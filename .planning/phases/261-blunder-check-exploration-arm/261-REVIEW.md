---
phase: 261-blunder-check-exploration-arm
reviewed: 2026-11-22T00:00:00Z
depth: standard
files_reviewed: 28
files_reviewed_list:
  - alembic/versions/20261130_120000_a7c3e5f9b261_phase_261_window_selection_snapshot.py
  - app/models/blunder_check.py
  - app/repositories/blunder_check_repository.py
  - app/routers/blunder_check.py
  - app/schemas/blunder_check.py
  - app/services/blunder_check_candidates.py
  - app/services/blunder_check_feedback.py
  - app/services/blunder_check_rules.py
  - app/services/blunder_check_selection.py
  - app/services/blunder_check_service.py
  - scripts/blunder_check/caught_rate.py
  - frontend/src/components/analysis/FacepalmMoveChip.tsx
  - frontend/src/components/library/FacepalmBadgePopover.tsx
  - frontend/src/components/library/FacepalmChip.tsx
  - frontend/src/components/library/FacepalmExplanation.tsx
  - frontend/src/components/train/blunder-check/BlunderCheckSolution.tsx
  - frontend/src/lib/blunderCheckSolution.ts
  - frontend/src/lib/facepalm.ts
  - frontend/src/lib/theme.ts
  - frontend/src/types/blunderCheck.ts
  - tests/routers/test_blunder_check_exploration.py
  - tests/routers/test_blunder_check_solution.py
  - tests/services/test_blunder_check_selection.py
  - tests/services/test_blunder_check_feedback.py
  - tests/repositories/test_blunder_check_window_snapshot.py
  - tests/repositories/test_blunder_check_repository.py
  - tests/scripts/test_caught_rate.py
  - tests/test_game_repository.py
findings:
  critical: 0
  warning: 1
  info: 7
  total: 8
  necessity: 0
status: issues_found
---

# Phase 261: Code Review Report

**Reviewed:** 2026-11-22
**Depth:** standard
**Files Reviewed:** 28
**Status:** issues_found

## Summary

Reviewed the diff since `b9ebe962a` for the exploration arm: slot arm draw, probe/pool wiring, serve-time
snapshot columns, type-line facts, solution feedback, the migration, the calibration script and the frontend
chip/copy. No blocker found. The seven claims were attacked one by one; results:

1. **Holds.** `_fill_from_pool` (selection.py:482-494) builds the exploration pass only from
   `pool.candidates(reach, for_exploration=True)` (skips `probe == "cut"` batches) with `min_score=None`, and the
   main pass only from `plan.arm == "main"` slots with `FACEPALM_SCORE_MIN` applied per option in
   `_blunder_options` (candidates.py:338-340). An exploration slot the first pass leaves empty is in neither
   dict of the second pass. The `exhausted.update(("scored","cut"))` shortcut is sound for own picks (cut set is
   a subset of the scored set and the scored pick excludes only non-cut loads). Cut-to-scored relabel in
   `_load_into_pool` only happens when the scored probe itself returned the id.
2. **Holds.** Arm is stamped from `empty[pick.slot].arm` at fill time (selection.py:494); the only plan
   rewrites are `replace(plan, shape=...)` (:696), `replace(plan, origin="own")` (:806) and
   `replace(plan, origin="foreign")` (:821); `SlotPlan(` is constructed only in `draw_slot_plan`. Both window
   insert paths (`repository.py:352`, `:1219`) go through `_window_row`. Caveat in IN-06.
3. **Mostly holds, one exception (WR-01).** The cut is applied per option and is equivalent for the main arm in
   isolation; no query became unbounded (`load_blunder_flaws` is still `game_id IN (<= batch ids)`, the own scored
   probe is `IS NOT NULL` on the same covering index). The pass split changed the slot ordering across arms.
4. **Holds.** The solution is only built after `outcome is not None` (service.py:1229-1230); `feedback` exists
   only on `BlunderSolution`; false-alarm and herring solution types have no such field; it reads window columns
   only; a NULL snapshot returns `None` (`blunder_feedback` returns None on `score is None`). No schema
   serialises the ORM window wholesale (no `from_attributes`).
5. **Holds.** Ten nullable `add_column`s (metadata-only on PG 11+), eight CHECKs that every existing row
   satisfies (all ten columns NULL, `window_case <> 0 OR selection_arm IS NULL` true for NULL arm), literal names
   with no naming convention drift, single alembic head (`f3a7b9c1e259` is referenced only by this revision),
   downgrade drops constraints then columns in reverse. The validated ADD CONSTRAINT scans take a short
   ACCESS EXCLUSIVE lock on a table of a few thousand rows; acceptable.
6. **Holds with minor notes.** Denominator is caught + missed, false alarms are counted beside (`_band_row`).
   The live-score subquery compiles to a correlated `LIMIT 1` scalar subquery on `(game_id, ply, severity)`,
   one keyed probe per window, no join (verified by compiling the statement against the PostgreSQL dialect).
   The verdict `n >= 500 and low <= 0.26 and high >= 0.18` is exactly interval overlap with [0.18, 0.26].
7. **Holds.** `feedbackCopy` does `solution.feedback ?? null`; the typed library chip passes the same testid,
   same tint and `audience='self'` (same "your level" copy), so its behaviour is unchanged; `FacepalmMoveChip`
   maps `byOpponent` to `'opponent'` ("their").

## Warnings

### WR-01: Exploration-first pass breaks the cross-arm "rarest first" slot ordering and skews main shapes when supply is thin

**File:** `app/services/blunder_check_selection.py:485-494`
**Issue:** Before this phase one `assign_windows` call filled every empty slot of an origin in rarest-first order
(`_ordered_slots`: blunder positions descending, then herring lengths). `_fill_from_pool` now runs one call for
all exploration slots and only then one for the main slots, so an exploration slot always picks before any main
slot regardless of rarity. With `used_game_ids` carrying across passes (one window per game), an exploration
position-1 slot can take the only game that could host a main position-5 (or long herring) slot. The main slot
then stays empty and goes through `_redraw_and_refill`, which redraws its shape (`draw_blunder_shape`), so under
thin supply (small own pools, the 10th-percentile drill user has 305 scored own blunders, 88 at the cut) the
served main-arm shape distribution drifts toward easier shapes, and the main arm is not served exactly as it was
before the phase. The reverse is not true (exploration is never starved by main), so the asymmetry is systematic.
**Fix:** Let `assign_windows` take a per-slot cut and per-slot game frame, so one rarest-first call orders all
slots, for example:
```python
@dataclass(frozen=True)
class SlotRule:
    shape: WindowShape
    min_score: float | None
    games: Sequence[GameCandidates]   # exploration: no cut batches; main: all

picks = assign_windows(rules_by_slot, rng=rng, used_game_ids=used)
```
and compute `eligible` per slot from `rule.games`. If that is judged too large a change, at least order the two
passes by the rarest slot (run the pass that holds the globally rarest empty slot first) and add a test with one
game and an exploration pos-1 plus main pos-5 slot.

## Info

### IN-01: `--since` is interpreted in the operator's local timezone

**File:** `scripts/blunder_check/caught_rate.py:360`
**Issue:** `--since` is a `datetime.date` bound against `ended_at` (timestamptz). asyncpg's
`timestamptz_encode` turns a bare date into midnight in the client's local timezone, not UTC, so the window start
shifts by the operator's UTC offset. Harmless for a calibration report, but the "windows ended on or after this
date" help text is then not exactly true.
**Fix:** Bind an explicit UTC datetime: `datetime.datetime.combine(since, datetime.time.min, tzinfo=datetime.UTC)`.

### IN-02: Dead constant `UNSCORED_BAND`

**File:** `scripts/blunder_check/caught_rate.py:116`
**Issue:** `UNSCORED_BAND = "unscored"` is defined and never used (grep over `scripts/` and `tests/` finds only
the definition); unscored windows are counted by `count_unscored` instead.
**Fix:** Delete it.

### IN-03: Type-line vocabulary defined twice

**File:** `app/schemas/blunder_check.py:169`, `app/services/blunder_check_feedback.py:37`
**Issue:** The same four-value `Literal` exists as `BlunderTypeLineWire` and `TypeLine`. They must stay equal for
`_feedback_schema` to type-check, and nothing but ty keeps them in step.
**Fix:** Import `TypeLine` from the feedback module into the schema (or the reverse) and alias it once.

### IN-04: Neutral score sentence has no antecedent for "that level"

**File:** `frontend/src/lib/facepalm.ts:70-80`
**Issue:** For `audience='neutral'` the sentence reads "should have been easy to see for a player at that level".
"That level" refers to nothing in the popover. The three audiences were meant to stay neutral about whose blunder
it is (D-02), but this wording reads as a dangling reference.
**Fix:** Use a self-contained neutral phrase, for example "for a player at the same level" or "for a player of
that rating", and update `facepalm.test.ts` / `FacepalmExplanation.test.tsx` accordingly.

### IN-05: `_selection_record` drops the whole record silently

**File:** `app/services/blunder_check_selection.py:878-890`
**Issue:** The five `is None` checks and the `facepalm_type is None` check are unreachable for loader rows
(score is non-NULL only with `played_prob` and `loss` set, `material_missed` is paired with `loss` by
`ck_game_flaws_material_pair`, all fitted coefficients are non-zero), which the docstring acknowledges. If a
future model change made one reachable, the window would silently be served with a NULL arm: it would drop out of
the share check (`exploration_share` excludes NULL arms as legacy) and the feedback, with no log or Sentry
signal, and exploration windows would be undercounted without anyone noticing.
**Fix:** Keep the guard but call `sentry_sdk.set_context(...)` / `capture_message("blunder window without selection record")`
on the `None` branch (grouping-safe, no variables in the message), or drop the dead checks and let the CHECK
constraints fail loudly.

### IN-06: Recorded `arm_probability` is the arm coin only; per-blunder inclusion probability is not recorded

**File:** `app/services/blunder_check_rules.py:343-345`, `app/services/blunder_check_candidates.py:365-390`
**Issue:** `arm_probability` is `P(arm)` among blunder slots (0.2 / 0.8), recorded correctly on every refill and
redraw path. But the blunder inside an arm is chosen by `rng.choice` over all options of all eligible games in
the batch, so a game with several eligible blunders is proportionally more likely than a game with one, and exploration
slots that stay empty are dropped while main slots are retried through the cut probe. An inverse-probability
reading of the caught rate by score band using `arm_probability` alone corrects the arm mix, not this
within-arm weighting. The report currently splits by arm and band and does not weight, so it is not biased by
this, but the column name suggests more than it holds.
**Fix:** Note in the column comment and the script docstring that `arm_probability` is the arm share only; if a
weighted estimator is ever added, store the option count per slot as well.

### IN-07 (hazard): negative `type_swing` would abort the whole session start

**File:** `app/services/blunder_check_feedback.py:62-65` with the CHECK in `app/models/blunder_check.py`
**Issue:** `type_swing` is stored from `round(series[-1])` and the DB enforces `type_swing >= 0`. Non-negativity
holds only because `FACEPALM_LOSS_FLOOR` and `FACEPALM_MISSED_FLOOR` are both `0`; both are typed
`int | None`. If either floor is ever set to `None` for a refit, a negative swing violates
`ck_blunder_check_windows_type_swing` and the INSERT fails the entire session composition, not one window.
**Fix:** Clamp at the source: `return max(0, round(settled[-1])) if settled else None`.

---

_Reviewed: 2026-11-22_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
