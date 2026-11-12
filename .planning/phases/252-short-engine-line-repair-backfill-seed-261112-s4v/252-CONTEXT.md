# Phase 252: Short Engine Line Repair Backfill - Context

**Gathered:** 2026-11-12
**Status:** Ready for planning

<domain>
## Phase Boundary

Repair engine data that was stored truncated before the 2026-11-12 fix (releases #471 engine wrapper and worker
schema v3 gate, #472 opening cache, #473 frontend hooks). New damage has stopped: on prod the share of 1-2 ply
lines in newly analysed games fell from 26.9% to 1.8% after the deploy.

In scope, on prod and on the benchmark DB:
1. Re-search stored `game_positions.pv` rows of 1-2 plies (non-terminal) with the fixed wrapper.
2. Re-walk the `game_flaws` line blobs built from those short lines, through the existing tier-4 lane, so the
   server re-derives tactic tags on submit.
3. Pick up empty `[]` sentinel lines at opening plies whose position has no usable pv.
4. Benchmark DB: repair, retag, re-run the §5 tactic zones and update `app/services/tactic_delta_zones.py`.
5. A measurement (no repair) of how many flaw classifications would flip between bound-valued and exact evals.

Not in scope: re-evaluating evals, rewriting best-move rows or gem badges, regrading `drill_solves`, the opening
cache (heals on its own since #472), any frontend change, new worker lanes.

</domain>

<decisions>
## Implementation Decisions

### Best-move consistency
- **D-01:** The line re-search is pinned to the stored `best_move` (python-chess `root_moves`), so the repaired pv
  always starts with the stored best move. Answer keys, `game_best_moves`, gem badges and Maia stats stay valid and
  need no recompute. The phase does not overwrite an existing `best_move`.
- **D-02:** Where no `best_move` is stored, or the stored one is illegal in the position, search freely and write
  both the pv and its first move as `best_move`.

### Re-walk scope and order
- **D-03:** Only the blob whose line was repaired is re-walked. The flaw's other blob and its values stay
  untouched. The tier-4 selector keys on `allowed_pv_lines IS NULL` today and must be extended so a flaw with only
  one NULL line is picked up, and the submit must write only that line.
- **D-04:** Processing order is newest games first (by game date, across all users), for the line repair and for
  the re-walk. The re-walk therefore needs an ordered claim instead of the random lottery, for this backfill.

### Bound-valued evals
- **D-05:** Evals are not repaired in this phase. The pilot measures, on a sample, how many mistake/blunder
  classifications would flip between the stored eval and an exact re-search. If the flip rate is material, capture
  a follow-up seed; do not widen this phase.
- **D-06:** Blob node values of untouched walks and all `game_best_moves` rows stay as they are. Only re-walked
  blobs get exact values. No badge measurement.

### Run mechanics
- **D-07:** The line repair is an operator script run from the owner's box: local Stockfish pool, writes over the
  DB tunnel, resumable, with a `--db` switch in the style of `scripts/retag_flaws.py`. No new server endpoint and
  no worker release for the line repair.
- **D-08:** During the line repair the worker on that box is stopped and the script uses all engines. Live
  analysis relies on the server pool; the script does not check for other version-3 workers (owner's call: the
  server pool is enough at 1-5k new games a day).
- **D-09:** Step order: prod line repair, then prod re-walk on the fleet, with the benchmark line repair on the
  owner's box running alongside the prod re-walk. Benchmark re-walk, retag and zone refresh last.
- **D-10:** A 1% pilot runs first. If it passes, the full runs start automatically, without waiting for the owner.
  The run stops and returns to the owner when any of these holds:
  - more than about 3% of re-searched lines are still 1-2 plies, mates excluded (repair does not stick);
  - measured throughput puts the prod line repair beyond 10 days or the re-walk beyond 8 weeks;
  - any failed batch, a row-count mismatch, or prod DB connections or latency climbing during pilot writes;
  - the eval measurement (D-05) shows more than about 2% of mistake/blunder classifications flipping.
  The thresholds are named constants in the script, not prose.
  — **Reversibility:** one-way — the repair overwrites `game_positions.pv` and blob columns in place on prod; there
  is no stored copy of the old values, so the pilot gates and a dry-run mode are the only safety net.

### Decisions added at plan time (2026-11-12, owner answers after research)
- **D-11:** D-04's "ordered claim" is implemented as a just-in-time feeder (RESEARCH Pattern 4), not an ordered
  in-server claim. An operator script NULLs repaired lines newest-first in small windows and clears
  `games.blobs_completed_at`; the existing tier-4 lottery drains each window. Newest-first holds at window
  granularity. No up-front NULLing of all repaired lines, no index migration, no in-user order flag. This
  supersedes the "ordered claim instead of the random lottery" wording of D-04.
- **D-12:** The server-pool drain must not fully re-evaluate tier-4 games. `TIER_BLOB_BACKFILL` claims in the
  server pool go through a blob-only tick that shares its apply core with `/flaw-blob-submit`; `eval_cp`,
  `eval_mate` and the flaw set stay untouched (protects D-03, D-05, D-06). This also applies to natural tier-4
  games (owner accepted). A test must prove a tier-4 drain tick leaves `eval_cp` alone. The change needs one prod
  deploy before the re-walk and a restart of the `:8001` benchmark backend before the benchmark re-walk.
- **D-13:** Guest games are excluded from the line repair and the feeder work list.
- **D-14:** A prod `scripts/retag_flaws.py` sweep runs as the last prod step, after the re-walk has drained
  (never before). The benchmark retag stays in scope as before.
- **D-15:** The phase must work with a mixed worker fleet. The owner cannot update all workers in the short term,
  so upgrading the schema-version-2 workers is NOT a precondition for any step. The re-walk runs on whatever
  version-3 capacity exists (version-3 workers plus the server pool's blob-only tick, D-12). Version-2 workers must
  stay harmless: they keep getting 204 on the flaw-blob lane, and no lane a version-2 worker can still claim may
  pick up a re-walk game and fully re-evaluate it or overwrite a repaired line. Prove this with a test. No
  `WORKER_SCHEMA_VERSION_MIN` bump and no worker release. The re-walk time gate (D-10, 8 weeks) is judged on the
  drain rate measured with the fleet as it is; if it trips, the run returns to the owner.
- **No local undo log** (owner declined). The pilot gates and dry-run mode remain the only safety net (D-10).

### Measured on prod at plan time (2026-11-12, read-only)
- Non-guest tier-3 backlog 0 and non-guest natural tier-4 backlog 0 (guests: 56,007 and 2,063), so the fleet's
  flaw-blob rung gets time.
- Flaws with exactly one NULL blob line: 0 (4,531 with both NULL), so the per-line probe re-opens nothing on deploy.
- `worker_heartbeats`, last 2 days: 4 workers on schema version 2, 2 on version 3. The v2 workers get 204 on the
  flaw-blob lane, so the seed's 3.5-week re-walk estimate (whole fleet) does not hold; see D-15.
- 27 games have `played_at IS NULL`: order `played_at DESC NULLS LAST, id DESC`.
- `pg_stat_activity` baseline: 17 connections (afternoon).

### Claude's Discretion
- Batch sizes, commit cadence, progress reporting and the report format of the scripts.
- How the ordered re-walk claim is implemented (flag on the existing tier-4 claim, or a backfill-only claim).
- Whether the benchmark runs reuse the same script unchanged or need lane-specific handling.
- The exact SQL for excluding legitimately short lines (mate scores and terminal positions).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Investigation and plan
- `.planning/seeds/SEED-261112-s4v-short-stored-engine-lines.md` — root cause, what is wrong in storage, derived
  data map, Part B repair plan, time estimates, the empty opening-line edge case, breadcrumbs with function names.
- `.planning/quick/261112-j47-engine-wrapper-keep-last-exact-info-line/261112-j47-SUMMARY.md` — the engine wrapper
  fix this phase's re-searches rely on (`_select_final_infos`).
- `.planning/quick/261112-k56-opening-cache-treat-1-2-ply-cached-lines/261112-k56-SUMMARY.md` — usable-pv rule
  (`CACHED_PV_MIN_PLIES`, `cached_pv_usable`) and why the cache needs no separate repair.

### Operations
- `docs/production-runbook.md` — prod commands, Postgres limits (max_connections 50, keep operator connections
  under about 25).
- `docs/benchmark-lane-runbook.md` — benchmark backend on :8001, tranches, lane flags.
- `docs/dev-tooling.md` — script inventory, DB MCP servers.
- `.claude/skills/benchmarks/SKILL.md` — §5 tactic zones (classical + rapid lane) and the fast re-run path.
- `reports/retag/retag-2026-09-13.md` — prior prod retag run (3h17m, 4.76M flaws) as a sizing reference.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `app/services/engine.py` `EnginePool`: fixed wrapper; `protocol.analysis()` accepts `root_moves`, which D-01
  needs threaded through `_acquire_and_analyse` or a dedicated method.
- `scripts/retag_flaws.py`: template for an operator script with `--db dev|prod|benchmark`, `--workers`,
  `--throttle-ms`, dry-run, batched commits and a written report.
- Tier-4 lane: `_claim_tier4_blob` (`app/services/eval_queue_service.py`), `_build_flaw_blob_lease_positions` and
  `_refresh_blobs_completed` (`app/services/eval_apply.py`), `/flaw-blob-lease` and `_apply_flaw_blob_submit`
  (`app/routers/eval_remote.py`). The submit already re-derives tactic tags and clears the Maia stamp.
- `cached_pv_usable` / `pv_ply_count` in `app/services/eval_apply.py`: the single short-line predicate.
- `scripts/benchmarks/chapter5.py` `compute()`: fast path for the §5 refresh.

### Established Patterns
- Blobs are a walk along the stored pv; a blob can never be longer than its pv allows.
- pv at row k starts from position k, whose eval sits on row k-1 (post-move shift); the mate exclusion must read
  row k-1's `eval_mate`.
- Tier-4 treats `[]` as done and NULL as to-do; `games.blobs_completed_at` gates the claim.
- Long operator runs go from the orchestrator (`setsid nohup` plus Monitor), not from an executor subagent.
- Eval lottery tests: every non-guest Game insert needs finally-cleanup.

### Integration Points
- New script(s) under `scripts/`; selector and submit changes in the tier-4 path; no schema migration expected
  (planner to confirm, e.g. for an ordered claim).
- Phase 250's prod backfill reads the repaired allowed lines and should run after the prod line repair.

</code_context>

<specifics>
## Specific Ideas

- Sizes measured 2026-11-12: prod about 12M stored lines, about 3.4M short; benchmark about 3.1M, about 1M short.
  Estimates (unpiloted): prod line repair about 5 days on the owner's 8-engine box, prod re-walk about 26M
  searches or 3.5 weeks of fleet time for one line per flaw.
- Bound lines are always exactly 1 ply (lowerbound) or 2 plies (upperbound); 3-11 ply lines are genuine (79% of
  stored 3-5 ply lines carry a mate score) and need no repair.
- The three Hetzner workers were still on schema version 2 at context time; the re-walk on the fleet needs them
  updated to make the time estimate.

</specifics>

<deferred>
## Deferred Ideas

- Full or partial re-evaluation of bound-valued evals: only if the D-05 measurement shows a material flip rate;
  would be its own phase.
- Recomputing gem and great-move badges from exact best-move values.
- Regrading `drill_solves` solved against short lines.
- The stale `ANALYSIS_FREE_RUN_MIN_MULTIPV` doc comment in `frontend/src/pages/Analysis.tsx` (the second line is
  not always present); fix when Phase 249 has merged.

### Reviewed Todos (not folded)
- `todo.match-phase` returned keyword-only matches (for example `172-deferred-review-findings.md`); none relates to
  this phase.

</deferred>

---

*Phase: 252-Short Engine Line Repair Backfill*
