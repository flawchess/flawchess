---
phase: quick-260529-cum
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - app/services/canonical_slice_sql.py
  - tests/scripts/fixtures/global_percentile_cdf/
  - CHANGELOG.md
autonomous: true
requirements: [PERF-percentile-cte]

must_haves:
  truths:
    - "The 3 time-pressure per-TC builders (time_pressure_score_gap, clock_gap, net_flag_rate) scope endgame-entry-clock aggregation to recent_capped games"
    - "per_user_cte_score_gap_tc scopes its endgame_game_ids CTE to recent_capped games"
    - "per_user_cte_achievable_tc scopes its endgame_game_ids CTE to recent_capped games (entry_rows inherits via existing JOIN)"
    - "per_user_cte_score_gap_bucket_tc is left byte-identical (already scoped via spans JOIN recent_capped)"
    - "The 32 SQL-snapshot fixtures are regenerated; only the score_gap / achievable_score_gap / time_pressure_score_gap / clock_gap / net_flag_rate cells drift; the conv/parity/recovery bucket fixtures do NOT change"
    - "tests/scripts/test_gen_global_percentile_cdf_unchanged.py passes against the regenerated goldens"
    - "Each edit site carries an inline comment explaining why scoping to recent_capped is result-equivalent"
  artifacts:
    - path: "app/services/canonical_slice_sql.py"
      provides: "Three scoping edits + rationale comments"
      contains: "JOIN recent_capped rc ON rc.id = gp.game_id"
    - path: "CHANGELOG.md"
      provides: "Unreleased Fixed/Changed bullet for the percentile-compute query optimization"
  key_links:
    - from: "_endgame_entry_clocks_cte"
      to: "recent_capped"
      via: "JOIN rc.id = gp.game_id"
      pattern: "JOIN recent_capped rc ON rc.id = gp.game_id"
    - from: "per_user_cte_score_gap_tc.endgame_game_ids"
      to: "recent_capped"
      via: "game_id IN (SELECT id FROM recent_capped)"
      pattern: "IN \\(SELECT id FROM recent_capped\\)"
---

<objective>
Scope the `game_positions` aggregation in the benchmark-percentile CTE family to the
single selected user's recent games instead of aggregating the entire table globally
and discarding nearly all of it. Confirmed performance issue: a /db-report flagged the
CTE family at ~6s/call, ~58 min cumulative server time on prod. The single-user hot path
(`compute_stage_a`/`compute_stage_b`, run on every import + eval-drain completion) renders
`selected_users AS (SELECT CAST(:user_id AS int) AS user_id)`, so only one user's ≤3000
recent games survive the downstream join — yet 5 of 6 per-TC metric builders scan all
users' positions before that join.

Purpose: Cut percentile-compute query time without changing any output value. The fix is
**result-equivalent**, not just faster (see rationale below — recorded as code comments).
Output: Three scoping edits in `app/services/canonical_slice_sql.py`, regenerated SQL
fixtures, and a CHANGELOG entry.

Result-equivalence rationale (record at each edit site as a code comment per CLAUDE.md
bug/non-obvious-code comment rule):
- Only games in `recent_capped` survive the downstream joins
  (`scored LEFT JOIN endgame_game_ids ON eg.game_id = rc.id`;
  `joined JOIN endgame_entry_clocks ee ON ee.game_id = rc.id`;
  `entry_rows JOIN ... er.game_id = rc.id`). Restricting the aggregated set to
  `recent_capped`'s games changes nothing in the output.
- `HAVING count >= 6` is per-game over that game's full position set; filtering by game_id
  MEMBERSHIP (not by row) keeps every row of each retained game, so the count and the
  `array_agg(first clock)` values are byte-identical for surviving games.
- Shared-path safety: these builders are also used by the offline benchmark CDF script
  (`scripts/gen_global_percentile_cdf.py`, `source="benchmark"`) where `selected_users`
  is the whole cohort. The fix is still correct there because `recent_capped` derives from
  `selected_users` regardless of source.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@app/services/canonical_slice_sql.py
@tests/scripts/test_gen_global_percentile_cdf_unchanged.py

Key facts already confirmed by code read:
- `_endgame_entry_clocks_cte()` (lines 591-602) has NO `recent_capped` join — it
  aggregates `game_positions` globally. It is the shared helper for all THREE
  time-pressure builders (`per_user_cte_time_pressure_score_gap`,
  `per_user_cte_clock_gap`, `per_user_cte_net_flag_rate`), each of which prepends
  `_recent_capped_per_tc_cte(...)` immediately before it in the WITH chain — so
  `recent_capped` is ALWAYS in scope. One edit fixes all three.
- `per_user_cte_score_gap_tc` `endgame_game_ids` CTE (lines 858-862) scans
  `game_positions` globally; `recent_capped` is in scope.
- `per_user_cte_achievable_tc` `endgame_game_ids` CTE (lines 916-920) scans globally;
  `recent_capped` is in scope. Its `entry_rows` CTE already JOINs `endgame_game_ids`
  so it inherits the scoping automatically — NO separate edit to `entry_rows`.
- `per_user_cte_score_gap_bucket_tc` `spans` CTE (lines 1005-1009) ALREADY does
  `JOIN recent_capped rc ON rc.id = gp.game_id`. This is the proof pattern.
  LEAVE IT EXACTLY AS-IS — out of scope.
- The non-per-TC builders (`per_user_cte_score_gap`, `per_user_cte_achievable`) are
  NOT in the prod single-user hot path described by /db-report. The task scope names
  only the per-TC `_tc` builders and the shared `_endgame_entry_clocks_cte` helper.
  Do NOT touch `per_user_cte_score_gap` / `per_user_cte_achievable` (the non-`_tc`
  builders at lines 320-451) — they are out of scope for this quick task.
</context>

<tasks>

<task type="auto">
  <name>Task 1: Scope the three game_positions aggregations to recent_capped, with rationale comments</name>
  <files>app/services/canonical_slice_sql.py</files>
  <action>
Make exactly these three edits. Each gets a short inline SQL comment (per CLAUDE.md
non-obvious-code comment rule) explaining that scoping to recent_capped is
result-equivalent because only recent_capped games survive the downstream join and the
per-game `HAVING count >= 6` is unaffected by game_id membership filtering.

EDIT 1 — `_endgame_entry_clocks_cte()` (currently lines 591-602). Add a join to
`recent_capped` so only the selected user's recent games are aggregated. Change the FROM
to `FROM game_positions gp JOIN recent_capped rc ON rc.id = gp.game_id`, keeping the
existing `WHERE gp.endgame_class IS NOT NULL`, `GROUP BY gp.game_id`, and
`HAVING count(gp.ply) >= 6` unchanged. Add an inline `-- ` SQL comment above or beside
the JOIN noting `recent_capped` is always prepended by all 3 callers
(`_recent_capped_per_tc_cte`) and the join is result-equivalent. Also update the
function docstring's existing prose minimally if needed to mention the scoping (do not
over-edit). This single edit fixes all three time-pressure builders.

EDIT 2 — `per_user_cte_score_gap_tc` `endgame_game_ids` CTE (currently lines 858-862).
Add `AND game_id IN (SELECT id FROM recent_capped)` to the WHERE so:
  SELECT game_id FROM game_positions
  WHERE endgame_class IS NOT NULL AND game_id IN (SELECT id FROM recent_capped)
  GROUP BY game_id HAVING count(*) >= 6
Add the result-equivalence comment.

EDIT 3 — `per_user_cte_achievable_tc` `endgame_game_ids` CTE (currently lines 916-920).
Apply the IDENTICAL `AND game_id IN (SELECT id FROM recent_capped)` predicate as EDIT 2.
Add the result-equivalence comment. Do NOT modify its `entry_rows` CTE — it JOINs
`endgame_game_ids` and inherits the scoping automatically.

DO NOT TOUCH `per_user_cte_score_gap_bucket_tc` (its `spans` CTE already joins
recent_capped — it is the proof pattern). DO NOT TOUCH the non-`_tc` builders
`per_user_cte_score_gap` / `per_user_cte_achievable`.

Keep the SQL string formatting consistent with the surrounding f-strings (2-space CTE
indentation). No magic numbers introduced (the `6` is the existing per-game endgame-ply
threshold, left verbatim).
  </action>
  <verify>
    <automated>grep -c "JOIN recent_capped rc ON rc.id = gp.game_id" app/services/canonical_slice_sql.py</automated>
  </verify>
  <done>
`_endgame_entry_clocks_cte` joins `recent_capped`; both `per_user_cte_score_gap_tc` and
`per_user_cte_achievable_tc` `endgame_game_ids` CTEs carry the
`AND game_id IN (SELECT id FROM recent_capped)` predicate; each edit site has an inline
result-equivalence comment; `per_user_cte_score_gap_bucket_tc` and the non-`_tc` builders
are unchanged.
  </done>
</task>

<task type="auto">
  <name>Task 2: Regenerate SQL fixtures and confirm only the expected cells drifted</name>
  <files>tests/scripts/fixtures/global_percentile_cdf/</files>
  <action>
Run the regen snippet documented verbatim in the module docstring of
`tests/scripts/test_gen_global_percentile_cdf_unchanged.py` (the inline
`uv run python - <<'PY' ... PY` heredoc that imports `IN_SCOPE_METRICS`,
`ALL_TIME_CONTROLS`, `_build_per_user_with_anchor_query` from
`scripts.gen_global_percentile_cdf`, clears `*.sql`, and rewrites every
`{metric}__{tc}.sql` with `snapshot_date=date(2026, 5, 26)`). It is pure SQL-string
generation — NO database required.

Then run `git diff --stat tests/scripts/fixtures/global_percentile_cdf/` and confirm the
drift is confined to the expected cells:
  - score_gap__{tc}, achievable_score_gap__{tc}, time_pressure_score_gap__{tc},
    clock_gap__{tc}, net_flag_rate__{tc} (their respective TCs) MAY change.
  - score_gap_conv__{tc}, score_gap_parity__{tc}, score_gap_recovery__{tc} (the untouched
    bucket builder) MUST NOT change.
If any conv/parity/recovery bucket fixture changed, the edits touched the wrong builder —
stop and revert. If a metric that should have drifted did not, the edit did not take —
stop and inspect.
  </action>
  <verify>
    <automated>git -C /home/aimfeld/Projects/Python/flawchess diff --stat tests/scripts/fixtures/global_percentile_cdf/ | grep -E 'score_gap_(conv|parity|recovery)' && echo "UNEXPECTED bucket drift" && exit 1 || echo "bucket fixtures unchanged (OK)"</automated>
  </verify>
  <done>
Fixtures regenerated; `git diff --stat` shows drift ONLY in score_gap / achievable_score_gap /
time_pressure_score_gap / clock_gap / net_flag_rate cells; the conv/parity/recovery bucket
fixtures are unchanged.
  </done>
</task>

<task type="auto">
  <name>Task 3: CHANGELOG entry + full pre-PR checklist gate</name>
  <files>CHANGELOG.md</files>
  <action>
Add one terse, user/ops-facing bullet under `## [Unreleased]` → `### Fixed` (create the
subsection if absent, else append; `### Changed` is also acceptable if the existing
section structure makes it the better fit) referencing the percentile-compute query
optimization. Keep it terse and avoid em-dashes (CLAUDE.md style). Example tone:
"Optimized benchmark-percentile compute queries to scan only the selected user's recent
games (was scanning the full game_positions table), cutting per-call time on the
import/eval-drain hot path."

Then run the full pre-PR checklist from CLAUDE.md and resolve all output before declaring
done (the dev DB must be running for pytest:
`docker compose -f docker-compose.dev.yml -p flawchess-dev up -d`):
  - `uv run ruff format app/ tests/`
  - `uv run ruff check app/ tests/ --fix`
  - `uv run ty check app/ tests/`  (zero errors)
  - `uv run pytest -x`  — pay special attention to
    `tests/services/test_canonical_slice_sql.py`,
    `tests/services/test_canonical_slice_per_user_vs_benchmark_parity.py`, and the fixture
    canary `tests/scripts/test_gen_global_percentile_cdf_unchanged.py` (these directly
    cover the edited SQL). The parity test (single_user vs benchmark) is the strongest
    proof of result-equivalence — it must stay green.
If ruff format/fix modifies any file, that is expected; the commit will include it.
  </action>
  <verify>
    <automated>cd /home/aimfeld/Projects/Python/flawchess && uv run ruff format --check app/ tests/ && uv run ruff check app/ tests/ && uv run ty check app/ tests/ && uv run pytest tests/scripts/test_gen_global_percentile_cdf_unchanged.py tests/services/test_canonical_slice_sql.py tests/services/test_canonical_slice_per_user_vs_benchmark_parity.py -x</automated>
  </verify>
  <done>
CHANGELOG.md has an Unreleased Fixed/Changed bullet for the optimization; ruff format
(check), ruff check, ty check (zero errors), and the targeted pytest suite all pass; the
full `uv run pytest -x` run is green.
  </done>
</task>

</tasks>

<verification>
- `grep -n "JOIN recent_capped rc ON rc.id = gp.game_id" app/services/canonical_slice_sql.py`
  shows the helper join in `_endgame_entry_clocks_cte` (in addition to the pre-existing
  `spans` join in `per_user_cte_score_gap_bucket_tc`).
- `grep -n "IN (SELECT id FROM recent_capped)" app/services/canonical_slice_sql.py` shows
  exactly two matches (score_gap_tc + achievable_tc `endgame_game_ids`).
- `git diff --stat tests/scripts/fixtures/global_percentile_cdf/` shows no change to any
  `score_gap_conv/parity/recovery` fixture.
- `uv run pytest tests/scripts/test_gen_global_percentile_cdf_unchanged.py` passes.
- `uv run pytest tests/services/test_canonical_slice_per_user_vs_benchmark_parity.py`
  passes (result-equivalence proof).
- Full pre-PR checklist green (ruff format/check, ty, pytest -x).
</verification>

<success_criteria>
- Three scoping edits applied, each with an inline result-equivalence comment.
- `per_user_cte_score_gap_bucket_tc` and the non-`_tc` builders untouched.
- Fixtures regenerated; drift confined to the expected metric cells.
- CHANGELOG bullet added.
- Entire pre-PR checklist passes against the existing dev DB (no DB reset).
</success_criteria>

<output>
Create `.planning/quick/260529-cum-scope-game-positions-aggregation-to-sele/260529-cum-SUMMARY.md` when done
</output>
