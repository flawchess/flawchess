---
phase: quick-260529-une
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - frontend/src/components/charts/EndgameTypeCard.tsx
  - frontend/src/components/charts/__tests__/EndgameTypeCard.test.tsx
  - frontend/src/components/charts/__tests__/EndgameTypeBreakdownSection.test.tsx
  - frontend/src/pages/__tests__/Endgames.overallPerformance.test.tsx
  - frontend/src/pages/Endgames.tsx
autonomous: true
requirements: [QUICK-260529-une]
must_haves:
  truths:
    - "Each EndgameTypeCard renders WDL bar + Games link, Score bullet, and Score Gap bullet — and NO Conversion/Recovery gauges."
    - "The empty-state (total === 0) card shows the title row and 'Not enough data yet' text with no gauge block."
    - "frontend gates pass: npm run lint && npm run knip && npm test -- --run."
    - "No backend file is modified; category.conversion.* stays on the /stats wire and in test fixtures."
  artifacts:
    - path: "frontend/src/components/charts/EndgameTypeCard.tsx"
      provides: "Gauge-free type card (WDL + Score + Score Gap only)"
      contains: "ScoreGapRow"
  key_links:
    - from: "frontend/src/components/charts/EndgameTypeCard.tsx"
      to: "@/lib/theme"
      via: "ZONE_SUCCESS / ZONE_DANGER import (gapColor still uses them)"
      pattern: "ZONE_(SUCCESS|DANGER)"
---

<objective>
Declutter the Endgame Type Breakdown cards by removing the two Conversion/Recovery
`EndgameGauge`s from each `EndgameTypeCard` (both the live-render row and the
empty-state shell). Keep one card per endgame type (no TC split). Everything else
on the card stays: WDL bar + Games link, Score bullet row, Score Gap bullet row.

Purpose: The Conv/Recov gauges overload the section and mispaint by time control
(a bullet player judged against slow-TC bands). Removing them declutters and kills
the mispaint by removal. Authoritative scope + rationale:
`.planning/notes/endgame-type-card-drop-gauges.md`.

Output: A gauge-free `EndgameTypeCard`, updated frontend tests, a trimmed page-level
breakdown InfoPopover, with all three frontend gates green.
</objective>

<frontend_only_guardrail>
THIS IS A FRONTEND-ONLY CHANGE. DO NOT TOUCH ANY BACKEND CODE OR THE CODEGEN.

The backend per-type conv/recov is NOT dead — it feeds the LLM insights narration:
- `app/services/insights_service.py` (`_findings_conversion_recovery_by_type`, ~line 1017)
  consumes `cat.conversion.conversion_pct` / `recovery_pct` / `recovery_games`.
- The per-class bands in `app/services/endgame_zones.py` feed that same pipeline.

Therefore you MUST NOT:
- Remove or alter the `ConversionRecoveryStats` schema, the endgame_service computation,
  or any backend Python.
- Edit `scripts/gen_endgame_zones_ts.py` or the Python zone registry.
- Hand-edit the AUTO-GENERATED `frontend/src/generated/endgameZones.ts`
  (the `PER_CLASS_GAUGE_ZONES` export stays in that file; it just stops being imported).
- Strip `category.conversion.*` from the `/stats` wire or from frontend types — insights
  needs the same response shape. Test fixtures MAY keep `conversion`/`recovery` data
  (still on the type, harmless).
- Run any backend gate (ruff/ty/pytest) or `bin/reset_db.sh`.

Knip note (pre-verified): `frontend/src/generated/endgameZones.ts` is ALREADY in the knip
`ignore` list (`frontend/knip.json` line 19). So `PER_CLASS_GAUGE_ZONES` going
frontend-dead will NOT trip knip and NO knip-config edit is required. Just confirm
`npm run knip` passes — do not add a redundant ignore entry.
`colorizeGaugeZones` STAYS exported from `@/lib/theme` (still used by
`EndgameMetricsByTcCard.tsx` and `endgameMetrics.ts`) — only its import in
`EndgameTypeCard.tsx` is removed.
</frontend_only_guardrail>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/notes/endgame-type-card-drop-gauges.md
@frontend/src/components/charts/EndgameTypeCard.tsx
@frontend/knip.json
</context>

<tasks>

<task type="auto">
  <name>Task 1: Remove the Conv/Recov gauges from EndgameTypeCard</name>
  <files>frontend/src/components/charts/EndgameTypeCard.tsx</files>
  <action>
Remove the two Conversion/Recovery gauges from the card, in both render paths, and
clean up all now-unused symbols. Specifics:

1. Live-render gauge row: delete the `grid grid-cols-2` block keyed
   `data-testid={`${tileTestId}-gauges`}` containing the two `EndgameGauge`s
   (Conversion + Recovery), ~lines 287-317, plus its leading comment block
   ("Gauge row (Conv | Recov side-by-side)..."). The first child of the body
   becomes the WDL/Games block (`SHOW_WDL_BAR_IN_TYPE_CARDS` ternary).

2. Empty-state shell (`!hasGames`, ~lines 192-241): delete the `grid grid-cols-2 ...
   opacity-50` gauge block (the `-gauges`, `-conv-gauge`, `-recov-gauge` divs and
   their `EndgameGauge`s). Keep the `<p className="text-sm text-muted-foreground py-4">
   Not enough data yet</p>` as the only body content inside the
   `flex flex-col gap-4 p-4` wrapper. Update the comment above the `if (!hasGames)`
   block to reflect that there is no gauge row anymore.

3. Delete now-unused locals: the `bands` derivation (~lines 146-149), the
   `const [convLower, convUpper] = bands!.conversion;` /
   `const [recovLower, recovUpper] = bands!.recovery;` pair (~lines 245-246), and the
   `convZones` / `recovZones` `colorizeGaugeZones(...)` derivations (~lines 247-256),
   plus the comment that precedes them ("bands is non-undefined here..."). There are
   no other `bands` usages — verify with grep before deleting.

4. Remove the `PER_TYPE_GAUGE_SIZE` constant (~line 75) and its comment.

5. Remove now-unused imports: `EndgameGauge` (from '@/components/charts/EndgameGauge'),
   `PER_CLASS_GAUGE_ZONES` (from '@/generated/endgameZones' — keep
   `ENDGAME_TYPE_SCORE_GAP_NEUTRAL_MAX` and `ENDGAME_TYPE_SCORE_GAP_NEUTRAL_MIN`,
   still used by the Score Gap row), and `colorizeGaugeZones` (from '@/lib/theme').

KEEP everything else exactly: WDL bar + Games link block, the Score bullet row
(`-score-row`), the Score Gap row (`ScoreGapRow` / `-asg-bullet`), `ZONE_SUCCESS`
and `ZONE_DANGER` (gapColor still uses them), `ZONE_NEUTRAL`,
`MIN_GAMES_FOR_RELIABLE_STATS`, `UNRELIABLE_OPACITY`, `useEvalCoverage`,
`ENDGAME_TYPE_DESCRIPTIONS`, the title InfoPopover, the `typeDescription`
derivation, the `n=total` chip, and all start/end predicted-score slots.

Do not add a TC split, do not introduce new props, and do not touch any backend file.
After editing, the only `@/lib/theme` symbols imported should be those still
referenced (ZONE_DANGER, ZONE_NEUTRAL, ZONE_SUCCESS, MIN_GAMES_FOR_RELIABLE_STATS,
UNRELIABLE_OPACITY) — confirm by grep that no removed symbol is still referenced.
  </action>
  <verify>
    <automated>cd frontend && grep -nE "EndgameGauge|PER_CLASS_GAUGE_ZONES|colorizeGaugeZones|PER_TYPE_GAUGE_SIZE|convZones|recovZones|convLower|recovLower|\bbands\b" src/components/charts/EndgameTypeCard.tsx; test -z "$(grep -nE 'EndgameGauge|PER_CLASS_GAUGE_ZONES|colorizeGaugeZones|PER_TYPE_GAUGE_SIZE|convZones|recovZones|\bbands\b' src/components/charts/EndgameTypeCard.tsx)" && npx tsc --noEmit -p tsconfig.json</automated>
  </verify>
  <done>
`EndgameTypeCard.tsx` contains no `EndgameGauge`, `PER_CLASS_GAUGE_ZONES`,
`colorizeGaugeZones`, `PER_TYPE_GAUGE_SIZE`, `convZones`, `recovZones`, or `bands`
references. The component still renders WDL/Games, Score bullet, and Score Gap rows,
and TypeScript compiles with zero errors.
  </done>
</task>

<task type="auto">
  <name>Task 2: Drop gauge assertions from the 3 frontend tests and trim the breakdown InfoPopover</name>
  <files>frontend/src/components/charts/__tests__/EndgameTypeCard.test.tsx, frontend/src/components/charts/__tests__/EndgameTypeBreakdownSection.test.tsx, frontend/src/pages/__tests__/Endgames.overallPerformance.test.tsx, frontend/src/pages/Endgames.tsx</files>
  <action>
Update tests to match the gauge-free card, and trim the page-level breakdown popover.

EndgameTypeCard.test.tsx:
- In the "Layout" test (~lines 148-160), remove the two gauge assertions
  (`${TILE_TESTID}-conv-gauge`, `${TILE_TESTID}-recov-gauge`) and rename the test
  title from "renders gauges, WDL bar, and Score bullet" to "renders WDL bar and
  Score bullet". Keep the WDL / score-row / score-value / score-bullet / score-info /
  games-link / title-info assertions.
- In the "renders empty-class shell when total === 0" test (~lines 191-231), remove
  the `${TILE_TESTID}-gauges` lookup and the `opacity-50` className assertion
  (~lines 222-223). Keep the `Not enough data yet` text assertion and all the
  `queryByTestId(...).toBeNull()` assertions (wdl, score-row, score-bullet,
  games-link, asg-bullet). The fixture's `conversion: {...}` object may stay (harmless).
- In the "shows n=total chip ..." test (~lines 233-257), drop "Gauges + WDL still
  render" from the comment and remove any gauge testid lookup if present (keep the
  `-wdl` assertion).
- In the "positions the ScoreGapRow as the last row" test (~lines 333-355): this test
  anchors DOM ordering on `${TILE_TESTID}-gauges` as the first child. Re-anchor it on
  the WDL block instead — replace `const gauges = screen.getByTestId(`${TILE_TESTID}-gauges`)`
  with the WDL element (`screen.getByTestId(`${TILE_TESTID}-wdl`)`), rename the local,
  and update the index comparisons so the WDL block is the first body child and the
  asg row is last. Keep the intent (Score Gap row is the last row in the card).

EndgameTypeBreakdownSection.test.tsx:
- Only a comment references `conv-gauge` (~line 151, inside the `TOP_LEVEL_CARD_RE`
  explanation). Update that comment so it no longer cites a `-conv-gauge` sub-element
  (use a surviving sub-element like `-score-bullet` as the example). No assertion
  changes needed here.

Endgames.overallPerformance.test.tsx:
- The `conversion_pct` / `recovery_pct` in the fixture (~lines 231-236) are fixture
  data only — leave them. The `Recovery:` references at lines 344-365 belong to the
  page-level concepts accordion (ordering of "Endgame Entry Eval" / "Endgame Score"
  paragraphs after a separate "Recovery:" paragraph in the concepts accordion), NOT to
  the type-card gauges. DO NOT change those tests. No edits to this file are expected;
  if a grep shows no `*-gauge` / `*-gauges` testid assertions here (it should), leave
  the file untouched and note it in the SUMMARY.

Endgames.tsx — page-level "Endgame Type Breakdown" h2 InfoPopover (~lines 631-647):
- The popover has two `<p>` blocks. Keep the first (taxonomy: "how you perform across
  the different kinds of endgames (rook, minor piece, pawn, queen, mixed)"). From the
  second `<p>` (~lines 641-645), remove the Conversion and Recovery clause so the card
  description no longer defines metrics the card no longer shows. Keep a short sentence
  stating each card shows your win/draw/loss rate for that type (the WDL bar). Do NOT
  touch the page-level concepts accordion (~lines 382-525) which still legitimately
  defines Conversion/Recovery for the insights narration and other surfaces.
- Keep all existing `data-testid`s; obey the text-sm floor (this is a tooltip surface
  but you are only removing text, not adding sub-text-sm copy).
  </action>
  <verify>
    <automated>cd frontend && grep -nE "conv-gauge|recov-gauge|-gauges" src/components/charts/__tests__/EndgameTypeCard.test.tsx src/components/charts/__tests__/EndgameTypeBreakdownSection.test.tsx src/pages/__tests__/Endgames.overallPerformance.test.tsx; test -z "$(grep -hoE '(conv-gauge|recov-gauge|-gauges)' src/components/charts/__tests__/EndgameTypeCard.test.tsx src/pages/__tests__/Endgames.overallPerformance.test.tsx)"</automated>
  </verify>
  <done>
No `*-conv-gauge` / `*-recov-gauge` / `*-gauges` testid assertions remain in the
EndgameTypeCard or Endgames.overallPerformance tests; the section test comment no
longer cites a gauge sub-element; the breakdown h2 InfoPopover no longer defines
Conversion/Recovery; the concepts accordion in Endgames.tsx is untouched.
  </done>
</task>

<task type="auto">
  <name>Task 3: Run and green the frontend pre-PR gates</name>
  <files>frontend/src/components/charts/EndgameTypeCard.tsx, frontend/src/components/charts/__tests__/EndgameTypeCard.test.tsx</files>
  <action>
From `frontend/`, run the three frontend pre-PR gates and resolve any failures:

  npm run lint && npm run knip && npm test -- --run

Expected: lint clean (no unused imports left behind from Task 1), knip clean
(`PER_CLASS_GAUGE_ZONES` is dead but its file is already knip-ignored — if knip
unexpectedly flags `EndgameGauge`, `colorizeGaugeZones`, or anything else, that means a
real consumer was removed by mistake or a stray import remains; fix the code, do NOT add
new knip ignores or touch the generated file), and all frontend tests pass.

If any gate modifies files (e.g. a formatter), the fix belongs in the frontend source
or test files listed above. Do NOT run backend gates (ruff/ty/pytest) — no backend
changed. Do NOT run `bin/reset_db.sh`.
  </action>
  <verify>
    <automated>cd frontend && npm run lint && npm run knip && npm test -- --run</automated>
  </verify>
  <done>
`npm run lint`, `npm run knip`, and `npm test -- --run` all pass from `frontend/` with
no backend files modified.
  </done>
</task>

</tasks>

<verification>
- `EndgameTypeCard.tsx` renders no Conversion/Recovery gauge in either render path.
- WDL bar + Games link, Score bullet, and Score Gap bullet still render.
- `npm run lint && npm run knip && npm test -- --run` all green from `frontend/`.
- `git status` shows changes only under `frontend/` — zero backend (`app/`,
  `scripts/`) or generated-file (`frontend/src/generated/endgameZones.ts`) edits.
</verification>

<success_criteria>
- Gauges removed from both the live and empty-state card renders.
- Three frontend test files updated (or confirmed untouched where appropriate) and passing.
- Breakdown h2 InfoPopover no longer defines Conversion/Recovery; concepts accordion intact.
- All three frontend gates pass; no backend/codegen/generated-file changes.
</success_criteria>

<output>
Create `.planning/quick/260529-une-declutter-endgame-type-breakdown-cards-r/260529-une-SUMMARY.md` when done.
</output>
