---
spike: 003
name: catchup-queue-sizing
type: standard
validates: "Given the prod DB, when counting recently-active users' recent games lacking per-ply evals, then the tier-2 catch-up queue size and implied duration at the measured throughput are known"
verdict: VALIDATED
related: [001-sf-1m-node-latency-local, 002-sf-1m-node-latency-prod]
tags: [prod-db, queue-sizing, eval-drain, seed-012, q-008]
---

# Spike 003: Catch-up queue sizing (prod DB)

## What This Validates

Given prod data (read-only via `flawchess-prod-db`, 2026-06-12), when the
SEED-012 tier-2 automatic window is sized at 100/200/500 recent games per
active user, then we know how many games/plies the catch-up queue contains and
how long it takes at spike 002's measured **5.83 positions/s** (= 503,712
plies/day on 6 workers).

"Lacks eval" proxy = `white_blunders IS NULL AND black_blunders IS NULL` (the
Q-007-validated summary-column proxy, inverted). Evaluated plies/game =
`ply_count − 14` (book-skip approximation). Queries in `queries.sql`.

## Results

**Activity caveat discovered:** `users.last_activity` was backfilled around
2026-03-22 (its global minimum), so windows ≥ ~80 days include every user and
are meaningless. 30d and 60d are the usable windows: 61 users active in 30d
(34 of them guests), 108 in 60d, 134 total.

**Tier-2 catch-up queue** (games lacking evals within each user's N most
recent; duration at 503,712 plies/day):

| Cohort | Users w/ games | w100 | w200 | w500 |
|---|---|---|---|---|
| active ≤30d | 56 | 4,429 g / 237k plies / **0.5 d** | 8,512 g / 454k plies / **0.9 d** | 19,641 g / 1.06M plies / **2.1 d** |
| active 31–60d | 30 | +2,401 g / 133k plies | +4,681 g / 261k plies | +10,754 g / 605k plies |

**Tier-3 ceiling (entire prod DB):** 598,340 games, of which **558,466 (93%)
lack per-ply evals** — 33.2M evaluated plies → **~66 days** of pure idle-drain
to full coverage of everything ever imported.

Real evaluated-plies/game ≈ 53 (237k/4,429), close to the 60 used in
spike 001/002 projections — those projections are mildly conservative.

## Investigation Trail

1. First activity query showed 100% of users "active within 90d" — followed
   up with `min(last_activity)` and found the 2026-03-22 backfill artifact.
   Recorded so the milestone doesn't size cohorts on a >60d window.
2. Split 30d vs 31–60d cohorts: the 60d cohort adds ~55% more volume. Even
   the generous (60d, w500) tier-2 queue is 1.67M plies ≈ 3.3 days.
3. Whole-DB query as the tier-3 sanity check: 93% of prod games lack evals —
   confirming Q-007's finding (12.2% avg analyzed) from the volume side.

## Results — Verdict

**VALIDATED — the catch-up problem is smaller than feared.** A w200 automatic
window for 30d-active users catches up in under a day; w500 in ~2 days. The
idle tier-3 drain reaches full-database coverage in ~2 months. SEED-012's
"initial catch-up ≈ a week" estimate was pessimistic; the milestone can
comfortably set the automatic window at 200 (or even 500) games and write UX
copy promising same-day/next-day analysis for newly active users. New-import
increments (~50 games ≈ 2,650 plies ≈ 8 min of one worker) are negligible.
