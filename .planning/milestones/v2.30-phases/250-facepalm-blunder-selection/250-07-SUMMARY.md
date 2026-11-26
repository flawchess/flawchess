---
phase: 250-facepalm-blunder-selection
plan: 07
subsystem: backfill
tags: [maia, facepalm-score, backfill, d-18, cutoff-checkpoint, hash-residue-shards]

requires:
  - phase: 250-facepalm-blunder-selection
    provides: "plan 05 hook scorer (_derive_post_blunder, _facepalm_values, FACEPALM_COLUMNS, mark_facepalm_*), plan 04 FACEPALM_MODEL, plan 01 line_facts"
  - phase: 247-maia-flaw-stats
    provides: "sharded stamp-as-checkpoint backfill script this plan extends"
provides:
  - "scripts/backfill_maia_flaws.py --mode spread: the Maia pass over base-stamped games, hook-identical values, stamp-as-checkpoint"
  - "scripts/backfill_maia_flaws.py --mode line --cutoff: the Maia-free, re-runnable line recompute (D-18)"
  - "ScoringMode spread / line in maia_flaw_scoring: _spread_row, _line_row, GameMaiaScore.spreads_scored / scores_set, write_game_maia_scores(..., line_cutoff=)"
  - "--status --mode spread and --status --mode line --cutoff counts for the operator plans"
affects: [250-08, 250-09, 250-10, Phase 252 pv repair]

actuals:
  tokens: 20288
  tasks: 2
  commits: 2
plan_head_before: 066beb8b16fcc03acd3823b07e33cac259506a75
plan_head_after: f75d9683ec9581164d2b9dc15ae931d620308dff

tech-stack:
  added: []
  patterns:
    - "A line pass whose checkpoint is a bound cutoff timestamp instead of an IS NULL stamp: re-runnable by design, resumable with the same value"
    - "One module constant per mode predicate (_SPREAD_PENDING_CLAUSE, _LINE_STALE_CLAUSE) shared by the selector and the status counts so they cannot drift"
    - "Derived stored values (played prob, spread) travel on FlawMaiaInput but stay out of the inputs fingerprint"

key-files:
  created: []
  modified:
    - app/services/maia_flaw_scoring.py
    - scripts/backfill_maia_flaws.py
    - tests/services/test_maia_flaw_scoring.py
    - tests/scripts/test_backfill_maia_flaws.py

key-decisions:
  - "FlawMaiaInput.stored_played_prob / stored_reply_spread are required fields (no default), like refutation_pv, so a new construction site cannot silently feed NULL into a score recompute; neither is in the fingerprint"
  - "line mode rows are built from _facepalm_values and drop the maia_reply_spread key, so the hook, the spread pass and the line pass share one value computation"
  - "A flaw whose board cannot be rebuilt gets NULL line keys in line mode (the stored values would describe a different position); a missing rating in spread mode keeps the line facts and leaves spread and score NULL, as the hook does"
  - "line_done_since_cutoff counts spread-stamped games with flaws and a line stamp at or after the cutoff, which includes games the live hook stamped after the cutoff"

patterns-established:
  - "The cutoff is a checkpoint: same value resumes, a later value is a new full recompute; it is parsed to an aware datetime, bound as :cutoff and echoed in the JSON report and progress log"

requirements-completed: [D-06, D-08, D-18]

coverage:
  - id: F1
    description: "--mode spread scores a base-stamped game's user blunders with the hook's scorer (stored played prob, one post-blunder inference per blunder), writes exactly the eight facepalm keys, leaves base values and the refutation pair untouched, sets the spread and line stamps, and a rerun selects 0 games"
    requirement: "D-08"
    verification:
      - kind: integration
        ref: "tests/scripts/test_backfill_maia_flaws.py#test_spread_mode_scores_and_stamps_base_stamped_game"
        status: pass
      - kind: unit
        ref: "tests/services/test_maia_flaw_scoring.py#test_spread_mode_rows_carry_only_facepalm_keys, test_spread_mode_no_rating_keeps_line_facts_and_skips_inference, test_write_spread_mode_sets_spread_and_line_stamps_only"
        status: pass
    human_judgment: false
  - id: F2
    description: "--mode line --cutoff recomputes line facts and score for spread-stamped games with a NULL or older line stamp, including rows that already hold values and blunders that had no line, without Maia"
    requirement: "D-18"
    verification:
      - kind: integration
        ref: "tests/scripts/test_backfill_maia_flaws.py#test_line_mode_recomputes_rows_that_already_hold_values, test_line_mode_blunder_without_a_line_gets_one_later, test_line_mode_selector_rules"
        status: pass
      - kind: unit
        ref: "tests/services/test_maia_flaw_scoring.py#test_line_mode_never_calls_maia_and_writes_only_line_keys"
        status: pass
    human_judgment: false
  - id: F3
    description: "The cutoff is the checkpoint: same cutoff resumes, it is required for line mode, rejected elsewhere, must carry an offset, and is a bound parameter never interpolated"
    requirement: "D-18"
    verification:
      - kind: integration
        ref: "tests/scripts/test_backfill_maia_flaws.py#test_line_mode_resumes_with_the_same_cutoff, test_line_mode_selector_binds_the_cutoff_never_interpolates_it, test_cli_cutoff_rules"
        status: pass
      - kind: unit
        ref: "tests/services/test_maia_flaw_scoring.py#test_write_line_mode_needs_a_cutoff_when_require_unstamped, test_write_line_mode_cutoff_decides_already_stamped"
        status: pass
    human_judgment: false
  - id: F4
    description: "The line-mode shard never calls start_maia or inference and exits 0 without Maia"
    requirement: "D-18"
    verification:
      - kind: integration
        ref: "tests/scripts/test_backfill_maia_flaws.py#test_line_mode_shard_never_starts_maia_and_exits_ok_without_it"
        status: pass
    human_judgment: false
  - id: F5
    description: "--status for spread and line modes prints the stamped / pending games and the user-blunder spread, score and qualifying counts"
    requirement: "D-08"
    verification:
      - kind: integration
        ref: "tests/scripts/test_backfill_maia_flaws.py#test_spread_status_counts, test_line_status_counts"
        status: pass
    human_judgment: false

duration: 13min
completed: 2026-11-13
status: complete
---

# Phase 250 Plan 07: Facepalm Backfill Modes (spread + line) Summary

**The backfill gets two separable passes for the facepalm columns: a Maia `--mode spread` over base-stamped games and a Maia-free, re-runnable `--mode line --cutoff` recompute, both through the hook's own scorer and both touching user-side blunders only**

## Performance

- **Duration:** 13 min
- **Started:** 2026-11-13T20:36:16Z
- **Completed:** 2026-11-13T20:49:02Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments

- `ScoringMode` gains `spread` and `line`. `_spread_row` computes the reply spread with one post-blunder inference per user blunder and the facepalm score from the STORED `maia_played_prob` (the base inference is not re-run); rows carry PK plus the eight `FACEPALM_COLUMNS`. `_line_row` needs no Maia and no rating: the six line keys and `facepalm_score` come from the stored line, `maia_played_prob` and `maia_reply_spread`, and `maia_reply_spread` is never written. Both reuse `_facepalm_values`, so the hook, the spread pass and the line pass cannot disagree.
- `write_game_maia_scores` checks and sets the stamps per mode (table in its docstring): spread checks `facepalm_spread_completed_at` and sets it plus the line stamp; line checks `facepalm_line_completed_at` against `line_cutoff` (stamp at or after it means already stamped) and sets only the line stamp; line with `require_unstamped` and no cutoff raises `ValueError`.
- `--mode spread`: constant clause `g.facepalm_spread_completed_at IS NULL AND g.maia_flaws_completed_at IS NOT NULL`, hash-residue shards, stamp-as-checkpoint, new report counters `spreads_scored/null`, `scores_set/null`.
- `--mode line --cutoff`: constant clause `(line stamp IS NULL OR line stamp < CAST(:cutoff AS timestamptz)) AND spread stamp IS NOT NULL`; the cutoff is parsed to an aware datetime (offset required), bound as `:cutoff`, threaded through shard entry, write and `ShardReport.cutoff`, and echoed in the progress log. Line mode skips `start_maia` and the exit-3 gate. Module docstring documents the two-pass design and both prod usage lines.
- `--status --mode spread` prints `spread_stamped_games spread_pending_games user_blunders_total user_blunders_with_spread user_blunders_with_score user_blunders_qualifying` (qualifying = `facepalm_score >= FACEPALM_SCORE_MIN`); `--status --mode line --cutoff X` prints `line_done_since_cutoff line_pending_games` plus the total / score / qualifying counts. Selector and status share the mode predicate constants.

## Task Commits

1. **Task 1: Tracer, --mode spread scores a base-stamped game's user blunders and stamps it** - `94a7632e4` (feat)
2. **Task 2: --mode line --cutoff, the Maia-free re-runnable recompute (D-18)** - `f75d9683e` (feat)

**Plan metadata:** committed separately (docs: complete plan)

Tracer gate: `human_verify_mode` is `end-of-phase` and the tracer's `<verify>` is automated-only, so it was re-run after the Task 1 commit work (both module suites, then the bounded dev run). Tracer verified end-to-end, expanded.

## Bounded dev runs (foreground, dev DB, user 28)

Task 1 (`--report-dir` pointed at the scratchpad so no report file lands in the repo):

- `--mode spread --workers 1 --user-id 28 --limit 20`: `total: games_selected=20 games_scored=20 games_stamped=20 ... games_write_failed=0 games_score_failed=0 ... spreads_scored=52 spreads_null=0 scores_set=0 scores_null=52 reason_refutation_missing=52`, exit 0. The 20 newest base-stamped games carry no ply + 1 best move or line on dev, so no score could be set (stored-line-too-short/missing blunders stay NULL by design).
- `--status --mode spread --user-id 28` after it: `spread_stamped_games=20 spread_pending_games=2860 user_blunders_total=5396 user_blunders_with_spread=52 user_blunders_with_score=0 user_blunders_qualifying=0`.
- A second bounded run with `--limit 200` (the acceptance criterion needs a value above 0): `total: games_selected=200 games_stamped=200 ... games_write_failed=0 games_score_failed=0 ... spreads_scored=358 spreads_null=0 scores_set=229 scores_null=129 reason_refutation_missing=94`, then `--status --mode spread --user-id 28`: `spread_stamped_games=220 spread_pending_games=2660 user_blunders_total=5396 user_blunders_with_spread=410 user_blunders_with_score=229 user_blunders_qualifying=59`.

Task 2:

- `--mode line --workers 1 --user-id 28 --limit 1` (no cutoff): usage + `error: --mode line requires --cutoff`, exit 2.
- `--mode line --cutoff 2026-11-13T20:46:13+00:00 --workers 1 --user-id 28 --limit 20`: exit 0, `games_stamped=20 ... games_write_failed=0 games_score_failed=0 ... spreads_scored=0 ... scores_set=0 scores_null=52` (same 20 line-less games).
- `--status --mode line --cutoff 2026-11-13T20:46:13+00:00 --user-id 28` after it: `line_done_since_cutoff=20 line_pending_games=200 user_blunders_total=5396 user_blunders_with_score=229 user_blunders_qualifying=59`.
- Resume with the same cutoff and `--limit 220`: exit 0, `games_selected=200 games_stamped=200 ... scores_set=229 scores_null=129` (the line pass reproduced the spread pass's 229 scores); status then `line_done_since_cutoff=220 line_pending_games=0 ... user_blunders_with_score=229 user_blunders_qualifying=59`; a further run with the same cutoff selected `games_selected=0`.

## Mutation check

`_LINE_STALE_CLAUSE` reduced to the line-stamp-IS-NULL form (the `< cutoff` branch disabled): 5 tests fail (`test_line_mode_selector_rules`, `test_line_mode_recomputes_rows_that_already_hold_values`, `test_line_mode_blunder_without_a_line_gets_one_later`, `test_line_mode_resumes_with_the_same_cutoff`, `test_line_status_counts`). Restored afterwards; the line tests are green again.

## Decisions Made

- `FlawMaiaInput.stored_played_prob` / `stored_reply_spread` have no defaults (same reasoning as plan 05's `refutation_pv`); `fingerprint_of` excludes them with a comment.
- Line rows reuse `_facepalm_values` and drop the spread key, rather than a second score computation.
- `_spread_row` uses `_flaw_board` + `_mover_elo` instead of `_flaw_context`, so a missing rating keeps the line facts and leaves only the spread and score NULL, exactly like the hook (with `_flaw_context` a no-rating blunder would have been written all-NULL, wiping settled line facts).
- A line-mode flaw with an unusable board (fen mismatch, unparseable PGN) is written with NULL line keys: stored values would describe a different position.
- `_start_maia_and_run` decides on `shard_kwargs["mode"]`, so the line pass runs on a box without onnxruntime or the model.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] `_spread_row` via `_flaw_context` would wipe line facts for unrated games**
- **Found during:** Task 1 design
- **Issue:** the plan names `_flaw_context` (board + Elo) for `_spread_row`; that helper returns `no_rating` before any line facts exist, so a spread-mode write would have overwritten valid line facts with NULL for a game whose mover has no rating, diverging from the hook.
- **Fix:** `_flaw_board` + `_mover_elo`; no rating keeps line facts, spread and score NULL. Covered by `test_spread_mode_no_rating_keeps_line_facts_and_skips_inference`.
- **Files modified:** app/services/maia_flaw_scoring.py
- **Committed in:** 94a7632e4

### Process notes (not behavior deviations)

- The service-layer line code (`_line_row`, `LINE_ROW_COLUMNS`, cutoff-aware `write_game_maia_scores`) was written in one pass with the spread code and therefore landed in the Task 1 commit; the script's line mode, its CLI, status, and all line tests are in the Task 2 commit.
- Task 2 is `tdd="true"`: the script-level tests were written first and observed failing (every `_run` / `_select` call raised `TypeError` on the not-yet-existing `cutoff` argument, plus the new line tests), but no separate RED commit was made because the RED state broke 20 pre-existing tests in the same file. pytest output has no supported `tdd-red-evidence` format, so the classifier was not run; the mutation check above is the stronger proof.
- The bounded dev runs used `--report-dir` in the session scratchpad instead of the default `reports/maia-flaws-backfill`, so no report JSON was added to the repo.

---

**Total deviations:** 1 auto-fixed (1 bug avoided in the plan's helper choice)
**Impact on plan:** None on scope. The spread pass now matches the hook for unrated games.

## Issues Encountered

- The first 20 newest base-stamped dev games have no usable lines, so the plan's `--limit 20` run could not reach `user_blunders_with_score > 0`; a `--limit 200` run did (229). Not a code issue.
- `facepalm_score` is a REAL column: a score equal to `FACEPALM_SCORE_MIN` (0.7) reads back just below it, so the status-count test uses `FACEPALM_SCORE_MIN + 0.1` for its qualifying row. Noted here because `facepalm_score >= FACEPALM_SCORE_MIN` consumers elsewhere share the property for borderline values.

## Verification

- `uv run pytest tests/scripts/test_backfill_maia_flaws.py tests/services/test_maia_flaw_scoring.py -x`: 102 passed.
- `uv run pytest -n auto -q`: 6315 passed, 19 skipped.
- `uv run ty check app/ tests/ scripts/`: all checks passed. `ruff format --check` and `ruff check .` clean. `check_function_size.py app/ --fail-over-depth 4`: no breaches.
- Acceptance greps: `grep -c '"spread"' scripts/backfill_maia_flaws.py` = 5, `grep -c "facepalm_spread_completed_at IS NULL"` = 1, `grep -c "CAST(:cutoff AS timestamptz)"` = 1, `grep -c "def _line_row" app/services/maia_flaw_scoring.py` = 1; the bound-parameter test asserts `params["cutoff"]` is the datetime and the compiled SQL contains neither its ISO string nor its year.

## Known Stubs

None.

## Threat Flags

None. T-250-19 mitigated (parsed to an aware datetime, bound as `:cutoff`, test proves no interpolation), T-250-20 held (pool_size=1 per shard, `--workers` and `--throttle-ms` unchanged, no concurrency defaults raised), T-250-21 unchanged (banner prints database and server before any work), T-250-22 held (advisory lock plus fingerprint including the ply + 1 line per game; the line pass is the safety net).

## Next Phase Readiness

- Plan 09 can run `--mode spread` on prod (`--workers 6 --throttle-ms 50` per the module docstring); plan 10 the line pass with a fixed cutoff after the Phase 252 repair.
- Blunders with a stored line shorter than `LINE_DEPTH` plies keep a NULL `facepalm_score` by design until the D-18 refit (owner decision, plan 04); `scores_null` in the reports counts them.

## Self-Check: PASSED

Both task commits (`94a7632e4`, `f75d9683e`) are ancestors of HEAD (measured count 2 from the ledger base `066beb8b1`); all four modified files exist; full suite, ty, ruff and the depth gate are clean.

---
*Phase: 250-facepalm-blunder-selection*
*Completed: 2026-11-13*
