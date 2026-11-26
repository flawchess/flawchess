---
phase: 257-facepalm-rate-library-stats
plan: 07
subsystem: docs
tags: [changelog, pre-merge-gate, facepalm]
status: complete

requires:
  - phase: 257-facepalm-rate-library-stats (plans 01-06)
    provides: the share chart, the Facepalm blunders card and the type tint described in the changelog
provides:
  - three user-facing CHANGELOG.md bullets under [Unreleased]
  - a green full pre-merge gate on the phase branch
  - D-06 and D-14 end-of-phase guard results
affects: []

actuals:
  tokens: 900
  tasks: 2
  commits: 1
plan_head_before: 9501872ed3ab2849d0fe2f0950e15bc0eda360d6
plan_head_after: 68fea07f0267be1d275a2225fa380bac305144df
commits: 1

key-files:
  created: []
  modified:
    - CHANGELOG.md

key-decisions:
  - "Changelog bullets state what the user sees, without probability wording (D-05) and without the two banned verdict names (D-14)"

requirements-completed: [D-05, D-06, D-14]

duration: 12 min
completed: 2026-11-20
---

# Phase 257 Plan 07: Changelog and pre-merge gate Summary

**Three user-facing changelog bullets (share chart, Facepalm blunders card, type tint) under [Unreleased], D-06 and D-14 guards proven, and the full CLAUDE.md pre-merge gate green on the phase branch.**

## Accomplishments

- `CHANGELOG.md` `[Unreleased]`: two `### Added` bullets (Facepalm share of blunders chart; Facepalm blunders card in You vs. your opponents) and one `### Changed` bullet (chips tinted by type: teal missed win, crimson allowed loss, on the Flaws tab, the analysis move list and the eval chart tooltip).
- D-06 guard: `app/repositories/blunder_check_repository.py` and `app/repositories/query_utils.py` show no diff against the merge base with `main`; `tests/repositories/test_blunder_check_repository.py` and `tests/test_query_utils.py` pass (51 tests), and the library facepalm filter tests pass (14 selected).
- D-14 guard: neither "chance blindness" nor "threat blindness" appears under `frontend/src` or in `CHANGELOG.md`.
- Full pre-merge gate, every step green, nothing skipped, baselined or loosened.

## Task Commits

1. `68fea07f0` docs(257-07): changelog bullets for the facepalm share chart, card and type tint

Task 2 changed no files: the gate found nothing to fix and ruff made no changes, so no style commit was needed.

## Gate Results

| Step | Result |
| ---- | ------ |
| `ruff format app/ tests/ scripts/ analysis/` | 630 files left unchanged |
| `ruff check . --fix` | all checks passed, no files changed |
| `ty check app/ tests/ scripts/` | all checks passed |
| `ty check analysis/` (analysis project) | all checks passed |
| `check_function_size.py app/ --fail-over-depth 4` | OK, 1667 functions, no breaches |
| `uv run pytest -n auto -x` | 7264 passed, 19 skipped |
| `npm run lint` | clean |
| `npm run build` | clean (tsc -b + vite) |
| `npm test -- --run` | 6661 passed |
| `npm run knip` | clean (only its two pre-existing configuration hints) |

## Deviations from Plan

None - plan executed exactly as written.

## Handed to UAT

These need the prod database or a post-release read, so the orchestrator or owner runs them; none blocks the phase. The dev browser checks from plans 03, 04 and 06 (type tint on the three surfaces, share chart hover and thin-TC fallback, Facepalm blunders card placement, three popovers, neutral bars) also remain deferred to phase UAT, together with the owner's confirmation that "The gap is too large to be chance." reads as a statement about the gap (D-05).

1. **Prod share-floor probe (D-03, research Open Question 1).** Open `bin/prod_db_tunnel.sh`, run `temp/facepalm-257/prod_share_probe.sql` through the `flawchess-prod-db` MCP (15 accounts with the most analyzed games, per TC; expect 1 to 3 s). Threshold: keep `FACEPALM_SHARE_MIN_SCORED = 50` when `max_step_below50` is routinely above about 0.08 while `max_step_at_or_above50` stays under about 0.06; otherwise report the numbers for an owner call. Note: `temp/` is gitignored, so the probe files live only in this checkout.
2. **Prod comparison EXPLAIN on the largest account (D-11 latency, research Open Question 2).** Replace `987654321` in `temp/facepalm-257/prod_comparison_probe.sql` with the id of the account with the most analyzed games and run it under `EXPLAIN (ANALYZE, BUFFERS)`. Threshold: the fenced facepalm comparison finishes in under about 1 s; above that, move the facepalm rows to their own endpoint in a follow-up so the Stats page TC switch does not wait on them.
3. **Post-deploy opponent-side read (D-12).** After the release that ships this phase: on flawchess.com, sign in as the owner (prod user 28), open Library, Stats, You vs. your opponents. Expect the opponent side of the Facepalm blunders card to show real, non-zero rates in each time control (opponent blunders are scored on prod; dev user 28 has only 144 of 5,624 opponent blunders scored, so dev reads near zero).

## Known Stubs

None.

## Threat Flags

None. T-257-10 mitigated: no diff on the D-06 readers plus their regression tests green. T-257-11: ruff made no changes.

## Self-Check: PASSED

- FOUND: CHANGELOG.md carries "Facepalm share of blunders" (1), "Facepalm blunders card" (1) and "allowed loss" (2) inside `[Unreleased]`.
- FOUND commit `68fea07f0` (ancestor of HEAD).
- Branch still `gsd/phase-257-facepalm-rate-library-stats`.
