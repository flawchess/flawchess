# Phase 258: Library Stats Recent Sample for Snapshot Charts (SEED-261121-3ou) - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-11-21
**Phase:** 258-library-stats-recent-sample-snapshots
**Areas discussed:** Cap vs colour filter, Basis line wording and place, No recent games, Performance bar

---

## Cap vs colour filter

| Option | Description | Selected |
|--------|-------------|----------|
| Filter first, then cap | Most recent 1000 games of that colour per TC; same rule as every other sidebar filter | ✓ |
| Cap first, then colour | The colour's games inside the most recent 1000 of both colours; same period for both, half the sample | |

**User's choice:** Filter first, then cap
**Notes:** Accepted that a colour view reaches about twice as far back as the unfiltered view.

---

## Basis line wording and place

### Placement

| Option | Description | Selected |
|--------|-------------|----------|
| Replace it, once | The existing coverage line in Flaw Stats becomes the basis line, shown once above the tiles; timeline gets its own caption | ✓ |
| Repeat per section | Same line under each of the three snapshot headings | |
| In the sticky TC bar | Next to the time-control switch | |

**User's choice:** Replace it, once

### Wording

| Option | Description | Selected |
|--------|-------------|----------|
| Name what bounds it | Four variants naming the bound that cut the sample; "in the current filters" only when a filter is active | ✓ |
| Always state the rule | One fixed sentence with the full rule and the start month | |
| Short line, rule in a popover | Counts and start month only; rule explained in an info popover | |

**User's choice:** Name what bounds it

### Timeline marking

| Option | Description | Selected |
|--------|-------------|----------|
| Short caption only | "All games in the current filters" at the timeline title | ✓ |
| Caption plus popover sentence | Caption and a sentence on why the tiles can differ from the last point | |
| Nothing new | Basis line is the only explanation | |

**User's choice:** Short caption only

---

## No recent games

### Quiet time control

| Option | Description | Selected |
|--------|-------------|----------|
| Keep TC, explain the gap | TC stays on the switch so the timeline is reachable; snapshot areas show a message | ✓ |
| Drop the TC from the switch | Simplest; old timeline unreachable without a recency filter | |
| Fall back to older games | Most recent 1000 whatever their age when the window is empty | |

**User's choice:** Keep TC, explain the gap

### Empty state

| Option | Description | Selected |
|--------|-------------|----------|
| One message, sections hidden | Message in the basis-line slot; tiles and the two comparison sections not rendered | ✓ |
| Message in every section | All three headings stay, each with the message | |
| Message with a button | Adds a button that sets the recency filter | |

**User's choice:** One message, sections hidden

### "All time" default

| Option | Description | Selected |
|--------|-------------|----------|
| Accept it, name the way out | No filter changes; the message names "Past 5 years" or a custom range | ✓ |
| Selecting 'All time' counts as explicit | Needs the filter store to tell default from chosen | |
| Relabel the default on this tab | "All time (charts: 36 months)" on Library Stats only | |

**User's choice:** Accept it, name the way out
**Notes:** Raised by Claude after finding that `recency: null` is both the default and the "All time" option.

---

## Performance bar

| Option | Description | Selected |
|--------|-------------|----------|
| No slower than today | Before/after timing per endpoint on the largest account; no regression allowed | ✓ |
| Fixed budget per endpoint | A hard number such as 3 seconds | |
| Measure and report only | Timings recorded, no gate | |

**User's choice:** No slower than today

| Option | Description | Selected |
|--------|-------------|----------|
| Prod data, before merge | Read-only EXPLAIN ANALYZE over the prod tunnel before the squash-merge | ✓ |
| Dev DB before merge, prod after | Local timing, then Sentry traces after deploy | |
| Benchmark DB | Large volumes, but not app-like accounts | |

**User's choice:** Prod data, before merge

---

## Claude's Discretion

- API field names and schema shape for the window metadata
- How the windowed set is shared in SQL between the counts and the three comparisons
- Clock anchoring the 36 months (`dev_now_utc` preferred over SQL `NOW()`)
- Default time control when the remembered one has no recent games
- Tiebreak on `played_at` at the cap boundary
- Test ids and Umami targets

## Deferred Ideas

- Full-history timelines on Endgames Stats with the same split
- An actively chosen "All time" as an explicit recency choice
- Recent-sample treatment for the Results Breakdown section
