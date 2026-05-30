# SEED-029 Phase A — continuation handoff (2026-05-30)

Read this + `SEED-029-benchmarks-deterministic-rebuild.md` to continue the faithful port
of the `/benchmarks` report into the deterministic generator `scripts/gen_benchmarks.py`.
Work in this worktree (`feat/gen-benchmarks-port`), not the main checkout.

## The mandate (unchanged — from the seed)

Reproduce the EXISTING methodology in `.claude/skills/benchmarks/SKILL.md` verbatim. The
gate is a numeric diff: the generator's output must match `reports/benchmark/benchmarks-latest.md`
(2026-05-27 snapshot) within rounding for every metric, marginal, and d-value. Mismatches are
either port bugs you fix, or prior transcription errors you footnote — decide explicitly.
Do NOT add methodology changes (#4 ELO-correlation, #6 conditional-opportunity floors) — Phase B.
Code emits numbers; the SKILL.md LLM applies verdict words + narrates. Read-only against the
benchmark DB (localhost:5433; `bin/benchmark_db.sh start` if down).

## What's done (committed on this branch)

- `955c3f9f` §1 Stratified Sample — 4 tables (cohort coverage), exact match.
- `28dba510` §2.1 Middlegame-entry eval — two-pass (baseline + centered dist) + Cohen's d.
- `67a65ed9` §3.1.1 Non-EG Score + §3.1.6 EG Score Gap + the shared `distribution.py` machinery
  (chapter2 refactored onto it). 33 tests green.
- `fffcf6ef` §3.1.2 EG-entry eval — extracted the shared two-pass eval machinery into
  `entry_eval.py` (baseline + per_user_color_with(phase) + centered_expr + baseline_table),
  refactored chapter2 onto it, added `distribution.pooled_agg_select` for the uncentered
  pooled arm. §3.1.2 reproduces the report EXACTLY (pass 1, both pooled variants, all
  marginals on n/mean/SD, both verdicts TC 0.14 / ELO 0.11) — NO transcription errors.
- `80714151` §3.1.3 Achievable Score — standard MetricBlock (score unit), reuses
  `_metric_section`. Added shared `sql.ENTRY_ROWS_CTE` + `sql.expected_score_sql()` +
  `sql.USER_COLOR_SIGN_SQL` (the ROW_NUMBER first-endgame-ply CTE + Lichess sigmoid, both
  reused by §3.1.5). Reproduces the report EXACTLY (pooled, all marginals, both verdicts
  TC 0.12 / ELO 0.12 1600-vs-2400) — NO transcription errors.
- `63c5f44f` §3.1.4 Endgame Score — simplest MetricBlock (score unit, INNER JOIN
  endgame_game_ids + ≥20 floor + USER_SCORE_EXPR). Pooled + all marginals reproduce the
  report exactly. FOUND a pair-selection slip: ELO max |d| is (800, 2400) at 0.34694,
  not the report's (800, 2000) at 0.34679 — both round to 0.35 / review, magnitude +
  verdict unchanged (same class as §2.1). Footnoted in test + chapter3 docstring.
- (next commit) §3.1.5 Achievable Score Gap — MetricBlock (pp unit). d_i = USER_SCORE_EXPR
  − expected_score_sql() (reuses §3.1.3's entry_rows + sigmoid; mate INCLUDED). ≥20 non-null
  pairs floor. Pooled + all marginals reproduce the report exactly. FOUND a pair-selection
  slip: TC max |d| is (rapid, classical) at 0.134, NOT the report's labeled (bullet, rapid)
  which is only 0.08 — the report carried the right magnitude (0.13/collapse) on the wrong
  pair label. ELO (800, 2400) 0.34 matches. **§3.1 now COMPLETE (3.1.1–3.1.6).**

## Architecture (scripts/benchmarks/ subpackage; tests in tests/scripts/benchmarks/)

- `sql.py` — shared SQL building blocks + pure `elo_bucket()`. Constants: ELO_ANCHORS, TC_ORDER,
  SELECTED_USERS_CTE (canonical completed-checkpoint join), USER_ELO_AT_GAME_SQL,
  EQUAL_FOOTING_FILTER, BASE_GAME_FILTER, SPARSE_CELL_EXCLUSION, USER_SCORE_EXPR,
  ENDGAME_GAME_IDS_CTE, MIDDLEGAME_PHASE/ENDGAME_PHASE, EVAL_OUTLIER_TRIM_CP=2000,
  EVAL_CONFIDENCE_MIN_N=20, SCORE_GAP_MIN_GAMES=30, ENDGAME_MIN_GAMES=20, LICHESS_WIN_CHANCES_K.
- `stats.py` — pure Cohen's d: `cohens_d`, `max_abs_d` (LevelStat → DResult). Unit-tested.
- `distribution.py` — THE reusable per-user-metric engine. `agg_select(value, digits, mean_digits)`
  builds the canonical pooled+ELO+TC GROUPING SETS SELECT (SQL percentile_cont + var_samp);
  `pooled_agg_select(...)` is the ungrouped-pooled-only variant (elo_bucket/tc → NULL) for
  UNION'ing an extra pooled row (e.g. §3.1.2 uncentered) onto a GROUPING SETS arm;
  `split_grouping_sets(rows)` → (pooled Distribution, elo Marginals, tc Marginals);
  `verdict(axis, marginals)`; `pooled_table` / `marginal_table` / `verdict_block` render with a
  `Unit` ("cp" | "score" | "pp"). Use this for every per-user metric (§3.1.3/3.1.4/3.1.5, §3.2, §3.4).
- `entry_eval.py` — shared two-pass phase-entry-eval machinery (§2.1 phase=1, §3.1.2 phase=2):
  `baseline(session, phase)`, `per_user_color_with(phase)` (WITH clause through the canonical
  `per_user_color` CTE), `centered_expr(centering_cp)`, `baseline_table(b)`. Both chapter2 and
  chapter3 §3.1.2 build on it so the cohort/equal-footing/trim logic can't drift.
- `render.py` — `markdown_table`, `fmt_int` (commas ≥1000), `fmt_signed`/`fmt_unsigned` (U+2212
  minus, half-up), `fmt_value(v, unit, role, *, pooled)` (cp/score/pp display).
- `chapter1.py`, `chapter2.py`, `chapter3.py` — chapters; registered in gen_benchmarks._CHAPTER_BUILDERS.

## The cadence (one sub-metric at a time)

1. Read the SKILL.md section's SQL (it's the source of truth for query logic).
2. VERIFY against the live DB first via `mcp__flawchess-benchmark-db__query` — run the section's
   query and confirm it reproduces the report's numbers BEFORE writing code. This is where the
   port findings surface.
3. Build the chapter function using `distribution.agg_select` + `split_grouping_sets` + `verdict`
   + the shared tables. Most metrics only differ in their per-user CTE + value expr + Unit + floor.
4. Gate: add expected values to a `test_chapterN_diff.py` (assert pooled + marginals + verdicts);
   `uv run --active pytest tests/scripts/benchmarks/ -q` (the live-DB gates take ~3 min — they scan
   game_positions; they skip when the DB is down).
5. ruff format + ruff check + ty check (all must be clean). Then generate
   (`uv run python scripts/gen_benchmarks.py --db benchmark`) and eyeball the section markdown.
6. Commit per the per-section checkpoint pattern (user-approved).

## Gotchas / locked decisions (learned this session — don't relearn)

- **Sub-800 drop**: the inline §2.1/§3.1.x SQL computes elo_bucket with a NULL branch but OMITS the
  `WHERE user_elo_at_game >= 800` guard the building-block text mandates. The report was generated
  WITH the drop (ELO marginals sum to pooled n). ALWAYS apply it. (chapter3 does it in per_user.)
- **Checkpoint join**: the DB now has completed checkpoints for all 5 ELO buckets, so the canonical
  SELECTED_USERS_CTE is the only path — SKILL.md's "current-DB-state exception" (lower() join, no
  checkpoint) is obsolete. Footnote it in the SKILL.md rewrite.
- **SQL percentiles, Python Cohen's d**: keep percentile_cont/stddev_samp in SQL (faithful, zero
  interpolation drift); only the hand-computed Cohen's d moved to Python (stats.py).
- **Rounding**: cp metrics round mean to 2 dp in SQL then display half-up to 1 dp (so 3.65 → +3.7);
  pass `mean_digits=2, digits=1`. Proportion/pp metrics use `digits=4`, display ×100 half-up 1 dp.
  Negative sign is U+2212. Means at the .5 boundary may show ±1 ulp vs the report (within rounding).
- **§3.1 has NO 5×4 cell grid** (the report omits it for 3.1.x) — emit pooled + ELO + TC marginals
  + verdict only. Marginals: emit the FULL p05–p95 column set uniformly (the report trims p05/p95 on
  some marginals editorially; the generator's superset is fine — the gate asserts values, not the
  column subset). §3.2.1/§3.4 DO use the 5×4 cell grid — build it in distribution.py when you reach them.
- **Prior-report transcription errors found (all footnoted, verdict-neutral)**: §2.1 ELO d pair
  (800,1200)→(800,1600); §3.1.1 pooled SD 8.3%→8.8%; §3.1.6 pooled mean −0.9→−0.95 (rounding boundary);
  §3.1.4 ELO d pair (800,2000)→(800,2400) (0.34679 vs 0.34694, both →0.35/review);
  §3.1.5 TC d pair (bullet,rapid)→(rapid,classical) (report's labeled pair = 0.08, the true
  max 0.13 is rapid-vs-classical — right magnitude, wrong pair label; verdict collapse unchanged).
  §3.1.2 + §3.1.3 had NONE. Expect more — verify, don't assume the report is exact.

## Remaining work

- §3.2 Conv/Parity/Recovery (3.2.1) — multi-metric + composite Endgame Skill; uses the 5×4 cell grid.
- §3.3 Time Pressure (3.3.x); §3.4 Endgame Type per-class (3.4.x) — partitioned per class/bin.
- §4 — already deterministic; chapter just references scripts/gen_global_percentile_cdf.py.

## LAST steps of Phase A (after all chapters pass — do NOT do early)

- Rewrite `.claude/skills/benchmarks/SKILL.md` to invoke the generator + narrate the artifact
  (preserve display-format / table-render / report-rotation rules; LLM applies verdict thresholds;
  footnote the obsolete checkpoint exception + the comma-grouping ≥1,000 reconciliation).
- Implement report rotation in gen_benchmarks._write_outputs (rotate prior benchmarks-latest.md to
  benchmarks-YYYY-MM-DD.md) and switch off the gen-scaffold-* filenames. Drop the cross-snapshot section.
- The gen-scaffold-* artifacts are gitignored on purpose until then.

## Run reference

```
bin/benchmark_db.sh start
uv run python scripts/gen_benchmarks.py --db benchmark      # full report → reports/benchmark/gen-scaffold-*
uv run --active pytest tests/scripts/benchmarks/ -q          # gates (~3 min; skip if DB down)
uv run --active ruff format scripts/benchmarks/ tests/scripts/benchmarks/
uv run --active ruff check  scripts/benchmarks/ scripts/gen_benchmarks.py tests/scripts/benchmarks/
uv run --active ty check    scripts/benchmarks/ scripts/gen_benchmarks.py tests/scripts/benchmarks/
```
