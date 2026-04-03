---
phase: quick-260403-ld8
plan: 01
subsystem: frontend
tags: [testing, zobrist, pgn, date-formatting, pure-functions]
dependency_graph:
  requires: []
  provides: [frontend-unit-test-coverage]
  affects: [ci-test-suite]
tech_stack:
  added: []
  patterns: [vitest, describe/it blocks, bigint assertions]
key_files:
  created:
    - frontend/src/types/api.test.ts
    - frontend/src/lib/pgn.test.ts
    - frontend/src/lib/utils.test.ts
    - frontend/src/lib/zobrist.test.ts
  modified: []
decisions:
  - "540-day boundary test uses exact date math (2023-01-01 to 2024-06-23 = 540 days) to avoid off-by-one with 18*30 constant"
metrics:
  duration: "2 minutes"
  completed: "2026-04-03"
  tasks_completed: 2
  files_created: 4
---

# Quick Task 260403-ld8: Frontend Component Test Coverage

**One-liner:** Unit tests for resolveMatchSide, pgnToSanArray, date tick formatters, and Zobrist hash computation verified against backend test vectors.

## Tasks Completed

| # | Name | Commit | Files |
|---|------|--------|-------|
| 1 | resolveMatchSide all 6 combinations + pgnToSanArray edge cases | 430379b | api.test.ts, pgn.test.ts |
| 2 | Date formatting utilities + Zobrist hash test vectors | e757227 | utils.test.ts, zobrist.test.ts |

## Test Coverage Added

**frontend/src/types/api.test.ts** — `resolveMatchSide` (6 tests)
- All 6 combinations of MatchSide (`mine`/`opponent`/`both`) x Color (`white`/`black`)
- Confirms mine→own color, opponent→opposite color, both→full

**frontend/src/lib/pgn.test.ts** — `pgnToSanArray` (8 tests)
- Standard 3-ply and 5-ply PGN parsing
- Empty string, single move
- Multi-digit move numbers (10. Qd2...)
- Castling: O-O and O-O-O preserved
- Extra whitespace, leading/trailing whitespace

**frontend/src/lib/utils.test.ts** — `createDateTickFormatter` + `formatDateWithYear` (11 tests)
- Long-range (> 540 days): format `"Jan '24"` with abbreviated year
- Short-range (<= 540 days): format `"Jun 15"` with month+day only
- Boundary: exactly 540-day span uses short format (not strictly greater than)
- Single-element array and empty array do not throw
- `formatDateWithYear`: Jan 1, Dec 31, and mid-year dates

**frontend/src/lib/zobrist.test.ts** — `computeHashes` + `hashToString` (16 tests)
- 3 backend-verified position test vectors:
  - Starting position: whiteHash `5858837776588196015n`, blackHash `-3976252316203442281n`, fullHash `5060803636482931868n`
  - After 1.e4: whiteHash `-6532466553307562974n`, blackHash unchanged, fullHash `-9062197578030825066n`
  - After 1.e4 e5: whiteHash unchanged from e4, blackHash `1839718147647814041n`, fullHash `595762792459712928n`
- Invariant tests: color hashes are independent (moving white does not change blackHash)
- `hashToString`: positive, negative, zero, large positive, large negative bigints

## Verification

```
Test Files  5 passed (5)
Tests       73 passed (73)
```

No regressions. All new tests pass.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed off-by-one in boundary test for createDateTickFormatter**
- **Found during:** Task 2 RED run
- **Issue:** Test used "2023-01-01" to "2024-07-01" (547 days) for the "exactly 18 months" boundary case, but the threshold is `18 * 30 = 540` days. 547 > 540, so it triggered the long-range format instead of short.
- **Fix:** Changed the boundary test to use dates 540 days apart (2023-01-01 to 2024-06-23), with a comment explaining the 18*30 constant math.
- **Files modified:** `frontend/src/lib/utils.test.ts`
- **Commit:** e757227

## Known Stubs

None.

## Self-Check: PASSED

Files exist:
- frontend/src/types/api.test.ts: FOUND
- frontend/src/lib/pgn.test.ts: FOUND
- frontend/src/lib/utils.test.ts: FOUND
- frontend/src/lib/zobrist.test.ts: FOUND

Commits:
- 430379b: FOUND (api.test.ts, pgn.test.ts)
- e757227: FOUND (utils.test.ts, zobrist.test.ts)
