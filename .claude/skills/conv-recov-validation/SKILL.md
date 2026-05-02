---
name: conv-recov-validation
description: Generate a validation report for the FlawChess conversion/recovery threshold and persistence configuration (currently t=100 centipawns + 4-ply persistence) against Stockfish engine evaluation as ground truth. Uses the benchmark DB (Lichess sample with `eval_cp` annotations) to validate that the material-imbalance proxy tracks engine eval with a consistent, predictable offset, and that 4-ply persistence closes a meaningful fraction of the gap to Stockfish. Use this skill whenever the user asks about validating the conversion/recovery thresholds, validating the 4-ply persistence rule, comparing material imbalance vs Stockfish eval, "is t=100 still the right threshold", "does persistence actually help", "how close is our proxy to engine ground truth", or wants an updated version of `endgame-conversion-recovery-analysis.md`. Trigger on phrases like "conv/recov validation", "conversion recovery validation", "validate threshold", "validate persistence", "material vs stockfish", "material vs eval", "proxy validation", "100 centipawn threshold", "4-ply persistence", "endgame threshold report", "engine eval validation". Writes a timestamped markdown report to reports/conv-recov-validation-YYYY-MM-DD.md.
---

# Conversion / Recovery Validation

Validate that the **t=100 centipawn + 4-ply persistence** rule for conversion/recovery classification (live in `_compute_score_gap_material` / `_endgame_skill_from_bucket_rows`) is still the right call, and quantify how close the material-imbalance proxy lands to Stockfish engine evaluation as ground truth.

The legacy version of this report (`reports/endgame-conversion-recovery-analysis.md`, 2026-04-07) ran on the **prod DB** (~180k games, 14.7% Lichess eval coverage, 0% chess.com) and was right on the headline call but small-sampled on the Stockfish head-to-head (queen 28 games, pawn 109 games). This skill rebuilds the analysis on the **benchmark DB** — Lichess-only by construction with much denser eval coverage — applying the canonical cell-anchoring methodology from the `benchmarks` skill so the numbers are robust enough to commit to long-term.

## What this skill does NOT cover

- **5-ply / 6-ply persistence comparison.** Settled in the original report (≤1pp shift, 2–3% sample loss). Not worth re-running.
- **Re-deriving the threshold itself.** t=100 was chosen for coverage, not from a continuous sweep. This skill validates it; it does not propose t=50 or t=150.
- **Gauge zone re-calibration as a primary deliverable.** The `benchmarks` skill is the canonical source for gauge zones (Section 2). This skill includes a *quick* per-user distribution at t=100 + 4-ply for context, but defers full zone calibration to the benchmarks report.

## Target

- **Benchmark DB only** (`mcp__flawchess-benchmark-db__query`). Validation against Stockfish only makes sense on a population with eval coverage; the prod DB no longer has enough.
- Benchmark DB runs in Docker on `localhost:5433`. If `docker compose -p flawchess-benchmark ps` shows nothing, run `bin/benchmark_db.sh start` first.
- Each MCP call runs one statement (no `;`-separated multi-statement).

## Methodology lifted from the `benchmarks` skill

Read `.claude/skills/benchmarks/SKILL.md` if you need the full justification for any of these — they exist to keep population stats honest.

### Canonical `selected_users` CTE — non-optional

Every query starts with this CTE. The `bic.status='completed'` filter is mandatory — `benchmark_selected_users` is the candidate *pool*, not the ingested set, and skipping the filter pulls in zero-game users that drag medians to nonsense.

```sql
WITH selected_users AS (
  SELECT u.id AS user_id, bsu.rating_bucket, bsu.tc_bucket
  FROM benchmark_selected_users bsu
  JOIN benchmark_ingest_checkpoints bic
    ON bic.lichess_username = bsu.lichess_username
   AND bic.tc_bucket = bsu.tc_bucket
   AND bic.status = 'completed'
  JOIN users u ON u.lichess_username = bsu.lichess_username
)
```

Then JOIN `selected_users su ON su.user_id = g.user_id` and filter `g.time_control_bucket::text = su.tc_bucket`. The `::text` cast is required because `games.time_control_bucket` is the `timecontrolbucket` enum and `bsu.tc_bucket` is `varchar`.

### Sparse-cell exclusion

The `(rating_bucket=2400, tc_bucket='classical')` cell is structurally undersampled (~12 completed users, ~55 games/user) and **must be excluded from every aggregation in this report** — pooled overall, marginals, head-to-head, gap closure, and per-user distribution. Apply at the `selected_users` JOIN:

```sql
WHERE NOT (su.rating_bucket = 2400 AND su.tc_bucket = 'classical')
```

This skill operates almost entirely on pooled/per-class numbers (not per-cell), so the exclusion lives in the WHERE clause of the outer query rather than the marginal aggregation step. Cell-level breakouts (if any) keep the cell with an `n=12*` footnote — but most sections here are pooled by design, since the question is "does the proxy track eval", not "does it track eval differently per cohort".

### Base game filters

Every query: `g.rated AND NOT g.is_computer_game`. Do not apply `opponent_strength` or `recency` filters — population stats are unconstrained by per-user UI filters.

### Per-class `class_span` building block

Each `(game_id, endgame_class)` span ≥6 plies contributes one row. A single game traversing queen→rook contributes once to each, mirroring the live Endgame Categories convention.

```sql
class_span AS (
  SELECT game_id, endgame_class, min(ply) AS entry_ply
  FROM game_positions
  WHERE endgame_class IS NOT NULL
  GROUP BY game_id, endgame_class
  HAVING count(*) >= 6
)
```

The whole-game (first-endgame-only) version used by the live conv/par/recov gauge is also valid; for this validation we use per-class spans because the Stockfish comparison is a per-class question.

### Persistence approximation

The 4-ply persistence rule in this skill checks `position at entry_ply + 4` directly (same `endgame_class`), as in the old report and the benchmarks skill. The live backend uses an `array_agg` + contiguity check that is slightly stricter — small systematic difference that doesn't move the headline numbers. Surface this caveat in the report header.

### Eval columns

`game_positions.eval_cp` (smallint) is the centipawn evaluation from Lichess `%eval` PGN annotations, white-perspective. Apply `eval_cp * color_sign` to convert to user-perspective like material. `eval_mate` (smallint) is plies-to-mate; treat it as a "huge" eval but for this report we filter on `eval_cp IS NOT NULL` and rely on cp values directly. Mate-only positions are a small minority (~1M out of 30M endgame positions) and generally already covered by the cp value when both are present.

## Live-threshold grep

Before running, grep the constants the report's headline number lands against. Record the literal values in a "Currently set in code" subsection so the verdict compares proposals against live values, not memory.

| Constant | File | Section the validation answers |
|---|---|---|
| `_MATERIAL_ADVANTAGE_THRESHOLD` (= 100) | `app/services/endgame_service.py` | Section 1, 3 |
| persistence ply (= 4) | same file (search for `+ 4` near material check) | Sections 1–4 |
| `ENDGAME_PLY_THRESHOLD` (= 6) | same file | Setup |

Use the Grep tool, not bash. Record the literal values so a reader six months from now can sanity-check the "currently set" column without rebuilding context.

## Shared SQL building block — `entries`

The whole report runs off one shared CTE, then filters/aggregates differently per section. Build it once, reuse everywhere:

```sql
WITH selected_users AS (
  SELECT u.id AS user_id, bsu.rating_bucket, bsu.tc_bucket
  FROM benchmark_selected_users bsu
  JOIN benchmark_ingest_checkpoints bic
    ON bic.lichess_username = bsu.lichess_username
   AND bic.tc_bucket = bsu.tc_bucket
   AND bic.status = 'completed'
  JOIN users u ON u.lichess_username = bsu.lichess_username
),
class_span AS (
  SELECT game_id, endgame_class, min(ply) AS entry_ply
  FROM game_positions
  WHERE endgame_class IS NOT NULL
  GROUP BY game_id, endgame_class HAVING count(*) >= 6
),
entries AS (
  SELECT
    g.id AS game_id, g.user_id,
    su.rating_bucket AS elo_bucket, su.tc_bucket AS tc,
    cs.endgame_class,
    CASE
      WHEN (g.result='1-0' AND g.user_color='white')
        OR (g.result='0-1' AND g.user_color='black') THEN 1.0
      WHEN g.result='1/2-1/2' THEN 0.5 ELSE 0.0
    END AS score,
    CASE WHEN g.user_color='white' THEN 1 ELSE -1 END AS color_sign,
    ep.material_imbalance AS entry_imb,
    ep.eval_cp           AS entry_eval,
    ap.material_imbalance AS after_imb,
    ap.eval_cp           AS after_eval
  FROM games g
  JOIN selected_users su ON su.user_id = g.user_id
  JOIN class_span cs     ON cs.game_id = g.id
  JOIN game_positions ep ON ep.game_id = g.id AND ep.ply = cs.entry_ply
  LEFT JOIN game_positions ap
    ON ap.game_id = g.id AND ap.ply = cs.entry_ply + 4
   AND ap.endgame_class = cs.endgame_class
  WHERE g.rated AND NOT g.is_computer_game
    AND g.time_control_bucket::text = su.tc_bucket
    AND NOT (su.rating_bucket = 2400 AND su.tc_bucket = 'classical')
)
```

Each section below is a `WITH selected_users AS (...), class_span AS (...), entries AS (...) SELECT ... FROM entries ...` query — the differences are in the SELECT clause and FILTER predicates, not the CTE backbone.

The user-perspective threshold checks are:

- **Conversion (advantage):** `entry_imb * color_sign >= 100`
- **Recovery (disadvantage):** `entry_imb * color_sign <= -100`
- **Persistence at +4 plies:** AND `after_imb * color_sign >= 100` (or `<= -100`)
- **Eval-based equivalent:** swap `entry_imb` → `entry_eval`. Eval naturally handles transient imbalances, so `u=100` is intentionally specified without persistence — that's the point of the comparison.

For the **conversion outcome rate**: `avg(CASE WHEN score=1.0 THEN 1.0 ELSE 0.0 END)` (Win %).
For the **recovery outcome rate**: `avg(CASE WHEN score>=0.5 THEN 1.0 ELSE 0.0 END)` (Save %, win-or-draw).

These mirror `_endgame_skill_from_bucket_rows`.

## Section 1 — Eval coverage on benchmark DB

**Question:** What fraction of qualifying endgame positions have Stockfish evals on the benchmark DB? This sets the size of the head-to-head subset and lets the reader judge whether Section 3's verdict is well-powered.

Report:
- Total endgame games (per-class spans, ≥6 plies, after sparse-cell exclusion).
- Positions with `entry_eval IS NOT NULL`.
- Positions with both `entry_eval IS NOT NULL AND after_eval IS NOT NULL` (the head-to-head subset).
- Coverage % overall and per endgame class.

This replaces the old report's "Data Availability" table (which compared chess.com to Lichess). On the benchmark DB the answer is "Lichess by construction; coverage ~20–25% of endgame positions, much higher than prod".

## Section 2 — Material threshold comparison (full benchmark dataset)

Mirrors the old report's Section 1 but on the benchmark DB. Drop the persistence-window comparison entirely (the old Section 2) — the user explicitly said no need to re-run 5/6-ply.

For each endgame class, compute Win % (conversion) and Save % (recovery) for these four configs:

| Config | Predicate at entry | Predicate at entry+4 |
|---|---|---|
| Baseline (equal) | within ±100 (i.e. NOT advantage AND NOT disadvantage) | none |
| t=300, no persist | `\|imb*sign\| >= 300` | none |
| t=300 + 4-ply | same as above | AND `\|after_imb*sign\| >= 300` |
| **t=100 + 4-ply (live)** | `\|imb*sign\| >= 100` | AND `\|after_imb*sign\| >= 100` |

Output two tables per metric (conversion and recovery): rate-table and sample-size table, columns by endgame class. Bold the live row.

For per-user coverage (the old report's "users with ≥20 games in category" table), use the canonical CTE — count distinct users where each user has ≥20 games meeting the predicate **in their selected TC**. Reproduce only the t=100 + 4-ply column; the t=300 column is historical. Population should easily clear ≥10 users/cell after the threshold drop, so include a one-row "users with ≥20 games (any cell)" summary per class plus a short note on how this ladders up to the benchmarks-skill cell-floor expectations.

The headline finding from the old report — **the t=100 threshold roughly 6×s the pawn-endgame conversion sample and triples actionable per-user coverage** — should re-derive here on the bigger dataset. State the multiplier explicitly.

## Section 3 — Stockfish head-to-head (eval-available subset)

This is the centerpiece. **Filter the `entries` CTE to rows where `entry_eval IS NOT NULL AND after_eval IS NOT NULL`** so material-vs-eval is compared on the same population.

Per endgame class, output:

```
| Type | t=100 + 4-ply (material)  | u=100 (eval, no persist)  | Delta |
|------|---------------------------|---------------------------|-------|
| rook | <rate> (n=<count>)        | <rate> (n=<count>)        | <pp>  |
...
```

Two tables: conversion (Win %) and recovery (Save %).

The expected pattern from the old report (which the benchmark DB will reproduce with much narrower CIs):

- **Conversion gap is positive** — eval is higher than material. Eval correctly excludes positions where the user has +1 pawn but is in fact losing (bad structure, no activity, exposed king).
- **Recovery gap is negative** — eval is lower than material. Eval correctly excludes positions where the user is down material but has positional compensation (passed pawn, active pieces).

Both signs going the same direction across classes is the **systematic offset** finding — frame it as "the proxy passes validation if the offset is consistent and predictable, even if not zero". A *random* offset would invalidate the proxy; a systematic one preserves relative rankings between endgame types and trends over time, which is what the gauges actually need.

## Section 4 — Eval agreement with material imbalance

For positions where material says the user is disadvantaged (`entry_imb * color_sign <= -100`) **and** `entry_eval IS NOT NULL`:

| Endgame Class | Games | Eval agrees (≤ -100) | Avg eval_cp | Avg material_imb | Eval flips sign |

- "Eval agrees" = `entry_eval * color_sign <= -100`. High agreement (>70%) means material is a faithful proxy *for that class*.
- "Avg eval_cp" and "Avg material_imb" are signed (user-perspective). Eval is typically more amplified in pawn endgames (down-1-pawn → losing) and more compressed in mixed.
- "Eval flips sign" = `entry_eval * color_sign > 0`. The fraction of "material disadvantage" entries that engine eval reads as winning.

Repeat the same table for the conversion side (`entry_imb * color_sign >= 100`), reporting how often eval agrees the user is winning.

The old report only included the disadvantage side; including both sides here gives a symmetric view of the proxy's noise.

## Section 5 — Persistence gap closure vs Stockfish

This makes the value of 4-ply persistence concrete. On the eval-available subset, compare three configurations per endgame class:

| Type | t=100 no-persist | t=100 + 4-ply | u=100 (gold std) | Gap w/o p | Gap w/ p | % gap closed |
|------|------------------|---------------|------------------|-----------|----------|--------------|

`% gap closed = (gap_w/o_p − gap_w/_p) / gap_w/o_p`. Compute separately for conversion and recovery.

Headline framing from the old report worth reproducing:

> Persistence closes 50–70% of the gap to Stockfish for pawn and mixed endgames — the two highest-volume categories. The effect is strongest where it should be: pawn endgames (transient capture spikes during pawn trades) and mixed endgames (complex trades create frequent transient imbalances). Recovery benefits more than conversion because transient material spikes disproportionately inflate the recovery pool — a momentary capture briefly makes the user "down material" before the recapture.

If the benchmark-DB numbers contradict this framing on any class, *do not* paper over it — re-state the new pattern. The bigger sample may show e.g. that queen-recovery persistence does or doesn't help where the old 28-sample answer was statistical noise.

## Section 6 — Decision

State the verdict explicitly. Default text (adapt to the actual numbers):

> **Selected configuration: t=100 + 4-ply persistence (material imbalance). Validated against the benchmark DB.**

Rationale checklist (one sentence each, with numbers):

1. **Coverage** — works for 100% of imported games regardless of platform; eval covers only the X% of Lichess games with `%eval` annotations and 0% of chess.com.
2. **Sample size** — N pawn-conv games, N pawn-recov games on the full benchmark population (orders of magnitude above the prod DB report).
3. **Signal quality** — conversion rates X–Ypp above the equal-material baseline; recovery rates X–Ypp below.
4. **Consistent offset vs ground truth** — gap to eval is Xpp for simpler endgames (rook/minor/pawn), wider for queen/mixed. Direction is the same across classes (the systematic-offset finding).
5. **Persistence pulls the proxy toward eval where it matters** — closes X% of the gap on pawn and mixed.

Trade-offs accepted (state explicitly so anyone challenging the choice has the explicit cost):

- Conversion rates run ~Xpp lower than a hypothetical engine-based metric.
- Recovery rates run ~Xpp higher.
- Mixed and queen have the weakest material-to-eval correlation but the largest sample sizes, so the noise averages out at the population level.

Future upgrade path: if FlawChess adds its own engine analysis at import, eval-based metrics become viable on 100% of games, the persistence filter becomes redundant, and the gauge offsets close. Until then, t=100 + 4-ply is the right call.

## Section 7 — Per-user distribution at t=100 + 4-ply (context only)

Quick per-user distribution to validate that the live gauge zones still differentiate at the benchmark scale. **This is not a gauge re-calibration** — that lives in the `benchmarks` skill (Section 2). Include here only because the old report did, and a reader validating the threshold will reasonably ask "and the gauges still work, right?".

For users with ≥20 endgame games in their selected TC (canonical CTE, sparse cell excluded), compute per-user conversion rate, recovery rate, and Endgame Skill = mean of non-empty bucket rates (`_endgame_skill_from_bucket_rows` semantics — equal-weighted mean of the buckets the user has data for, NOT 0.7·conv + 0.3·recov which the old report incorrectly stated).

Output a Min / P10 / P25 / Median / P75 / P90 / Max table per metric.

Compare median to the live gauge `warn/succ` boundary and state whether the median user lands near it (which is the calibration target). If median is far off-boundary — say ≥5pp — flag for the benchmarks skill to re-run the calibration. Do not propose new boundaries here.

## Report file layout

Write to `reports/conv-recov-validation-YYYY-MM-DD.md` (UTC date). Layout:

```markdown
# Conversion / Recovery Validation — <DATE>

- **DB**: benchmark (Docker on localhost:5433, flawchess_benchmark)
- **Snapshot taken**: <ISO timestamp>
- **Population**: <N_users> completed users / <N_games> rated non-computer games / <N_endgame_positions> endgame positions
- **Eval coverage at endgame entries**: <N_with_eval> / <N_total> (<pct>%)
- **Cell anchoring**: 400-wide ELO buckets via benchmark_selected_users.rating_bucket; tc_bucket from same table; per-user TC restricted to selected tc_bucket
- **Selection provenance**: 2026-03 Lichess monthly dump
- **Base filters**: g.rated AND NOT g.is_computer_game; per-user filter g.time_control_bucket = bsu.tc_bucket; benchmark_ingest_checkpoints.status = 'completed'
- **Sparse-cell exclusion**: `(2400, classical)` excluded from all aggregations
- **Persistence approximation**: SQL uses `entry_ply + 4` with same-class join; backend uses array_agg contiguity check (small systematic difference)
- **Currently set in code**: `_MATERIAL_ADVANTAGE_THRESHOLD` = 100, persistence = 4 plies, `ENDGAME_PLY_THRESHOLD` = 6 (per `app/services/endgame_service.py`)

## 1. Eval coverage on benchmark DB
... (positions with eval / total, per class)

## 2. Material threshold comparison (full benchmark dataset)
... (rate + sample tables for conv/recov, per class; per-user coverage)

## 3. Stockfish head-to-head (eval-available subset)
... (per-class material vs eval comparison; conversion + recovery)

## 4. Eval agreement with material imbalance
... (per-class agreement % and sign-flip rate, both directions)

## 5. Persistence gap closure vs Stockfish
... (per-class gap closed; conversion + recovery)

## 6. Decision
... (verdict, rationale checklist with numbers, trade-offs, future upgrade path)

## 7. Per-user distribution at t=100 + 4-ply (context only)
... (Min/P10/P25/Median/P75/P90/Max per metric, gauge alignment note)
```

## Re-running

If today's file already exists and the user asks for a section subset, replace only those sections; preserve the header. Always rebuild Section 6 from whatever sections are present so the verdict reflects the updated numbers, not stale ones.

If the user asks for a fresh snapshot, write to today's file; never mutate prior dates.

If the benchmark DB has been re-ingested with a denser eval coverage between runs, mention the changed coverage in the header so the reader knows why numbers shifted.

## Workflow

1. **Pre-flight**: confirm benchmark DB is up (`docker compose -p flawchess-benchmark ps`); start with `bin/benchmark_db.sh start` if needed.
2. **Live-threshold grep**: record current values of `_MATERIAL_ADVANTAGE_THRESHOLD`, the persistence ply, and `ENDGAME_PLY_THRESHOLD` from `app/services/endgame_service.py`.
3. **Run sections in order** (1 → 7). Each section is one or two MCP queries plus markdown formatting; don't batch into a single mega-query — keep results inspectable.
4. **Write the report file as you go** — append each section to `reports/conv-recov-validation-YYYY-MM-DD.md` so a partial failure leaves a partial-but-readable artifact.
5. **End with the decision** — Section 6 is the deliverable. If the numbers contradict the headline framing in any class, write the contradiction plainly. The point of a validation report is to surface bad news, not bury it.
