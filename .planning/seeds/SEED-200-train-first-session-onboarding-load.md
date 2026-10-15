---
id: SEED-200
status: dormant
planted: 2026-10-15
planted_during: ad-hoc Train return-rate analysis + guest walkthrough (quick 261015-pjr shipped the guest copy fix from the same session)
trigger_when: owner wants to lift Train first-session completion or second-session return, or any Train onboarding/stepper work; re-pull the abandonment numbers first (entered_at only exists since 2026-09-27, so the sample is still small)
scope: small to medium (copy merges and spreading the walkthrough over puzzles 1-3 are frontend-only; measuring the effect needs a before/after funnel query)
---

# SEED-200: Lighten the first Train session's onboarding

Status: **hypothesis, not a decided design.** The data shows *where* first sessions die; the
tutorial load is the most plausible cause found so far, not a proven one.

## Why This Matters

Train's return rate is decent (about 46% of first-session completers come back for a second), but
a large share of users never finish the first session at all, and most of those quit at the very
start. That leak sits before the return-rate question even applies.

## Data (prod, pulled 2026-10-15, owner user 28 excluded)

**Return rate since warm-ups shipped (2026-08-14, release #308):** 83 of 181 users whose first
completed session came after the release completed a second one (45.9%).

**First-session abandonment.** `drill_sessions.entered_at` (first Start/Resume press) only exists
since 2026-09-27, so this uses each user's first *entered* session since then:

| Audience | Entered | Completed | Abandoned (open or expired) |
|---|---|---|---|
| Guest origin (guest now, or promoted later) | 68 | 39 | 29 (43%) |
| Registered | 93 | 69 | 24 (26%) |

About half of the abandoners (25 of 53) stopped after solving **0 or 1** puzzles. Few quit at
puzzle 4 or 5, so session length (6 puzzles default) is not the lever.

Other context from the same pull:

- A first session from the user's own games returned less often than a warm-up first session
  (registered, promoted guests excluded: 45.2% vs 55.6%).
- Users with push reminders on returned 75% (21/28) vs 41% (62/153) without; heavily
  self-selected, and the score screen already asks for reminders.

## What the first puzzle costs today (guest walkthrough 2026-10-15, dev build)

**12 bubbles of tutorial around puzzle 1:**

- 6 intro steps before the first move (`introSteps` in `frontend/src/lib/trainBotCopy.ts`):
  welcome, the "only one or several?" question, the vocabulary, the practice rationale, the
  warm-up notice, then the turn prompt.
- 5 walkthrough steps on the first reveal (the `WALKTHROUGH_*` constants in the same file):
  result bubble, chips, stepping through the line, sidelines, "understand, don't memorize",
  Analyze/Next.

Each bubble is fine on its own; together they are a wall of text before anything feels like a game.

## Candidate levers (refine before implementing)

1. **Merge the two "only one / several" intro steps** (`INTRO_QUESTION` + `INTRO_VOCABULARY`), and
   consider folding the practice rationale into the closing prompt. Keep `STEPPER_COPY_MAX_CHARS`
   (145) and the owner's "no internal bubble scrolling" rule.
2. **Spread the reveal walkthrough over puzzles 1-3** instead of all on puzzle 1: e.g. result +
   chips on 1, line stepping + sidelines on 2, Analyze + "don't memorize" on 3. Each step still
   fires once per account (`reveal_walkthrough_seen_at` would need per-step stamps or a counter).
3. **Measure** with the same funnel query before and after: share of first entered sessions that
   end with 0-1 solved puzzles, split guest-origin vs registered.

## Pitfalls

- Phase 222/237 UAT history: the intro was *split* into more, shorter steps on purpose (phone
  bubble is 204 px, owner chose more Next clicks over scrolling). Merging must not bring back
  long bubbles; shorten copy rather than concatenate.
- `introStepCount` is asserted as 5/6 in tests and drives the stepper index type (`IntroStep`).
- Guest-origin users abandon far more; part of that may be guests trying Train out of curiosity
  rather than onboarding fatigue. Compare registered-only before and after.

## Related

- Quick 261015-pjr: truthful warm-up copy for guests with imported games (same session).
- SEED-199: subnav and section discoverability (same "where do users drop off" thread).
