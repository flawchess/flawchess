---
quick_id: 260605-v6v
title: Rename flaw attribution tags + make tempo optional
date: 2026-06-05
status: complete
commits:
  - 3b659b48 refactor(quick-260605-v6v): rename flaw-attribution tags to final taxonomy
  - b78d11f0 test(quick-260605-v6v): update flaw tests for final taxonomy and at-most-one tempo
---

# Quick Task 260605-v6v — Summary

Renamed the flaw attribution taxonomy in the shipped Phase 106 backend to the final names locked in
`.planning/notes/flaw-tag-naming.md`, and made the tempo dimension optional. No DB migration (tags
are computed on-the-fly, never persisted).

> **Orchestration note.** The executor ran in an isolated git worktree that forked from the older
> `a1af4689` (phase-106-shipped) rather than the pre-dispatch HEAD, so the standard
> `worktree.cleanup-wave` merge refused on a base-mismatch guard. The two rename commits touch only
> `app/`+`tests/` code files, which the active `gsd/phase-107` branch had not modified since
> `a1af4689` (zero overlap), so they were cherry-picked cleanly onto `gsd/phase-107` as `3b659b48`
> + `b78d11f0` and the worktree was removed. The executor's original SUMMARY lived only in the
> worktree working tree and was recreated here.

## Changes

**Task 1 — production code**
- `app/services/flaws_service.py`: `FlawTag` Literal renamed (`unpunished`→`lucky-escape`,
  `from-winning`→`while-ahead`, `time-pressure`→`low-clock`, `hasty`→`impatient`,
  `knowledge-gap`→`considered`, `phase-opening`→`opening`, `phase-middlegame`→`middlegame`,
  `phase-endgame`→`endgame`). `_classify_tempo` return narrowed to `TempoTag | None`, returning
  `None` on missing clock/move-time (was a `knowledge-gap` fallback). `_build_tags` guards the tempo
  append. `_phase_tag` drops the `phase-` prefix. `TempoTag` narrowed to
  `low-clock | impatient | considered`.
- `app/services/library_service.py`: `_CHIP_ORDER` and `_TEMPO_TAGS` use new names. The dead
  `_PHASE_TAG_PREFIX` (the old `tag.startswith("phase-")` exclusion, which the prefix-drop would
  have silently broken — letting phase tags leak onto card chips) is replaced by a `_PHASE_TAGS`
  frozenset membership check in `_curate_chips`. `_PHASE_TAG_TO_KEY` is now an identity map (kernel
  emits final keys directly), kept for the typed membership check.
- `app/schemas/library.py`: `TagDistribution.tempo` docstring documents the at-most-one /
  unmeasured-remainder semantics (the tempo dict now sums to ≤ M+B flaws).

**Task 2 — tests**
- `tests/services/test_flaws_service.py`: tempo/attribution/phase assertions updated to new names;
  the two former `knowledge-gap`-fallback tests now assert `result is None`; new
  `test_no_tempo_tag_when_flaw_has_missing_clock_data` proves the structural change; the
  "exactly one tempo tag" invariant relaxed to `<= 1`.
- `tests/services/test_library_service.py`: chip-curation tests use new names; tempo-sum assertion
  relaxed to `<= total_flaws`.

## Out-of-scope guardrail honored

The unrelated **Endgames "time-pressure" feature** (10+ files) was NOT touched. Verified:
`git diff a1af4689..HEAD -- app/ tests/` contains no endgame/time-pressure-feature files.

## Verification

Backend gate GREEN:
- `ruff format --check`: 5 files already formatted
- `ruff check`: All checks passed
- `ty check app/ tests/`: All checks passed (zero errors)
- Executor full run: `pytest -n auto` → **2321 passed / 10 skipped**
- Post-cherry-pick re-run of the two affected test files on `gsd/phase-107`: **81 passed**

## Residual (intentional, minor)

Internal helper names (`_is_unpunished`) and a couple of code comments still use the old chess-
concept words; only the user-/API-facing tag *values* were in scope. Left as-is.
