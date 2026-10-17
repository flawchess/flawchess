# Phase 240: First-session funnel, before snapshot (SEED-200)

Pulled 2026-10-15 20:35 UTC from prod, read-only through the query-only `flawchess-prod-db` MCP.
Prod at that point: `origin/production` faf9c8a8f (release #424, "Train reveal clock-context line"),
Alembic head `778c806092fb` (the old walkthrough column still exists; the Phase 240 migration
`5448f030de58` is not deployed). Latest `drill_sessions.session_date` in the data: 2026-10-14.

Query: the SEED-200 "Measure" SQL run verbatim with `:since` = '2026-09-28'. Owner user 28 is
excluded inside the query. Cohort: users whose first-ever Train session was entered and dated
2026-09-28 or later. Aggregate counts only.

## Before

Raw result rows:

| guest_origin | abandoned | solved_cap3 | n | intro_never_stamped | walk_never_stamped |
|---|---|---|---|---|---|
| false | false | 3 | 22 | 0 | 0 |
| false | true | 0 | 2 | 0 | 0 |
| false | true | 1 | 7 | 0 | 5 |
| false | true | 2 | 5 | 0 | 0 |
| false | true | 3 | 3 | 0 | 0 |
| true | false | 3 | 23 | 0 | 0 |
| true | true | 0 | 5 | 3 | 5 |
| true | true | 1 | 4 | 0 | 3 |
| true | true | 2 | 2 | 0 | 0 |
| true | true | 3 | 8 | 0 | 0 |

First sessions by audience:

| Audience | First sessions | Completed | Abandoned |
|---|---|---|---|
| Guest origin (guest now, or promoted later) | 42 | 23 | 19 (45%) |
| Registered | 39 | 22 | 17 (44%) |
| Total | 81 | 45 | 36 (44%) |

Where the 36 abandoners stop:

| Stop point | Reg | Guest | Total |
|---|---|---|---|
| 0 solved, never made the first guess (intro not stamped) | 0 | 3 | 3 |
| 0 solved, guessed but never submitted a move (intro stamped) | 2 | 2 | 4 |
| 1 solved, never finished the reveal tour | 5 | 3 | 8 |
| 1 solved, finished the tour | 2 | 1 | 3 |
| 2 solved | 5 | 2 | 7 |
| 3+ solved | 3 | 8 | 11 |

These match the seed's 2026-10-15 numbers exactly (same day, no new first sessions in between).

## After (post-deploy)

The migration from plan 01 drops `reveal_walkthrough_seen_at` and adds `reveal_tour_stage`
(0 = no tour part finished, 3 = all three finished). The adapted query: in CTE `j`, select
`t.reveal_tour_stage` instead of the old timestamp; in the final select, replace
`walk_never_stamped` with `tour_part1_unfinished` (stage 0) and `tour_unfinished` (stage below 3).
Set `:since` to the deploy date of the release that carries the migration, so the cohort only
holds first sessions that saw the new onboarding.

```sql
with first_ever as (
  select distinct on (s.user_id) s.* from drill_sessions s where s.user_id <> 28
  order by s.user_id, s.session_date, s.id
), f as (select * from first_ever where entered_at is not null and session_date >= :since),
j as (
  select f.id, f.status, (u.is_guest or u.promoted_at is not null) as guest_origin,
    (select count(distinct d.position) from drill_solves d
       where d.session_id = f.id and d.solved_at is not null) as solved,
    t.intro_seen_at, t.reveal_tour_stage
  from f join users u on u.id = f.user_id left join train_settings t on t.user_id = f.user_id
)
select guest_origin, status <> 'completed' as abandoned, least(solved, 3) as solved_cap3, count(*) n,
  count(*) filter (where intro_seen_at is null) as intro_never_stamped,
  count(*) filter (where reveal_tour_stage = 0) as tour_part1_unfinished,
  count(*) filter (where reveal_tour_stage < 3) as tour_unfinished
from j group by 1, 2, 3 order by 1, 2, 3;
```

A user with no `train_settings` row yields NULL for `reveal_tour_stage`, which neither filter
counts; the before query counted such users under `walk_never_stamped`. Every user who entered a
session has a settings row in practice, so this should not move the numbers, but check
`count(*) filter (where reveal_tour_stage is null)` once on the after read.

The comparison row moves: with the tour split over three reveals, "1 solved, never finished the
reveal tour" before maps to "1 solved, tour part 1 unfinished" (`tour_part1_unfinished`) after.

The after read is a post-deploy follow-up comparing the "1 solved, tour unfinished" and "0 solved"
rows and overall abandonment, split guest-origin vs registered; it is not a phase gate. The cohort
is small (81 first sessions in 17 days), so wait for a comparable count before reading it.
