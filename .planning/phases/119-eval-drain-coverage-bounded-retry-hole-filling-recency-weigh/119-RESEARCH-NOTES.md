# Phase 119 — Pre-planning research notes

Prod `last_activity` analysis for SEED-046 (recency-weighted tier-3 lottery) τ/floor tuning.
Queried prod (`flawchess-prod-db`, non-guest users only) on **2026-06-14**. These are guesses
validated against the *current* prod shape; the seed's plan is to retune live once shipped.

## Source data (prod, non-guest users)

- **66 non-guest users**, 0 with NULL `last_activity`.
- Days-since-`last_activity` distribution: min 0.10, p10 7.17, p25 19.18, **p50 46.99**, p75 68.36,
  p90 71.97, max 83.80. → **dormant-heavy** userbase.
- **59 of 66** non-guest users have engine backlog (`needs_engine_full_evals`). Confirms the seed's
  "every user has a backlog" premise.
- Backlog users active within: **≤1d: 2, ≤3d: 3, ≤7d: 6, ≤14d: 12.** On a typical day only 0–2
  backlog users are "recent."
- Candidate-pool size (`games WHERE full_evals_completed_at IS NULL AND lichess_evals_at IS NULL`):
  **557,683 rows**, 110 distinct `user_id` (see guest flag below).

### Ages of backlog-bearing users active ≤21d (the only ones with above-floor weight)

| user_id | age_days | weight @ τ½=1d | weight @ τ½=3d |
|--------:|---------:|---------------:|---------------:|
| 3       | 0.10     | 0.93           | 0.98           |
| 28      | 0.25     | 0.84           | 0.94           |
| 175     | 1.37     | 0.39           | 0.73           |
| 168     | 4.86     | 0.034          | 0.33           |
| 165     | 6.63     | 0.010          | 0.22           |
| 161     | 6.74     | 0.009          | 0.21           |
| 96      | 7.61     | 0.005          | 0.18           |
| 162     | 7.83     | 0.004          | 0.17           |
| 146     | 8.61     | 0.002          | 0.14           |
| 157     | 10.50    | 0.001          | 0.09           |
| 153     | 11.83    | ≈floor         | 0.07           |
| 151     | 12.80    | ≈floor         | 0.06           |
| 147     | 14.39    | ≈floor         | 0.04           |
| 109     | 18.94    | ≈floor         | 0.02           |
| 108     | 19.91    | ≈floor         | 0.02           |

`weight = exp(-Δt / τ) + floor`, peak normalized to 1.0, `τ = τ½ / ln2`.

## τ / floor recommendation

- **Half-life τ½ ≈ 1 day** (decay constant `τ = τ½ / ln2 ≈ 1.44 d`). Default.
  - A returning user (`last_activity → now`, weight ≈ 1.0) gets ~30–40% of draws *immediately*
    even against the 1–2 currently-recent users; badge ticks roughly every ~25s at the ~10s
    tier-3 claim cadence. Best serves the seed's stated priority ("fast catch-up on return").
  - Alternative **τ½ = 2–3 days** spreads the idle drain more evenly across the "active in the
    last 2 weeks" cohort but dilutes a fresh return (~20% share). Choose only if smoother idle
    sharing is wanted over return-burst responsiveness.
- **Floor ≈ 0.005** (keep ≤ 0.01) of peak weight.
  - Jobs: anti-starvation, idle uniform fallback, and keeping the Efraimidis–Spirakis key
    `-ln(random()) / weight` finite (weight must never be 0).
  - Must stay small: 59-user floor mass at floor=0.005 ≈ 0.30 (a lone returner keeps ~65–70%
    share); at floor=0.05 the floor mass ≈ 2.95 swamps a returning user (~16% share). Do **not**
    size the floor large.
- Both are single tunable module constants — retune live in prod per SEED-046.

### Why the design is robust to the exact τ

The userbase is dormant-heavy (median 47d stale; only 0–2 backlog users recent on a typical
day). Common case: no one recent → floor-dominated → **near-uniform random** over ~59 candidates,
which is the correct idle behavior (drain everyone slowly + fairly). The moment anyone browses
they leap to the front regardless of τ within 0.5–3 days. So τ tuning is low-risk.

## Correctness / perf flags for the planner (surfaced by the data)

1. **Exclude guests in the candidate query.** Raw `SELECT DISTINCT user_id FROM games
   WHERE full_evals_completed_at IS NULL AND lichess_evals_at IS NULL` returns **110** distinct
   users, but only **59** are non-guest. The lottery MUST JOIN `users` and filter
   `is_guest = false`, or it drains guests despite Phase 117's QUEUE-08 guest exclusion. The
   games-only DISTINCT is **not** the candidate set.
2. **557,683-row candidate pool → DISTINCT-user perf risk** (the seed's flagged main risk). Add a
   partial index `(user_id) WHERE full_evals_completed_at IS NULL AND lichess_evals_at IS NULL`.
   A plain `DISTINCT` over 557k rows may not hit the seed's sub-100ms target — consider a
   loose-index-scan / recursive-CTE skip-scan for distinct `user_id`. EXPLAIN during planning.
3. **ES key + floor numerical safety:** because `weight ≥ floor > 0`, `-ln(random()) / weight` is
   always finite. The floor is both a fairness knob and a div-by-zero guard — don't drop it.

## Queries used (reproducible)

```sql
-- distribution
SELECT count(*), count(*) FILTER (WHERE last_activity IS NULL),
  percentile_cont(ARRAY[0.1,0.25,0.5,0.75,0.9]) WITHIN GROUP (
    ORDER BY EXTRACT(EPOCH FROM (now()-last_activity))/86400.0)
FROM users WHERE is_guest IS FALSE;

-- recency buckets + backlog cross
-- candidate pool size
SELECT count(*), count(DISTINCT user_id) FROM games
WHERE full_evals_completed_at IS NULL AND lichess_evals_at IS NULL;
```
