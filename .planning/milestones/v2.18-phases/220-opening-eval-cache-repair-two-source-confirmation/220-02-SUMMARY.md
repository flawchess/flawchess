---
phase: 220-opening-eval-cache-repair-two-source-confirmation
plan: 02
subsystem: database
tags: [sqlalchemy, postgresql, opening-cache, eval-drain, eval-remote, db-report]

# Dependency graph
requires:
  - phase: 220-01
    provides: audit tables, scripts/opening_cache_repair.py, session_maker/EnginePool
      injection pattern (not directly consumed by this plan's code, but the shared
      phase substrate)
provides:
  - The remote-worker atomic-submit lane (app/routers/eval_remote.py) now writes
    opening_position_eval through the SAME _upsert_opening_cache the drain tick
    uses (CACHEFIX-12) — the benchmark-lane/remote-heavy-fleet throughput fix
    CACHEFIX-08 (plan 07) needs as its second confirmation source.
  - A deterministic OPENING_CACHE_BACKFILL_SQL donor order (newest
    full_evals_completed_at, pv-bearing tiebreak) replacing the arbitrary
    DISTINCT-ON-with-no-ORDER-BY pick that caused SEED-164 diagnosis 3.
  - The full-eval drain tick no longer donates a lichess-eval game's opening
    plies to the cache (closes a provenance-rule violation vs the tick's own
    documented invariant).
  - Two new db-report Sanity Checks (Check C lichess cross-check, Check D
    opening bounce rate) implementing CACHEFIX-09 as skill content (D-10 — no
    cron, no in-app periodic task).
affects: [220-06, 220-07]

# Actuals (#2632)
actuals:
  tokens: 9429
  tasks: 3
  commits: 3

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "One function, two call sites: _upsert_opening_cache (eval_drain.py) is now
      called from BOTH _full_drain_tick and _apply_atomic_submit
      (eval_remote.py), each building its own filtered target list
      (engine_targets / _cache_targets) but never duplicating the shared
      function's filter/collapse/upsert logic."
    - "Pre-merge snapshot for self-write exclusion: _worker_evaluated_plies is
      captured as frozenset(engine_result_map) immediately after the map is
      built from body.evals and BEFORE _merge_dedup_pv_into_engine_map mutates
      it with cache-transplanted tuples — the only way to distinguish
      worker-fresh values from dedup-injected ones after the merge runs."

key-files:
  created: []
  modified:
    - app/routers/eval_remote.py
    - app/services/eval_drain.py
    - tests/test_eval_worker_endpoints.py
    - tests/services/test_full_eval_drain.py
    - .claude/skills/db-report/SKILL.md

key-decisions:
  - "Task 1 revealed a real interaction, not a new bug: _resolve_full_eval's
    pre-existing dedup-hit-wins-over-fresh-engine-result priority (unchanged by
    this plan) now lets a game's OWN first submit seed a cache row that its OWN
    later resubmission then reads back instead of a fresh value. This is the
    SAME behavior the drain tick already had (it always wrote the cache first).
    Fixed the one existing test this exposed
    (test_atomic_retry_snapshotted_ply_no_longer_flaw_does_not_raise) by
    clearing the opening cache between its two submits, isolating its actual
    concern (StaleDataError in blob restore) from the newly-added cache write —
    rather than touching _resolve_full_eval's read-priority semantics, which is
    out of this plan's scope and shared by the tick."
  - "Check D's SQL restricts the 250-360cp band to the DROP magnitude
    (abs(eval_P - eval_{P-1})), not the bounce magnitude — matching the seed's
    'restricted to the 250-360cp band' phrasing for where the poison
    concentrated, reported as a separate percentage from the overall rate."

patterns-established: []

requirements-completed: [CACHEFIX-09, CACHEFIX-12]

coverage:
  - id: D1
    description: "Remote-worker atomic submit populates opening_position_eval
      through the shared _upsert_opening_cache, excluding dedup-sourced plies
      and lichess-eval games"
    requirement: CACHEFIX-12
    verification:
      - kind: unit
        ref: "tests/test_eval_worker_endpoints.py::test_submit_writes_cache"
        status: pass
      - kind: unit
        ref: "tests/test_eval_worker_endpoints.py::test_lease_shrinks_after_submit"
        status: pass
      - kind: unit
        ref: "tests/test_eval_worker_endpoints.py::test_submit_no_self_write"
        status: pass
      - kind: unit
        ref: "tests/test_eval_worker_endpoints.py::test_submit_lichess_game_no_cache_write"
        status: pass
    human_judgment: false
  - id: D2
    description: "OPENING_CACHE_BACKFILL_SQL donor choice is deterministic
      (newest full_evals_completed_at, pv-bearing tiebreak); all five gate
      predicates and ON CONFLICT DO NOTHING unchanged"
    requirement: CACHEFIX-12
    verification:
      - kind: unit
        ref: "tests/services/test_full_eval_drain.py::TestDedupHitsParity::test_backfill_prefers_newest_pv_bearing_donor"
        status: pass
      - kind: unit
        ref: "tests/services/test_full_eval_drain.py (six pre-existing gate tests, unchanged)"
        status: pass
    human_judgment: false
  - id: D3
    description: "Full-eval drain tick no longer donates a lichess-eval game's
      opening plies to the cache"
    requirement: CACHEFIX-12
    verification:
      - kind: unit
        ref: "tests/services/test_full_eval_drain.py::TestBestMove::test_tick_lichess_no_cache_donation"
        status: pass
    human_judgment: false
  - id: D4
    description: "db-report skill gains Check C (lichess cross-check, PASS if
      n_bad <= 5) and Check D (opening bounce rate, coarse sanity check only),
      each with all seven structural parts Check A/B use"
    requirement: CACHEFIX-09
    verification:
      - kind: other
        ref: "grep-based structural checks (Check C/D headings, verdict lines,
          reference numbers) — see plan Task 3 acceptance_criteria, all pass"
        status: pass
    human_judgment: true
    rationale: "The plan's <verify> carries a <human-check> asking to run the
      db-report skill against the dev database and confirm the rendered report
      shows both checks with their verdict lines and reference blockquotes. Not
      run in this session (no interactive MCP DB tool available to this
      executor) — deferred to end-of-phase UAT per workflow.human_verify_mode
      default (end-of-phase)."

# Metrics
duration: 55min
completed: 2026-09-09
status: complete
---

# Phase 220 Plan 02: Remote-Submit Cache Write, Deterministic Backfill Donor, db-report Sanity Checks Summary

**Remote-worker atomic submit now writes `opening_position_eval` through the same shared function as the drain tick, `OPENING_CACHE_BACKFILL_SQL` picks a deterministic newest-donor instead of an arbitrary one, the tick stops leaking lichess-eval opening plies into the cache, and the `db-report` skill gains two integrity checks (lichess cross-check + opening bounce rate).**

## Performance

- **Duration:** ~55 min
- **Tasks:** 3
- **Files modified:** 5 (0 created)

## Accomplishments
- `_apply_atomic_submit` (`app/routers/eval_remote.py`) now populates the opening
  dedup cache via `_upsert_opening_cache` — the same function `_full_drain_tick`
  uses — giving the benchmark lane (remote-worker-only) opening dedup for the
  first time (measured 0 rows in `opening_position_eval` on the benchmark DB
  before this change, `localhost:5433` — the baseline for plan 06's acceptance
  query 12).
- A pre-merge snapshot (`_worker_evaluated_plies`) plus a filtered target list
  (`_cache_targets`) reproduce the tick's `engine_targets` semantics exactly:
  dedup-sourced plies and lichess-eval games never round-trip back into the
  cache.
- `OPENING_CACHE_BACKFILL_SQL` gained
  `ORDER BY nxt.full_hash, g.full_evals_completed_at DESC, cur.pv IS NULL` —
  the newest, pv-preferring donor wins deterministically instead of whichever
  row Postgres's `DISTINCT ON` scan happened to visit first (SEED-164
  diagnosis 3). All five gate predicates and `ON CONFLICT DO NOTHING` are
  unchanged; all six pre-existing gate tests still pass unmodified.
- `_full_drain_tick` no longer donates a lichess-eval game's opening plies to
  the cache — closing a real provenance-rule violation the tick's own
  dedup-partition comment already forbade (SEED-109 item 4) but never enforced
  at the cache-write call site.
- `db-report` SKILL.md's Sanity Checks section gained Check C (lichess
  cross-check, `PASS` if `n_bad <= 5`) and Check D (opening bounce rate,
  explicitly a coarse sanity check only), implementing CACHEFIX-09 per D-10 (no
  cron, no in-app periodic task).

## Task Commits

Each task was committed atomically:

1. **Task 1: Submit path writes the opening cache through the shared function
   (CACHEFIX-12)** — `db499ff23` (feat)
2. **Task 2: Deterministic `OPENING_CACHE_BACKFILL_SQL` donor order and the
   lichess-eval tick guard** — `5664068a0` (feat)
3. **Task 3: `db-report` skill gains Check C and Check D** — `16f10c569` (docs)

**Plan metadata:** committed alongside this SUMMARY

## Files Created/Modified
- `app/routers/eval_remote.py` — `_worker_evaluated_plies` snapshot, `_cache_targets`
  build, three new kwargs on the `apply_full_eval(...)` call, `_upsert_opening_cache`
  import from `eval_drain`
- `app/services/eval_drain.py` — deterministic `ORDER BY` on
  `OPENING_CACHE_BACKFILL_SQL`; `update_opening_cache` / `engine_targets_for_cache`
  guarded on `not is_lichess_eval_game` in `_full_drain_tick`
- `tests/test_eval_worker_endpoints.py` — 4 new tests (`test_submit_writes_cache`,
  `test_lease_shrinks_after_submit`, `test_submit_no_self_write`,
  `test_submit_lichess_game_no_cache_write`) + a cache-cleanup fix to an existing
  regression test exposed by the new write path
- `tests/services/test_full_eval_drain.py` — 2 new tests
  (`test_backfill_prefers_newest_pv_bearing_donor`,
  `test_tick_lichess_no_cache_donation`)
- `.claude/skills/db-report/SKILL.md` — Check C and Check D sections, §3 intro
  updated to name all four checks

## Decisions Made

- **Task 1 exposed a real cache-vs-fresh-resubmit interaction, not a new bug.**
  `_resolve_full_eval`'s dedup-hit-wins-over-fresh-engine-result priority is
  pre-existing (unchanged by this plan) and already applied identically on the
  drain-tick side (the tick has always written the cache). Extending the same
  cache-write behavior to the submit path means a game's own first submit can
  now seed a cache row its own later resubmission reads back instead of a
  fresh value — exposed by
  `test_atomic_retry_snapshotted_ply_no_longer_flaw_does_not_raise`, which
  submits deliberately different (blunder vs. flat) evals for the same
  positions across two attempts to exercise an unrelated blob-restore
  regression. Fixed by clearing the opening cache between the test's two
  submits rather than touching `_resolve_full_eval`'s read-priority semantics
  (shared by the tick, out of this plan's scope, and not something CACHEFIX-12
  asked to change).
- Check D's bounce-rate SQL restricts the "250-360cp band" to the drop
  magnitude (`abs(eval_P - eval_{P-1})`), reporting it as a separate,
  denominator-restricted percentage from the overall rate — matching the
  seed's phrasing of "restricted to the 250-360cp band" as the range where
  the poison concentrated.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Existing regression test broken by the new cache-write path**
- **Found during:** Task 1 (full-suite verification after adding the 4 new tests)
- **Issue:** `test_atomic_retry_snapshotted_ply_no_longer_flaw_does_not_raise`
  submits a game twice with deliberately different eval values (blunder, then
  flat) to exercise an unrelated blob-restore regression (FLAWCHESS-8D). Once
  the first submit also seeds the opening cache (this plan's own change),
  `_resolve_full_eval`'s pre-existing dedup-hit-wins-over-fresh priority
  resurrected the first (blunder) submit's cached eval on the second submit's
  dedup_map fetch, masking the test's actual concern behind an unrelated
  cache-vs-fresh interaction (`still_flaw is not None` when it should be
  `None`). Confirmed genuinely caused by this plan's change: reverting just
  the tick-guard/self-write-exclusion hunk and re-running reproduced the
  failure; reverting NEITHER hunk (full modified file) also reproduced it,
  proving the cache-write addition itself — not a test-ordering artifact — is
  the cause.
- **Fix:** Added `_delete_opening_cache(...)` between the test's two submits
  (and in its `finally` cleanup) so the second submit's dedup_map fetch does
  not see the first submit's cache write, isolating the pre-existing
  regression test from the newly-added cache-write behavior.
- **Files modified:** `tests/test_eval_worker_endpoints.py`
- **Verification:** Test passes; confirmed it fails without the guard/without
  the cleanup via a controlled before/after run (see above).
- **Committed in:** `db499ff23` (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (1 bug, test-only — no production code affected
beyond this plan's own intended changes).
**Impact on plan:** The fix is test-only and necessary for the suite to stay
green; it does not touch `_resolve_full_eval` or any other shared read-path
logic used by the drain tick.

## Issues Encountered
None beyond the deviation documented above.

## User Setup Required
None — no external service configuration required.

## Next Phase Readiness

Ready for the remaining Phase 220 plans (03-08). Notes for downstream plans:

- **Plan 07 (CACHEFIX-08, two-source confirmation)** can now rely on the
  remote-worker submit lane as its second confirmation source — before this
  plan, ~85% of full-eval throughput (the benchmark/remote-heavy lane) never
  reached the cache at all.
- **Plan 06 (prod acceptance)** has its benchmark-DB baseline: `0` rows in
  `opening_position_eval` before this change (`localhost:5433`, queried
  directly via `docker compose -f docker-compose.benchmark.yml -p
  flawchess-benchmark exec db psql`).
- The `db-report` skill's Check C/D are skill content only — no code, no test
  coverage possible for markdown structure beyond the grep-based acceptance
  criteria already run in this plan. The `<human-check>` (running the skill
  against the dev DB and visually confirming the rendered report) is deferred
  to end-of-phase UAT.
- No blockers.

---
*Phase: 220-opening-eval-cache-repair-two-source-confirmation*
*Completed: 2026-09-09*

## Self-Check: PASSED

- All 5 modified files confirmed present on disk with the expected changes
  (`git show HEAD --stat` and per-file `git diff` reviewed above).
- All 3 commits (`db499ff23`, `5664068a0`, `16f10c569`) confirmed in `git log`.
- `uv run pytest tests/test_eval_worker_endpoints.py tests/services/test_full_eval_drain.py tests/services/test_eval_drain.py -q` — 198 passed.
- `uv run python -c "import app.main"` — exits 0, no circular import.
- `uv run ruff check .` — all checks passed.
- `uv run ty check app/ tests/ scripts/` — all checks passed.
- `uv run python scripts/check_function_size.py app/ --fail-over-depth 4 --fail-over-loc 200` — 1031 functions scanned, no breaches.
- All Task 3 grep-based acceptance criteria and the plan's own Python verify
  script (`SKILL-CHECKS-OK`) pass.
