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

## Live prod bug to fix in this phase: tier-3 leaks lichess %eval games (D-118-04 dead tiebreaker)

Diagnosed 2026-06-14 from a prod observation (user 28, just-logged-in): the coverage
badge ("N of M analyzed") appeared frozen while the games table showed a game completing
every ~1-2s. Root cause is a Phase 118 selection bug, not a badge bug.

**The bug.** `_claim_tier3_derived` (`app/services/eval_queue_service.py:204-233`) selects on
`full_evals_completed_at IS NULL` **only** — it does NOT exclude lichess %eval games. D-118-04
tried to *deprioritize* them via `Game.lichess_evals_at.isnot(None).asc()` (line 230), but that
is the **last** `ORDER BY` key and `Game.played_at.desc()` (line 226) breaks the tie first.
`played_at` is effectively unique per game, so the lichess tiebreaker almost never fires. Net
effect: lichess games get picked by recency like any other, and the drain runs a **full engine
pass** on games that `Game.needs_engine_full_evals` (`app/models/game.py:223`) says to skip.
Measured on user 28: 260 of 295 full-eval'd games already had lichess %evals; ~18 of the last 25
completions were lichess re-analysis → ~70% of throughput wasted, none of it advancing
user-visible coverage.

**Why the badge looked stuck.** Badge counts `is_analyzed` = `white_blunders IS NOT NULL`, which
lichess games already satisfy at import. Re-analyzing them sets `full_evals_completed_at` (visible
in the table) but not new `white_blunders`, so `analyzed_count` plateaus. The frontend stall
detector (`useEvalCoverage.ts:13`, `MAX_STALL_POLLS=5` → 15s of no `analyzed_count` delta) then
halts polling → frozen badge until manual reload. For user 28 the badge poll is governed solely by
this branch (entry-ply done → `pct_complete=100`; tier-3 creates no `eval_jobs` rows → `in_flight_count=0`).

**Fix (already the planned end-state).** The SEED-046 candidate pool above
(`full_evals_completed_at IS NULL AND lichess_evals_at IS NULL`) is exactly `needs_engine_full_evals`
and already excludes lichess games. So this is a correctness requirement for the lottery rewrite,
not new scope. **Planner must ensure the new weighted-lottery selection REPLACES
`_claim_tier3_derived`'s WHERE clause (and drops the dead line-230 tiebreaker), not layers on top of
the existing `full_evals_completed_at IS NULL`-only predicate.** Update the D-118-04 ordering tests
in `tests/services/test_eval_queue.py` accordingly.

**Side effects of the fix (both desirable, verify in UAT):**
- Badge self-unfreezes: once only never-analyzed games are picked, every tier-3 tick advances
  `analyzed_count`, so the stall detector only trips on genuinely-stuck games (its intent). No
  frontend change needed, but confirm the badge ticks live for a returning user with backlog.
- PV/best_move backfill for lichess games is dropped. **Confirmed moot today**: `best_move`/`pv`
  have zero consumers (no router/schema/frontend reads them — grep 2026-06-14). D-118-04's
  "PV-backfill-only" rationale for keeping lichess games in tier-3 can be retired. If a
  PV-consuming feature ships later, it needs a dedicated lightweight PV-only pass, not a full
  engine re-eval — do NOT re-add lichess games to the full-eval tier to get PVs.

### Do NOT re-key the coverage badge on `full_evals_completed_at`

Tempting simplification to reject: the badge's analyzed count uses `Game.is_analyzed`
(`white_blunders IS NOT NULL`, source-agnostic — lichess %eval freebies count), NOT
`full_evals_completed_at`. Keep it that way. Two reasons: (1) post-migration lichess imports
don't stamp `full_evals_completed_at` (only the engine drain writes it), so it already
undercounts today — user 28: 688 `is_analyzed` vs 295 `full_evals_completed_at`. (2) Once this
phase excludes lichess games from the drain (above), those games will *never* get
`full_evals_completed_at`, so a badge keyed on it could never reach `total_count` — permanently
stuck short with no mechanism to close the gap. The drain backlog predicate
(`needs_engine_full_evals`) and the user-facing coverage predicate (`is_analyzed`) are
deliberately different axes; don't collapse them.

### Opportunistic cleanup: rename the `is_analyzed` local in the queue/drain (name collision)

Low-risk readability fix, do it while touching `eval_queue_service.py` / `eval_drain.py` for the
lottery (NOT a separate phase). There are two unrelated things both named `is_analyzed`:

- `Game.is_analyzed` — hybrid property, `white_blunders IS NOT NULL` (flaw analysis present, any source).
- a local var in `eval_queue_service.py` (lines ~86, 177-182, 208, 240-241, 269-298) and
  `eval_drain.py` (lines ~349, 363-369, 399, 601-604, 1293, 1322-1408) meaning
  `lichess_evals_at IS NOT NULL` (i.e. "this is a lichess %eval game", D-117-07) — used to gate
  eval-preservation (don't overwrite authoritative lichess post-move %evals).

The collision makes the drain hard to read (same name, opposite-ish meaning). Rename the local
(and the `ClaimedJob.is_analyzed` field) to something like `is_lichess_eval_game` /
`has_lichess_evals`. Pure rename, no behavior change. Skip if it bloats the lottery diff — flag
as a follow-up rather than forcing it in.
