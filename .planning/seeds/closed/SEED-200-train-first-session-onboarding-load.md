---
id: SEED-200
status: closed. Resolved by Phase 240 (squash d9e944d52 on main, 2026-10-16, release #426).
promoted_to: Phase 240
promoted: 2026-10-15
planted: 2026-10-15
planted_during: ad-hoc Train return-rate analysis + guest walkthrough (quick 261015-pjr shipped the guest copy fix from the same session); design refined in /gsd-explore the same day
trigger_when: owner wants to lift Train first-session completion or second-session return, or any Train onboarding/stepper work; re-pull the funnel split below first (entered_at only exists since 2026-09-27, so the sample is still small)
scope: small to medium (intro/walkthrough copy and per-puzzle tour split are frontend; first-puzzle ordering is a small backend change in session composition; measuring needs the funnel query below)
---

# SEED-200: Lighten the first Train session's onboarding

Status: **design refined (explore 2026-10-15), not yet planned.** The funnel split now points at the
puzzle-1 reveal tour as the largest single drop point, but the sample is small (81 first sessions).

## Why This Matters

Train's return rate is decent (about 46% of first-session completers come back for a second), but
a large share of users never finish the first session at all, and many of those quit around
puzzle 1. That leak sits before the return-rate question even applies.

## Data (prod, pulled 2026-10-15, owner user 28 excluded)

**Return rate since warm-ups shipped (2026-08-14, release #308):** 83 of 181 users whose first
completed session came after the release completed a second one (45.9%).

**First-session abandonment, clean cohort.** The original pull used each user's first *entered*
session since `entered_at` shipped (2026-09-27), which mixes in registered users who already had
Train sessions before that date (so it was not their first session). The clean cohort below is
users whose **first-ever** session is entered and dated 2026-09-28 or later:

| Audience | First sessions | Completed | Abandoned |
|---|---|---|---|
| Guest origin (guest now, or promoted later) | 42 | 23 | 19 (45%) |
| Registered | 39 | 22 | 17 (44%) |

The earlier "guests 43% vs registered 26%" gap does not survive the clean cohort: truly new
registered users abandon as often as guests.

**Where the 36 abandoners stop** (stamps: `intro_seen_at` fires on the first guess,
`reveal_walkthrough_seen_at` fires when the user leaves the reveal from the tour's last step):

| Stop point | Reg | Guest | Total |
|---|---|---|---|
| 0 solved, never made the first guess (intro not stamped) | 0 | 3 | 3 |
| 0 solved, guessed but never submitted a move | 2 | 2 | 4 |
| 1 solved, never finished the reveal tour | 5 | 3 | **8** |
| 1 solved, finished the tour | 2 | 1 | 3 |
| 2 solved | 5 | 2 | 7 |
| 3+ solved | 3 | 8 | 11 |

The puzzle-1 reveal tour is the largest single drop point: 8 of 81 first sessions (10%) end inside
it. The pre-move intro loses 3 (all guests). Small numbers, so treat this as directional.

Other context from the original pull:

- A first session from the user's own games returned less often than a warm-up first session
  (registered, promoted guests excluded: 45.2% vs 55.6%).
- Users with push reminders on returned 75% (21/28) vs 41% (62/153) without; heavily
  self-selected, and the score screen already asks for reminders.

## What the first puzzle costs today (guest walkthrough 2026-10-15, dev build)

**11-12 bubbles of tutorial around puzzle 1:**

- 5 intro steps before the first move (6 on a warm-up), `introSteps` in
  `frontend/src/lib/trainBotCopy.ts`: welcome, the "only one or several?" question, the vocabulary,
  the practice rationale, (warm-up notice), then the closing prompt. The closing prompt already
  asks "Is there only one good move, or several?" (`promptCopy`), so `INTRO_QUESTION` duplicates it.
- 6 walkthrough steps on the first reveal (`walkthroughCopy`, `WALKTHROUGH_STEP_COUNT`): result,
  chips, stepping through the line, sidelines + rewind, "understand, don't memorize", Analyze/Next.

## Refined design (explore 2026-10-15, owner-agreed)

Guiding rule: **the user acts within one or two taps, and reads later.**

1. **Intro shrinks to 2 bubbles.** Welcome (audience copy, may be tightened), then the merged
   closing prompt: the "only one or several?" question with the guess buttons. Drop
   `INTRO_QUESTION` (duplicate) and `INTRO_VOCABULARY`.
2. **The first verdict teaches the vocabulary.** A random first guess is fine; the verdict explains
   what "only one" / "several" meant for this position. Learning by doing, not by definition.
3. **Practice rationale moves to the session-1 score screen** ("learn when to slow down and
   calculate…"), where the user has just felt the difference.
4. **Warm-up notice leaves the intro.** Place it after puzzle 1 (verdict tail or score screen;
   decide in discuss-phase).
5. **Reveal tour spreads over puzzles 1-3** (each step still fires once per account, so
   `reveal_walkthrough_seen_at` needs per-step stamps or a counter):
   - Puzzle 1: result + Next (2 steps).
   - Puzzle 2: chips + stepping through lines.
   - Puzzle 3: sidelines, "understand, don't memorize", Analyze.
6. **Chips stay visible on puzzle 1, just unexplained.** No variant reveal screen: it would add
   state and tests and a "where did these come from" moment on puzzle 2.
7. **First puzzle of the first-ever session is a sharp one.** A sharp first puzzle gives a real
   payoff on the first reveal and teaches the half of the question that needs teaching ("several"
   is just normal chess). Move the first sharp puzzle to slot 0 after the D-09 composition shuffle
   (`train_repository.py`, `random.Random(...).shuffle(reconstructed)`). The only leak: slot 0 of
   session 1 is never a herring, which is acceptable. If an own-games first session has no sharp
   puzzle, keep the random order.
8. **Put a soft or herring puzzle within puzzles 2-3 of the first session**, so both verdict
   halves appear while the tour is still running.
9. **Copy length is a hard ceiling.** Every bubble stays within `STEPPER_COPY_MAX_CHARS` (145, the
   phone bubble above the buttons); merged bubbles are rewritten shorter, never concatenated.
   The existing budget tests stay.
10. **Bubble vs board overlay split is accepted.** On phones the intro sits below the board (free
    space, board must stay visible for the decision) and the reveal tour sits on the board (the
    space below holds the strip, chips and move list being explained; Phase 237 G-01 moved it there
    to avoid scrolling). With 1-2 steps per puzzle the overlay is brief. Check during planning that
    the overlay reads as Hilda (avatar + bubble style), not as a separate tooltip system.

## Measure

Re-run the clean-cohort funnel (first-ever session, entered, dated after the release) before and
after, and compare the "1 solved, never finished the reveal tour" and "0 solved" rows plus overall
abandonment. Split registered vs guest-origin.

```sql
with first_ever as (
  select distinct on (s.user_id) s.* from drill_sessions s where s.user_id <> 28
  order by s.user_id, s.session_date, s.id
), f as (select * from first_ever where entered_at is not null and session_date >= :since),
j as (
  select f.id, f.status, (u.is_guest or u.promoted_at is not null) as guest_origin,
    (select count(distinct d.position) from drill_solves d
       where d.session_id = f.id and d.solved_at is not null) as solved,
    t.intro_seen_at, t.reveal_walkthrough_seen_at
  from f join users u on u.id = f.user_id left join train_settings t on t.user_id = f.user_id
)
select guest_origin, status <> 'completed' as abandoned, least(solved, 3) as solved_cap3, count(*) n,
  count(*) filter (where intro_seen_at is null) as intro_never_stamped,
  count(*) filter (where reveal_walkthrough_seen_at is null) as walk_never_stamped
from j group by 1, 2, 3 order by 1, 2, 3;
```

After the change, `reveal_walkthrough_seen_at` semantics change (per-step stamps), so adapt the
"never finished the tour" column to whatever stamp replaces it.

## Pitfalls

- Phase 222/237 UAT history: the intro was *split* into more, shorter steps on purpose (phone
  bubble is 204 px, owner chose more Next clicks over scrolling). Merging must not bring back
  long bubbles; shorten copy rather than concatenate.
- `introStepCount` is asserted as 5/6 in tests and drives the stepper index type (`IntroStep`);
  `WALKTHROUGH_STEP_COUNT` and `WalkthroughStep` likewise.
- The first-puzzle reorder must run after the D-09 shuffle and only on the first-ever session, or
  it leaks herring slots in every session.

## Related

- Quick 261015-pjr: truthful warm-up copy for guests with imported games (same session).
- SEED-199: subnav and section discoverability (same "where do users drop off" thread).
