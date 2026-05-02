---
phase: 78
plan: 06
type: execute
wave: 3
depends_on: [78-01, 78-02, 78-03, 78-04, 78-05]
files_modified:
  - reports/conv-recov-validation-2026-05-XX.md
autonomous: false
requirements: [FILL-03, FILL-04, VAL-01, VAL-02]
tags: [cutover, operator, backfill, validation, deploy, vo-1-vo-2]

must_haves:
  truths:
    - "Cutover ordering is operator-orchestrated and atomic per CONTEXT.md D-07: dev → benchmark → VAL-01 sign-off → prod backfill from local → merge → deploy → live UI smoke check (VAL-02). Prod backfill happens BEFORE deploy so the deployed code reads ready eval data with zero broken-classification window."
    - "Round 1 (dev DB localhost:5432): `uv run python scripts/backfill_eval.py --db dev --limit 50` smoke check on a tiny dataset before committing to the full benchmark run."
    - "Round 2 (benchmark DB localhost:5433): full benchmark backfill, then `/conv-recov-validation` re-run with the project skill, validating ≥99% agreement on populated subset (VAL-01 hard gate per FILL-03)."
    - "Round 3 (prod DB via `bin/prod_db_tunnel.sh` localhost:15432): full prod backfill while running migrations is NOT YET on prod. Backfill is read+write of `eval_cp` / `eval_mate` columns only — no schema changes."
    - "EXPLAIN (ANALYZE, BUFFERS) on the rewritten queries against benchmark DB shows `Index Only Scan using ix_gp_user_endgame_game` with `Heap Fetches: 0` (REFAC-04 acceptance)."
    - "After all three backfill rounds + EXPLAIN check pass, merge the phase branch to main, deploy via `bin/deploy.sh` (which runs the Alembic migration on container startup), then do the live UI smoke check (VAL-02) on 3-5 representative test users."
    - "If VAL-01 agreement < 99% on benchmark, STOP. Do not proceed to prod backfill. Investigate residual delta — likely `material_imbalance`-based proxy drift in queries that never made it to the new eval path, or seeded fixture issues. Treat as a phase blocker."
    - "If VAL-02 surfaces obvious regressions (zero/null gauges on populated users, nonsense spikes), revert via `git revert` of the merge commit + `bin/deploy.sh`. The DB-side eval data stays (no rollback of writes) so a follow-up fix re-uses the same data."
  artifacts:
    - path: "reports/conv-recov-validation-2026-05-XX.md"
      provides: "Post-benchmark-backfill validation report (VAL-01 acceptance evidence)"
      contains: "agreement"
  key_links:
    - from: "Plan 78-03 backfill script"
      to: "Round 1 / Round 2 / Round 3 execution"
      via: "scripts/backfill_eval.py CLI"
      pattern: "uv run python scripts/backfill_eval.py --db"
    - from: "Plan 78-05 Alembic migration"
      to: "prod deploy step"
      via: "deploy/entrypoint.sh runs migrations on backend container start"
      pattern: "alembic upgrade head"
    - from: "Round 2 benchmark backfill"
      to: "VAL-01 conv-recov-validation skill"
      via: "Claude project skill invocation"
      pattern: "/conv-recov-validation"
---

<objective>
Operator-orchestrated cutover. This plan does NOT create new code — it sequences the execution of the artifacts shipped in Plans 78-01..05 in the precise order required by D-07: dev → benchmark → VAL-01 → prod backfill → merge → deploy → VAL-02. Each round is gated by an operator checkpoint so the operator stays in the loop on a one-way change.

Purpose: FILL-03 sequencing, FILL-04 prod coverage, VAL-01 agreement gate, VAL-02 live-UI smoke check. The phase ships without this plan only if the operator is fine with a broken-classification window post-deploy. We chose the inverse: prod backfill BEFORE deploy means the new code reads ready data on first request.

Output: `reports/conv-recov-validation-2026-05-XX.md` (date stamp at run time) showing ≥99% agreement; operator sign-off recorded in this plan's SUMMARY; phase merged + deployed; VAL-02 sanity check passed.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@.planning/milestones/v1.15-phases/78-stockfish-eval-cutover-for-endgame-classification/78-CONTEXT.md
@.planning/milestones/v1.15-phases/78-stockfish-eval-cutover-for-endgame-classification/78-SPEC.md
@.planning/milestones/v1.15-phases/78-stockfish-eval-cutover-for-endgame-classification/78-RESEARCH.md
@.planning/milestones/v1.15-phases/78-stockfish-eval-cutover-for-endgame-classification/78-VALIDATION.md
@.planning/milestones/v1.15-phases/78-stockfish-eval-cutover-for-endgame-classification/78-03-backfill-script-PLAN.md
@.planning/milestones/v1.15-phases/78-stockfish-eval-cutover-for-endgame-classification/78-05-endgame-refactor-PLAN.md
@CLAUDE.md
@bin/deploy.sh
@bin/prod_db_tunnel.sh

<interfaces>
<!-- Backfill script CLI from Plan 78-03 (already shipped) -->
```
uv run python scripts/backfill_eval.py --db {dev|benchmark|prod} [--user-id N] [--dry-run] [--limit N]
```

<!-- Project skill: /conv-recov-validation -->
- Skill file: .claude/skills/conv-recov-validation/SKILL.md
- Writes report to: reports/conv-recov-validation-YYYY-MM-DD.md
- Operates against benchmark DB by default (status='completed' filter, sparse-cell exclusion per MEMORY.md)

<!-- Prod tunnel -->
```
bin/prod_db_tunnel.sh        # opens tunnel localhost:15432 → prod:5432
bin/prod_db_tunnel.sh stop   # closes tunnel
```

<!-- Deploy -->
```
bin/deploy.sh   # triggers GitHub Actions CI/deploy workflow for main and monitors progress
```
</interfaces>
</context>

<tasks>

<task type="checkpoint:human-action" gate="blocking">
  <name>Task 1: Round 1 — Dev DB smoke backfill</name>
  <files>N/A — operator-driven cutover step; no code changes in this task. See `<how-to-verify>` for the exact commands and `<resume-signal>` for the gating signals.</files>
  <action>Execute the steps listed in `<how-to-verify>` and report the outcome via `<resume-signal>`. The executor agent blocks until the operator returns the signal; this is an operator-only orchestration step (no code or file changes happen here).</action>
  <what-built>Plans 78-01..05 are merged into the phase branch. Local Stockfish is installed. Operator runs the backfill script against the local dev DB to confirm end-to-end correctness on a tiny dataset before committing CPU time to the full benchmark run.</what-built>
  <how-to-verify>
    1. Confirm dev DB is up: `docker compose -f docker-compose.dev.yml -p flawchess-dev up -d`.
    2. Confirm Stockfish is on PATH locally: `stockfish --help | head -1`.
    3. Run dry-run smoke: `uv run python scripts/backfill_eval.py --db dev --dry-run` — note the row count.
    4. Run live smoke with limit: `uv run python scripts/backfill_eval.py --db dev --limit 50`.
    5. Verify writes happened — query against dev DB:
       ```sql
       SELECT COUNT(*) AS populated
       FROM game_positions
       WHERE endgame_class IS NOT NULL AND (eval_cp IS NOT NULL OR eval_mate IS NOT NULL);
       ```
    6. Re-run the same backfill: `uv run python scripts/backfill_eval.py --db dev --limit 50` — confirm idempotency (no engine calls in logs, OR a row count of 0 in the "Found N span-entry rows" log line).
  </how-to-verify>
  <verify>
    <automated>echo "Operator-only checkpoint; verification is the resume-signal payload."</automated>
  </verify>
  <done>Operator has returned the resume-signal payload listed below; the next task can proceed.</done>
  <resume-signal>Reply with one of: `dev-backfill-ok`, `dev-backfill-failed: <reason>`, or `dev-stockfish-missing: <details>`.</resume-signal>
</task>

<task type="checkpoint:human-action" gate="blocking">
  <name>Task 2: Round 2 — Benchmark DB full backfill</name>
  <files>N/A — operator-driven cutover step; no code changes in this task. See `<how-to-verify>` for the exact commands and `<resume-signal>` for the gating signals.</files>
  <action>Execute the steps listed in `<how-to-verify>` and report the outcome via `<resume-signal>`. The executor agent blocks until the operator returns the signal; this is an operator-only orchestration step (no code or file changes happen here).</action>
  <what-built>Operator runs the full backfill against the benchmark DB. This is the "real" run — RESEARCH.md estimates ~1.5M positions × ~35ms at depth 15 ≈ 2 hours on 8 cores. Tune local concurrency expectations accordingly. The operator's local Stockfish version is recorded in Plan 78-01's SUMMARY.</what-built>
  <how-to-verify>
    1. Confirm benchmark DB is up: `bin/benchmark_db.sh start` (or `docker compose -f docker-compose.benchmark.yml -p flawchess-benchmark up -d`).
    2. Run dry-run to count work: `uv run python scripts/backfill_eval.py --db benchmark --dry-run`. Expected: hundreds of thousands of rows; this is the proper scale.
    3. Run full backfill: `uv run python scripts/backfill_eval.py --db benchmark`. Use `screen` or `tmux` so a tunnel/terminal drop does not kill the run. COMMIT-every-100 means partial progress is preserved.
    4. While running, monitor logs at COMMIT boundaries — every 100 evals prints a timestamped "Committed N/total" line.
    5. After completion, verify zero remaining NULL span entries on benchmark:
       ```sql
       -- Run via mcp__flawchess-benchmark-db__query
       WITH spans AS (
         SELECT user_id, game_id, endgame_class, MIN(ply) AS min_ply, COUNT(ply) AS ply_cnt
         FROM game_positions
         WHERE endgame_class IS NOT NULL
         GROUP BY user_id, game_id, endgame_class
         HAVING COUNT(ply) >= 6
       )
       SELECT COUNT(*) AS still_null
       FROM game_positions gp
       JOIN spans s ON s.user_id = gp.user_id
                   AND s.game_id = gp.game_id
                   AND s.endgame_class = gp.endgame_class
                   AND s.min_ply = gp.ply
       WHERE gp.eval_cp IS NULL AND gp.eval_mate IS NULL;
       ```
       Expected: `0` (or a small handful of rows where engine error skipped — check Sentry for warnings).
    6. Run `EXPLAIN (ANALYZE, BUFFERS)` on a representative `query_endgame_entry_rows` invocation — pick a real user_id from benchmark DB. Use the SQL pattern from RESEARCH.md lines 731-741. Expected: `Index Only Scan using ix_gp_user_endgame_game` with `Heap Fetches: 0` (or near-zero after `VACUUM ANALYZE` which the script ran). REFAC-04 acceptance.
  </how-to-verify>
  <verify>
    <automated>echo "Operator-only checkpoint; verification is the resume-signal payload."</automated>
  </verify>
  <done>Operator has returned the resume-signal payload listed below; the next task can proceed.</done>
  <resume-signal>Reply with one of: `benchmark-backfill-ok` (and report row counts + EXPLAIN summary), `benchmark-backfill-partial: <reason>` (operator decides whether to proceed), or `benchmark-backfill-failed: <reason>`.</resume-signal>
</task>

<task type="checkpoint:human-verify" gate="blocking">
  <name>Task 3: VAL-01 — Run /conv-recov-validation skill on benchmark DB</name>
  <files>N/A — operator-driven cutover step; no code changes in this task. See `<how-to-verify>` for the exact commands and `<resume-signal>` for the gating signals.</files>
  <action>Execute the steps listed in `<how-to-verify>` and report the outcome via `<resume-signal>`. The executor agent blocks until the operator returns the signal; this is an operator-only orchestration step (no code or file changes happen here).</action>
  <what-built>The benchmark DB has full eval coverage on endgame span entries. The `/conv-recov-validation` project skill walks endgame games, computes both the OLD (now removed from prod code, but the skill may still synthesize the proxy locally for comparison) and NEW (eval-based) classification, and reports agreement.</what-built>
  <how-to-verify>
    1. Run the skill: `/conv-recov-validation` (the operator invokes via Claude with appropriate skill context). The skill writes `reports/conv-recov-validation-YYYY-MM-DD.md` with today's date.
    2. Read the generated report. Required readings:
       - Headline agreement on populated subset MUST be ≥ 99% (per VAL-01 acceptance + SPEC line 153).
       - The report should explicitly state the populated subset is ~100% of endgame span entries on benchmark (FILL-04 invariant on benchmark DB).
       - Per-class breakdowns should show agreement near 100% across all classes (queen, rook, minor, pawn, mixed). The pre-cutover report (`reports/conv-recov-validation-2026-05-02.md`) showed queen and pawnless underperforming — post-cutover those gaps should be gone because both proxy and ground truth derive from `eval_cp` / `eval_mate`.
    3. If agreement is < 99%, this is a phase BLOCKER. Investigate:
       - Are there `material_imbalance` references still in the proxy side of the skill that don't match the new eval path?
       - Are there NULL eval rows the skill is treating as proxy-true?
       - Did the migration fully apply on benchmark? (`uv run alembic current` against benchmark URL.)
       - Did the backfill skip rows due to engine errors? Check Sentry warnings count.
       Stop here, fix, and re-run. Do NOT proceed to Round 3.
    4. Stage the report file: `git add reports/conv-recov-validation-YYYY-MM-DD.md` (commit will land in this plan's commit).
  </how-to-verify>
  <verify>
    <automated>echo "Operator-only checkpoint; verification is the resume-signal payload."</automated>
  </verify>
  <done>Operator has returned the resume-signal payload listed below; the next task can proceed.</done>
  <resume-signal>Reply with one of: `val-01-passed: <agreement>%`, `val-01-failed: <agreement>% — <issue>`, or `val-01-blocked: <details>`.</resume-signal>
</task>

<task type="checkpoint:human-action" gate="blocking">
  <name>Task 4: Round 3 — Prod DB backfill (via SSH tunnel)</name>
  <files>N/A — operator-driven cutover step; no code changes in this task. See `<how-to-verify>` for the exact commands and `<resume-signal>` for the gating signals.</files>
  <action>Execute the steps listed in `<how-to-verify>` and report the outcome via `<resume-signal>`. The executor agent blocks until the operator returns the signal; this is an operator-only orchestration step (no code or file changes happen here).</action>
  <what-built>Operator opens the prod SSH tunnel, runs the backfill against prod DB. This is BEFORE merge + deploy — when the new code ships, prod's eval columns are already populated, so the new repository queries read ready data on the first request.</what-built>
  <how-to-verify>
    1. Open prod tunnel: `bin/prod_db_tunnel.sh` (forwards localhost:15432 → prod:5432).
    2. Dry-run on prod: `uv run python scripts/backfill_eval.py --db prod --dry-run`. Note row count — should be the prod span-entry NULL count (mostly chess.com games + lichess games where lichess `%eval` did not cover the span entry).
    3. Optional: targeted single-user run for a test account first: `uv run python scripts/backfill_eval.py --db prod --user-id <test-user-id>`. Confirms the prod path is wired before the long all-users run.
    4. Full prod backfill: `uv run python scripts/backfill_eval.py --db prod`. Use `screen`/`tmux`. Tunnel drops are recoverable — COMMIT-every-100 + SELECT-NULL resume means restart from where it died.
    5. Watch CPU on the operator's machine — Stockfish at depth 15 with Threads=1 uses one core continuously. The wall-clock for the full prod backfill depends on row count; if dry-run reports 100k rows, expect ~2 hours single-thread.
    6. Post-completion verification on prod:
       ```sql
       -- Run via mcp__flawchess-prod-db__query (read-only role; this is a sanity check, not a write)
       WITH spans AS (
         SELECT user_id, game_id, endgame_class, MIN(ply) AS min_ply, COUNT(ply) AS ply_cnt
         FROM game_positions
         WHERE endgame_class IS NOT NULL
         GROUP BY user_id, game_id, endgame_class
         HAVING COUNT(ply) >= 6
       )
       SELECT COUNT(*) AS still_null
       FROM game_positions gp
       JOIN spans s ON s.user_id = gp.user_id AND s.game_id = gp.game_id
                   AND s.endgame_class = gp.endgame_class AND s.min_ply = gp.ply
       WHERE gp.eval_cp IS NULL AND gp.eval_mate IS NULL;
       ```
       Expected: `0` (or a small handful from engine errors — check Sentry).
    7. Spot-check that pre-existing lichess `%eval` rows are unchanged — pick a known game_id with lichess eval, query before/after the backfill (or use git history for the value), confirm byte-for-byte preservation (FILL-04 invariant).
    8. Close the tunnel: `bin/prod_db_tunnel.sh stop`.
  </how-to-verify>
  <verify>
    <automated>echo "Operator-only checkpoint; verification is the resume-signal payload."</automated>
  </verify>
  <done>Operator has returned the resume-signal payload listed below; the next task can proceed.</done>
  <resume-signal>Reply with one of: `prod-backfill-ok: <still_null_count>`, `prod-backfill-tunnel-flaky: <details>` (operator decides retry strategy), or `prod-backfill-failed: <reason>`.</resume-signal>
</task>

<task type="checkpoint:human-action" gate="blocking">
  <name>Task 5: Merge phase branch to main + deploy</name>
  <files>N/A — operator-driven cutover step; no code changes in this task. See `<how-to-verify>` for the exact commands and `<resume-signal>` for the gating signals.</files>
  <action>Execute the steps listed in `<how-to-verify>` and report the outcome via `<resume-signal>`. The executor agent blocks until the operator returns the signal; this is an operator-only orchestration step (no code or file changes happen here).</action>
  <what-built>Code refactor (Plans 78-01..05) merges to main; CI runs the full test suite + ruff + ty; bin/deploy.sh ships to prod. The Alembic migration runs automatically on backend container start (per CLAUDE.md `deploy/entrypoint.sh`).</what-built>
  <how-to-verify>
    1. Confirm phase branch is up to date with main: `git fetch origin && git rebase origin/main` (resolve conflicts if any — unlikely given v1.15 is single-phase).
    2. Push the phase branch: `git push origin <phase-branch>`.
    3. Open PR: `gh pr create --title "Phase 78: Stockfish eval cutover for endgame classification" --body "<summary>"`.
    4. Wait for CI green: `gh pr checks <pr-number>`. The CI must include the new Stockfish install step from Plan 78-01 and run the engine wrapper tests (Plan 78-02), backfill tests (Plan 78-03), import-path tests (Plan 78-04), refactor tests (Plan 78-05).
    5. Squash-merge to main: `gh pr merge --squash --delete-branch <pr-number>` (or via web UI).
    6. Deploy: `bin/deploy.sh`. Watch the GitHub Actions workflow — the deploy step rebuilds the Docker image with the pinned Stockfish, runs `alembic upgrade head` on container start (which applies the Plan 78-05 migration), and starts the new backend with the lifespan-managed engine.
    7. Confirm deploy succeeded:
       - `ssh flawchess "cd /opt/flawchess && docker compose ps"` — backend running.
       - `ssh flawchess "cd /opt/flawchess && docker compose exec backend stockfish --help | head -3"` — Stockfish present in container (ENG-01 acceptance, manual).
       - `ssh flawchess "cd /opt/flawchess && docker compose logs backend --tail 100"` — look for "Application startup complete" + no engine startup errors.
       - `ssh flawchess "cd /opt/flawchess && docker compose exec backend pgrep stockfish"` — confirms long-lived UCI process exists (ENG-01 / D-01 acceptance).
    8. Confirm migration applied: `ssh flawchess "cd /opt/flawchess && docker compose exec backend uv run alembic current"` — should show the new revision from Plan 78-05.
  </how-to-verify>
  <verify>
    <automated>echo "Operator-only checkpoint; verification is the resume-signal payload."</automated>
  </verify>
  <done>Operator has returned the resume-signal payload listed below; the next task can proceed.</done>
  <resume-signal>Reply with one of: `deploy-ok: <revision>`, `ci-failed: <details>`, or `deploy-failed: <details>`.</resume-signal>
</task>

<task type="checkpoint:human-verify" gate="blocking">
  <name>Task 6: VAL-02 — Live UI smoke check on prod</name>
  <files>N/A — operator-driven cutover step; no code changes in this task. See `<how-to-verify>` for the exact commands and `<resume-signal>` for the gating signals.</files>
  <action>Execute the steps listed in `<how-to-verify>` and report the outcome via `<resume-signal>`. The executor agent blocks until the operator returns the signal; this is an operator-only orchestration step (no code or file changes happen here).</action>
  <what-built>Production is running the new code against the pre-backfilled prod DB. Operator inspects the live Endgames page for 3-5 representative test users covering different (rating, TC) cells and confirms gauges render sensibly with no obvious regressions.</what-built>
  <how-to-verify>
    1. Pick 3-5 test users covering:
       - Different ratings (e.g. one ~1200, one ~1800, one ~2200).
       - Different time controls (bullet / blitz / rapid / classical).
       - At least one chess.com-only user (no lichess `%eval` historically — these users got the most new evals from backfill).
       - At least one lichess-heavy user (most span entries already had lichess `%eval` — fewer new evals, but classification semantics changed).
    2. For each user, visit `https://flawchess.com/endgames` (after impersonation if admin-impersonation is wired, or via the user's own account).
    3. Inspect:
       - **No nulls / zeros on populated users:** every endgame class with ≥ N games shows a gauge value, not "—" or 0.
       - **No nonsense spikes:** a 1500-rated rapid user's queen-conversion rate shouldn't suddenly be 100% or 0%; expect somewhere in the 30-70% range.
       - **Expected accuracy improvements:** queen and pawnless classes were the proxy's weak spots per the source validation report. Their post-cutover gauges should look more sensible — but operator judgment, not a hard threshold.
       - **Endgame ELO timeline still renders:** the timeline chart depends on `query_endgame_elo_timeline_rows` (one of the three refactored queries). If the timeline is empty or broken, that's a regression.
    4. Spot-check ONE specific game's classification by visiting it via Bookmarks / Game card and confirming the conv/recov label matches what the eval would predict (gross sanity: if user was up a queen at endgame entry, that class should classify as conversion).
    5. If a regression is found, decide:
       - **Cosmetic / per-user weird but data-explainable:** ack and move on; some shifts are expected per VAL-02 SPEC text.
       - **Page broken / null gauges across users / EXPLAIN regressed to seq scan:** revert via `git revert <merge-commit>` + `bin/deploy.sh`. The DB-side eval data is preserved (no rollback of writes); a follow-up fix on a new branch can re-use it.
  </how-to-verify>
  <verify>
    <automated>echo "Operator-only checkpoint; verification is the resume-signal payload."</automated>
  </verify>
  <done>Operator has returned the resume-signal payload listed below; the next task can proceed.</done>
  <resume-signal>Reply with one of: `val-02-ok`, `val-02-cosmetic: <details>` (acceptable shifts), or `val-02-regression: <details>` (triggers revert).</resume-signal>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| Operator's local machine → benchmark DB | Local Stockfish, local DB writes. Benchmark DB is a separate database from prod. |
| Operator's local machine → prod DB (via SSH tunnel) | Tunnel `localhost:15432 → prod:5432`. Backfill writes only `eval_cp` / `eval_mate` columns. No schema changes. |
| Phase branch → main → prod | Standard PR + CI + deploy. Migration runs in container startup. |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-78-28 | Tampering | Wrong --db target during backfill (e.g. accidentally hitting prod when meaning benchmark) | mitigate | `--db` is REQUIRED with explicit choices (Plan 78-03). Operator's `_log` output echoes `db=prod` on every commit boundary. Round 1 / Round 2 / Round 3 are explicit named checkpoints in this plan. |
| T-78-29 | Tampering | Lichess `%eval` annotations overwritten on prod | mitigate | Backfill SELECT WHERE clause excludes any row with existing eval (Plan 78-03 Wave 0 test asserted this). Spot check in Task 4 confirms preservation on prod sample. |
| T-78-30 | DoS | Migration locks prod `game_positions` writes mid-deploy | mitigate (observe) | Partial index on `endgame_class IS NOT NULL` rows; lock window is bounded. Operator chooses deploy time (off-peak). CONCURRENTLY upgrade is a documented follow-up (Plan 78-05). |
| T-78-31 | DoS | Prod backfill saturates operator's local machine, slows tunnel I/O | accept | Single-thread Stockfish (D-03 Threads=1). Operator can pause/resume by killing + relaunching script. COMMIT-every-100 ensures no data loss. |
| T-78-32 | Repudiation | No record of what was backfilled / when | mitigate | Plan 78-03 script prints timestamped log lines per COMMIT. SUMMARY.md for Plan 78-06 records: row counts per round, VAL-01 agreement %, deploy timestamp, VAL-02 outcome. Sentry captures any engine errors. |
| T-78-33 | Information disclosure | SSH tunnel credentials / prod DB read-only role compromise | accept | `bin/prod_db_tunnel.sh` uses operator's existing SSH key. Prod DB read-only role for query MCP is documented; backfill uses the prod app role (read-write but only on `eval_cp`/`eval_mate`). Existing security perimeter, not changed by this phase. |
| T-78-34 | Elevation of privilege | Operator runs prod backfill from compromised local machine | accept | Existing risk; not introduced by this phase. Standard endpoint hygiene applies. |
| T-78-35 | DoS | VAL-01 fails late in the cycle, after benchmark backfill consumed hours | accept | This is the COST of getting VAL-01 right. The VAL-01 gate exists precisely so this failure happens BEFORE prod backfill. Sunk-cost CPU on benchmark is the price of correctness. |
</threat_model>

<verification>
- All six checkpoints pass with operator sign-off.
- Post-prod-backfill SQL on prod returns 0 NULL span entries (FILL-04).
- `reports/conv-recov-validation-2026-05-XX.md` exists and shows ≥ 99% agreement on populated subset (VAL-01).
- Production deploy succeeded; `docker compose exec backend stockfish --help` works (ENG-01).
- VAL-02 operator smoke check confirms gauges render sensibly on representative users.
- `pgrep stockfish` count stable inside the running backend container (long-lived UCI confirmed).
</verification>

<success_criteria>
- Three backfill rounds executed in order: dev → benchmark → VAL-01 → prod.
- Benchmark agreement ≥ 99% before prod backfill.
- Prod backfill completes BEFORE merge + deploy (zero broken-classification window).
- Phase merged to main, deployed via `bin/deploy.sh`, migration applied automatically.
- VAL-02 smoke check passes (or surfaces only acceptable accuracy-driven shifts).
</success_criteria>

<output>
After completion, create `.planning/milestones/v1.15-phases/78-stockfish-eval-cutover-for-endgame-classification/78-06-SUMMARY.md` recording: row counts per round, VAL-01 agreement percentage and link to the new validation report, deploy timestamp + revision, list of test users inspected for VAL-02, any cosmetic shifts noted.
</output>
