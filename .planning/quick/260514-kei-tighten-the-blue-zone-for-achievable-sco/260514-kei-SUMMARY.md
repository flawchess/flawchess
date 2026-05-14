---
type: quick
status: complete
completed: 2026-05-14
one_liner: Tighten Achievable Score Gap neutral band to ±5pp via a dedicated `achievable_score_gap` ZONE_REGISTRY entry, keeping Endgame Score Gap at ±10pp.
commits:
  - 951043ea
  - 5c303fc8
key_files_modified:
  - app/services/endgame_zones.py
  - scripts/gen_endgame_zones_ts.py
  - frontend/src/generated/endgameZones.ts
  - frontend/src/components/charts/EndgameOverallScoreGapRow.tsx
  - frontend/src/components/charts/EndgameOverallPerformanceSection.tsx
  - tests/services/test_endgame_zones.py
---

# Quick Task 260514-kei: Tighten Achievable Score Gap blue zone

## One-liner

Split the shared `SCORE_GAP_NEUTRAL_*` constant into per-row bands so the Achievable Score Gap row (Card 3) can tighten its neutral zone to ±5pp without affecting the Endgame Score Gap row (which stays at ±10pp). The Python `ZONE_REGISTRY` now carries a dedicated `achievable_score_gap` entry; the TS codegen mirrors it as `ACHIEVABLE_SCORE_GAP_NEUTRAL_MIN/MAX = -0.05 / 0.05` alongside the unchanged `SCORE_GAP_NEUTRAL_MIN/MAX = -0.1 / 0.1`.

## What changed

### Task 1 — Registry entry + codegen (commit `951043ea`)

- `app/services/endgame_zones.py`:
  - `MetricId` Literal alias extended to include `"achievable_score_gap"` (placed alphabetically near `"score_gap"`, with a brief comment citing the split rationale).
  - New `ZONE_REGISTRY["achievable_score_gap"]: ZoneSpec(typical_lower=-0.05, typical_upper=0.05, direction="higher_is_better")` inserted immediately after the `"score_gap"` entry to keep the two cohort-aware gap metrics colocated. Inline comment cites `reports/benchmarks-latest.md §3.1.5`, pooled IQR `[-3.9pp, +4.6pp]` rounded to ±5pp, and notes per-ELO stratification deferred (d=0.62 keep-separate verdict).

- `scripts/gen_endgame_zones_ts.py`:
  - New `_ACHIEVABLE_SCORE_GAP_SPEC = ZONE_REGISTRY["achievable_score_gap"]` pull near the existing `_SCORE_GAP_SPEC` pull.
  - Two new export lines emitted adjacent to the `SCORE_GAP_NEUTRAL_*` lines: `ACHIEVABLE_SCORE_GAP_NEUTRAL_MIN` and `ACHIEVABLE_SCORE_GAP_NEUTRAL_MAX`. Preserves the `*_NEUTRAL_MIN`/`*_NEUTRAL_MAX` naming convention.

- `frontend/src/generated/endgameZones.ts` (auto-generated, not hand-edited):
  - Now exports both `SCORE_GAP_NEUTRAL_MIN/MAX = -0.1 / 0.1` (unchanged) and `ACHIEVABLE_SCORE_GAP_NEUTRAL_MIN/MAX = -0.05 / 0.05` (new).

- `tests/services/test_endgame_zones.py`:
  - `test_all_scalar_metrics_have_entries` updated to include `"achievable_score_gap"` in the expected `ZONE_REGISTRY.keys()` set. Docstring extended to document the 260514-kei split.

### Task 2 — Wire the new band into ScoreGapRow + EndgameOverallPerformanceSection (commit `5c303fc8`)

- `EndgameOverallScoreGapRow.tsx`:
  - Removed direct imports of `SCORE_GAP_NEUTRAL_MIN/MAX` — the row no longer owns the band choice.
  - Added two required props: `neutralMin: number` and `neutralMax: number`. Both forwarded to `<MiniBulletChart>`. JSDoc on each prop notes they're signed score-gap units in `[-1, +1]`.
  - File-level docstring updated to remove the line claiming both rows "share … the neutral band from `SCORE_GAP_NEUTRAL_MIN/MAX`" and replaced with a note that the band is now caller-supplied (and which row gets which).

- `EndgameOverallPerformanceSection.tsx`:
  - Import block now pulls both `ACHIEVABLE_SCORE_GAP_NEUTRAL_*` and `SCORE_GAP_NEUTRAL_*` from `@/generated/endgameZones`.
  - `gapZoneColor` parameterized: `gapZoneColor(value, neutralMin, neutralMax)`. Comment above the function references the split rationale.
  - Two call sites: `gapColor` now passes `SCORE_GAP_NEUTRAL_*` (Endgame Score Gap stays ±10pp); `achievableGapColor` now passes `ACHIEVABLE_SCORE_GAP_NEUTRAL_*` (Achievable moves to ±5pp).
  - Both `<ScoreGapRow>` instances now pass matching `neutralMin`/`neutralMax`.
  - Achievable row's `<MetricStatPopover>` updated to use `ACHIEVABLE_SCORE_GAP_NEUTRAL_*` for `neutralLower`/`neutralUpper` so its narrated band matches the visible gauge band. Endgame row's popover keeps `SCORE_GAP_NEUTRAL_*` (unchanged).

## Verification

| Gate | Result |
|------|--------|
| `uv run ty check app/ tests/` | clean |
| `uv run pytest tests/ -x -q` | 1457 passed, 6 skipped |
| `uv run ruff check app/ tests/ scripts/` | clean |
| `uv run python scripts/gen_endgame_zones_ts.py && git diff --exit-code frontend/src/generated/endgameZones.ts` | no drift after restage (codegen idempotent) |
| `cd frontend && npm run build` | succeeds in 4.87s, no TS errors |
| `cd frontend && npm test -- --run` | 375 passed (32 files) |
| `cd frontend && npm run lint` | clean |
| `cd frontend && npm run knip` | clean (no dead exports introduced) |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 — Blocking issue] Updated `test_all_scalar_metrics_have_entries`**

- **Found during:** Task 1 verification (initial `pytest -x` run).
- **Issue:** The registry-sanity test in `tests/services/test_endgame_zones.py` asserts on the exact set of `ZONE_REGISTRY.keys()`. Adding a new entry without updating this guardrail caused 1 test failure (`AssertionError: Extra items in the left set: 'achievable_score_gap'`).
- **Fix:** Added `"achievable_score_gap"` to the expected set and extended the docstring to document the 260514-kei split rationale so the next reader has the source citation inline.
- **Files modified:** `tests/services/test_endgame_zones.py`
- **Commit:** `951043ea` (same atomic commit as the registry entry — keeping the guardrail in lockstep with the schema it guards).

No other deviations. Plan executed exactly as written.

## Self-Check: PASSED

- `app/services/endgame_zones.py` — FOUND, ZONE_REGISTRY has `achievable_score_gap` entry.
- `scripts/gen_endgame_zones_ts.py` — FOUND, emits new constants.
- `frontend/src/generated/endgameZones.ts` — FOUND, exports `ACHIEVABLE_SCORE_GAP_NEUTRAL_MIN/MAX = -0.05 / 0.05`.
- `frontend/src/components/charts/EndgameOverallScoreGapRow.tsx` — FOUND, `neutralMin`/`neutralMax` are required props, no `endgameZones` imports.
- `frontend/src/components/charts/EndgameOverallPerformanceSection.tsx` — FOUND, parameterized `gapZoneColor`, both rows pass row-specific bands.
- `tests/services/test_endgame_zones.py` — FOUND, expected key set includes `"achievable_score_gap"`.
- Commit `951043ea` — present in `git log`.
- Commit `5c303fc8` — present in `git log`.
