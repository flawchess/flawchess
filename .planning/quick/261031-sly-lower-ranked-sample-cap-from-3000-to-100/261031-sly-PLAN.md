---
quick_id: 261031-sly
mode: quick
phase: quick-261031-sly
plan: 01
type: execute
wave: 1
depends_on: []
autonomous: true
requirements:
  - "todo:2026-10-31-ranked-sample-cap-1000"
files_modified:
  - app/services/canonical_slice_sql.py
  - tests/services/test_canonical_slice_sql.py
  - tests/scripts/fixtures/global_percentile_cdf/ (all 52 *.sql goldens, one mechanical substitution)
  - frontend/src/components/openings/stats/outOfOpeningCopy.ts
  - frontend/src/components/openings/stats/__tests__/OutOfOpeningPopover.test.tsx
  - scripts/recompute_capped_user_percentiles.py
  - tests/scripts/test_recompute_capped_user_percentiles.py
  - app/services/insights_llm.py
  - app/prompts/endgame_insights.md
  - tests/services/test_insights_llm.py
  - tests/prompts/test_endgame_insights_prompt.py
  - tests/routers/test_insights_openings.py
  - app/schemas/endgames.py
  - app/routers/openings.py
  - app/routers/endgames.py
  - app/services/endgame_ranked_service.py
  - app/models/user_rating_anchors.py
  - app/models/user_benchmark_percentile.py
  - frontend/src/components/endgames/EndgameStatsTab.tsx
  - frontend/src/types/endgames.ts
  - CHANGELOG.md

estimate:
  tokens: 90000
  raw_tokens: 90000
  tasks: 3
  confidence: low

must_haves:
  truths:
    - "The on-read ranked sample (Endgame Stats ranked stats, Out of the opening) takes at most the 1000 most recent canonical games per time control: ranked_games_sql and every per_user_cte_* builder emit `rn <= 1000`."
    - "The benchmark cohort CDF needs no rebuild: no deduped-cohort benchmark user has more than 1000 rated human games in any time control (planner baseline 2026-10-31: 0 user-TC pairs, max exactly 1000 in every TC)."
    - "After the dev recompute, no dev user_rating_anchors row pools more than 1000 games and no pool-count percentile row (time_pressure_score_gap, clock_gap, net_flag_rate, opening_worse_rate, opening_better_rate) has n_games above 1000 (planner baseline: 13 and 54)."
    - "A stage that captured an exception never prunes: recompute_user skips the stale-row delete (and Stage B) when Stage A recorded a failure, so a transient error cannot delete a user's percentiles."
    - "Every user-facing and LLM-facing statement of the cap says 1000 (UI shows 1,000), and the endgame insights cache is invalidated by endgame_v50."
    - "CHANGELOG.md [Unreleased] carries a user-facing bullet for the cap change."
  artifacts:
    - path: app/services/canonical_slice_sql.py
      provides: "RECENT_GAMES_PER_TC_CAP = 1000, the single source for the ranked window"
    - path: scripts/recompute_capped_user_percentiles.py
      provides: "One-off recompute of Stage A + Stage B for users whose ranked sample is capped, with stale-row pruning"
    - path: tests/scripts/test_recompute_capped_user_percentiles.py
      provides: "Selection, prune and skip-on-failure coverage for the recompute script"
  key_links:
    - from: frontend/src/components/openings/stats/outOfOpeningCopy.ts
      to: app/services/canonical_slice_sql.py
      via: "RECENT_GAMES_PER_TC_CAP mirror constant (must equal the backend value)"
    - from: scripts/recompute_capped_user_percentiles.py
      to: app/services/user_benchmark_percentiles_service.py
      via: "compute_stage_a / compute_stage_b with the session_maker kwarg"
    - from: scripts/recompute_capped_user_percentiles.py
      to: user_rating_anchors
      via: "stale anchors pruned AFTER Stage A and BEFORE Stage B, because Stage B reads anchors via fetch_anchors_for_user"
---

<objective>
Lower the ranked-sample cap `RECENT_GAMES_PER_TC_CAP` from 3000 to 1000 games per time control so the
user side of every peer-ranked metric (endgame ranked stats, out-of-opening worse/better) matches the
benchmark peers it is ranked against (the benchmark ingest stops at 1000 games per user per TC). Then
recompute the persisted per-user values that were computed on the old basis, and fix every copy,
prompt and docstring statement of the cap.

Purpose: an improving heavy player is currently ranked on up to 3x more (and older) games than their
peers. Spec: `.planning/todos/pending/2026-10-31-ranked-sample-cap-1000.md`.

Output: the constant change with refreshed SQL goldens, a one-off recompute script (run on dev here,
on prod by the operator after deploy), updated UI/LLM copy, an insights cache bump, a CHANGELOG bullet.

How persisted values get recomputed (planner finding, read from code): Stage A
(`compute_stage_a`: anchors + `score_gap` rows) and Stage B (`compute_stage_b`: the 10 eval-dependent
families + per-colour opening rows) are triggered only from `import_service._complete_import_job` and
the `eval_drain` zero-pending crossing. There is no version stamp or stale detection, and both stages
are upsert-only (rows a recompute no longer produces are never deleted). So a one-off script is needed,
and it must prune rows the new-basis run did not rewrite (for example a time-pressure cell that falls
below its 30-game floor on 1000 games).
</objective>

<execution_context>
@~/.claude/gsd-core/workflows/execute-plan.md
@~/.claude/gsd-core/templates/summary.md
</execution_context>

<context>
@.planning/todos/pending/2026-10-31-ranked-sample-cap-1000.md
@.planning/STATE.md
@CLAUDE.md
@frontend/CLAUDE.md

Grounded facts (planner, 2026-10-31, verify rather than trust):
- Constant: `app/services/canonical_slice_sql.py:122`; the only emitted-SQL use is `_recent_capped_per_tc_cte` (`WHERE g.rn <= {RECENT_GAMES_PER_TC_CAP}`). Simulated change: no other `<= 1000` literal exists in any builder, so the symbolic count asserts in `tests/services/test_canonical_slice_sql.py` (around :182, :359) and `tests/services/test_canonical_slice_per_user_vs_benchmark_parity.py` (:202) keep passing unchanged.
- Goldens that pin the old cap: `_BASELINE_PER_USER_CTE_MEDIAN_ANCHOR_RAPID_BENCHMARK` (`tests/services/test_canonical_slice_sql.py:74`), `_GOLDEN_BUILDER_SHA256` (:1183, simulated: 52 of 53 hashes change, only `selected_users:single_user` stays), and the 52 files in `tests/scripts/fixtures/global_percentile_cdf/` (two `rn <=` predicates each).
- The SHA golden's own comment says: after an intentional builder change, regenerate the percentiles, not just the hashes. Task 2 is that regeneration.
- Insights cache is already at `endgame_v49` (v49 added the summary field after the todo was written), so the bump is v49 to v50, not v48 to v49. Ten test sites pin `endgame_v49`.
- `RankedMetricPopover.tsx` contains no cap literal (it renders `metric.n`), so it needs no edit despite the todo listing it.
- Import `game_cap` (1000/3000/5000 in `user_import_settings`, `ImportFilterCard`, `useImportSettings`) is OUT OF SCOPE. `frontend/src/lib/gemMove.ts` mentions unrelated "3,000 positions": leave it.
- Dev affected users (canonical count above 1000 in some TC): ids 2, 8, 14, 28, 31, 46, 47 (13 user-TC pairs). Benchmark DB container `flawchess-benchmark-db-1` (port 5433) and dev DB `flawchess-dev-db-1` were both up.
</context>

<tasks>

<task type="tracer">
  <name>Task 1: Cap 1000 end to end on the on-read path (constant, SQL goldens, frontend mirror, CDF no-op proof)</name>
  <files>app/services/canonical_slice_sql.py, tests/services/test_canonical_slice_sql.py, tests/scripts/fixtures/global_percentile_cdf/*.sql (52 files), frontend/src/components/openings/stats/outOfOpeningCopy.ts, frontend/src/components/openings/stats/__tests__/OutOfOpeningPopover.test.tsx</files>
  <read_first>
    - app/services/canonical_slice_sql.py (lines 1-60, 110-160, 300-340, 895-910, 970-980, 1048-1058, 1170-1180, 1320-1332)
    - tests/services/test_canonical_slice_sql.py (lines 48-100 baseline string, 1166-1290 SHA golden and `_current_builder_sha256`)
    - tests/scripts/test_gen_global_percentile_cdf_unchanged.py (module docstring: fixture regeneration recipe)
    - frontend/src/components/openings/stats/outOfOpeningCopy.ts (lines 20-30, 75-82)
  </read_first>
  <action>
    1. In `app/services/canonical_slice_sql.py` set `RECENT_GAMES_PER_TC_CAP: int = 1000`. Add a two-line comment above it: the cap matches the benchmark ingest depth (at most 1000 games per user per TC), so the user basis and the peer basis are both "most recent 1000 games in the last 36 months"; lowered from 3000 on 2026-10-31. Update every docstring/comment in this file that states the old cap value so it says 1000: module docstring (:5 and :39), the median-anchor floor comment (:144), `_recent_capped_per_tc_cte` docstring (:318), the conversion/parity/recovery rate docstrings (:902, :975, :1053), `per_user_cte_median_anchor` docstring (:1174), and the LATERAL join note (:1327-1328) whose arithmetic becomes 1000 games x ~50 lookup rows, about 50K comparisons per user per TC. Docstrings are not part of the emitted SQL, so they do not affect the hashes.
    2. In `tests/services/test_canonical_slice_sql.py` change the cap in the `WHERE g.rn` line of `_BASELINE_PER_USER_CTE_MEDIAN_ANCHOR_RAPID_BENCHMARK` (:74) from 3000 to 1000. Regenerate `_GOLDEN_BUILDER_SHA256`: run `uv run python -c "import json; from tests.services.test_canonical_slice_sql import _current_builder_sha256 as f; print(json.dumps(f(), indent=4))"` AFTER step 1 and paste the new hex values into the dict (keys and order unchanged; expect exactly 52 values to change, `selected_users:single_user` unchanged). Append one line to the comment block above the dict: hashes refreshed 2026-10-31 for the 1000-game cap, persisted percentiles regenerated by `scripts/recompute_capped_user_percentiles.py`.
    3. Rewrite the 52 benchmark-side SQL goldens with one mechanical substitution of the cap inside the `rn <=` predicate (3000 becomes 1000), for example `sed -i 's/rn <= 3000/rn <= 1000/g'` over `tests/scripts/fixtures/global_percentile_cdf/*.sql`. Do not hand-edit anything else in those files; `test_gen_global_percentile_cdf_unchanged.py` proves the result is byte-identical to a regeneration.
    4. Frontend mirror: in `outOfOpeningCopy.ts` set the `RECENT_GAMES_PER_TC_CAP` mirror constant to 1000. In `OutOfOpeningPopover.test.tsx` (:122) update the expected disclosure substring to the new formatted number (1,000); the rest of the sentence is unchanged.
    5. CDF no-op proof (data check, not code): run the benchmark query in the verify block. It counts, over the benchmark cohort (users joined to `benchmark_selected_users` by lower-cased lichess username), the (user, TC) pairs with more than 1000 rated non-computer games, with no recency or Elo filter, which is a strict upper bound on the canonical slice. Expected `0` (planner baseline 2026-10-31: 0, max exactly 1000 per TC). If the container is down, start it with `bin/benchmark_db.sh start`; if it still cannot be reached, record the check as pending for the orchestrator in the SUMMARY. If the result is above 0, do NOT regenerate the CDF in this task: finish the code changes, then report the count as a blocker in the SUMMARY (a CDF rebuild via `scripts/gen_global_percentile_cdf.py` + `seed_cohort_cdf.py` is a separate decision).
    Commit on `main` (confirm `git branch --show-current` prints `main` first): `feat(quick-261031-sly): lower the ranked-sample cap to 1000 games per time control`.
  </action>
  <verify>
    <automated>uv run pytest tests/services/test_canonical_slice_sql.py tests/services/test_canonical_slice_per_user_vs_benchmark_parity.py tests/scripts/test_gen_global_percentile_cdf_unchanged.py -q -x</automated>
    <automated>npm --prefix frontend test -- src/components/openings/stats/__tests__/OutOfOpeningPopover.test.tsx</automated>
    <automated>! grep -nE '(recent-|recent |~|<= |up to |at most )3,?000|3000(-cap| games| per)|CAP(: int)? = 3000' app/services/canonical_slice_sql.py frontend/src/components/openings/stats/outOfOpeningCopy.ts frontend/src/components/openings/stats/__tests__/OutOfOpeningPopover.test.tsx   # baseline at HEAD: 13 matching lines</automated>
    <automated>test "$(grep -rl 'rn <= 1000' tests/scripts/fixtures/global_percentile_cdf | wc -l)" -eq 52 &amp;&amp; test "$(grep -rl 'rn <= 3000' tests/scripts/fixtures/global_percentile_cdf | wc -l)" -eq 0</automated>
    <automated>test "$(docker compose -f docker-compose.benchmark.yml -p flawchess-benchmark exec -T db psql -U postgres -d flawchess_benchmark -At -c "SELECT count(*) FROM (SELECT g.user_id, g.time_control_bucket FROM games g WHERE g.user_id IN (SELECT u.id FROM users u JOIN benchmark_selected_users bsu ON lower(bsu.lichess_username) = lower(u.lichess_username)) AND g.rated AND NOT g.is_computer_game GROUP BY g.user_id, g.time_control_bucket HAVING count(*) > 1000) x")" = "0"</automated>
  </verify>
  <done>Constant is 1000; all three SQL golden sets pass against the new cap; the out-of-opening disclosure renders "1,000"; the benchmark check returned 0 (or its result is recorded in the SUMMARY); one commit on main.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Recompute script for persisted percentiles and anchors, tested, run on dev</name>
  <files>scripts/recompute_capped_user_percentiles.py, tests/scripts/test_recompute_capped_user_percentiles.py</files>
  <read_first>
    - app/services/user_benchmark_percentiles_service.py (lines 1-75 docstring, 130-160 STAGE_A_METRIC / STAGE_B_METRIC_FAMILIES, 421-670 per-cell upsert, compute_stage_a, compute_stage_b)
    - app/repositories/user_benchmark_percentiles_repository.py (lines 95-130: upsert refreshes computed_at with func.now())
    - app/repositories/user_rating_anchors_repository.py (lines 95-120: same for anchors)
    - app/models/user_rating_anchors.py and app/models/user_benchmark_percentile.py (columns; both tables have computed_at)
    - scripts/fix_lichess_eval_provenance.py (lines 44-65 bootstrap and DbTarget, 244-300 _confirm_prod / _parse_args / _run: the conventions to copy)
    - tests/scripts/test_fix_lichess_eval_provenance.py (db_session usage, ensure_test_user, Game seeding)
  </read_first>
  <behavior>
    - select_affected_users(session, cap=3): a user with 4 qualifying blitz games is returned; a user with 3 qualifying blitz games plus 1 unrated, 1 against an opponent 200 Elo away and 1 played 37 months ago is NOT returned (proves the predicate mirrors the canonical slice); a user with no games but a user_rating_anchors row pooling 5 games is returned (persisted branch). Assert membership only, never list equality (the test DB may hold other committed users).
    - prune_stale_stage_a(session, user_id, since): deletes that user's user_rating_anchors rows and metric = score_gap percentile rows whose computed_at is before since; keeps the user's fresh rows, keeps the user's Stage-B rows even when stale, keeps other users' stale rows; returns the number of rows deleted.
    - prune_stale_stage_b(session, user_id, since): deletes that user's non-score_gap percentile rows (including white/black opening rows) older than since; keeps score_gap rows, fresh rows and other users' rows; returns the count.
    - recompute_user with Stage A replaced by a fake that calls sentry_sdk.capture_exception inside capture_failures(): neither prune function runs, Stage B is not called, the outcome reports stage_a_ok False.
    - recompute_user happy path with fakes and spies: call order is Stage A, prune A, Stage B, prune B; outcome reports both stages ok with the prune counts.
  </behavior>
  <action>
    Create `scripts/recompute_capped_user_percentiles.py`, following the conventions of `scripts/fix_lichess_eval_provenance.py` (sys.path bootstrap, `db_url_for_target`, `create_async_engine` + `async_sessionmaker(engine, expire_on_commit=False)`, engine disposed in `finally`, `asyncio.run(main)`), with full type hints (ty runs on scripts/). Module docstring: WHY (cap lowered 2026-10-31; Stage A/B are upsert-only and rerun only at import completion and the eval-drain zero-pending crossing, so heavy users keep rows computed on the old basis, and cells that fall below a floor on the new basis would never be deleted), WHEN (on prod run it AFTER the deploy that ships the new cap: the pre-deploy app would overwrite rows on the old cap at the next import or eval drain), and usage lines for dev and for prod behind `bin/prod_db_tunnel.sh`.
    Public functions (names fixed, the tests import them):
    - `select_affected_users(session, *, cap: int = RECENT_GAMES_PER_TC_CAP) -> list[int]`: sorted distinct user ids from the union of (a) users with more than `cap` games in some non-null `time_control_bucket` under the canonical slice predicate copied from `_recent_capped_per_tc_cte`: `rated`, `NOT is_computer_game`, both ratings not null, `played_at >= NOW() - INTERVAL '{RECENCY_WINDOW_MONTHS} months'`, and `equal_footing_filter_sql()` (import both from `canonical_slice_sql`; interpolate only the int constant and that helper's output, bind `cap` as a parameter); and (b) users with a `user_rating_anchors` row where `n_chesscom_games + n_lichess_games > cap` (rows computed on the old basis whose count has since drifted). No guest filter: guest rows are persisted the same way.
    - `prune_stale_stage_a(session, *, user_id: int, since: datetime) -> int` and `prune_stale_stage_b(session, *, user_id: int, since: datetime) -> int` with the semantics in the behavior block. Use `STAGE_A_METRIC` from the service as a bound parameter, never a string literal. They do not commit; the caller does.
    - `capture_failures()`: a context manager that patches `sentry_sdk.capture_exception` (for example `unittest.mock.patch.object(sentry_sdk, "capture_exception", new=recorder)`) with a recorder that appends a small record (exception type name and message) to a list it yields, and prints the traceback to stderr. Reason, to state in a comment: Sentry is not initialised in a script, and Stage A/B swallow every exception after calling `sentry_sdk.capture_exception`, so without the hook a failed recompute is invisible.
    - `recompute_user(maker, user_id: int, failures: list[...]) -> UserOutcome` (a small dataclass: user_id, stage_a_ok, stage_b_ok, pruned_a, pruned_b). Steps: read `since` with `SELECT now()` in its own session (its transaction ends before Stage A starts, so every row Stage A/B upserts gets a later `computed_at`); `await compute_stage_a(user_id, session_maker=maker)`; if the failure list grew, return without pruning and without Stage B (Stage B would rank against stale anchors); otherwise prune A in a fresh session and commit; THEN `await compute_stage_b(user_id, session_maker=maker)` (order matters: Stage B reads anchors, so a stale anchor must be gone first); prune B only if Stage B recorded no new failure.
    CLI: `--db {dev,prod}` required; default is a dry run that prints the affected count and ids and writes nothing; `--execute` runs `recompute_user` for each id sequentially inside one `capture_failures()` block and prints one progress line per user with `flush=True`; `--yes` skips the prod confirmation, which otherwise asks the operator to type `prod` (copy `_confirm_prod`). Finish with a summary (users processed, rows pruned, failed user ids) and exit with status 1 if any user failed, 0 otherwise. Re-running is safe (upserts plus prune).
    Write `tests/scripts/test_recompute_capped_user_percentiles.py` first (RED), covering every behavior bullet. DB tests run in the rolled-back `db_session` with `ensure_test_user`; reserve user ids 99671-99673 for this module (planner checked they are unused). Seed percentile and anchor rows with explicit `computed_at` values (stale = since minus 1 day, fresh = since plus 1 minute). The two `recompute_user` tests need no DB: monkeypatch the script module's `compute_stage_a`, `compute_stage_b`, `prune_stale_stage_a`, `prune_stale_stage_b` and the `since` reader, and pass a dummy maker. Mutation check (memory: prove a guard by reverting it): temporarily delete the early return after a failed Stage A, confirm the failure test goes red, restore it.
    Then run on DEV only (never reset the dev DB): dry run, then `--execute`. Expect about 7 affected users (2, 8, 14, 28, 31, 46, 47) and exit status 0. Do NOT run against prod; the prod run is an operator step for the SUMMARY.
    Commit on `main`: `feat(quick-261031-sly): recompute script for capped user percentiles`.
  </action>
  <verify>
    <automated>uv run pytest tests/scripts/test_recompute_capped_user_percentiles.py -q -x</automated>
    <automated>uv run ruff check scripts/recompute_capped_user_percentiles.py tests/scripts/test_recompute_capped_user_percentiles.py &amp;&amp; uv run ty check scripts/recompute_capped_user_percentiles.py tests/scripts/test_recompute_capped_user_percentiles.py</automated>
    <automated>uv run python scripts/recompute_capped_user_percentiles.py --db dev &amp;&amp; uv run python scripts/recompute_capped_user_percentiles.py --db dev --execute</automated>
    <automated>test "$(docker compose -f docker-compose.dev.yml -p flawchess-dev exec -T db psql -U postgres -d flawchess -At -c "SELECT (SELECT count(*) FROM user_rating_anchors WHERE n_chesscom_games + n_lichess_games > 1000) + (SELECT count(*) FROM user_benchmark_percentiles WHERE metric IN ('time_pressure_score_gap','clock_gap','net_flag_rate','opening_worse_rate','opening_better_rate') AND n_games > 1000)")" = "0"   # baseline before the run: 13 + 54</automated>
  </verify>
  <done>All behavior tests pass and the failure-skip test was shown to bite; ruff and ty are clean on both files; the dev dry run lists the affected users; the dev execute run exits 0; the dev DB has no anchor or pool-count percentile row above 1000 games; one commit on main.</done>
</task>

<task type="auto">
  <name>Task 3: Copy, prompt, docstrings, insights cache bump, CHANGELOG, then the backend suite</name>
  <files>app/services/insights_llm.py, app/prompts/endgame_insights.md, tests/services/test_insights_llm.py, tests/prompts/test_endgame_insights_prompt.py, tests/routers/test_insights_openings.py, app/schemas/endgames.py, app/routers/openings.py, app/routers/endgames.py, app/services/endgame_ranked_service.py, app/models/user_rating_anchors.py, app/models/user_benchmark_percentile.py, frontend/src/components/endgames/EndgameStatsTab.tsx, frontend/src/types/endgames.ts, CHANGELOG.md</files>
  <read_first>
    - app/services/insights_llm.py (lines 99-107)
    - app/prompts/endgame_insights.md (line 161)
    - frontend/src/components/endgames/EndgameStatsTab.tsx (lines 48-56)
    - CHANGELOG.md (lines 1-40, the [Unreleased] section)
  </read_first>
  <action>
    All edits below are one-line copy or comment changes; each replaces the stated cap value with 1000 and changes nothing else.
    1. Insights cache: in `app/services/insights_llm.py` set `_PROMPT_VERSION = "endgame_v50"` and add a `# v50:` line directly above the existing v49 line (ranked sample now capped at 1000 games per TC and the prompt's basis sentence updated; bumping invalidates every v49 cache row). Leave the v48 history line as is: it records what v48 meant. Replace `endgame_v49` with `endgame_v50` at all ten test sites (`grep -rl endgame_v49 tests` lists them: tests/services/test_insights_llm.py, tests/prompts/test_endgame_insights_prompt.py, tests/routers/test_insights_openings.py) and update the docstring at tests/services/test_insights_llm.py:414 to read "(v48 ranked sample + v49 summary + v50 1000-game cap)".
    2. Prompt: `app/prompts/endgame_insights.md:161`, the peer-rank basis in the "Preferred signal rule" paragraph becomes "the most recent ~1000 games per TC".
    3. Docstrings and comments stating the cap: `app/schemas/endgames.py:417`, `app/routers/openings.py:81`, `app/routers/endgames.py:39`, `app/services/endgame_ranked_service.py:6`, `app/models/user_rating_anchors.py:6`, `app/models/user_benchmark_percentile.py:96` and `:100`. No Alembic migration: model docstrings are not schema.
    4. Frontend: in `EndgameStatsTab.tsx:52` the "Your ranked games" paragraph says "up to 1,000 games per time control" (comma form, matching the out-of-opening disclosure); `frontend/src/types/endgames.ts:254` comment says 1000. Do not touch `RankedMetricPopover.tsx` (no cap literal) or anything import-related (`game_cap` is out of scope).
    5. CHANGELOG.md: under `## [Unreleased]` / `### Changed`, add one bullet in plain user language, no em-dash, along the lines of: peer rankings on Endgame Stats and in "Out of the opening" now use your most recent 1,000 games per time control (was 3,000), the same depth as the benchmarked players you are compared with, so recent improvement shows up sooner.
    6. Gates (direct main commit, so not the full pre-merge gate, but the suite runs once because the constant feeds many queries): `uv run ruff format app/ tests/ scripts/`, `uv run ruff check . --fix`, `uv run ty check app/ tests/ scripts/`, `uv run python scripts/check_function_size.py app/ --fail-over-depth 4`, then `uv run pytest -n auto -x`. Frontend: lint, build (tsc -b catches nothing here but the constraint asks for it), and the two touched test files. If a formatter or autofix changes files, include them in this commit.
    Commit on `main`: `chore(quick-261031-sly): cap copy, insights cache v50, changelog`.
  </action>
  <verify>
    <automated>test "$(grep -rnE '(recent-|recent |~|<= |up to |at most )3,?000|3000(-cap| games| per)|CAP(: int)? = 3000' app frontend/src --exclude-dir=node_modules --exclude-dir=data | grep -v '# v48:' | wc -l)" -eq 0   # baseline at HEAD: 23</automated>
    <automated>test "$(grep -rl endgame_v49 tests app | wc -l)" -eq 0 &amp;&amp; grep -q '_PROMPT_VERSION = "endgame_v50"' app/services/insights_llm.py</automated>
    <automated>uv run pytest tests/services/test_insights_llm.py tests/prompts/test_endgame_insights_prompt.py tests/routers/test_insights_openings.py -q -x</automated>
    <automated>npm --prefix frontend run lint &amp;&amp; npm --prefix frontend run build &amp;&amp; npm --prefix frontend test -- src/components/endgames/EndgameStatsTab.test.tsx src/components/openings/stats/__tests__/OutOfOpeningPopover.test.tsx</automated>
    <automated>uv run ruff format --check app/ tests/ scripts/ &amp;&amp; uv run ruff check . &amp;&amp; uv run ty check app/ tests/ scripts/ &amp;&amp; uv run python scripts/check_function_size.py app/ --fail-over-depth 4 &amp;&amp; uv run pytest -n auto -x</automated>
  </verify>
  <done>No statement of the old ranked cap remains in app/ or frontend/src (the v48 history comment excepted); prompt version is endgame_v50 with all test pins updated; the CHANGELOG bullet exists; ruff, ty, the nesting gate, the full backend suite and the frontend lint/build/targeted tests pass; one commit on main.</done>
</task>

</tasks>

<source_audit>
| Source item (todo scope) | Covered by |
|---|---|
| Backend constant to 1000 | Task 1 |
| Frontend mirror constant | Task 1 |
| Peer CDFs need no rebuild, verified | Task 1 step 5 (benchmark query; planner baseline 0) |
| Recompute Stage B and user_rating_anchors for affected users | Task 2 (Stage A is included because it owns the anchors and the score_gap rows) |
| Insights cache bump | Task 3 (v49 to v50; the todo's v48 to v49 predates the v49 summary bump) |
| endgame_insights.md "~N games per TC" | Task 3 |
| Copy: EndgameStatsTab, out-of-opening disclosure | Task 3, Task 1 |
| Copy: RankedMetricPopover | No edit needed: verified it has no cap literal |
| Docstrings (canonical_slice_sql, endgame_ranked_service, routers, models, schemas) | Task 1 (canonical_slice_sql), Task 3 (rest) |
| Tests that pin 3000 | Task 1 (SQL goldens, popover test) |
| Out of scope: import game_cap | Untouched (stated in Task 3) |
</source_audit>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| operator CLI to prod DB | `recompute_capped_user_percentiles.py --db prod --execute` deletes and rewrites persisted per-user rows over the SSH tunnel |
| script to app services | the script reuses `compute_stage_a` / `compute_stage_b`, which swallow exceptions |

## STRIDE Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation Plan |
|-----------|----------|-----------|----------|-------------|-----------------|
| T-261031-sly-01 | Tampering | recompute script target selection | high | mitigate | `--db` is required with choices dev/prod only; default is a write-free dry run; `--execute` against prod requires typing `prod` unless `--yes`; URLs come from `db_url_for_target` |
| T-261031-sly-02 | Tampering | stale-row prune after a failed recompute | high | mitigate | `capture_failures()` records every swallowed exception; a stage with a recorded failure never prunes, and Stage B never runs after a failed Stage A; covered by the skip-on-failure test plus a mutation check |
| T-261031-sly-03 | Tampering | race with a concurrent app Stage B whose transaction began before `since` | low | accept | can only drop rows that the next import or eval drain rewrites; re-running the script repairs it; window is about one second per user |
| T-261031-sly-04 | Denial of service | prod DB load during the recompute | low | accept | users are processed sequentially through the existing percentile semaphore; roughly 186 user-TC pairs on prod |
| T-261031-sly-05 | Information disclosure | script output | low | accept | prints user ids and counts only, no emails or game data |
| T-261031-sly-SC | Tampering | npm/pip/cargo installs | high | accept | this plan installs no packages |
</threat_model>

<verification>
- `rn <= 1000` is the only cap predicate in emitted canonical SQL; all three golden suites pass.
- Benchmark cohort: 0 (user, TC) pairs above 1000 rated human games, so `app/data/cohort_cdf.tsv` stays valid.
- Dev DB after the recompute: 0 anchors pooling above 1000 games, 0 pool-count percentile rows above 1000.
- No old-cap statement left in app/ or frontend/src outside the v48 history comment; prompt version endgame_v50.
- Full backend suite (`uv run pytest -n auto -x`) green; frontend lint, build and targeted tests green.
</verification>

<success_criteria>
- Ranked metrics for users with more than 1000 games in a TC are computed on, and ranked from, their most recent 1000 games, both on read and in persisted rows (dev verified; prod after the operator run).
- Users with at most 1000 games in every TC are unaffected (cap does not bind; their rows are not touched).
- The SUMMARY lists the post-deploy operator step: `bin/prod_db_tunnel.sh`, then `uv run python scripts/recompute_capped_user_percentiles.py --db prod` (dry run, expect roughly 120-190 users), then the same with `--execute`, run only after the release containing this change is live on flawchess.com; plus the suggestion to move the script to `scripts/archive/` afterwards.
</success_criteria>

<output>
Create `.planning/quick/261031-sly-lower-ranked-sample-cap-from-3000-to-100/261031-sly-SUMMARY.md` when done. Include: the benchmark check result, the dev affected-user count and the recompute summary line, any failed user ids, and the prod operator step from the success criteria.
</output>
