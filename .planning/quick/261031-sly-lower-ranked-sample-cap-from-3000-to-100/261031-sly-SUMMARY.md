---
quick_id: 261031-sly
phase: quick-261031-sly
plan: 01
status: complete
subsystem: ranked-sample / persisted percentiles
tags: [canonical-slice, percentiles, insights-cache, one-off-script]
requirements: ["todo:2026-10-31-ranked-sample-cap-1000"]
key-files:
  created:
    - scripts/recompute_capped_user_percentiles.py
    - tests/scripts/test_recompute_capped_user_percentiles.py
  modified:
    - app/services/canonical_slice_sql.py
    - tests/services/test_canonical_slice_sql.py
    - tests/scripts/fixtures/global_percentile_cdf/ (52 goldens)
    - frontend/src/components/openings/stats/outOfOpeningCopy.ts
    - app/services/insights_llm.py
    - app/prompts/endgame_insights.md
    - CHANGELOG.md
actuals:
  tasks: 3
  commits: 3
plan_head_before: 37dcb551701937c5dee92c9fae39dbe59068bdd2
plan_head_after: f4c0b154bbea5cc93700afb01910868ef6063b60
commits: 3
---

# Quick 261031-sly: Ranked-sample cap lowered from 3000 to 1000

`RECENT_GAMES_PER_TC_CAP` is now 1000, so the user side of every peer-ranked metric uses the same depth as the benchmark peers. Persisted dev rows were recomputed with a new one-off script that prunes rows the new run did not rewrite.

## Commits

| Task | Commit | Message |
|------|--------|---------|
| 1 | 1125cc404 | feat(quick-261031-sly): lower the ranked-sample cap to 1000 games per time control |
| 2 | f660f6480 | feat(quick-261031-sly): recompute script for capped user percentiles |
| 3 | f4c0b154b | chore(quick-261031-sly): cap copy, insights cache v50, changelog |

## Benchmark CDF no-op check

Verified by the orchestrator via MCP and re-run by me with the plan's psql query against `flawchess-benchmark-db`: 0 (user, TC) pairs in the benchmark cohort with more than 1000 rated human games (max exactly 1000 in bullet/blitz/rapid/classical). `app/data/cohort_cdf.tsv` stays valid, no CDF rebuild.

## Test results

- Task 1: `test_canonical_slice_sql.py` + `test_canonical_slice_per_user_vs_benchmark_parity.py` + `test_gen_global_percentile_cdf_unchanged.py`: 394 passed. 52 of 53 builder SHA hashes changed (only `selected_users:single_user` unchanged). Frontend `OutOfOpeningPopover.test.tsx`: 9 passed. 52 CDF fixtures contain `rn <= 1000`, 0 contain `rn <= 3000`.
- Task 2: `test_recompute_capped_user_percentiles.py`: 6 passed. Mutation check: replacing the early return after a failed Stage A with `pass` turned `test_recompute_user_skips_prune_and_stage_b_after_stage_a_failure` red (1 failed, 5 passed); restored afterwards (6 passed). ruff and ty clean on both files.
- Task 3 gates: `ruff format` (537 files unchanged), `ruff check` clean, `ty check app/ tests/ scripts/` clean, `check_function_size.py app/ --fail-over-depth 4` OK (1279 functions, no breaches).
- Full backend suite `uv run pytest -n auto -x`: **5660 passed, 19 skipped, 0 failed** (101 s).
- Frontend: `npm run lint` clean, `npm run build` OK, `EndgameStatsTab.test.tsx` + `OutOfOpeningPopover.test.tsx`: 14 passed.
- Old-cap grep over `app/` and `frontend/src` (the `# v48:` history line excepted): 0 matches (baseline 23). `endgame_v49` occurrences in `app/` and `tests/`: 0; `_PROMPT_VERSION = "endgame_v50"`.

## Dev recompute (flawchess-dev-db, never reset)

- Baseline before: 13 anchors pooling > 1000 games, 54 pool-count percentile rows with n_games > 1000.
- Dry run: `7 affected users (cap 1000): [2, 8, 14, 28, 31, 46, 47]`.
- Execute run summary: `Summary: 7 users processed, 1 stale rows pruned, 0 failed []`, exit 0. Only user 14 had a stale row pruned (1 Stage A row); no Stage B prunes.
- Post-run check: anchors > 1000 = 0, pool-count percentile rows with n_games > 1000 = 0.

## Deviations from Plan

**1. [Rule 3 - Blocking] Script needed ORM model registration**
- **Found during:** Task 2 dev `--execute` run.
- **Issue:** The first execute attempt failed for all 7 users ("mappers failed to initialize": `users` table, then `OAuthAccount`) because a bare script does not load the models the app registers at startup. Because Stage A/B swallow exceptions, this surfaced only through the `capture_failures` hook.
- **Fix:** Added `import app.models`, `app.models.oauth_account`, `app.models.user` at the top of the script (same pattern as `scripts/resweep_holed_games.py`).
- **Effect:** The failed first attempts pruned nothing (0 stale rows pruned, 7 failed, exit 1), which is a real-world confirmation that the skip-on-failure guard prevents data loss. The subsequent run succeeded for all 7 users.
- **Commit:** f660f6480

Otherwise the plan was executed as written. `RankedMetricPopover.tsx` was left untouched (no cap literal) and the import `game_cap` was not modified.

## Prod operator steps (post-deploy only, not run here)

1. Deploy the release containing this change and wait until it is live on flawchess.com (the pre-deploy app would overwrite rows on the old cap at the next import or eval drain).
2. Open the prod tunnel: `bin/prod_db_tunnel.sh`.
3. Dry run (writes nothing): `uv run python scripts/recompute_capped_user_percentiles.py --db prod` (expect roughly 120-190 users).
4. Execute: `uv run python scripts/recompute_capped_user_percentiles.py --db prod --execute` (type `prod` at the prompt, or pass `--yes`). Check that the summary line reports 0 failed and exit status is 0; re-running is safe.
5. Afterwards, consider moving the script and its test to `scripts/archive/`.

The insights cache (`endgame_v50`) invalidates itself on deploy; no manual step.

## Known Stubs

None.

## Threat Flags

None. The script adds no network surface; it is an operator CLI with a dry-run default, `--db` limited to dev/prod, and a typed `prod` confirmation.

## Self-Check: PASSED

Created files exist (script, test); commits 1125cc404, f660f6480, f4c0b154b are on `main`; measured commit count 3 matches `plan_head_before..HEAD`.
