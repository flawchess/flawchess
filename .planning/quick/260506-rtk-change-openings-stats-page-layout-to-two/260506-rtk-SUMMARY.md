---
quick_id: 260506-rtk
type: summary
mode: quick
status: completed
completed: 2026-05-06
duration_minutes: ~30
commits:
  - hash: b08512c5
    subject: "feat(260506-rtk): replace Stats subtab table with 2-column card layout"
files_created:
  - frontend/src/components/stats/OpeningStatsCard.tsx
  - frontend/src/components/stats/OpeningStatsSection.tsx
  - frontend/src/components/stats/__tests__/OpeningStatsCard.test.tsx
files_modified:
  - frontend/src/pages/Openings.tsx
files_deleted:
  - frontend/src/components/stats/MostPlayedOpeningsTable.tsx
  - frontend/src/components/stats/__tests__/MostPlayedOpeningsTable.test.tsx
  - frontend/src/components/stats/MinimapPopover.tsx
---

# Quick task 260506-rtk: Stats subtab 2-column card layout

## Summary

Replaced the Openings → Stats subtab list/table layout with a 2-column card grid that mirrors Openings → Insights. Each opening (bookmark or most-played) is now an `OpeningStatsCard` with a permanent inline miniboard on the left and stacked content on the right (header, WDL chart, eval bullet chart with confidence info icon, and Moves + Games links). White openings stack in the left column at `lg+`, black in the right; single column on mobile. The previous list/table layout (`MostPlayedOpeningsTable`) and its parallel mobile renderer (`MobileMostPlayedRows`) are gone, along with the now-orphaned `MinimapPopover`.

## What changed

- **New `OpeningStatsCard`** — per-row card. Reuses `LazyMiniBoard`, `WDLChartRow` (with `showSegmentCounts={false}` for compactness), `MiniBulletChart`, `BulletConfidencePopover`, `evalZoneColor`, `MIN_GAMES_OPENING_ROW` muting, and the same mobile/desktop two-branch JSX shape as `OpeningFindingCard`. Border-left color tracks `evalZoneColor(avg_eval_pawns)` when MG eval is present, falls back to `transparent` (so the `border-l-4` still reserves space without misleading color) when `eval_n === 0`.
- **New `OpeningStatsSection`** — 2-column grid wrapper using the same `grid grid-cols-1 lg:grid-cols-2 gap-x-6 gap-y-4` shape as `OpeningInsightsBlock.SectionsContent`. White keys (`white-bookmarks`, `mpo-white`) get `lg:col-start-1`, black keys get `lg:col-start-2`. The "show N more" fold from `MostPlayedOpeningsTable` (`INITIAL_VISIBLE_COUNT = 3`) is preserved per section; bookmark sections pass `showAll`.
- **`Openings.tsx`** — rewrote the `statisticsContent` block. Bookmarks render through one `OpeningStatsSection` call, most-played through a second, with the WinRateChart sandwiched between them so behavior matches the previous layout. Dropped the `<div className="hidden lg:block">…<MostPlayedOpeningsTable /></div>` + `<div className="lg:hidden">…<MobileMostPlayedRows /></div>` split at all four sites. Deleted the inline `MobileMostPlayedRows` helper, `MOBILE_MPO_INITIAL_VISIBLE_COUNT`, and the now-unused `formatSignedEvalPawns`, `EVAL_BULLET_DOMAIN_PAWNS`, `EVAL_NEUTRAL_MAX_PAWNS`, `EVAL_NEUTRAL_MIN_PAWNS`, `evalZoneColor`, `MIN_GAMES_OPENING_ROW`, `BulletConfidencePopover`, `MinimapPopover`, `ChevronDown`, `ChevronUp` imports.
- **New `handleOpenMoves(opening, color)`** — wires the card's Moves link to the Move Explorer. Pattern mirrors `handleOpenFinding` from the Insights block: load the opening's PGN onto the board (`pgnToSanArray(opening.pgn)`), set color/flip/match-side filter, navigate to `/openings/explorer`. The PGN round-trip works for both most-played rows (canonical PGN from the API) and bookmark rows (`sanArrayToPgn(b.moves)` round-trip in `buildBookmarkRows`).
- **Deletions** — `MostPlayedOpeningsTable.tsx`, its test file, and `MinimapPopover.tsx` (orphaned after removal of MobileMostPlayedRows + MostPlayedOpeningsTable).
- **New tests** — `OpeningStatsCard.test.tsx` covers the 6 plan-stipulated behaviors: board fen + flip-by-color, WDL bar testid, eval cell signed text + zone color + bullet + popover, em-dash placeholder when `eval_n === 0`, Moves + Games callbacks invoked with `(opening, color)`, low-data muting, and border-left color (zone vs transparent fallback). Uses the same `normalizeColor` jsdom-oklch trick as the deleted `MostPlayedOpeningsTable.test.tsx`.

## Files touched

| Status | Path |
|---|---|
| created | `frontend/src/components/stats/OpeningStatsCard.tsx` |
| created | `frontend/src/components/stats/OpeningStatsSection.tsx` |
| created | `frontend/src/components/stats/__tests__/OpeningStatsCard.test.tsx` |
| modified | `frontend/src/pages/Openings.tsx` |
| deleted | `frontend/src/components/stats/MostPlayedOpeningsTable.tsx` |
| deleted | `frontend/src/components/stats/__tests__/MostPlayedOpeningsTable.test.tsx` |
| deleted | `frontend/src/components/stats/MinimapPopover.tsx` |

`Openings.tsx` is net −231 lines (1945 → 1714) thanks to the helper removals. Total diff: 7 files, +712 / −943.

## Commits

- `b08512c5` — `feat(260506-rtk): replace Stats subtab table with 2-column card layout`

## Verification

Ran inside `frontend/`:

- `npm run lint` — clean (eslint, no output).
- `npm run knip` — clean (no dead exports, no unused dependencies).
- `npm test -- --run` — 24 test files / 277 tests passing. New `OpeningStatsCard.test.tsx` contributes 11 tests covering the 6 behaviors above. `Openings.statsBoard.test.tsx` still passes (it tests the `getBoardContainerClassName` helper, unaffected by the layout change).
- `npm run build` — production build succeeds (3001 modules transformed, 4.99s).

Followed TDD: wrote the test file first, confirmed RED (component didn't exist → vitest "module not found"), implemented the component, confirmed GREEN. Initial GREEN run had 2 jsdom oklch normalization failures (`oklch(0.5 ...)` vs `oklch(0.50 ...)`), fixed by reusing the `normalizeColor` helper from the previous test file.

## Caveats

- **No real-browser visual verification.** This task ran in a worktree agent without a dev server running, so the new layout was not opened in a browser. The card structure was verified against `OpeningFindingCard.tsx` (which the user has already approved on the Insights subtab — the new card uses the exact same outer JSX shape). The plan explicitly noted manual smoke is "developer's responsibility, post-task".
- **Empty Bookmarks state preserved verbatim.** When `bookmarks.length === 0`, the existing "Tip: Save some openings…" CTA card still renders as the only Stats-tab content (it does not go through `OpeningStatsSection`). Same behavior as before.
- **MPO empty state combined.** Previously the white and black most-played sections each had their own `data-testid="mpo-white-section"` / `mpo-black-section` containers and were rendered as siblings. The new layout keeps the same testids on each grid cell, but the parent that controls whether the grid even mounts now checks `mostPlayedData.white.length > 0 || mostPlayedData.black.length > 0`. If both are empty, no grid renders — same as before (where both branches would skip independently).
- **InfoPopover testids preserved.** `mpo-white-info` and `mpo-black-info` testids stay on the section heading popovers.
- **Card idx scheme.** Cards use `idx = sectionIdx * 100 + rowIdx` so testids stay unique across white/black columns within one `OpeningStatsSection` call. This is implementation-internal; nothing else reads these idx values.
- **Moves link routing.** `handleOpenMoves` parses `opening.pgn` via `pgnToSanArray`. For bookmark rows, the pgn is a `sanArrayToPgn(b.moves)` round-trip done in `buildBookmarkRows`, so this round-trips cleanly. If a future bookmark has a malformed pgn, the load will throw inside `chess.loadMoves`. The previous code path would not have hit this since bookmarks didn't have a Moves link. Acceptable risk given the round-trip is exercised on every render of the Stats subtab and would surface immediately.

## Plan deviations

None worth flagging beyond the "card idx scheme" implementation choice noted above. The plan left the borderLeft fallback choice up to the executor (transparent vs muted token) — went with `transparent` so the `border-l-4` reserves space without color, matching how `OpeningFindingCard` has always been built.

## Self-Check

- `frontend/src/components/stats/OpeningStatsCard.tsx` — FOUND
- `frontend/src/components/stats/OpeningStatsSection.tsx` — FOUND
- `frontend/src/components/stats/__tests__/OpeningStatsCard.test.tsx` — FOUND
- `frontend/src/components/stats/MostPlayedOpeningsTable.tsx` — REMOVED (verified absent)
- `frontend/src/components/stats/__tests__/MostPlayedOpeningsTable.test.tsx` — REMOVED (verified absent)
- `frontend/src/components/stats/MinimapPopover.tsx` — REMOVED (verified absent)
- Commit `b08512c5` — FOUND in `git log`

## Self-Check: PASSED
