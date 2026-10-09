# Phase 230: Weekly Train Leaderboards - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-10-03
**Phase:** 230-weekly-train-leaderboards
**Areas discussed:** Layout & placement, Hidden/anon/guest edges

---

## Layout & placement

| Option | Description | Selected |
|--------|-------------|----------|
| One card, 2 tabs | Points / Accuracy toggle, countdown in header | ✓ |
| Two cards stacked | Both always visible, ~20+ rows on mobile | |
| Two cards side by side | md+ side by side, tight at max-w-2xl | |

| Option | Description | Selected |
|--------|-------------|----------|
| After streak card | Bubble → Streak → Leaderboard → Stats → Schedule | ✓ |
| After stats card | Less prominent | |
| Above streak card | Pushes Start down on mobile | |

| Option | Description | Selected |
|--------|-------------|----------|
| Rank-change line only | One compact line per board on the score screen | ✓ |
| Line + full tabbed card | Duplicates the landing | |
| Points board line only | Accuracy moves too little per session | |

| Option | Description | Selected |
|--------|-------------|----------|
| Points | Fixed default tab | |
| Remember last tab | Points first, then localStorage | ✓ |
| Accuracy if qualified | Smart default | |

| Option | Description | Selected |
|--------|-------------|----------|
| Accuracy | Short, honest label + helper line | ✓ |
| Avg score | Can read as skill | |
| Consistency | Less obvious meaning | |

| Option | Description | Selected |
|--------|-------------|----------|
| '#12 this week' | Plain rank when no before-rank | ✓ |
| 'New: #12' | Frames first entry as event | |
| 'Up from unranked' | Treat no rank as bottom | |

**User's choice:** One tabbed card after the streak card, remembered tab, "Accuracy" label, rank-change line only on the score screen, plain "#12 this week" for first entry.

---

## Hidden/anon/guest edges

| Option | Description | Selected |
|--------|-------------|----------|
| Private would-be row | Hidden user sees own row marked "Hidden from others" | ✓ |
| Board without own row | Top 5 + "you're hidden" | |
| No board at all | Card disappears | |

| Option | Description | Selected |
|--------|-------------|----------|
| Ghost row in the list | "You (guest)" row with neighbours + sign-up CTA | ✓ |
| Top 5 + one nudge line | "You'd be #N" line only | |

| Option | Description | Selected |
|--------|-------------|----------|
| Plain 'Anonymous' | Identical labels OK | ✓ |
| Exclude no-username users | Overrides locked rule | |
| 'Anonymous' + nudge | Own row adds import nudge | |

| Option | Description | Selected |
|--------|-------------|----------|
| New 'Leaderboards' card, last | 4th card, guest-hidden, not reset | |
| New card, first | Most visible | |
| Inside a 'Privacy' card | General Privacy card for future toggles | ✓ |

| Option | Description | Selected |
|--------|-------------|----------|
| 'You'd be #7' | Hypothetical line, no extra CTA | ✓ |
| No rank line for guests | Landing only | |

**User's choice:** Private would-be row for hidden users, ghost row for guests, plain Anonymous, toggle inside a Privacy card, guest score line "You'd be #7".

---

## Claude's Discretion

- Row content, own-row highlight, tentative marker styling
- "N points to pass" semantics on the Accuracy board
- Countdown format and cadence; refetch timing
- Empty-week and no-solves-yet states
- Privacy card position (excluded from Reset, hidden for guests)
- Query shape, indexing on `solved_at`, caching
- Umami events for tab switch and opt-out

## Deferred Ideas

- Medals + weekly snapshot table (SEED-185 follow-up)
- Username verification if impersonation abuse appears
