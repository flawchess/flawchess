---
phase: 175-board-filter-gem-great-consumption
plan: 06
subsystem: ui
tags: [react, typescript, recharts, gem-great, eval-chart, badges]

# Dependency graph
requires:
  - phase: 175-board-filter-gem-great-consumption
    provides: "175-03: GREAT_ACCENT/GREAT_ACCENT_BG/MAIA_ACCENT/MAIA_ACCENT_BG theme colors, GemIcon/GreatMoveIcon"
  - phase: 175-board-filter-gem-great-consumption
    provides: "175-02/175-05: EvalPoint.best_move_tier/maia_prob on both the backend read path and the frontend TS type, already present on evalSeries for every analyzed game"
provides:
  - "EvalChart gem/great dot layer (violet/blue filled dots), sharing the existing highlightedPlies emphasis/dim prop with the flaw-dot layer; user-scoped via a new explicit userColor prop"
  - "bestMoveDotSpec (lib/bestMoveDot.ts) — pure, directly unit-tested color/tier/highlight binding + user-only filter, reused by the render prop"
  - "isUserPly (lib/plyOwnership.ts) — shared mover-parity helper (even=White, odd=Black) scoping every gem/great surface to the user's own plies"
  - "GemGreatBadge (components/library) — SeverityBadge-pattern pill (hover-highlight, click-to-cycle), shared by LibraryGameCard and AnalysisTagsPanel"
  - "LibraryGameCard Gem/Great badges — desktop + mobile, cycling the eval chart's commandedPly/commandSeq through the USER's gem/great plies"
  - "AnalysisTagsPanel Gem/Great badges — cycling the board via onCyclePly through the USER's gem/great plies, wired into the panel's existing highlight machinery"
  - "Analysis.tsx analyzed-board gem/great corner markers show BOTH players (Plan 05 study feature, kept per the user's decision) — distinct from the user-only badges/dots/cycling (see Fix section FINAL RESOLUTION)"
affects: []

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Pure spec function extracted to its own lib module (not the component file) so react-refresh's component-only-export rule is satisfied AND the color/tier/highlight binding is directly unit-testable without mounting recharts' custom dot render prop"
    - "A tier-scoped ref kind ({kind:'bestMove'; tier}) added to each card/panel's own local FlawRef union, following the codebase's established no-shared-extraction convention between LibraryGameCard and AnalysisTagsPanel"
    - "GemGreatBadge as a single tier-parameterized component (gem|great) shared across two call sites, mirroring 175-03's GemMoveBadge tier-prop precedent to avoid badge-family drift"

key-files:
  created:
    - frontend/src/lib/bestMoveDot.ts
    - frontend/src/lib/plyOwnership.ts
    - frontend/src/lib/__tests__/plyOwnership.test.ts
    - frontend/src/components/library/GemGreatBadge.tsx
    - frontend/src/components/library/__tests__/EvalChart.test.tsx
    - frontend/src/components/library/__tests__/GemGreatBadge.test.tsx
  modified:
    - frontend/src/components/library/EvalChart.tsx
    - frontend/src/components/results/LibraryGameCard.tsx
    - frontend/src/components/results/__tests__/LibraryGameCard.test.tsx
    - frontend/src/components/analysis/AnalysisTagsPanel.tsx
    - frontend/src/components/analysis/__tests__/AnalysisTagsPanel.test.tsx
    - frontend/src/pages/Analysis.tsx
    - frontend/src/pages/__tests__/Analysis.test.tsx

key-decisions:
  - "bestMoveDotSpec lives in lib/bestMoveDot.ts, not EvalChart.tsx — exporting a non-component function from a file that also exports the EvalChart component violates react-refresh/only-export-components; extracting it also makes the color/tier/highlight binding directly unit-testable, sidestepping recharts 3's jsdom pixel-position unreliability (same caveat EndgameClockDiffOverTimeChart's own tests already document)."
  - "GemGreatBadge is one tier-parameterized component (tier: 'gem'|'great'), shared by both LibraryGameCard and AnalysisTagsPanel — the codebase's D-05/175-03 precedent is to share small presentational badges (SeverityBadge already crosses this boundary) while keeping the card/panel-level *Plies/FlawRef logic duplicated per file."
  - "AnalysisTagsPanel's guard relaxed from 'no flaw markers -> render nothing' to 'no flaw markers AND no gem/great plies -> render nothing' — a flawless-but-brilliant game (zero flaws) can still have gem/great plies, and the plan's own 'only when such plies exist' requirement is unreachable for that game class without this fix."
  - "User-only scoping fix: best_move_tier is POSITION-scoped (both players), so a shared isUserPly (lib/plyOwnership.ts) mover-parity helper scopes all four surfaces (badges/cycling, eval-chart dots, analysis board markers) to the user's own plies. EvalChart gained an explicit userColor prop kept SEPARATE from flipped (display) — move ownership is a data concern."
  - "RESOLVED (user decision 2026-07-17): badges/eval-chart-dots/cycling are USER-ONLY; the analyzed board keeps showing BOTH players' gems/greats (Plan 05 study feature + opponent popover). The board-only user filter was added in bb66dbd5 then reverted in 19722b82; sites 1-3 stay user-only."

requirements-completed: []

coverage:
  - id: D1
    description: "Gem (violet, MAIA_ACCENT) and great (blue, GREAT_ACCENT) filled dots render on the eval chart, sourced directly from each EvalPoint's best_move_tier; a null-tier ply renders nothing"
    verification:
      - kind: unit
        ref: "frontend/src/components/library/__tests__/EvalChart.test.tsx::bestMoveDotSpec (color/tier binding) — 7 tests: gem->MAIA_ACCENT, great->GREAT_ACCENT, null-tier->null, null-es->null, highlight emphasis, dim, empty-set no-op"
        status: pass
      - kind: unit
        ref: "frontend/src/components/library/__tests__/EvalChart.test.tsx::EvalChart gem/great dot layer — mount smoke test — mounts without crashing with mixed gem/great/plain plies"
        status: pass
    human_judgment: false
  - id: D2
    description: "Gem/Great cycling badges on the Library game card (mobile + desktop) — render only when the game has >=1 ply of that tier, hover emphasizes the eval chart's dots, activation cycles commandedPly/commandSeq through that tier's plies with wrap"
    verification:
      - kind: unit
        ref: "frontend/src/components/results/__tests__/LibraryGameCard.test.tsx::LibraryGameCard Gem/Great badges (Phase 175 Plan 06) — 6 tests: absent when no plies, correct counts, Great omitted when only gem exists, cycling wraps, independent cycling between tiers"
        status: pass
    human_judgment: false
  - id: D3
    description: "Gem/Great cycling badges on the AnalysisTagsPanel — render only when the game has >=1 ply of that tier (including flawless games), activation cycles the board via onCyclePly through that tier's plies"
    verification:
      - kind: unit
        ref: "frontend/src/components/analysis/__tests__/AnalysisTagsPanel.test.tsx::AnalysisTagsPanel Gem/Great badges (Phase 175 Plan 06) — 5 tests: correct counts, absent when no plies, renders with zero flaw markers, onCyclePly sequence with wrap, independent tier cycling"
        status: pass
    human_judgment: false
  - id: D4
    description: "Full frontend verification gate: tsc -b, eslint, knip, and the full vitest suite all pass with the new code"
    verification:
      - kind: unit
        ref: "npx tsc -b (clean), npm run lint (0 errors), npm run knip (0 issues), npm test -- --run (171 files / 2306 tests, all passing)"
        status: pass
    human_judgment: false
  - id: D5
    description: "User-only scoping fix (RESOLVED per user decision): the gem/great count badges, cycling, and eval-chart dots include ONLY the user's own plies (best_move_tier is position-scoped and previously leaked the opponent's gems/greats); the analyzed board INTENTIONALLY keeps showing BOTH players' gems/greats as study context (Plan 05 feature). Shared isUserPly helper (mover parity) scopes sites 1-3."
    verification:
      - kind: unit
        ref: "frontend/src/lib/__tests__/plyOwnership.test.ts (parity rule: even=White, odd=Black, invalid color=false)"
        status: pass
      - kind: unit
        ref: "EvalChart.test.tsx::user-only scoping (dot renders on user ply, excluded on opponent ply, both colors); LibraryGameCard.test.tsx + AnalysisTagsPanel.test.tsx (count + cycling exclude opponent plies)"
        status: pass
      - kind: unit
        ref: "Analysis.test.tsx: opponent's stored gem DOES paint the analyzed board + move list with the 'Your opponent found a gem move!' popover (board = both players, restored per user decision)"
        status: pass
    human_judgment: false

# Metrics
duration: ~35min
completed: 2026-07-17
status: complete
---

# Phase 175 Plan 06: Gem/Great Eval-Chart Dots + Cycling Badges Summary

**Brings gem/great moves to full parity with flaws on the eval chart (violet/blue dots, sourced from EvalPoint.best_move_tier) and in move-cycling navigation (new GemGreatBadge, shared by the Library game card and the analysis panel).**

## Performance

- **Duration:** ~65 min (implementation + verification + user-only fix + board revert; commit span `084baf26` → `19722b82`)
- **Completed:** 2026-07-17 (last commit `bb66dbd5`)
- **Tasks:** 3 (+ 1 lint-driven follow-up fix + 1 user-verification bug fix + 1 board-marker revert per user decision)
- **Files modified:** 15 total (6 created, 9 modified — includes the user-only fix)

## Accomplishments

- **Gem/great dot layer on EvalChart.tsx** — a second invisible `<Line>` overlay, independent of the existing flaw-dot layer, drawing a filled violet (`MAIA_ACCENT`) or blue (`GREAT_ACCENT`) dot wherever `EvalPoint.best_move_tier` is non-null. No new prop was needed for the data (`evalSeries` already carries `best_move_tier` per Plan 02/05); the layer reuses the existing `highlightedPlies` prop so the Task 2/3 badges' hover/cycle interactions emphasize these dots exactly like the severity/tag badges already emphasize flaw dots (empty/null set = no-op, matching the flaw layer's own convention). A short "Gem"/"Great" tooltip row shows when the hovered ply has a tier and no flaw marker (the two are mutually exclusive per ply).
- **`bestMoveDotSpec` extracted to `lib/bestMoveDot.ts`** — a pure function (color/tier/highlight-radius/dim-opacity spec) that the render prop calls internally. Extracting it was required by `react-refresh/only-export-components` (EvalChart.tsx also exports the `EvalChart` component) and, as a bonus, makes the color/tier binding directly unit-testable without mounting recharts' custom `dot` prop — recharts 3 renders those behind portal/zIndex layers that make jsdom pixel-position assertions unreliable (the same caveat `EndgameClockDiffOverTimeChart.test.tsx` already documents for its own dot layer).
- **`GemGreatBadge` (new, `components/library/GemGreatBadge.tsx`)** — a tier-parameterized (`gem`/`great`) pill mirroring `SeverityBadge`'s exact interaction shape (hover-highlight, click-to-cycle, keyboard activation), colored via `MAIA_ACCENT`/`GREAT_ACCENT` + `MAIA_ACCENT_BG`/`GREAT_ACCENT_BG` with a leading `GemIcon`/`GreatMoveIcon`. One component, shared by both `LibraryGameCard` and `AnalysisTagsPanel` (matching the codebase's precedent of sharing small presentational badges — `SeverityBadge` already crosses that same card/panel boundary — while keeping each caller's own `*Plies`/`FlawRef` cycling logic duplicated per file, per this codebase's established D-05 convention).
- **`LibraryGameCard.tsx`** — derives `bestMovePlies` (ascending gem/great plies) from `game.eval_series`, extends its local `FlawRef` union with a `{kind:'bestMove'; tier}` variant, and renders the badges on both the mobile flaw row and the desktop severity-badge stack, only when the game has >=1 ply of that tier. `onHover` sets the shared `highlightedPlies` state; `onActivate` reuses the exact `handleActivate`/`commandSeq` cycling mechanism the severity/tag badges already use.
- **`AnalysisTagsPanel.tsx`** — same pattern; no new prop was needed since the panel already receives the full `GameFlawCard` (`game.eval_series` was already in scope). Extended the panel's local `FlawRef` union, wired the badges next to the severity row, and relaxed the panel's "no flaw markers → render nothing" guard so a flawless-but-brilliant game (zero flaw markers, but a gem/great move) still shows its badges — otherwise the "only when such plies exist" requirement would be unreachable for that game class. The panel mounts exactly once (per its existing docstring/architecture), so mobile+desktop parity is automatic.

## Task Commits

Each task was committed atomically:

1. **Task 1: Gem/great dots on the eval chart** — `084baf26` (feat)
2. **[Rule 1 fix] Extract bestMoveDotSpec into its own module** — `fe6222fb` (fix)
3. **Task 2: Gem/Great cycling badges — Library game card** — `eadb80f3` (feat)
4. **Task 3: Gem/Great cycling badges — Analysis page** — `a2116b9c` (feat)
5. **[User-verification bug fix] Scope gem/great to the user's own moves only** — `bb66dbd5` (fix) — see the Fix (user-only scoping) section below
6. **[User decision] Restore opponent gems on the analyzed board** — `19722b82` (fix) — targeted revert of site 4 only; sites 1-3 stay user-only

## Files Created/Modified

- `frontend/src/components/library/EvalChart.tsx` — gem/great `<Line>` dot layer, tooltip row, imports `bestMoveDotSpec`
- `frontend/src/lib/bestMoveDot.ts` — `bestMoveDotSpec` pure function + `GEM_GREAT_DOT_RADIUS` (new file)
- `frontend/src/components/library/__tests__/EvalChart.test.tsx` — `bestMoveDotSpec` unit tests + a mount smoke test (new file)
- `frontend/src/components/library/GemGreatBadge.tsx` — shared gem/great pill badge (new file)
- `frontend/src/components/library/__tests__/GemGreatBadge.test.tsx` — badge unit tests (new file)
- `frontend/src/components/results/LibraryGameCard.tsx` — `bestMovePlies`, `FlawRef.bestMove`, badge rendering (mobile + desktop)
- `frontend/src/components/results/__tests__/LibraryGameCard.test.tsx` — Gem/Great badge tests + a `commandedPly`/`commandSeq`-exposing `EvalChart` stub update
- `frontend/src/components/analysis/AnalysisTagsPanel.tsx` — `bestMovePlies`, `FlawRef.bestMove`, badge rendering, relaxed empty-markers guard
- `frontend/src/components/analysis/__tests__/AnalysisTagsPanel.test.tsx` — Gem/Great badge tests

## Decisions Made

- `bestMoveDotSpec` lives in `lib/bestMoveDot.ts`, not `EvalChart.tsx` — required by `react-refresh/only-export-components` (a component file can only export components under Fast Refresh); also makes the color/tier/highlight binding directly unit-testable without mounting recharts' custom `dot` render prop.
- `GemGreatBadge` is one tier-parameterized component shared by both call sites, not two near-identical badges or two separate copies — mirrors 175-03's `GemMoveBadge tier` prop precedent and matches `SeverityBadge`'s existing cross-file reuse.
- Relaxed `AnalysisTagsPanel`'s early-return guard from "no flaw markers → null" to "no flaw markers AND no gem/great plies → null", since a flawless game can still have gem/great plies and the spec explicitly requires the badges to render "only when such plies exist" — the prior guard made that unreachable for flawless games.
- Reused the existing `highlightedPlies`/`commandedPly`/`commandSeq` machinery end-to-end (EvalChart prop, LibraryGameCard's `handleActivate`, AnalysisTagsPanel's `onCyclePly`) rather than inventing a parallel gem/great-specific cycling mechanism — the plan explicitly asked to "copy the exact cycling logic the severity/tag badges use."

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] `react-refresh/only-export-components` lint error on the initial EvalChart.tsx implementation**
- **Found during:** Task 3 (running the full lint gate before the SUMMARY)
- **Issue:** Task 1's `bestMoveDotSpec` was initially exported directly from `EvalChart.tsx`, which also exports the `EvalChart` React component — ESLint's `react-refresh/only-export-components` rule forbids mixing component and non-component exports in one file (Fast Refresh requirement).
- **Fix:** Extracted `bestMoveDotSpec` (+ `GEM_GREAT_DOT_RADIUS` and its own highlight/dim constants, cross-referenced in a comment to `EvalChart.tsx`'s own `HIGHLIGHT_RADIUS_FACTOR`/`DIMMED_MARKER_OPACITY` to avoid drift) into a new `frontend/src/lib/bestMoveDot.ts` module, mirroring the established `gemGlyph.ts`/`greatGlyph.ts` "plain module, not the component file" pattern. `EvalChart.tsx` now imports it.
- **Files modified:** `frontend/src/components/library/EvalChart.tsx`, `frontend/src/components/library/__tests__/EvalChart.test.tsx`, `frontend/src/lib/bestMoveDot.ts` (new)
- **Verification:** `npm run lint` clean (0 errors); `npx tsc -b` clean; full test suite still 2296/2296 passing.
- **Committed in:** `fe6222fb` (separate fix commit, since it corrects Task 1's own code)

---

**Total deviations:** 1 auto-fixed (1 bug/lint fix)
**Impact on plan:** No scope creep — the fix is purely mechanical (module relocation) with zero behavior change, required to pass the plan's own mandated verification gate (`npm run lint`).

## Issues Encountered

None beyond the lint fix documented above.

## Known Stubs

None — every rendering surface (eval chart dots, both badge locations) is wired to real data (`EvalPoint.best_move_tier` from the already-shipped Plan 02/05 backend/frontend pipeline); no placeholder/mock data paths were introduced.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- Gem/great moves now have full UI parity with flaws: eval-chart dots (Task 1), Library-card cycling badges (Task 2), and analysis-panel cycling badges (Task 3) all consume the same `EvalPoint.best_move_tier` data the Phase 175 backend/frontend pipeline (Plans 01-05) already ships.
- No further plumbing is needed for gem/great consumption — `LibraryGameCard` and `AnalysisTagsPanel` both derive their badge state directly from props they already receive (`game.eval_series`), with no new API surface.
- `STATE.md`/`ROADMAP.md` intentionally left untouched per this plan's constraints — the orchestrator owns those updates.

## Fix (user-only scoping)

**Bug found during user verification:** gem/great was counted/shown for BOTH players, but it must be the USER's moves only.

**Systemic root cause.** `EvalPoint.best_move_tier` is **position-scoped**, not user-scoped — the backend stores a tier for BOTH players' best moves (a position either does or doesn't have a "best move"; that's independent of whose turn it is). The original Plan 06 design *intent* was user-only (evidenced by the now-corrected "there is no opponent gem concept" comment), but the user filter was never implemented, so every consumption surface silently included the opponent's gems/greats. My initial Task 1-3 implementation inherited this gap on the new surfaces, and it also pre-existed on Plan 05's board markers.

**Shared fix (Step 0).** Added `frontend/src/lib/plyOwnership.ts` exporting `isUserPly(ply, userColor)` — the single source of the mover-parity rule (even ply = White, odd = Black; a ply belongs to the user when the mover matches `user_color`; unknown/invalid color → false). Unit-tested in `frontend/src/lib/__tests__/plyOwnership.test.ts`. Every fix site uses this helper — the `ply % 2` expression is never duplicated.

**FINAL RESOLUTION (user decision, 2026-07-17): the analyzed board shows BOTH players' gems/greats; badges, eval-chart dots, and cycling are USER-ONLY.**

The first fix (`bb66dbd5`) made all four sites user-only and flagged the board (site 4) as a judgment call, since Plan 05 had deliberately shown the opponent's stored gems on the analyzed board with a "Your opponent found a gem move!" popover. The user reviewed the flag and decided to **restore the opponent gems on the analyzed board** (study context) while keeping the new Plan 06 stat surfaces user-only. Site 4 was therefore reverted in a targeted follow-up (`19722b82`); sites 1-3 stay user-only.

**The final scoping (three sites user-only, one site both-players):**

1. **`AnalysisTagsPanel.tsx` `bestMovePlies`** — USER-ONLY. Filter the gem/great ply collection with `isUserPly(pt.ply, game.user_color)`. Fixes both the badge COUNT and CYCLING (both derive from these lists).
2. **`LibraryGameCard.tsx` `bestMovePlies`** — USER-ONLY. Same filter, via a narrowed `userColor` (`game.user_color` is typed `string`).
3. **Eval-chart dots** — USER-ONLY. `bestMoveDotSpec` (`lib/bestMoveDot.ts`) gained a `userColor` argument; `EvalChart` gained an explicit `userColor?: 'white' | 'black'` prop (deliberately kept SEPARATE from `flipped`, which is display-only — move ownership is a data-scoping concern), threaded into `buildBestMoveDotRenderer` and the "Gem"/"Great" tooltip row. Both callers pass `user_color` (`LibraryGameCard` → `game.user_color`; `Analysis.tsx` → `gameData.user_color`). The misleading "no opponent gem concept" comments were updated to state that opponent best-moves exist in the data and are intentionally excluded here.
4. **`Analysis.tsx` `storedTierByPly` (analyzed-board corner markers)** — BOTH PLAYERS (reverted per the user decision). The map keeps every ply with a non-null `best_move_tier`/`maia_prob`, no user filter — the analyzed board is a study surface, and `resolveMarkerFor`'s `byOpponent` path renders the "Your opponent found a gem move!" popover for the opponent's gems. The `isUserPly` import was removed from `Analysis.tsx` (no longer referenced there; knip-clean).

**Fix commits:**
- `bb66dbd5` (fix) — user-only scoping across all four sites + the `plyOwnership` helper.
- `19722b82` (fix) — targeted revert of site 4 only (restore opponent gems on the analyzed board, per the user decision). Sites 1-3 untouched.

**Fix verification (from `frontend/`, after both fix commits):**
- `npx tsc -b` — clean (exit 0)
- `npm run lint` — 0 errors (3 pre-existing `coverage/` generated-file warnings only, unrelated)
- `npm run knip` — 0 issues (the removed `isUserPly` import from `Analysis.tsx` keeps it clean)
- `npm test -- --run` — 171 files / 2306 tests, all passing. The restored Plan 05 test asserts the opponent's stored gem DOES paint the analyzed board + move list with the opponent popover heading; the user-only tests for badges/cycling/dots continue to prove opponent plies are EXCLUDED there.

**Fix files created:** `frontend/src/lib/plyOwnership.ts`, `frontend/src/lib/__tests__/plyOwnership.test.ts`
**Fix files modified:** `frontend/src/lib/bestMoveDot.ts`, `frontend/src/components/library/EvalChart.tsx` (+ test), `frontend/src/components/results/LibraryGameCard.tsx` (+ test), `frontend/src/components/analysis/AnalysisTagsPanel.tsx` (+ test), `frontend/src/pages/Analysis.tsx` (+ test) — `Analysis.tsx` net change after both commits is only the `storedTierByPly` comment (the filter itself was added then reverted).

---
*Phase: 175-board-filter-gem-great-consumption*
*Completed: 2026-07-17*

## Self-Check: PASSED

All created/modified files confirmed present on disk; all 6 commits (`084baf26`,
`fe6222fb`, `eadb80f3`, `a2116b9c`, `bb66dbd5`, `19722b82`) confirmed in git
history. Final scoping: badges/eval-chart-dots/cycling are user-only; the
analyzed board shows both players' gems/greats (per the user's decision).
Full frontend suite 2306/2306 green; `npx tsc -b` clean; `npm run lint`
0 errors; `npm run knip` 0 issues.
