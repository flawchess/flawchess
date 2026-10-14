---
phase: quick-261014-rux
plan: 01
quick_id: 261014-rux
mode: quick
type: execute
wave: 1
depends_on: []
files_modified:
  - scripts/benchmarks/chapter5.py
  - tests/scripts/test_chapter5_sql.py
  - tests/scripts/benchmarks/test_chapter5_diff.py
  - app/services/flaw_delta_zones.py
  - app/services/library_service.py
  - app/schemas/library.py
  - tests/services/test_flaw_delta_zones.py
  - tests/services/test_flaw_comparison.py
  - reports/benchmark/benchmarks-latest.md
  - reports/benchmark/benchmarks-2026-10-12.md
  - .claude/skills/benchmarks/SKILL.md
  - CHANGELOG.md
autonomous: false
requirements: ["QUICK-261014-rux"]

estimate:
  tokens: 155000
  raw_tokens: 155000
  tasks: 3
  confidence: low

must_haves:
  truths:
    - "One foreground run of `uv run python -m scripts.benchmarks.chapter5 --db benchmark --out temp/261014-rux/run` computes the 12 flaw metrics AND the 9 tempo x phase crossed cells on the whole-cohort basis (every `g.evals_completed_at IS NOT NULL` game of a selected user passing sql.BASE_GAME_FILTER, all four TCs, at least 20 games per user x (game-time ELO, TC) cell, no benchmark_selection / full-eval / full-PV / blob gate), and the 38 tactic metrics on the unchanged classical + rapid full-analysis lane; every flaw block's TC marginal lists bullet, blitz, rapid and classical"
    - "In both section 5 bases user_moves is CEIL(ply_count/2) for white and FLOOR(ply_count/2) for black, matching library_service._user_moves_from_ply_count; a DB-free SQL-shape test pins that direction"
    - "tests/scripts/benchmarks/test_chapter5_diff.py EXPECTED_* values (12 flaw, 9 crossed, 38 tactic, zone_viable set over 59 metrics, per-basis cohort summaries) are transcribed mechanically from that same run's chapter5.json, the offline transcription check passes, and the live diff gate passes once (or a straggler drift is recorded, not re-looped)"
    - "Every one of the 12 flaw metrics and 9 crossed cells has its own registry entry for each of bullet, blitz, rapid and classical; flaw_delta_zone(metric, tc) and tempo_phase_zone(tempo, phase, tc) index the TC directly (no ZONE_TC_FOR); the values equal what temp/261014-rux/derive_bands.py derives from chapter5.json under the owner-chosen TC band rule (`--check` passes); tactic_delta_zones.py and its ZONE_TC_FOR mapping are unchanged"
    - "The applied TC band rule (A = locked D-10 verdict rule, B = per-TC bands everywhere) is the owner's checkpoint answer and is stated in the registry docstring, the report section 5 and the SUMMARY"
    - "reports/benchmark/benchmarks-latest.md (dated 2026-10-14, previous latest archived verbatim as benchmarks-2026-10-12.md) narrates section 5 on the split basis with the run's snapshot timestamp: intro basis note, 5.1 to 5.12 with four-TC marginals and verdict words, 5.13 lane tactics, 5.14 / 5.15 split by basis, new 5.16 crossed cells, and the two summary tables; .claude/skills/benchmarks/SKILL.md section 5 documents the same"
    - "CHANGELOG.md [Unreleased] gains exactly one user-facing bullet that is true for the rule applied"
  artifacts:
    - path: "scripts/benchmarks/chapter5.py"
      provides: "Basis-parameterised _base_games_cte(basis), parity-fixed user_moves, TEMPO_PHASE_METRICS (9 crossed cells), two zone queries + two viability queries, Chapter5Values with tempo_phase and per-basis cohorts, render with split 5.14/5.15 and new 5.16"
      contains: "TEMPO_PHASE_METRICS"
    - path: "tests/scripts/benchmarks/test_chapter5_diff.py"
      provides: "Diff gate regenerated from the 2026-10-14 run, incl. crossed-cell expectations"
      contains: "EXPECTED_TEMPO_PHASE"
    - path: "app/services/flaw_delta_zones.py"
      provides: "FLAW_DELTA_ZONES and TEMPO_PHASE_ZONES keyed by all four TimeControlBucket values; direct-TC lookups; ZONE_TC_FOR kept only for the tactic registry"
      contains: "\"bullet\""
    - path: "tests/services/test_flaw_delta_zones.py"
      provides: "Per-(metric, TC) and per-(cell, TC) half-width pins generated from the run; four-TC structure and direct-lookup identity tests"
      contains: "\"bullet\""
    - path: "reports/benchmark/benchmarks-2026-10-12.md"
      provides: "Verbatim archive of the lane-basis report (rotation rule)"
  key_links:
    - from: "scripts/benchmarks/chapter5.py::_base_games_cte"
      to: "scripts/benchmarks/chapter5.py::_per_user_cte / _viability_sql"
      via: "one base CTE per basis embedded in that basis's zone query and viability query (no drift between the two)"
      pattern: "_base_games_cte\\("
    - from: "temp/261014-rux/run/chapter5.json"
      to: "app/services/flaw_delta_zones.py"
      via: "derive_bands.py (rule A or B) prints the symmetric_band(q1, q3) literals; --check re-derives and compares against the imported registry"
      pattern: "symmetric_band\\("
    - from: "app/services/flaw_delta_zones.py::flaw_delta_zone"
      to: "app/services/library_service.py::_build_flaw_bullet"
      via: "band = flaw_delta_zone(metric, tc), now FLAW_DELTA_ZONES[metric][tc]"
      pattern: "flaw_delta_zone\\("
    - from: "app/services/flaw_delta_zones.py::tempo_phase_zone"
      to: "app/services/library_service.py::_build_tempo_phase_cell"
      via: "band = tempo_phase_zone(tempo, phase, tc), now TEMPO_PHASE_ZONES[(tempo, phase)][tc]"
      pattern: "tempo_phase_zone\\("
---

<objective>
Move the 12 flaw-delta metrics of benchmark section 5 back to the whole-cohort basis (all four TCs), fix the user-move parity flip, add the 9 tempo x phase crossed cells to chapter5 on the same basis, re-run section 5 once, regenerate the diff gate from that run, and serve per-TC flaw and crossed-cell bands in the app wherever the owner-chosen TC rule says split. Tactic metrics stay on the full-analysis lane and keep ZONE_TC_FOR.

Purpose: section 5.15 shows the lane flaw bands are 70 to 140% sampling noise (about 69 games per user, 100-game cap); the whole cohort (up to 1000 games per user) has signal/noise 1.1 to 2.4, and per-TC IQRs differ up to 12x (hasty: bullet 0.15 vs classical 1.76 per 100 moves, 261014-qj8-PROBE.md) while the app serves one band to every TC.

Output: refactored chapter5.py + SQL-shape test + regenerated diff gate; per-TC FLAW_DELTA_ZONES / TEMPO_PHASE_ZONES with pinned tests; refreshed report section 5 (old latest archived); SKILL.md section 5 docs; one CHANGELOG bullet.

PLANNER FLAG (read before execution, the reason Task 2 exists): the locked rule "split where the TC collapse verdict says split" uses the D-10 Cohen's-d verdict, which tests a shift in the MEAN of per-user values between TCs. A band is a SPREAD statistic (IQR). On this exact basis with all four TCs (reports/benchmark/benchmarks-2026-08-18.md, top-axis collapse summary) every flaw metric's TC max |d| was 0.03 to 0.21 (collapse or review), so the literal rule will almost certainly split nothing: bullet would keep a band about 2x wider than its own IQR and classical one about 2x narrower, and the requested CHANGELOG sentence would be false. Task 2 puts that to the owner with the run's numbers. The orchestrator may ask the owner up front (the 2026-08-18 evidence already exists) and record the answer, in which case Task 2 does not pause.
</objective>

<execution_context>
@~/.claude/gsd-core/workflows/execute-plan.md
@~/.claude/gsd-core/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@CLAUDE.md
@.planning/quick/261014-qj8-benchmark-bands-for-the-tempo-x-phase-he/261014-qj8-PROBE.md
@scripts/benchmarks/chapter5.py
@app/services/flaw_delta_zones.py
@tests/scripts/test_chapter5_sql.py
@tests/services/test_flaw_delta_zones.py

Read on demand (large): .claude/skills/benchmarks/SKILL.md lines 1840-2010 (section 5 docs, incl. "Verdict to registry rule (D-10)"); reports/benchmark/benchmarks-latest.md lines 1-22, 165-178, 695-1486 (section 5), 1486-1600 (summary tables); tests/scripts/benchmarks/test_chapter5_diff.py (shape of EXPECTED_* dicts and the _check_* helpers); tests/services/test_flaw_comparison.py lines 225-250, 645-670, 715-745.

Pre-239 whole-cohort predicate (authoritative, recover with `git show 34a82eda3^:scripts/benchmarks/chapter5.py`): base_games = `FROM games g JOIN selected_users su ON su.user_id = g.user_id WHERE {sql.BASE_GAME_FILTER} AND g.evals_completed_at IS NOT NULL` (1,223,105 games at the 239 snapshot; the probe's pooled n was 4,827 user-cells).

<interfaces>
Verified in the codebase at planning time:

- scripts/benchmarks/chapter5.py: `_base_games_cte()` (no args, lane only) is embedded by `_per_user_cte()` and `_viability_sql()`; `_FLAW_TAG_PREDICATES` (12 keys, tempo = 0/1/2, phase = 0/1/2), `_TACTIC_PREDICATES`, `_ALL_METRICS = FLAW_DELTA_METRICS + TACTIC_METRICS`, one UNION ALL zone query over `pu` with `dist.GROUPING_SETS`; flaw delta = (p - o)::float / NULLIF(user_moves, 0), tactic delta = (p - o)::float; `_assemble_block` (cell floor 30, `_safe_verdict`), `_noise_row`, `_compute_viability` returns (rows, CohortSummary); `Chapter5Values{flaw, tactic, viability, noise, cohort}`; render(): sections 5.1-5.12 via `_metric_section(..., "pp3")`, 5.13 `_render_tactic_table` (`_TACTIC_TABLE_TCS = ("rapid", "classical")`, `_tc_range` / `_max_abs_d` hard-code the "per100g" unit), 5.14 `_render_viability(viability, cohort)`, 5.15 `_render_noise_summary`; `_main` writes chapter5.md + chapter5.json (json.dumps default=str) and prints `_summary_line`.
- app/repositories/library_repository.py comments (lines ~1852, ~2251) cite `chapter5.py _base_games_cte` as the tactic calibration basis: keep the function NAME `_base_games_cte` (add a parameter) so they stay true.
- scripts/gen_benchmarks.py only calls `chapter5.build`; nothing outside chapter5.py reads `values["cohort"]`.
- app/services/flaw_delta_zones.py: `ZoneBand`, `symmetric_band(q1, q3)` (half-width = ceil of (q3 - q1)/2 on the 0.01 grid), `ZoneTc = Literal["rapid", "classical"]`, `ZONE_TC_FOR`; `FLAW_DELTA_ZONES: Mapping[FlawDeltaMetric, Mapping[ZoneTc, ZoneBand]]`; `TEMPO_PHASE_ZONES: Mapping[tuple[FlawTempoMetric, FlawPhaseMetric], Mapping[ZoneTc, ZoneBand | None]]`; `flaw_delta_zone` / `tempo_phase_zone` index via ZONE_TC_FOR. app/services/tactic_delta_zones.py imports `ZONE_TC_FOR, ZoneBand, ZoneTc, symmetric_band` from it (keep all four exported). `TimeControlBucket` comes from app.schemas.normalization (already imported there; do NOT import app.schemas.library, import cycle).
- app/schemas/library.py: FlawBullet `has_zone` is documented "Always True: every flaw metric has a band", so the flaw registry value type must stay non-optional ZoneBand.
- tests/services/test_tactic_delta_zones.py already pins ZONE_TC_FOR (blitz/bullet -> rapid) and `tactic_delta_zones.ZONE_TC_FOR is ZONE_TC_FOR`.
- tests/scripts/benchmarks/ is excluded by pyproject addopts; the documented explicit-path command `uv run pytest tests/scripts/benchmarks/test_chapter5_diff.py -q` runs it (one compute() per session).
- benchmark DB URL defaults to localhost:5433 in app/core/config.py, so the run works from a worktree without .env.
</interfaces>
</context>

<tasks>

<task type="tracer" tdd="true">
  <name>Task 1: Section 5 end to end on the split basis: chapter5 refactor, one run, diff gate from that run</name>
  <files>scripts/benchmarks/chapter5.py, tests/scripts/test_chapter5_sql.py, tests/scripts/benchmarks/test_chapter5_diff.py</files>
  <precondition>The benchmark DB answers on localhost:5433 (start it with `bin/benchmark_db.sh start` if not) and no other benchmark-DB scan is running (`pgrep -f "scripts.benchmarks.chapter5|gen_benchmarks|benchmark_lane"` prints nothing).</precondition>
  <behavior>
    - The whole-cohort base CTE carries `g.evals_completed_at IS NOT NULL` and the BASE_GAME_FILTER TC anchor, and none of benchmark_selection, bs.armed, a tranche filter, full_evals_completed_at, full_pv_completed_at or blobs_completed_at.
    - The lane base CTE is unchanged (armed, classical + rapid tranches, full evals, full PVs, blobs) and does not carry evals_completed_at.
    - Both base CTEs define user_moves with CEIL(g.ply_count / 2.0) for white and FLOOR(g.ply_count / 2.0) otherwise, as a base_games column (no user_moves_per_game helper CTE).
    - TEMPO_PHASE_METRICS has 9 keys `{tempo}__{phase}`, phase-major (opening, middlegame, endgame_phase) with tempo order low_clock, hasty, unrushed inside each phase; each predicate is the tempo predicate AND the phase predicate taken from _FLAW_TAG_PREDICATES.
    - The whole-cohort zone SQL has nv_ columns for the 12 flaw keys and the 9 crossed keys and no tactic column; the lane zone SQL has the 38 tactic columns and no flaw column; each basis's zone and viability SQL embed that basis's base CTE.
  </behavior>
  <action>
Step 1, chapter5.py (keep functions small, nesting depth at most 4, explicit return types, Literal not bare str):
(a) Add `Basis = Literal["whole_cohort", "lane"]` and give `_base_games_cte` a `basis: Basis` parameter (keep the name: library_repository comments cite it). "whole_cohort" reproduces the pre-239 predicate exactly (see the context block: games JOIN selected_users, sql.BASE_GAME_FILTER, `g.evals_completed_at IS NOT NULL`; all four TCs; no lane join or completion predicates). "lane" keeps today's predicate verbatim. Rewrite the docstring to explain both and why tactics need the lane (blob-gated motifs: outside the lane game_flaws has no pv_lines, while tempo/phase/miss/lucky/reversed/squandered columns are populated for every flaw).
(b) Parity fix: one module-level constant holds the user_moves CASE for both bases, white gets CEIL(g.ply_count / 2.0), every other colour FLOOR(g.ply_count / 2.0). Put a comment at the fix site: white moves first, so it plays the odd half-moves; runs before 2026-10-14 had the two swapped; the direction now matches library_service._user_moves_from_ply_count (PR #420 review). Correct every docstring and the render intro that state the old direction, and delete the "KNOWN FLIP" comment block.
(c) Add TEMPO_PHASE_METRICS (9 (key, delta_col) pairs, delta_col = f"delta_{key}", order per the behavior block) and `_TEMPO_PHASE_PREDICATES` built by AND-ing the existing tempo and phase entries of _FLAW_TAG_PREDICATES (no new SQL literals). Crossed cells are rate metrics: same (p - o)::float / NULLIF(user_moves, 0) delta as the 12.
(d) Metrics per basis: whole_cohort = FLAW_DELTA_METRICS + TEMPO_PHASE_METRICS, lane = TACTIC_METRICS. `_per_user_cte(basis)`, `_metric_select` and `_viability_sql(basis)` build from that basis's metrics only; the rate-vs-count delta choice is decided by membership in the rate set. compute() runs four queries sequentially on the one session (zone whole_cohort, zone lane, viability whole_cohort, viability lane), never asyncio.gather on one AsyncSession (CLAUDE.md).
(e) Chapter5Values: add `tempo_phase: dict[str, MetricBlock]` (9 crossed blocks) and replace `cohort` with `cohorts: dict[Basis, CohortSummary]`; viability rows cover 12 + 9 + 38 = 59 metrics, noise rows the same 59. degenerate_iqr / zone_viable fill-in stays as today, per metric.
(f) render(): rewrite the intro basis note for the split basis (flaw metrics and crossed cells: whole cohort, all four TCs, up to 1000 games per user per TC, mixed eval provenance disclosed not excluded per Phase 212 D-06; tactic metrics: full-analysis lane, classical + rapid, blitz/bullet tactic zones read rapid in the app via ZONE_TC_FOR); state the parity direction now used; keep the estimator, cell-floor and sparse-cell notes. Sections 5.1 to 5.12 and 5.13 keep their code path (flaw TC marginals now show four levels). 5.14 viability becomes two sub-blocks, each with its own cohort line from `cohorts[basis]`: "Whole-cohort basis" (flaw table, then a tempo x phase table) and "Full-analysis lane" (tactic table). 5.15 noise becomes two tables (whole cohort: flaw + crossed, pp; lane: tactic, per 100 games); the noise-summary blockquote must no longer claim every band sits at the lane's 100-game cap. Append "### 5.16 Tempo x Phase Crossed Cells": one compact row per cell in pp3 units with tempo, phase, n, p25, p50, p75, a p25-to-p75 column for each of bullet, blitz, rapid and classical, TC max abs d, ELO max abs d, pct_nonzero, noise-only IQR, zone_viable. Make the unit and the TC list parameters of `_tc_range` / the compact-table builder instead of copying `_render_tactic_table`. Update SECTION and `_summary_line` (flaw / crossed / tactic counts, TC levels of the blunder block, games per basis).
(g) Leave FULL_ANALYSIS_TRANCHES, the 20-game floor, the 30-user-cell floor, the viability rule and the noise formula unchanged.

Step 2, tests/scripts/test_chapter5_sql.py: rewrite TestFullAnalysisBasis into per-basis tests for every behavior bullet above (the old blanket "evals_completed_at must not appear" assertion becomes "lane only"); keep the cell-floor, safe-verdict, zone-viability and tactic-predicate tests; add the crossed-metric list/predicate tests and the parity-direction test. RED first: write these, see them fail against today's chapter5.py, then implement Step 1. Run `uv run pytest tests/scripts/test_chapter5_sql.py -q` until green. Mutation check: swap CEIL/FLOOR back in the constant, confirm the parity test fails, restore.

Step 3, the run (single blocking step; nothing else touches the benchmark DB meanwhile): write `date -u +%Y-%m-%dT%H:%MZ` and the output of `uv run python scripts/benchmark_lane.py status --all-tranches --db benchmark` into temp/261014-rux/run/SNAPSHOT.txt, then run `uv run python -m scripts.benchmarks.chapter5 --db benchmark --out temp/261014-rux/run` in the FOREGROUND with the Bash timeout at 600000 ms (pre-239 whole-cohort compute took about 1.5 min and the lane about 1 min, so expect a few minutes). If it will not finish inside the 10-minute Bash cap, use the detached setsid nohup + Monitor pattern from memory project_orchestrator_long_operator_runs and wait for chapter5.json before doing anything else; never start a second scan in parallel. Sanity gate before moving on: the summary line lists bullet, blitz, rapid, classical; whole-cohort games are near 1.22M and the flaw pooled n is near 4,827 user-cells (within a few percent). A large deviation means the base predicate is wrong: stop and diff it against the git show.

Step 4, scratch tooling in temp/261014-rux/ (gitignored, not committed, per memory feedback_drafts_in_repo_temp):
- gen_diff_expected.py: loads chapter5.json and prints the EXPECTED_* Python literals for test_chapter5_diff.py (flaw pooled / ELO / TC / verdicts for the 12; the same four for the 9 crossed cells; tactic pooled (n, p25, p50, p75) + verdicts; the zone_viable set over 59 metrics; per-basis cohort summaries). Values verbatim from the JSON, verdict d rounded to 2 dp exactly as _check_verdicts compares.
- check_expected.py: imports the regenerated test module and runs its _check_* helpers against the JSON blocks (offline transcription check, no DB scan), exit code non-zero on any mismatch.
- derive_bands.py: reads chapter5.json. Mode `--evidence` prints, for each of the 12 flaw metrics and 9 crossed cells: TC max |d| with pair and verdict word (below 0.2 collapse, 0.2 to below 0.5 review, 0.5 or more keep separate), pooled IQR, the four per-TC IQRs (per 100 moves) and max/min per-TC IQR ratio, pct_nonzero, zone_viable. Default mode prints registry literals and test pin tables under the rule read from temp/261014-rux/RULE (written in Task 2), with `--check` importing app.services.flaw_delta_zones and comparing every entry (exit non-zero on mismatch). Derivation rule, mechanical: q(x) = round(x * 100, 3) (proportion to per 100 moves, the report's pp3 precision). Split decision per block: rule A splits only when the block has a TC verdict with max_abs_d of 0.5 or more; rule B always splits. For each TC L in bullet, blitz, rapid, classical: if split AND L is present in tc_marginal (not thin) AND its p25 is below its p75, the band is symmetric_band(q(L.p25), q(L.p75)); otherwise symmetric_band(q(pooled.p25), q(pooled.p75)). A crossed cell whose viability row has zone_viable false is None for all four TCs. A flaw metric with zone_viable false aborts the script (the flaw registry is non-optional): escalate to the owner, do not invent a band.

Step 5, tests/scripts/benchmarks/test_chapter5_diff.py: replace every EXPECTED_* block with gen_diff_expected.py output; add EXPECTED_TEMPO_PHASE (pooled, ELO, TC, verdicts) and a test_chapter5_tempo_phase test reusing the helpers; assert the per-basis cohort summaries; viability length = 12 + 9 + 38; rewrite the module docstring (split basis, snapshot timestamp and lane status from SNAPSHOT.txt, game / user-cell / distinct-user counts per basis, parity fixed). Then run check_expected.py, then the live gate once. If the live gate fails only by straggler drift (lane still finishing), record the drift in the SUMMARY and do not loop; any structural failure is a bug to fix.
  </action>
  <verify>
    <automated>uv run pytest tests/scripts/test_chapter5_sql.py -q && test -s temp/261014-rux/run/chapter5.json && uv run python temp/261014-rux/check_expected.py temp/261014-rux/run/chapter5.json && uv run python temp/261014-rux/derive_bands.py temp/261014-rux/run/chapter5.json --evidence && uv run pytest tests/scripts/benchmarks/test_chapter5_diff.py -q</automated>
  </verify>
  <done>chapter5.py computes flaw + crossed metrics on the whole cohort with four-TC marginals and tactics on the lane, parity fixed; the SQL-shape test is green and its parity test bit under mutation; temp/261014-rux/run/ holds chapter5.md, chapter5.json and SNAPSHOT.txt from ONE run; the diff gate is regenerated from that JSON, passes the offline check and the live run (or the straggler drift is recorded); derive_bands.py --evidence prints the 21-row evidence table. Commit: `feat(benchmarks): section 5 flaw metrics on the whole cohort, parity fix, tempo x phase cells`.</done>
</task>

<task type="checkpoint:decision" gate="blocking-human">
  <name>Task 2: Owner picks the TC band rule from the run's evidence (locked D-10 verdict rule vs per-TC everywhere)</name>
  <decision>Which rule turns the run's numbers into per-TC flaw and crossed-cell bands. Write the answer ("A" or "B") into temp/261014-rux/RULE. If the orchestrator already got the owner's answer before execution, write it, note it in the SUMMARY, and continue without pausing. Unattended with no answer: A, the locked decision.</decision>
  <context>Show the owner the `derive_bands.py temp/261014-rux/run/chapter5.json --evidence` table. The locked rule splits a metric only when its TC Cohen's d reaches keep separate (0.5 or more). That d measures how far the per-user MEAN moves between TCs; a band is the IQR, a spread. Flaw gaps are centred near zero in every TC while their spread grows with the time control (PROBE.md, old basis: hasty IQR 0.15 bullet vs 1.76 classical, opening 0.13 vs 0.81, endgame 0.09 vs 0.37), and on this same basis the 2026-08-18 report had every flaw TC d between 0.03 and 0.21. Expect rule A to split nothing. Elo keying stays out of scope under either rule. Tactic bands are untouched under either rule.</context>
  <options>
    <option id="A">
      <name>A: locked D-10 rule, split only where the TC verdict is keep separate</name>
      <pros>Exactly the decision as written; the same verdict-to-registry rule every other benchmark section uses.</pros>
      <cons>Probably zero splits: all four TCs get the pooled whole-cohort band, so bullet's band stays about 2x its own IQR and classical's about half of its own. The app change shrinks to refreshed numbers, and the requested "blitz and bullet now use their own bands" CHANGELOG line would be false (Task 3 then uses the alternative wording).</cons>
    </option>
    <option id="B">
      <name>B (recommended): per-TC bands for every flaw metric and every viable crossed cell</name>
      <pros>Fixes the problem that motivated the task: each TC's band is that TC's own IQR. Every TC level has hundreds of user-cells and whole-cohort signal/noise above 1, and where two TCs really are alike their bands come out alike anyway. Pooled fallback stays for a thin or degenerate TC level.</pros>
      <cons>Departs from the D-10 verdict-gated rule for these metrics; 84 registry entries instead of 21 to pin (all generated by derive_bands.py, so no hand transcription).</cons>
    </option>
  </options>
  <resume-signal>Reply "A" or "B" (or name another rule, e.g. "split when max/min per-TC IQR ratio is 2 or more", which then replaces the split decision in derive_bands.py).</resume-signal>
</task>

<task type="auto" tdd="true">
  <name>Task 3: Per-TC registry from the run, tests, CHANGELOG, report section 5 and SKILL.md docs</name>
  <files>app/services/flaw_delta_zones.py, app/services/library_service.py, app/schemas/library.py, tests/services/test_flaw_delta_zones.py, tests/services/test_flaw_comparison.py, CHANGELOG.md, reports/benchmark/benchmarks-2026-10-12.md, reports/benchmark/benchmarks-latest.md, .claude/skills/benchmarks/SKILL.md</files>
  <precondition>temp/261014-rux/RULE contains A or B (Task 2) and temp/261014-rux/run/chapter5.json is the Task 1 run.</precondition>
  <behavior>
    - FLAW_DELTA_ZONES and TEMPO_PHASE_ZONES carry exactly the keys bullet, blitz, rapid, classical for every metric / cell, on the 0.01 grid, zone_lo below zone_hi where banded.
    - flaw_delta_zone(m, tc) is FLAW_DELTA_ZONES[m][tc] and tempo_phase_zone(t, p, tc) is TEMPO_PHASE_ZONES[(t, p)][tc] for all four TCs (identity).
    - The half-width pins per (metric, TC) and (cell, TC) equal derive_bands.py output; the zoneless crossed set equals the run's non-viable cells.
    - The flaw-comparison payload's bullet for a bullet-TC game reads the bullet entry, not the rapid one (proved with a monkeypatched four-TC registry whose bullet / rapid / classical bands differ).
  </behavior>
  <action>
Step 1, registry (app/services/flaw_delta_zones.py): run `uv run python temp/261014-rux/derive_bands.py temp/261014-rux/run/chapter5.json` and paste its literals. FLAW_DELTA_ZONES becomes Mapping[FlawDeltaMetric, Mapping[TimeControlBucket, ZoneBand]] and TEMPO_PHASE_ZONES Mapping[tuple[FlawTempoMetric, FlawPhaseMetric], Mapping[TimeControlBucket, ZoneBand | None]], every entry written as symmetric_band(q1, q3) with the 3-dp quartiles (D-15: never a raw ZoneBand literal); a small helper returns one shared band under all four TCs for an unsplit metric. flaw_delta_zone and tempo_phase_zone index the TC directly. Keep ZoneTc and ZONE_TC_FOR exported unchanged (tactic_delta_zones.py imports them) with a comment that only the tactic registry uses them now; do not touch tactic_delta_zones.py. Rewrite the module docstring and the TEMPO_PHASE_ZONES basis comment: whole-cohort section 5 run at the SNAPSHOT.txt timestamp, the applied rule (A or B, per the owner at Task 2), crossed cells now measured by chapter5 section 5.16 with the parity fix (the qj8 PROBE is superseded), D-15 symmetric bands, no Elo keying. Then run derive_bands.py with `--check`.
Step 2, comments only: in app/services/library_service.py (_build_flaw_bullets and _build_tempo_phase_cell docstrings) and app/schemas/library.py (FlawBullet zone comment, TempoPhaseCell docstring) replace "per-zone-TC", "pooled" and the D-08 mapping wording for flaws with "per-TC band". No logic change in either file.
Step 3, tests. tests/services/test_flaw_delta_zones.py: replace _SYMMETRIC_HALF_WIDTHS and _TEMPO_PHASE_HALF_WIDTHS with per-(key, TC) pin tables printed by derive_bands.py; four-TC structure, grid and identity tests per the behavior block; the zoneless crossed set from the run; drop the flaw-side ZONE_TC_FOR test (tests/services/test_tactic_delta_zones.py pins the mapping); keep the symmetric_band rounding test; under rule B add one test that hasty's bullet half-width is smaller than its classical half-width. tests/services/test_flaw_comparison.py: test_bullets_and_zone_bounds asserts each TC's bullets carry flaw_delta_zone(tag, that tc) and no longer claims blitz reads the rapid band (docstring too); test_classical_and_bullet_bands monkeypatches a four-TC hasty entry with distinct bullet, rapid and classical bands and asserts bullet reads the bullet band; the tempo x phase shape test's banded-cell count and zoneless assertion follow the run's viable set. Mutation check: route flaw_delta_zone through ZONE_TC_FOR temporarily, confirm test_classical_and_bullet_bands fails, restore, record it in the SUMMARY (memory feedback_mutation_test_gap_closures). Frontend: grep frontend/src for tests pinning registry values; they use fixtures today, so expect no frontend change.
Step 4, CHANGELOG.md: one bullet under [Unreleased] / ### Changed. If at least one flaw metric got per-TC bands: "Library Stats: flaw comparisons now use a typical range measured on games of the selected time control, so blitz and bullet get their own ranges instead of the rapid one." If rule A split nothing: "Library Stats: the typical ranges for flaw comparisons are re-measured on all benchmark games of every time control." Commas, not em-dashes.
Step 5, report. Rotate first: copy reports/benchmark/benchmarks-latest.md verbatim to reports/benchmark/benchmarks-2026-10-12.md (first-line date; never edit the archive afterwards). Then in benchmarks-latest.md: title date 2026-10-14; the "Snapshot taken" and "§5" header bullets and the section 1 paragraph on the section 5 basis (around line 170) describe the split basis, the snapshot timestamp, per-basis counts, the parity fix and the applied rule; replace the whole "## 5." region up to "## Top-axis collapse summary" with temp/261014-rux/run/chapter5.md as the skeleton plus the hand-authored narration the benchmarks skill requires (SKILL.md "Narration procedure"): per metric 5.1 to 5.12 the verdict words for both axes from the d thresholds, the noise line, the recommendation under the applied rule with the served per-TC half-widths, the low_clock viability row, the squandered / lucky state-conditional note; 5.13 stays the lane narration with this run's numbers, and if any tactic pooled quartile would move a served tactic half-width, note the drift (the tactic registry stays as is, out of scope); 5.14 / 5.15 narrated per basis; 5.16 narrated (which cells are banded, the served per-TC half-widths). Update the "Top-axis collapse summary" rows for 5.1 to 5.12 plus one 5.16 row, and the "Recommended thresholds summary" flaw and crossed-cell rows (current = the old registry, recommended = the new per-TC values). Remove the Phase 239 lane-proposal / owner-override language for flaw bands and the old parity-flip note from the live report. Stale check: grep the section 5 region for the old lane cohort numbers (138,104 and 2,006) outside 5.13 / lane lines, and for "rapid zones" wording applied to flaws (memory project_diff_gate_not_narration).
Step 6, .claude/skills/benchmarks/SKILL.md: the frontmatter description and the section 5 docs (basis table now per basis, blitz/bullet stopgap scoped to tactics, D-01 estimator parity direction fixed, a new "Tempo x phase crossed cells (5.16)" subsection, noise diagnostic wording per basis, viability now 59 rows split by basis, mixed eval provenance: flaw metrics read the whole cohort again so their game_flaws mix lichess-classified and engine-homogenized rows, disclosed, collapse methodology noting four TC levels for flaw metrics, "Verdict to registry rule" rewritten to the rule the owner picked and the old "Flaw bands keep the whole-cohort basis (Phase 239 D-07 override)" paragraph replaced, fast-path summary line, report section structure template).
Commit in two steps: `feat(library): per-TC flaw and tempo x phase benchmark bands` (registry, comments, tests, CHANGELOG) and `docs(benchmarks): section 5 on the whole-cohort basis` (report + archive + SKILL.md).
  </action>
  <verify>
    <automated>uv run python temp/261014-rux/derive_bands.py temp/261014-rux/run/chapter5.json --check && uv run pytest tests/services/test_flaw_delta_zones.py tests/services/test_flaw_comparison.py tests/services/test_tactic_delta_zones.py tests/scripts/test_chapter5_sql.py -q && test -f reports/benchmark/benchmarks-2026-10-12.md && head -1 reports/benchmark/benchmarks-latest.md | grep -q 2026-10-14 && grep -q "5.16" reports/benchmark/benchmarks-latest.md && grep -q "5.16" .claude/skills/benchmarks/SKILL.md</automated>
  </verify>
  <done>Registry entries equal the derived bands for every (metric or cell, TC) under the owner's rule; flaw and crossed lookups no longer go through ZONE_TC_FOR while the tactic registry is untouched; the pinned tests and the mutation check pass/bite; one truthful CHANGELOG bullet; the archived 2026-10-12 report exists verbatim and the latest report and SKILL.md describe the split basis, the parity fix, the crossed cells and the applied rule with this run's numbers.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| script -> benchmark DB (localhost:5433) | Offline, local, READ ONLY transaction; SQL text built from in-code constant sets only |
| client -> API (GET /api/library/flaw-comparison) | Unchanged: user-scoped query; this task only swaps the constant bands attached per TC |

## STRIDE Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation Plan |
|-----------|----------|-----------|----------|-------------|-----------------|
| T-261014-rux-01 | Tampering (integrity of displayed verdicts) | FLAW_DELTA_ZONES / TEMPO_PHASE_ZONES | low | mitigate | Bands derived mechanically from the run's chapter5.json by derive_bands.py; `--check` re-derives and compares against the imported registry; per-(key, TC) half-widths pinned in tests/services/test_flaw_delta_zones.py |
| T-261014-rux-02 | Tampering (SQL text) | scripts/benchmarks/chapter5.py query builders | low | mitigate | Every interpolated identifier comes from closed in-code sets (_FLAW_TAG_PREDICATES, FAMILY_TO_MOTIF_INTS, the Basis Literal); the run executes under SET TRANSACTION READ ONLY |
| T-261014-rux-03 | Information disclosure | benchmark report / chapter5.json | low | accept | Aggregate cohort statistics only, no user identifiers; chapter5.json stays in gitignored temp/ |
| T-261014-rux-SC | Tampering | npm/pip/cargo installs | low | accept | No package installs in this plan; any lockfile diff is a deviation to report |
</threat_model>

<verification>
- Task 1: SQL-shape test green with the parity mutation observed failing; one run's chapter5.md / chapter5.json / SNAPSHOT.txt in temp/261014-rux/run/; diff gate transcribed from it (offline check green) and the live gate run once.
- Task 2: owner answer recorded in temp/261014-rux/RULE and the SUMMARY.
- Task 3: derive_bands.py --check green; the four service/script test files green; ZONE_TC_FOR mutation observed failing; report archived + refreshed; SKILL.md updated.
- Final, before the squash-merge to main (CLAUDE.md pre-merge gate, run from the worktree root; in a fresh worktree first `uv sync --group maia-inference` and `(cd frontend && npm ci)`): `uv run ruff format app/ tests/ scripts/ analysis/`, `uv run ruff check . --fix`, `uv run ty check app/ tests/ scripts/`, `uv run --project analysis --with ty ty check analysis/`, `uv run python scripts/check_function_size.py app/ --fail-over-depth 4`, `uv run pytest -n auto -x`, `( cd frontend && npm run lint && npm run build && npm test -- --run && npm run knip )`. Commit any formatter change as `style(...)`.
</verification>

<success_criteria>
- Section 5 flaw metrics and the 9 crossed cells are measured on the whole cohort across all four TCs with the parity fix; tactics stay on the lane.
- The app serves each TC its own flaw and crossed-cell band wherever the owner's rule says split (one shared band elsewhere), all values traceable to one run's JSON.
- Diff gate, report section 5, SKILL.md and the registry all describe the same run and the same rule.
- Pre-merge gate green; work squash-merged to main.
</success_criteria>

<output>
Create `.planning/quick/261014-rux-benchmark-5-whole-cohort-basis-and-per-t/261014-rux-SUMMARY.md` when done, including: the snapshot timestamp and per-basis counts, the owner's rule and the resulting split / unsplit list, any tactic drift noted, the parity and ZONE_TC_FOR mutation-check results, live diff-gate outcome, and the gate results.
</output>
