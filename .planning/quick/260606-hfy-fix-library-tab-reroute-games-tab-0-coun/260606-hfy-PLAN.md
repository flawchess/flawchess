---
phase: quick-260606-hfy
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - frontend/src/pages/library/LibraryPage.tsx
  - frontend/src/pages/library/GamesTab.tsx
  - frontend/src/components/results/LibraryGameCardList.tsx
  - frontend/src/pages/library/__tests__/LibraryPage.reroute.test.tsx
autonomous: true
requirements: [LIB-FIX-REROUTE, LIB-FIX-COUNT, LIB-FIX-TABORDER]

must_haves:
  truths:
    - "Clicking the Library nav lands on a Library subtab (not the Openings page)"
    - "The Games subtab count row shows matched games out of the user's real total imported games (no '... of 0')"
    - "Library subtabs are ordered Import - Games - Stats and the Stats trigger uses the same icon as the Openings Stats subtab (BarChart2)"
  artifacts:
    - path: "frontend/src/pages/library/LibraryPage.tsx"
      provides: "Library landing redirect + subtab order/icon"
    - path: "frontend/src/components/results/LibraryGameCardList.tsx"
      provides: "Count row denominator wiring"
  key_links:
    - from: "GamesTab.tsx"
      to: "useUserProfile"
      via: "total imported game count passed as count denominator"
---

<objective>
Fix three frontend bugs in the Library tab introduced/exposed by Phase 107 work:

1. The Library nav immediately reroutes to the Openings page (can't access Library).
2. The Games subtab count row reads "N of 0 games" because it references a non-existent `total` field on the API response.
3. The Library subtabs are ordered Import / Stats / Games and the Stats tab uses a different icon than the Openings Stats subtab.

Purpose: Restore Library navigation and a correct game-count display, and align subtab ordering/iconography with the Openings page.
Output: Corrected `LibraryPage.tsx`, `GamesTab.tsx`, `LibraryGameCardList.tsx`, plus a small regression test for the reroute.
</objective>

<execution_context>
@$HOME/.claude/gsd-core/workflows/execute-plan.md
@$HOME/.claude/gsd-core/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@CLAUDE.md

# Root-caused files (read these — line numbers from planning investigation)
@frontend/src/pages/library/LibraryPage.tsx
@frontend/src/pages/library/GamesTab.tsx
@frontend/src/components/results/LibraryGameCardList.tsx

# Reference for the correct Stats icon (Openings page uses BarChart2)
# frontend/src/pages/Openings.tsx:15 imports BarChart2; lines 806-808 use it on the Stats TabsTrigger.

# Profile-count pattern already present in LibraryPage.tsx:19-22
# (profile.chess_com_game_count + profile.lichess_game_count). useUserProfile from '@/hooks/useUserProfile'.
</context>

<tasks>

<task type="auto">
  <name>Task 1: Fix Library landing reroute + reorder subtabs + Stats icon</name>
  <files>frontend/src/pages/library/LibraryPage.tsx</files>
  <action>
ROOT CAUSE (reroute): In LibraryPage.tsx the landing redirect (currently lines 27-35) sends users with games OFF the Library page entirely — `Navigate to={noGames ? '/library/import' : '/openings'}`. This is why clicking Library immediately lands on Openings. Decision 7 (commit 51537b63) is explicitly marked reversible in the comment.

Fix the redirect so a returning user with games lands on a Library SUBTAB instead of leaving the page. Change the redirect target from `/openings` to `/library/games` (returning users with games should see their games browser; new users with zero games still go to `/library/import`). Keep the `profile != null` guard (only redirect once the profile is loaded) and the `replace` behavior. Update the inline comment to reflect the new behavior (replace the "returning users go to Openings" note; remove or revise the commit-51537b63 reference so the comment matches the code).

ROOT CAUSE (tab order + icon): The subtab order is Import / Stats / Games and the Stats trigger uses `LayoutDashboard`. The Openings Stats subtab uses `BarChart2` (see Openings.tsx:15, 806-808).

Reorder the TabsTrigger elements in BOTH the desktop block (lines ~56-67) and the mobile block (lines ~103-127) to: Import, Games, Stats. The `TabsContent` blocks do not need reordering (Tabs matches by value), but you MAY reorder them too for readability — keep all six values (`import`, `games`, `stats` x2 sections) intact.

Replace the Stats trigger icon `LayoutDashboard` with `BarChart2` in the desktop block. The mobile Stats trigger currently has NO icon (line ~111-118 renders just "Stats" text) — add `<BarChart2 className="mr-1.5 h-4 w-4" />` before the "Stats" label to match the desktop trigger and the Openings pattern. (Per CLAUDE.md "apply changes to mobile too".)

Update imports on line 2: remove `LayoutDashboard` (verify it has no other use in the file — it does not), add `BarChart2`. Import from `lucide-react`.

Preserve all existing `data-testid` attributes (`tab-import`, `tab-games`, `tab-stats`, and the `-mobile` variants) exactly. Preserve the `activeTab` derivation logic (lines 37-41) — it keys off `/import` and `/games` substrings and defaults to `stats`, which still works after reordering.
  </action>
  <verify>
    <automated>cd frontend && npx tsc --noEmit 2>&1 | grep -i "LibraryPage" || echo "no LibraryPage type errors"</automated>
  </verify>
  <done>Clicking Library (path `/library`) with games redirects to `/library/games`, with zero games to `/library/import` — never to `/openings`. Subtab triggers render in order Import, Games, Stats on desktop and mobile. Both Stats triggers show the BarChart2 icon. `LayoutDashboard` no longer imported. tsc passes.</done>
</task>

<task type="auto">
  <name>Task 2: Fix the "N of 0 games" count row denominator</name>
  <files>frontend/src/pages/library/GamesTab.tsx, frontend/src/components/results/LibraryGameCardList.tsx</files>
  <action>
ROOT CAUSE: GamesTab.tsx line 169 reads `const totalGames = gamesData?.total ?? 0;`, but the API response type `LibraryGamesResponse` (frontend/src/types/library.ts:77-82 and backend app/schemas/library.py:53-63) has NO `total` field — only `games`, `matched_count`, `offset`, `limit`. So `totalGames` is ALWAYS 0, producing "5090 of 0 games" in LibraryGameCardList.tsx:54-56. This is a frontend-only bug; do NOT add a backend `total` field (avoids an unfiltered count query and a schema change — the user's profile already carries the real total).

Fix in GamesTab.tsx:
- Import `useUserProfile` from '@/hooks/useUserProfile' (same hook LibraryPage.tsx:15 uses).
- Call it: `const { data: profile } = useUserProfile();`
- Compute the real total imported games the same way LibraryPage.tsx:19-22 does:
  `const totalImported = profile != null ? profile.chess_com_game_count + profile.lichess_game_count : 0;`
  Add a named-constant-free comment noting this is the user's all-platform imported-game total (the count-row denominator), distinct from `matched_count` (games matching the current filters).
- Replace line 169 `const totalGames = gamesData?.total ?? 0;` with `const totalGames = totalImported;`.
- The `noGamesImported` derivation (line 174) currently keys off `totalGames === 0`; since `totalGames` is now profile-based, this still reads correctly (zero imported games ⇒ empty state). Verify the empty-state logic still makes sense: `noGamesImported` should be true when the user has imported nothing, `noMatchedGames` when they have games but filters matched none. Keep `matchedCount`-based gating for the list render (line 238) unchanged.

LibraryGameCardList.tsx needs no structural change — it already renders `{matchedCount} of {total} games` (line 54) using the `total` prop passed from GamesTab (line 241 `total={totalGames}`). After Task 2 wiring, `total` carries the real imported count. Confirm the prop name `total` still maps to `totalGames` in the GamesTab call site; no rename needed.

Do NOT change the backend or the API client.
  </action>
  <verify>
    <automated>cd frontend && grep -n "gamesData?.total" src/pages/library/GamesTab.tsx && echo "STILL PRESENT - FAIL" || echo "removed OK"</automated>
  </verify>
  <done>GamesTab no longer references `gamesData?.total`. The count row denominator is the user's total imported games (chess_com + lichess from profile). With imported games present and 5090 matches, the row reads "5090 of {realTotal} games", never "of 0". Empty-state branches still behave correctly.</done>
</task>

<task type="auto">
  <name>Task 3: Add a reroute regression test</name>
  <files>frontend/src/pages/library/__tests__/LibraryPage.reroute.test.tsx</files>
  <action>
Add a focused regression test for the Library landing redirect (Task 1). Place it at frontend/src/pages/library/__tests__/LibraryPage.reroute.test.tsx (create the __tests__ dir if absent).

Follow the existing frontend test conventions (vitest + @testing-library/react + react-router MemoryRouter). Look at frontend/src/pages/__tests__/Openings.statsBoard.test.tsx or Import.stateMachine.test.tsx for the mocking pattern (how they mock hooks like useUserProfile and wrap in providers/router).

Mock `useUserProfile` to control the profile. Render `LibraryPage` inside a `MemoryRouter` with `initialEntries={['/library']}` and a `Routes`/catch-all that captures the resolved location (e.g. a `<Route path="*">` location-spy, or assert via a LocationDisplay component reading useLocation).

Two assertions:
1. Profile with games (e.g. chess_com_game_count: 10, lichess_game_count: 0) ⇒ redirect resolves to `/library/games` (NOT `/openings`).
2. Profile with zero games (both counts 0) ⇒ redirect resolves to `/library/import`.

If mocking the full LibraryPage subtree (ImportTab/GamesTab/StatsTab pull in many deps) is heavy, mock those three child components to trivial stubs so the test isolates the redirect logic. Keep the test under ~60 lines. Provide a QueryClientProvider if any child or hook requires it.

Do not over-engineer — this single test guards the reroute regression cheaply; no need to test tab order or count display (those are visual/data-shape changes covered by tsc + manual UAT).
  </action>
  <verify>
    <automated>cd frontend && npx vitest run src/pages/library/__tests__/LibraryPage.reroute.test.tsx 2>&1 | tail -15</automated>
  </verify>
  <done>The new test passes: `/library` with games redirects to `/library/games`, with zero games to `/library/import`. Test does not assert `/openings` anywhere as a Library landing target.</done>
</task>

</tasks>

<verification>
Run the frontend gate (CLAUDE.md Pre-PR checklist, frontend portion):

```bash
cd frontend && npm run lint && npm test -- --run
```

All must pass. tsc (via build/lint) must be clean. Manual UAT (not blocking, note in SUMMARY): start dev server, click Library nav → lands on Library Games subtab (with games) or Import (zero games), never Openings; Games count row shows real total; subtabs read Import / Games / Stats with the bar-chart icon on Stats (desktop + mobile).
</verification>

<success_criteria>
- Library nav reaches a Library subtab, never `/openings`.
- Games subtab count row shows correct "{matched} of {totalImported} games".
- Subtab order is Import / Games / Stats; Stats uses BarChart2 on desktop and mobile.
- New reroute regression test passes; frontend lint + tests green.
</success_criteria>

<output>
Create `.planning/quick/260606-hfy-fix-library-tab-reroute-games-tab-0-coun/260606-hfy-SUMMARY.md` when done.
</output>
