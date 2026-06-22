---
phase: quick-260622-fdh
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - frontend/src/components/results/LibraryGameCard.tsx
autonomous: true
requirements: [QUICK-260622-fdh]
must_haves:
  truths:
    - "On desktop (sm+), the LibraryGameCard board renders at ~200px square in a left column"
    - "On desktop, the game date appears in the card header, not in the body metadata block"
    - "On desktop, the right column stacks: compact metadata strip, eval chart + severity badges, tactic chips (Missed/Allowed/Context)"
    - "The mobile body (sm:hidden) is byte-for-byte unchanged, including its date-in-metadata block"
    - "tsc -b, lint, and frontend tests all pass"
  artifacts:
    - path: "frontend/src/components/results/LibraryGameCard.tsx"
      provides: "Redesigned desktop body with board-left / stacked-right two-column layout"
      contains: "DESKTOP_BOARD_SIZE"
  key_links:
    - from: "LibraryGameCard desktop body"
      to: "LazyMiniBoard"
      via: "size={DESKTOP_BOARD_SIZE} with DESKTOP_BOARD_SIZE = 200"
      pattern: "DESKTOP_BOARD_SIZE"
    - from: "LibraryGameCard desktop right column"
      to: "chipsBlock / severityBadges shared fragments"
      via: "relocated into the right column without changing how the mobile body consumes them"
      pattern: "chipsBlock"
---

<objective>
Redesign the desktop (`hidden sm:flex`) body of `LibraryGameCard.tsx` into a board-left / stacked-right two-column layout, leaving the mobile (`sm:hidden`) body byte-for-byte unchanged.

Purpose: a larger board and a cleaner, denser desktop card. The board grows from 132px to ~200px and moves into its own full-height left column; the right column stacks a one-line metadata strip, the eval chart + severity badges, and the tactic chips (which move out of the current full-width Row 2). The game date moves from the body metadata into the header.

Output: a single redesigned desktop body in `LibraryGameCard.tsx`. No new files, no backend changes.
</objective>

<execution_context>
@$HOME/.claude/gsd-core/workflows/execute-plan.md
</execution_context>

<context>
@.planning/STATE.md
@./CLAUDE.md

# The component under redesign (read fully — already analyzed in planning):
@frontend/src/components/results/LibraryGameCard.tsx

# Sub-component prop contracts (already analyzed in planning):
# - LazyMiniBoard takes a numeric `size` px prop.
# - EvalChart takes a `heightClass` Tailwind prop.
@frontend/src/components/board/LazyMiniBoard.tsx
@frontend/src/components/library/EvalChart.tsx
@frontend/src/components/results/LibraryGameCardList.tsx
</context>

<constraints>
Read and honor CLAUDE.md, especially the Frontend section. Specifically:
- Mobile body (`<div className="flex flex-col gap-2 sm:hidden px-4 py-4">`, ~line 894) must be UNCHANGED. Do not touch it.
- The shared `severityBadges` (~line 716) and `chipsBlock` (~line 791) fragments are consumed by BOTH bodies. Relocating them in the desktop body must NOT change their definitions or how the mobile `flawContent` (~line 860) composes them. Move only WHERE they render in the desktop body, not WHAT they are.
- No magic numbers — the desktop board size is a named constant (`DESKTOP_BOARD_SIZE`, bump 132 → 200). Leave `MOBILE_BOARD_SIZE` untouched.
- `text-sm` is the floor — no `text-xs` in new code (the existing hover/tap info-tooltip exception does not apply to the new metadata strip).
- Theme colors from `theme.ts`; no hardcoded semantic colors. The redesign should reuse existing classes/fragments, so no new color literals are expected.
- Keep all existing `data-testid`s working (`flaw-controls-${game.game_id}`, `card-col2-${game.game_id}`, `eval-chart-${game.game_id}`, `library-game-card-${game.game_id}`, etc.). Add `data-testid` to any NEW interactive element (none expected — this is layout-only).
- Frontend has NO Prettier — do NOT run prettier. ESLint only.
- npm lint/test do NOT type-check (esbuild strips types) — `npx tsc -b` (or `npm run build`) is REQUIRED in verify.
</constraints>

<tasks>

<task type="auto">
  <name>Task 1: Move the date into the desktop header and add a desktop-only metadata strip</name>
  <files>frontend/src/components/results/LibraryGameCard.tsx</files>
  <action>
The game date currently renders only in the shared `metadata` block (via `dateItem`, ~line 668), which both bodies consume. The mobile body must keep showing the date in its metadata, but the desktop body must show it in the header instead. So do NOT remove `dateItem` from the shared `metadata` — instead give the desktop body its own metadata source.

(a) Header: in the desktop header span (the `hidden sm:block` span at ~line 644, which renders "■ White (rating) vs □ Black (rating)"), append the formatted date so the header reads names + ratings + date. Reuse `formatDate(game.played_at)` and render it as a muted trailing element (e.g. a `text-muted-foreground` span separated by a "·" or wrapped so it sits to the right of the matchup). Keep it on the single desktop header line; truncate behavior on the matchup must still work. Do NOT touch the mobile header block (the `flex sm:hidden` div at ~line 649). The date is a small calendar-less label here; reuse the `Calendar` icon only if it reads well, otherwise plain text is fine.

(b) Desktop metadata strip: create a NEW desktop-only metadata fragment (a single compact line) rendering `opening name · time control · move count · result`, WITHOUT the date (the date moved to the header). One line, `text-sm`, truncate/ellipsis the opening name when it overflows. Reuse the existing item fragments where practical: `timeControlItem`, `moveCountItem`, and the `resultIndicator`/`terminationItem`; render the opening name inline (it currently lives in `openingLine`). Keep it to ONE visual line (e.g. `flex items-center gap-2 ... truncate` with the opening name as the only flexible/truncating element). Name it clearly (e.g. `desktopMetaStrip`). This fragment is used ONLY by the desktop body in Task 2; it must not alter the shared `metadata`, `openingLine`, or mobile rendering.
  </action>
  <verify>
    <automated>cd frontend && npx tsc -b</automated>
  </verify>
  <done>The desktop header includes the game date; a new desktop-only metadata strip fragment (opening · TC · moves · result, no date, one line, text-sm) exists. The shared `metadata` block and mobile header/body are unchanged. `npx tsc -b` passes.</done>
</task>

<task type="auto">
  <name>Task 2: Rebuild the desktop body as board-left / stacked-right two columns</name>
  <files>frontend/src/components/results/LibraryGameCard.tsx</files>
  <action>
Rewrite ONLY the desktop body — the `<div className="hidden sm:flex sm:flex-col sm:gap-3 px-4 py-4">` block (~lines 945-1042). Do not touch the mobile body above it or the shared fragment definitions.

Bump the board constant: change `const DESKTOP_BOARD_SIZE = 132;` to `const DESKTOP_BOARD_SIZE = 200;` (~line 61). Leave `MOBILE_BOARD_SIZE` as-is.

New desktop body structure (header stays above, unchanged structurally apart from the date added in Task 1):
- A two-column flex row: `flex gap-3 items-stretch` (items-stretch so the right column drives height and the left board column can read as full-height).
  - LEFT column: the `LazyMiniBoard` ONLY, `size={DESKTOP_BOARD_SIZE}` (200), keeping the existing props (`fen={boardFen}`, `flipped`, `arrows={boardArrows}`, `lastMove={lastMove}`). It is `shrink-0`. The board is 200px square; the right column's three stacked rows should sum to roughly the same height so the row reads balanced (~210px body). The W/D/L accent stays on the `Card` (do not move it).
  - RIGHT column: `flex-1 min-w-0 flex flex-col gap-2`, three stacked rows:
    1. The desktop metadata strip from Task 1 (`desktopMetaStrip`).
    2. Eval chart + severity badges — SAME pairing as today: a flex row with the chart wrapper `flex-1 min-w-0` (keep the `card-col2-${game.game_id}` testid on the chart wrapper) and the severity badge stack beside it (`flex flex-col items-stretch gap-1.5 shrink-0 [&>*]:justify-center` with the `flaw-controls-${game.game_id}` testid, exactly as the current desktop Row 1 does). Render `<EvalChart .../>` with the same props as the current desktop instance; the chart `heightClass` may stay `h-[116px]` or be adjusted slightly so rows 1-3 sum to ~200px (the board height) — pick a value and keep `text-sm` floor irrelevant here (chart is graphical). For the analyzed-but-missing-series and unanalyzed states, reuse the existing `NoAnalysisState` fallbacks already present in the desktop body (preserve the `card-col2-${game.game_id}` testid on the relevant wrapper for the analyzed branch).
    3. The tactic chips: render `chipsBlock` (the shared fragment) here, wrapped in the `flaw-controls-${game.game_id}` div (`flex flex-col gap-1.5`), analyzed-games-and-`chipsBlock`-truthy only — same guard as the current Row 2 (`game.analysis_state === 'analyzed' && chipsBlock`). The chips now occupy the right column (~70% width) instead of full width; more wrapping is acceptable and expected. Do NOT modify `chipsBlock`, `ChipColumn`, or `TacticMotifGroup` — only relocate the render site.

Notes:
- The current desktop body had the md-grid alignment trick (board col aligns with the ALLOWED chip column). That alignment goal is GONE in the new layout (chips are in the right column, not a full-width row), so drop the `md:grid md:grid-cols-3` / `md:col-span-2` wiring and the alignment comments. Replace with the straightforward flex two-column layout above.
- Two `data-testid="flaw-controls-${game.game_id}"` wrappers can legitimately exist in the desktop body (severity stack + chips block) — this already happens in the current code and the outside-pointer handler uses `closest(...)`, so it is fine.
- Keep using `cn(...)` for any conditional classes; do not hand-roll string concatenation where `cn` is already the pattern.
  </action>
  <verify>
    <automated>cd frontend && npx tsc -b && npm run lint</automated>
  </verify>
  <done>The desktop body is a two-column layout: board-only left column at 200px, right column stacking metadata strip + (eval chart + severity badges) + tactic chips. `DESKTOP_BOARD_SIZE` is 200. The mobile body and all shared fragment definitions are unchanged. Existing testids preserved. `tsc -b` and `npm run lint` pass.</done>
</task>

<task type="auto">
  <name>Task 3: Verify full frontend gate and confirm mobile body is untouched</name>
  <files>frontend/src/components/results/LibraryGameCard.tsx</files>
  <action>
Run the full frontend gate. Then confirm the mobile body block (the `sm:hidden` div and everything it renders) is byte-for-byte unchanged versus before this task — compare against git (`git diff` should show changes ONLY in: the `DESKTOP_BOARD_SIZE` constant, the desktop header span, the new desktop metadata strip fragment, and the desktop body block; NOT in the mobile body, the shared `metadata`/`openingLine`/`severityBadges`/`chipsBlock`/`flawContent` definitions, or the mobile header).

If `git diff` shows any change inside the `sm:hidden` mobile body or inside the shared fragment definitions (other than relocating where `severityBadges`/`chipsBlock` are RENDERED in the desktop body), revert that change — those must stay identical.
  </action>
  <verify>
    <automated>cd frontend && npx tsc -b && npm run lint && npm test -- --run</automated>
  </verify>
  <done>`npx tsc -b`, `npm run lint`, and `npm test -- --run` all pass. `git diff frontend/src/components/results/LibraryGameCard.tsx` confirms the mobile body and shared fragment definitions are unchanged; only the desktop constant, header date, new desktop metadata strip, and desktop body block changed.</done>
</task>

</tasks>

<verification>
- `cd frontend && npx tsc -b` — type-checks clean (REQUIRED; lint/test do not type-check).
- `cd frontend && npm run lint` — ESLint clean (no Prettier).
- `cd frontend && npm test -- --run` — frontend tests pass.
- `git diff frontend/src/components/results/LibraryGameCard.tsx` — changes confined to the desktop constant, desktop header date, new desktop metadata strip, and desktop body block; mobile body and shared fragments untouched.
</verification>

<success_criteria>
- Desktop body: board-only left column at ~200px (named `DESKTOP_BOARD_SIZE`), right column stacking metadata strip → eval chart + severity badges → tactic chips.
- Game date shows in the desktop header, removed from the desktop body metadata, still present in the mobile metadata.
- Mobile body byte-for-byte unchanged; shared `severityBadges`/`chipsBlock` fragments relocated (not redefined) in the desktop body.
- No magic numbers, `text-sm` floor respected, theme colors only, testids preserved.
- Full frontend gate (`tsc -b`, lint, test) green.
</success_criteria>

<output>
Create `.planning/quick/260622-fdh-redesign-librarygamecard-desktop-layout-/260622-fdh-SUMMARY.md` when done.
</output>
