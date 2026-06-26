---
id: SEED-067
status: dormant
planted: 2026-06-26
planted_during: follow-up to quick task 260626-dxs (suppress clock/move-time display for daily/correspondence games); this file is the distilled output
trigger_when: when next touching time-management / endgame time-pressure stats OR the benchmark clock/flag-rate cohort CTEs; OR immediately if any import path ever starts populating `base_time_seconds` for daily/correspondence games (the silent guard breaks the moment that happens); OR when calibrating / auditing the benchmark `net_flag_rate` metric.
scope: Small — backend only (make one implicit exclusion explicit + close one missing-guard inconsistency); no schema, no frontend, no migration.
---

# SEED-067: Harden daily/correspondence exclusion in time-management stats

## Why This Matters

Quick task **260626-dxs** fixed the *display* symptom: chess.com "daily" and lichess
"correspondence" games carry meaningless `%clk` annotations, so `game_positions.clock_seconds`
is populated with garbage (witness: dev game 687474, user 28 — clocks jump 0.7s → 21.3s →
1008s → 90s). That fix nulls the clock at the eval-chart / flaw-card build sites only.

The open question that fix deliberately left out of scope: **do the time-management /
time-pressure aggregates also consume that garbage?** Investigation answer (2026-06-26):
**not today — but only by accident, and the protection is fragile.**

These games bucket as `time_control_bucket = "classical"` with `base_time_seconds` /
`increment_seconds` = NULL. Nothing in the stats SQL excludes them. They are fetched and then
silently discarded in Python by a `base_time_seconds is None` guard. The exclusion is
**implicit and incidental**, not a deliberate "skip correspondence" filter — and it now has a
clean, explicit alternative that didn't exist before: the `is_correspondence_time_control()`
predicate added in 260626-dxs.

## The factual picture (verified 2026-06-26)

**User-facing endgame Time-Pressure stats — protected, but incidentally:**
- `app/repositories/endgame_repository.py::query_clock_stats_rows` (~lines 759-876)
  `array_agg(clock_seconds ORDER BY ply)` — applies only `apply_game_filters(...)` +
  `Game.user_id == user_id`. **No TC filter, no `base_time_seconds` guard, no slash check.**
  A classical-bucketed daily game with garbage clocks IS returned by the query.
- Pollution is prevented only downstream in Python:
  - `app/services/endgame_service.py::_compute_time_pressure_cards` ~line 2171:
    `if base_time_seconds is None or base_time_seconds <= 0: continue`
  - `_compute_clock_diff_timeline` ~line 2772: identical guard.
  - Plus a `MAX_CLOCK_PCT_OF_BASE = 2.0` clamp as a second sanity gate.
  Because daily games have `base_time_seconds = NULL`, the whole row is dropped before any
  clock value is aggregated. Correct result, fragile mechanism.

**`apply_game_filters()` (`app/repositories/query_utils.py:170-171`)** does
`Game.time_control_bucket.in_(time_control)` only when a TC list is passed. The endgame stats
caller passes none, so nothing is filtered — daily games pass straight through.

**Benchmark cohort CTEs (`app/services/canonical_slice_sql.py`):**
- `per_user_cte_time_pressure_score_gap` (~line 359) and `per_user_cte_clock_gap` (~line 443)
  explicitly filter `WHERE g.base_time_seconds IS NOT NULL AND g.base_time_seconds > 0`
  (~lines 414, 478). Daily games excluded — good.
- **`per_user_cte_net_flag_rate` (~lines 502-555) is MISSING that guard** its siblings have.
  Its metric uses `termination`/`result` (not clock values), so it's not *clock-value*
  pollution — but a correspondence endgame game can be counted in `pool_n` / contribute a
  timeout outcome to the benchmark flag-rate denominator. This is a real, if minor,
  inconsistency between sibling CTEs.

## The risk this seed guards against

1. **Silent dependency on a NULL.** Every user-facing time-stat's correctness hinges on
   `base_time_seconds` staying NULL for daily/correspondence games. If any future import /
   normalization change ever populates `base_time_seconds` for a daily game (e.g. someone
   "fixes" the NULL, or a new platform format slips through), the garbage `clock_seconds`
   flows straight into clock-advantage averages, pressure quintiles, and the clock-diff
   timeline — with no SQL-level backstop. The failure would be silent and hard to trace.
2. **Sibling-CTE inconsistency.** `net_flag_rate` counting correspondence games while its two
   siblings exclude them is a latent benchmark-calibration discrepancy.

## Suggested work (when promoted) — keep it small

1. **Make the exclusion explicit, not incidental.** Add a daily/correspondence exclusion at
   the SQL layer for the clock-consuming queries, using the new predicate's logic rather than
   relying on `base_time_seconds IS NULL`. Two clean options:
   - Add `WHERE base_time_seconds IS NOT NULL` to `query_clock_stats_rows` to mirror the
     benchmark CTEs (turns the incidental Python guard into a deliberate, documented SQL
     filter), OR
   - Add an explicit correspondence exclusion (SQL analog of `is_correspondence_time_control`
     — a `time_control_str NOT LIKE '%/%'` / `position('/' in ...)` predicate) so intent is
     legible at the query and survives even if `base_time_seconds` semantics change.
   Prefer whichever reads as "we deliberately exclude per-move games here," and leave the
   Python guard in as defense-in-depth.
2. **Close the `net_flag_rate` gap.** Add the same `base_time_seconds IS NOT NULL AND > 0`
   guard (or the explicit correspondence exclusion) to `per_user_cte_net_flag_rate` so all
   three benchmark CTEs agree on the cohort. Note: this changes the benchmark flag-rate
   cohort, so it requires a cohort/zone refresh — check against `reports/benchmarks-latest.md`
   per the "benchmarks are the source of truth" practice, don't just edit the CTE blindly.
3. **Regression test** the explicit exclusion: a daily game (`time_control_str = "1/86400"`,
   `base_time_seconds = NULL`, clock-bearing positions) contributes nothing to the
   time-pressure cards / clock-diff timeline even if a stray non-NULL `base_time_seconds`
   were present.

## Scope boundary (what this is NOT)

- NOT a new time-control bucket / enum / filter for daily/correspondence (same non-goal as
  260626-dxs — daily stays bucketed `classical`).
- NOT touching storage/import — `game_positions.clock_seconds` stays populated; this is purely
  about which rows the *stats* layer reads.
- NOT a frontend change.

## Cross-References

- Quick task **260626-dxs** (`.planning/quick/260626-dxs-...`) — the display-layer fix that
  surfaced this question and added the reusable `is_correspondence_time_control()` predicate in
  `app/services/normalization.py`.
- Benchmark calibration discipline — see the project memory on benchmarks being the source of
  truth for "typical"; any `net_flag_rate` cohort change must re-validate against
  `reports/benchmarks-latest.md`.
