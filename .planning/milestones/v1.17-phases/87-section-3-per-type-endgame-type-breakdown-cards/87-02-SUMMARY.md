---
phase: 87-section-3-per-type-endgame-type-breakdown-cards
plan: 02
subsystem: frontend
tags: [endgames, react, vitest, sig-gating, info-popover, mini-bullet, score-confidence]

requires:
  - phase: 87-01
    provides: 10 additive ConversionRecoveryStats wire fields (opp_*_pct, opp_*_games, conv_diff_*, recov_diff_*) on the 0-1 scale
  - phase: 86-section-2-endgame-metrics-4-card-layout
    provides: EndgameMetricCard pattern (sig-gating triple, MetricStatPopover content, opacity-50 / UNRELIABLE_OPACITY / muted-opp conventions); shared lib/endgameMetrics.ts module
  - phase: 84-data-plumbing-per-type-cohort-p50-and-mirror-rate-audit
    provides: PER_CLASS_GAUGE_ZONES codegen registry for per-type p25/p75 gauge bands
provides:
  - Three new exports in lib/endgameMetrics.ts: ENDGAME_TYPE_DESCRIPTIONS (5 entries, pawnless pruned), SHOW_WDL_BAR_IN_TYPE_CARDS (boolean = true), ENDGAME_CLASS_TO_SLUG (6 entries with pawnless retained)
  - EndgameTypeCard component fully wired to consume the Plan 01 wire shape; renders title + 2 gauges + WDL bar + 2 peer-bullet rows + Games deep-link
  - Vitest coverage (9 tests) for layout, sparse states, sig-gating, and the WDL flag fallback
affects:
  - 87-03 (EndgameTypeBreakdownSection orchestrator + Endgames.tsx mount swap + EndgameWDLChart / EndgameConvRecovChart deletion)

tech-stack:
  added: []
  patterns:
    - "Per-card title InfoPopover content sourced from a shared map (ENDGAME_TYPE_DESCRIPTIONS) keyed by the typed Exclude<EndgameClass, 'pawnless'> union — the TypeScript narrowing is what makes pruning safe and explicit"
    - "Hard-coded fallback flag (SHOW_WDL_BAR_IN_TYPE_CARDS) exported from a shared lib so the card can swap its WDL row for a standalone Games deep-link without prop drilling; the flag is mocked in vitest via vi.doMock + vi.importActual to verify the fallback path"
    - "Defensive PER_CLASS_GAUGE_ZONES[classKey] check that falls through to the empty-class shell rather than throwing — satisfies noUncheckedIndexedAccess without rendering a broken gauge for any unknown future class"

key-files:
  created:
    - frontend/src/components/charts/EndgameTypeCard.tsx (~470 LOC including the empty-class shell branch, the locked D-10 popover copy constants, and the full peer-bullet wiring for both metrics)
    - frontend/src/components/charts/__tests__/EndgameTypeCard.test.tsx (~330 LOC, 9 tests across 4 describe groups)
  modified:
    - frontend/src/lib/endgameMetrics.ts (+35 LOC for the three new exports + the EndgameClass type import widening)

key-decisions:
  - "Slug map lifted into lib/endgameMetrics.ts (NOT inlined): the CONTEXT 'Claude's Discretion' decision point allowed inlining inside EndgameTypeCard or lifting; lifted because Plan 03's orchestrator will also need the slug derivation (testid + deep-link), and the consumer count of two already justifies the shared export per CLAUDE.md no-magic-numbers"
  - "Empty-class shell uses an early return at the top of the component (not a conditional branch inside the body wrapper). The defensive PER_CLASS_GAUGE_ZONES[classKey] miss also lands on this branch, so 'unknown class' and 'total=0' share a single shell UX. The shell still renders the title row + InfoPopover so the card stays in the grid for layout stability"
  - "MetricStatPopover.value is set to the SIGNED user−opp diff (not the absolute pct) per Phase 86 EndgameMetricCard convention. Combined with baseline=0, neutralLower/Upper=±0.05, vocabulary='score', and relative=true, this gives the standard popover header 'X% above/below 0%' with the sig/CI block underneath"
  - "Empty-class gauge zone uses a single 0→1 colorizeGaugeZones band (not the per-class bands). The gauge needle is at 0 with opacity-50 wrapper, so the user reads 'no data', not 'red zone' — semantically distinct from a confirmed-low rate"
  - "Test file uses fireEvent.click instead of @testing-library/user-event because the project doesn't depend on user-event (only @testing-library/react). For a single click without keyboard sequencing or focus-management coverage, fireEvent is equivalent"
  - "WDL-flag gating test uses vi.doMock + vi.resetModules + a re-import inside a single it() so the rest of the test file sees the real flag value. Avoids cross-test contamination of a const-export mock"

patterns-established:
  - "Per-card title InfoPopover content lives in a shared lib map (ENDGAME_TYPE_DESCRIPTIONS) — future per-class card-style refactors should source titles the same way instead of inlining JSX strings"
  - "When a wire field carries both a 0-1 scale (Phase 86 convention) and a 0-100 scale (legacy Phase 84) for backward compat, the new card consumes only the new field — avoids accidental cross-scale arithmetic"

requirements-completed: [SEC3-02, SEC3-04]

duration: ~25min
completed: 2026-05-14
---

# Phase 87 Plan 02: EndgameTypeCard per-class card shell Summary

**Presentation-only per-class card that mirrors Phase 86 EndgameMetricCard with two metrics (Conversion + Recovery gauges + peer bullets) plus a Games deep-link, fully consumed via the Plan 01 wire shape; lib/endgameMetrics.ts extended with three new shared exports; 9 vitest cases cover layout, sparse states, sig-gating, and the SHOW_WDL_BAR_IN_TYPE_CARDS fallback.**

## Performance

- **Duration:** ~25 min
- **Started:** 2026-05-14
- **Completed:** 2026-05-14
- **Tasks:** 3
- **Files modified:** 3 (1 modified + 2 created)

## Accomplishments

- Extended lib/endgameMetrics.ts with three new exports per CONTEXT D-04 / D-11 / D-16: `ENDGAME_TYPE_DESCRIPTIONS` (5 entries, `pawnless` pruned via `Exclude<EndgameClass, 'pawnless'>`), `SHOW_WDL_BAR_IN_TYPE_CARDS: boolean = true`, `ENDGAME_CLASS_TO_SLUG` (all 6 entries kept for completeness).
- Built EndgameTypeCard.tsx as a presentation-only component consuming `EndgameCategoryStats` plus `sharePct` / `onCategorySelect` / `tileTestId`. Title row carries a per-card InfoPopover (D-11) and a conditional `n=total` chip (D-15). Body holds the gauge row (Conv + Recov side-by-side, sourced from `PER_CLASS_GAUGE_ZONES[class]`), the WDL row with embedded Games deep-link (or a standalone Games-link row under the gauges when `SHOW_WDL_BAR_IN_TYPE_CARDS = false`), the Conv peer-bullet row, and the Recov peer-bullet row. Empty class (`total = 0`) renders an early-return shell with opacity-50 gauges + "Not enough data yet".
- Sig-gating triple wired per metric (CONTEXT D-09): `deriveLevel(p, opp_games) → isConfident()` AND `diff outside ±NEUTRAL_ZONE` AND `hasOpponent` → inline `style.color` (ZONE_DANGER below NEUTRAL_ZONE_MIN, ZONE_SUCCESS at/above NEUTRAL_ZONE_MAX). Gauges always-colored; WDL bar untinted.
- D-10 locked popover copy mounted via two `MetricStatPopover` instances per card (Conv + Recov), each carrying its own `explanation` constant plus a shared `METHODOLOGY_BLOCK` ReactNode.
- All sub-element testids derived from `tileTestId` per CONTEXT D-16 (`-conv-gauge`, `-recov-gauge`, `-wdl`, `-conv-{you,opp,diff,info,muted}`, `-recov-{you,opp,diff,info,muted}`, `-games-link`, `-title-info`, `-n-chip`).
- 9 vitest cases across 4 describe groups: 3 layout (full render, link href, onClick), 3 sparse-state (Conv muted, empty class, n-chip + opacity), 2 sig-gating (paint vs no-paint), 1 WDL-flag fallback (`vi.doMock` flips the const). All green.

## Task Commits

Each task was committed atomically on the worktree branch:

1. **Task 1: Extend lib/endgameMetrics.ts with three new exports** — `dcfe81b6` (feat)
2. **Task 2: Build EndgameTypeCard.tsx** — `3a02ee79` (feat)
3. **Task 3: Vitest coverage for EndgameTypeCard** — `92dec6a1` (test)

## Files Created/Modified

- `frontend/src/lib/endgameMetrics.ts` — widened the `@/types/endgames` import to include `EndgameClass`; appended `ENDGAME_TYPE_DESCRIPTIONS` (5 entries, lifted verbatim from `EndgameWDLChart.tsx:30-37` with the `pawnless` entry pruned via `Exclude<EndgameClass, 'pawnless'>`), `SHOW_WDL_BAR_IN_TYPE_CARDS: boolean = true`, and `ENDGAME_CLASS_TO_SLUG` (6 entries, hyphenated slugs lifted verbatim from `EndgameWDLChart.tsx:21-28`). All three exports carry comment blocks citing the CONTEXT decision IDs.
- `frontend/src/components/charts/EndgameTypeCard.tsx` — new file. Header comment block citing Phase 87 + the Phase 86 parity rationale + the single-bullet doctrine. Module-level constants `CONV_EXPLANATION`, `RECOV_EXPLANATION`, `METHODOLOGY_BLOCK` carry the D-10 locked copy. Component is a single function (~370 logic LOC including the empty-class shell branch and both peer-bullet rows). Imports grouped per the EndgameMetricCard.tsx convention: types → router/icons → component primitives → generated → libs → types → local relative.
- `frontend/src/components/charts/__tests__/EndgameTypeCard.test.tsx` — new file. `buildConversion` / `buildCategory` factories for the wire shape, `renderCard` helper wrapping `<MemoryRouter>` + `<TooltipProvider>` (the Tooltip primitive requires a Provider in the test tree). 4 describe groups: Layout (3 tests), Sparse states (3), Sig-gating (2), WDL flag gating (1).

## Decisions Made

- **Slug map lifted into `lib/endgameMetrics.ts` (NOT inlined).** CONTEXT.md §D-16 noted "lifted into `lib/endgameMetrics.ts` (`ENDGAME_CLASS_TO_SLUG`) OR inlined in the card per Claude's Discretion". Lifted because: (a) Plan 03's orchestrator (`EndgameTypeBreakdownSection`) will need the slug for `data-testid="type-card-{slug}"` derivation; (b) the consumer count of two (card + orchestrator) already exceeds the CLAUDE.md "magic-number" threshold; (c) lifting matches the precedent set by Phase 86 lifting `MIRROR_BUCKET` / `BULLET_DOMAIN` / `NEUTRAL_ZONE_*` into the same module.
- **`noUncheckedIndexedAccess` defensive branch on `PER_CLASS_GAUGE_ZONES[classKey]`.** The Record access returns `T | undefined` under `noUncheckedIndexedAccess`. Chose to fold the "missing class" branch into the same empty-class shell used for `total = 0` rather than rendering a broken gauge or throwing. Rationale: pawnless is filtered upstream via `HIDDEN_ENDGAME_CLASSES` (Endgames.tsx:53) so the branch should never fire in production, but if a new `EndgameClass` is ever added without a corresponding `PER_CLASS_GAUGE_ZONES` entry, the card renders the safe empty shell instead of crashing. None of the test fixtures triggered this branch — they all use `rook`, which has a populated entry.
- **Test fixtures use `fireEvent.click` instead of `@testing-library/user-event`.** The project depends only on `@testing-library/react`; adding `user-event` would be a scope expansion not requested by the plan. For a single click with no keyboard sequencing or focus-management coverage, `fireEvent` is functionally equivalent. The plan's `<read_first>` included a reference to `userEvent`, but the runtime check showed it isn't installed (Rule 3 — blocking issue auto-fixed by switching to `fireEvent`).
- **`TooltipProvider` wrapping in test render helper.** The Tooltip primitive throws "Tooltip must be used within TooltipProvider" without an ancestor `<TooltipProvider>`. The Phase 86 `EndgameMetricCard.test.tsx` doesn't need it because that card doesn't use `<Tooltip>` (the Games-count is a static span). Phase 87 wraps the Games deep-link in `<Tooltip>` per CONTEXT D-08, so the test wrapper adds `<TooltipProvider>` between `<MemoryRouter>` and the card.
- **Empty-class gauges use a single 0→1 band, not the per-class bands.** Rationale: when `total = 0` the gauge needle is at 0 with an `opacity-50` wrapper, so the user reads "no data" rather than "deep red zone". Painting the danger zone over an actual zero value would be misleading. The empty-class branch still renders both `-conv-gauge` and `-recov-gauge` wrappers so the testid scheme stays stable across data states (the gauge primitive renders even at value=0).
- **WDL-flag gating test uses `vi.doMock` + `vi.resetModules` + dynamic re-import.** A static `vi.mock` at module-scope would also affect every other test in the file because `SHOW_WDL_BAR_IN_TYPE_CARDS` is captured in the import graph at module-evaluation time. Using `vi.doMock` inside a single `it()` then dynamic-importing the card preserves the real flag in the other 8 tests. After the test, `vi.doUnmock` + `vi.resetModules` restore the original module graph.

## Lifted `ENDGAME_TYPE_DESCRIPTIONS` strings (for Plan 03 HUMAN-UAT cross-reference)

The 5 surviving descriptions (lifted verbatim from `EndgameWDLChart.tsx:30-37`, with `pawnless` pruned):

- **rook:** `Endgames with rooks as the only non-king, non-pawn pieces. The most common Endgame Type besides Mixed.`
- **minor_piece:** `Endgames with bishops and/or knights as the only non-king, non-pawn pieces.`
- **pawn:** `King and pawn endgames only. No other pieces remain on the board.`
- **queen:** `Endgames where queens are the only non-king, non-pawn pieces.`
- **mixed:** `Endgames with pieces from two or more piece types: rooks, minor pieces (bishops/knights), and queens (e.g. queen + rook, rook + knight).`

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 — Blocking dependency] Switched from `@testing-library/user-event` to `fireEvent`.**

- **Found during:** Task 3 (first vitest run)
- **Issue:** The plan's `<read_first>` referenced `userEvent from '@testing-library/user-event'`, but `package.json` doesn't include the package. Vitest reported `Failed to resolve import "@testing-library/user-event"`.
- **Fix:** Swapped `userEvent.click(...)` for `fireEvent.click(...)` from `@testing-library/react`. The click semantics are equivalent for this test (single click, no focus / keyboard sequencing), and avoiding a new devDependency keeps the plan in scope.
- **Files modified:** `frontend/src/components/charts/__tests__/EndgameTypeCard.test.tsx`
- **Verification:** All 9 tests pass; `npm run lint` clean.
- **Committed in:** `92dec6a1` (Task 3 commit, alongside the rest of the test file)

**2. [Rule 3 — Blocking missing provider] Wrapped test renders in `<TooltipProvider>`.**

- **Found during:** Task 3 (second vitest run after fix 1)
- **Issue:** The card uses `<Tooltip>` around the Games deep-link. Without an ancestor `<TooltipProvider>`, Radix throws `Tooltip must be used within TooltipProvider` at render time. The Phase 86 `EndgameMetricCard.test.tsx` doesn't need it because that card doesn't use `<Tooltip>`.
- **Fix:** Imported `TooltipProvider` from `@/components/ui/tooltip` and wrapped the card render tree (`<MemoryRouter>` → `<TooltipProvider>` → `<EndgameTypeCard>`).
- **Files modified:** same as fix 1
- **Verification:** All 9 tests pass.
- **Committed in:** same commit as fix 1

---

**Total deviations:** 2 auto-fixed (both Rule 3 — blocking test-infra issues; neither expands plan scope).
**Impact on plan:** Both fixes are local to the test file and do not affect the card's runtime behavior, the acceptance criteria, or the wire-shape contract.

## Issues Encountered

- Frontend `node_modules` was not present in the worktree on first `tsc` attempt (same issue noted in Plan 01's SUMMARY). Ran `npm install` (~1 min); subsequent commands clean.
- No deviations from Phase 86 `EndgameMetricCard` patterns turned out to be necessary beyond the additive structural changes already specified in the plan (two gauges per card instead of one, two peer-bullets, Games as a `<Link>` instead of a span, per-card title InfoPopover). The side-by-side gauge row uses `grid grid-cols-2 gap-2` identical to the legacy `EndgameConvRecovChart.tsx:106` and reads well at every breakpoint in the test fixture (no tablet-specific grid override needed; Plan 03's real-device HUMAN-UAT will confirm).

## Self-Check: PASSED

All three task commits exist on the worktree branch:

- `dcfe81b6` (Task 1, lib exports) — FOUND
- `3a02ee79` (Task 2, EndgameTypeCard) — FOUND
- `92dec6a1` (Task 3, vitest) — FOUND

All modified files verified present on disk:

- `frontend/src/lib/endgameMetrics.ts` — FOUND
- `frontend/src/components/charts/EndgameTypeCard.tsx` — FOUND
- `frontend/src/components/charts/__tests__/EndgameTypeCard.test.tsx` — FOUND

Verification commands all green:

- `cd frontend && npx tsc --noEmit` — exits 0
- `cd frontend && npm run lint` — exits 0
- `cd frontend && npx vitest run src/components/charts/__tests__/EndgameTypeCard.test.tsx` — 9 passed (1 file)
- `cd frontend && npm run knip` — exits 0 (no dead exports introduced; the three new lib exports are imported by the new card)

Acceptance greps:
- 3 new exports in `lib/endgameMetrics.ts` — confirmed
- `pawnless` appears once in the lib (only in `ENDGAME_CLASS_TO_SLUG`, not in `ENDGAME_TYPE_DESCRIPTIONS`) — confirmed
- `'minor-piece'` appears once in the lib — confirmed
- 0 occurrences of `text-xs` in `EndgameTypeCard.tsx` — confirmed (CLAUDE.md no-text-xs rule)
- 19 occurrences of `data-testid={\`${tileTestId}-` in the card — confirmed (≥10 per D-16)
- 8 occurrences of `deriveLevel|isConfident` — confirmed (≥4 per sig-gating triple applied for Conv + Recov)

## Next Phase Readiness

- **Plan 03 (EndgameTypeBreakdownSection orchestrator + mount swap + legacy deletion):** the card is ready to mount. The orchestrator imports `EndgameTypeCard`, `ENDGAME_CLASS_TO_SLUG` from `lib/endgameMetrics`, and filters `categories` via `HIDDEN_ENDGAME_CLASSES` from `Endgames.tsx:53`. Per-card `sharePct = cat.total / totalGames * 100`. `tileTestId = \`type-card-${ENDGAME_CLASS_TO_SLUG[cat.endgame_class]}\``. The h2 page-level InfoPopover (D-12) absorbs the legacy `EndgameWDLChart` + `EndgameConvRecovChart` intro copy.
- **HUMAN-UAT (Plan 03):** the mobile real-device density check decides whether `SHOW_WDL_BAR_IN_TYPE_CARDS` flips to `false` before merge. The fallback path is verified by vitest, so flipping the flag is a one-line constant change with no further code edits needed.
- **POLISH-04 (Phase 88):** 375px parity audit explicitly deferred per CONTEXT §D-04.

---
*Phase: 87-section-3-per-type-endgame-type-breakdown-cards*
*Plan: 02*
*Completed: 2026-05-14*
