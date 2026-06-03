---
phase: quick-260603-pgv
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - frontend/src/components/insights/OpeningFindingCard.tsx
  - frontend/src/components/stats/OpeningStatsCard.tsx
  - frontend/src/components/insights/OpeningInsightsBlock.tsx
  - frontend/src/lib/theme.ts
  - frontend/src/components/insights/OpeningFindingCard.test.tsx
  - frontend/src/components/stats/__tests__/OpeningStatsCard.test.tsx
autonomous: true
requirements: [QUICK-260603-pgv]

must_haves:
  truths:
    - "In the Insights card, only the Score row dims when score confidence is low; only the Eval row dims when eval confidence is low"
    - "In the Stats card, the same per-row dimming applies; the whole-card <20-games dim is gone"
    - "Neither card root carries opacity:0.5 anymore"
    - "The Insights section info popover copy describes per-row (per-stat) dimming, not whole-card dimming"
    - "Card border / left-spine accent and the on-board arrow are unchanged"
  artifacts:
    - path: "frontend/src/components/insights/OpeningFindingCard.tsx"
      provides: "Per-row confidence dimming on score + eval rows"
    - path: "frontend/src/components/stats/OpeningStatsCard.tsx"
      provides: "Per-row confidence dimming; isCardMuted removed"
    - path: "frontend/src/components/insights/OpeningInsightsBlock.tsx"
      provides: "Updated dimming-copy in the FindingsSection info popover"
  key_links:
    - from: "OpeningFindingCard.tsx score row cells"
      to: "isConfident(finding.confidence)"
      via: "dimScoreRow opacity style"
      pattern: "dimScoreRow"
    - from: "OpeningStatsCard.tsx eval row cells"
      to: "isConfident(opening.eval_confidence)"
      via: "dimEvalRow opacity style"
      pattern: "dimEvalRow"
---

<objective>
In the Openings Stats and Insights cards, dim the Score and Eval rows individually (mini bullet chart + value text + confidence popover trigger) when that specific row's confidence is low, instead of dimming the whole card. Update the Insights section info-popover copy about dimming to match.

Purpose: A card with a reliable score but a noisy eval (or vice versa) currently dims everything, hiding good signal. Per-row dimming keeps the trustworthy stat at full opacity and only fades the one that isn't statistically distinguishable from chance.

Output: Both card components dim per-row, the whole-card opacity dim is removed from both, the now-dead `MIN_GAMES_OPENING_ROW` constant is removed, the Insights tooltip copy is updated, and all affected tests are rewritten to assert per-row dimming.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md

Read these source files in full before editing (the orchestrator already confirmed line context, but read to anchor your edits):
@frontend/src/components/insights/OpeningFindingCard.tsx
@frontend/src/components/stats/OpeningStatsCard.tsx
@frontend/src/components/insights/OpeningInsightsBlock.tsx

Key facts already established (do not re-explore):
- In BOTH cards, `scoreEvalBlock` is a single `const` JSX value reused in both the mobile (`sm:hidden`) and desktop (`hidden sm:flex`) layouts. A single edit to that const covers both layouts. Do NOT duplicate the change anywhere — there is no per-layout copy of the score/eval rows.
- There is NO shared per-row wrapper element. The 2-col grid lays the four cells out directly: a bullet `<div>` and a text `<span>` for the score row, and (in the `tier2` branch) a bullet `<div>` and a text `<span>` for the eval row. To dim a row you must apply the opacity style to BOTH cells of that row.
- `isConfident` and `UNRELIABLE_OPACITY` are already imported in both card files. Do NOT add a new opacity constant, a new prop, or a new color.
- `MIN_GAMES_OPENING_ROW` (theme.ts:90) is imported ONLY by `OpeningStatsCard.tsx` (and referenced by its test). After removing `isCardMuted`, the constant becomes dead. Knip runs in CI and fails on unused exports, so the export in `theme.ts` must also be removed.
- `MIN_GAMES_FOR_RELIABLE_STATS` and the `isReliableScore` border/left-spine logic stay untouched in both cards. Only opacity behavior changes.
</context>

<tasks>

<task type="auto">
  <name>Task 1: Per-row confidence dimming in both card components</name>
  <files>frontend/src/components/insights/OpeningFindingCard.tsx, frontend/src/components/stats/OpeningStatsCard.tsx, frontend/src/lib/theme.ts</files>
  <action>
In `OpeningFindingCard.tsx`:
- Remove the `isUnreliable` computation (the `finding.n_games < MIN_GAMES_FOR_RELIABLE_STATS || finding.confidence === 'low'` block and its D-11 comment) and drop the `...(isUnreliable ? { opacity: UNRELIABLE_OPACITY } : {})` spread from `rootStyle`. `rootStyle` keeps only `{ borderLeftColor }`. Keep `MIN_GAMES_FOR_RELIABLE_STATS` in the imports ONLY if it is still referenced elsewhere in the file after this removal; grep the file — if it is no longer used, remove it from the theme import to keep knip clean.
- Add two row-dim flags near the existing `showScoreZoneFont` / `showEvalZoneFont` computations: `const dimScoreRow = !isConfident(finding.confidence);` and `const dimEvalRow = hasMgEval && !isConfident(finding.eval_confidence);`. (Eval dimming only applies when there is an eval value; the `EvalCpuPlaceholder` branch and the `—` no-eval case are not dimmed.)
- In `scoreEvalBlock`, apply `style={dimScoreRow ? { opacity: UNRELIABLE_OPACITY } : undefined}` to BOTH the score-bullet `<div>` (`data-testid={`${cardTestId}-score-bullet`}`) and the score-text `<span>` (`data-testid={`${cardTestId}-score-text`}`). Apply `style={dimEvalRow ? { opacity: UNRELIABLE_OPACITY } : undefined}` to BOTH the eval-bullet `<div>` (`data-testid={`${cardTestId}-bullet`}`) and the eval-text `<span>` (`data-testid={`${cardTestId}-eval-text`}`) inside the `tier2` branch.

In `OpeningStatsCard.tsx`:
- Remove the `isCardMuted` computation (the `opening.total < MIN_GAMES_OPENING_ROW` line and its comment) and drop the `...(isCardMuted ? { opacity: UNRELIABLE_OPACITY } : {})` spread from `rootStyle`. `rootStyle` keeps only the existing conditional `borderLeftColor` spread.
- Remove `MIN_GAMES_OPENING_ROW` from the `@/lib/theme` import.
- Add `const dimScoreRow = !isConfident(scoreStats.confidence);` and `const dimEvalRow = hasMgEval && !isConfident(opening.eval_confidence);` near `showScoreZoneFont` / `showEvalZoneFont`.
- Apply the same per-cell opacity style to the four cells exactly as in OpeningFindingCard (score-bullet div + score-text span -> dimScoreRow; eval-bullet div + eval-text span inside the `tier2` branch -> dimEvalRow).

In `theme.ts`:
- Remove the now-dead `export const MIN_GAMES_OPENING_ROW = 20;` and its preceding comment block (lines ~86-90). Leave `UNRELIABLE_OPACITY` and `MIN_GAMES_FOR_RELIABLE_STATS` intact.

Do NOT touch: the border / left-spine logic, the on-board arrow, `showScoreZoneFont` / `showEvalZoneFont` font-color gating, or the `EvalCpuPlaceholder` branch. The dim style is independent of and composes with the existing font-color style on the inner value spans (different elements, no conflict). Mobile parity is automatic because `scoreEvalBlock` is the single shared const — confirm you only edit it once per file.
  </action>
  <verify>
    <automated>cd frontend && npm run lint && npx tsc --noEmit && npm run knip</automated>
  </verify>
  <done>Both cards dim only the low-confidence row's two cells (bullet + text + popover, since the popover sits inside the text span); neither card root carries opacity; `MIN_GAMES_OPENING_ROW` is gone from theme.ts and unreferenced; lint, typecheck, and knip pass.</done>
</task>

<task type="auto">
  <name>Task 2: Update Insights tooltip copy and rewrite affected tests</name>
  <files>frontend/src/components/insights/OpeningInsightsBlock.tsx, frontend/src/components/insights/OpeningFindingCard.test.tsx, frontend/src/components/stats/__tests__/OpeningStatsCard.test.tsx</files>
  <action>
COPY UPDATE (`OpeningInsightsBlock.tsx`, the InfoPopover `<p>` at ~line 232-236):
Replace the existing sentence about whole-card dimming. Use this exact replacement for the first paragraph (keep the surrounding 16-half-move and Stockfish paragraph, and the italic Tip paragraph, unchanged):

  "A strength or weakness shows up when your score is below 45% or above 55% over at least 20 games. The Score or Eval value is dimmed individually when that stat isn't statistically distinguishable from chance, or rests on too few games. The more games you have, the higher the statistical confidence in the findings."

No em-dashes (project style). Terse, user-facing.

TEST REWRITE — `OpeningFindingCard.test.tsx` (the `UNRELIABLE_OPACITY` block, ~lines 372-391):
Replace the three whole-card-root opacity tests with per-row tests. The dual mobile+desktop layout duplicates testids, so use `screen.getAllByTestId(...)` and assert on the first match (or assert all match). New tests:
- "dims the Score row cells when finding.confidence === 'low'": `makeFinding({ confidence: 'low', n_games: 100, eval_confidence: 'high', eval_n: 18, avg_eval_pawns: 0.5 })`. Assert both `getAllByTestId('opening-finding-card-0-score-bullet')[0]` and `...-score-text'[0]` have `style.opacity` === `String(UNRELIABLE_OPACITY)`; assert the eval cells (`-bullet`, `-eval-text`) do NOT; assert the card root (`opening-finding-card-0`) has empty `style.opacity`.
- "dims the Eval row cells when finding.eval_confidence === 'low'": `makeFinding({ confidence: 'high', eval_confidence: 'low', eval_n: 18, avg_eval_pawns: 0.5 })`. Assert eval cells dimmed, score cells NOT, root NOT.
- "does NOT dim either row when both confidences are high": `makeFinding({ confidence: 'high', eval_confidence: 'high', eval_n: 18, avg_eval_pawns: 0.5 })`. Assert none of the four cells nor the root carry opacity 0.5.
Note: `makeFinding` defaults `confidence: 'medium'` and `eval_confidence: 'medium'`, both of which `isConfident()` treats as confident (not dimmed) — only `'low'` dims. Confirm `isConfident` semantics by reading `@/lib/significance` if unsure before writing assertions.

TEST REWRITE — `OpeningStatsCard.test.tsx` (the "low-data muting" describe block, ~lines 192-211):
Replace the two whole-card-root tests. The Stats card derives score confidence via `computeScoreConfidence(wins, draws, total)`, NOT a literal field, so drive the score-row dim by choosing W/D/total that yield a 'low' vs confident bucket (mirror the existing border tests which already pick such values, e.g. the sparse `total < MIN_GAMES_FOR_RELIABLE_STATS` opening yields low confidence; a `total: 50` even-record opening with a clear score yields confident). The eval-row dim is driven by the literal `eval_confidence` field (default `'low'` in `makeOpening`). New tests:
- "dims the Score row cells when score confidence is low": use a sparse opening (e.g. `makeOpening({ wins: 3, draws: 2, losses: 4, total: 9 })`) so `computeScoreConfidence` returns low. Assert score-bullet + score-text cells dimmed; assert card root opacity is `''`.
- "does NOT dim the Score row when score confidence is high": use a confident opening (large total, lopsided record, e.g. `makeOpening({ wins: 40, draws: 5, losses: 5, total: 50 })`). Assert score cells not dimmed, root not dimmed.
- "dims the Eval row cells when opening.eval_confidence is 'low'": `makeOpening({ eval_n: 18, avg_eval_pawns: 0.5, eval_confidence: 'low', wins: 40, draws: 5, losses: 5, total: 50 })` (high score confidence to isolate the eval dim). Assert eval-bullet + eval-text cells dimmed, score cells NOT, root NOT.
Keep the `eval_n`/`avg_eval_pawns` set so the eval row actually renders (tier2 is mocked on by `renderCard` / `useReadiness`; confirm by reading the existing eval tests in the file, which already render the eval row). Remove the now-unused `UNRELIABLE_OPACITY` import only if no remaining test references it — it IS still referenced by the new tests, so keep it.

After edits, ensure no test still references `MIN_GAMES_OPENING_ROW` (it is removed from theme.ts). Grep both test files and the rest of `src/` to confirm zero remaining references before finishing.
  </action>
  <verify>
    <automated>cd frontend && npm test -- --run src/components/insights/OpeningFindingCard.test.tsx src/components/stats/__tests__/OpeningStatsCard.test.tsx src/components/insights/OpeningInsightsBlock</automated>
  </verify>
  <done>Tooltip copy describes per-row/per-stat dimming with no em-dashes; both rewritten test files pass; no remaining references to `MIN_GAMES_OPENING_ROW` anywhere in `src/`.</done>
</task>

</tasks>

<verification>
Run the full affected-frontend gate before declaring done:

```bash
cd frontend && npm run lint && npm run knip && npm test -- --run \
  src/components/insights/OpeningFindingCard.test.tsx \
  src/components/stats/__tests__/OpeningStatsCard.test.tsx \
  src/components/insights/OpeningInsightsBlock
```

`npm run knip` is mandatory here because `MIN_GAMES_OPENING_ROW` was removed — knip confirms no dead export remains and no import dangles. Typecheck via `npx tsc --noEmit` (or `npm run build` if that's the project's TS gate) should also be clean.

(The full integration gate — backend + complete frontend suite per CLAUDE.md — is the orchestrator's responsibility at squash-merge time, not this executor's.)
</verification>

<success_criteria>
- Insights card: Score row dims iff `finding.confidence === 'low'`; Eval row dims iff `finding.eval_confidence === 'low'` and an eval value exists; whole-card opacity dim removed.
- Stats card: Score row dims iff `computeScoreConfidence(...)` bucket is low; Eval row dims iff `opening.eval_confidence === 'low'` and an eval value exists; `isCardMuted` / `<20`-games whole-card dim removed.
- `MIN_GAMES_OPENING_ROW` removed from `theme.ts` and unreferenced project-wide.
- Border / left-spine accent, on-board arrow, and font-color zone gating unchanged in both cards.
- Insights `FindingsSection` info-popover copy describes per-row dimming, no em-dashes.
- Both card edits touch only the single shared `scoreEvalBlock` const (mobile + desktop covered once).
- lint, knip, typecheck, and the three affected test files all pass.
</success_criteria>

<output>
Create `.planning/quick/260603-pgv-in-the-openings-stats-and-insights-table/260603-pgv-SUMMARY.md` when done.
</output>
