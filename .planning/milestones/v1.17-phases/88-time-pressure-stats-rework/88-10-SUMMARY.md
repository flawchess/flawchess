---
phase: 88-time-pressure-stats-rework
plan: 10
subsystem: api
tags: [endgame-analytics, time-pressure, codegen, drift-gate, gap-closure]

requires:
  - phase: 88
    provides: endgame_zones.py registry, gen_endgame_zones_ts.py codegen pipeline, MIN_GAMES_PER_TC_CARD + MIN_GAMES_PER_PRESSURE_BIN as endgame_service-local constants
provides:
  - MIN_GAMES_PER_TC_CARD and MIN_GAMES_PER_PRESSURE_BIN promoted to module-level Python constants in app/services/endgame_zones.py (single source of truth).
  - app/services/endgame_service.py imports the two constants from endgame_zones (top-level, PEP 8 compliant).
  - scripts/gen_endgame_zones_ts.py imports the two constants and emits them as `export const` declarations in the generated TS.
  - frontend/src/generated/endgameZones.ts now exports MIN_GAMES_PER_TC_CARD = 20, MIN_GAMES_PER_PRESSURE_BIN = 5, and a typed `getPressureBinBand(tc, quintile): { min, max } | null` helper.
  - Stale "PLACEHOLDER" / "placeholder until benchmarks" comments stripped from the generated TS — replaced with calibration attribution to reports/benchmarks-latest.md §3.3.1 / §3.3.3 (Phase 88-08, 2026-05-17).
affects:
  - 88-11 (consumes the new TS exports: replaces local `const MIN_GAMES_PER_TC_CARD = 20` / `MIN_GAMES_PER_PRESSURE_BIN = 5` in EndgameTimePressureCard.tsx with imports from endgameZones; replaces the unsafe `PRESSURE_BIN_SCORE_NEUTRAL_ZONES[tc][q as 0|1|2|3|4]!` pattern with `getPressureBinBand(tc, q)`).
  - 88-12 (PRESSURE_BIN_SCORE_NEUTRAL_ZONES sanity recalibration is unchanged — this plan only renamed comments, did not touch numeric values).

tech-stack:
  added: []
  patterns:
    - "Codegen-mirrored cross-stack constant: a Python module-level constant in endgame_zones.py is imported by scripts/gen_endgame_zones_ts.py and emitted as a TS `export const` literal. The CI drift gate (`git diff --exit-code` on the generated TS file) blocks any divergence."
    - "Generated typed helper with defensive narrowing: when a Record<Tuple, T> lookup needs `noUncheckedIndexedAccess`-safe access from a runtime number, codegen emits a thin helper that performs an explicit range check and returns `T | null` rather than asking each call site to use a non-null assertion."

key-files:
  created: []
  modified:
    - app/services/endgame_zones.py
    - app/services/endgame_service.py
    - scripts/gen_endgame_zones_ts.py
    - frontend/src/generated/endgameZones.ts

key-decisions:
  - "Constants imported at the top of endgame_service.py (PEP 8 / ruff E402 compliance), not at the original mid-file location of the deleted declarations. The plan's <action> step 2 suggested a comment at the import site; placed inline with the import block instead of mid-file to keep the import-graph linter clean."
  - "Comment swap on the CLOCK_GAP block (not in the plan's explicit grep gate but listed in <action> step 3): replaced 'placeholder until benchmarks §3.3.1' with calibration attribution. Same Phase 88-08 source, consistent with the PRESSURE_BIN swap, and folds into the IN-02 close."
  - "Zone numeric values held constant in this plan. The plan explicitly defers recalibration to Plan 88-12 ('Sanity-rerun against opp-quintile semantics in Plan 88-12' is now in the generated comment header)."

patterns-established:
  - "Lift-then-mirror: when a backend constant gets duplicated in frontend code and starts drifting, lift it to a Python source-of-truth module that the codegen already imports, then emit it as a TS export. Two-step migration: (1) backend rewires its import; (2) codegen adds the constant. Frontend rewiring to consume the new TS export is a separate plan (88-11) so the cross-stack boundary stays drift-clean at each merge."

requirements-completed:
  - POLISH-03

duration: ~15min
completed: 2026-05-17
---

# Phase 88.1 Plan 10: Codegen MIN_GAMES_* + getPressureBinBand helper Summary

**Codegen-pipeline gap closure: lifts the two endgame-time-pressure gating thresholds to `app/services/endgame_zones.py` (single Python source of truth), emits them via `scripts/gen_endgame_zones_ts.py` as TS const exports, adds a typed `getPressureBinBand(tc, q)` helper for defensive `noUncheckedIndexedAccess` lookups, and strips two stale "PLACEHOLDER" comments on already-calibrated zones.**

## Performance

- **Duration:** ~15 min
- **Started:** 2026-05-17 (Wave 2 of Phase 88.1)
- **Completed:** 2026-05-17
- **Tasks:** 2 (atomic per-task commits)
- **Files modified:** 4 (1 backend src, 1 backend service rewire, 1 codegen script, 1 generated TS)

## Accomplishments

- **WR-04 closed.** `MIN_GAMES_PER_TC_CARD = 20` and `MIN_GAMES_PER_PRESSURE_BIN = 5` now live in `app/services/endgame_zones.py` as the single source of truth. The backend service imports them from there; the codegen imports them from there; the generated TS emits them. The frontend `EndgameTimePressureCard.tsx` still carries local `const` shadows of the same values — that wire-up is explicitly Plan 88-11's scope, by the wave structure documented in this plan's frontmatter `affects`.
- **IN-02 closed.** Two stale comment fragments removed from the generated TS:
  - Line 91 (pre-regen): `// PLACEHOLDER values — calibrated by benchmarks §3.3.3 in Plan 08.` → replaced with attribution + Plan 88-12 sanity-rerun note.
  - Line 102 (pre-regen): `// Phase 88: Clock Gap scalar neutral band (placeholder until benchmarks §3.3.1).` → replaced with attribution.
- **IN-06 closed / WR-03 prepared.** New `getPressureBinBand(tc, quintile): { min, max } | null` helper in the generated TS provides explicit `0..4` range narrowing for downstream consumers. Plan 88-11 will swap the unsafe `PRESSURE_BIN_SCORE_NEUTRAL_ZONES[tc][q as 0|1|2|3|4]!` pattern in `EndgameTimePressureCard.tsx` for this helper.
- **Codegen drift gate clean.** `uv run python scripts/gen_endgame_zones_ts.py --check` exits 0 after regeneration. The diff against the prior generated file is purely additive (3 new exports + 1 helper function) and 2 comment swaps. No zone numeric values changed.

## Task Commits

1. **Task 1 (refactor): lift MIN_GAMES_* to endgame_zones.py** — `eaf40d58` (refactor)
2. **Task 2 (feat): codegen MIN_GAMES_* + getPressureBinBand helper** — `68df25bd` (feat)

The SUMMARY metadata commit follows below.

## Files Created/Modified

- `app/services/endgame_zones.py` — added two module-level constants (`MIN_GAMES_PER_TC_CARD: int = 20`, `MIN_GAMES_PER_PRESSURE_BIN: int = 5`) in the named-constants block alongside `NEUTRAL_PCT_THRESHOLD` / `NEUTRAL_TIMEOUT_THRESHOLD` / `PRESSURE_BIN_NEUTRAL_CAP`.
- `app/services/endgame_service.py` — deleted the local declarations (former lines 1250-1257) and added a top-level `from app.services.endgame_zones import (MIN_GAMES_PER_PRESSURE_BIN, MIN_GAMES_PER_TC_CARD)` next to the existing service-layer imports. Inline comment at the import site (`# Phase 88.1: MIN_GAMES_* lifted to endgame_zones.py for codegen sharing (WR-04).`).
- `scripts/gen_endgame_zones_ts.py` — added the two constants to the `from app.services.endgame_zones import (...)` block (with `noqa: E402` already present on the import); inside `_render()`, appended the two `export const` declarations and the `getPressureBinBand` helper between the `PRESSURE_BIN_SCORE_NEUTRAL_ZONES` block and the `CLOCK_GAP_NEUTRAL_MIN/MAX` block; replaced both PLACEHOLDER comment lines with calibration attribution.
- `frontend/src/generated/endgameZones.ts` — regenerated from the updated codegen script. Net change: +21 / -2 (3 new const exports + 1 new helper function + 2 comment swaps; zero numeric changes).

## Decisions Made

- **Import placement (Task 1):** the plan's `<action>` step 2 said "Keep an inline comment at the import site". The plan example showed the import mid-file at the old declaration site, but that would trip ruff E402 (`module-level import not at top of file`). Placed at the top with the other `from app.services.*` imports, keeping the comment inline as a block-level note. Backend ruff + ty + pytest all clean.
- **Clock-gap comment swap (Task 2):** the plan's grep gate (`grep -cE "PLACEHOLDER|placeholder until benchmarks" frontend/src/generated/endgameZones.ts` should be 0) requires removing both stale comments. Re-attributed both to the same Phase 88-08 benchmark calibration source for consistency.
- **Held zone numeric values constant:** the plan's `<action>` step 5 explicitly says "the diff must NOT touch any zone numeric value (calibration is held constant in this plan; Plan 88-12 owns recalibration)." Verified in the generated diff — only comment + additive-export changes.

## Deviations from Plan

None — plan executed as written. The only adjustment is the import-placement decision documented above (driven by ruff E402, which is a project-wide hard CI gate per CLAUDE.md).

## Issues Encountered

- **Frontend `node_modules` missing in the worktree.** Resolved by `npm install` (lockfile-based install, no new packages, no version drift). Required to run `npx tsc`, `npm run lint`, `npm run knip`, and `npm test`. This is a worktree-setup issue, not a plan deviation; flagged here because it's an extra side effect that future worktree-mode executors will encounter.

## User Setup Required

None — backend + codegen-only gap closure. Frontend consumption (replacing the local `MIN_GAMES_PER_*` literals in `EndgameTimePressureCard.tsx` with imports from `@/generated/endgameZones`, and replacing the unsafe `!` lookup with `getPressureBinBand`) is Plan 88-11.

The new TS exports (`MIN_GAMES_PER_TC_CARD`, `MIN_GAMES_PER_PRESSURE_BIN`, `getPressureBinBand`) are temporarily unused by application code — but knip is configured to ignore `src/generated/endgameZones.ts` (see `frontend/knip.json`), so this does not break CI.

## Verification

- `uv run ruff check .` → All checks passed.
- `uv run ruff format app/services/endgame_zones.py app/services/endgame_service.py` → 2 files left unchanged.
- `uv run ty check app/ tests/` → All checks passed.
- `uv run pytest tests/services/test_time_pressure_service.py tests/services/test_endgame_zones.py -x -q` → 63 passed in 0.16s.
- `uv run python scripts/gen_endgame_zones_ts.py` → regenerated successfully.
- `uv run python scripts/gen_endgame_zones_ts.py --check` → `OK: frontend/src/generated/endgameZones.ts is up to date.` (drift gate clean).
- `git diff --exit-code frontend/src/generated/endgameZones.ts` → exits 0 (post-commit).
- `cd frontend && npx tsc --noEmit -p tsconfig.app.json` → exits 0.
- `cd frontend && npm run lint` → exits 0.
- `cd frontend && npm run knip` → exits 0.
- `cd frontend && npm test -- --run` → 43 test files, 490 tests passed.
- Acceptance-criteria grep gates (Task 1, 4 / 4):
  - `grep -c "MIN_GAMES_PER_TC_CARD: int = 20" app/services/endgame_zones.py` → 1.
  - `grep -c "MIN_GAMES_PER_PRESSURE_BIN: int = 5" app/services/endgame_zones.py` → 1.
  - `grep -v '^#' app/services/endgame_service.py | grep -cE "^MIN_GAMES_PER_TC_CARD: int = 20|^MIN_GAMES_PER_PRESSURE_BIN: int = 5"` → 0.
  - `grep -c "from app.services.endgame_zones import" app/services/endgame_service.py` → 1.
- Acceptance-criteria grep gates (Task 2, 4 / 4):
  - `grep -c "export const MIN_GAMES_PER_TC_CARD = 20" frontend/src/generated/endgameZones.ts` → 1.
  - `grep -c "export const MIN_GAMES_PER_PRESSURE_BIN = 5" frontend/src/generated/endgameZones.ts` → 1.
  - `grep -c "export function getPressureBinBand" frontend/src/generated/endgameZones.ts` → 1.
  - `grep -cE "PLACEHOLDER|placeholder until benchmarks" frontend/src/generated/endgameZones.ts` → 0.

## Self-Check: PASSED

- `eaf40d58` (Task 1 refactor commit) — present in `git log` (verified: `git log --oneline -3` shows it).
- `68df25bd` (Task 2 feat commit) — present in `git log`.
- `app/services/endgame_zones.py` — modified, FOUND.
- `app/services/endgame_service.py` — modified, FOUND.
- `scripts/gen_endgame_zones_ts.py` — modified, FOUND.
- `frontend/src/generated/endgameZones.ts` — modified + regenerated, FOUND.

## Next Phase Readiness

Wave 2 of Phase 88.1 advances to Plan 88-11 next:

- Rewires `frontend/src/components/charts/EndgameTimePressureCard.tsx` to:
  - Import `MIN_GAMES_PER_TC_CARD` / `MIN_GAMES_PER_PRESSURE_BIN` from `@/generated/endgameZones` (delete the local `const` shadows on lines 40 + 43).
  - Replace the unsafe `PRESSURE_BIN_SCORE_NEUTRAL_ZONES[tc][q as 0|1|2|3|4]!` pattern with `getPressureBinBand(tc, q)` and handle the `null` return (closes WR-03).
  - Rename `cohort_score` → `opp_score` in the local `PressureQuintileBullet` TS type to match Plan 88-09's backend Pydantic rename (and update the "vs cohort" popover copy to "vs opponent").
- Plan 88-12 runs the benchmark sanity recalibration against the new same-game opp-quintile semantics (Plan 88-09's design pivot, D-07) — band shape is mathematically unaffected by the swap, but IQR values get re-confirmed.

---

*Phase: 88.1-time-pressure-stats-rework*
*Plan: 10*
*Completed: 2026-05-17*
