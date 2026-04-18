---
name: benchmarks
description: Generate FlawChess population-level benchmarks from the prod or local dev database — per-user score-gap (endgame vs non-endgame), endgame Conversion/Parity/Recovery rates bucketed by ELO (500-wide) and time control, time-pressure stats at endgame entry (avg clock diff, net timeout rate), time-pressure-vs-performance curves across time controls, composite Endgame Skill distribution by ELO × TC, and Endgame ELO vs Actual ELO gap distribution per (platform, time-control) combo. Use this skill whenever the user asks about endgame benchmarks, neutral zones, gauge ranges, "what's typical", baseline distributions, calibrating thresholds, comparing time controls, deciding whether to collapse time controls, setting conversion/recovery/parity/skill ranges, or calibrating Endgame ELO timeline expectations. Trigger on phrases like "benchmark", "benchmarks", "baseline", "neutral zone", "gauge range", "distribution of rates", "how are rates distributed", "score gap distribution", "conversion distribution", "endgame skill distribution", "endgame ELO distribution", "endgame ELO gap", "calibrate thresholds", "collapse time controls", "is collapsing TC justified". Writes a timestamped markdown report to reports/benchmarks-YYYY-MM-DD.md.
---

# Benchmarks

Generate population-level benchmarks for FlawChess endgame analytics. The goal is to calibrate neutral zones, gauge ranges, and thresholds (e.g. for the Endgames tab gauges) from the observed distribution of real player data — not arbitrary guesses.

## Target selection

- Default: **production** (`mcp__flawchess-prod-db__query`) — population stats are only meaningful on real data.
- If the user says "local", "dev", or "local db" → use **local** (`mcp__flawchess-db__query`).
- Before running prod queries, check the SSH tunnel. If `lsof -i :15432` shows no listener, run `bin/prod_db_tunnel.sh` first. If the tunnel was already open, leave it.
- Each MCP call runs one statement (no `;`-separated multi-statement).

## Report scope

By default, run **all four** benchmark sections and write to `reports/benchmarks-YYYY-MM-DD.md` (UTC date). If the user only asks for one (e.g. "just the clock pressure benchmark"), run that section only and append to today's report — don't overwrite prior sections.

When writing the report, always include at the top:
- Target DB (prod/local) and snapshot timestamp
- Base filters applied: `rated = TRUE AND NOT is_computer_game` (mirrors the frontend's default human-opponent, rated-only posture)
- Sample floors used for each section
- **Currently-set thresholds read from the code** (see next section) — so the data-driven recommendations can be compared against what's live, not against Claude's guesses.

## Read the live thresholds from the code FIRST

Before running any SQL, **grep the frontend for the constants each section's gauge depends on** and include them in a "Currently set in code" subsection at the top of each benchmark section. The recommendations at the bottom of each section must compare `recommended` vs `currently set`, not invent values from nothing.

Never assume a metric uses absolute units when the code uses relative ones, or vice versa. Past mistakes that must not repeat:
- **Time pressure uses `% of base time`, NOT absolute seconds.** The clock-pressure gauge compares `user_avg_pct − opp_avg_pct` (both are `clock_seconds / base_time_seconds * 100`). Reports should present section 3 in **% of base time** and frame the recommendation that way. Absolute seconds are only useful as a secondary readout.
- **The time-pressure-vs-performance chart (section 4) currently POOLS across time controls** (single `user_series + opp_series` pair, see `_compute_time_pressure_chart` in `app/services/endgame_service.py`). Section 4's job is therefore "is the current pooling still justified?", not "should we collapse?" — the default is already collapsed.

### Code locations to grep (update when files move)

| Section | Metric | File | Constants |
|---|---|---|---|
| 1 | Endgame-vs-non-endgame score gap | `frontend/src/components/charts/EndgamePerformanceSection.tsx` | `SCORE_DIFF_NEUTRAL_MIN/MAX`, `SCORE_DIFF_DOMAIN` |
| 2 | Conversion / parity / recovery gauges | `frontend/src/components/charts/EndgameScoreGapSection.tsx` | `FIXED_GAUGE_ZONES` (per bucket), `NEUTRAL_ZONE_MIN/MAX`, `BULLET_DOMAIN` |
| 3 | Clock-diff neutral zone | `frontend/src/components/charts/EndgameClockPressureSection.tsx` | `NEUTRAL_PCT_THRESHOLD` (±pp of base time), `NEUTRAL_TIMEOUT_THRESHOLD` (±pp net timeout) |
| 4 | Time-pressure chart pooling | `app/services/endgame_service.py::_compute_time_pressure_chart` + `frontend/src/components/charts/EndgameTimePressureSection.tsx` | `Y_AXIS_DOMAIN`, `X_AXIS_DOMAIN`, `MIN_GAMES_FOR_CLOCK_STATS` |
| 5 | Endgame Skill gauge zones | `frontend/src/components/charts/EndgameScoreGapSection.tsx` | `ENDGAME_SKILL_ZONES` (3-band: danger / neutral / success) |
| 6 | Endgame ELO formula + window | `app/services/endgame_service.py` | `ENDGAME_ELO_TIMELINE_WINDOW` (=100), `_ENDGAME_ELO_SKILL_CLAMP_LO/HI` (=0.05/0.95), `MIN_GAMES_FOR_TIMELINE` (=10, in `openings_service.py`), `_MATERIAL_ADVANTAGE_THRESHOLD` (=100) |

Grep with e.g. `rg "SCORE_DIFF_NEUTRAL|SCORE_DIFF_DOMAIN" frontend/src` (Grep tool, not bash) before writing each section. Record the literal values in the report.

## Shared SQL building blocks

Re-used across sections. Keep these as CTEs when assembling queries rather than duplicating logic.

### `endgame_game_ids`
Games that meet the uniform 6-ply endgame rule (`ENDGAME_PLY_THRESHOLD` in the backend):
```sql
SELECT game_id
FROM game_positions
WHERE endgame_class IS NOT NULL
GROUP BY game_id
HAVING count(*) >= 6
```

### `first_endgame`
First endgame ply per qualifying game:
```sql
SELECT game_id, min(ply) AS entry_ply
FROM game_positions
WHERE endgame_class IS NOT NULL
GROUP BY game_id
HAVING count(*) >= 6
```

### `user_score_expr`
User's score in a game (0.0 / 0.5 / 1.0):
```sql
CASE
  WHEN (g.result = '1-0' AND g.user_color = 'white')
    OR (g.result = '0-1' AND g.user_color = 'black') THEN 1.0
  WHEN g.result = '1/2-1/2' THEN 0.5
  ELSE 0.0
END
```

### `base_filter_expr`
Applied to every section:
```sql
g.rated AND NOT g.is_computer_game
```

Do **not** filter by `opponent_strength` or `recency` in benchmarks — population-level stats should be unconstrained by per-user UI filters.

### Sample floors (defaults — can be overridden)

| Benchmark | Minimum games |
|-----------|---------------|
| B1 score gap | 30 endgame AND 30 non-endgame games per user |
| B2 conv/parity/recov distribution | 10 games per user in a given (ELO bucket × TC × material bucket) cell for per-user distributions; cells also shown only if the cell's pooled n ≥ 100 |
| B3 clock stats | 20 endgame games per user per TC |
| B4 pressure-vs-performance | 100 games per (TC × time-remaining bucket) cell to show a point on the curve |
| B5 Endgame Skill | 20 endgame games per user per (ELO bucket × TC), AND at least 2 of the 3 material sub-buckets non-empty for that user (mirrors the service's "mean across non-empty buckets" rule); cells shown only if ≥ 10 users qualify |
| B6 Endgame ELO gap | 30 endgame games per user per (platform × TC) combo AND 100 total games per combo (matches `ENDGAME_ELO_TIMELINE_WINDOW`); user must also have a non-NULL `user_rating` so Actual ELO is defined |

---

## Section 1 — Score % Difference (Endgame vs Non-Endgame)

**Question:** How big is the gap between a player's score in games that reached an endgame vs games that didn't, across the player base? Used to pick the neutral zone on the "score gap" gauge.

**Per-user metric:** `endgame_score − non_endgame_score`, where each `score` is the usual `win + draw/2` average.

### Query
```sql
WITH endgame_game_ids AS (
  SELECT game_id FROM game_positions
  WHERE endgame_class IS NOT NULL
  GROUP BY game_id HAVING count(*) >= 6
),
rows AS (
  SELECT
    g.user_id,
    CASE
      WHEN (g.result = '1-0' AND g.user_color = 'white')
        OR (g.result = '0-1' AND g.user_color = 'black') THEN 1.0
      WHEN g.result = '1/2-1/2' THEN 0.5
      ELSE 0.0
    END AS score,
    (eg.game_id IS NOT NULL) AS has_endgame
  FROM games g
  LEFT JOIN endgame_game_ids eg ON eg.game_id = g.id
  WHERE g.rated AND NOT g.is_computer_game
),
per_user AS (
  SELECT
    user_id,
    count(*) FILTER (WHERE has_endgame) AS eg_games,
    count(*) FILTER (WHERE NOT has_endgame) AS non_eg_games,
    avg(score) FILTER (WHERE has_endgame) AS eg_score,
    avg(score) FILTER (WHERE NOT has_endgame) AS non_eg_score
  FROM rows
  GROUP BY user_id
  HAVING count(*) FILTER (WHERE has_endgame) >= 30
     AND count(*) FILTER (WHERE NOT has_endgame) >= 30
)
SELECT
  count(*) AS n_users,
  round(avg(eg_score - non_eg_score)::numeric, 4) AS mean_diff,
  round(stddev_samp(eg_score - non_eg_score)::numeric, 4) AS std_diff,
  round(percentile_cont(0.05) WITHIN GROUP (ORDER BY eg_score - non_eg_score)::numeric, 4) AS p05,
  round(percentile_cont(0.10) WITHIN GROUP (ORDER BY eg_score - non_eg_score)::numeric, 4) AS p10,
  round(percentile_cont(0.25) WITHIN GROUP (ORDER BY eg_score - non_eg_score)::numeric, 4) AS p25,
  round(percentile_cont(0.50) WITHIN GROUP (ORDER BY eg_score - non_eg_score)::numeric, 4) AS p50,
  round(percentile_cont(0.75) WITHIN GROUP (ORDER BY eg_score - non_eg_score)::numeric, 4) AS p75,
  round(percentile_cont(0.90) WITHIN GROUP (ORDER BY eg_score - non_eg_score)::numeric, 4) AS p90,
  round(percentile_cont(0.95) WITHIN GROUP (ORDER BY eg_score - non_eg_score)::numeric, 4) AS p95,
  round(min(eg_score - non_eg_score)::numeric, 4) AS min_diff,
  round(max(eg_score - non_eg_score)::numeric, 4) AS max_diff
FROM per_user;
```

### Currently set in code (grep before reporting)

Read `frontend/src/components/charts/EndgamePerformanceSection.tsx` and record the literal values of `SCORE_DIFF_NEUTRAL_MIN`, `SCORE_DIFF_NEUTRAL_MAX`, and `SCORE_DIFF_DOMAIN`. Report them as "currently set: neutral ±X, domain ±Y" at the top of Section 1.

### Output
A single-row percentile table plus:
- **Currently set in code:** `SCORE_DIFF_NEUTRAL_MIN..MAX` and `SCORE_DIFF_DOMAIN` — stated as-is.
- **Recommended neutral zone:** `[p25, p75]` rounded to a readable width (e.g. ±0.03 → ±3 pp).
- **Recommended gauge range:** `[p05, p95]` — covers almost the whole population without being dominated by tails.
- **Verdict:** state whether the code's current zone matches the data-driven zone, and if not, whether to widen, narrow, or re-center.
- Also dump the raw per-user list (user_id, eg_score, non_eg_score, diff, eg_games, non_eg_games) sorted by `diff` so we can eyeball who the tail users are.

---

## Section 2 — Conversion / Parity / Recovery Distribution

**Question:** How do per-game Conversion, Parity, Recovery rates (= user score within that material-entry bucket) vary across ELO (500-wide) and time control? Used to calibrate the conv/parity/recov gauges.

Per the clarified scope: **bucket games, not users.** Each game contributes to one (ELO bucket × TC × material bucket) cell based on its own per-game rating and its own material imbalance at endgame entry — no per-user ELO assignment.

### Bucket rules
- **ELO bucket** = `floor(user_rating / 500) * 500` where `user_rating = white_rating if user_color='white' else black_rating`. Exclude games where that rating is NULL.
- **Time control bucket** = `g.time_control_bucket` (bullet / blitz / rapid / classical). Exclude NULL.
- **Material bucket** (mirrors `app/services/endgame_service.py::_compute_score_gap_material`):
  - Let `sign = 1` if white, `-1` if black.
  - `entry_imb_user = entry.material_imbalance * sign`
  - `after_imb_user = after.material_imbalance * sign` where `after` is the position at `entry_ply + 4` **and** `after.endgame_class IS NOT NULL` (else NULL).
  - Bucket: `conversion` if both ≥ +100, `recovery` if both ≤ −100, else `parity` (including NULL after_imb).
  - Threshold 100 mirrors `_MATERIAL_ADVANTAGE_THRESHOLD`.

### Query
```sql
WITH first_endgame AS (
  SELECT game_id, min(ply) AS entry_ply
  FROM game_positions
  WHERE endgame_class IS NOT NULL
  GROUP BY game_id HAVING count(*) >= 6
),
bucketed AS (
  SELECT
    g.id AS game_id,
    g.user_id,
    g.time_control_bucket AS tc,
    CASE WHEN g.user_color = 'white' THEN g.white_rating ELSE g.black_rating END AS user_rating,
    CASE
      WHEN (g.result='1-0' AND g.user_color='white')
        OR (g.result='0-1' AND g.user_color='black') THEN 1.0
      WHEN g.result='1/2-1/2' THEN 0.5
      ELSE 0.0
    END AS score,
    CASE WHEN g.user_color='white' THEN 1 ELSE -1 END AS color_sign,
    ep.material_imbalance AS entry_imb,
    ap.material_imbalance AS after_imb
  FROM games g
  JOIN first_endgame fe ON fe.game_id = g.id
  JOIN game_positions ep
    ON ep.game_id = g.id AND ep.ply = fe.entry_ply
  LEFT JOIN game_positions ap
    ON ap.game_id = g.id AND ap.ply = fe.entry_ply + 4
   AND ap.endgame_class IS NOT NULL
  WHERE g.rated AND NOT g.is_computer_game
    AND g.time_control_bucket IS NOT NULL
),
classified AS (
  SELECT
    user_id,
    tc,
    (floor(user_rating::numeric / 500) * 500)::int AS elo_bucket,
    score,
    CASE
      WHEN entry_imb IS NULL OR after_imb IS NULL THEN 'parity'
      WHEN (entry_imb * color_sign) >=  100 AND (after_imb * color_sign) >=  100 THEN 'conversion'
      WHEN (entry_imb * color_sign) <= -100 AND (after_imb * color_sign) <= -100 THEN 'recovery'
      ELSE 'parity'
    END AS bucket
  FROM bucketed
  WHERE user_rating IS NOT NULL
)
SELECT
  elo_bucket, tc, bucket,
  count(*) AS games,
  round(avg(score)::numeric, 4) AS score,
  count(DISTINCT user_id) AS users
FROM classified
GROUP BY elo_bucket, tc, bucket
ORDER BY elo_bucket, tc, bucket;
```

Run this once — the pivoted output powers the next two tables.

### Currently set in code (grep before reporting)

Read `frontend/src/components/charts/EndgameScoreGapSection.tsx` and extract:
- `FIXED_GAUGE_ZONES` — the per-bucket gauge neutral bands (conversion / parity / recovery).
- `NEUTRAL_ZONE_MIN/MAX` — the neutral band on the opponent-calibrated bullet chart.
- `BULLET_DOMAIN` — the bullet chart's half-width.

Report each of these literal values at the top of Section 2 so recommendations can be compared against what's live.

### Output tables (one per material bucket: conversion, parity, recovery)

Rows = ELO bucket (`<500, 500–999, 1000–1499, ...`), columns = TC (bullet / blitz / rapid / classical). Cell = pooled score with `(n games)` on a second line. Grey out cells with `games < 100` (show value but flag as low-confidence).

After each table, include:
- **Currently set in code** for that bucket: the `FIXED_GAUGE_ZONES[bucket]` neutral band.
- **Overall pooled rate** across all cells (weighted by games).
- **Opponent rate** = `1 − pooled_rate(mirror_bucket)` (conversion ↔ recovery; parity ↔ parity).
- **Rate gap** = user − opponent. The observed range of this gap (min/max/p25/p75 across the ELO × TC cells) gives the data-driven neutral-zone width.
- **Verdict:** compare the code's current neutral band to the observed population median and p25/p75. State "keep", "widen", "narrow", or "re-center" with one-line rationale.

### Per-user distribution within cells (optional second view)

For each (ELO × TC × material_bucket) cell with ≥ 10 users each having ≥ 10 games in the cell, add a p25/p50/p75 of per-user rates. This shows *spread* within a cell and is what backs statements like "at 1500 blitz, half of users convert between 68% and 78%". Only emit cells that pass the sample floor.

---

## Section 3 — Time Pressure at Endgame Entry

**Question:** How do the per-user average clock difference (**in % of base time**) and net timeout rate (at endgame entry) distribute across users, per time control? Used to calibrate the neutral zone for the clock pressure gauge.

**Primary metric: % of base time.** The live clock-pressure gauge in `EndgameClockPressureSection.tsx` compares `user_avg_pct − opp_avg_pct`, where each `pct = clock_seconds / base_time_seconds * 100`. Report the distribution of `avg_pct_diff` (per-user, per-TC) as the main result. Absolute seconds are a secondary readout only (useful to sanity-check magnitudes but not for setting zones).

Note: this is a **per-user** distribution. A user with enough endgame games in a TC contributes one datapoint to that TC's distribution.

### Currently set in code (grep before reporting)

Read `frontend/src/components/charts/EndgameClockPressureSection.tsx` and record the literal values of `NEUTRAL_PCT_THRESHOLD` and `NEUTRAL_TIMEOUT_THRESHOLD`. As of last audit: both sit around ±5–10pp; recommendations should state the currently-set number and whether the data supports widening/narrowing.

### Extracting clocks at endgame entry (SQL approximation)

The backend scans ply arrays in Python to find the first non-NULL clock for each parity. A reasonable SQL approximation takes the clocks at `entry_ply` and `entry_ply + 1` and routes by parity + user color. This misses cases where those specific plies are NULL — document in the report as a small systematic bias vs. the backend's stricter logic.

### Query
```sql
WITH first_endgame AS (
  SELECT game_id, min(ply) AS entry_ply
  FROM game_positions
  WHERE endgame_class IS NOT NULL
  GROUP BY game_id HAVING count(*) >= 6
),
clock_raw AS (
  SELECT
    g.id AS game_id, g.user_id, g.user_color, g.time_control_bucket AS tc,
    g.base_time_seconds, g.termination, g.result,
    fe.entry_ply,
    p1.clock_seconds AS clk_at_entry,
    p2.clock_seconds AS clk_at_entry_plus_1
  FROM games g
  JOIN first_endgame fe ON fe.game_id = g.id
  LEFT JOIN game_positions p1
    ON p1.game_id = g.id AND p1.ply = fe.entry_ply
  LEFT JOIN game_positions p2
    ON p2.game_id = g.id AND p2.ply = fe.entry_ply + 1
  WHERE g.rated AND NOT g.is_computer_game
    AND g.time_control_bucket IS NOT NULL
),
routed AS (
  SELECT
    user_id, tc, base_time_seconds, termination, result, user_color,
    CASE
      WHEN user_color='white' AND entry_ply % 2 = 0 THEN clk_at_entry
      WHEN user_color='white' AND entry_ply % 2 = 1 THEN clk_at_entry_plus_1
      WHEN user_color='black' AND entry_ply % 2 = 1 THEN clk_at_entry
      ELSE clk_at_entry_plus_1
    END AS user_clk,
    CASE
      WHEN user_color='white' AND entry_ply % 2 = 0 THEN clk_at_entry_plus_1
      WHEN user_color='white' AND entry_ply % 2 = 1 THEN clk_at_entry
      WHEN user_color='black' AND entry_ply % 2 = 1 THEN clk_at_entry_plus_1
      ELSE clk_at_entry
    END AS opp_clk
  FROM clock_raw
),
clean AS (
  SELECT
    user_id, tc, termination, result, user_color,
    user_clk, opp_clk, base_time_seconds,
    (user_clk - opp_clk) AS diff_seconds,
    -- Primary metric: clock diff as % of base time (matches live gauge).
    -- base_time_seconds is never NULL here because a TC bucket implies it.
    (user_clk - opp_clk) / NULLIF(base_time_seconds, 0) * 100 AS diff_pct
  FROM routed
  WHERE user_clk IS NOT NULL AND opp_clk IS NOT NULL
    AND base_time_seconds IS NOT NULL AND base_time_seconds > 0
    AND user_clk <= 2.0 * base_time_seconds
    AND opp_clk <= 2.0 * base_time_seconds
),
per_user_tc AS (
  SELECT
    user_id, tc,
    count(*) AS games,
    avg(diff_pct) AS avg_diff_pct,
    avg(diff_seconds) AS avg_diff_s,
    sum(CASE
          WHEN termination='timeout' AND (
               (result='1-0' AND user_color='white')
            OR (result='0-1' AND user_color='black')) THEN 1 ELSE 0
        END) AS timeout_wins,
    sum(CASE
          WHEN termination='timeout' AND (
               (result='1-0' AND user_color='black')
            OR (result='0-1' AND user_color='white')) THEN 1 ELSE 0
        END) AS timeout_losses
  FROM clean
  GROUP BY user_id, tc
  HAVING count(*) >= 20
)
SELECT
  tc,
  count(*) AS n_users,
  -- Clock diff in % of base time (primary metric — matches live gauge)
  round(avg(avg_diff_pct)::numeric, 2) AS mean_pct,
  round(percentile_cont(0.05) WITHIN GROUP (ORDER BY avg_diff_pct)::numeric, 2) AS pct_p05,
  round(percentile_cont(0.25) WITHIN GROUP (ORDER BY avg_diff_pct)::numeric, 2) AS pct_p25,
  round(percentile_cont(0.50) WITHIN GROUP (ORDER BY avg_diff_pct)::numeric, 2) AS pct_p50,
  round(percentile_cont(0.75) WITHIN GROUP (ORDER BY avg_diff_pct)::numeric, 2) AS pct_p75,
  round(percentile_cont(0.95) WITHIN GROUP (ORDER BY avg_diff_pct)::numeric, 2) AS pct_p95,
  -- Clock diff in absolute seconds (secondary readout only)
  round(avg(avg_diff_s)::numeric, 2) AS mean_s,
  round(percentile_cont(0.25) WITHIN GROUP (ORDER BY avg_diff_s)::numeric, 2) AS s_p25,
  round(percentile_cont(0.50) WITHIN GROUP (ORDER BY avg_diff_s)::numeric, 2) AS s_p50,
  round(percentile_cont(0.75) WITHIN GROUP (ORDER BY avg_diff_s)::numeric, 2) AS s_p75,
  -- Net timeout rate in pp
  round(avg((timeout_wins - timeout_losses)::numeric / games * 100), 2) AS mean_net_timeout_pct,
  round(percentile_cont(0.05) WITHIN GROUP (ORDER BY (timeout_wins - timeout_losses)::numeric / games * 100)::numeric, 2) AS net_p05,
  round(percentile_cont(0.25) WITHIN GROUP (ORDER BY (timeout_wins - timeout_losses)::numeric / games * 100)::numeric, 2) AS net_p25,
  round(percentile_cont(0.50) WITHIN GROUP (ORDER BY (timeout_wins - timeout_losses)::numeric / games * 100)::numeric, 2) AS net_p50,
  round(percentile_cont(0.75) WITHIN GROUP (ORDER BY (timeout_wins - timeout_losses)::numeric / games * 100)::numeric, 2) AS net_p75,
  round(percentile_cont(0.95) WITHIN GROUP (ORDER BY (timeout_wins - timeout_losses)::numeric / games * 100)::numeric, 2) AS net_p95
FROM per_user_tc
GROUP BY tc
ORDER BY CASE tc WHEN 'bullet' THEN 1 WHEN 'blitz' THEN 2 WHEN 'rapid' THEN 3 WHEN 'classical' THEN 4 END;
```

### Output
Three percentile tables, rows = TC:
1. **Clock diff, % of base time** (primary — matches live gauge): columns `n_users / mean / p05 / p25 / p50 / p75 / p95`.
2. **Net timeout rate, pp** (primary): same columns.
3. **Clock diff, seconds** (secondary readout, 3 cols: `s_p25 / s_p50 / s_p75`) — sanity-check only.

Below the tables:
- **Recommended neutral zone** = `[p25, p75]` per TC in **% of base time**.
- **Recommended gauge range** = `[p05, p95]` per TC in **% of base time**.
- **Compared to currently-set `NEUTRAL_PCT_THRESHOLD`** (read from code): state whether the symmetric `±N` band the code uses encompasses the observed p25–p75 for each TC.
- Note whether the **% zones** look similar across TCs. Because the metric is already normalized by base time, TCs can plausibly share a single zone — evaluate this empirically; do not assume they must differ.

---

## Section 4 — Time Pressure vs Performance (Across Time Controls)

**Question:** The live chart already **pools all time controls into a single series** (see `_compute_time_pressure_chart` in `app/services/endgame_service.py` — `pooled_user_buckets` / `pooled_opp_buckets`). Is that pooling still justified, or does the data now suggest the chart should split by TC?

**Currently set in code (grep before reporting):** confirm that `_compute_time_pressure_chart` still pools TCs and state this explicitly at the top of Section 4. Also record `Y_AXIS_DOMAIN` and `X_AXIS_DOMAIN` from `EndgameTimePressureSection.tsx` so the report can flag whether the observed curve uses the full axis range or sits squashed inside it.

### Query
```sql
WITH first_endgame AS (
  SELECT game_id, min(ply) AS entry_ply
  FROM game_positions
  WHERE endgame_class IS NOT NULL
  GROUP BY game_id HAVING count(*) >= 6
),
clock_raw AS (
  SELECT
    g.id AS game_id, g.user_color, g.time_control_bucket AS tc, g.base_time_seconds, g.result,
    fe.entry_ply,
    p1.clock_seconds AS clk_at_entry,
    p2.clock_seconds AS clk_at_entry_plus_1
  FROM games g
  JOIN first_endgame fe ON fe.game_id = g.id
  LEFT JOIN game_positions p1
    ON p1.game_id = g.id AND p1.ply = fe.entry_ply
  LEFT JOIN game_positions p2
    ON p2.game_id = g.id AND p2.ply = fe.entry_ply + 1
  WHERE g.rated AND NOT g.is_computer_game
    AND g.time_control_bucket IS NOT NULL
    AND g.base_time_seconds IS NOT NULL AND g.base_time_seconds > 0
),
game_pct AS (
  SELECT
    tc,
    CASE
      WHEN (result='1-0' AND user_color='white')
        OR (result='0-1' AND user_color='black') THEN 1.0
      WHEN result='1/2-1/2' THEN 0.5
      ELSE 0.0
    END AS user_score,
    (CASE
       WHEN user_color='white' AND entry_ply % 2 = 0 THEN clk_at_entry
       WHEN user_color='white' AND entry_ply % 2 = 1 THEN clk_at_entry_plus_1
       WHEN user_color='black' AND entry_ply % 2 = 1 THEN clk_at_entry
       ELSE clk_at_entry_plus_1
     END) / NULLIF(base_time_seconds, 0) * 100 AS user_pct
  FROM clock_raw
)
SELECT
  tc,
  least(floor(user_pct / 10)::int, 9) AS bucket,
  count(*) AS games,
  round(avg(user_score)::numeric, 4) AS score
FROM game_pct
WHERE user_pct IS NOT NULL AND user_pct <= 200
GROUP BY tc, bucket
ORDER BY tc, bucket;
```

### Output
A 10-row × 4-column table (rows = time-remaining bucket 0–10% … 90–100%, columns = bullet / blitz / rapid / classical). Cell format: `score (n)`. Suppress cells with `n < 100`.

Below the table, compute:
- **Per-bucket range** = max − min across TCs (only for buckets where ≥ 3 TCs have n ≥ 100).
- **Max per-bucket range** across all buckets.
- **Pearson correlation** between each TC's curve and the pooled curve (requires one follow-up query — skip if trivial).

Verdict: if max per-bucket range < 0.05 (5 pp) across the reliable buckets, the existing pooled (collapsed) chart remains safe and no change is recommended. Otherwise, recommend splitting the chart by TC and state the specific bucket(s) where the spread is unacceptable. Frame the conclusion as "keep the current pooling" vs "change to per-TC" — never as "should we collapse?", because it is already collapsed.

---

## Section 5 — Endgame Skill Distribution

**Question:** How does the composite Endgame Skill (mean-across-non-empty-buckets of Conv Win %, Parity Score %, Recov Save %) distribute across users per (ELO bucket × TC)? Used to calibrate the `ENDGAME_SKILL_ZONES` gauge and to answer "what's a typical skill value at my rating level?"

Endgame Skill is what the backend `_endgame_skill_from_bucket_rows` helper in `app/services/endgame_service.py` computes on each window, and it's the input to the `endgame_elo_from_skill` formula (Section 6). Benchmarking it in isolation lets us calibrate the skill gauge independently of the ELO translation.

### Currently set in code (grep before reporting)

Read `frontend/src/components/charts/EndgameScoreGapSection.tsx` and extract the literal values of `ENDGAME_SKILL_ZONES`. As of this skill's last audit the bands are `[0–0.45 danger, 0.45–0.55 neutral, 0.55–1.00 success]` (mirrors the Parity gauge so the color story stays consistent). Report the literal values and the comment above the constant (it documents "typical value lands around 52% on FlawChess data") at the top of Section 5.

### Skill math, translated to SQL

The Python helper splits each eligible endgame game into one of three mutually-exclusive buckets (`conversion` / `parity` / `recovery`) based on material imbalance at entry and at `entry_ply + 4` (see Section 2's bucket rules — same logic applies), then:

1. **Per-bucket rate** — mean of per-game contributions inside that bucket:
   - conversion → `1.0` if user won else `0.0` (Win %)
   - parity → user score `1.0 / 0.5 / 0.0` (Score %)
   - recovery → `1.0` if user won or drew else `0.0` (Save %)
2. **Skill** — unweighted mean of the non-empty per-bucket rates (so a user with only parity games has `skill = parity_rate`; a user with all three has `skill = (conv + par + recov) / 3`).

The "non-empty-buckets" rule is why we can't just average per-game rates directly — we have to materialize per-bucket rates first and then average those.

### Query
```sql
WITH first_endgame AS (
  SELECT game_id, min(ply) AS entry_ply
  FROM game_positions
  WHERE endgame_class IS NOT NULL
  GROUP BY game_id HAVING count(*) >= 6
),
bucketed AS (
  SELECT
    g.user_id,
    g.time_control_bucket AS tc,
    (floor((CASE WHEN g.user_color='white' THEN g.white_rating ELSE g.black_rating END)::numeric / 500) * 500)::int AS elo_bucket,
    CASE
      WHEN (g.result='1-0' AND g.user_color='white')
        OR (g.result='0-1' AND g.user_color='black') THEN 1.0
      WHEN g.result='1/2-1/2' THEN 0.5
      ELSE 0.0
    END AS score,
    CASE WHEN g.user_color='white' THEN 1 ELSE -1 END AS color_sign,
    ep.material_imbalance AS entry_imb,
    ap.material_imbalance AS after_imb
  FROM games g
  JOIN first_endgame fe ON fe.game_id = g.id
  JOIN game_positions ep
    ON ep.game_id = g.id AND ep.ply = fe.entry_ply
  LEFT JOIN game_positions ap
    ON ap.game_id = g.id AND ap.ply = fe.entry_ply + 4
   AND ap.endgame_class IS NOT NULL
  WHERE g.rated AND NOT g.is_computer_game
    AND g.time_control_bucket IS NOT NULL
    AND (CASE WHEN g.user_color='white' THEN g.white_rating ELSE g.black_rating END) IS NOT NULL
),
classified AS (
  SELECT
    user_id, tc, elo_bucket,
    CASE
      WHEN entry_imb IS NULL OR after_imb IS NULL THEN 'parity'
      WHEN (entry_imb * color_sign) >=  100 AND (after_imb * color_sign) >=  100 THEN 'conversion'
      WHEN (entry_imb * color_sign) <= -100 AND (after_imb * color_sign) <= -100 THEN 'recovery'
      ELSE 'parity'
    END AS bucket,
    -- Per-game contribution to that bucket's rate:
    CASE
      WHEN entry_imb IS NULL OR after_imb IS NULL THEN score  -- parity = score %
      WHEN (entry_imb * color_sign) >=  100 AND (after_imb * color_sign) >=  100
        THEN CASE WHEN score = 1.0 THEN 1.0 ELSE 0.0 END       -- conversion = win %
      WHEN (entry_imb * color_sign) <= -100 AND (after_imb * color_sign) <= -100
        THEN CASE WHEN score >= 0.5 THEN 1.0 ELSE 0.0 END      -- recovery = save %
      ELSE score
    END AS bucket_contribution
  FROM bucketed
),
per_user_bucket AS (
  SELECT
    user_id, tc, elo_bucket, bucket,
    count(*) AS games,
    avg(bucket_contribution) AS bucket_rate
  FROM classified
  GROUP BY user_id, tc, elo_bucket, bucket
),
per_user_skill AS (
  -- Mean-across-non-empty-buckets == simple AVG over the rows we just produced,
  -- because per_user_bucket only has a row when the bucket had >= 1 game.
  SELECT
    user_id, tc, elo_bucket,
    count(*) AS buckets_used,        -- 1..3
    sum(games) AS total_games,
    avg(bucket_rate) AS skill
  FROM per_user_bucket
  GROUP BY user_id, tc, elo_bucket
  HAVING sum(games) >= 20
     AND count(*) >= 2                -- at least 2 of the 3 buckets non-empty
)
SELECT
  elo_bucket, tc,
  count(*) AS n_users,
  round(avg(skill)::numeric, 4) AS mean_skill,
  round(stddev_samp(skill)::numeric, 4) AS std_skill,
  round(percentile_cont(0.05) WITHIN GROUP (ORDER BY skill)::numeric, 4) AS p05,
  round(percentile_cont(0.25) WITHIN GROUP (ORDER BY skill)::numeric, 4) AS p25,
  round(percentile_cont(0.50) WITHIN GROUP (ORDER BY skill)::numeric, 4) AS p50,
  round(percentile_cont(0.75) WITHIN GROUP (ORDER BY skill)::numeric, 4) AS p75,
  round(percentile_cont(0.95) WITHIN GROUP (ORDER BY skill)::numeric, 4) AS p95,
  round(min(skill)::numeric, 4) AS min_skill,
  round(max(skill)::numeric, 4) AS max_skill
FROM per_user_skill
GROUP BY elo_bucket, tc
HAVING count(*) >= 10
ORDER BY elo_bucket, CASE tc WHEN 'bullet' THEN 1 WHEN 'blitz' THEN 2 WHEN 'rapid' THEN 3 WHEN 'classical' THEN 4 END;
```

### Output

Two views:

1. **ELO × TC matrix (primary).** Rows = ELO bucket (`<500, 500–999, 1000–1499, ...`), columns = TC (bullet / blitz / rapid / classical). Each cell shows `p50 [p25–p75] (n_users)`. Grey out cells with `n_users < 10` as low-confidence.
2. **Pooled percentile table.** Single row per TC, columns `n_users / p05 / p25 / p50 / p75 / p95 / mean ± std`. Also emit one "all TCs pooled" row as the overall baseline.

Below the tables:
- **Currently set in code:** the literal `ENDGAME_SKILL_ZONES` boundaries and the "typical value" comment.
- **Recommended neutral zone** = `[p25, p75]` pooled across all ELO buckets and TCs (the skill gauge in `EndgameScoreGapSection.tsx` is shown on the overall tab, so the pooled percentiles are what matter).
- **Recommended gauge range** = `[p05, p95]` pooled.
- **Slope by ELO:** state whether `p50` moves meaningfully across ELO buckets. If it does (e.g. > 5 pp between adjacent 500-wide buckets), note that a single pooled gauge will favor one ELO cohort over others — future work could consider ELO-stratified zones like Section 2's `FIXED_GAUGE_ZONES`, but only if the slope is large enough to justify UI complexity.
- **Verdict:** compare the code's current neutral band `[0.45, 0.55]` against the observed pooled p25/p75. State "keep", "widen to X", "narrow to Y", or "re-center at Z" with one-line rationale. Also flag whether the "typical value" code comment (52% last audited) still matches the pooled median within ±1pp.

### Per-user list (optional)

After the summary, dump the top 20 and bottom 20 users by pooled skill (collapsed across their cells) with columns `user_id / skill / buckets_used_avg / total_games / dominant_tc` so outliers are eyeballable. Useful to spot data-quality problems (e.g. a user whose skill is 0.9 because they only have 3 parity games — the sample floor should already exclude them, but double-check).

---

## Section 6 — Endgame ELO vs Actual ELO Gap

**Question:** How does the gap `Endgame ELO − Actual ELO` distribute across users per (platform × time-control) combo? The Endgame ELO Timeline chart shows this gap visually ("bright = Actual ELO, dark dashed = Endgame ELO"). This section answers "what magnitude of gap is typical?" and "is there systematic bias between platforms?" — useful for future calibration of any "notable divergence" callout, and sanity-checking the 400-Elo scaling coefficient in the formula.

The metric is computed per user per combo using the same window math as the live timeline: trailing 100 endgame games and trailing 100 all games, per combo. We use the user's **current** pool (not a rolling weekly series) to get one datapoint per (user, combo), which is what makes the distribution well-defined.

### Currently set in code (grep before reporting)

Read `app/services/endgame_service.py` and record the literal values of:
- `ENDGAME_ELO_TIMELINE_WINDOW` (trailing window size for the endgame pool — should be `100`)
- `_ENDGAME_ELO_SKILL_CLAMP_LO` and `_ENDGAME_ELO_SKILL_CLAMP_HI` (should be `0.05` and `0.95` — caps the formula's Elo contribution at ≈±510)
- `MIN_GAMES_FOR_TIMELINE` (imported from `app/services/openings_service.py`, should be `10` — per-point emission threshold)
- `_MATERIAL_ADVANTAGE_THRESHOLD` (should be `100`)

Also record the formula for reference:
`endgame_elo = round(avg_opp_rating + 400 · log10(skill / (1 − skill)))`

The `400` is the classical Elo scaling constant — a 400-point differential ⇒ the stronger side scores ~91% vs the weaker. The `log10(skill/(1−skill))` term is the inverse of the Elo expected-score curve applied to the measured skill rate.

### Query

We compute per-user per-combo skill (using the same 3-bucket logic as Section 5) and pair it with the average opponent rating and the user's own average rating over the same endgame pool. `actual_elo` in the query is the user's mean rating across their last N endgame games for that combo — this matches how the live timeline defines it at each weekly point (rolling mean user_rating over the all-games pool), collapsed to a single snapshot.

```sql
WITH first_endgame AS (
  SELECT game_id, min(ply) AS entry_ply
  FROM game_positions
  WHERE endgame_class IS NOT NULL
  GROUP BY game_id HAVING count(*) >= 6
),
endgame_games AS (
  SELECT
    g.user_id,
    g.platform,
    g.time_control_bucket AS tc,
    g.played_at,
    CASE WHEN g.user_color='white' THEN g.white_rating ELSE g.black_rating END AS user_rating,
    CASE WHEN g.user_color='white' THEN g.black_rating ELSE g.white_rating END AS opp_rating,
    CASE
      WHEN (g.result='1-0' AND g.user_color='white')
        OR (g.result='0-1' AND g.user_color='black') THEN 1.0
      WHEN g.result='1/2-1/2' THEN 0.5
      ELSE 0.0
    END AS score,
    CASE WHEN g.user_color='white' THEN 1 ELSE -1 END AS color_sign,
    ep.material_imbalance AS entry_imb,
    ap.material_imbalance AS after_imb,
    row_number() OVER (
      PARTITION BY g.user_id, g.platform, g.time_control_bucket
      ORDER BY g.played_at DESC, g.id DESC
    ) AS rn_desc
  FROM games g
  JOIN first_endgame fe ON fe.game_id = g.id
  JOIN game_positions ep
    ON ep.game_id = g.id AND ep.ply = fe.entry_ply
  LEFT JOIN game_positions ap
    ON ap.game_id = g.id AND ap.ply = fe.entry_ply + 4
   AND ap.endgame_class IS NOT NULL
  WHERE g.rated AND NOT g.is_computer_game
    AND g.time_control_bucket IS NOT NULL
    AND g.platform IN ('chess.com', 'lichess')
    AND (CASE WHEN g.user_color='white' THEN g.white_rating ELSE g.black_rating END) IS NOT NULL
    AND (CASE WHEN g.user_color='white' THEN g.black_rating ELSE g.white_rating END) IS NOT NULL
),
window_games AS (
  -- Trailing 100 endgame games per (user, platform, tc). Matches ENDGAME_ELO_TIMELINE_WINDOW.
  SELECT *
  FROM endgame_games
  WHERE rn_desc <= 100
),
classified AS (
  SELECT
    user_id, platform, tc, score, user_rating, opp_rating,
    CASE
      WHEN entry_imb IS NULL OR after_imb IS NULL THEN 'parity'
      WHEN (entry_imb * color_sign) >=  100 AND (after_imb * color_sign) >=  100 THEN 'conversion'
      WHEN (entry_imb * color_sign) <= -100 AND (after_imb * color_sign) <= -100 THEN 'recovery'
      ELSE 'parity'
    END AS bucket,
    CASE
      WHEN entry_imb IS NULL OR after_imb IS NULL THEN score
      WHEN (entry_imb * color_sign) >=  100 AND (after_imb * color_sign) >=  100
        THEN CASE WHEN score = 1.0 THEN 1.0 ELSE 0.0 END
      WHEN (entry_imb * color_sign) <= -100 AND (after_imb * color_sign) <= -100
        THEN CASE WHEN score >= 0.5 THEN 1.0 ELSE 0.0 END
      ELSE score
    END AS bucket_contribution
  FROM window_games
),
per_user_bucket AS (
  SELECT
    user_id, platform, tc, bucket,
    count(*) AS games,
    avg(bucket_contribution) AS bucket_rate
  FROM classified
  GROUP BY user_id, platform, tc, bucket
),
per_user_skill AS (
  SELECT
    user_id, platform, tc,
    count(*) AS buckets_used,
    sum(games) AS total_games,
    avg(bucket_rate) AS skill
  FROM per_user_bucket
  GROUP BY user_id, platform, tc
  HAVING sum(games) >= 30
     AND count(*) >= 2
),
per_user_pool AS (
  -- Opponent avg + user avg across the same endgame window (trailing 100).
  SELECT
    user_id, platform, tc,
    count(*) AS endgame_games,
    avg(opp_rating)::numeric AS avg_opp_rating,
    avg(user_rating)::numeric AS actual_elo
  FROM window_games
  GROUP BY user_id, platform, tc
),
joined AS (
  SELECT
    s.user_id, s.platform, s.tc, s.skill, s.total_games,
    p.avg_opp_rating, p.actual_elo,
    -- Clamp skill to [0.05, 0.95] before the log, matching _ENDGAME_ELO_SKILL_CLAMP_*
    least(0.95, greatest(0.05, s.skill)) AS clamped_skill
  FROM per_user_skill s
  JOIN per_user_pool p
    ON p.user_id = s.user_id AND p.platform = s.platform AND p.tc = s.tc
  WHERE p.endgame_games >= 30
),
elo AS (
  SELECT
    user_id, platform, tc, skill, total_games, avg_opp_rating, actual_elo,
    round(avg_opp_rating + 400 * log(10, clamped_skill / (1 - clamped_skill))) AS endgame_elo,
    round(avg_opp_rating + 400 * log(10, clamped_skill / (1 - clamped_skill)) - actual_elo) AS gap
  FROM joined
)
SELECT
  platform, tc,
  count(*) AS n_users,
  round(avg(actual_elo)::numeric) AS mean_actual,
  round(avg(endgame_elo)::numeric) AS mean_endgame,
  round(avg(gap)::numeric, 1) AS mean_gap,
  round(stddev_samp(gap)::numeric, 1) AS std_gap,
  round(percentile_cont(0.05) WITHIN GROUP (ORDER BY gap)::numeric) AS gap_p05,
  round(percentile_cont(0.25) WITHIN GROUP (ORDER BY gap)::numeric) AS gap_p25,
  round(percentile_cont(0.50) WITHIN GROUP (ORDER BY gap)::numeric) AS gap_p50,
  round(percentile_cont(0.75) WITHIN GROUP (ORDER BY gap)::numeric) AS gap_p75,
  round(percentile_cont(0.95) WITHIN GROUP (ORDER BY gap)::numeric) AS gap_p95,
  round(min(gap)::numeric) AS gap_min,
  round(max(gap)::numeric) AS gap_max
FROM elo
GROUP BY platform, tc
ORDER BY platform, CASE tc WHEN 'bullet' THEN 1 WHEN 'blitz' THEN 2 WHEN 'rapid' THEN 3 WHEN 'classical' THEN 4 END;
```

Note: Postgres' `log(base, numeric)` is `log_base(x)`, so `log(10, x)` is `log10(x)`. PG also has `log(x)` (base 10) without the base arg; either works but `log(10, x)` is explicit.

### Output

Three views:

1. **Per-combo gap percentile table.** Rows = 8 combos (chess.com × {bullet, blitz, rapid, classical} then lichess × same). Columns `n_users / gap_p05 / gap_p25 / gap_p50 / gap_p75 / gap_p95 / mean_gap ± std / mean_actual / mean_endgame`.
2. **Per-combo skill percentile table.** Same rows, columns `skill_p25 / skill_p50 / skill_p75` (re-aggregate from the `elo` CTE by swapping `gap` for `skill` — one follow-up query or reuse the Section 5 query filtered to the pool).
3. **Pooled gap histogram.** One row per 100-Elo-wide bucket from `gap_p05` to `gap_p95` pooled across combos, showing `count` and `cumulative %`. Quick visual sanity-check for distribution shape (expected: roughly bell-curve centered near 0 with modest right skew from the save-bonus in recovery games).

Below the tables:
- **Currently set in code:** literal values of `ENDGAME_ELO_TIMELINE_WINDOW`, the skill clamp bounds, `MIN_GAMES_FOR_TIMELINE`, `_MATERIAL_ADVANTAGE_THRESHOLD`, plus the formula itself.
- **Platform bias check:** state whether `mean_gap` differs systematically between chess.com and lichess (same TC) by more than ±25 Elo. Chess.com uses Glicko-1 and lichess uses Glicko-2 — non-zero bias is expected and not a bug, but document the observed magnitude so downstream features don't assume cross-platform symmetry.
- **TC slope check:** within each platform, state whether `mean_gap` drifts across TCs. Slower TCs tend to surface deeper endgame skill (longer games → more endgame technique visible), so bullet gaps may sit lower than classical gaps on average. Report the observed direction and magnitude.
- **Clamp saturation:** count users whose `skill` is at the clamp boundary (≤ 0.05 or ≥ 0.95). If more than 1% of qualifying users saturate on either side, the clamp is doing heavy lifting — consider whether that's the intended behaviour (it caps the formula's blow-up) or a symptom of the skill definition being too coarse.
- **Recommended "notable divergence" threshold (forward-looking):** `|gap| > gap_p90_abs` pooled (roughly the top/bottom decile). Today's live UI doesn't expose a "your endgames are pulling your rating up/down notably" callout, but if a future phase adds one this gives it a data-driven threshold.
- **Verdict on the 400-Elo scaling:** if the pooled `std_gap` lands in the 120–200 range, the formula's sensitivity looks reasonable. Much narrower (< 80) means the clamp is compressing the signal too aggressively; much wider (> 300) means a handful of small-sample users are dominating despite the 30-game floor — consider raising the floor in a future revision.

### Per-user list (optional)

Dump the 20 largest positive gaps and 20 largest negative gaps with columns `user_id / platform / tc / actual_elo / endgame_elo / gap / total_games / buckets_used` so tail users are eyeballable. Useful to spot data-quality problems (e.g. a user at the clamp with only 30 games — borderline sample).

---

## Report file layout

Write to `reports/benchmarks-YYYY-MM-DD.md` using today's UTC date. Layout:

```markdown
# FlawChess Benchmarks — <DATE>

- **DB**: prod / local
- **Snapshot taken**: <ISO timestamp>
- **Base filters**: rated = TRUE AND NOT is_computer_game
- **Sample floors**: <floors used>

## 1. Score % Difference (endgame vs non-endgame)
...

## 2. Conversion / Parity / Recovery by ELO × TC
...

## 3. Time Pressure at Endgame Entry
...

## 4. Time Pressure vs Performance — cross-TC comparison
...

## 5. Endgame Skill by ELO × TC
...

## 6. Endgame ELO vs Actual ELO Gap per combo
...

## Recommended thresholds summary
| Metric | Code constant | Currently set | Recommended (p25–p75 / p05–p95) | Verdict |
| ... | ... | ... | ... | ... |
```

The final summary table at the bottom is the main deliverable. Every row must cite the **code constant name** and its **currently-set value** alongside the recommendation, and end with an explicit verdict (`keep`, `widen to X`, `narrow to Y`, `re-center at Z`, `switch metric to %`, etc.). Recommendations without a current-value comparison are not useful — the point of the benchmark is to answer "should the live zone change, and to what?", not to invent zones in a vacuum.

## Re-running & append mode

If `reports/benchmarks-YYYY-MM-DD.md` already exists for today, check which sections are present. If the user asked for a subset (e.g. "just rerun section 3"), replace only that section — do not clobber the others. Always preserve the header and the final summary table (rebuild the summary from the sections present in the file).

If the user asks for an older date's benchmark (e.g. "run a new snapshot"), write to today's file; don't mutate old reports.
