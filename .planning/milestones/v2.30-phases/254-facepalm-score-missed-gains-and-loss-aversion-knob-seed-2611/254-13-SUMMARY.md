---
phase: 254-facepalm-score-missed-gains-and-loss-aversion-knob-seed-2611
plan: 13
subsystem: backend
tags: [facepalm-score, game_flaws, maia, backfill, line_material]
requires:
  - phase: 254-12
    provides: "Refit shipped; drop cycle branch reopened off origin/main"
provides:
  - "The post-commit hook and every backfill mode (full, spread, line, pre) write facts only: no stored facepalm_score, no legacy line_loss_* values"
  - "GameMaiaScore.scores_set computed in memory with the Python twin at FACEPALM_DRILL_LAMBDA"
  - "line_material no longer maps facts onto the legacy columns (LINE_LOSS_COLUMNS, LINE_MATE_PLY_COLUMN, LineFacts.as_columns removed)"
affects: [254-17, 254-14]
plan_head_before: e09d3ba577b473963495dff11b111b045c1be6bf
plan_head_after: dfca9d6a9988697c056e237899516b56734bb6b2
commits: 3
actuals:
  tokens: 14500
  tasks: 2
  commits: 3
tech-stack:
  added: []
  patterns:
    - "A row builder never carries a derived score: the backfill report's scored count is recomputed per row from the facts (row value, else the stored input)"
key-files:
  created: []
  modified:
    - app/services/maia_flaw_stats.py
    - app/repositories/game_flaws_repository.py
    - app/services/maia_flaw_scoring.py
    - app/services/line_material.py
    - scripts/backfill_maia_flaws.py
    - tests/services/test_maia_flaw_scoring.py
    - tests/services/test_line_material.py
    - tests/scripts/test_backfill_maia_flaws.py
key-decisions:
  - "FACEPALM_COLUMNS now lists five fact columns (maia_reply_spread, line_mate_ply, played_line_material, best_line_material, best_line_mate_ply); line_mate_ply is kept because facepalm_expr still reads it"
  - "_facepalm_values lost its played_prob and pre parameters (they only fed the stored score); _stored_pre was removed; the stored inputs stay on FlawMaiaInput for the in-memory scored count"
  - "scores_set is computed by _row_score per in-scope row, falling back to the stored inputs for keys a spread or line row does not write; a pre-mode row has no line facts and counts 0, as before"
  - "The model columns stay (plan 17 drops them): a re-score no longer clears stale values in facepalm_score / line_loss_* on rows downgraded from blunder"
requirements-completed: [D-01, D-02, D-19]
status: complete
coverage:
  - id: D1
    description: "Hook and every backfill mode write facts only, no stored score and no legacy line-loss key"
    requirement: "D-02"
    verification:
      - kind: unit
        ref: "tests/services/test_maia_flaw_scoring.py::test_rows_carry_facts_only"
        status: pass
      - kind: unit
        ref: "tests/services/test_maia_flaw_scoring.py::test_hook_full_mode_still_stamps"
        status: pass
  - id: D2
    description: "Backfill report scored count computed in memory at the drill lambda"
    requirement: "D-01"
    verification:
      - kind: unit
        ref: "tests/services/test_maia_flaw_scoring.py::test_scores_set_counts_in_memory"
        status: pass
      - kind: unit
        ref: "tests/services/test_maia_flaw_scoring.py::test_in_memory_score_equals_expression"
        status: pass
  - id: D3
    description: "Legacy column mapping removed from line_material; tests compare arrays"
    requirement: "D-19"
    verification:
      - kind: unit
        ref: "tests/services/test_line_material.py"
        status: pass
      - kind: integration
        ref: "uv run pytest -n auto -x (6610 passed, 19 skipped)"
        status: pass
---

# Phase 254 Plan 13: Writers stop, legacy mapping gone Summary

The hook and all four backfill modes now write only facts (reply spread, both signed material arrays, both mate plies, the pre inputs); the stored score and the five legacy line-loss columns are no longer written, and `line_material` no longer maps facts onto them.

## Accomplishments

- **Task 1 (tracer, `a9f9043a8`).** `FacepalmStats`, `null_facepalm_stats` and `FACEPALM_COLUMNS` drop `facepalm_score` and `line_loss_1/3/5/7/9`. `_facepalm_values` returns facts only and no longer needs the played probability or the pre inputs. `GameMaiaScore.scores_set` is computed per in-scope row by `_row_score`, which scores the row's facts with the Python twin at `FACEPALM_DRILL_LAMBDA` and falls back to the stored inputs for the keys a spread or line row does not carry (D-01). Module docstring updated (no stored score, five fact columns).
- **Task 2 (`78d05c1ce`).** `LINE_LOSS_COLUMNS`, `LINE_MATE_PLY_COLUMN` and `LineFacts.as_columns` removed; `LINE_LOSS_DEPTHS` and every counting rule kept. Tests compare `material_array()` and `mate_ply` against the stored arrays (new `_fact_columns` helper in two test modules).
- **Docstring follow-up (`dfca9d6a9`).** `scripts/backfill_maia_flaws.py` module docstring no longer claims the legacy columns or the score are written (comment-only change).
- New tests: `test_rows_carry_facts_only`, `test_scores_set_counts_in_memory`, `test_hook_full_mode_still_stamps`, `test_in_memory_score_equals_expression` (replaces `test_stored_score_equals_expression`, now also pins that the stored column stays NULL).

## Verification

- Task 1 verify, `uv run pytest tests/services/test_maia_flaw_scoring.py tests/services/test_maia_flaw_stats.py -n auto -q` (run with test_line_material): 150 passed, exit 0
- Task 2 verify, `uv run pytest tests/services/test_line_material.py tests/scripts/test_backfill_maia_flaws.py -n auto -q` (run together with the two Task 1 files): 189 passed, exit 0
- Key check script (no `facepalm_score` / `line_loss_*` in `FacepalmStats` or `FACEPALM_COLUMNS`): exit 0
- `grep -rnE "as_columns\(|LINE_LOSS_COLUMNS" app scripts tests --include='*.py' | wc -l`: 0 (baseline 16 in 5 files)
- `uv run ty check app/ tests/ scripts/`: all checks passed; `check_function_size.py app/ --fail-over-depth 4`: OK, no breaches; `ruff check .` and `ruff format --check`: clean
- `uv run pytest -n auto -x`: 6610 passed, 19 skipped

## Deviations from Plan

None in behaviour. Two small notes:

- **[Rule 3 - blocking] Test seeds.** `_STALE_FACEPALM` still seeds the legacy columns (they exist until plan 17), but readers compare only `FACEPALM_COLUMNS`, so a `_PRIOR_FACEPALM_FACTS` view was added for the survivor assertions in the reclassify tests.
- **Docstring edit outside the plan's file list.** `scripts/backfill_maia_flaws.py` was touched for its docstring only; no behaviour change.
- Not run (not in the plan's gate for this plan, frontend untouched): frontend lint/build/test and `knip`.

## Known Stubs

None.

## Threat Flags

None. T-254-44 mitigated: the report's scored count is computed in memory and pinned by `test_scores_set_counts_in_memory`.

## Notes for plan 17

- The ORM attributes `GameFlaw.facepalm_score` and `line_loss_*` still exist and are still read by `scripts/copy_line_material.py`, `scripts/blunder_check/fit_facepalm.py`, `tests/facepalm_seed.py` consumers and a few tests; this plan did not touch them.
- After this release, rows rescored by the hook keep whatever stale values the legacy columns already held (they are not cleared any more).

## Self-Check: PASSED

Commits `a9f9043a8`, `78d05c1ce`, `dfca9d6a9` are on `gsd/phase-254-facepalm-score-missed-gains-and-loss-aversion-knob-seed-2611`; modified files exist; full suite green.
