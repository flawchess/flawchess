---
phase: 254-facepalm-score-missed-gains-and-loss-aversion-knob-seed-2611
plan: 05
subsystem: blunder-check-tooling
tags: [facepalm-score, miss-labels, blind-sampler, stratification, read-only-prod]
requires:
  - phase: 254-01
    provides: "line_facts / best_line_facts and the signed 9-slot LineFacts"
  - phase: 254-04
    provides: "metrics.material_type / MIN_MISSED_GAIN, facepalm_features parse_labels / PolicyFn / DB_TARGETS"
  - phase: 254-16
    provides: "best_move_uci and pre_blunder_spread (one pre-blunder policy call gives best_prob and pre_spread)"
provides:
  - "scripts/blunder_check/miss_labels.py: read-only blind stratified miss sampler (about 40 pure misses, about 10 mixed rows) writing a blind sheet and a hidden key file"
  - "Set id 7 sheet columns n, set, elo, move, link, label (label empty): parse_labels reads it like any label file, so facepalm_features.py --labels takes it next to the 180 existing labels"
  - "Key file n -> game_id, ply, played_3, best_3, missed, best_prob, pre_spread, material_type, stratum (gitignored temp/)"
affects: [254-07, 254-11]
tech-stack:
  added: []
  patterns:
    - "Stratification as pure functions over derived candidates (cells, quotas, same-bucket borrowing) so it is testable without a database or Maia"
    - "Cheap prefilters (excluded game, rating) before the PGN replay; stability, material type and the policy call only after"
key-files:
  created:
    - scripts/blunder_check/miss_labels.py
    - tests/scripts/test_miss_labels.py
  modified: []
key-decisions:
  - "Stable line = the stored pv has at least MIN_STABLE_LINE_PLIES (3) tokens, or the replayed line ends in a checkmate of either side (is_stable_line(pv, ends_in_mate=...)); the best pv counts the best move as its first ply, the refutation pv starts after the blunder"
  - "The pre-blunder spread uses pre_blunder_spread from maia_flaw_stats (plan 16) and the best move best_move_uci, so the sampler's inputs are the ones the hook stores"
  - "A short cell borrows only from the other cells of its OWN missed-size bucket (nearest tertile first); a bucket with no supply stays short and is reported (unfilled), never padded from another bucket"
  - "Tertile cuts are computed from the pure-miss pool's own best_prob values (index n*k/3), a value equal to a cut goes to the upper tertile; the remainder of the 40 over 12 cells goes to cells that have supply"
  - "Mover rating is the user's raw platform rating at game time read in SQL (user-side blunders only), the same unit as the elo column of the 180 existing labels; Maia gets the pinned Elo"
  - "A candidate whose best move is outside Maia's policy, or with no policy, is dropped and counted (cannot be placed in a tertile)"
requirements-completed: [D-14, D-15, D-16]
coverage:
  - id: D1
    description: "D-14: blind sheet with exactly the BLIND_COLUMNS header, empty label, set 7, analysis links, no score or input; the hidden inputs and the stratum are in the key file"
    requirement: "D-14"
    verification:
      - kind: unit
        ref: "tests/scripts/test_miss_labels.py#test_blind_sheet_has_no_values"
        status: pass
      - kind: unit
        ref: "tests/scripts/test_miss_labels.py#test_key_file_holds_hidden_inputs"
        status: pass
    human_judgment: false
  - id: D2
    description: "D-14: 40 pure misses over 4 missed-size buckets x 3 best-move tertiles (3 or 4 per cell) plus 10 mixed rows; shortfall and unfilled rows reported"
    requirement: "D-14"
    verification:
      - kind: unit
        ref: "tests/scripts/test_miss_labels.py#test_stratify_spreads_missed_size_and_best_prob"
        status: pass
      - kind: unit
        ref: "tests/scripts/test_miss_labels.py#test_stratify_reports_shortfall"
        status: pass
      - kind: unit
        ref: "tests/scripts/test_miss_labels.py#test_stratify_reports_a_bucket_without_supply"
        status: pass
      - kind: unit
        ref: "tests/scripts/test_miss_labels.py#test_bucket_and_tertile_helpers"
        status: pass
    human_judgment: false
  - id: D3
    description: "D-15 / D-16: stable-line, rating and excluded-game filters; a short mate-ended line is kept; same seed gives the same sheet"
    requirement: "D-15"
    verification:
      - kind: unit
        ref: "tests/scripts/test_miss_labels.py#test_filters_drop_unstable_and_high_rated"
        status: pass
      - kind: unit
        ref: "tests/scripts/test_miss_labels.py#test_mate_ended_short_best_line_is_kept"
        status: pass
      - kind: unit
        ref: "tests/scripts/test_miss_labels.py#test_same_seed_same_sheet"
        status: pass
    human_judgment: false
  - id: D4
    description: "The sampler runs end to end against the read-only dev database with local Maia (TABLESAMPLE SQL, PGN replay, line facts, policy call, sheet and key written)"
    verification:
      - kind: other
        ref: "uv run --group maia-inference python scripts/blunder_check/miss_labels.py --db dev --sample-percent 100 --pure-misses 8 --mixed 2 --max-rating 3000 --out temp/blunder-check/miss-labels-dev.tsv --key-out temp/blunder-check/miss-labels-dev-key.json (exit 0)"
        status: pass
    human_judgment: false
  - id: D5
    description: "Whether the real prod draw yields enough pure misses in the rare buckets (5-8, 9+) and the owner can label the sheet blind"
    verification: []
    human_judgment: true
    rationale: "The prod draw is the orchestrator's job in plan 07; supply per cell is only known from a real prod run and the summary line's shortfall"
duration: ~75 min (start time not captured, estimate)
completed: 2026-11-14
status: complete
plan_head_before: 56996ae9be480797a1be511220d65365df594d56
plan_head_after: afffd25091314387a5680ce7978442af568e44f9
commits: 3
actuals:
  tokens: 11200
  tasks: 2
  commits: 3
---

# Phase 254 Plan 05: Blind stratified miss sampler Summary

The D-14 / D-15 sampler is one command: it reads user-side blunders of movers rated below 2000 from a TABLESAMPLE of games through the read-only engine, keeps rows whose best and refutation lines are stable, classifies them with `material_type`, stratifies the misses over missed size x best-move probability, and writes a blind sheet plus a hidden key file.

## Accomplishments

- **Sampler (D-15, D-16).** `miss_labels.py` selects user-side blunders (severity blunder, `~is_opponent_expr`) from `TABLESAMPLE SYSTEM (:pct) REPEATABLE (:seed)` over games with the mover's rating (below `MAX_MOVER_RATING = 2000`), `game_positions.pv` and `best_move` at the flaw ply and `pv` at ply + 1, on the calibration platforms, through `make_readonly_engine` (one connection, read-only, no write statement). Python then drops excluded games (every `--exclude-labels` TSV, default the 180 existing labels) and high-rated movers, replays the PGN (`replay_flaw_boards`), computes `line_facts` and `best_line_facts`, drops rows where either stored line is shorter than `MIN_STABLE_LINE_PLIES = 3` and does not end in mate, classifies with `material_type`, and makes one Maia policy call (at the mover's pinned Elo) for pure misses and mixed rows to get `best_prob` and `pre_spread`.
- **Stratification (D-14).** `stratify` fills `MISSED_SIZE_BUCKETS` (1-2, 3-4, 5-8, 9+; a best mate within `LINE_DEPTH` counts in 9+) x three best-move tertiles (cuts from the pool's own distribution) with 3 or 4 rows per cell for 40 pure misses, plus 10 mixed rows drawn without strata. A short cell borrows from the nearest other cell of its own size bucket; the shortfall per cell and the rows no cell of the bucket could give (`unfilled`) are in the summary line. The result is shuffled with the seed so the sheet order hides the stratum; the same seed and pool give a byte-identical sheet whatever order the pool arrived in.
- **Blind output (D-14).** The sheet header is exactly `n, set, elo, move, link, label` with set `7`, the mover's raw rating, the SAN move, `https://flawchess.com/analysis?game_id=<id>&ply=<ply>` and an empty label (no score, no input, no stratum, no usernames). The key JSON (default `temp/blunder-check/miss-labels-key.json`, gitignored) maps n to game_id, ply, played_3, best_3, missed, best_prob, pre_spread, material type and stratum. The links are written, never printed; the summary line carries counts only.
- **Dev smoke run.** Exit 0, sheet header is the BLIND_COLUMNS line (10 rows). Summary line: `candidates read 9977; dropped: unstable_line 3728; stable 6249; by material type: loses 1644, loses_and_misses 792, misses 1541, neither 2272; rows written 10 (1-2 / hard 1, 1-2 / mid 1, 3-4 / easy 1, 5-8 / easy 1, 5-8 / hard 1, 9+ / easy 1, 9+ / hard 1, 9+ / mid 1, mixed 2); shortfall: none; unfilled pure 0, mixed 0`. About 40% of dev rows are dropped as unstable lines, so Phase 252's repair status matters for the prod yield.

## Task Commits

1. **Task 1 (tracer): candidate rows to a blind sheet and a key file** - `e6d4ddc31` (feat)
2. **Task 2 (RED): failing tests for stratification, shortfall and bucket helpers** - `6ecc39eba` (test)
3. **Task 2 (GREEN): stratify by missed size and best-move probability, report shortfall** - `afffd2509` (feat)

Tracer gate: the tracer `<verify>` is automated-only, so it was re-run end to end (8 tests, `--help`, and the dev smoke run against the real read-only dev database with Maia) before expansion; it passed.

## TDD Gate Compliance (Task 2)

- **RED:** 4 tests failed for the planned reasons: the tracer's unstratified draw gave 1 stratum instead of 12 (`assert 1 == 12`), reported no shortfall (`not enough values to unpack`, `unfilled_pure` 0), and the helper stubs raised `NotImplementedError`. The `gsd_run check tdd-red-evidence` classifier was not run (no TAP/JUnit record captured); pytest output was inspected by hand. As in plan 16, the helper stubs were added in the RED commit so the failure is a behaviour failure and not an ImportError.
- **GREEN:** `uv run pytest tests/scripts/test_miss_labels.py -q` : 12 passed.
- **REFACTOR:** none.
- The filter and same-seed behaviours named under Task 2 were already implemented by the tracer (the pipeline needs them), so their tests are in the tracer commit and were green at the RED commit by construction; only the stratification, shortfall and helper tests were RED.

## Verification

- `uv run pytest tests/scripts/test_miss_labels.py -q` : 12 passed (acceptance `-k "blind or key or pipeline"`: 3 passed)
- `uv run python scripts/blunder_check/miss_labels.py --help` : exit 0
- `uv run ruff check` / `ruff format --check` on both files, `uv run ty check scripts/ tests/scripts/test_miss_labels.py` : clean
- Dev smoke run: exit 0, `temp/blunder-check/miss-labels-dev.tsv` first line is the BLIND_COLUMNS header

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] The pool's arrival order changed the draw**
- **Found during:** Task 1 (`test_same_seed_same_sheet`)
- **Issue:** the tracer `stratify` shuffled the pool in the order it was given, so two runs with the same seed and the same candidates in a different order wrote different sheets.
- **Fix:** `stratify` sorts the candidates by (game_id, ply) before any seeded draw.
- **Files modified:** scripts/blunder_check/miss_labels.py
- **Verification:** `test_same_seed_same_sheet` reverses the pool and compares the two sheets byte for byte.
- **Committed in:** `e6d4ddc31`

**Total deviations:** 1 auto-fixed (Rule 1). **Impact:** none on scope.

### Process notes

- A test for a short mate-ended best line (`test_mate_ended_short_best_line_is_kept`), a bucket-without-supply test and a summary-line test were added beyond the plan's behaviour list (12 tests instead of 7).
- A candidate whose best move is outside Maia's policy is dropped with a counted reason (the plan did not name this case; a row without a best_prob cannot be placed in a tertile).

## Issues Encountered

- The per-plan commit ledger under the git dir was not used (worktree tooling), so `plan_head_before` is the dispatch base SHA and `commits: 3` was measured with `git rev-list --count` against it.
- Duration is an estimate (start time not captured). `actuals.tokens` is chars/4 over the added lines of the three commits (44,671 chars).
- **Prod run not done (no prod access).** The real draw is the orchestrator's job in plan 07. Runtime note for it: the dev smoke read 9,977 candidate rows and took about 5 minutes (PGN replay dominates); the default `--sample-percent 0.5` on prod reads a comparable number of rows. If the summary line reports a shortfall in the 5-8 or 9+ buckets, raise `--sample-percent` or change `--seed` and rerun; the 252 repair status changes how many rows survive the stable-line filter.

## Known Stubs

None.

## Threat Flags

None. T-254-14 holds: the only engine is `make_readonly_engine` (read-only transactions, statement timeout, one connection) and the script contains no write statement. T-254-15 holds: the sheet carries rating, SAN move and an analysis link only; the key file defaults to gitignored `temp/` and `--db` URLs are never printed.

## Next Phase Readiness

Plan 07 can run `uv run --group maia-inference python scripts/blunder_check/miss_labels.py --db prod --out temp/blunder-check/miss-labels.tsv` (prod tunnel up), give the owner the sheet, keep the key file under `temp/`, and later pass the labelled TSV to `facepalm_features.py --labels` together with `leg2-labels-2026-11-11.tsv`. The key file lets plan 11 join each label back to its stratum and hidden inputs.

## Self-Check: PASSED

Created files exist (`scripts/blunder_check/miss_labels.py`, `tests/scripts/test_miss_labels.py`), commits `e6d4ddc31`, `6ecc39eba`, `afffd2509` are on HEAD, tests / ruff / ty pass, the dev smoke run exited 0.
