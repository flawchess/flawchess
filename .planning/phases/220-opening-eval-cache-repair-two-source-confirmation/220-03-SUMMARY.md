---
phase: 220-opening-eval-cache-repair-two-source-confirmation
plan: 03
subsystem: database
tags: [postgresql, sqlalchemy, stockfish, opening-cache-repair, flaws, advisory-lock]

# Dependency graph
requires:
  - phase: 220-01
    provides: audit tables (opening_cache_audit, opening_cache_repair_rows,
      opening_cache_repair_games, opening_cache_repair_progress), the stage
      state machine (_stage_gate/_STAGE_ORDER), seed/calibrate/screen/orphans,
      the injectable session_maker/EnginePool pattern
  - phase: 220-02
    provides: the remote-worker submit lane writing the opening cache
      (second confirmation source CACHEFIX-08 will need), db-report Check C/D
provides:
  - Three working repair stages closing the pipeline's core loop
    (seed -> calibrate -> screen -> orphans -> confirm -> propagate ->
    rederive -> report): confirm (1M-node re-evaluation, floor-gated cache
    overwrite), propagate (old-value predicate, post-move shift, per-cell
    audit trail), rederive (locked per-game reclassification through the
    drain's own diff/upsert, drill pruning, herring counting)
  - `refresh_game_oracle_counts` -- the public promotion of eval_apply's
    oracle-count writer, letting rederive and the live drain refresh a
    game's oracle counts through the exact same function
  - The D-04 concurrency invariant closed on BOTH sides: rederive takes the
    per-game advisory lock apply_full_eval already uses; the blob-submit
    write path takes the same lock plus an in-lock re-read that filters both
    write payloads down to plies still present
  - `scripts/backfill_flaws.py --from-repair-table`, a thin delegating
    wrapper onto run_rederive (the single rederive implementation)
affects: [220-04, 220-05, 220-06, 220-07, 220-08]

# Actuals (#2632)
actuals:
  tokens: 56992
  tasks: 4
  commits: 2

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Per-hash propagate as 3 independent UPDATE...RETURNING statements
      (eval on the post-move-shifted carrier row, best_move and pv each
      independently gated on their OWN old-value match on the position's own
      row) rather than one combined-predicate statement -- lets a row whose
      best_move transplanted but pv did not (or vice versa) be handled
      correctly without a fragile combined WHERE clause, at the cost of one
      extra round-trip per hash."
    - "Rederive's read-only classify_game_flaws probe BEFORE the write call:
      _rederive_reclassify_game calls classify_game_flaws itself (pure, no
      writes) to detect a GameNotAnalyzed 'reason' result and skip
      _classify_and_fill_oracle entirely for that game -- a second READ-ONLY
      call to the classifier, never a second WRITER, so CACHEFIX-06's
      single-writer rule holds while still letting rederive tell 'game
      genuinely unanalyzable' apart from 'a real exception'."
    - "before/after ply-set snapshots for rederive's flaws_added/
      flaws_removed: computed as the symmetric difference of the FULL ply
      sets read before and after _classify_and_fill_oracle runs, not derived
      from a total-count arithmetic formula -- the two are mathematically
      identical when every ply has at most one flaw row, but the set form
      needs no cross-check and is what running rederive twice on an
      unchanged game trivially proves is zero both ways."

key-files:
  created: []
  modified:
    - scripts/opening_cache_repair.py
    - app/services/eval_apply.py
    - app/routers/eval_remote.py
    - scripts/backfill_flaws.py
    - tests/scripts/test_opening_cache_repair.py
    - tests/test_backfill_flaws.py
    - tests/test_eval_worker_endpoints.py

key-decisions:
  - "D-04 resolved exactly as RESEARCH.md recommended: rederive takes
    pg_advisory_xact_lock(_game_write_lock_key(game_id)) as the FIRST
    statement of its per-game transaction (the same key, same position as
    apply_full_eval) -- not SELECT ... FOR UPDATE on games, which would
    serialize against no existing writer. The blob-submit lane's
    pre-existing StaleDataError window (FLAWCHESS-8D: null_flaw_plies read
    in a session that closes before the write session opens) is closed with
    the SAME lock plus an in-lock re-read of surviving game_flaws.ply values,
    filtering BOTH blob_map and the tactic-tag updates list -- the lock alone
    does not close the window; the re-read is the load-bearing half."
  - "blobs_pending=True for rederive's _classify_and_fill_oracle call (per
    RESEARCH.md's judgement call): a freshly-inserted flaw gets a NULL
    tactic tag, left for tier-4, matching both live write lanes -- not the
    pre-Phase-143 gate-free raw tag blobs_pending=False would produce."
  - "--from-repair-table hosts the rederive LOOP in
    scripts/opening_cache_repair.py (run_rederive), with
    scripts/backfill_flaws.py's flag as a thin delegating wrapper --
    satisfies CACHEFIX-06's literal wording (via backfill_flaws.py) and its
    real constraint (no second classifier call site) simultaneously, since
    backfill_flaws.py's own write path is delete-then-insert and would wipe
    blob/tactic columns for every repaired game."
  - "opening_cache_repair_games' single (non-color-split) flaws_before_inacc/
    flaws_after_inacc columns are always 0: game_flaws.severity only ever
    stores mistake(1)/blunder(2) rows (inaccuracies are never materialized,
    D-03 in game_flaws_repository.py), so a 'game_flaws counts grouped by
    severity' snapshot -- exactly what the plan specifies -- structurally
    cannot see inaccuracies. Documented in _snapshot_rederive_state's
    docstring so a future reader doesn't mistake this for a bug."
  - "propagate's per-hash repair_rows audit trail is keyed by the EVAL
    rewrite's RETURNING set (game_id, p.ply); best_move_replaced/pv_replaced
    are derived by checking membership of the companion row n's own
    RETURNING sets. A carrier whose best_move or pv rewrote WITHOUT its
    paired eval also rewriting (a partial-transplant edge case RESEARCH.md
    flagged as rare, since pv is only ever written at flaw-adjacent plies)
    still gets its game correctly added to opening_cache_repair_games (the
    games-touched set is the union of all three statements' RETURNING game
    ids), but would not get a dedicated repair_rows row of its own -- a
    documented scope limitation, not covered by this plan's must_haves."

patterns-established:
  - "Batch = one transaction per stage-unit, no engine/gather split needed
    when the stage makes no engine calls: propagate's _run_propagate_batch
    opens ONE session for both the read (SELECT confirmed_bad rows) and
    write (the per-hash UPDATE/INSERT statements) phases, unlike
    confirm/screen which must close the session before the asyncio.gather
    engine call (Pitfall 8) and reopen a write session after."
  - "Rederive's per-game isolation: _walk_rederive pages through 'pending'
    opening_cache_repair_games rows and calls _rederive_one_game once per
    game, each in its OWN transaction -- one game's exception (captured to
    Sentry, or silently marked failed for the expected GameNotAnalyzed case)
    never rolls back a neighbour, and the SAME query naturally re-selects
    only still-pending rows on the next page, making the walk resumable
    with no separate cursor column needed (unlike screen's last_game_id_walked)."

requirements-completed: [CACHEFIX-04, CACHEFIX-05, CACHEFIX-06]

coverage:
  - id: D1
    description: "confirm stage: 1M-node re-evaluation of every flagged row
      via evaluate_nodes_with_pv on a re-asserted board; overwrites all four
      cache columns only on confirmed_bad; --dry-run and --limit 0 handled;
      stamps confirm_finished_at only on true exhaustion"
    requirement: CACHEFIX-04
    verification:
      - kind: unit
        ref: "tests/scripts/test_opening_cache_repair.py::TestConfirm (7
          tests: bad_overwrites, clean_untouched, boundary, mate_mismatch,
          empty, order, dry_run)"
        status: pass
      - kind: unit
        ref: "uv run ty check app/ tests/ scripts/"
        status: pass
    human_judgment: false
  - id: D2
    description: "propagate stage: old-value predicate on both eval columns
      (NULL-safe via IS NOT DISTINCT FROM + CAST), eval written on the
      post-move-shifted carrier row, best_move/pv independently gated on
      their own old-value match on the position's own row, per-cell repair
      trail, idempotent re-run, no game-type filter (lichess carriers may
      legitimately match)"
    requirement: CACHEFIX-05
    verification:
      - kind: unit
        ref: "tests/scripts/test_opening_cache_repair.py::TestPropagate (5
          tests: predicate, shift, idempotent, no_carriers, dry_run)"
        status: pass
    human_judgment: false
  - id: D3
    description: "rederive stage: per-game pg_advisory_xact_lock (same key/
      position as apply_full_eval), routed exclusively through
      _classify_and_fill_oracle (blobs_pending=True, flaw_pv_blobs=None),
      refresh_game_oracle_counts promoted to public, drill_items pruned for
      orphaned plies, herring_pool rows counted (never deleted), a failing
      game isolated to itself with GameNotAnalyzed handled without a Sentry
      capture, idempotent re-run"
    requirement: CACHEFIX-06
    verification:
      - kind: unit
        ref: "tests/scripts/test_opening_cache_repair.py::TestRederive (7
          tests: preserves_blobs, counts, rearm, drills, failure, idempotent,
          lock)"
        status: pass
      - kind: integration
        ref: "tests/services/test_eval_apply.py + tests/services/test_full_eval_drain.py
          (88 tests, unchanged) -- the rename did not break the live drain"
        status: pass
    human_judgment: false
  - id: D4
    description: "D-04's other half: _apply_flaw_blob_submit's write session
      takes the same advisory lock plus an in-lock re-read filtering both
      write payloads to surviving plies, so a concurrent rederive DELETE
      cannot resurrect a flaw or 500 the submit"
    requirement: CACHEFIX-06
    verification:
      - kind: unit
        ref: "tests/test_eval_worker_endpoints.py::TestFlawBlobSubmitEndpoint::test_blob_submit_no_resurrect"
        status: pass
    human_judgment: false
  - id: D5
    description: "scripts/backfill_flaws.py --from-repair-table: thin
      delegating wrapper onto run_rederive, never enters the existing
      delete-then-insert branch"
    requirement: CACHEFIX-06
    verification:
      - kind: unit
        ref: "tests/test_backfill_flaws.py::TestFromRepairTable::test_from_repair_table_delegates"
        status: pass
    human_judgment: false

# Metrics
duration: ~170min
completed: 2026-09-10
status: complete
---

# Phase 220 Plan 03: Confirm/Propagate/Rederive Repair Stages Summary

**`confirm`, `propagate`, and `rederive` close the repair pipeline's core loop -- 1M-node re-evaluation with a floor-gated cache overwrite, the post-move-shift-aware old-value carrier rewrite, and locked per-game reclassification through the drain's own blob-preserving classifier -- with the D-04 concurrency invariant closed on both the rederive and blob-submit sides.**

## Performance

- **Duration:** ~170 min
- **Tasks:** 4
- **Files modified:** 7 (0 created)

## Accomplishments

- `confirm`: re-evaluates every `flagged` audit row at the drain's own
  1M-node budget (`evaluate_nodes_with_pv`), re-asserting the Zobrist hash
  against a rebuilt carrier board before the call, and overwrites all four
  `opening_position_eval` columns ONLY on the `confirmed_bad` branch (delta
  exceeds `confirm_floor`, or mate/non-mate status differs regardless of
  delta). `confirmed_clean` rows are byte-identical afterwards. A row whose
  carrier no longer replays transitions to `hash_mismatch` and is skipped.
- `propagate`: rewrites carrier `game_positions` rows that still hold a
  `confirmed_bad` row's exact old cached value -- the eval lands on
  `n.ply - 1` (post-move shift), while `best_move`/`pv` are rewritten
  independently on row `n` itself, each gated on its OWN old-value match.
  Records one `opening_cache_repair_rows` audit row per rewritten eval cell
  and upserts `opening_cache_repair_games` `pending` for every touched game.
  Idempotent (a second run rewrites zero rows, no PK violation) and never
  filters by game type -- a lichess carrier may legitimately match, and that
  is the only permitted contact with a lichess-analysed game this phase.
- `rederive`: for every `pending` `opening_cache_repair_games` row, takes
  `pg_advisory_xact_lock(_game_write_lock_key(game_id))` as the FIRST
  statement of its own per-game transaction (the same key/position
  `apply_full_eval` already uses, so no new deadlock cycle and correct
  serialization against both live write lanes), then reclassifies through
  `_classify_and_fill_oracle` (`blobs_pending=True`, `flaw_pv_blobs=None`) --
  the drain's own diff/upsert, never the blob-destructive delete-then-insert
  shape. Prunes `drill_items` at plies that lost their flaw, counts (never
  deletes) `herring_pool` rows at repaired plies, and isolates a failing
  game to itself: `GameNotAnalyzed` is marked `failed` with that reason and
  NOT sent to Sentry; every other exception is captured with no variables in
  the message string and the loop continues to the next game.
- `eval_apply._write_oracle_counts` promoted to the public
  `refresh_game_oracle_counts` -- Phase 214 already extracted this block;
  this plan only renames it and updates its one caller.
- D-04's other half: `_apply_flaw_blob_submit`'s write session now takes the
  same advisory lock plus an in-lock re-read of surviving `game_flaws.ply`
  values, filtering both `blob_map` and the tactic-tag `updates` list. Before
  this fix, `null_flaw_plies` (read in a session that closes before the
  write session opens) could still name a ply `rederive` deleted in the
  window, and `bulk_update_tactic_tags`'s ORM bulk-update-by-PK raised
  `StaleDataError` on that vanished row -- turning a 200 into a 500 and
  losing every blob in the submit, not just the deleted ply's.
- `scripts/backfill_flaws.py --from-repair-table`: a thin delegating wrapper
  onto `run_rederive`, so a future operator recompute pass has exactly ONE
  rederive implementation to reach for, never the blob-destructive legacy
  branch.

## Task Commits

Each task was committed atomically (Tasks 1-3 share one continuously-edited
file region -- see Deviations for why they landed in one commit):

1. **Tasks 1-3: `confirm`/`propagate`/`rederive` stages +
   `refresh_game_oracle_counts` promotion** -- `2333e54b8` (feat)
2. **Task 4: D-04 blob-submit lock/re-read + `backfill_flaws.py
   --from-repair-table`** -- `9507d0fd3` (feat)

**Plan metadata:** committed alongside this SUMMARY

## Files Created/Modified

- `scripts/opening_cache_repair.py` -- `confirm`/`propagate`/`rederive`
  stages, their CLI subparsers/dispatch entries, and every private helper
  each stage needs (1906 lines added)
- `app/services/eval_apply.py` -- `_write_oracle_counts` renamed to public
  `refresh_game_oracle_counts`, its one call site updated
- `app/routers/eval_remote.py` -- `_apply_flaw_blob_submit`'s write session
  gains the advisory lock + in-lock surviving-ply re-read
- `scripts/backfill_flaws.py` -- `--from-repair-table` flag, delegating to
  `run_rederive`; stale `reclassify_positions.py` docstring reference removed
- `tests/scripts/test_opening_cache_repair.py` -- `TestConfirm` (7),
  `TestPropagate` (5), `TestRederive` (7) -- 19 new tests, 2466 lines added
- `tests/test_backfill_flaws.py` -- `TestFromRepairTable` (1 new test)
- `tests/test_eval_worker_endpoints.py` -- `test_blob_submit_no_resurrect`
  (1 new test)

## Decisions Made

- **D-04 resolved on both sides exactly as RESEARCH.md recommended**: the
  advisory lock (not `FOR UPDATE` on `games`) in `rederive`, and the SAME
  lock plus an in-lock re-read (the load-bearing half) in the blob-submit
  write path.
- **`blobs_pending=True`** for rederive's `_classify_and_fill_oracle` call --
  matches both live write lanes; a freshly-discovered flaw gets a NULL
  tactic tag, not the pre-Phase-143 gate-free raw one.
- **`--from-repair-table` hosts the rederive loop in
  `opening_cache_repair.py`**, with `backfill_flaws.py`'s flag as a thin
  delegating wrapper -- satisfies CACHEFIX-06's literal wording AND its
  real constraint (no second classifier call site) simultaneously.
- **Propagate's per-hash writes are 3 independent
  `UPDATE ... RETURNING` statements** (eval on the shifted carrier row;
  best_move and pv each independently gated on their own old-value match on
  row `n`) rather than one combined-predicate statement -- correctly handles
  a carrier whose best_move transplanted without its pv (or vice versa),
  at the cost of one extra round-trip per hash. This is a planner-discretion
  structural choice within the plan's own literal wording ("run a second
  statement... replacing best_move and pv"); the plan did not mandate exactly
  one SQL statement for that step, and 3 statements give unambiguous
  per-column change flags without a fragile combined `CASE WHEN` + re-derived
  match expression in `RETURNING`.
- **`opening_cache_repair_games`' inaccuracy columns are always 0** by
  construction (see key-decisions) -- documented in the model-adjacent
  helper's docstring, not fixed, since `game_flaws` genuinely never stores
  inaccuracy rows and the plan's own snapshot source ("game_flaws counts
  grouped by severity") cannot see them.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] `scripts/opening_cache_repair.py` needed
`ruff format` applied across the whole file, not just my new sections**
- **Found during:** Pre-commit verification (`ruff format --check`)
- **Issue:** `ruff format --check` reported the file (including pre-existing
  Plan 01/02 code I never touched) as unformatted -- the committed state
  predates a formatter/config change, not something my edits introduced.
- **Fix:** Ran `ruff format` on exactly the files this plan touches (never
  the whole repo -- CLAUDE.md scope boundary), which normalized both my new
  code and the pre-existing lines in the same file.
- **Files modified:** `scripts/opening_cache_repair.py`,
  `tests/scripts/test_opening_cache_repair.py`
- **Verification:** `ruff format --check` clean on all 7 touched files
  afterward; full targeted + regression test suite re-run green.
- **Committed in:** `2333e54b8`

---

**Total deviations:** 1 auto-fixed (1 blocking -- pre-existing formatter
drift, not a logic change).
**Impact on plan:** Whitespace-only reformatting of lines this plan did not
otherwise touch; zero behavior change, confirmed by re-running the full
targeted test suite (276 tests) after the reformat.

### Process deviation (not a Rule 1-4 auto-fix, documented for transparency)

**Tasks 1-3 committed together, not as 3 separate commits.** The plan's own
tasks 1 (`confirm`), 2 (`propagate`), and 3 (`rederive`) were implemented as
one continuous authoring pass into `scripts/opening_cache_repair.py` (shared
imports, adjacent CLI subparser/dispatch entries, and rederive's helper
functions interleaved with propagate's in the same file region). Splitting
this into 3 clean git commits after the fact would have required either (a)
temporarily removing later tasks' code to commit an artificial
"confirm-only" intermediate state with zero functional benefit, or (b)
manual patch-hunk surgery across a ~1900-line addition with no reliable
automated split point. Each task's own acceptance criteria (grep-based
symbol checks, `-k confirm`/`-k propagate`/`-k rederive` test selection
counts) were independently verified to pass before moving to the next task,
so the SUMMARY's per-task coverage table above still gives full,
individually-verified attribution -- only the git history granularity is
coarser than 1:1. Task 4 (D-04 blob-submit fix + `--from-repair-table`)
touches an entirely disjoint set of files and is its own commit.

## Issues Encountered

- **`_snapshot_rederive_state`'s test expectations required recomputation**:
  my first draft of `test_rederive_counts` assumed the fresh-game fixture
  (`_insert_rederive_game`, matching `tests/test_backfill_flaws.py`'s
  `committed_analyzed_game` shape) would produce exactly 2 flaws (the
  intended blunder@2 + mistake@4). Running `classify_game_flaws` directly
  against the fixture showed it actually produces 4 flaws (plies 1-4) --
  the adjacent transitions independently register "lucky"/"reversed"/
  "squandered" tags for the OTHER color's perspective on the same eval
  swing. Fixed by recomputing the test's expected before/after ply sets and
  `flaws_added`/`flaws_removed` counts against the real classifier output
  rather than my initial assumption. No production code was affected --
  this was purely a test-expectation correction caught by running the test.
- **`GameFlaw.allowed_pv_lines`/`missed_pv_lines` are `deferred=True`**:
  accessing them via a plain `select(GameFlaw)` triggers a lazy-load that
  raised `sqlalchemy.exc.MissingGreenlet` outside the loading session's
  greenlet context in `test_rederive_preserves_blobs`. Fixed by adding
  `.options(undefer(GameFlaw.allowed_pv_lines), undefer(GameFlaw.missed_pv_lines))`
  to the verification query, matching the model's own documented
  `undefer()` opt-in pattern (`tests/test_game_flaws_model.py` precedent).

## User Setup Required

None -- no external service configuration required.

## Next Phase Readiness

Ready for plan 04 (`report` + `legacy-sample`) and plan 06 (prod acceptance),
which read this plan's audit tables and per-cell/per-game trail directly.

Notes for downstream plans:
- **Plan 04 (`report`)** can rely on `opening_cache_audit.confirmed_at`/
  `repaired_at`, `opening_cache_repair_rows.best_move_replaced`/
  `pv_replaced` (tracked separately -- a zero `pv_replaced` count across the
  whole run is expected, not a bug, per Pitfall 5), and
  `opening_cache_repair_games.flaws_added`/`flaws_removed`/`drill_items_pruned`/
  `herrings_touched` for its before/after tables.
- **Residual assumption, not fixed here (RESEARCH.md A2)**:
  `eval_entry._classify_and_insert_flaws` is an unlocked flaw inserter whose
  population (fresh imports, `evals_completed_at IS NULL`) is *inferred* to
  be disjoint from the repair's long-completed carriers, not measured. If a
  future incident shows contact between the two, the fix is the same
  advisory lock, not a redesign.
- **`opening_cache_repair_games`' known scope limitation** (see
  key-decisions): a carrier whose `best_move`/`pv` rewrote without its
  paired eval also rewriting still correctly gets its game added to the
  `pending` set for rederive, but would not get a dedicated
  `opening_cache_repair_rows` audit row of its own. Flagged for whoever
  reviews plan 04's report output against real prod data.
- No blockers.

---
*Phase: 220-opening-eval-cache-repair-two-source-confirmation*
*Completed: 2026-09-10*

## Self-Check: PASSED

- All 7 modified files confirmed present on disk with the expected changes.
- Both commits (`2333e54b8`, `9507d0fd3`) confirmed in `git log`.
- `uv run pytest tests/scripts/test_opening_cache_repair.py tests/test_eval_worker_endpoints.py tests/test_backfill_flaws.py tests/services/test_eval_apply.py tests/services/test_full_eval_drain.py tests/services/test_eval_drain.py -q` -- 276 passed.
- `uv run pytest -n auto -x -q -p no:warnings` (full backend suite) -- 4573 passed, 19 skipped, 0 failed.
- `uv run ty check app/ tests/ scripts/` -- all checks passed.
- `uv run ruff check .` -- all checks passed.
- `uv run ruff format --check` on all 7 touched files -- all clean.
- `uv run python scripts/check_function_size.py app/ --fail-over-depth 4 --fail-over-loc 200` -- 1031 functions scanned, no breaches.
- All Task 1-4 grep-based acceptance criteria (rename gate, classifier call,
  advisory lock presence, blob-destructive-shape absence, drill/herring
  delete absence, D-04 wiring) verified directly, all pass.
