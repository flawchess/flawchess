# Phase 224: Guest Activation — Welcome Removal & Guest Train (SEED-169) - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-09-17
**Phase:** 224-guest-activation-welcome-removal-and-guest-train
**Areas discussed:** Zero-game Train entry, Bot voice for the sign-up ask, Purged-guest Train state, Metric recording

Scouting surfaced one fact neither the seed nor the roadmap mentioned: `/train/*` is wrapped in `ImportRequiredRoute` and the Train nav item is locked for every zero-game account, so removing `_reject_guest` alone would not let a 0-game guest reach Train. Compose itself already works with zero games (herrings + sharp filler, no rating input).

---

## Zero-game Train entry

| Option | Description | Selected |
|--------|-------------|----------|
| Everyone | Add /train to IMPORT_EXEMPT_ROUTES, drop the ImportRequiredRoute wrapper; registered 0-game accounts get the warm-up loop too | ✓ |
| Guests only | Exempt /train only when profile.is_guest | |
| Keep the import lock | Guests must import first; roadmap SC 2 would need rewording | |

**User's choice:** Everyone

| Option | Description | Selected |
|--------|-------------|----------|
| Unlocked nav item only | Train is clickable from the first visit; Import bubble stays on the sign-up ask | ✓ |
| Import bubble also pitches Train | One sentence + a third "Try Train" button on Import | |
| Nav dot for 0-game accounts too | Extend the Phase 222 Train dot past the navUnlocked gate | |

**User's choice:** Unlocked nav item only
**Notes:** Claude corrected the option text afterwards: the Phase 222 dot is gated on `navUnlocked`, so a 0-game guest sees a clickable item without the dot. Decoupling the dot is Claude's discretion.

| Option | Description | Selected |
|--------|-------------|----------|
| Two flags: hasGames + isGuest | No games → import wording for both account types; guest → append sign-up ask | ✓ |
| isGuest only (roadmap literal) | Registered 0-game users keep the false "We're analyzing your games" copy | |
| Single no-games line for everyone | One neutral line; the ask lives only in the button row | |

**User's choice:** Two flags: hasGames + isGuest

---

## Bot voice for the sign-up ask

| Option | Description | Selected |
|--------|-------------|----------|
| Neutral, like today's score copy | One persona-neutral ask per surface | ✓ |
| Per-temperament variants | One ask each for the smart (score) and friendly (Import) pools | |
| Per-persona (223 D-08 shape) | Record<PersonaId, string>, 16 authored asks per surface | |

**User's choice:** Neutral

| Option | Description | Selected |
|--------|-------------|----------|
| Navigate to /welcome (roadmap literal) | Full-page four-delta explainer with a Back affordance | ✓ |
| Inline dialog with the four deltas | Radix Dialog over the score screen / Import page | |

**User's choice:** Navigate to /welcome

| Option | Description | Selected |
|--------|-------------|----------|
| Import-specific: analysis + any device | Today's alert message in bot voice; distinct from the score-screen ask | ✓ |
| Same ask as the score screen | One shared sentence | |
| All four deltas in one line | Compress the /welcome list into the bubble | |

**User's choice:** Import-specific

| Option | Description | Selected |
|--------|-------------|----------|
| Existing flow: / | Home routes to import or library; no return-to parameter | ✓ |
| Return to /train | Thread a return path through the promotion flow | |

**User's choice:** Existing flow

---

## Purged-guest Train state

| Option | Description | Selected |
|--------|-------------|----------|
| Wipe them with the games | Purge also deletes drill_sessions, drill_solves, train_settings for the guest | ✓ |
| Preserve (187/189 D-04 as-is) | Only games go; session history and settings stay on the surviving User row | |
| Wipe solves, keep sessions + settings | Reset the served-filler ledger only | |

**User's choice:** Wipe them with the games

| Option | Description | Selected |
|--------|-------------|----------|
| Existing limiter is enough | 5 guests/hour/IP x 6 puzzles/day; research verifies the Cf-Connecting-Ip path | ✓ |
| Add a guest Train ceiling | Lifetime session cap or filler-only for guests | |

**User's choice:** Existing limiter is enough

---

## Metric recording

| Option | Description | Selected |
|--------|-------------|----------|
| Baseline note + Activity split | reports/growth/ markdown with SQL + numbers; Activity Train card gains a guest-cohort row | ✓ |
| Baseline note only | Markdown only, re-run SQL by hand later | |
| Dashboard only | Read the baseline off rolling-window cards | |

**User's choice:** Baseline note + Activity split

| Option | Description | Selected |
|--------|-------------|----------|
| Completed while still a guest | status='completed' AND session_date < coalesce(promoted_at, 'infinity') | ✓ |
| Any session by a guest-cohort user | Post-promotion sessions included | |

**User's choice:** Completed while still a guest

| Option | Description | Selected |
|--------|-------------|----------|
| Exclude purged users, same as the funnel | games_purged_at IS NULL predicate + existing purged_excluded footnote | ✓ |
| Retain a counter on users | Stamp a lifetime count before the purge deletes the rows | |

**User's choice:** Exclude purged users

---

## Claude's Discretion

- Train nav dot decoupling from `navUnlocked` for `/train`.
- Import bubble `state` kind and persona stability.
- `/welcome` behaviour for registered visitors.
- Enabling `useTrainProgress` for guests in `App.tsx`; push hooks stay guest-gated.
- Exact wording of all new strings.
- Delete-vs-rewrite per affected frontend test.

## Deferred Ideas

- Return-to-`/train` after sign-up from the score screen.
- Import bubble pitching Train / "Try Train" button.
- Guest-specific Train ceiling or filler-only mode.
- Todos reviewed, not folded: WR-01 `pt-33` axis label, Phase 172 review leftovers, bitboard storage, variation-tree nested button (all keyword-match noise).
