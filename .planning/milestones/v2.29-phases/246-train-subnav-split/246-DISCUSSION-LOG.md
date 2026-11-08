# Phase 246: Train Subnav Split, Today / Leaderboard / Archive (SEED-261106-gw8) - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md. This log preserves the alternatives considered.

**Date:** 2026-11-06
**Phase:** 246-train-subnav-split
**Areas discussed:** Archive card details, Streak card additions, Tab width and visibility

**Offered but not selected:** Evicted puzzles (default applied, see Claude's Discretion).

---

## Archive card details

### What sits beside the board

| Option | Description | Selected |
|--------|-------------|----------|
| Game + status | Opponent and rating, date and time control, plus a status line | ✓ |
| Status only | Just the status line | |
| Game only | Opponent, date and time control | |

**User's choice:** Game + status

### Show the originally played move

| Option | Description | Selected |
|--------|-------------|----------|
| No, keep it out | Consistent with the no-arrows rule; Analyze shows it anyway | ✓ |
| Yes, as text | Recognisable at a glance, small hint on a later Retry | |
| Mastered only | Show on Mastered, hide on Parked | |

**User's choice:** No, keep it out

### Empty list

| Option | Description | Selected |
|--------|-------------|----------|
| Explainer + Today link | Per-list copy from the existing explainers, plus a link to Today | ✓ |
| Plain one-liner | Text only, no link | |
| Import ask when no games | As the first option, with an Import button for zero-game accounts | |

**User's choice:** Explainer + Today link

---

## Streak card additions

### Which board the rank line uses

| Option | Description | Selected |
|--------|-------------|----------|
| Points only | Always a real rank; reads `#4 this week` | ✓ |
| Better of the two | Whichever rank is higher | |
| Both | `#4 Points · #2 Accuracy` | |

**User's choice:** Points only

### No rank this week

| Option | Description | Selected |
|--------|-------------|----------|
| Link to board instead | `See this week's leaderboard` in the same spot | ✓ |
| Hide the line | Appears after the first solve of the week | |
| 'Unranked this week' | States it plainly, with a link | |

**User's choice:** Link to board instead

### Where Points today lives

| Option | Description | Selected |
|--------|-------------|----------|
| Text line in streak card | Muted line in the details column | ✓ |
| Stat tile below streak card | Keeps the tile look as a single card | |
| Drop it | The score screen already showed the result | |

**User's choice:** Text line in streak card

### Guests and opted-out players

| Option | Description | Selected |
|--------|-------------|----------|
| Same rank line | As on their own board view; planning confirms `viewer.rank` is populated | ✓ |
| Link only | Always the fallback link | |
| Hide for guests | Opt-outs get the rank, guests get no line | |

**User's choice:** Same rank line

---

## Tab width and visibility

### Desktop width

| Option | Description | Selected |
|--------|-------------|----------|
| Wide tabs, per-tab content | Tabs at `max-w-7xl` like Library; Today and Leaderboard in a 2xl column, Archive full width | ✓ |
| Narrow tabs, wide Archive grid | Tabs at `max-w-2xl`, Archive grid breaks out wider | |
| Width follows the tab | Tabs change size between tabs | |

**User's choice:** Wide tabs, per-tab content

### First visit

| Option | Description | Selected |
|--------|-------------|----------|
| Always show | Same page for everyone; Start moves down about 40px on a phone | ✓ |
| Hide until first session | Focuses the first visit, needs an onboarding gate | |

**User's choice:** Always show

---

## Claude's Discretion

- Evicted puzzles stay in the list via `LEFT JOIN`, with counts unchanged (area not selected).
- Defaults shown to the user before writing context: non-sticky mobile tabs, Mastered as the default list, list in the URL path.
- Retry's reserved space, arriving-move highlight, clickable board, rank line loading and error states.

## Deferred Ideas

- Retry must hide or disable its button on evicted puzzles (SEED-261106-q92).
- Tactic motif filter and Stats tab, already recorded in the seed.
- Four keyword-only todo matches reviewed and not folded.
