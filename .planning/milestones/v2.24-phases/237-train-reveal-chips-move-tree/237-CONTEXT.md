# Phase 237: Train Reveal Verdict Strip, Line Chips & One Move Tree - Context

**Gathered:** 2026-10-08
**Status:** Ready for planning

<domain>
## Phase Boundary

Rework the post-solve Train reveal so it fits a 390x844 phone without scrolling and teaches through
one model instead of two (line cards + a separate free-play mode). Delivers the sketch 008 "Combined"
design (SEED-194): verdict strip, You/Best/Game line chips with chip-driven board arrows, one
pre-loaded move tree with in-place sideline forks, a phone action bar for the whole reveal, the
desktop layout, and a rewritten first-reveal tour. Frontend, plus one small backend schema change for
telemetry v2 (D-12). The seven ROADMAP items and guardrails are locked and not re-opened here; this
file records the decisions that resolve their ambiguities.

</domain>

<decisions>
## Implementation Decisions

### Locked upstream (ROADMAP Phase 237 + SEED-194 + sketch 008; do not re-open)
- Strip replaces the bot bubble after the reveal (phone); the Your-call card goes. Desktop keeps the
  full verdict bubble (no strip).
- Chips You / Best / Game (mark, SAN, eval) replace the line cards; the reveal opens with **You**
  active; only the active chip's arrow + mark are opaque, every other arrow/mark (also-fine included)
  fades to ~20-30%, never hidden; a played move from the puzzle position that matches a line activates
  that chip.
- One `useAnalysisBoard` tree with the three lines pre-loaded; moving a piece forks a sideline in place
  (× closes it); no free-play mode, no card swap; a one-line Stockfish row (expandable to PV 2) only off
  the known lines; `useTrainFreePlay`'s per-move grading markers stay on sideline moves.
- Phone action bar ⏮ ‹ › ⇅ + Analyze + Next for the whole reveal (⏮ = old Solution, keeps sidelines);
  first view fits 390x844 with no scroll. Desktop: ← → step, Home = puzzle position.
- Guardrails: SOLV-02 (a fork never reaches grading), herring / server-graded verdicts and Phase 211
  D-06 "Also fine" marks preserved, restored-reveal path (`CachedTrainReveal`, Analyze → Back) restores
  active chip + tree, test ids / reveal tests move off the card structure, `TrainReveal.tsx` is split.

### Tree & chip navigation
- **D-01:** Tapping a chip while the board is anywhere other than that chip's line jumps the board to
  the **puzzle position** (root) with the tapped chip's arrow lit, and the list switches to that line.
  Matches the sketch (`case 'chip'` → `goto(0)`). Arrows only exist at the root, so this is the one
  place a chip's meaning is visible.
- **D-02:** Chips group by distinct first move: **any** coinciding roles merge into one chip and one
  arrow, labelled with the roles joined ("You = Best", "You = Game"). Owner fact: the Game move is
  always the flaw (a blunder), never the best move, so **Best = Game and You = Best = Game cannot
  occur**; in practice only You = Best and You = Game happen. Implement the generic rule (today's
  `buildLineBoxes` grouping already does this) but do not design copy, tests or tour text around the
  impossible merges.
- **D-03:** Pre-loaded lines keep the existing 12-ply cap (`MAX_LINE_PLIES`). The user can fork past
  the end; the Stockfish row takes over off the known lines.
- **D-04:** A move from the puzzle position that matches none of the lines **deselects all chips**:
  no chip is active, every root arrow fades, and the list shows only the user's line. Tapping a chip or
  ⏮ returns to the root as usual (D-01).

### Verdict strip
- **D-05:** The strip's one line is the D-23 verdict clause without the `[+n]` brackets (the points pill
  carries the total), with the move half split into four words: **best move** (You = Best), **good
  move** (tier good, not the best), **decent move** (inaccuracy), **wrong move** (mistake/blunder).
  E.g. "Right call, best move" / "Wrong call, but a good move" / "Right call, wrong move". Points per
  tier are unchanged (scoring is untouched).
- **D-06:** That vocabulary applies **everywhere** the clause appears: the collapsed strip, the
  expanded verdict and the desktop bubble. `verdictClause` / `verdictClauseParts` in
  `lib/trainBotCopy.ts` change, so the verdict needs to know whether the played move equals the best
  move (not just the tier). Keep `scorePuzzle` as the only points source (D-23 Option B).
- **D-07:** Tapping the strip expands, in this order: the full bot verdict (opener, clause with its
  points chips, look-closer, return tail), the Your-call feedback (call label + points, guess prose,
  motif), and the "Also fine, e.g. …" list. This is everything the bubble and the Your-call card show
  today; nothing is dropped. No Analyze button in the expansion (the bar carries it).
- **D-08:** The strip always starts **collapsed**, on every reveal, regardless of score.

### Tour rewrite
- **D-09:** The new first-reveal tour keeps **6 steps**, each within `STEPPER_COPY_MAX_CHARS` (145):
  1. strip: your result, tap it for the full feedback (target: strip);
  2. chips: tap a line to focus it, the other arrows fade; mention "You = Best"/"You = Game" only when a
     merged chip is on screen (target: chips);
  3. stepping: ‹ › in the bar or tap a move in the list to step the line (target: move list / bar);
  4. board: move a piece to try your own idea; ⏮ goes back to the puzzle position (target: board);
  5. D-21 "understand why, don't just memorize" (target: chips + list);
  6. action bar: Analyze (only when `hasAnalyze`) + Next (target: the bottom action bar).
  "Only describe what is on screen" still holds; `hasSolution` goes away.
- **D-10:** During the tour the stepper bubble (reuse `TrainBotStepper`) renders **stacked above the
  strip**, so step 1 can spotlight the real strip. The tour bubble disappears when the tour ends. The
  phone view may scroll during the tour only; the no-scroll acceptance applies to the reveal outside the
  tour.
- **D-11:** Claude drafts all copy. Browser UAT of the tour runs at 390x844, 375x667 and desktop, done
  by the agent (memory `feedback_run_device_uat_yourself`); only the real-phone tap leg is deferred to
  the owner.

### Telemetry
- **D-12:** Bump `ReviewTelemetry` to **`v: 2`** (backend `Literal[1, 2]` or equivalent, the frontend
  `TELEMETRY_SCHEMA_VERSION`, and the parity test `tests/schemas/test_train_telemetry_parity.py`).
  Keep the keys whose meaning carries over: `review_ms`, `review_hidden_ms`, `exit`,
  `review_line_steps` (now: steps through the tree via ‹ › or list taps), `review_explore_moves`,
  `review_board_moves`, `review_analyze_opened`. Replace `review_cards_opened` / `review_cards_total`
  with a chips pair (distinct chips selected beyond the default You / chips shown) and add a strip
  expanded flag. v1 rows stay valid; old bundles keep sending v1. The `SolveTelemetry` patch is
  unaffected.
  — **Reversibility:** costly — a published request schema version; once v2 rows are written the
  column carries two shapes and every analysis query has to branch on `v`.
- **D-13:** A hand-played move that matches a known line (no sideline created) counts as a **board
  move, not a fork**: `review_explore_moves` stays "every user-played move" (board + Stockfish-row
  clicks) and `review_board_moves` its hand-played subset, as in v1. `review_explored` becomes "forked
  at least one sideline".
- **D-14:** Umami fires only for **low-frequency** actions: strip expand, ⏮ rewind (successor of
  `train-solution`), sideline close × (successor of `train-explore-exit`), and the first fork per
  puzzle. Chip taps and tree steps stay in the ReviewTelemetry counters only.

### Claude's Discretion
- Late-arriving lines as chips (Phase 236 D-14/D-15): how a chip and its branch look while the
  your/best line is still loading or failed, and how the game-move search's line grafts in when it
  resolves (the tree must accept a branch arriving after mount without moving the user's board).
- What the list shows for a root fork after a chip is tapped again (D-04): whether the user's
  root-level sideline stays reachable (e.g. as a sideline before move 1 of the active line) or only via
  stepping. Keep the sideline in the tree either way (⏮ keeps sidelines).
- Which tree convention represents three root-level branches given `useAnalysisBoard`'s single
  `mainLine` (e.g. active line = mainLine, re-pointed on chip change, or a new multi-root API).
- Free-play engine lifetime and contention: the engine now has a reason to exist for the whole reveal
  (Stockfish row off-line, sideline grading); research must check contention with the grading Worker
  and the Phase 236 background search / serialization (`onKeyLine` hook), and whether it should start
  only on the first off-line position.
- Umami target names for D-14 (`ACTION_TARGETS` in `lib/analytics.ts`), and whether the retired
  `train-solution` / `train-explore-exit` targets are renamed or kept as aliases.
- Exact v2 key names, the eval bar's behaviour off the known lines, desktop keyboard details beyond ←
  → Home, and how `TrainReveal.tsx` / `TrainSolveScreen.tsx` are split (seams: strip, chips, tree
  list, action bar, a `useTrainRevealTree`-style data hook).
- Whether `TrainLineStepper.tsx` is retired (likely) and how `buildTrainStepArrows/Markers` give way
  to per-chip opacity in `lib/trainArrows.ts`.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Design direction (locked)
- `.planning/seeds/SEED-194-train-reveal-chips-and-move-tree.md`: problem measurements, proposed
  direction, where it lands, watch-outs (onboarding plumbing, telemetry, test ids, SOLV-02, restored
  reveal)
- `.planning/sketches/008-train-reveal-mobile-layout/index.html`: the owner-approved sketch; tab
  "★ Combined · phone" and "★ Combined · desktop" (chip grouping `chipGroups()`, arrow dimming
  `arrowsSvg()`, chip tap `case 'chip'`, strip `stripHtml()`, desktop `deskHtml()`)
- `.planning/sketches/008-train-reveal-mobile-layout/README.md`: variants and round-2 owner feedback
- `.planning/sketches/MANIFEST.md` §008: recorded decisions
- `.planning/ROADMAP.md` § Phase 237: the seven scoped items and guardrails

### Prior phase decisions that constrain this one
- `.planning/phases/236-train-phone-grade-instant-verdict/236-CONTEXT.md`: D-14/D-15/D-16 (reveal
  shows before the background search finishes; loading/failed line states; display numbers unchanged)
- Phase 233 telemetry (ReviewTelemetry D-03/D-05/D-11/D-12/D-14): `app/schemas/train.py`
  `ReviewTelemetry`, `frontend/src/lib/trainTelemetry.ts`,
  `tests/schemas/test_train_telemetry_parity.py`
- Phase 222 D-21/D-24 (walkthrough, copy budget, "only describe what is on screen") and Phase 233
  D-13 (sticky walkthrough flag): see `frontend/src/lib/trainBotCopy.ts` `walkthroughCopy` and
  `frontend/src/hooks/useTrainOnboarding.ts`
- Phase 211 D-06 (vetted "Also fine" marks never re-derived): `frontend/src/hooks/useTrainFreePlay.ts`
  header comment
- D-23 verdict copy: `frontend/src/lib/trainBotCopy.ts` `verdictClause` / `verdictCopy`

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `frontend/src/hooks/useAnalysisBoard.ts`: branching tree (`insertPvLine`, `playUciLine`,
  `deleteSubtree`, `clearAllSidelines`, `goToRoot`, `goToNode`); single `mainLine` is the constraint
  for three root branches.
- `frontend/src/hooks/useTrainFreePlay.ts`: per-move grading on the tree, per-FEN eval cache, D-06
  vetted-move badges; today starts an empty tree on the first free move and creates its engine only
  while `isExploring`.
- `frontend/src/components/analysis/VariationTree.tsx`: numbered, wrapping move list with sidelines
  and ×; candidate for the tree list (or its rendering helpers).
- `frontend/src/components/train/TrainBotStepper.tsx`: walkthrough bubble, reused for D-10.
- `frontend/src/lib/mobileBoardControls.ts` (`usePublishMobileBoardControls`): today swaps the bottom
  nav for board controls only in free play; becomes the whole-reveal action bar.
- `frontend/src/components/train/TrainReveal.tsx` `buildLineBoxes`: already groups coinciding roles
  (D-02) and carries Phase 236 `pending: 'loading' | 'failed'`.

### Established Patterns
- `CardEngageKind` + `REVIEW_CARD_HOVER_MIN_MS` drive Phase 233 card engagement; replaced by the chips
  pair in v2 (D-12).
- Telemetry constants are mirrored backend↔frontend and CI-locked by the parity test (plain integer
  literals).
- Arrow/marker composition lives in `frontend/src/lib/trainArrows.ts` (spotlight today, per-chip
  opacity after).

### Integration Points
- `frontend/src/components/train/TrainSolveScreen.tsx`: `handlePieceDrop` free-play branch (SOLV-02
  comment block), `lineStep`, `isBoardDeparted`, `verdictActions` row, walkthrough bubble body, mobile
  board controls.
- `frontend/src/lib/trainRevealCache.ts` + `frontend/src/pages/Train.tsx`: `CachedTrainReveal`
  must carry the active chip and tree.
- Tests to move: `components/train/__tests__/TrainReveal.test.tsx`, `TrainSolveScreen.test.tsx`,
  `TrainSolveScreen.restoredGameArrow.test.tsx`, `TrainLineStepper.test.tsx`,
  `pages/__tests__/Train.solveLoop.test.tsx`, `lib/__tests__/trainRevealCache.test.ts`.

</code_context>

<specifics>
## Specific Ideas

- Strip wording examples: "Right call, best move", "Right call, good move", "Right call, decent move",
  "Right call, wrong move", "Wrong call, but a good move".
- Merged chip labels: "You = Best", "You = Game".
- Baseline screenshots for before/after comparison: `temp/puzzle-reveal-ux/` (2026-10-08).

</specifics>

<deferred>
## Deferred Ideas

None. The discussion stayed within phase scope.

</deferred>

---

*Phase: 237-train-reveal-chips-move-tree*
*Context gathered: 2026-10-08*
