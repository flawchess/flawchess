---
phase: 77-troll-opening-watermark-on-insights-findings
plan: 03
subsystem: frontend
tags: [insights, openings, ui, watermark, react, vitest]
requires:
  - "frontend/src/lib/trollOpenings.ts (Plan 01)"
  - "frontend/src/data/trollOpenings.ts (Plan 02)"
  - "frontend/src/assets/troll-face.svg (Plan 01)"
  - "TROLL_WATERMARK_OPACITY in frontend/src/lib/theme.ts (Plan 01)"
provides:
  - "Conditional <img> watermark on OpeningFindingCard, gated on isTrollPosition(entry_fen, color)"
  - "9 new test cases under describe('Phase 77 — Troll-opening watermark') asserting D-02/D-03/D-04/D-05"
affects:
  - "frontend/src/components/insights/OpeningFindingCard.tsx"
  - "frontend/src/components/insights/OpeningFindingCard.test.tsx"
tech_stack:
  added: []
  patterns:
    - "Decorative <img> idiom (alt='' + aria-hidden='true')"
    - "Single absolute-positioned sibling covering both mobile and desktop branches"
    - "pointer-events-none to keep underlying interactive elements clickable"
key_files:
  created: []
  modified:
    - frontend/src/components/insights/OpeningFindingCard.tsx
    - frontend/src/components/insights/OpeningFindingCard.test.tsx
decisions:
  - "Watermark is severity-independent (D-05): fires for every classification x severity combo"
  - "Sized h-16 w-16 (64px) on mobile, sm:h-20 sm:w-20 (80px) on desktop — both inside the 60-80px CONTEXT.md guideline"
  - "Mock @/data/trollOpenings rather than @/lib/trollOpenings in tests, so isTrollPosition runs its real derivation logic and only the curated key set is stubbed"
metrics:
  duration_minutes: 3
  completed_date: 2026-04-28
  tasks_completed: 2
  files_changed: 2
  tests_added: 9
  tests_total: 28
---

# Phase 77 Plan 03: Render watermark on OpeningFindingCard Summary

One-liner: Conditional troll-face watermark wired onto `OpeningFindingCard` (Insights findings), gated by `isTrollPosition(finding.entry_fen, finding.color)`, with full mobile/desktop parity, click pass-through, and 9 new tests.

## Tasks Executed

| Task | Name                                                    | Commit  | Files                                                              |
| ---- | ------------------------------------------------------- | ------- | ------------------------------------------------------------------ |
| 1    | Add watermark to OpeningFindingCard                     | 1f45662 | frontend/src/components/insights/OpeningFindingCard.tsx           |
| 2    | Extend OpeningFindingCard tests with Phase 77 assertions | edeb5fa | frontend/src/components/insights/OpeningFindingCard.test.tsx     |

## What Shipped

### Component change (`OpeningFindingCard.tsx`)

- Imports added:
  - `TROLL_WATERMARK_OPACITY` (appended to existing `@/lib/theme` import)
  - `isTrollPosition` from `@/lib/trollOpenings`
  - `trollFaceUrl` from `@/assets/troll-face.svg`
- New derivation right after `isUnreliable`:
  ```tsx
  const showTroll = isTrollPosition(finding.entry_fen, finding.color);
  ```
- Outer card div className change (only `relative` added, all other tokens preserved):
  - **Before:** `block border-l-4 charcoal-texture border border-border/20 rounded px-4 py-3`
  - **After:** `block relative border-l-4 charcoal-texture border border-border/20 rounded px-4 py-3`
- Watermark `<img>` inserted as the LAST child of the outer card div (sibling to both the mobile-branch `flex flex-col gap-2 sm:hidden` div and the desktop-branch `hidden sm:flex gap-3 items-center` div):
  ```tsx
  {showTroll && (
    <img
      src={trollFaceUrl}
      alt=""
      aria-hidden="true"
      data-testid={`opening-finding-card-${idx}-troll-watermark`}
      className="absolute bottom-2 right-2 h-16 w-16 sm:h-20 sm:w-20 pointer-events-none select-none"
      style={{ opacity: TROLL_WATERMARK_OPACITY }}
    />
  )}
  ```

### Watermark className (verbatim, for reviewer/verifier)

```
absolute bottom-2 right-2 h-16 w-16 sm:h-20 sm:w-20 pointer-events-none select-none
```

### Outer card div className (post-change)

```
block relative border-l-4 charcoal-texture border border-border/20 rounded px-4 py-3
```

The prior className tokens are preserved verbatim — `relative` is the only addition, inserted directly after `block`.

### Test changes (`OpeningFindingCard.test.tsx`)

- Top-of-file `vi.mock('@/data/trollOpenings', ...)` block stubs the curated set with a single sentinel white-side key (`8/8/8/8/4P3/8/PPPP1PPP/RNBQKBNR`) and an empty black-side set. Tests are independent of the live curated data shipped in Plan 02.
- New module-scope FEN constants:
  - `TROLL_FIXTURE_FEN` — derives, for `color: 'white'`, to the seeded sentinel key, triggering the watermark.
  - `NON_TROLL_FIXTURE_FEN` — derives to a non-matching key.
- `renderCard` helper extended with optional `onFindingClick`/`onOpenGames` props (backwards-compatible: previous call sites still work).
- New `describe('Phase 77 — Troll-opening watermark', ...)` block with 9 tests:
  1. Renders watermark img when entry_fen + color match the troll set
  2. Absent when position is NOT in the troll set
  3. Absent when color routes to the empty `BLACK_TROLL_KEYS` set
  4. Watermark has `pointer-events-none` class (D-04)
  5. Watermark is decorative: `alt=""` + `aria-hidden="true"`
  6. Renders for `weakness` / `major` (D-05 always-on)
  7. Renders for `strength` / `minor` (D-05 always-on)
  8. Renders exactly once across both mobile and desktop branches (D-03)
  9. Click on Moves button still fires `onFindingClick` (D-04 regression)

### Test count delta

- Before Plan 03: 19 tests in `OpeningFindingCard.test.tsx`
- After Plan 03: 28 tests in `OpeningFindingCard.test.tsx`
- Delta: +9 tests (the original plan referenced 8 tests in the bullet list but the action block specified 9 cases — including the third absent-watermark case that exercises the empty `BLACK_TROLL_KEYS` set; all 9 were implemented)

## Sizing Rationale (no deviation)

The plan's recommended sizing was applied verbatim:
- Mobile: `h-16 w-16` = 64 px
- Desktop (`sm` breakpoint): `sm:h-20 sm:w-20` = 80 px
- Both fall inside the 60-80 px guideline from `77-CONTEXT.md` "Claude's Discretion".

No deviation from recommended sizing.

## Verification

- `cd frontend && npx tsc --noEmit -p tsconfig.app.json` → exit 0 (no errors)
- `cd frontend && npm run lint` → exit 0 (ESLint clean)
- `cd frontend && npm test -- --run src/components/insights/OpeningFindingCard.test.tsx` → 28/28 passing
- All grep tokens from the acceptance criteria present in the modified files (`TROLL_WATERMARK_OPACITY`, `isTrollPosition`, `trollFaceUrl`, `troll-watermark`, `block relative border-l-4`).
- Manual visual verification at desktop and 375 px mobile is deferred to phase-end per `77-VALIDATION.md` (Manual-Only Verifications) — this plan does not gate on it.

## Requirements Addressed

- **D-02** — Visual placement (absolute bottom-right, 30% opacity from theme)
- **D-03** — Mobile parity (single sibling element covers both layouts; test asserts exactly-one rendering)
- **D-04** — No click blocking (`pointer-events-none` class + click pass-through regression test)
- **D-05** — Always-on regardless of severity (no severity gating; tests for both weakness/major and strength/minor)
- **D-10** (Insights side) — Matching contract uses `entry_fen` + `color`

## Deviations from Plan

None — plan executed exactly as written. The 9-test count matches the explicit test cases in the `<action>` block; the introductory bullet list said 8 ("Test A" through "Test H") but the spelled-out action block adds a third absent-watermark case (empty `BLACK_TROLL_KEYS` routing) for 9 total. All 9 were implemented.

## Self-Check: PASSED

Verifying claims:

- `frontend/src/components/insights/OpeningFindingCard.tsx` — modified (commit 1f45662)
- `frontend/src/components/insights/OpeningFindingCard.test.tsx` — modified (commit edeb5fa)
- Commit `1f45662` exists in `git log`
- Commit `edeb5fa` exists in `git log`
- Test file contains `describe('Phase 77 — Troll-opening watermark'` (verified in test run output: 9 new test cases)
- `vi.mock('@/data/trollOpenings'` present at top of test file
- 28 total tests passing under `vitest run`
- Card outer div className grep `'block relative border-l-4'` matches
- Watermark `<img>` contains `alt=""`, `aria-hidden="true"`, `pointer-events-none`, and `style={{ opacity: TROLL_WATERMARK_OPACITY }}`

All Plan 03 acceptance criteria satisfied.
