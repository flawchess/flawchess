# Phase 244: Train SR Ladder Rework, Calculation Not Recall (SEED-207) - Context

**Gathered:** 2026-11-02
**Status:** Ready for planning

<domain>
## Phase Boundary

Rework Train's spaced-repetition ladder so repeats test calculation instead of recall of the previous attempt
or the reveal screen: correct solve -> retry in 10 days (D-11, overrides SEED-207's 14), wrong solve -> retry in 4 days, mastered after 2
consecutive correct solves, Door B leech threshold 6 -> 4. Includes a one-off in-flight migration of active
`drill_items` due dates, Train copy updates, scheduler tests and a changelog entry. No schema change.

Locked by SEED-207 (not re-discussed, read the seed for evidence): the 4d fail interval, mastery at 2, Door A
stays at 3 (never solved), Door B 4 lifetime lapses, a correct FIRST attempt counts toward mastery, brand-new
items stay due immediately, no A/B test, no retroactive Door B parking, mastered/parked rows unchanged.

Out of scope (ROADMAP): A/B test, the ~1-month post-ship re-check of SEED-207 Tables 2/3, same-motif mastery
check, fast-correct recall flag.

</domain>

<decisions>
## Implementation Decisions

### Ladder mechanics (`app/services/train_scheduler.py`)
- **D-01:** Named constants replace `LADDER_DAYS`: `CORRECT_RETRY_DAYS = 10` (see D-11), `FAIL_RETRY_DAYS = 4`,
  `MASTERY_STREAK_THRESHOLD = 2`, `LEECH_FAIL_THRESHOLD = 4` (`PARK_FAIL_THRESHOLD` stays 3). Remove
  `LADDER_DAYS` from `__all__` and every import site.
- **D-02: Drop weekday snapping from `apply_result`. OVERRIDES the ROADMAP/SEED-207 line "due dates still snap
  forward via `next_scheduled_day`".** Correct branch: `due_date = today + CORRECT_RETRY_DAYS`; fail branch:
  `due_date = today + FAIL_RETRY_DAYS`, exactly, independent of `weekday_mask`. Owner's reasoning: the schedule
  can change (existing code deliberately never re-snaps on a mask change, `train_repository.py` ~line 443), and
  snapping buys nothing because composition already serves any `due_date <= today` item at the next session.
  Consequence: `apply_result` no longer needs the `weekday_mask` parameter. Remove it and update the call site
  in `train_repository.py` (or keep it only if removal is disproportionate; planner's call, but it must be
  unused for due-date math). `next_scheduled_day` itself stays: `session_window` and the tick machine still use
  it. Update the `next_scheduled_day` docstring cross-reference that names `apply_result`.
- **D-03:** Known, accepted trade-off of D-02: the verdict tail `returnPhrase` (`frontend/src/lib/trainBotCopy.ts`)
  says "Back in N days" from the raw due date, so under a sparse schedule it can understate the real wait. No
  copy change needed for this; `NEXT_SESSION_TAIL` (`due_date <= expires_on`) keeps working.
- **D-04:** Update the module docstring, `apply_result` docstring and the Door B rationale comment
  (the "6, not Anki's 8" and "alternation caps the streak at 1" reasoning no longer holds with 2-in-a-row
  mastery; restate per the SEED-207 leech-door math). Also the `drill_item.py` docstring ("3 ... spaced-correct
  solves", "6") and the `train_repository.py` ~443 "does NOT re-snap" note if it now reads oddly.

### In-flight migration
- **D-05: Alembic data migration**, same release as the scheduler change, so there is no window where old due
  dates meet new rules. Data-only (no schema change); downgrade is a no-op (irreversible data change, say so in
  the revision). — **Reversibility:** one-way — pushed due dates on prod rows cannot be restored after a
  downgrade; harmless (items only resurface later).
- **D-06: No streak remap.** SEED-207's "old streak 2 -> 1" is dropped: with threshold 2, both old streak 1 and
  old streak 2 master on the next correct solve (`streak + 1 >= 2`) and both reset to 0 on a fail, so the remap
  would change nothing behaviourally. Streak values stay as they are.
- **D-07: Push due dates on all three paths, never pull earlier:**
  - ACTIVE items with `streak >= 1`: `due_date = max(due_date, last correct solve date + 10)`.
  - ACTIVE items with `streak = 0` that have a failed solve: `due_date = max(due_date, last fail date + 4)`.
  - Never-attempted ACTIVE items (no SR solve): untouched, stay due immediately.
  - MASTERED / PARKED rows: untouched. No retroactive Door B parking (items with `fail_count >= 4` park at their
    next lapse).
  "Last solve" comes from `drill_solves` (`source = 0` SR, `game_id IS NOT NULL`, `solved_at IS NOT NULL`,
  matched on `(user_id, game_id, ply)`, `correct_move` true/false).
- **D-08: No weekday snapping in the migration** (consistent with D-02). Raw `last solve date + N`.
- **D-09:** Overdue items stay due: the `max(...)` form means an item whose floor is already in the past keeps
  its current (past) due date.
- **D-10:** Items already composed into an open session at deploy are not touched specially: the session keeps
  serving them and the solve is graded by the new `apply_result`.

### Prod sizing (2026-11-02, read-only query, 10d correct floor)
Active items whose due date the migration actually moves (floor still in the future):

| Old state | Items moved | Without migration |
|---|---|---|
| streak 1, last correct < 10d ago | 328 | next correct (due ~day 3) would master on a recall-timed repeat |
| streak 2, last correct < 10d ago | 21 | old 10-day step already matches the new floor almost everywhere |
| streak 0, last fail < 4d ago | 87 | one more next-session retry |

About 436 rows move in total. Totals: 2,983 active (1,202 streak 0 of which 765 never attempted, 894 streak 1,
887 streak 2). Use these counts as a sanity check for the migration's affected-row count on prod (they will
drift by deploy day).

### Correct-path interval (revisited after the first CONTEXT draft)
- **D-11: `CORRECT_RETRY_DAYS = 10`, overriding SEED-207's 14.** Owner challenged 14 as too long. Re-analysis
  on prod (2026-11-02):
  - SEED-207 Table 3's "memory gone by 8-11 days" rests on n=19 and does not survive a finer split: attempt 2
    after a correct first solve has 5-10 timed solves per bucket at 8-9d / 10-11d / 12-14d, with think ratios
    1.11x / 0.75x / 0.52x (noise). The data shows memory clearly present at a week and cannot separate 10 from 14.
  - The only well-sampled long-gap data (old ladder's 10-day third step, attempt 3+ after correct solves): think
    time vs first solve 0.66x at 10-11d (n=294) and 0.59x at 12-14d (n=30). No visible fade between 10 and 14,
    so the extra 4 days buy no measurable recall reduction (memory and genuine learning are mixed here).
  - 10 days gets more users to a mastering solve (25% of users are active >= 14d after their first solve,
    roughly 29% at 10d; the fail path masters at day 14 instead of 18).
  - The ~1-month post-ship re-check then fills exactly the empty attempt-2 10-11d bucket. If think time there is
    clearly below 1.0x, move to 14.
  - Accepted cost: mastery is permanent, so a recall-assisted mastery retires an item for good.
- **Owner correction recorded:** a first Train attempt is not memory-free. Serious players analyze their games
  on chess.com/lichess right after playing. Measured effect is small: first-attempt accuracy 61.7% when the game
  is < 7 days old (n=1,868), 60.3% at 7-30d, 58.1% at 30-180d, i.e. about 2-4 points vs +14 points one day after
  a Train reveal (SEED-207 Table 2). Do not describe first attempts as "no memory possible" in docstrings or copy.

### Claude's Discretion
- **Copy wording** (owner skipped this area): Home.tsx ladder explainer (line ~69), `README.md:36`,
  `MASTERED_TAIL` in `trainBotCopy.ts` (~521), `MASTERED_EXPLAINER` / `PARKED_EXPLAINER` in `TrainStatsCard.tsx`
  (~39-41, plus the comment at ~34), and any other Train copy naming three solves or 3/10-day steps (grep bot
  lines and the reveal tour). Plain, short, matching existing Train tone; no em-dash spam. Describe the new
  ladder as "a few days after a miss, ten days after a solve, until solved twice in a row" or similar.
- **Local date of a solve in the migration:** `solved_at` is UTC; whether to convert via
  `train_settings.timezone` (`AT TIME ZONE`, fallback UTC) before adding days is the planner's call. Off by at
  most one day either way.
- **Post-ship re-check hook** (owner skipped): optional; at most a dated open-thread line in STATE.md pointing at
  SEED-207 Follow-up 1. No committed query script required.
- **Migration test:** how to test the data migration (e.g. a test seeding items + solves and running the
  revision's SQL) is the planner's call; the scheduler unit tests in the ROADMAP are mandatory.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Design and evidence
- `../../seeds/closed/SEED-207-train-sr-ladder-calculation-not-recall.md` — locked decisions, evidence tables,
  rejected options, implementation sketch. NOTE: D-02/D-06/D-08/D-11 above override its snapping,
  streak-remap and 14-day lines.
- `.planning/ROADMAP.md` § Phase 244 — scope, tests, out-of-scope list.
- `.planning/seeds/closed/SEED-037-train-spaced-repetition-blunder-drills.md` — original SR design.

### Code
- `app/services/train_scheduler.py` — `apply_result`, constants, `next_scheduled_day`, `session_window`.
- `app/repositories/train_repository.py` — `apply_result` call site, new-item creation (`due_date=today`, ~2302),
  `_next_due_date`, mask-change note (~443).
- `app/models/drill_item.py`, `app/models/drill_solve.py` — item state and solve history.
- `tests/services/test_train_scheduler.py` — scheduler tests to update.
- Prior Train data migrations for pattern: `alembic/versions/20260727_143852_b1724dc27de8_phase_191_train_settings_new_defaults.py`,
  `alembic/versions/20260728_055940_f2624e60292e_phase_193_session_tick_shield.py`,
  `alembic/versions/20261015_194346_5448f030de58_phase_240_reveal_tour_stage.py`.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `apply_result` is a pure function over `ItemState`; the whole ladder change is local to it plus constants.
- Session composition already backfills an SR shortfall with new items and sharp fillers
  (`train_repository.py` cross-backfill, `sharp_filler`), so longer delays do not shrink sessions.

### Established Patterns
- New items are created with `streak=0, due_date=today` in composition, so "new items due immediately" holds
  without touching the fail-delay path; a test should pin it.
- No client logic reads the thresholds; frontend changes are prose only. `returnPhrase` derives its tail from
  `due_date`, so it adapts automatically.
- Train data changes ship as Alembic revisions applied by `bin/deploy.sh`.

### Integration Points
- `app/core/dev_clock.py` docstring mentions the ladder (check wording).
- `frontend/src/types/train.ts` exposes `streak` on items (no UI reads it as "x of 3"; verify during planning).

</code_context>

<specifics>
## Specific Ideas

- Owner's principle on scheduling: item due dates should not depend on the user's training schedule (D-02, D-08).

</specifics>

<deferred>
## Deferred Ideas

- Post-ship re-check of SEED-207 Tables 2/3 (~1 month after deploy), already listed as out of scope.
- Same-motif mastery check and fast-correct recall flag (SEED-207 Follow-ups 2/3, own seeds).

### Reviewed Todos (not folded)
- Four keyword-only matches from `todo.match-phase` (172 deferred review findings, bitboard storage,
  variation-tree nested button, pt-33 Tailwind label): unrelated to the SR ladder, not folded.

</deferred>

---

*Phase: 244-train-sr-ladder-calculation-not-recall*
*Context gathered: 2026-11-02*
