---
phase: 88-time-pressure-stats-rework
plan: 14
subsystem: endgame-analytics
tags: [endgame-analytics, time-pressure, scope-amendment, schema-additive, A-3]
requires: [88-13]
provides:
  - top-zone-summary-stats-on-time-pressure-card
  - net-timeout-rate-zone-tint
affects:
  - app/schemas/endgames.py
  - app/services/endgame_service.py
  - frontend/src/types/endgames.ts
  - frontend/src/components/charts/EndgameTimePressureCard.tsx
  - tests/services/test_time_pressure_service.py
  - frontend/src/components/charts/__tests__/EndgameTimePressureCard.test.tsx
  - frontend/src/components/charts/__tests__/EndgameTimePressureSection.test.tsx
  - CHANGELOG.md
tech-stack:
  added: []
  patterns:
    - "_ClockAggregate slot-dataclass for additive per-TC accumulators"
    - "Reusing _iterate_clock_rows single-pass (no new repo query)"
    - "FRACTION vs PERCENT unit-conversion at the tint helper boundary"
key-files:
  modified:
    - app/schemas/endgames.py
    - app/services/endgame_service.py
    - frontend/src/types/endgames.ts
    - frontend/src/components/charts/EndgameTimePressureCard.tsx
    - tests/services/test_time_pressure_service.py
    - frontend/src/components/charts/__tests__/EndgameTimePressureCard.test.tsx
    - frontend/src/components/charts/__tests__/EndgameTimePressureSection.test.tsx
    - CHANGELOG.md
decisions:
  - "Aggregator shape: single _ClockAggregate dataclass with 9 summable fields per TC bucket — preferred over a dict-of-dicts because the field set is fixed, all fields share the same lifecycle, and the dataclass reads cleaner at the accumulation site."
  - "Format helpers (formatPctSecs, formatNetTimeoutRate, tintForNetTimeoutRate) inlined into EndgameTimePressureCard.tsx — single consumer per the deleted EndgameClockPressureSection precedent. Do NOT extract until a second consumer arrives."
  - "Pydantic defaults (5 averages = None, net_timeout_rate = 0.0) are mandatory (B-2 lock) — protected the legacy keyword-style construction in the test class TestPydanticDefaults."
  - "Net flag rate unit lock (B-1): rate is a FRACTION (0.005 = 0.5%); NEUTRAL_TIMEOUT_THRESHOLD is in PERCENT (5.0). Tint helper multiplies by 100 before comparison, with the unit relationship asserted via test cases at ±6% (tinted) and ±3% (untinted)."
metrics:
  duration_minutes: 12
  completed_date: 2026-05-17
---

# Phase 88 Plan 14: Card Top-Zone Stats Restored (CONTEXT §2 A-3) Summary

Restored five clock averages and the net flag rate per Time Pressure card as a top zone above the quintile bullets, fulfilling the user-approved scope amendment in §2 of `88-CONTEXT.md`. These stats were deleted in Phase 88-07 with the legacy `EndgameClockPressureSection.tsx`; they now live on each `TimePressureTcCard` and are wired from the same `query_clock_stats_rows` row stream the per-quintile bullets already consume.

## What Shipped

**Backend (`app/schemas/endgames.py`):** `TimePressureTcCard` gains six fields — `user_avg_pct`, `user_avg_seconds`, `opp_avg_pct`, `opp_avg_seconds`, `avg_clock_diff_seconds` (all `float | None = None`), plus `net_timeout_rate: float = 0.0`. The defaults are not cosmetic — they keep existing call sites that build `TimePressureTcCard(...)` keyword-style without these new args compiling untouched (B-2 lock), and the `TestPydanticDefaults` test pins this invariant.

**Backend (`app/services/endgame_service.py`):** A new module-scope `_ClockAggregate` slot-dataclass (9 summable fields) is accumulated per TC bucket inside `_iterate_clock_rows`. The function now returns a 5-tuple; `_compute_time_pressure_cards` destructures it and derives the six card fields. No new repo query — `query_clock_stats_rows` already emits `termination`, `result`, and `user_color` alongside the clock arrays, so the additive work is O(1) per row inside the existing O(N) pass.

**Frontend (`frontend/src/types/endgames.ts`):** TS type `TimePressureTcCard` mirrors the backend additions (5 fields `number | null` + 1 field `number`). JSDoc references the §2 A-3 amendment.

**Frontend (`frontend/src/components/charts/EndgameTimePressureCard.tsx`):** The JSX body now renders a top zone (`Clock Gap` bullet + a 3-stat row "My avg time / Opp avg time / Net flag rate") above a thin `border-t border-border/40` separator and the quintile bullets. Three inline format helpers (`formatPctSecs`, `formatNetTimeoutRate`, `tintForNetTimeoutRate`) handle null em-dashes, signed-percent formatting, and the zone tint. The `tintForNetTimeoutRate` helper multiplies `rate * 100` before comparing to `NEUTRAL_TIMEOUT_THRESHOLD` because the backend convention is FRACTION (`0.005`) and the threshold constant is in PERCENT (`5.0`) — this unit conversion is the B-1 lock and is tested explicitly at ±6% (tinted) and ±3% (untinted).

**Tests:** `TestTcCardTopZoneStats` adds 7 backend tests (5 from the plan plus 2 supplementary: termination=None doesn't trigger timeout counters, Pydantic defaults work). `EndgameTimePressureCard.test.tsx` adds 4 tests under "Plan 88-14 A-3: top-zone 3-stat row" (3-stat render, em-dash on null, tint above/below threshold, untinted within threshold). Section test fixtures (`buildCard` and `makeCard`) updated to seed the new fields.

**CHANGELOG.md:** One bullet under `[Unreleased] → Changed` reflects the honest "restored" framing — these stats existed pre-88-07.

## Aggregator Design Choice

Picked **single `_ClockAggregate` dataclass over a dict-of-dicts.** Reasoning:

- 9 fields are fixed and share a lifecycle (one writer in `_iterate_clock_rows`, one reader in `_compute_time_pressure_cards`). A dataclass is the cohesive shape; a dict-of-dicts would just be a typed dict with worse field-access ergonomics.
- `slots=True` keeps the memory footprint tight — 4 TC buckets max means we allocate 4 `_ClockAggregate` instances per request.
- Accumulation reads cleanly: `agg.user_clock_sum_seconds += user_clock` vs `agg[tc]['user_clock_sum_seconds'] += user_clock`.
- The dataclass file location (module-scope near `_TIME_CONTROL_ORDER`) mirrors the existing pattern for module-level constants and helpers — no surprise.

## Format Helper Inlining

`formatPctSecs`, `formatNetTimeoutRate`, and `tintForNetTimeoutRate` live inside `EndgameTimePressureCard.tsx` (private to the file, not exported). Per the CLAUDE.md "no premature extraction" guidance and the precedent in the deleted `EndgameClockPressureSection.tsx`, these single-consumer helpers stay co-located with their consumer. If Phase 88-15's restored line chart ends up needing the same formatters, they can be promoted to a shared module then; doing it now would be over-engineering with one user.

## Deviations from Plan

None. Plan executed as written. The plan called for "5 new backend tests" — I added 7 (the 5 specified plus `test_termination_none_not_counted_as_timeout` and `test_pydantic_defaults_allow_keyword_construction_without_new_fields`) because both edge cases were explicitly called out in the `<behavior>` section as required invariants. The plan called for "3 new frontend tests" — I added 4 (the 3 specified plus an untinted-within-threshold case) because the B-1 unit-conversion lock named ±3% as a required assertion.

The `_make_row` test helper grew an `_UNSET` sentinel pattern (instead of `None`) because tests legitimately need to pass `None` for `user_clock` / `opp_clock` to exercise the clock-ineligible accumulation branch. The default-fallback semantics were preserved for existing callers.

## What's Next (Phase 88 §2 Status)

| Ask | Plan | Status |
|---|---|---|
| A-1 | 88-13 | Done (separate per-TC containers shipped) |
| A-2 | 88-15 | Pending (line chart restoration — backend timeline payload + new chart component) |
| A-3 | **88-14** | **Done (this plan)** |
| A-4 | 88-13 | Done |
| A-5 | 88-13 | Done |

Plan 88-15 remains the only outstanding §2 ask. After it lands, re-verification picks up per the routing notes in CONTEXT §2.

## Self-Check: PASSED

**Files claimed:**

- `app/schemas/endgames.py` — FOUND, 6 new fields on `TimePressureTcCard` (`grep -c 'user_avg_pct: float | None' app/schemas/endgames.py` = 1; `grep -c 'net_timeout_rate: float' app/schemas/endgames.py` = 2).
- `app/services/endgame_service.py` — FOUND, `_ClockAggregate` defined and used (`grep -c '_ClockAggregate' app/services/endgame_service.py` = 6).
- `frontend/src/types/endgames.ts` — FOUND, 6 new fields (`grep -c user_avg_pct frontend/src/types/endgames.ts` = 1).
- `frontend/src/components/charts/EndgameTimePressureCard.tsx` — FOUND, `ThreeStatRow` defined and used (`grep -c ThreeStatRow` = 3), `NEUTRAL_TIMEOUT_THRESHOLD` imported + tint helper (`grep -c NEUTRAL_TIMEOUT_THRESHOLD` = 4), all 3 testids present.
- `tests/services/test_time_pressure_service.py` — FOUND, `TestTcCardTopZoneStats` class added (7 tests).
- `frontend/src/components/charts/__tests__/EndgameTimePressureCard.test.tsx` — FOUND, 4 new tests under "Plan 88-14 A-3" describe block.
- `frontend/src/components/charts/__tests__/EndgameTimePressureSection.test.tsx` — FOUND, `buildCard` fixture updated.
- `CHANGELOG.md` — FOUND, bullet under `[Unreleased] → Changed`.

**Commits present in git log:**

- `276faef2` test(88-14): add failing tests for TimePressureTcCard top-zone stats (RED) — FOUND.
- `a006b1c1` feat(88-14): restore top-zone summary stats on TimePressureTcCard (GREEN) — FOUND.
- `d581a27c` test(88-14): add failing tests for card top-zone 3-stat row (RED) — FOUND.
- `9557df5c` feat(88-14): render top-zone 3-stat row above quintile bullets (GREEN) — FOUND.

**Verification commands (already run during execution):**

- `uv run pytest tests/services/test_time_pressure_service.py tests/test_endgame_service.py tests/test_endgame_repository.py -q` → 341 passed.
- `uv run ruff check .` → All checks passed!
- `uv run ty check app/ tests/` → All checks passed!
- `uv run python scripts/gen_endgame_zones_ts.py --check` → up to date.
- `cd frontend && npm test -- --run EndgameTimePressureCard.test.tsx EndgameTimePressureSection.test.tsx` → 35 passed.
- `cd frontend && npx tsc --noEmit -p tsconfig.app.json` → exit 0.
- `cd frontend && npm run lint` → exit 0.
- `cd frontend && npm run knip` → exit 0.
- `cd frontend && npm run build` → exit 0.

## TDD Gate Compliance

Both tasks followed RED → GREEN. Git log shows:

- `test(88-14): … (RED)` at 276faef2, then `feat(88-14): … (GREEN)` at a006b1c1 (Task 1, backend).
- `test(88-14): … (RED)` at d581a27c, then `feat(88-14): … (GREEN)` at 9557df5c (Task 2, frontend).

No refactor commit was needed — the inline format helpers and `_ClockAggregate` dataclass were the GREEN-phase shape and required no clean-up pass.
