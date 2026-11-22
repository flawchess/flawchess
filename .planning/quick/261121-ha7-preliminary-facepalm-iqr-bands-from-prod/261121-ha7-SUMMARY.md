---
phase: quick-261121-ha7
plan: 01
subsystem: library-stats
tags: [facepalm, zones, library-stats, frontend, backend]
requires:
  - SEED-261120-bzq (replaces these bands later)
provides:
  - app/services/facepalm_zones.py (provisional per-TC FACEPALM_ZONES registry)
  - banded facepalm bullets (has_zone true) on /library/facepalm-comparison
  - standard verdict colours, axis caption and "Typical gap among FlawChess players" popover copy for the facepalm tile and card
affects:
  - app/schemas/library.py
  - app/services/library_service.py
  - frontend/src/lib/gapBar.ts
tech-stack:
  added: []
  patterns: [symmetric_band registry reuse, withGapVerdict shared suffix, GapAxisCaption shared component]
key-files:
  created:
    - app/services/facepalm_zones.py
    - tests/services/test_facepalm_zones.py
    - frontend/src/components/library/stats/GapAxisCaption.tsx
  modified:
    - app/schemas/library.py
    - app/services/library_service.py
    - tests/services/test_flaw_comparison.py
    - frontend/src/lib/gapBar.ts
    - frontend/src/lib/flawComparisonMeta.ts
    - frontend/src/types/library.ts
    - frontend/src/components/library/stats/GapPopover.tsx
    - frontend/src/components/library/stats/facepalmRangeNote.ts
    - frontend/src/components/library/stats/FacepalmCard.tsx
    - frontend/src/components/library/stats/FlawTiles.tsx
    - frontend/src/components/library/stats/ContextTagCards.tsx
    - CHANGELOG.md
    - .planning/seeds/SEED-261120-bzq-facepalm-benchmark-zones-and-clock-matrix.md
decisions:
  - "FacepalmMetric / FACEPALM_METRICS moved into the registry module (like FlawDeltaMetric) to avoid a schema/registry import cycle"
  - "Facepalm card gets the better / worse axis caption (orchestrator decision), via a shared GapAxisCaption component extracted from ContextTagCards (react-refresh forbids non-component exports from the .tsx)"
  - "get_facepalm_comparison docstring left untouched per D-06"
metrics:
  tasks: 3
  commits_note: see frontmatter commits
status: complete
actuals:
  tokens: 60000
  tasks: 3
  commits: 3
plan_head_before: 2afd6919806da0e86aa5064b7f97e4fd8bc3b7e9
plan_head_after: 7df5a40698676c47e6f3bb076a7f00fd4a3179b0
completed: 2026-11-21
---

# Quick 261121-ha7: Preliminary facepalm IQR bands from prod Summary

Provisional per-TC typical bands (prod-derived symmetric IQR/2 around 0, 12 pinned half-widths) for the three facepalm rows, with the standard red/green verdict, a better/worse axis caption on the card, and "Fewer is better." plus "Typical gap among FlawChess players" popover copy.

## What was done

- **Task 1 (d9599c8ef)**: new `app/services/facepalm_zones.py` (`FACEPALM_ZONES`, `facepalm_zone`, `FacepalmMetric`, `FACEPALM_METRICS`, reusing `ZoneBand`/`symmetric_band`); `FacepalmBullet.has_zone` default True; `_build_facepalm_bullet`/`_compute_facepalm_bullets` take the TC and set the band on both return paths. Registry test pins all 12 half-widths; flaw-comparison DB tests flipped (blitz vs rapid literal spot checks).
- **Task 2 (27bcb5bb8)**: `noVerdict` opt-out and `omitDirection` removed; `withGapVerdict` added to `gapBar.ts` and used by `rangeLine` and `facepalmRangeNote`; tile and card colour significant out-of-band gaps (tile number keeps `FACEPALM_BAND_SWATCH`); card gets `GapAxisCaption` (`context-card-facepalm-axis`); tests rewritten, section axis count 4 -> 5.
- **Task 3 (7df5a4069)**: seed update note and one CHANGELOG `### Changed` bullet (appended at the end of the first `### Changed` list in `[Unreleased]`).

## Deviations from Plan

- **Orchestrator decision 1 (not in the plan):** the Facepalm card now carries the better / worse axis caption. To share the caption without a react-refresh violation, extracted `GapAxisCaption.tsx` and made `ContextTagCards` use it. The card's "closed card text" test no longer bans "better / worse" words; `LibraryStatsSections` axis-count assertions went 4 -> 5 (test renamed "five cards"). The `ContextTagCards` docstring now says the trailing card carries its own caption.
- Tests were written before the implementation but the RED run was not executed as a separate step (tests were written, implementation followed, then the combined GREEN run); no impact on results.
- No other deviations; D-06 guard: `git diff 2afd69198 -- app/services/library_service.py` touches neither `get_facepalm_comparison` nor `fetch_facepalm_comparison` (0 matching diff lines).

## Items for the owner / merge time

1. **Stale docstring (D-06):** `get_facepalm_comparison` in `app/services/library_service.py` still says "three neutral rows" (~L1950 at plan time). Deliberately untouched to keep the Phase 258 surface clean; fix when this branch merges after Phase 258.
2. The earlier `### Added` CHANGELOG bullet for the card still says "These rows have no typical range yet" (documents release #496; not edited per plan).
3. Phase 258 is running in the main checkout; this branch must squash-merge after it and re-run the full pre-merge gate then.

## Gate results (worktree, branch quick/facepalm-prelim-bands)

- `ruff format app/ tests/ scripts/ analysis/`: no changes after final commit
- `ruff check . --fix`: all checks passed
- `ty check app/ tests/ scripts/`: all checks passed
- `ty check analysis/` (analysis venv): all checks passed
- `check_function_size.py app/ --fail-over-depth 4`: OK, no breaches
- `pytest -n auto -x` (full): 7295 passed, 20 skipped
- `npm run lint`: clean; `npm run build`: success; `npm run knip`: exit 0 (two pre-existing configuration hints only)
- `npm test -- --run` (full): 377 files, 6703 tests passed

## Known Stubs

None.

## Threat Flags

None: only constant zone fields in an existing authenticated response; no new endpoints or inputs.

## Self-Check: PASSED

- app/services/facepalm_zones.py, tests/services/test_facepalm_zones.py, frontend/src/components/library/stats/GapAxisCaption.tsx exist.
- Commits d9599c8ef, 27bcb5bb8, 7df5a4069 are on quick/facepalm-prelim-bands (3 commits since 2afd69198).

## Re-run on the Phase 259 model (2026-11-22)

After Phase 259 (facepalm score on stored scalar inputs, refit coefficients) the quartiles were
re-measured on prod with the same basis and gates; see CONTEXT.md "Re-run on the Phase 259 model".
`FACEPALM_ZONES`, the pinned half-widths in `tests/services/test_facepalm_zones.py` and the blitz
spot checks in `tests/services/test_flaw_comparison.py` were updated. The branch was rebased onto
main (Phases 258 and 259) first; conflicts in `app/schemas/library.py`, `library_service.py`, the
FacepalmCard test, CHANGELOG and STATE were resolved, and the stale "three neutral rows" docstring
in `get_facepalm_comparison` now reads "banded".

