---
phase: 77-troll-opening-watermark-on-insights-findings
reviewed: 2026-04-29T00:00:00Z
depth: standard
files_reviewed: 11
files_reviewed_list:
  - frontend/scripts/curate-troll-openings.ts
  - frontend/src/components/insights/OpeningFindingCard.tsx
  - frontend/src/components/insights/OpeningFindingCard.test.tsx
  - frontend/src/components/insights/OpeningInsightsBlock.test.tsx
  - frontend/src/components/move-explorer/MoveExplorer.tsx
  - frontend/src/components/move-explorer/__tests__/MoveExplorer.test.tsx
  - frontend/src/data/trollOpenings.ts
  - frontend/src/lib/theme.ts
  - frontend/src/lib/trollOpenings.ts
  - frontend/src/lib/trollOpenings.test.ts
  - frontend/knip.json
findings:
  blocker: 1
  warning: 4
  total: 5
status: issues_found
---

# Phase 77: Code Review Report

**Reviewed:** 2026-04-29
**Depth:** standard
**Files Reviewed:** 11
**Status:** issues_found

## Summary

The phase delivers a clean visual easter egg with strong test coverage. The core derivation helper is well-isolated and unit-tested. However, the derivation throws on malformed FEN inputs and is invoked unconditionally during render of every Insights card and every Move Explorer row — a single bad payload becomes a render-time crash that takes down the entire surface (no error boundary in either subtree). Several test-fidelity and defensive-coding gaps are also flagged.

Phase artifacts already document known intentional deviations (stub data file, Bongcloud test FEN correction, `makeEntry` default change, `useMemo` ordering); those are not re-flagged here.

## Blocker Issues

### BL-01: `isTrollPosition` throws on malformed FEN; no boundary protects Insights/Explorer surfaces

**Files:**
- `frontend/src/lib/trollOpenings.ts:15-17` (the throw)
- `frontend/src/components/insights/OpeningFindingCard.tsx:61` (call site)
- `frontend/src/components/move-explorer/MoveExplorer.tsx:268` (call site)

**Issue:** `deriveUserSideKey` throws `Invalid FEN piece-placement: expected 8 ranks, got N` whenever the input doesn't have exactly 8 ranks. `isTrollPosition` calls it unconditionally and is then invoked at render time inside `OpeningFindingCard` (every finding) and `MoveRow` (every row). A single malformed `entry_fen` or `result_fen` from the API would throw during render and — without an error boundary — break the whole Insights block or Move Explorer table. The fragility was already visible during execution: changing the `makeEntry` test default from `result_fen: ''` to a valid 8-rank FEN was forced (77-04-SUMMARY.md) because every pre-existing Move Explorer test crashed on the same throw. Production code shouldn't be more brittle than test scaffolding.

**Fix:** Make `isTrollPosition` defensive — catch the throw and return `false`, so a bad FEN suppresses the watermark/icon rather than crashing the surface:
```ts
export function isTrollPosition(fen: string, side: Color): boolean {
  let key: string;
  try {
    key = deriveUserSideKey(fen, side);
  } catch {
    return false; // decorative; missing the easter egg beats crashing the panel
  }
  return side === 'white' ? WHITE_TROLL_KEYS.has(key) : BLACK_TROLL_KEYS.has(key);
}
```
Keep `deriveUserSideKey` strict (the curation script still wants the throw). Add a unit test asserting `isTrollPosition('garbage', 'white') === false`. Apply the same logic to the `position`-prop throw in `MoveExplorer.tsx:81-85` — downgrade to a fallback (skip troll matching) so the panel keeps rendering.

## Warnings

### WR-01: Move Explorer test fixture `RESULT_FEN_AFTER_E5` is inconsistent with its SAN context

**File:** `frontend/src/components/move-explorer/__tests__/MoveExplorer.test.tsx:37, 320, 363, 381, 395`

**Issue:** `RESULT_FEN_AFTER_E5 = 'rnbqkbnr/pppp1ppp/8/4p3/4P3/8/PPPP1PPP/RNBQKBNR'` is the position after **1.e4 e5** (both pawns on the board), yet it is paired with `makeEntry({ move_san: 'e4', result_fen: RESULT_FEN_AFTER_E5 })` rendered from `position={START_FEN}`. The actual result FEN of playing `e4` from start is `rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR` (no black e5). The tests pass because `MoveExplorer` doesn't replay the move — it just feeds `entry.result_fen` to `isTrollPosition`. But the fixture misrepresents the SAN→result_fen contract production code relies on, making future tests that validate move legality with chess.js break unexpectedly.

**Fix:** Either rename to a name that matches the fixture content (e.g. `RESULT_FEN_BONGCLOUD_KEY_TRIGGER`) and acknowledge it's a synthetic key-only fixture, or pick a real post-e4 position whose white-stripped key is in the curated set. Lowest-friction: rename the constant + adjust the SAN tokens so the SAN/parent/result triple is internally consistent.

### WR-02: Watermark visually overlaps the Moves/Games link row on mobile

**File:** `frontend/src/components/insights/OpeningFindingCard.tsx:144-158, 184`

**Issue:** On mobile (the `flex flex-col gap-2 sm:hidden` branch), `linksRow` is the last item stacked in the right-hand sub-column. The watermark is anchored `bottom-2 right-2` at `h-16 w-16` (64px) with `pointer-events-none`. At 375px, the 64px stamp sits behind the Moves/Games button row. `pointer-events-none` keeps clicks working, but at 30% opacity the stamp still cuts text/button contrast on the controls users are trying to read. CONTEXT.md D-03 explicitly mandated 375px visual re-verification; 77-03-SUMMARY.md does not record one.

**Fix:** Either (a) shrink the mobile watermark below the link-row band: `h-12 w-12 sm:h-20 sm:w-20`; or (b) anchor it to top-right on mobile only: `top-2 right-2 sm:top-auto sm:bottom-2`; or (c) verify visually at 375px and document the result. Recommend (a).

### WR-03: Knip `ignore` for the data file masks future dead exports

**File:** `frontend/knip.json:18`

**Issue:** Adding `"src/data/trollOpenings.ts"` to `ignore` means knip will no longer flag *any* unused export from that file. Today both `WHITE_TROLL_KEYS` and `BLACK_TROLL_KEYS` are imported by `lib/trollOpenings.ts`, so the file is genuinely live. Per Pitfall 5 in 77-RESEARCH.md, the prescribed pattern is "import both sets in the helper so neither goes unused" — that's already how the helper works. Adding the file to `ignore` defensively means a future refactor that drops one set, or adds a third unused export, won't be caught.

**Fix:** Remove `src/data/trollOpenings.ts` from the `knip.json` ignore list. If knip currently flags it, investigate the actual reason (Plan 02's note about the "unused until Plan 03" window is now moot — `isTrollPosition` imports both sets and is used by both `OpeningFindingCard` and `MoveExplorer`).

### WR-04: Curation script bypasses the project's `noUncheckedIndexedAccess` enforcement

**File:** `frontend/scripts/curate-troll-openings.ts` (whole file)

**Issue:** `frontend/tsconfig.app.json` enables `noUncheckedIndexedAccess`, but `frontend/scripts/` is not included in any project tsconfig — the script runs via `npx tsx` and only gets type-checked transitively when `tsx` runs it. CLAUDE.md mandates "every array/Record index access in the curation script and the utility returns `T | undefined`" (per RESEARCH.md). Today the script gets away with `chapters[chapterIdx]!`, `verboseHistory[plyIdx]!`, `sans[i]!`, `tokens[1]` etc. via `!` assertions justified by loop-bound comments — that's locally fine, but the enforcement is by author discipline, not by the type-checker. A future edit could regress without notice.

**Fix:** Either (a) add `frontend/scripts/**` to `tsconfig.app.json`'s `include` array, or (b) create a sibling `frontend/tsconfig.scripts.json` that extends `tsconfig.app.json` and add a `tsc -p tsconfig.scripts.json` step to CI. (a) is one-line. Also add a run-time guard `if (!title) continue;` in `extractCandidates` to formalize the implicit non-null assumption on `headers.Event` / `headers.White`.

### WR-05: `sideJustMoved` `useMemo` contradicts the documented anti-pattern and creates load-bearing render order

**File:** `frontend/src/components/move-explorer/MoveExplorer.tsx:78-87`

**Issue:** 77-RESEARCH.md "Anti-Patterns to Avoid" explicitly says: *"Computing `isTrollPosition` inside a `useMemo` or hook ... Memoizing adds React-render bookkeeping for a function that runs in <1µs. Just call it inline."* The same logic applies here — it's a `string.split` + 1-char compare on a stable prop. 77-04-SUMMARY.md notes this `useMemo` had to be reordered to run before `moveMap`'s `useMemo` so the friendly error message wins; that ordering is now load-bearing for error UX, which is fragile (a future hook insertion could re-break it).

**Fix:** Inline it as a plain `const` at the top of the component body so the derivation runs synchronously before `moveMap`:
```tsx
const sideToken = position.split(' ')[1];
if (sideToken !== 'w' && sideToken !== 'b') {
  throw new Error(`MoveExplorer: position must be a full FEN with side-to-move, got: ${position}`);
}
const sideJustMoved: Color = sideToken === 'w' ? 'white' : 'black';
```
Combined with BL-01, also relax the throw to a fallback so a bad FEN doesn't break the whole panel.

---

_Reviewed: 2026-04-29_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
