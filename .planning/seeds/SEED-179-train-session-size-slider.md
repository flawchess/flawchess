---
id: SEED-179
status: dormant
planted: 2026-10-02
planted_during: no open milestone (after v2.19), during Phase 226 (SEED-171); standalone /gsd-explore session on Train session size
trigger_when: next Train UX touch, or whenever a small frontend-only quick task fits
scope: small (frontend-only quick task, no backend change, no migration)
---

# SEED-179: Train puzzles-per-session slider (3-30, step 3)

## Why This Matters

Some users want to train longer. One asked for more than one session per day,
which the owner rejects (one session per day stays the model). The need is
assumed to be **volume** (more solving time per day), not depth on the same
material.

Prod, 2026-10-02, current `train_settings.puzzles_per_session` of users with any
`drill_sessions` row:

| Setting | Any session | ≥1 completed session |
|---|---|---|
| 3 | 16 (3.9%) | 13 (7.1%) |
| 6 (default) | 346 (85.0%) | 129 (70.9%) |
| 9 | 19 (4.7%) | 17 (9.3%) |
| 12 | 8 (2.0%) | 8 (4.4%) |
| 15 | 18 (4.4%) | 15 (8.2%) |

Users who complete sessions leave the default more often (29% vs 15%), and more
of them moved up (45) than down (16).

Supply is not a constraint: 0 of 995 sessions with a `requested_count` were ever
short (`puzzle_count < requested_count`). The per-game cap
(`MAX_ITEMS_PER_GAME_PER_SESSION = 1`) leaves the median user ~400 distinct
games with an eligible blunder, and the herring cross-backfill covers thin pools.

## What

In `frontend/src/components/train/TrainScheduleSettings.tsx`, replace
`PUZZLES_PER_SESSION_PRESETS` (`[3, 6, 9, 12, 15]`) and the Radix `ToggleGroup`
with the existing `frontend/src/components/ui/slider.tsx`:

- min 3, max 30, step 3; default stays 6 (`DEFAULT_PUZZLES_PER_SESSION` in
  `app/services/train_scheduler.py`)
- show the current value as a label next to the slider
- keep the existing debounced draft save
- update tests and testids that reference `filter-puzzles-{n}`

No backend change and no migration. The DB CHECK is `puzzles_per_session BETWEEN
1 AND 50` and `TrainSettingsUpdate` uses `Field(ge=1, le=50)`. Keep the backend
bound at 50 deliberately, so raising the UI max later is a one-constant frontend
change. All existing stored values (3/6/9/12/15) sit on the new 3-step grid.

## Decisions

- **3-30 step 3** over **5-50 step 5**: the latter drops the default 6 (where 85%
  of users sit) and needs a remap migration for every existing value.
- **Slider** over **more chips** (3/6/9/12/15/20/30/50): eight chips do not fit a
  mobile row.
- **Cap at 30 for now**: raise later if users pile up at the max.
- **Accepted risk: SR backlog.** `compose_slots` gives 75% of a session to SR
  (`HERRING_SHARE = 0.25`); due reviews claim those slots first and new items pad
  the rest. A 30-puzzle session therefore introduces up to ~23 new items per day.
  A user who later lowers the size inherits an overdue backlog that drains
  slowly. The scheduler self-regulates (new intake stops while dues exceed SR
  slots), so nothing breaks; the visible cost is a large "waiting puzzles" count
  on the start screen.

## Follow-ups (out of scope for this seed)

1. **Raise the max** if a meaningful share of users (e.g. ≥15%) sit at 30. Check
   the `train_settings.puzzles_per_session` distribution on prod.
2. **Decouple a new-items-per-day cap from session size** (Anki-style, herrings
   fill the remainder), only if users complain about the review backlog after
   lowering their session size.

## Breadcrumbs

- `frontend/src/components/train/TrainScheduleSettings.tsx` (presets constant ~line 100, ToggleGroup ~line 539)
- `frontend/src/components/ui/slider.tsx`
- `app/models/train_settings.py` (CHECK 1-50, server_default 6)
- `app/schemas/train.py` (`puzzles_per_session: int = Field(ge=1, le=50)`)
- `app/services/train_pool.py` (`compose_slots`, `HERRING_SHARE`, `MAX_ITEMS_PER_GAME_PER_SESSION`)
- `app/models/drill_session.py` (`requested_count` vs `puzzle_count`, D-14 short-session state)
- `.planning/seeds/closed/SEED-037-train-spaced-repetition-blunder-drills.md`
