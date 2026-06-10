# Phase 114: Benchmark Flaw-Delta Zone Computation — Research

**Researched:** 2026-06-10
**Domain:** Benchmark generator extension — flaw-delta per-(ELO×TC) quartile computation
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** All 13 flaw-delta metrics use the same estimator: paired per-game delta on a per-100-of-your-own-moves basis. Per game: `(your_tag_count − opp_tag_count) / your_moves_in_game × 100`. Per-cohort-user delta = mean of those paired per-game deltas. Then Q1/Q3 across cohort users per (ELO×TC) cell. The game is the independence unit; no count-rate vs proportion split.
- **D-02:** Unified estimator decided by analysis (see CONTEXT.md). The opportunity denominator's benefit does not survive ELO-matched pairing + the split's cost in zone stability.
- **D-03:** `squandered`/`lucky` (state-conditional) residual caveat goes in a Phase 115 tooltip line, not a separate denominator.
- **D-04:** SEED-040 family split, FLAWCMP-02 Wilson method — voided. Phase 115 uses the unified paired per-game delta for all families.
- **D-05:** Combos (`hasty+miss`, `low-clock+miss`) are two more metrics in the same pipeline, not deferred.
- **D-06:** Generator additionally emits a per-metric viability diagnostic (non-zero delta users, non-degenerate IQR cells, median events/user).
- **D-07:** A cell-specific Q1/Q3 is emitted only when the cell clears the contributor floor; otherwise null. Phase 115 falls back to marginal/global zone.
- **D-08:** Cohort-user inclusion gated by a single uniform "min analyzed games" floor applied to all 13 metrics. Exact N set at plan time. Existing ≥30-contributing-users-per-cell floor remains on top.
- **D-09:** Phase 114 deliverable is the benchmark report only — no committed JSON/Python zone module, no DB table.
- **D-10:** Phase 115 hand-authors final zone constants from the report.

### Claude's Discretion

- Exact placement/numbering of the new benchmark chapter in SKILL.md + report layout (e.g. "§5 Flaw-Delta Zones").
- Concrete `scripts/benchmarks/` module structure, SQL, and move-count denominator source.
- Exact form of the viability-diagnostic columns (D-06).
- Whether to add a chapter-diff gate test under `tests/scripts/benchmarks/` (recommended).

### Deferred Ideas (OUT OF SCOPE)

- Tactic-motif bullets (SEED-039) — zoneless until cohort-wide Stockfish PVs exist.
- Eval-coverage raising (SEED-012) — upstream eval-pipeline concern.
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| FLAWBMK-01 | Benchmark pipeline computes per-cohort-user you-opponent delta per flaw metric over their games | Confirmed via D-01 unified estimator; `game_flaws` has both sides materialized (Phase 113). SQL pattern documented in §Move-Count Denominator and §SQL Shape below. |
| FLAWBMK-02 | Pipeline emits per-(ELO×TC) Q1/Q3 quartiles + ELO and TC marginals | Confirmed reuse of `dist.agg_select` + `GROUPING SETS` pattern from existing chapters. |
| FLAWBMK-03 | Established Cohen's-d collapse verdict runs per metric per axis | `dist.verdict()` helper in `scripts/benchmarks/distribution.py` is reusable as-is. |
| FLAWBMK-04 | `/benchmarks` skill extended to produce these flaw-delta quartiles/marginals/verdicts, written to benchmark report | New chapter `"5-flaw-delta-zones"` added to `gen_benchmarks.py` CHAPTER_STUBS + `_CHAPTER_BUILDERS` + SKILL.md. |
</phase_requirements>

---

## Summary

Phase 113 materialized both sides' flaws in benchmark `game_flaws` (confirmed: 3,805,691 rows, ~50/50 player/opponent split). Phase 114 adds a new §5 chapter to `scripts/gen_benchmarks.py` that computes, for each of the 15 flaw-delta metrics (13 tags + 2 combos), the per-(ELO×TC) Q1/Q3 quartiles plus ELO and TC marginals, with the established Cohen's-d collapse verdict per axis.

The generator pattern is already fully established. The new chapter is a clean analogue of `chapter3.py`'s per-user metric blocks: one per-user CTE computing the mean paired-delta per user per (game-time ELO, TC) cell, then the shared `dist.agg_select` + `GROUPING SETS` pattern for pooled/marginal distribution, then `dist.verdict()` for the collapse verdict. The chapter feeds a new `scripts/benchmarks/chapter5.py` module.

The move-count denominator (`your_moves_in_game`) is confirmed derivable from `game_positions` via ply-parity counting — **not** from `games.move_count` (discussed below). `games.move_count` is 99.88% populated for analyzed benchmark games, but the correct denominator for the D-01 estimator is the count of `game_positions` rows where `ply >= 1` AND mover matches `user_color`, matching the existing `fetch_total_user_moves()` pattern in `library_repository.py`.

**Primary recommendation:** Add `scripts/benchmarks/chapter5.py` with a single `build(session)` function computing all 15 metrics in one SQL pass (or one pass per metric batch with shared per-user CTE), following the chapter3 analog. Register it as `"5-flaw-delta-zones"` in `gen_benchmarks.py`. The per-user floor is **20 analyzed games** (see D-08 analysis below).

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Flaw-delta per-game computation (SQL) | Database / Storage | — | Pure SQL aggregation over `game_flaws` + `game_positions` + `games`; no Python computation per row |
| Per-user quartile aggregation | Database / Storage | — | `percentile_cont`, `stddev_samp`, `GROUPING SETS` in SQL, reusing existing `dist.agg_select` |
| Cohen's-d collapse verdict | Backend (generator script) | — | `stats.max_abs_d()` + `dist.verdict()` in Python, operating on SQL-emitted marginals |
| Viability diagnostic | Database / Storage | Backend (generator script) | SQL counts non-zero contributors; Python formats/emits as diagnostic block |
| Report narration (verdict words + recommendations) | LLM (SKILL.md) | — | Code/LLM seam — generator emits numbers, SKILL.md applies verdict words and authors prose |
| Zone constants (Phase 115) | Backend (hand-authored Python) | Frontend (codegen) | `endgame_zones.py` pattern; `gen_endgame_zones_ts.py` codegen — Phase 115 concern |

---

## Standard Stack

No new dependencies. This phase uses only existing packages.

### Core (existing, no install needed)
| Component | Location | Purpose |
|-----------|----------|---------|
| `scripts/gen_benchmarks.py` | repo root | Entry point; chapter dispatch |
| `scripts/benchmarks/chapter5.py` | **new file** | §5 flaw-delta zones chapter |
| `scripts/benchmarks/sql.py` | existing | Shared CTE constants, ELO bucketing, sparse-cell exclusion |
| `scripts/benchmarks/distribution.py` | existing | `agg_select`, `GROUPING_SETS`, `split_grouping_sets`, `verdict` |
| `scripts/benchmarks/stats.py` | existing | `max_abs_d`, Cohen's-d computation |
| `scripts/benchmarks/render.py` | existing | `markdown_table`, `fmt_value`, `Unit` |
| `app/repositories/query_utils.py` | existing | `is_opponent_expr`, `player_only_gate` — parity convention |

### Package Legitimacy Audit

No new packages installed in this phase. All code uses existing project dependencies.

| Package | Verdict | Disposition |
|---------|---------|-------------|
| (none — existing stack only) | — | N/A |

---

## Architecture Patterns

### System Architecture Diagram

```
benchmark DB (port 5433)
  game_flaws (both sides — Phase 113 hand-off)
  game_positions (ply rows — user move count source)
  games (user_color, move_count, evals_completed_at, ratings)
  benchmark_selected_users + benchmark_ingest_checkpoints
       |
       v
scripts/gen_benchmarks.py --db benchmark
  → _CHAPTER_BUILDERS["5-flaw-delta-zones"] = chapter5.build
       |
       v
scripts/benchmarks/chapter5.py
  per_user_moves CTE (game_positions ply parity count)
  per_game_delta CTE (game_flaws tag counts, player vs opponent, per game)
  per_user_delta CTE (mean of per-game deltas per user per ELO×TC)
  distribution query (GROUPING SETS → pooled + ELO marginals + TC marginals)
  viability diagnostic query (non-zero contributors, IQR degeneracy)
       |
       v
reports/benchmark/benchmarks-generated.{json,md}  [gitignored]
       |
       v
SKILL.md narration (verdict words, recommendations, report assembly)
       |
       v
reports/benchmark/benchmarks-latest.md  [committed]
```

### Recommended Project Structure

New files:
```
scripts/benchmarks/
├── chapter5.py     # NEW — §5 Flaw-Delta Zones
tests/scripts/benchmarks/
├── test_chapter5_diff.py   # NEW (recommended) — numeric diff gate
```

Modified files:
```
scripts/gen_benchmarks.py       # register chapter5 in CHAPTER_STUBS + _CHAPTER_BUILDERS
.claude/skills/benchmarks/SKILL.md   # new §5 section (narration + report layout)
```

### Pattern: Chapter `build()` Function

Every chapter follows this shape — chapter5 follows the same contract: [ASSUMED based on chapter2.py/chapter3.py patterns, verified in session]

```python
# Source: scripts/benchmarks/chapter2.py + chapter3.py (verified in session)
async def build(session: AsyncSession) -> dict[str, Any]:
    values = await compute(session)
    return {"status": "OK", "section": SECTION, "values": values, "markdown": render(values)}
```

### Pattern: Canonical per-user CTE shape (from chapter3.py)

```python
# Source: scripts/benchmarks/chapter3.py _per_user_cte() (verified in session)
f"WITH {sql.SELECTED_USERS_CTE},\n"
"rows AS (\n"
f"  SELECT g.user_id, ({sql.USER_ELO_AT_GAME_SQL}) AS ueag, su.tc_bucket AS tc,\n"
"         ...per-game values...\n"
"  FROM games g\n"
"  JOIN selected_users su ON su.user_id = g.user_id\n"
f"  WHERE {sql.BASE_GAME_FILTER}\n"
"),\n"
"per_user AS (\n"
f"  SELECT user_id, ({bucket_case}) AS elo_bucket, tc,\n"
"         avg(...) AS metric_value\n"
f"  FROM rows WHERE ueag >= {sql.ELO_FLOOR}\n"
"  GROUP BY user_id, elo_bucket, tc\n"
f"  HAVING count(*) >= {FLOOR}\n"
"),\n"
"pu AS MATERIALIZED (\n"
f"  SELECT * FROM per_user WHERE {sql.SPARSE_CELL_EXCLUSION}\n"
")"
```

### Anti-Patterns to Avoid

- **Using `games.move_count` as the denominator:** `move_count` is total full moves (both colors). For "your moves", count `game_positions` rows where `ply >= 1` AND mover parity matches `user_color`. White user: even plies (0, 2, 4...); Black user: odd plies (1, 3, 5...). This distinction matters: in a 28-move game white makes 28 moves (plies 0..54 even) and black makes 27-28 (plies 1..53 odd).
- **Scattering `ply % 2` math inline:** Always use the `is_opponent_expr` / `player_only_gate` helpers from `query_utils.py`. A prior off-by-one bug lived here (D-01 / RESEARCH Pitfall 1 in Phase 113).
- **Running chapters with a short timeout:** The benchmark generator takes several minutes for heavy span scans. Do not add a timeout.
- **Omitting the checkpoint join:** `benchmark_selected_users` is the candidate pool. Without `bic.status = 'completed'`, skipped/failed candidates with no games pollute the sample.

---

## Q1: Move-Count Denominator (Load-Bearing, D-01)

**Confirmed answer:** Count `game_positions` rows with `ply >= 1` AND mover matches `user_color` via ply parity.

The exact SQL (SQL-only version for the benchmark generator, no SQLAlchemy ORM):

```sql
-- user_moves_in_game per (game_id, user_id): count game_positions plies where mover = user
SELECT
  gp.game_id,
  g.user_id,
  COUNT(*) AS user_moves
FROM game_positions gp
JOIN games g ON g.id = gp.game_id
WHERE gp.ply >= 1   -- ply 0 = initial position (no move)
  AND (
    (gp.ply % 2 = 0 AND g.user_color = 'white') OR
    (gp.ply % 2 = 1 AND g.user_color = 'black')
  )
GROUP BY gp.game_id, g.user_id
```

This mirrors `fetch_total_user_moves()` in `library_repository.py` (verified in session, lines 599–667) and the `_count_user_moves()` semantics. [VERIFIED: codebase grep]

**Why not `games.move_count`:** [VERIFIED: benchmark DB query session]
- `games.move_count` = total full moves in the game (integer). For a 28-move game, white makes 28 moves, black 27–28.
- The ply-count approach gives the exact player move count per game, consistent with what `fetch_total_user_moves()` computes, and avoids the off-by-one at game end (last move may be white or black).
- `games.move_count` is 99.88% populated for analyzed benchmark cohort games (1,607,089 of 1,609,033), so it could serve as a fast approximate denominator in a pinch, but the ply-count join is the correct approach.

**SQL integration in the chapter:** The per-game delta CTE joins `game_positions` for the user-move count inline alongside the `game_flaws` tag count. No separate subquery needed — a single join on `(game_id, ply_parity)`.

**Approximate denominator shortcut (optional):** If the per-game `game_positions` join proves slow in practice (it adds ~1.5M rows to scan), `CEIL(g.move_count / 2.0)` can substitute for white and `FLOOR(g.move_count / 2.0)` for black as a fast approximation. Measurement at plan time confirms which to use. For now the ply-parity join is the authoritative approach.

---

## Q2: Generator Module Structure — Closest Analog and Seams

### CHAPTER_STUBS + _CHAPTER_BUILDERS registration

In `scripts/gen_benchmarks.py` (lines 140–168, verified in session):

1. Add to `CHAPTER_STUBS` tuple (insert after `"3.4-endgame-type"`, before `"4-global-percentile-cdf"`):
   ```python
   ("5-flaw-delta-zones", "SKILL.md §5 — flaw-delta per-(ELO×TC) Q1/Q3 zones + collapse verdicts"),
   ```

2. Add to `_CHAPTER_BUILDERS` dict:
   ```python
   "5-flaw-delta-zones": chapter5.build,
   ```

3. Add import at top:
   ```python
   from scripts.benchmarks import chapter5
   ```

### Closest analog: `chapter3.py` `build_32` (Conv/Parity/Recovery — multi-metric per-user)

`build_32` / `compute_321` computes 4 metrics (conv, parity, recov, skill) in one pass over a shared per-user CTE + UNION ALL metric selects. Chapter 5 follows the same pattern but with 15 metrics and a different per-user CTE.

Key difference: chapter5 needs a **per-game** intermediate (player tag count, opponent tag count, user moves per game), then aggregates to per-user. Chapter 3.2 computes per-game averages directly. The SQL shape needs an extra per-game CTE layer.

### Suggested chapter5.py SQL shape (one scan for all 15 metrics):

```sql
-- Step 1: selected_users CTE (canonical)
WITH selected_users AS (...),

-- Step 2: analyzed games in cohort (equal-footing + rated + TC match)
base_games AS (
  SELECT g.id AS game_id, g.user_id, g.user_color,
         (CASE WHEN g.user_color::text = 'white' THEN g.white_rating ELSE g.black_rating END) AS ueag,
         su.tc_bucket AS tc
  FROM games g
  JOIN selected_users su ON su.user_id = g.user_id
  WHERE g.rated AND NOT g.is_computer_game
    AND g.time_control_bucket::text = su.tc_bucket
    AND g.white_rating IS NOT NULL AND g.black_rating IS NOT NULL
    AND abs((CASE WHEN g.user_color::text='white' THEN g.white_rating ELSE g.black_rating END)
          - (CASE WHEN g.user_color::text='white' THEN g.black_rating ELSE g.white_rating END)) <= 100
    AND g.evals_completed_at IS NOT NULL
    AND (CASE WHEN g.user_color::text = 'white' THEN g.white_rating ELSE g.black_rating END) >= 800
),

-- Step 3: user move count per game (ply parity, ply >= 1)
user_moves_per_game AS (
  SELECT gp.game_id, COUNT(*) AS user_moves
  FROM game_positions gp
  JOIN base_games bg ON bg.game_id = gp.game_id
  WHERE gp.ply >= 1
    AND ((gp.ply % 2 = 0 AND bg.user_color = 'white')
      OR (gp.ply % 2 = 1 AND bg.user_color = 'black'))
  GROUP BY gp.game_id
),

-- Step 4: per-game tag counts for player and opponent
per_game_tags AS (
  SELECT
    gf.game_id,
    bg.user_id, bg.ueag, bg.tc, bg.user_color,
    um.user_moves,
    -- player flaws (is_opponent = False)
    COUNT(*) FILTER(WHERE
      (gf.ply % 2 = 0 AND bg.user_color = 'white') OR
      (gf.ply % 2 = 1 AND bg.user_color = 'black')
    ) AS p_flaw_rate,
    -- ... (one column per tag × side, 15 metrics × 2 sides)
    -- opponent flaws (is_opponent = True)
    COUNT(*) FILTER(WHERE
      (gf.ply % 2 = 0 AND bg.user_color = 'black') OR
      (gf.ply % 2 = 1 AND bg.user_color = 'white')
    ) AS o_flaw_rate,
    -- ... all 15 metrics for both sides
  FROM game_flaws gf
  JOIN base_games bg ON bg.game_id = gf.game_id AND bg.user_id = gf.user_id
  JOIN user_moves_per_game um ON um.game_id = gf.game_id
  GROUP BY gf.game_id, bg.user_id, bg.ueag, bg.tc, bg.user_color, um.user_moves
),

-- Step 5: per-game deltas (per-100 of user moves)
per_game_delta AS (
  SELECT user_id, ueag, tc,
         (p_flaw_rate - o_flaw_rate)::float / NULLIF(user_moves, 0) * 100 AS d_flaw_rate,
         -- ... all 15 delta columns
  FROM per_game_tags
  WHERE user_moves > 0
),

-- Step 6: per-user mean delta per (game-time ELO, TC), floor gate
per_user AS (
  SELECT user_id, (<elo_bucket_case>) AS elo_bucket, tc,
         avg(d_flaw_rate) AS delta_flaw_rate,
         -- ... avg of all 15 delta columns
         count(*) AS analyzed_games
  FROM per_game_delta
  WHERE ueag >= 800
  GROUP BY user_id, elo_bucket, tc
  HAVING count(*) >= <MIN_ANALYZED_GAMES>   -- D-08 floor
),

-- Step 7: exclude sparse cell for GROUPING SETS
pu AS MATERIALIZED (
  SELECT * FROM per_user WHERE NOT (elo_bucket = 2400 AND tc = 'classical')
)
-- Then 15 UNION ALL agg_select blocks (or loop in Python)
```

**Performance note:** The `game_flaws` JOIN on `(game_id, user_id)` touches 3.8M rows. A `MATERIALIZED` CTE on `base_games` (only analyzed cohort games) reduces the scan to ~1.6M game_flaws rows. The `user_moves_per_game` JOIN on `game_positions` touches ~90M rows in a filtered context; adding `MATERIALIZED` on `base_games` narrows it significantly.

---

## Q3: Cohen's-d Collapse-Verdict Reuse

**Confirmed fully reusable as-is.** [VERIFIED: codebase read]

Location: `scripts/benchmarks/distribution.py` lines 158–163 (`verdict()` function) + `scripts/benchmarks/stats.py` (`max_abs_d()`).

```python
# Source: scripts/benchmarks/distribution.py verdict() (verified in session)
def verdict(axis: str, marginals: Sequence[Marginal]) -> Verdict:
    levels = [
        stats.LevelStat(m["label"], m["dist"]["n"], m["mean_raw"], m["var"]) for m in marginals
    ]
    result = stats.max_abs_d(levels)
    return Verdict(axis=axis, max_abs_d=result.max_abs_d, pair=result.pair)
```

Verdict thresholds (hard-coded, from SKILL.md §"Collapse verdict methodology"):
- `< 0.2` → **collapse** (single global zone)
- `0.2 ≤ d < 0.5` → **review** (default to single unless UI argument warrants splitting)
- `≥ 0.5` → **keep separate** (stratify zones along this axis)

The flaw-delta metrics are continuous per-user means (not bounded to [0,1]) — Cohen's d is scale-invariant, so the same thresholds apply without adaptation.

**Sparse-cell exclusion in verdicts:** The existing `SPARSE_CELL_EXCLUSION` predicate (`NOT (elo_bucket = 2400 AND tc = 'classical')`) applied in the `pu AS MATERIALIZED` CTE gates both the distribution and the verdict inputs. No adapter needed.

---

## Q4: The 15 Metrics — Exact Tag Keys

**Tag names as stored in `game_flaws` columns** (verified against `app/repositories/game_flaws_repository.py` and `app/services/flaws_service.py` in this session): [VERIFIED: codebase read]

The `game_flaws` table does NOT store string tags. Tags are encoded as integer columns and boolean columns:

| Metric | Column | Filter predicate | Notes |
|--------|--------|-----------------|-------|
| **Flaw Rate** | `severity IN (1, 2)` | `TRUE` (all rows are M+B) | All `game_flaws` rows qualify |
| **low-clock** | `tempo` | `tempo = 0` | `_TEMPO_INT: {"low-clock": 0, "hasty": 1, "unrushed": 2}` |
| **hasty** | `tempo` | `tempo = 1` | |
| **unrushed** | `tempo` | `tempo = 2` | |
| **opening** | `phase` | `phase = 0` | `_PHASE_INT: {"opening": 0, "middlegame": 1, "endgame": 2}` |
| **middlegame** | `phase` | `phase = 1` | |
| **endgame** | `phase` | `phase = 2` | |
| **miss** | `is_miss` | `is_miss = TRUE` | Boolean column |
| **lucky** | `is_lucky` | `is_lucky = TRUE` | Boolean column |
| **reversed** | `is_reversed` | `is_reversed = TRUE` | Boolean column |
| **squandered** | `is_squandered` | `is_squandered = TRUE` | Boolean column |
| **hasty+miss** (flagship combo) | `tempo`, `is_miss` | `tempo = 1 AND is_miss = TRUE` | Both conditions on same row |
| **low-clock+miss** (combo) | `tempo`, `is_miss` | `tempo = 0 AND is_miss = TRUE` | Both conditions on same row |

**Tag names reconciliation (IMPORTANT):** The `flaw-tag-naming.md` note describes a rename (`hasty` → `impatient`, `unrushed` → `considered`, `lucky` → `lucky-escape`) that had NOT been applied to the code as of the research session. The actual column encoding in `game_flaws_repository.py` line 30 uses `{"low-clock": 0, "hasty": 1, "unrushed": 2}` and the boolean columns are `is_miss`, `is_lucky`, `is_reversed`, `is_squandered`. The Phase 115 UI concern will use whatever names are live in code at that time. For Phase 114 SQL, use the integer/boolean column predicates above — tag names do not appear in the benchmark SQL.

**Combo mechanics:** A combo numerator counts `game_flaws` rows where BOTH predicates are true on the same row (same move). This is natural since a single `game_flaws` row represents one flaw event with all its tags. [VERIFIED: codebase read of game_flaw.py model]

---

## Q5: Chapter-Diff Test Pattern

**Pattern:** Each diff test file imports the chapter module, calls `chapter.compute(session)` or uses `chapter.build(session)`, then asserts pooled + ELO + TC marginal values and verdict `max_abs_d` values against known-good expected dicts. [VERIFIED: read of `tests/scripts/benchmarks/test_chapter3_diff.py`]

Key test structure:
```python
# Source: tests/scripts/benchmarks/test_chapter3_diff.py (verified in session)
pytestmark = pytest.mark.asyncio

EXPECTED_POOLED = {"n": ..., "mean": ..., "sd": ..., "p05": ..., "p25": ..., "p50": ..., "p75": ..., "p95": ...}
EXPECTED_ELO = {"800": (n, mean, sd, p25, p50, p75), ...}
EXPECTED_TC = {"bullet": (n, mean, sd, p25, p50, p75), ...}
EXPECTED_VERDICTS = {"metric_name": {"TC": (("level_a", "level_b"), max_d), "ELO": (...)}, ...}

async def test_chapter5_flaw_delta(benchmark_session: AsyncSession) -> None:
    values = await chapter5.compute(benchmark_session)
    # assert per-metric pooled, ELO, TC, verdict blocks
```

**Exclusion from default pytest run:** All benchmark tests are in `tests/scripts/benchmarks/` which is excluded via `--ignore` in `pyproject.toml`. They run on demand:
```bash
uv run pytest tests/scripts/benchmarks/test_chapter5_diff.py -q
```

**Recommendation:** Add `tests/scripts/benchmarks/test_chapter5_diff.py` — the code/LLM seam is exactly the scenario these gates protect. The gate validates that the generator numbers match what the SKILL narrates.

---

## Q6: Viability Diagnostic Shape

**Recommended per-metric diagnostic columns** (satisfies FLAWCMP-04 in Phase 115 by being readable from the report artifact):

For each of the 15 metrics in the report artifact JSON (under `chapters["5-flaw-delta-zones"]["values"]["viability"]`):

| Column | Type | Meaning |
|--------|------|---------|
| `metric` | str | e.g. `"hasty_miss"` |
| `users_contributing` | int | Users with non-zero per-user mean delta (player side has at least one event of this tag) |
| `users_total` | int | Total users passing the analyzed-games floor |
| `pct_nonzero` | float | `users_contributing / users_total * 100` |
| `cells_with_iqr` | int | Number of (ELO×TC) cells where `q75 > q25` (non-degenerate IQR) |
| `cells_total` | int | Total cells with ≥30 contributors |
| `median_events_per_user` | float | Median of the per-user numerator event count (unscaled, over all analyzed games) |

**Critical metrics to flag:** `low-clock` (only 75% of users have any), `low-clock+miss` (only 64% non-zero), `reversed` and `squandered` (both dense post-recalibration — 98% and 99% non-zero respectively per benchmark query results).

---

## Q7: D-08 Per-User Games Floor — Recommended Value

**Data:** [VERIFIED: benchmark DB query session, 2026-06-10]

Cohort analyzed-games distribution (3,753 users, over their selected TC, equal-footing not yet applied):

| Percentile | Analyzed games/user |
|------------|-------------------|
| p05 | 40 |
| p10 | 60 |
| p25 | 108 |
| p50 | 240 |
| p75 | 931 |
| p90 | 1000 |
| min | 2 |
| max | 1000 |

Users meeting floor thresholds (out of 3,753 total):
- ≥10 games: 3,736 (99.5%)
- ≥20 games: 3,700 (98.6%)
- ≥30 games: 3,637 (96.9%)
- ≥50 games: 3,468 (92.4%)
- ≥100 games: 2,908 (77.5%)

**Recommendation: floor = 20 analyzed games** (D-08).

Rationale:
- ≥20 passes 98.6% of the cohort, giving maximum statistical power for per-cell Q1/Q3.
- The existing `ENDGAME_MIN_GAMES = 20` constant in `scripts/benchmarks/sql.py` uses the same floor for endgame metrics — consistent.
- Dropping to ≥10 passes 99.5% but allows very noisy per-user deltas (10 games → wide CI on the per-user mean).
- Raising to ≥30 drops 3.1% of users with minimal gain in per-user delta stability.
- The ≥30-contributing-users-per-cell floor stays on top (cell-level stability), independent of this per-user floor.

**Constant to define in chapter5.py:**
```python
FLAW_DELTA_MIN_GAMES: int = 20  # Per-user analyzed-games floor for flaw-delta metrics (D-08)
```

---

## Common Pitfalls

### Pitfall 1: Off-by-one in ply parity (mover detection)
**What goes wrong:** Writing `ply % 2 = 1` for white mover instead of `ply % 2 = 0`. A prior off-by-one bug existed in this exact code area (documented in Phase 113 D-01).
**Why it happens:** The convention (even ply = white) is non-obvious and appears in multiple places.
**How to avoid:** Always use the SQL fragment matching `is_opponent_expr` in `query_utils.py` (even ply → white mover, odd ply → black mover). In pure SQL contexts write the same logic inline with a comment referencing the canonical source.
**Warning signs:** Player/opponent flaw counts flip in viability diagnostic (opponent rows > player rows by large margin, or vice versa).

### Pitfall 2: Denominator = 0 for games without game_positions rows
**What goes wrong:** Some games may have `evals_completed_at IS NOT NULL` but zero `game_positions` rows (edge cases: games with no positions analyzed). Division by zero.
**Why it happens:** The ply-parity count of `game_positions` could be 0.
**How to avoid:** Filter `WHERE user_moves > 0` in the per-game delta CTE before the division. Use `NULLIF(user_moves, 0) * 100` in SQL.
**Warning signs:** NULL or infinite delta values appearing in distributions.

### Pitfall 3: Including non-cohort-user `game_flaws` rows
**What goes wrong:** `game_flaws` in benchmark DB contains rows for all users (4,434 users with flaws), but only 3,753 are the cohort (benchmark_selected_users + completed checkpoint). Extra users inflate counts.
**Why it happens:** Dev-user flaws may be in the benchmark DB (users 28 & 44 from the backfill, or other non-cohort benchmark stubs).
**How to avoid:** The `selected_users` CTE + `JOIN selected_users su ON su.user_id = ...` is the mandatory cohort filter for every chapter query.

### Pitfall 4: Mixing game-time ELO bucketing with snapshot-rating bucketing
**What goes wrong:** Using `bsu.rating_bucket` instead of per-game bucketing, causing rating-lag bias in ELO-axis Cohen's-d (documented extensively in SKILL.md).
**How to avoid:** Always derive `elo_bucket` via `sql.elo_bucket_case_sql(sql.USER_ELO_AT_GAME_SQL)`.

### Pitfall 5: Omitting the equal-footing filter on flaw-delta games
**What goes wrong:** Matchmaking confound inflates apparent ELO skill ramp. 2400 cohort plays avg 50–130 Elo weaker opponents.
**How to avoid:** Include `sql.EQUAL_FOOTING_FILTER` (`abs(user_elo - opp_elo) <= 100`) in `base_games` CTE alongside `g.rated AND NOT g.is_computer_game`.

### Pitfall 6: Column name `is_miss` vs `miss` in SQL alias chains
**What goes wrong:** The `game_flaws` column is `is_miss`, `is_lucky`, `is_reversed`, `is_squandered`; but when aliased in a CTE inner SELECT, the outer query must use the alias name. Discovered in benchmark DB query session.
**How to avoid:** Use consistent column names throughout all CTE layers. Prefer `is_miss` as the alias to match the model column name.

---

## Code Examples

### Verified SQL pattern: user ply count per game

```sql
-- Source: app/repositories/library_repository.py fetch_total_user_moves() (verified in session)
-- Count player's moves per game using ply parity
SELECT gp.game_id, COUNT(*) AS user_moves
FROM game_positions gp
JOIN games g ON g.id = gp.game_id
WHERE gp.ply >= 1
  AND (
    (gp.ply % 2 = 0 AND g.user_color = 'white') OR
    (gp.ply % 2 = 1 AND g.user_color = 'black')
  )
GROUP BY gp.game_id
```

### Verified pattern: tag count split by player/opponent side

```sql
-- Source: app/repositories/query_utils.py is_opponent_expr (verified in session)
-- Player flaws: NOT is_opponent (even ply → white, player must be white; etc.)
COUNT(*) FILTER(WHERE
  (gf.ply % 2 = 0 AND g.user_color = 'white') OR
  (gf.ply % 2 = 1 AND g.user_color = 'black')
) AS player_flaw_count,

-- Opponent flaws: is_opponent
COUNT(*) FILTER(WHERE
  (gf.ply % 2 = 0 AND g.user_color = 'black') OR
  (gf.ply % 2 = 1 AND g.user_color = 'white')
) AS opp_flaw_count
```

### Verified pattern: per-game delta, per-100-user-moves

```sql
-- D-01 estimator: (your_tag_count − opp_tag_count) / your_moves_in_game × 100
-- Source: CONTEXT.md D-01 (verified formulation, benchmark DB confirmed both sides materialized)
(player_tag_count - opp_tag_count)::float / NULLIF(user_moves, 0) * 100 AS delta_per_100
```

### Verified pattern: per-user mean delta with floor gate

```python
# Source: scripts/benchmarks/chapter3.py _per_user_cte() pattern (verified in session)
"per_user AS (\n"
f"  SELECT user_id, ({bucket_case}) AS elo_bucket, tc,\n"
"         avg(delta_flaw_rate) AS d_flaw_rate,\n"
"         ... (all 15 metrics)\n"
f"  FROM per_game_delta WHERE ueag >= {sql.ELO_FLOOR}\n"
"  GROUP BY user_id, elo_bucket, tc\n"
f"  HAVING count(*) >= {FLAW_DELTA_MIN_GAMES}\n"  # D-08 floor = 20
")"
```

### Verified pattern: distribution aggregation call

```python
# Source: scripts/benchmarks/distribution.py (verified in session)
# agg_select + GROUPING SETS → split_grouping_sets → verdict
query = (
    _per_user_cte()
    + "\nSELECT\n"
    + dist.agg_select("d_flaw_rate", digits=4)  # proportion-like metric, 4 dp
    + f"\nFROM pu {dist.GROUPING_SETS}"
)
rows = await _fetch(session, query)
pooled, elo, tc = dist.split_grouping_sets(rows)
verdicts = [dist.verdict("TC", tc), dist.verdict("ELO", elo)]
```

---

## D-03 Spot-Check: Squandered/Lucky Exposure Confound

**Data from benchmark DB query (2026-06-10):** [VERIFIED: benchmark DB query session]

At ≥20 analyzed games floor:
- `squandered`: 3,681 of 3,700 users non-zero (99.5%); p10 = 6, p25 = 11 events
- `lucky`: 3,743 of 3,750 users non-zero (99.8%); p50 = substantial

The recalibration of `squandered` thresholds (2026-06-09, SQUANDERED_EXIT_ES 0.60→0.5910, FROM_WINNING_ES 0.85→0.7511) already delivered the expected 3× density gain per SEED-040 §"Upstream: impact-tag threshold recalibration." This confirms:
- Per-user mean deltas will be non-degenerate for nearly all cohort users for both impact tags.
- The exposure confound (D-03) is second-order given ELO-matched pairing — no further action in Phase 114.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Benchmark DB (port 5433) | All benchmark queries | Confirmed running | PostgreSQL 18 (Docker) | `bin/benchmark_db.sh start` |
| `game_flaws` both sides | Phase 114 core | Confirmed (3.8M rows, ~50/50 split) | Phase 113 hand-off complete | None — Phase 113 must complete first |
| `uv` + project Python env | Generator run | Confirmed | Python 3.13 | N/A |

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (asyncio) |
| Config file | `pyproject.toml` (addopts `--ignore=tests/scripts/benchmarks`) |
| Quick run command | `uv run pytest tests/scripts/benchmarks/test_chapter5_diff.py -q` |
| Full benchmark gate | `uv run pytest tests/scripts/benchmarks -q` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| FLAWBMK-01 | Computes per-user delta for all 15 metrics | unit (DB) | `uv run pytest tests/scripts/benchmarks/test_chapter5_diff.py` | ❌ Wave 0 |
| FLAWBMK-02 | Emits Q1/Q3 + ELO + TC marginals | unit (DB) | same | ❌ Wave 0 |
| FLAWBMK-03 | Cohen's-d verdicts per metric per axis | unit (DB) | same | ❌ Wave 0 |
| FLAWBMK-04 | Report artifact written with all 15 metrics | integration | generator smoke run | N/A (manual UAT) |

### Sampling Rate
- Per task commit: `uv run ruff check app/ tests/ && uv run ty check app/ tests/`
- Per wave merge: `uv run pytest -n auto -x` (standard suite; benchmark gates run separately on demand)
- Phase gate: generator run + SKILL.md narration + HUMAN-UAT report review

### Wave 0 Gaps
- [ ] `tests/scripts/benchmarks/test_chapter5_diff.py` — numeric diff gate for all 15 metrics, following `test_chapter3_diff.py` pattern
- [ ] `scripts/benchmarks/chapter5.py` — new chapter module (the primary deliverable)

*(Existing test infrastructure covers standard suite; only benchmark-specific files are new)*

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Count-rate vs proportion family split (SEED-040) | Single unified per-100-moves paired-delta estimator (D-01) | Phase 114 context session 2026-06-10 | No Wilson/FLAWCMP-02 machinery; one SQL shape for all 15 metrics |
| `is_opponent` stored column (SEED-040 original) | Derived at query time via ply-parity + `user_color` helper | Phase 113 context D-01 | No migration, no index; single tested helper |
| Hand-computed benchmark numbers (SKILL.md old flow) | Generator-driven (`gen_benchmarks.py`) | SEED-029 Phase A | Deterministic artifact, LLM narrates only |

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `games.move_count` is NULL for only 0.12% of analyzed benchmark games (1,944 of 1,609,033) | Q1 Move-Count Denominator | No functional risk — the ply-parity join from `game_positions` is the authoritative approach regardless; `move_count` is mentioned only as a possible approximation |
| A2 | The tag-rename from flaw-tag-naming.md (`hasty` → `impatient`, etc.) has NOT been applied to `game_flaws_repository.py` as of Phase 114 | Q4 The 15 Metrics | If it was applied, the integer encoding `{"hasty": 1}` would need updating; verify before writing SQL |
| A3 | The impact threshold recalibration (SQUANDERED_EXIT_ES, FROM_WINNING_ES, WINNING_LINE_ES, LOSING_LINE_ES) in flaw-tag-definitions.md has been implemented in `flaws_service.py` before the benchmark backfill | Q4 / D-03 | If NOT yet applied, `squandered` density may be lower than the benchmark query showed (which used live data); the recalibration was described as "pending /gsd-quick" as of 2026-06-09 |

**A3 clarification:** The `flaws_service.py` constants at lines 56–59 (verified in session) show:
- `FROM_WINNING_ES: float = 0.7511` (75.11% — recalibrated target ≈ +3.0 ✓)
- `WINNING_LINE_ES: float = 0.6762` (67.62% — recalibrated target ≈ +2.0 ✓)
- `LOSING_LINE_ES: float = 0.3238` (32.38% ✓)
- `SQUANDERED_EXIT_ES: float = 0.5910` (59.10% ✓)

All four recalibrated values ARE present in the code. The "pending /gsd-quick" note in flaw-tag-definitions.md is stale — the recalibration has been implemented. A2 remains to verify (tag naming).

---

## Open Questions

1. **Tag rename status (A2)**
   - What we know: `game_flaws_repository.py` uses `{"low-clock": 0, "hasty": 1, "unrushed": 2}`. `flaw-tag-naming.md` describes a rename to `impatient`/`considered`/`lucky-escape` but marks it as not yet implemented at the time of writing.
   - What's unclear: Whether any subsequent phase (107 or later) applied the rename to `game_flaws_repository.py`.
   - Recommendation: At plan start, verify `_TEMPO_INT` dict in `game_flaws_repository.py` still contains `"hasty"` and `"unrushed"` as keys. The SQL filters use integer values (0, 1, 2), not tag strings, so a tag rename in the Python code would not break the SQL.

2. **Performance of the multi-metric per-game CTE**
   - What we know: ~1.6M analyzed benchmark games × ~15 tag conditions per `game_flaws` join.
   - What's unclear: Whether a single 15-metric SQL pass or separate per-metric passes will be faster in practice.
   - Recommendation: Start with a single pass (one per_game_tags CTE, all 15 tag columns). If the query exceeds 5 minutes on the benchmark DB, split into logical groups (flaw rate + phase/tempo in one pass, opportunity + impact + combos in a second).

---

## Project Constraints (from CLAUDE.md)

- No magic numbers: define `FLAW_DELTA_MIN_GAMES: int = 20` as a named constant in `chapter5.py` (D-08 floor) and `FLAW_DELTA_DIGITS: int = 4` for SQL rounding.
- `ty` compliance: all new functions need explicit return type annotations; use `Sequence[RowMapping]` not `list` for SQL result parameters.
- Benchmark DB guard: generator must only run against `benchmark` or `dev` targets (never prod). The `_TARGET_PORT` dict in `gen_benchmarks.py` already enforces this.
- `uv run python scripts/gen_benchmarks.py --db benchmark` is the invocation; no timeout.
- Tests under `tests/scripts/benchmarks/` are excluded from `uv run pytest -n auto` via `addopts --ignore` in `pyproject.toml`.
- No new migrations, no new DB tables, no new committed JSON artifacts (D-09). The generator writes only gitignored intermediates.

---

## Sources

### Primary (HIGH confidence)
- `scripts/gen_benchmarks.py` — entry point, chapter dispatch, CHAPTER_STUBS, _CHAPTER_BUILDERS
- `scripts/benchmarks/sql.py` — canonical CTE constants, ELO bucketing, sparse-cell exclusion, equal-footing filter
- `scripts/benchmarks/distribution.py` — agg_select, GROUPING_SETS, split_grouping_sets, verdict
- `scripts/benchmarks/chapter2.py`, `chapter3.py` — concrete build/compute/render pattern to replicate
- `app/repositories/query_utils.py` — is_opponent_expr, player_only_gate (ply-parity convention)
- `app/repositories/library_repository.py` — fetch_total_user_moves() (confirmed ply-parity move-count pattern)
- `app/models/game_flaw.py` — GameFlaw schema (integer-encoded tempo/phase, boolean opportunity/impact)
- `app/repositories/game_flaws_repository.py` — _TEMPO_INT, _PHASE_INT encoding maps
- `app/services/flaws_service.py` — FlawTag Literal, impact constants (recalibration confirmed implemented)
- Benchmark DB queries (2026-06-10): cohort distribution, tag viability, move_count availability, both-sides materialization

### Secondary (MEDIUM confidence)
- `.planning/phases/114-benchmark-flaw-delta-zone-computation/114-CONTEXT.md` — locked decisions D-01..D-10
- `.planning/phases/113-opponent-flaw-materialization/113-CONTEXT.md` — Phase 113 hand-off confirmation
- `.claude/skills/benchmarks/SKILL.md` — methodology, collapse verdict thresholds, sparse-cell rule, report layout

---

## Metadata

**Confidence breakdown:**
- SQL shape and denominator source: HIGH — verified against actual code + benchmark DB
- Tag encoding: HIGH — verified against game_flaw.py model + game_flaws_repository.py
- Cohen's-d reuse: HIGH — verified distribution.py + stats.py code
- Benchmark cohort data: HIGH — live queries against benchmark DB (2026-06-10)
- D-08 floor recommendation: HIGH — supported by cohort distribution data
- Viability diagnostic shape: MEDIUM — derived from D-06 requirements, specific column names are Claude's discretion

**Research date:** 2026-06-10
**Valid until:** 2026-09-10 (stable infrastructure; only relevant change would be a new benchmark DB ingest)
