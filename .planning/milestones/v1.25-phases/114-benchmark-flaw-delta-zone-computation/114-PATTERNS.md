# Phase 114: Benchmark Flaw-Delta Zone Computation - Pattern Map

**Mapped:** 2026-06-10
**Files analyzed:** 4 new/modified files
**Analogs found:** 4 / 4

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `scripts/benchmarks/chapter5.py` | service (benchmark chapter) | batch / transform | `scripts/benchmarks/chapter3.py` | exact |
| `scripts/gen_benchmarks.py` | config / entry point | batch | `scripts/gen_benchmarks.py` (self) | exact (registration seam) |
| `tests/scripts/benchmarks/test_chapter5_diff.py` | test | batch | `tests/scripts/benchmarks/test_chapter3_diff.py` | exact |
| `.claude/skills/benchmarks/SKILL.md` | docs / narration | — | existing SKILL.md (self) | exact (new section appended) |

---

## Pattern Assignments

### `scripts/benchmarks/chapter5.py` (NEW — benchmark chapter, batch/transform)

**Analog:** `scripts/benchmarks/chapter3.py`

**Imports pattern** (`chapter3.py` lines 59–79):
```python
from __future__ import annotations

from collections.abc import Sequence
from typing import Any, TypedDict

from sqlalchemy import RowMapping, text
from sqlalchemy.ext.asyncio import AsyncSession

from scripts.benchmarks import distribution as dist
from scripts.benchmarks import sql
from scripts.benchmarks.render import (
    Align,
    Unit,
    fmt_int,
    fmt_value,
    markdown_table,
)
```

**Module-level constants** (`chapter3.py` lines 81–93):
```python
SECTION = "SKILL.md §5 — flaw-delta zones (5.x: per-(ELO×TC) Q1/Q3 + collapse verdicts)"

# Chapter 5 specific: per-user min analyzed games floor (D-08, matches ENDGAME_MIN_GAMES)
FLAW_DELTA_MIN_GAMES: int = 20  # Per-user analyzed-games floor for flaw-delta metrics

# SQL rounding digits for delta metrics (per-100-moves, signed floats)
_DELTA_DIGITS: int = 4
```

**TypedDict pattern for return values** (`chapter3.py` lines 96–107):
```python
class MetricBlock(TypedDict):
    pooled: dist.Distribution
    elo_marginal: list[dist.Marginal]
    tc_marginal: list[dist.Marginal]
    verdicts: list[dist.Verdict]


class Chapter5Values(TypedDict):
    flaw_rate: MetricBlock
    low_clock: MetricBlock
    hasty: MetricBlock
    # ... one key per metric
    viability: list[dict[str, Any]]  # D-06 diagnostic
```

**`_fetch` helper** (`chapter3.py` lines 109–111):
```python
async def _fetch(session: AsyncSession, sql_text: str) -> Sequence[RowMapping]:
    result = await session.execute(text(sql_text))
    return result.mappings().all()
```

**Per-user CTE shape** (`chapter3.py` `_per_user_cte()` lines 114–145, adapted for chapter5):

The canonical pattern (shared base): every per-user CTE starts with `sql.SELECTED_USERS_CTE`, joins `games` + `selected_users`, filters with `sql.BASE_GAME_FILTER`, applies `sql.elo_bucket_case_sql("ueag")`, floors with `HAVING count(*) >= FLOOR`, and materializes with `sql.SPARSE_CELL_EXCLUSION`:

```python
def _per_user_cte() -> str:
    bucket_case = sql.elo_bucket_case_sql("ueag")
    return (
        f"WITH {sql.SELECTED_USERS_CTE},\n"
        # chapter5-specific: adds base_games, user_moves_per_game, per_game_tags,
        # per_game_delta CTEs before per_user
        "...\n"
        "per_user AS (\n"
        f"  SELECT user_id, ({bucket_case}) AS elo_bucket, tc,\n"
        "         avg(d_flaw_rate) AS delta_flaw_rate,\n"
        "         -- ... avg of all 15 delta columns\n"
        f"  FROM per_game_delta WHERE ueag >= {sql.ELO_FLOOR}\n"
        "  GROUP BY user_id, elo_bucket, tc\n"
        f"  HAVING count(*) >= {FLAW_DELTA_MIN_GAMES}\n"
        "),\n"
        "pu AS MATERIALIZED (\n"
        f"  SELECT * FROM per_user WHERE {sql.SPARSE_CELL_EXCLUSION}\n"
        ")"
    )
```

**`BASE_GAME_FILTER` content** (`sql.py` lines 350–356) — includes equal-footing + rated + TC:
```python
BASE_GAME_FILTER: str = (
    "g.rated AND NOT g.is_computer_game\n"
    "    AND g.time_control_bucket::text = su.tc_bucket\n"
    "    AND g.white_rating IS NOT NULL AND g.black_rating IS NOT NULL\n"
    f"    AND {EQUAL_FOOTING_FILTER}"
)
```
Chapter5 must also add `AND g.evals_completed_at IS NOT NULL` (only analyzed games have flaws).

**Move-count denominator CTE** (derived from RESEARCH.md Q1 + `query_utils.py` ply-parity convention):
```sql
-- user_moves_per_game: count game_positions plies where mover = user (ply >= 1)
user_moves_per_game AS (
  SELECT gp.game_id, COUNT(*) AS user_moves
  FROM game_positions gp
  JOIN base_games bg ON bg.game_id = gp.game_id
  WHERE gp.ply >= 1
    AND (
      (gp.ply % 2 = 0 AND bg.user_color = 'white') OR  -- even ply = white mover
      (gp.ply % 2 = 1 AND bg.user_color = 'black')     -- odd ply = black mover
    )
  GROUP BY gp.game_id
)
```
**Critical**: even ply = white mover, odd ply = black mover. This mirrors `is_opponent_expr` in `query_utils.py` (Phase 113 D-01). The inverse (opponent moves) flips `white`/`black`.

**Player/opponent tag count split** (from `query_utils.py` `is_opponent_expr` pattern):
```sql
-- Player flaws: NOT is_opponent (player mover parity matches user_color)
COUNT(*) FILTER(WHERE
  (gf.ply % 2 = 0 AND bg.user_color = 'white') OR
  (gf.ply % 2 = 1 AND bg.user_color = 'black')
) AS p_flaw_rate,

-- Opponent flaws: is_opponent (mover parity is the OTHER color)
COUNT(*) FILTER(WHERE
  (gf.ply % 2 = 0 AND bg.user_color = 'black') OR
  (gf.ply % 2 = 1 AND bg.user_color = 'white')
) AS o_flaw_rate
```

**`compute()` function shape** (multi-metric UNION ALL, `chapter3.py` lines 156–174):
```python
async def compute(session: AsyncSession) -> Chapter5Values:
    # Build 15 metric select blocks via UNION ALL from shared pu CTE
    # OR run separate per-metric queries — one per metric with a 'metric' tag column
    selects = [
        f"SELECT '{metric}' AS metric,\n{dist.agg_select(col, digits=_DELTA_DIGITS)}\n"
        f"FROM pu {dist.GROUPING_SETS}"
        for metric, col in _FLAW_DELTA_METRICS
    ]
    query = _per_user_cte() + "\n" + "\nUNION ALL\n".join(selects)
    rows = await _fetch(session, query)

    blocks: dict[str, MetricBlock] = {}
    for metric, _ in _FLAW_DELTA_METRICS:
        metric_rows = [r for r in rows if r["metric"] == metric]
        pooled, elo, tc = dist.split_grouping_sets(metric_rows)
        blocks[metric] = MetricBlock(
            pooled=pooled,
            elo_marginal=elo,
            tc_marginal=tc,
            verdicts=[dist.verdict("TC", tc), dist.verdict("ELO", elo)],
        )
    # Also run viability diagnostic query separately (D-06)
    viability = await _compute_viability(session)
    return Chapter5Values(**blocks, viability=viability)  # type: ignore[arg-type]
```

**`dist.agg_select` call** (`chapter3.py` lines 216–218):
```python
dist.agg_select("delta_flaw_rate", digits=_DELTA_DIGITS)
```
This emits: `elo_bucket, tc, count(*) AS n, round(avg(...)::numeric, 4) AS mean, avg(...) AS mean_raw, round(stddev_samp(...)::numeric, 4) AS sd, var_samp(...) AS var, round(percentile_cont(0.05) ... AS p05, ... AS p25, ... AS p50, ... AS p75, ... AS p95`.

**`dist.split_grouping_sets` + `dist.verdict` call** (`chapter3.py` lines 167–173):
```python
pooled, elo, tc = dist.split_grouping_sets(metric_rows)
blocks[metric] = MetricBlock(
    pooled=pooled,
    elo_marginal=elo,
    tc_marginal=tc,
    verdicts=[dist.verdict("TC", tc), dist.verdict("ELO", elo)],
)
```

**`render()` + `build()` shape** (`chapter3.py` lines 636–698):
```python
def render(values: Chapter5Values) -> str:
    parts = ["## 5. Flaw-Delta Zones", "", "### 5.1 Per-Metric Flaw-Delta Q1/Q3", ""]
    for metric, col in _FLAW_DELTA_METRICS:
        block = values[metric]
        parts += _metric_section(
            f"#### 5.x {metric} (per-user you−opponent delta, per 100 moves)",
            block, "pp",
            pooled_label="Pooled distribution",
        )
        parts += ["", "---", ""]
    # viability table
    parts += _render_viability(values["viability"])
    return "\n".join(parts)


async def build(session: AsyncSession) -> dict[str, Any]:
    values = await compute(session)
    return {
        "status": "OK",
        "section": SECTION,
        "values": values,
        "markdown": render(values),
    }
```

**`_metric_section` render helper** (`chapter3.py` lines 562–581):
```python
def _metric_section(
    title: str, block: MetricBlock, unit: dist.Unit, *, pooled_label: str
) -> list[str]:
    return [
        title,
        "",
        f"##### {pooled_label}",
        "",
        dist.pooled_table(block["pooled"], unit),
        "",
        "##### ELO marginal",
        "",
        dist.marginal_table("ELO", block["elo_marginal"], unit),
        "",
        "##### TC marginal",
        "",
        dist.marginal_table("TC", block["tc_marginal"], unit),
        "",
        dist.verdict_block(block["verdicts"]),
    ]
```

**Shared render helpers** (`distribution.py` lines 182–198):
```python
dist.pooled_table(block["pooled"], unit)           # single-row table
dist.marginal_table("ELO", block["elo_marginal"], unit)   # multi-row table
dist.verdict_block(block["verdicts"])              # "#### Collapse verdict" block
```

---

### `scripts/gen_benchmarks.py` (MODIFY — registration seam)

**Registration location** (`gen_benchmarks.py` lines 140–168):

The two insertion points are `CHAPTER_STUBS` (lines 140–151) and `_CHAPTER_BUILDERS` (lines 158–168).

**`CHAPTER_STUBS` tuple** (lines 140–151) — insert new entry AFTER `"3.4-endgame-type"`, BEFORE `"4-global-percentile-cdf"`:
```python
CHAPTER_STUBS: tuple[tuple[str, str], ...] = (
    ("1-stratified-sample", "SKILL.md §1 — ..."),
    ("2.1-openings-middlegame-eval", "SKILL.md §2.1 — ..."),
    ("3.1-endgame-overall", "SKILL.md §3.1 — ..."),
    ("3.2-endgame-metrics-elo", "SKILL.md §3.2 — ..."),
    ("3.3-time-pressure", "SKILL.md §3.3 — ..."),
    ("3.4-endgame-type", "SKILL.md §3.4 — ..."),
    # INSERT HERE:
    ("5-flaw-delta-zones", "SKILL.md §5 — flaw-delta per-(ELO×TC) Q1/Q3 zones + collapse verdicts"),
    ("4-global-percentile-cdf", "SKILL.md §4 — ..."),
)
```

**`_CHAPTER_BUILDERS` dict** (lines 158–168) — add entry alongside chapter3:
```python
_CHAPTER_BUILDERS: dict[str, Callable[[AsyncSession], Awaitable[dict[str, Any]]]] = {
    "1-stratified-sample": chapter1.build,
    "2.1-openings-middlegame-eval": chapter2.build,
    "3.1-endgame-overall": chapter3.build,
    "3.2-endgame-metrics-elo": chapter3.build_32,
    "3.3-time-pressure": chapter3_3.build,
    "3.4-endgame-type": chapter3_4.build,
    "5-flaw-delta-zones": chapter5.build,   # ADD THIS
    "4-global-percentile-cdf": chapter4.build,
}
```

**Import addition** (lines 72–79):
```python
from scripts.benchmarks import (  # noqa: E402
    chapter1,
    chapter2,
    chapter3,
    chapter3_3,
    chapter3_4,
    chapter4,
    chapter5,   # ADD THIS
)
```

---

### `tests/scripts/benchmarks/test_chapter5_diff.py` (NEW — numeric diff gate)

**Analog:** `tests/scripts/benchmarks/test_chapter3_diff.py`

**File header + imports** (`test_chapter3_diff.py` lines 1–24):
```python
"""Numeric acceptance gate for Chapter 5 / §5 (flaw-delta zones).

Runs the chapter5 compute() against the live benchmark DB and asserts pooled +
ELO + TC marginals and Cohen's d verdicts for all 15 metrics. Skips when the
benchmark DB is unreachable. `benchmark_session` is from conftest.py.

Values are populated after the first successful generator run and committed.
"""

from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from scripts.benchmarks import chapter5

pytestmark = pytest.mark.asyncio
```

**Expected-value dict shape per metric** (`test_chapter3_diff.py` lines 26–49):
```python
EXPECTED_FLAW_RATE_POOLED = {
    "n": ...,
    "mean": ...,   # float, 4 dp
    "sd": ...,
    "p05": ...,
    "p25": ...,
    "p50": ...,
    "p75": ...,
    "p95": ...,
}
# label -> (n, mean, sd, p25, p50, p75)
EXPECTED_FLAW_RATE_ELO = {
    "800": (..., ..., ..., ..., ..., ...),
    "1200": (...),
    "1600": (...),
    "2000": (...),
    "2400": (...),
}
EXPECTED_FLAW_RATE_TC = {
    "bullet": (...),
    "blitz": (...),
    "rapid": (...),
    "classical": (...),
}
```

**Verdict expected dict shape** (`test_chapter3_diff.py` lines 76–79):
```python
EXPECTED_VERDICTS = {
    "flaw_rate": {"TC": (("bullet", "classical"), 0.xx), "ELO": (("800", "2400"), 0.xx)},
    "hasty": {"TC": ((...), 0.xx), "ELO": ((...), 0.xx)},
    # ... one entry per metric
}
```

**Check helper functions** (`test_chapter3_diff.py` lines 82–104) — copy verbatim:
```python
def _check_pooled(block, expected: dict) -> None:
    pooled = block["pooled"]
    assert pooled["n"] == expected["n"]
    for key in ("mean", "sd", "p05", "p25", "p50", "p75", "p95"):
        assert pooled[key] == pytest.approx(expected[key]), key


def _check_marginal(marginals, expected: dict) -> None:
    by_label = {m["label"]: m for m in marginals}
    assert set(by_label) == set(expected)
    for label, (n, mean, sd, p25, p50, p75) in expected.items():
        d = by_label[label]["dist"]
        assert d["n"] == n, label
        assert d["mean"] == pytest.approx(mean), label
        assert d["sd"] == pytest.approx(sd), label
        assert (d["p25"], d["p50"], d["p75"]) == pytest.approx((p25, p50, p75)), label


def _check_verdicts(block, expected: dict) -> None:
    by_axis = {v["axis"]: v for v in block["verdicts"]}
    for axis, (pair, d) in expected.items():
        assert by_axis[axis]["pair"] == pair, axis
        assert round(by_axis[axis]["max_abs_d"], 2) == d, axis
```

**Test function shape** (`test_chapter3_diff.py` lines 107–118):
```python
async def test_chapter5_flaw_delta(benchmark_session: AsyncSession) -> None:
    values = await chapter5.compute(benchmark_session)

    _check_pooled(values["flaw_rate"], EXPECTED_FLAW_RATE_POOLED)
    _check_marginal(values["flaw_rate"]["elo_marginal"], EXPECTED_FLAW_RATE_ELO)
    _check_marginal(values["flaw_rate"]["tc_marginal"], EXPECTED_FLAW_RATE_TC)
    _check_verdicts(values["flaw_rate"], EXPECTED_VERDICTS["flaw_rate"])
    # ... repeated for all 15 metrics
```

**`benchmark_session` fixture** — provided by `tests/scripts/benchmarks/conftest.py` (no changes needed). It calls `gen_benchmarks._db_url("benchmark")`, creates a read-only session, and skips if the benchmark DB is unreachable.

---

## Shared Patterns

### Distribution aggregation call (apply to all 15 metrics in chapter5)

**Source:** `scripts/benchmarks/distribution.py` lines 57–80 (`agg_select`)
**Apply to:** Every `SELECT` block in chapter5's UNION ALL
```python
# agg_select emits: elo_bucket, tc, n, mean (rounded), mean_raw, sd, var, p05..p95
dist.agg_select("delta_flaw_rate", digits=4)   # 4dp for per-100-moves delta metrics
# Pair with:
dist.GROUPING_SETS  # = "GROUP BY GROUPING SETS ((), (elo_bucket), (tc))"
```

### GROUPING SETS row classification (apply to every compute block)

**Source:** `scripts/benchmarks/distribution.py` lines 125–155 (`split_grouping_sets`)
**Apply to:** Every metric's row classification in chapter5
```python
pooled, elo, tc = dist.split_grouping_sets(metric_rows)
# pooled = all-NULL row; elo rows have elo_bucket set; tc rows have tc set
# elo sorted ascending; tc sorted by sql.TC_ORDER = ("bullet","blitz","rapid","classical")
```

### Cohen's-d collapse verdict (apply to all 15 metrics, both axes)

**Source:** `scripts/benchmarks/distribution.py` lines 158–163 (`verdict`)
**Apply to:** Every `MetricBlock` constructed in chapter5
```python
verdicts=[dist.verdict("TC", tc), dist.verdict("ELO", elo)]
# Internally calls stats.max_abs_d() over marginal LevelStat objects
# Thresholds (code emits d-value only; SKILL.md applies words):
#   < 0.2  → collapse    0.2–0.5 → review    >= 0.5 → keep separate
```

### Sparse-cell exclusion (apply in `pu AS MATERIALIZED` CTE)

**Source:** `scripts/benchmarks/sql.py` line 36
**Apply to:** The `pu AS MATERIALIZED` CTE in `_per_user_cte()`
```python
sql.SPARSE_CELL_EXCLUSION  # = "NOT (elo_bucket = 2400 AND tc = 'classical')"
```

### Selected-users cohort filter (mandatory, apply at top of every CTE chain)

**Source:** `scripts/benchmarks/sql.py` lines 335–346
**Apply to:** Start of every CTE in chapter5
```python
sql.SELECTED_USERS_CTE
# Includes: benchmark_selected_users JOIN benchmark_ingest_checkpoints (bic.status='completed')
# JOIN users — this is the mandatory cohort filter
```

### Game-time ELO bucketing (apply in per_user CTE)

**Source:** `scripts/benchmarks/sql.py` lines 303–314 + 319–321
**Apply to:** The `elo_bucket` derivation in per_user CTE
```python
bucket_case = sql.elo_bucket_case_sql(sql.USER_ELO_AT_GAME_SQL)
# USER_ELO_AT_GAME_SQL = "CASE WHEN g.user_color::text = 'white' THEN g.white_rating ELSE g.black_rating END"
# Results in CASE WHEN ... < 800 THEN NULL WHEN ... < 1200 THEN 800 ... ELSE 2400 END
```

### Ply-parity player/opponent convention (load-bearing for all flaw-delta SQL)

**Source:** `app/repositories/query_utils.py` `is_opponent_expr` (Phase 113) + confirmed in RESEARCH.md
**Apply to:** `user_moves_per_game` CTE and `per_game_tags` FILTER conditions
```
Even ply (0, 2, 4, ...) = WHITE mover
Odd ply  (1, 3, 5, ...) = BLACK mover

Player moves:  (ply % 2 = 0 AND user_color = 'white') OR (ply % 2 = 1 AND user_color = 'black')
Opponent moves:(ply % 2 = 0 AND user_color = 'black') OR (ply % 2 = 1 AND user_color = 'white')
```
**Never flip these.** A prior off-by-one bug lived here (Phase 113 D-01).

### Tag column encoding (apply in `per_game_tags` FILTER conditions)

**Source:** `app/repositories/game_flaws_repository.py` `_TEMPO_INT`, `_PHASE_INT`
**Apply to:** All flaw-count FILTER predicates in chapter5's SQL

| Metric | Column | Predicate |
|--------|--------|-----------|
| Flaw Rate | any row | `TRUE` (all game_flaws rows are M+B flaws) |
| low-clock | `tempo` | `tempo = 0` |
| hasty | `tempo` | `tempo = 1` |
| unrushed | `tempo` | `tempo = 2` |
| opening | `phase` | `phase = 0` |
| middlegame | `phase` | `phase = 1` |
| endgame | `phase` | `phase = 2` |
| miss | `is_miss` | `is_miss = TRUE` |
| lucky | `is_lucky` | `is_lucky = TRUE` |
| reversed | `is_reversed` | `is_reversed = TRUE` |
| squandered | `is_squandered` | `is_squandered = TRUE` |
| hasty+miss | `tempo`, `is_miss` | `tempo = 1 AND is_miss = TRUE` |
| low-clock+miss | `tempo`, `is_miss` | `tempo = 0 AND is_miss = TRUE` |

These are integer/boolean column filters; tag name strings do NOT appear in benchmark SQL.

### Artifact `build()` return contract (apply to chapter5.build)

**Source:** `scripts/benchmarks/chapter3.py` lines 683–698
**Apply to:** `chapter5.build()`
```python
async def build(session: AsyncSession) -> dict[str, Any]:
    values = await compute(session)
    return {
        "status": "OK",
        "section": SECTION,
        "values": values,
        "markdown": render(values),
    }
```
The `"status": "OK"` key is checked by `gen_benchmarks._generate_chapters` before writing the artifact.

---

## No Analog Found

All files have close analogs in the codebase. No files fall into this category.

---

## Metadata

**Analog search scope:** `scripts/benchmarks/`, `scripts/gen_benchmarks.py`, `tests/scripts/benchmarks/`
**Files read:** `chapter3.py` (845 lines), `gen_benchmarks.py` (318 lines), `distribution.py` (199 lines), `sql.py` (357 lines), `stats.py` (93 lines), `render.py` (105 lines), `test_chapter3_diff.py` (562 lines), `conftest.py` (40 lines)
**Pattern extraction date:** 2026-06-10
