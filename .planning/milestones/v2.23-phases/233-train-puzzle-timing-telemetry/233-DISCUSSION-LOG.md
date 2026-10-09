# Phase 233: Train Per-Puzzle Timing & Engagement Telemetry - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-10-05
**Phase:** 233-train-puzzle-timing-telemetry
**Areas discussed:** §4 extras to include, Engagement counter rules

Pre-discussion finding (no question asked): auth is `BearerTransport`, so `navigator.sendBeacon`
cannot authenticate; the unload flush uses `fetch` with `keepalive: true` instead (CONTEXT D-06).

---

## §4 extras to include

| Option | Description | Selected |
|--------|-------------|----------|
| Derive via exit key | `exit: next\|pagehide` on the review flush; shown = previous puzzle exited via Next | ✓ |
| Explicit shown ping | A third write per puzzle stamps when the board renders | |
| Skip it | Abandons at session level only | |

| Option | Description | Selected |
|--------|-------------|----------|
| Umami impression | One event per visit when the leaderboard card scrolls into view | |
| Skip it | Visits to /train as the exposure proxy | |

**User's choice (exposure):** "Just make sure the leaderboard toggle between points and accuracy is
tracked". Verified already tracked (`TrainLeaderboardCard.tsx:392`, Umami `tab-switch`); no
impression event.

| Option | Description | Selected |
|--------|-------------|----------|
| Telemetry key per solve | `client: mobile\|desktop` in telemetry, no migration | ✓ |
| Column on drill_sessions | TEXT + CHECK via migration, one per session | |
| Skip it | No device covariate | |

| Option | Description | Selected |
|--------|-------------|----------|
| Skip it | DB row is the single source, Umami funnels-only | ✓ |
| Add it | One bucketed `train-review` event per puzzle | |

---

## Engagement counter rules

| Option | Description | Selected |
|--------|-------------|----------|
| Hover held ≥800 ms | Named constant; desktop click counts immediately; mobile tap | ✓ |
| Hover held ≥400 ms | More permissive | |
| Clicks/taps only | Ignore hover | |

| Option | Description | Selected |
|--------|-------------|----------|
| Distinct cards | Plus `review_cards_total` for coverage | ✓ |
| Total opens, capped | Re-hovers inflate | |

| Option | Description | Selected |
|--------|-------------|----------|
| Flag it | `review_walkthrough: true`, counters recorded normally | ✓ |
| Don't record engagement then | Omit counters on walkthrough reveals | |
| Ignore | Accept the noise | |

| Option | Description | Selected |
|--------|-------------|----------|
| None beyond the seed list | No flips, no Solution-return counter | ✓ |
| Add solution returns | `review_solution_returns` | |
| Add returns + flips | Both | |

---

## Claude's Discretion

Accepted defaults (owner chose "I'm ready for context" over discussing them): reload mid-puzzle
stores what was measured plus `resumed: true`; one review timer across the Analyze round-trip;
per-key last write wins, Next makes a later pagehide a no-op; late flushes accepted on
completed/expired sessions for the caller's own solved row. Also cap values, `client` detection
source, `review_explored` definition, `v: 1`.

## Deferred Ideas

- Leaderboard exposure impression event (declined for now).
- Bucketed `train-review` Umami event (declined).
- Explicit shown ping (declined, derived from `exit`).
