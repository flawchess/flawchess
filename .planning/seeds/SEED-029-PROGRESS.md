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
- `98567c1a` §3.1.5 Achievable Score Gap — MetricBlock (pp unit). d_i = USER_SCORE_EXPR
  − expected_score_sql() (reuses §3.1.3's entry_rows + sigmoid; mate INCLUDED). ≥20 non-null
  pairs floor. Pooled + all marginals reproduce the report exactly. FOUND a pair-selection
  slip: TC max |d| is (rapid, classical) at 0.134, NOT the report's labeled (bullet, rapid)
  which is only 0.08 — the report carried the right magnitude (0.13/collapse) on the wrong
  pair label. ELO (800, 2400) 0.34 matches. **§3.1 now COMPLETE (3.1.1–3.1.6).**
- `1b0dff5f` §3.2 COMPLETE (3.2.1 + 3.2.2 + 3.2.3) — registered as its own chapter
  `3.2-endgame-metrics-elo` → `chapter3.build_32`. Added shared SQL building blocks to
  sql.py: `endgame_bucket_case_sql` (conv/parity/recov split, mirrors `_classify_endgame_bucket`),
  `bucket_score_case_sql` (win/score/save contribution), `win_chances_sigmoid_sql`,
  `span_es_sql` (per-span ΔES expectation, NO outlier trim). `expected_score_sql` refactored
  onto the sigmoid helper (byte-identical SQL — §3.1.3/§3.1.5 gates re-verified green).
  - §3.2.1 reuses ENDGAME_GAME_IDS_CTE + ENTRY_ROWS_CTE (rn=1) for the first-endgame-ply
    eval; per_user_cell pivots conv/par/recov rate + unweighted skill, ≥20 total games + ≥2
    buckets. conv/recov pooled + all marginals + verdicts EXACT (conv TC 0.93 / ELO 0.51;
    recov TC 0.90 / ELO 0.25). Skill = informational only (no verdict). With ~100% eval
    coverage every qualifying user has all 3 buckets, so `agg_select`'s `count(*)` n is
    faithful (n_conv == n == 4,616, verified).
  - §3.2.2 spans/spans_with_next/gap_rows/per_user_bucket span machinery (the one §3.4.2 will
    reuse). ≥20 spans/user/bucket. conv/recov pooled + all marginals + verdicts EXACT.
  - §3.2.3 derived (no DB query) — pure projection of §3.2.1/§3.2.2 marginals + verdicts;
    gated transitively. Emits sweep + max|d| only; LLM applies the collapse/review/keep word.
  - Parity slips (all verdict-NEUTRAL, footnoted): §3.2.1 TC 0.08→0.11 (rapid,classical);
    §3.2.1 ELO (800,2400)0.20→(1200,2400)0.22; §3.2.2 TC 0.10→0.18 (rapid,classical).
    §3.2.2 parity ELO 0.31 matches. Classical conv mean 0.7545 renders 75.4% (report 75.5%)
    — .5-boundary half-up display artifact (4 dp value exact), same class as known §3.1 cases.
- `c7d76c72` §3.3 COMPLETE (3.3.1 + 3.3.2 + 3.3.3) — NEW module `chapter3_3.py`, registered as
  chapter `3.3-time-pressure` → `chapter3_3.build`. Added shared clock SQL to sql.py:
  `FIRST_ENDGAME_ENTRY_CTE` (entry_ply variant of ENDGAME_GAME_IDS_CTE), `clock_routing_case`
  (user/opp clock at entry by color+parity), `CLOCK_MIN_GAMES`=20, `PRESSURE_BIN_MIN_GAMES`=5,
  `PRESSURE_BIN_NEUTRAL_CAP`=0.06.
  - §3.3.1 clock-diff % / clock-gap fraction / net-timeout — one shared clock-routing scan
    (clean→routed→per_user_cell, ≥20 games/user). clock-gap = clock-diff÷100 (computed natively
    at 4 dp). Pooled + all marginals reproduce the report EXACTLY (n=4,604; sub-800 + sparse
    applied even though §3.3.1's inline SQL omits them — universal rule, like §3.2.1).
    clock-diff verdicts TC 0.24 (bullet,classical) / ELO 0.17 (1600,2400) match. Net-timeout
    ELO 0.28 (800,2400) matches; TC slip report 0.04→det 0.09 (blitz,classical), both collapse.
  - §3.3.2 GAME-level curve. GROUPING SETS ((tb),(tb,tc),(tb,elo)) one scan → pooled 10-bucket
    curve + TC/ELO marginals + var_samp(score) for per-tb Cohen's d on the 0/0.5/1 outcome.
    Pooled curve + both marginals EXACT. Per-tb TC d tb0/5/9 = 0.39/0.14/0.05 (report ≈0.38/
    ≈0.13/0.05, 1-ulp); ELO ≤0.16 all buckets → collapse.
  - §3.3.3 per-user score per (TC×ELO×quintile), quintile=min(4,clock%//20), ≥5 games/bin,
    ≥10 users/cell, sub-800+sparse INLINE (per SKILL §3.3.3). ONE scan: GROUPING SETS
    ((quintile,tc),(quintile,elo)) — the (quintile,tc) rows ARE both the shipped band cells
    (ELO pooled) and the TC-axis verdict input. The 20-cell band table (n_users + p25/p50/p75)
    reproduces the report EXACTLY. **Verdict finding**: the report's per-quintile d's
    (≈0.18–0.46) do NOT reproduce under the documented per-user n/mean/var_samp recipe — they
    read as eyeballed/game-level. Deterministic per-user d's are larger: Q0 TC 0.75 / ELO 0.56,
    Q2 TC 0.46, Q3 ELO 0.34, Q4 ELO 0.31 (Q1 TC 0.32 / Q4 TC 0.19 match). Verdict-narrative
    only — the shipped per-(TC×quintile) band design is unaffected (the larger ELO d's, if
    anything, feed the Phase-B per-ELO stratification review). Emits deterministic values.
  - Rendering is bespoke (§3.3's slice/curve/band tables differ from §3.1/§3.2's MetricBlock
    layout); reuses `agg_select`/`split_grouping_sets`/`stats.max_abs_d` for COMPUTE only.
- **§3.4 COMPLETE (3.4.1 + 3.4.2 + 3.4.3) — diff gate run end-to-end GREEN** (2026-05-30,
  17m44s single job: test_341 + test_342 + test_343 + test_chapter3_322 all pass; the §3.2.2
  span-CTE refactor onto `sql.span_gap_ctes()` is confirmed report-faithful). NEW module
  `chapter3_4.py` registered as chapter `3.4-endgame-type` → `chapter3_4.build` (gen_benchmarks
  `_CHAPTER_BUILDERS`).
  - **§3.4.3 SD-rounding fix**: `_343_query()` rounded score/gap SD to 4 dp (→ 0.1487/0.0486)
    while the report displays them at 3 dp (0.149/0.049, same precision as the query's other
    five columns). Rounded the two SD columns to 3 dp to match the report's display precision —
    NOT a prior-report slip (0.1487→0.149, 0.0486→0.049 confirm the report is correct), just a
    port precision inconsistency. Rendered markdown was already correct (`fmt_unsigned(_, 3)`).
  - **Shared span machinery extracted** (the §3.2.2 reuse the handoff asked for): added
    `sql.span_gap_ctes()` (spans / spans_with_next / gap_rows — gap_rows now ALSO projects
    `endgame_class`, inert for §3.2.2) and `sql.CLASS_SPAN_CTE`. chapter3 §3.2.2 refactored
    onto `span_gap_ctes()` (semantically identical; re-run `test_chapter3_322` to confirm — it
    was SKIPPED when the DB was down, not yet re-verified). §3.4.2 + §3.4.3 reuse it.
  - **NEW stat `stats.spread_d()`** — §3.4.1 uses a DIFFERENT Cohen's d than §3.2/§3.3:
    `(max_mean − min_mean) / sqrt(mean(group variances))`, NOT pairwise-pooled `max_abs_d`.
    The SKILL §3.4.1 verdict text specifies it. Unit-tested (3 new tests in test_stats.py, all
    green). Using the wrong recipe gives rook conv TC 1.09 vs the report's 1.24.
  - §3.4.1 (bespoke render): pooled-by-class summary + per-(user,class) score IQR + conv/recov
    TC & ELO marginals + spread-d verdicts. Summary, IQR, and ALL conv/recov marginals (mean,
    p25, p75, n) reproduce the report EXACTLY; verdicts reproduce EXACTLY via spread_d
    (rook 1.24/0.32/1.33/0.20 … mixed 1.19/0.49/1.28/0.22). Slip: IQR mixed n_users 3,599 det
    vs report 3,597 (mean + all percentiles exact). FINDING: the SKILL §3.4.1 IQR query's
    `GROUP BY ... user_elo_at_game, elo_bucket, tc ...` FRAGMENTS the per-user unit by exact
    rating (→ rook n=2 garbage); the report used a `(user, class)` pooled unit — reproduced here.
  - §3.4.2 (reuses `span_gap_ctes`, grouped by endgame_class): pooled-by-class IQR + ELO/TC
    marginal means + collapse d. Pooled + marginals reproduce EXACTLY (all 6 classes incl.
    pawnless n=12). Verdict d uses pairwise-pooled `max_abs_d` (§3.1.5 recipe). Every verdict
    WORD matches (TC all collapse; ELO collapse rook/pawn/queen, review minor_piece/mixed) but
    the d MAGNITUDES carry pair-selection slips (report eyeballed sub-max pairs: pawn TC
    0.10→0.18, queen TC 0.18→0.198, queen ELO 0.16→0.17 — all verdict-neutral). The §3.4.2
    verdict test asserts collapse/review BANDS, not exact 2-dp d's.
  - §3.4.3 (inner-join of §3.4.1 score CTE + §3.4.2 gap CTE): reproduces the report EXACTLY —
    only `mixed` clears the ≥30 joined-user floor (n=5,274, r=+0.105, sign 46.3%, strict 42.2%,
    strong 9.0%, score SD 0.149, gap SD 0.049). FINDING: §3.4.3's `per_user_class_score`
    fragments per (user, exact-rating, elo, tc, class) — the SKILL query as written — which is
    why the small classes fall below the floor. This is a DIFFERENT unit from §3.4.1's
    report-IQR (which pools per (user, class)); the SKILL comment "reuses the §3.4.1 CTE" is
    inaccurate. Each subchapter reproduced as the report computed it.
  - **NO 5×4 per-class cell grid** in the report §3.4 (despite the handoff/older NOTE saying it
    "first appears at §3.4"): report §3.4.1/§3.4.2 emit pooled + marginals only (like §3.1/§3.2).
    The gate is the report, so chapter3_4 emits pooled + marginals only — no cell-grid builder.
  - SCRATCH to delete before commit: `temp/dump_d.py`, `temp/calc_d.py`, `temp/calc_d2.py`,
    `temp/*.out` (used to derive the deterministic verdict d-values; values are baked into the
    test). NB the FULL generator (`gen_benchmarks.py --db benchmark`) is now slow (§3.4 adds
    heavy span scans) and can exceed a 580s `timeout` — run it without a timeout; it is NOT
    needed for the gate (the gate calls `compute_34x` directly).

## Architecture (scripts/benchmarks/ subpackage; tests in tests/scripts/benchmarks/)

- `sql.py` — shared SQL building blocks + pure `elo_bucket()`. Constants: ELO_ANCHORS, TC_ORDER,
  SELECTED_USERS_CTE (canonical completed-checkpoint join), USER_ELO_AT_GAME_SQL,
  EQUAL_FOOTING_FILTER, BASE_GAME_FILTER, SPARSE_CELL_EXCLUSION, USER_SCORE_EXPR,
  ENDGAME_GAME_IDS_CTE, MIDDLEGAME_PHASE/ENDGAME_PHASE, EVAL_OUTLIER_TRIM_CP=2000,
  EVAL_CONFIDENCE_MIN_N=20, SCORE_GAP_MIN_GAMES=30, ENDGAME_MIN_GAMES=20, LICHESS_WIN_CHANCES_K.
- `stats.py` — pure Cohen's d: `cohens_d`, `max_abs_d` (pairwise pooled), `spread_d`
  (§3.4.1 ONLY: `(max−min)/sqrt(mean variance)`). LevelStat → DResult. Unit-tested.
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
- `chapter1.py`, `chapter2.py`, `chapter3.py` (§3.1+§3.2), `chapter3_3.py` (§3.3),
  `chapter3_4.py` (§3.4, bespoke render like §3.3) — chapters; registered in
  gen_benchmarks._CHAPTER_BUILDERS. §3.3 added clock building blocks to sql.py:
  `FIRST_ENDGAME_ENTRY_CTE`, `clock_routing_case`, CLOCK_MIN_GAMES, PRESSURE_BIN_MIN_GAMES,
  PRESSURE_BIN_NEUTRAL_CAP. §3.2 added `endgame_bucket_case_sql`, `bucket_score_case_sql`,
  `win_chances_sigmoid_sql`, `span_es_sql`, EVAL_ADVANTAGE_THRESHOLD, SECTION2_SPAN_MIN_SPANS.
  §3.4 added `sql.span_gap_ctes()` (shared spans/spans_with_next/gap_rows — chapter3 §3.2.2
  refactored onto it) + `sql.CLASS_SPAN_CTE` + `stats.spread_d`.

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
  §3.1.2 + §3.1.3 had NONE. §3.2 parity (×3, all verdict-neutral). §3.3.1 net-timeout TC
  0.04→0.09. §3.3.2 per-tb TC 0.38/0.13→0.39/0.14 (1-ulp). Expect more — verify, don't assume.
- **§3.3.3 verdict recipe mismatch (the one MATERIAL verdict divergence so far)**: the report's
  §3.3.3 per-quintile collapse d's (≈0.18–0.46) were NOT computed with the documented per-user
  n/mean/var_samp recipe — they read as eyeballed/game-level. Per-user scores cluster tightly
  (var≈0.014–0.034), so the same mean gap yields a much larger Cohen's d than the report shows
  (Q0 TC 0.43→0.75, Q0 ELO 0.20→0.56). The generator emits the deterministic per-user values; the
  20-cell band table (the actual shipped output) matches the report exactly, so this is
  verdict-narrative-only. If a future reviewer wants the report's verdict to match, the question
  is whether §3.3.3's verdict should be game-level (it should NOT, per the documented recipe).
- **§3.3 sub-800 + sparse are universal even when the inline §3.3.1/§3.3.2 SQL omits them** (same
  as §3.2.1). §3.3.3's inline SQL includes them. Apply to all three; pooled n=4,604 confirms.
- **§3.4.1 uses a DIFFERENT Cohen's d than every other subchapter**: `(max_mean − min_mean) /
  sqrt(mean(group variances))` (`stats.spread_d`), NOT pairwise-pooled `max_abs_d`. The SKILL
  §3.4.1 verdict text specifies it; it's the only place the spread recipe is used. §3.4.2 keeps
  pairwise-pooled (it says "same as §3.1.5"). Don't assume one d recipe across the report.
- **NEVER run two heavy benchmark-DB scans concurrently** (e.g. the full generator + a gate, or
  two gate jobs): it OOM'd/stopped the `flawchess-benchmark-db-1` container mid-run (→
  `ECONNREFUSED 127.0.0.1:5433`, and gates silently SKIP per conftest). Run sequentially; if the
  DB is unreachable, `bin/benchmark_db.sh start` and wait for `(healthy)`. asyncpg connects can
  hang for minutes against a dying container with 0 CPU — kill and restart the DB rather than wait.
- **The §3.4 SKILL "per-user-per-class score CTE" is reused inconsistently**: §3.4.1's report-IQR
  pools per `(user, class)`; §3.4.3's join fragments per `(user, exact-rating, elo, tc, class)`.
  Reproduce each exactly as the report did (verified against benchmarks-latest.md), not as the
  cross-reference comments claim. Footnoted in chapter3_4 docstring.

## Remaining work

- §4 — already deterministic; chapter just references scripts/gen_global_percentile_cdf.py.

NOTE on the 5×4 cell grid (RESOLVED): the SKILL "Output" sections mention 5×4 p50 cell tables,
but benchmarks-latest.md NEVER contains one — §3.1/§3.2/§3.3 AND §3.4 all emit pooled +
marginals only. The gate is the report, so no chapter builds a 5×4 grid (the earlier guess that
it "first appears at §3.4" was wrong — verified against the 2026-05-27 report).

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
