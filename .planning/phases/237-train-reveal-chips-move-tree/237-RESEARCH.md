# Phase 237: Train Reveal Verdict Strip, Line Chips & One Move Tree - Research

**Researched:** 2026-10-09
**Domain:** React 19 frontend refactor of the Train post-solve reveal (move tree, board overlay, mobile shell, onboarding tour, telemetry) plus one small Pydantic schema bump
**Confidence:** HIGH for codebase facts (every claim below was read in this session), MEDIUM for the recommended designs (they are reasoned from the code, not yet built)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

#### Locked upstream (ROADMAP Phase 237 + SEED-194 + sketch 008; do not re-open)
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

#### Tree & chip navigation
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

#### Verdict strip
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

#### Tour rewrite
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

#### Telemetry
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

### Deferred Ideas (OUT OF SCOPE)
None. The discussion stayed within phase scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

No REQ-IDs are mapped (ROADMAP: TBD). The planner should treat the seven ROADMAP items, the guardrails and D-01..D-14 as the requirement set. Suggested IDs for plan frontmatter, with the research that supports each:

| ID (suggested) | Description | Research Support |
|----|-------------|------------------|
| R1 / D-05..D-08 | Verdict strip replaces the bubble on phone; Your-call card removed | §Pattern 5 (shared `TrainVerdictDetails`), §Pitfall 12 (`verdictClauseParts` lives in TrainSolveScreen.tsx, not trainBotCopy) |
| R2 / D-02 | Line chips You/Best/Game with merge | §Pattern 2 (`buildChipGroups` from `buildLineBoxes`), §Code Examples |
| R3 / D-01, D-04 | Chip-driven board, dim not hide | §Pattern 3 (`rootFocus` + derived active chip), §Pattern 4 (opacity on `BoardArrow`/`SquareMarker`) |
| R4 / D-03, D-13 | One move tree, in-place forks, Stockfish row off-line, grading markers on sidelines | §Pattern 1 (`useTrainRevealTree` + non-navigating `graftLine`), §Pattern 6 (one reveal engine) |
| R5 | Phone action bar for the whole reveal, 390x844 no scroll | §Pattern 7 (payload extension + in-flow bar for `sm..lg`), §Pitfall 6 |
| R6 | Desktop layout, ← → Home | §Pattern 7, §Pattern 8 (keyboard) |
| R7 / D-09..D-11 | Tour rewrite | §Pattern 9, §Open Question 1 (existing users never see the new tour) |
| G-SOLV02 | Forks never reach grading | §Pitfall 9, test map |
| G-MARKS | Herring / server-graded / D-06 "Also fine" marks preserved | §Pattern 4, §Pitfall 10 |
| G-RESTORE | Analyze → Back restores chip + tree | §Pattern 10 (persist UCI paths, not node ids) |
| G-TELEM / D-12..D-14 | Review telemetry v2 + Umami successors | §Pattern 11, §Pitfall 4 |
| G-TESTS | Test ids / tests move off card structure | §Validation Architecture, Wave 0 |
</phase_requirements>

## Summary

The reveal today is two models glued onto one board. `TrainReveal.tsx` (now **1576 lines**, not the 1469 the seed measured) renders up to three line cards, each with its own `TrainLineStepper`, plus the Your-call card; a piece drop after the verdict calls `freePlay.start(...)`, which flips `isExploring` and swaps the cards for a Stockfish card plus `VariationTree` [VERIFIED: frontend/src/components/train/TrainReveal.tsx:1473-1500, TrainSolveScreen.tsx:1369-1390]. Board arrows come from three different sources depending on mode (`spotlitOverlay` / `buildTrainStepArrows` / `freePlayArrows`, TrainSolveScreen.tsx:1609-1613). Everything this phase needs already exists as parts: a branching tree with fork-or-advance semantics (`useAnalysisBoard`), per-move grading against a per-FEN eval cache (`useTrainFreePlay`), a wrapping move list with inline sidelines and × (`VariationTree`'s mobile renderer over `HorizontalMoveList`), compact engine rows (`EngineLines compact`), and a cross-tree bottom-bar seam (`usePublishMobileBoardControls`).

The one real gap in the tree API: **every grafting command moves the board**. `insertPvLine` parks `currentNodeId` at the fork node and refuses a null (root) fork, `playUciLine` lands on the line's end, and `loadMainLine` resets the whole tree [VERIFIED: useAnalysisBoard.ts:490-532, 634-680, 394-454]. Late-arriving lines (Phase 236 key line, played line, game-move search) and the restored-reveal path both need a graft that keeps the user's position. Add one additive command (`graftLine(uciMoves, parentId)`: child-reusing, non-navigating, single `setState`) and derive "which nodes belong to which known line" by walking each line's UCI path through the tree rather than storing roles on nodes. That one choice makes late lines, restored trees, and "a hand-played move that happens to match a line" (D-13) all fall out of the same code.

Three findings change the plan's scope and need owner attention: (1) **existing users will never see the new tour**: it is gated on `train_settings.reveal_walkthrough_seen_at IS NULL`, which every returning user already stamped (Open Question 1); (2) `TELEMETRY_SCHEMA_VERSION` is shared by `SolveTelemetry` and `ReviewTelemetry` on both sides, so "bump to 2" must introduce a separate review constant or it silently bumps the solve patch too (Pitfall 4); (3) the mobile bottom bar is `sm:hidden`, so between 640 px and 1023 px (stacked layout, no bottom bar) the action bar must also render in-flow (Pitfall 6).

**Primary recommendation:** Build a `useTrainRevealTree` hook on top of `useAnalysisBoard` (plus one additive `graftLine` command), make chip focus a pure function of `rootFocus` + the current node's path, drive one reveal-wide Stockfish engine (MultiPV 1 on known lines, 2+ off-line), dim rather than filter the reveal overlay via new optional `opacity` fields, and split `TrainReveal.tsx` along strip / chips / tree list / action bar / footer seams.

## Architectural Responsibility Map

All capabilities are client-side; the only server touch is the telemetry boundary.

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Move tree (3 pre-loaded lines + forks) | Browser (React hook `useTrainRevealTree`) | — | Ephemeral per reveal; `useAnalysisBoard` is already client-only (D-01 there: no URL/session persistence) |
| Chip grouping / focus / arrow dimming | Browser (pure functions in `lib/`) | — | Derived display state; keep pure so it is unit-testable without React |
| Sideline move grading | Browser (reveal Stockfish Worker) | — | Same pipeline as `useTrainFreePlay` today; never touches the server grade (SOLV-02) |
| Verdict, points, vetted "Also fine" moves | API (already in `SolveResponse`) | Browser renders | Server-final since Phases 211/236; the client must never re-derive (`scorePuzzle` only for display totals) |
| Restored reveal (Analyze → Back) | Browser sessionStorage (`train_reveal_cache`) | — | Per-tab navigation aid, already this tier |
| Review telemetry v2 | API (`ReviewTelemetry` Pydantic boundary, JSONB merge) | Browser accumulates | Boundary validation lives server-side (`extra="forbid"`) |
| Umami events | Browser (`trackFeature`) | Umami | Enumerated literals only |
| Bottom action bar | Browser (App shell `MobileBottomBar` via module store) | Page (`TrainSolveScreen` publishes) | Writer and reader live in unrelated subtrees (mobileBoardControls.ts header) |
| Onboarding watermark | API (`train_settings.reveal_walkthrough_seen_at`) | Browser | Stamp via `POST /train/onboarding/{step}` |

## Standard Stack

No new dependencies. Everything is in-repo.

### Core (already installed)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| react | ^19.2.8 | UI | Project stack [VERIFIED: frontend/package.json] |
| chess.js | 1.4.0 | move legality / SAN | `move()` THROWS on illegal input (useAnalysisBoard.ts:413-425 comment, Phase 210) [VERIFIED: node_modules/chess.js/package.json] |
| react-chessboard | 5.12.1 | board; arrows/markers are our own SVG overlay (`ArrowOverlay` in ChessBoard.tsx) | [VERIFIED: node_modules/react-chessboard/package.json] |
| vitest | 5.0.0 | frontend tests | [VERIFIED: node_modules/vitest/package.json] |
| @testing-library/react | ^16.3.2 | component tests (no user-event; tests use `fireEvent`) | [VERIFIED: frontend/package.json] |
| pydantic v2 / pytest | project lock | telemetry boundary + tests | [VERIFIED: app/schemas/train.py, tests/schemas/] |

### In-repo building blocks to reuse
| Module | What to reuse | Notes |
|--------|---------------|-------|
| `hooks/useAnalysisBoard.ts` | node map, `makeMove` (advance-or-fork), `goBack`, `goToNode`, `goToRoot`, `deleteSubtree`, move sounds | Add ONE command (`graftLine`); do not use `clearAllSidelines` (deletes every non-`mainLine` node, which would delete the other known lines) |
| `hooks/useTrainFreePlay.ts` | `evalByFen` FIFO cache, `currentQuality` (incl. D-06 root vetted lookup), `qualityByNode`, `markerEntryForQuality` | Fold into the new hook or keep as a grading sub-hook fed by an external engine |
| `components/analysis/VariationTree.tsx` | the wrapping `MobileTree` renderer (sidelines in parentheses, × with `btn-delete-line-{rootId}`, quality markers via `flawMarkerByNodeId`) | Add a `variant: 'wrap'` that forces `MobileTree` at every width (mirror of the existing `'vertical'` override at line 1091) |
| `components/board/HorizontalMoveList.tsx` | fixed-height `flex-wrap` box, auto-scroll to current | Used by `MobileTree` |
| `components/analysis/EngineLines.tsx` | `EngineLines` with `compact` and `maxLines` | The Stockfish row = `maxLines={expanded ? 2 : 1}` |
| `lib/mobileBoardControls.ts` | `usePublishMobileBoardControls` | Extend the payload (bot game precedent: `onResign` swaps in `BotGameMobileBar`) |
| `components/train/TrainBotStepper.tsx`, `TrainBotBubble.tsx` | tour stepper, desktop verdict bubble | `TrainBotBubble` already has `ring` |
| `TrainScoreChip` (exported from TrainReveal.tsx:418) | the `+N` pill | Strip total pill and the inline verdict pills |

**Installation:** none.

## Package Legitimacy Audit

This phase installs no external packages. Not applicable.

**Packages removed due to [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none

## Architecture Patterns

### System Architecture Diagram

```
                 SolveResponse (server verdict, vetted_moves, graded pair)
                               │
 grading Worker ──gradeResult / instantGrade(keyUci,keyLine) / gameMoveLine──┐
                               │                                              │
                               ▼                                              ▼
                     buildChipGroups(your/best/game UCIs)          line UCI sources (≤12 plies)
                               │                                              │
                               ▼                                              ▼
 user input ───────►  useTrainRevealTree ◄──── graftLine(lineUcis, root)  (non-navigating, child-reusing)
 (drop, ‹ › ⏮,         │  nodes / currentNodeId (useAnalysisBoard)
  list tap, chip,      │  linePaths[chip]  = walk(lineUcis)   ◄── derived, never stored on nodes
  SF-row click)        │  rootFocus (chip | null)  → activeChip = f(rootFocus, path(current))
                       │  isOffLine = current ∉ ∪ linePaths
                       │  qualityByNode (free nodes only) ◄── evalByFen ◄── reveal Stockfish engine
                       │                                                     (fen = displayFen,
                       │                                                      MultiPV 1 on-line,
                       │                                                      2+ off-line,
                       │                                                      off while instant pending)
        ┌──────────────┼───────────────────┬────────────────────┬─────────────────────┐
        ▼              ▼                   ▼                    ▼                     ▼
  board overlay   chips row          move list            Stockfish row         action bar
  (root: dimmed   (mark, SAN,        VariationTree         (only isOffLine)     ⏮ ‹ › ⇅ Analyze Next
   reveal overlay; eval, merged       variant='wrap',                            phone: MobileBottomBar
   line node: step  labels)           mainLine = active                          sm..lg: in-flow
   overlay; free:                     path, filtered nodes)                      lg+: under board
   grade marker)
        │
        ▼
 telemetry counters (chips, steps, forks, strip) ──► ReviewTelemetry v2 flush (Next / pagehide)
 Umami (strip expand, ⏮, ×, first fork)          ──► trackFeature (user handlers only)
 Analyze click ──► CachedTrainReveal + {rootFocus, currentPath, sidelinePaths} ──► restore replays paths
```

### Recommended file structure

```
frontend/src/
├── hooks/
│   ├── useAnalysisBoard.ts            # + graftLine (additive)
│   ├── useTrainRevealTree.ts          # NEW: tree + line paths + chip focus + free-node grading + nav + (de)serialize
│   └── useTrainFreePlay.ts            # DELETE (absorbed) or slim to a grading helper
├── lib/
│   ├── trainRevealLines.ts            # NEW (pure): RoleKey, MAX_LINE_PLIES, buildChipGroups, line UCI sources, sanFromPlayedUci
│   ├── trainArrows.ts                 # applyTrainSpotlight → buildChipFocusOverlay (dim, not filter); keep step builders
│   ├── trainBotCopy.ts                # verdictClause (D-05 words), walkthroughCopy (new steps, merged-chip arg, no hasSolution)
│   ├── trainTelemetry.ts              # REVIEW_TELEMETRY_SCHEMA_VERSION = 2, chips/strip/forked counters
│   ├── trainRevealCache.ts            # + optional tree fields
│   ├── mobileBoardControls.ts         # + optional train-reveal payload fields
│   └── analytics.ts                   # + 'train-sideline-fork' action, + 'train-verdict-strip' panel
└── components/train/
    ├── TrainReveal.tsx                # composition root only: reveal query, game-move search, layout
    ├── TrainVerdictStrip.tsx          # NEW (phone): avatar + total pill + one line, expands to details
    ├── TrainVerdictDetails.tsx        # NEW: full verdict + Your-call feedback + Also fine + motif (strip body AND desktop bubble)
    ├── TrainLineChips.tsx             # NEW
    ├── TrainMoveTreeList.tsx          # NEW: VariationTree wrap + Stockfish row
    ├── TrainRevealActionBar.tsx       # NEW: ⏮ ‹ › ⇅ Analyze Next (one component, three hosts)
    ├── TrainRevealGameFooter.tsx      # NEW: extracted footer (TrainReveal.tsx:1525-1573)
    └── TrainLineStepper.tsx           # DELETE (+ its test)
```

### Pattern 1: Tree with known lines as derived paths, plus a non-navigating graft

**What:** Keep `useAnalysisBoard`'s node map as the single tree. Pre-load each chip group's line with a new `graftLine(uciMoves, parentId)` that, in ONE functional `setState`, walks from `parentId`, reuses an existing child with the same from/to, creates the rest, and never touches `currentNodeId`. Compute `linePaths[chipKey]` each render by walking that line's UCI list from the root through existing children.

**Why:** `playUciLine` (the closest existing command) lands on the line's end and early-returns when nothing new was grafted, and `insertPvLine` parks the board at the fork node and requires a non-null fork id [VERIFIED: useAnalysisBoard.ts:490-493 `const forkNode = prev.nodes.get(forkNodeId); if (!forkNode) return prev;` and :528 `currentNodeId: forkNodeId, // park at fork, not first PV move`; :677-678 `if (landingId === prev.currentNodeId) return prev;` / `return { ...prev, nodes: newNodes, currentNodeId: landingId, nextId: id };`]. Neither can graft three root branches, nor a late line, without moving the user.

**Why derived paths:** child reuse means the same node can be "a user move" one second and "part of the game line" the next (the user hand-plays the game move before its search resolves; Phase 236 delivers lines late). Storing a role on the node goes stale; walking UCIs never does. It also makes D-13 automatic: `makeMove` reuses an existing child (useAnalysisBoard.ts:305-309), so a hand-played known move creates no node and is classified "on-line".

**Tree convention for `mainLine` (Discretion item):** do not rely on `mainLine` for semantics. Leave the hook's `mainLine` empty (seed root with `loadMainLine([], puzzle.fen)` as `useTrainFreePlay` already does at :415/:446) and pass the list component a **view**: `mainLine = activeLinePath` (or the user's root-fork chain under D-04) and a `nodes` map filtered to the active line, the free subtrees hanging off it, and free root forks. `VariationTree`'s `buildSiblingBlocks` then shows exactly the sketch's `selectedListHtml(true)`: active line numbered, free sidelines inline with ×, root forks before move 1 [VERIFIED: VariationTree.tsx:439-480 treats every non-`mainLine` node as a sideline; `nearestMainIdx === -1` blocks render before `mainLine[0]` in MobileTree, VariationTree.tsx:743].

**Root-fork reachability after a chip tap (Discretion):** show free root forks as a sideline before move 1 of the active line. This is what the sketch does (`selectedListHtml`: `const fromRoot = branchStarts([0]); if (fromRoot.length) body = fromRoot.map(sublineHtml).join('') + body;`, index.html:509-510) and it falls out of the filtered-view convention for free.

### Pattern 2: Chip groups from `buildLineBoxes`

Lift `buildLineBoxes` (TrainReveal.tsx:287-353) into `lib/trainRevealLines.ts` as `buildChipGroups`, keeping its grouping (`CANONICAL_ROLE_ORDER.filter((r) => uciByRole[r] === uci)`), its display-line precedence (best line wins, then played line, else the standalone game line), its Phase 236 `pending: 'loading' | 'failed' | null`, and its quality rule. Values to keep verbatim [VERIFIED: TrainReveal.tsx:83 `type RoleKey = 'your' | 'best' | 'game';`, :97 `const CANONICAL_ROLE_ORDER: readonly RoleKey[] = ['your', 'best', 'game'];`, :105 `const MAX_LINE_PLIES = 12;`]. Chip label = roles joined with " = " using short labels You / Best / Game (sketch `grp.roles.map((x) => LINE[x].short).join(' = ')`, index.html:495). Testids: new per-chip ids keyed on the primary role (e.g. `train-chip-your`, `train-chip-best`, `train-chip-game`), never on SAN.

Late/failed lines (Discretion): every chip group always seeds **at least its first move** (its UCI is known as soon as the chip exists: `playedMoveUci`, `instantGrade.keyUci`, `played_in_game_move_uci`), then extends when the line arrives. Pending chip: SAN + mark + a small spinner in place of the eval (`data-line-status="loading"`); failed: SAN + mark, no eval (`data-line-status="failed"`), list shows the single move. This also covers the WR-02 stand-in grade whose played line is empty (trainGradingSupport.ts:156-165 comment: "the played-move line is empty"). The SAN-only game move (no UCI, TrainReveal.tsx:1494-1498) gets a non-interactive chip with no arrow and no branch.

### Pattern 3: Chip focus = `rootFocus` state + path derivation

```
rootFocus: ChipKey | null         // the only stored focus; default = the chip containing 'your'
activeChip =
  current === root            ? rootFocus
  current on linePaths[k]     ? k
  current is free             ? chip whose path contains current's nearest known ancestor, else null (root fork, D-04)
```

- Chip tap (D-01): if `activeChip !== k` (board is on another line, a sideline of another line, or a root fork) → `goToRoot()`; always `setRootFocus(k)`. If the board is on k's line or a sideline hanging off it, stay put (sketch `case 'chip'` keeps position when `rootRole(S.cur) === role`). Count for telemetry.
- User move from root that matches a line → lands on that line's first node (reuse) → `setRootFocus(thatChip)` (sketch onSquare: "a played move that lands on a known line ... activates that line's chip").
- User move from root that matches nothing → new free root node → `setRootFocus(null)` (D-04).
- ⏮ → `goToRoot()`. Recommendation [ASSUMED]: if `rootFocus === null`, restore the default You chip so the root view always has a focus; otherwise keep it.
- › forward: at root go to the active chip's first node (or, under D-04, the last-visited root fork); below root prefer the last-visited child, else the child on the same known path, else lowest id. Do NOT use `useAnalysisBoard.goForward` (lowest-id / pv-first rule, :344-360). The sketch's own `fwd()` prefers `lastChild` even at root, which would step into the previously viewed line after a chip tap; avoid that at root.

### Pattern 4: Dim, don't filter: opacity on the overlay

`applyTrainSpotlight` FILTERS arrows and markers [VERIFIED: trainArrows.ts:535-539 `arrows: overlay.arrows.filter(matchesActivePair), markers: overlay.markers.filter(...)`]. Replace it with a builder that maps every arrow/marker to an opacity: active-group UCIs opaque, everything else (also-fine included) dimmed. Match arrows by start/end squares (same as today, so a merged You = Game chip lights both the quality-colored and the thin white arrow) and markers by `markerOwners` (WR-02: a badge belongs to the move that won its square).

`BoardArrow` and `SquareMarker` have no opacity field today; `ArrowOverlay` computes `opacity={arrow.isHovered ? ARROW_HOVER_OPACITY : baseOpacity}` with `const ARROW_OPACITY = 0.75;` / `const ARROW_LOW_EMPHASIS_OPACITY = 0.30;` [VERIFIED: ChessBoard.tsx:133-138, :233, :246]. Add optional `opacity?: number` to both types (ChessBoard.tsx:17 and boardMarkers.tsx:37) and honour it in `ArrowOverlay` and `SquareMarkerGroup` (`<g opacity=…>`, boardMarkers.tsx:288). Additive, default unchanged for every other caller (MiniBoard, Analysis, Openings). Put the dim factors in `lib/theme.ts` (frontend/CLAUDE.md: opacity factors are theme constants). Sketch values: arrows 0.22 dim / 0.92 lit, badges 0.32 dim / 1 lit (index.html:407-415).

Draw order: ChessBoard sorts `onTop` first, then hovered, then color/width (ChessBoard.tsx:186-197), and the game arrow is built with `onTop: true` (trainArrows.ts:461-467). Set `onTop` on the active group's arrows (and clear it on a dimmed game arrow) so the lit arrow paints above dimmed ones, the sketch's "the lit one paints on top".

Behavior change to call out in the plan: since 260902-qf7 the pristine board **hides** also-fine arrows until their card is hovered (TrainSolveScreen.tsx:1558-1581). The locked design draws them, dimmed. Sharp puzzles still draw none (`TRAIN_SHARP_ALT_MOVE_ARROWS = 0`, trainArrows.ts:127).

Off the root, keep today's per-position overlays: on a known-line node, `buildTrainStepMarkers` (first move keeps its quality badge) and `buildTrainStepArrows` (blue next-move pointer along the line) plus the quality-colored last-move highlight; on a free node, the grading marker and quality-colored highlight from the tree hook plus optional Stockfish arrows (`buildTrainFreePlayArrows(pvLines, sfArrows)`). The sketch draws nothing past ply 1, but the step overlay is UAT-earned behavior; keeping it is the conservative choice [ASSUMED: owner may prefer the sketch's barer board].

### Pattern 5: One verdict body, two hosts

Extract `renderVerdictBubbleBody` (TrainSolveScreen.tsx:377-436) and the Your-call card body (TrainReveal.tsx:1405-1458: call label + `TrainScoreChip`, `guessFeedbackProse`, Also fine SAN list, motif) into one `TrainVerdictDetails`. Phone: `TrainVerdictStrip` renders avatar + total pill (`scorePuzzle`) + one-line clause, a `<button aria-expanded>` that reveals `TrainVerdictDetails` (D-07 order). Desktop: `TrainBotBubble` with `TrainVerdictDetails` as its body, in the right column. Keep existing testids where the element survives (`train-bot-verdict-line`, `train-bot-pill-guess`, `train-bot-pill-move`, `train-bot-look-closer`, `train-bot-return-tail`, `train-verdict-guess-prose`, `train-reveal-also-fine`, `train-reveal-motif`) so assertions port mechanically.

D-05/D-06 copy: the current clause [VERIFIED: trainBotCopy.ts:412-419]:
```
if (correctGuess && moveQuality === 'good') return 'Right call [+1], right move [+2].';
if (correctGuess && moveQuality === 'inaccuracy') return 'Right call [+1], decent move [+1].';
if (correctGuess) return 'Right call [+1], wrong move [+0].';
if (moveQuality === 'good') return 'Wrong call [+0], but the right move [+2].';
if (moveQuality === 'inaccuracy') return 'Wrong call [+0], decent move [+1].';
return 'Wrong call [+0], wrong move [+0].';
```
Both `verdictClause` (trainBotCopy.ts) and `verdictClauseParts` (TrainSolveScreen.tsx:346-361, with `'right move'` / `'but the right move'`) change. Add an `isBest: boolean` input computed from the SAME predicate that merges the You and Best chips (`lastPlayedUci === revealBestUci`, where `revealBestUci = gradeResult?.bestMoveUci ?? instantGrade?.keyUci ?? null`, TrainSolveScreen.tsx:1507), and say "best move" only when `isBest && moveQuality === 'good'`. Wrong-call wording for the best move ("but the best move") is Claude's draft (D-11). Points are untouched: `MOVE_TIER_POINTS = { good: 2, inaccuracy: 1, wrong: 0 }`, `GUESS_POINTS = 1`, `scorePuzzle = (correctGuess ? GUESS_POINTS : 0) + MOVE_TIER_POINTS[moveTier]` [VERIFIED: trainScore.ts:25-29, :49, :68-70].

### Pattern 6: One reveal engine (Discretion: engine lifetime and contention)

Today three Workers can exist on the solve screen: the session-scoped grading engine, the free-play engine (`enabled: isExploring`, multiPv `max(sfLines, sfArrows)`, useTrainFreePlay.ts:254-258), and the eval-bar engine (`enabled: evalBarFen !== null`, `TRAIN_EVAL_BAR_MULTIPV = 1`, disabled while exploring and while an instant grade is pending, TrainSolveScreen.tsx:1472-1483, :252). The free-play and eval-bar engines are mutually exclusive by gate.

Recommendation: collapse them into ONE `useStockfishEngine` for the reveal: `fen = displayFen`, `enabled = showEvalBar` (verdict landed AND `instantGrade?.status !== 'pending'`, the Phase 236 RESEARCH Pitfall 2 rule), `multiPv = isOffLine ? max(2, sfArrows) : 1`. `useStockfishEngine` re-searches at a new MultiPV **without restarting the Worker** [VERIFIED: useStockfishEngine.ts:66-70 doc comment "A change re-searches the current position at the new width WITHOUT restarting the worker (D-06)"]. It feeds the eval bar on every node, the Stockfish row and SF arrows off-line, and the eval cache the sideline grader reads.

Why this matters beyond Worker count: the grader rates a free move from `evalByFen.get(parentFen)` (useTrainFreePlay.ts:331-332). Today the free-play engine only ever searches positions **inside** free play, so the first free move forked from a stepped line position has no parent eval and never gets a badge (only the root is seeded, :283-292). An engine that searches every displayed node fills the cache for the parent naturally. Keep the root seed from `gradeResult` (and the D-06 vetted-move root shortcut, :359-362).

Contention: the grading Worker's background search (instant path) and the game-move search are serialized inside `useTrainGradingEngine` (Phase 236 plan 04); the reveal engine is a separate Worker. Gating it off while `instantGrade` is pending keeps the Phase 236 guarantee that nothing competes with the phone-accuracy ground-truth search. The game-move search may still overlap the reveal engine exactly as the eval bar overlaps it today, which is no regression. Lazy start (only on the first off-line position) is unnecessary because the eval bar already needs a search on-line.

### Pattern 7: Action bar, three hosts

`TrainRevealActionBar` (⏮ ‹ › ⇅ + Analyze + Next). Hosts:
- `< sm` (phones): published through `usePublishMobileBoardControls`; `MobileBottomBar` renders it instead of the main nav, the same way `onResign` swaps in `BotGameMobileBar` (App.tsx:487-505). Extend `MobileBoardControls` with optional train fields (e.g. `onNext`, `analyzeTo: string | null`, `onAnalyzeClick`, `highlight?: boolean` for the tour ring) and add them to the effect's destructure and deps (mobileBoardControls.ts:79-105).
- `sm` to `< lg`: render the same component **in-flow** under the board. `MOBILE_BOTTOM_BAR_CLASSES` contains `sm:hidden` [VERIFIED: App.tsx:464-465 `'fixed bottom-0 inset-x-0 flex sm:hidden z-40 bg-background border-t border-border pb-safe'`], and the Train layout only goes two-column at `lg` (TrainSolveScreen.tsx:1930). Today's free-play strip already uses this split (`hidden sm:block`, TrainReveal.tsx:596-598).
- `lg+` desktop: under the board in the left column with a `← → Home` hint (sketch `deskHtml`).

Publish for the whole reveal (`showResultRow && verdict !== null`), not only while exploring (today: `freePlay.isExploring ? {...} : null`, TrainSolveScreen.tsx:968-991). Keep `board-btn-*` testids from `BoardControls` for ⏮ ‹ › ⇅ and `btn-train-analyze` / `btn-train-next` for the actions so most existing selectors survive. ⏮ is the `train-solution` successor (Pattern 11). Analyze stays a router `<Link>` with `onClick={handleAnalyzeFromReveal}` (never `data-umami-event` on an internal Link).

### Pattern 8: Desktop keyboard

`useBoardNavigationInput` handles only ArrowLeft/ArrowRight and is inert while every container ref is null; Train never attaches one [VERIFIED: useBoardNavigationInput.ts:140 `if (e.key !== 'ArrowLeft' && e.key !== 'ArrowRight') return;`; header comment "Both surfaces are inert while every container ref is null"]. Call it from the tree hook with a ref on the desktop board wrapper and the hook's own back/forward (Pattern 3 forward rule), and add an optional `goHome` (Home key) to its options, additive for Analysis/Openings. It already guards inputs, modifiers, modals and key repeat.

### Pattern 9: Tour

- `walkthroughCopy(step, hasAnalyze, mergedChip: 'best' | 'game' | null)`: drop `hasSolution`; new `spotlightTarget` union, e.g. `'strip' | 'chips' | 'tree' | 'board' | 'lines' | 'bar'` [VERIFIED current: trainBotCopy.ts:533 `spotlightTarget: 'verdict' | 'lines' | 'board' | 'actions';`, :526-527 `export type WalkthroughStep = 0 | 1 | 2 | 3 | 4 | 5;` / `export const WALKTHROUGH_STEP_COUNT = 6;`, :219 `export const STEPPER_COPY_MAX_CHARS = 145;`]. On desktop step 1 targets the verdict bubble (no strip) and step 6 the controls row under the board; copy must read correctly on both ("only describe what is on screen").
- `useTrainWalkthrough` today auto-advances step 1 on a spotlight and step 2 on a line step, and scrolls `[data-testid^="train-line-box-"]` into view on phones (useTrainWalkthrough.ts:26-27, :157-173). Re-point: chip tap advances the chips step, a tree step advances the stepping step, optionally a fork advances the board step; replace the card-scroll effect with "scroll the active target into view" (the phone may scroll during the tour, D-10).
- Last step: today `lastControl` IS the real Solution/Analyze/Next row inside the bubble (TrainSolveScreen.tsx:449-479). Now the actions live in the bar: pass `lastControl={null}` (or a short note) and ring the bar via the payload `highlight` flag. Leaving through the bar's Next/Analyze must still call `walkthrough.leave()` (stamps `reveal_walkthrough` only on the last step, :182-186).
- Phone render order during the tour (D-10): Hilda's `TrainBotStepper` bubble, then the strip. Desktop: Hilda bubble stacked above the verdict bubble in the right column.
- Telemetry `markWalkthroughActive` (sticky, Phase 233 D-13) stays.

### Pattern 10: Restored reveal

Node ids are not stable across a rebuild (the game line arrives asynchronously after a restore, so seeding order and ids differ). Persist UCI paths, not ids:
```
CachedTrainReveal += {
  revealTree?: {
    rootFocus: 'your' | 'best' | 'game' | null;   // primary role of the focused chip group
    currentPath: string[];                          // UCIs root → current node
    sidelinePaths: string[][];                      // UCIs root → each free leaf
  }
}
```
On restore: seed known lines, `graftLine` each sideline path from the root and the current path, then `goToNode` the node at `currentPath` (silent). Late game-line seeding reuses the grafted nodes (child reuse), so nothing duplicates. The field is optional: entries from older bundles restore to "You focused, at root, no sidelines". `isCachedTrainReveal` is a shallow check (trainRevealCache.ts:99-119); validate the new field loosely (arrays of strings) and drop it, not the whole entry, when malformed.

### Pattern 11: Telemetry v2 and Umami

Review telemetry, frontend [VERIFIED: trainTelemetry.ts:14 `export const TELEMETRY_SCHEMA_VERSION = 1;`, :26 `export const TELEMETRY_CARDS_CAP = 10;`, :31 `export const REVIEW_CARD_HOVER_MIN_MS = 800;`, :38 `export type ExploreMoveSource = 'board' | 'engine-line';`, :41 `export type CardEngageKind = 'open' | 'hover-start' | 'hover-end';`]. Backend [VERIFIED: app/schemas/train.py:195 `TELEMETRY_SCHEMA_VERSION: Final = 1`, :203 `TELEMETRY_CARDS_CAP: Final = 10`, :279 SolveTelemetry `v: Literal[1]`, :385 ReviewTelemetry `v: Literal[1]`].

Recommended v2 shape (key names are Discretion):
| v2 key | Meaning | Type |
|--------|---------|------|
| `v` | `2` | `Literal[1, 2]` on `ReviewTelemetry` |
| `review_chips_selected` | distinct chip groups selected by the user (tap, or a line-matching move from root) excluding the default You group | `TelemetryCardCount` (reuse cap 10, keeps the frontend constant imported so knip stays quiet) |
| `review_chips_total` | chip groups shown | `TelemetryCardCount` |
| `review_strip_expanded` | strip opened at least once (phone only; absent/false on desktop) | `StrictBool` |
| `review_explored` | forked at least one sideline (D-13) | `StrictBool` (meaning changes under v2) |
| `review_line_steps` | ‹ › / list taps / ← → | unchanged type |

Add a `model_validator(mode="after")` that rejects v2 keys on a v1 body and `review_cards_*` on a v2 body, so the JSONB column holds two clean shapes. Introduce `REVIEW_TELEMETRY_SCHEMA_VERSION` (= 2) on both sides and add it to the parity test's `_MIRRORED_CONSTANTS`; leave `TELEMETRY_SCHEMA_VERSION = 1` for `SolveTelemetry` (D-12: the solve patch is unaffected). Update `types/train.ts` `ReviewTelemetry` (`v: 1` at :220) to the v2 shape and `ReviewTelemetrySnapshot` + `isUsableReviewSnapshot` with `chipKeys` / `chipsTotal` / `stripExpanded` / `forked`.

Umami [VERIFIED: analytics.ts:384-402 ACTION_TARGETS includes `'analyze'`, `'train-solution'`, `'train-solve-retry'`, `'train-explore-exit'`; :361 `BOARD_TOOL_TARGETS = ['flip', 'paste-open', 'paste-load', 'line-expand', 'line-delete', 'elo-reset']`]. frontend/CLAUDE.md: "Never rename an existing event name or target". Recommendation:
| D-14 action | Event | Target | Why |
|-------------|-------|--------|-----|
| ⏮ rewind | `action` | `train-solution` (kept) | same meaning (back to the puzzle position); keeps history |
| sideline × | `board-tool` | `line-delete` (already fired by `VariationTree`'s × with page = train, VariationTree.tsx:689) | no new target; the old Stockfish-card × (`train-explore-exit`) has no successor UI, so stop emitting it and drop it from `ACTION_TARGETS` (removal is not a rename) |
| first fork per puzzle | `action` | NEW `train-sideline-fork` | per-puzzle ref flag, reset on puzzle change, fired from the drop/SF-click handler |
| strip expand | `panel-open` | NEW `train-verdict-strip` | opening a panel is the verb; fire only on the collapsed→open transition from the click handler |

All four must fire from user handlers, never from effects (frontend/CLAUDE.md D-03). The flip in the bar should go through `BoardControls`' existing `board-tool flip` event (BoardControls.tsx:218) or replicate it.

### Anti-Patterns to Avoid
- **Storing a `role` on tree nodes:** goes stale under child reuse and late lines. Derive from UCI paths.
- **Seeding lines with sequential `makeMove`/`playUciLine` calls:** `stateRef` only syncs after render (L-1/L-7 comments in useAnalysisBoard.ts:476-482); one `setState` per graft, functional updaters only.
- **Using `clearAllSidelines` for ⏮ or reset:** it deletes every non-`mainLine` node, i.e. the other known lines. ⏮ keeps sidelines; a puzzle change re-seeds a fresh tree.
- **Filtering the overlay for focus:** the design dims; filtering reintroduces the "hidden" state D-locked against.
- **Bumping the shared `TELEMETRY_SCHEMA_VERSION`:** changes `SolveTelemetry.v` too.
- **A per-file "complexity ceiling" mindset:** comments like "TrainReveal is pinned at the eslint `complexity: 68` ceiling" (TrainReveal.tsx:869-874) are stale; `eslint.config.js` now gates only `max-depth: 4`. Split for clarity, not for a pin.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Move tree, fork-or-advance, sounds | a new tree | `useAnalysisBoard` + one `graftLine` | sound suppression, illegal-SAN guards, child reuse already solved |
| Wrapping move list with sidelines and × | a token renderer | `VariationTree` `MobileTree` via a `variant: 'wrap'` | numbering, parentheses, × with tracking, quality markers, auto-scroll |
| Compact engine row | a PV formatter | `EngineLines compact maxLines={1 or 2}` | SAN replay, click-to-graft (`onMoveClick` → prefix UCIs), stable `minHeight` |
| Sideline move grading | a new classifier | `classifyTrainMoveQuality` + `evalToExpectedScore` + `terminalPositionEval` + `vettedMoveForSquares` | identical to the verdict pipeline and D-06 vetted lookup |
| Phone bottom bar takeover | a new fixed bar | `usePublishMobileBoardControls` + a `MobileBottomBar` branch | precedent `BotGameMobileBar`; avoids two fixed bars |
| Arrow/badge geometry | new SVG | `ChessBoard` `ArrowOverlay` + optional `opacity` | dedupe, outline, sort, badges |
| Window arrow keys | a keydown listener | `useBoardNavigationInput` (+ optional Home) | six guards incl. inputs, modals, repeat throttle |
| `+N` pill | a styled span | `TrainScoreChip` | shared scoring language (Phase 222 D-23) |

**Key insight:** this phase is mostly re-wiring proven parts. The two genuinely new pieces of logic are the non-navigating graft and the chip-focus derivation; keep both pure and unit-tested.

## Runtime State Inventory

This is a refactor of a shipped surface with persisted client and server state.

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | `drill_solves.telemetry` JSONB rows carrying v1 review keys (`review_cards_opened`, `review_cards_total`); merged per key with `coalesce(telemetry, '{}') || patch` (train_repository.py:3257-3270) | None (v1 stays valid, no backfill). Document that a row's `v` reflects the LAST patch, so v1-era solve keys sit under `v: 2` once a v2 review flush lands (Pitfall 4) |
| Stored data | `train_settings.reveal_walkthrough_seen_at` (alembic 7d6bb75aae54) already stamped for every user who finished the old tour | **Decision needed** (Open Question 1): accept, null it with a data migration, or add a new watermark/step |
| Live service config | Umami dashboards/funnels on `action:train-solution`, `action:train-explore-exit`, `board-tool:line-delete` (Umami DB, not git) | `train-solution` keeps flowing; `train-explore-exit` goes flat after deploy; note in CHANGELOG/STATE so funnels are not misread |
| OS-registered state | None (verified: no OS-level registration for this surface) | None |
| Secrets / env vars | None (no env var or secret names this phase) | None |
| Build artifacts / client caches | Open tabs and the PWA service worker can run the old bundle after deploy: they keep posting v1 review bodies and writing `train_reveal_cache` entries without tree fields | Backend must keep accepting v1 indefinitely; restore must default missing tree fields. No cache-version bump needed |

## Common Pitfalls

### Pitfall 1: Every existing graft moves the board
**What goes wrong:** a late line (key line via `onKeyLine`, played line when the background grade lands, game line when its search resolves) yanks the user back to the root or to the line's end. **Why:** `insertPvLine` parks at the fork, `playUciLine` lands at the end, `loadMainLine` resets. **Avoid:** `graftLine` must not write `currentNodeId`. **Warning sign:** a test that steps into a sideline, then resolves the game search, and sees `data-position` change.

### Pitfall 2: Seeding in one batch with stale state
**What goes wrong:** three grafts in one render chain onto the wrong parent. **Why:** command callbacks read `stateRef.current`, which syncs in an effect after render (useAnalysisBoard.ts:251-253). **Avoid:** do all graft work inside functional updaters (`setState((prev) => …)`), as `insertPvLine`/`playUciLine` already do.

### Pitfall 3: Forward goes to the wrong line at the root
**What goes wrong:** › at the puzzle position steps into Best while You is focused. **Why:** `goForward` picks the lowest-id child (or a pv child). **Avoid:** the hook computes the target id (Pattern 3) and calls `goToNode`.

### Pitfall 4: The shared schema version and the merged `v` key
**What goes wrong:** bumping `TELEMETRY_SCHEMA_VERSION` to 2 makes every solve POST send `v: 2`, which `SolveTelemetry` (`v: Literal[1]`) rejects; `SolveRequest`'s wrap validator then silently drops the whole solve telemetry (test_train_telemetry_schema.py:89-104 asserts invalid telemetry becomes `None`). **Avoid:** a separate `REVIEW_TELEMETRY_SCHEMA_VERSION`. Also: the review patch and solve patch both write the top-level `v`, so after the first review flush the stored row says `v: 2` while its solve keys are v1-shaped; analysis queries branch on `v` for review keys only. Update `test_review_telemetry_rejects_malformed`, whose parametrize list contains `{"v": 2, "exit": "next"}` as a must-reject case (test_train_telemetry_schema.py:64).

### Pitfall 5: Returning users never see the new tour
**What goes wrong:** the reveal changes completely (bottom nav replaced, Solution gone, chips) but only first-time users get the tour. **Why:** `resolveWalkthroughStep` returns null when `settings.reveal_walkthrough_seen_at !== null` (useTrainWalkthrough.ts:94-103). **Avoid:** owner decision before planning (Open Question 1).

### Pitfall 6: Tablet widths lose the action bar
**What goes wrong:** at 640-1023 px the stacked layout shows no ⏮ ‹ › and no Next. **Why:** the fixed bar is `sm:hidden`; Train is two-column only at `lg`. **Avoid:** in-flow bar for `sm..lg` (Pattern 7). Test at 768 px in UAT.

### Pitfall 7: The phone bar replaces the nav for the whole reveal
**What goes wrong:** a user who wants to leave Train mid-reveal has no bottom nav. **Why:** locked design. **Avoid:** nothing to change, but make sure the bar unpublishes on unmount and on puzzle transitions before the reveal (the hook's effect cleanup already sets the payload to null), and that the guess/grading phases still show the nav.

### Pitfall 8: `HorizontalMoveList` auto-scroll can scroll the page
**What goes wrong:** stepping causes the window to jump on a short phone. **Why:** it calls `activeRef.current?.scrollIntoView({ block: 'nearest', behavior: 'smooth' })` (HorizontalMoveList.tsx, effect on `currentKey`), which scrolls every scrollable ancestor. **Avoid:** fine when the first view fits without scroll; check at 375x667 (where it does not fit) during UAT. If it jumps, scroll the list box's `scrollTop` directly in the wrap variant.

### Pitfall 9: SOLV-02 regression via the new drop path
**What goes wrong:** a post-verdict drop reaches `gradeAndSolve`. **Why:** the guard is purely ordering: `guess === null` → nudge; `moveApplied` → free branch; only then the graded path (TrainSolveScreen.tsx:1356-1406). **Avoid:** keep the order; the new branch becomes `if (verdict === null) return false; return tree.playMove(source, target);`. Keep tests asserting `solvePuzzle` called exactly once and the grading engine's `gradeMove` not called again after forks.

### Pitfall 10: Merged chips and shared target squares
**What goes wrong:** dimming a You = Game chip leaves its thin white arrow bright, or a dimmed best badge sits on a lit alternative's square. **Why:** a merged group owns two arrows with different `layerKey`s; badges are deduped by end square (played > best > fine > game, trainArrows.ts:405-414). **Avoid:** match arrows by squares and badges by `markerOwners`, exactly as `applyTrainSpotlight` does today.

### Pitfall 11: Late lines and the instant-path gates
**What goes wrong:** the reveal engine runs while the Phase 236 background grade is pending; or a pending chip shows a stale eval. **Avoid:** gate the reveal engine on `instantGrade?.status !== 'pending'` (as `showEvalBar` does, TrainSolveScreen.tsx:1472); render pending/failed chips per Pattern 2.

### Pitfall 12: Copy lives in two places
**What goes wrong:** the strip says "best move" but the desktop bubble still says "right move". **Why:** `verdictClauseParts` is in TrainSolveScreen.tsx (:346-361), not trainBotCopy.ts as CONTEXT D-06 assumes; `verdictClause` (bracket text) is in trainBotCopy.ts. **Avoid:** move the parts function next to `verdictClause` in `trainBotCopy.ts` (it returns strings and numbers, so the module stays React-free) and drive both from one table. Tests at trainBotCopy.test.ts:359 and :366 pin the old wording.

### Pitfall 13: Test sentinels tied to the card structure
**What goes wrong:** most reveal tests break at once. **Why:** `train-verdict-guess` (the Your-call card, which goes) appears 96 times as the "reveal landed" wait target; `train-line-box-your-move` 61, `train-line-box-best-move` 37, `btn-train-solution` 22, `train-line-stepper-token-0` 16, `train-reveal-exploration` 11 (counted across TrainSolveScreen.test.tsx, TrainReveal.test.tsx, TrainSolveScreen.restoredGameArrow.test.tsx, Train.solveLoop.test.tsx). **Avoid:** Wave 0 adds a shared helper (e.g. `waitForReveal()` keyed on `train-reveal`) and a stable new sentinel, then ports file by file.

### Pitfall 14: knip after removals
**What goes wrong:** CI fails on dead exports. **Candidates:** `CardEngageKind`, `REVIEW_CARD_HOVER_MIN_MS`, `TrainLineStepper` (+ `TRAIN_LINE_STEPPER_MAX_HEIGHT_PX`, `TrainLineStep`), `useTrainFreePlay`/`TrainFreePlayState`, `applyTrainSpotlight`, `trainGlyphColor`, `TrainRevealStep`, and `ArrowGlyphIcon` (its only consumer is TrainReveal.tsx). Run `npm run knip` per plan.

### Pitfall 15: Type-checking is not in lint/test
`npm run lint` and `npm test` do not type-check (frontend/CLAUDE.md); shared types change heavily here (`BoardArrow`, `SquareMarker`, `MobileBoardControls`, `ReviewTelemetry`, `CachedTrainReveal`). Run `npm run build` in every plan's verify step.

## Code Examples

Recommended shapes, derived from in-repo patterns (not official docs).

### Non-navigating graft (additive to `useAnalysisBoard`)
```typescript
// Mirrors playUciLine's child reuse (useAnalysisBoard.ts:634-680) but never writes currentNodeId.
const graftLine = useCallback((uciMoves: string[], parentId: NodeId | null): void => {
  if (uciMoves.length === 0) return;
  setState((prev) => {
    const parentFen = parentId !== null ? (prev.nodes.get(parentId)?.fen ?? null) : prev.rootFen;
    if (parentFen === null) return prev; // unknown parent → no-op
    const nodes = new Map(prev.nodes);
    const chess = new Chess(parentFen);
    let cursor: NodeId | null = parentId;
    let id = prev.nextId;
    for (const uci of uciMoves) {
      let move: ReturnType<typeof chess.move>;
      try {
        move = chess.move({ from: uci.slice(0, 2), to: uci.slice(2, 4), promotion: uci.length > 4 ? uci.slice(4, 5) : 'q' });
      } catch {
        break; // chess.js 1.4 throws on illegal input (Phase 210)
      }
      const existing = findChild(nodes, cursor, move.from, move.to); // small helper, keeps depth ≤ 4
      if (existing) { cursor = existing.id; continue; }
      nodes.set(id, buildNode(id, move.san, chess.fen(), move.from, move.to, cursor));
      cursor = id;
      id++;
    }
    return id === prev.nextId ? prev : { ...prev, nodes, nextId: id };
  });
}, []);
```

### Path walk for known-line membership
```typescript
/** Node ids along `uciMoves` from the root, stopping at the first missing child. */
export function walkLinePath(nodes: Map<NodeId, MoveNode>, uciMoves: readonly string[]): NodeId[] {
  const path: NodeId[] = [];
  let parent: NodeId | null = null;
  for (const uci of uciMoves) {
    const child = findChild(nodes, parent, uci.slice(0, 2), uci.slice(2, 4));
    if (!child) break;
    path.push(child.id);
    parent = child.id;
  }
  return path;
}
```

### Telemetry v2 validator (backend)
```python
class ReviewTelemetry(BaseModel):
    model_config = ConfigDict(extra="forbid")
    # Must be a member of {TELEMETRY_SCHEMA_VERSION, REVIEW_TELEMETRY_SCHEMA_VERSION}.
    v: Literal[1, 2]
    ...
    review_chips_selected: TelemetryCardCount | None = None
    review_chips_total: TelemetryCardCount | None = None
    review_strip_expanded: StrictBool | None = None

    @model_validator(mode="after")
    def _keys_match_version(self) -> "ReviewTelemetry":
        """Reject v2 keys on a v1 body and v1 card keys on a v2 body (expected client drift, no Sentry)."""
        v1_only = (self.review_cards_opened, self.review_cards_total)
        v2_only = (self.review_chips_selected, self.review_chips_total, self.review_strip_expanded)
        if self.v == 1 and any(x is not None for x in v2_only):
            raise ValueError("v2 keys on a v1 review body")
        if self.v == 2 and any(x is not None for x in v1_only):
            raise ValueError("v1 card keys on a v2 review body")
        return self
```
(`ValueError` here becomes a normal 422 for the review route, matching the "a bad body is a normal 422" docstring at app/schemas/train.py:378-379.)

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Line cards with per-card `TrainLineStepper` | chips + one tree list | this phase | `TrainLineStepper.tsx` retires |
| Free play as a mode (`isExploring` swap, Solution exit) | forks in place, ⏮ | this phase | `useTrainFreePlay.start/reset` semantics go away |
| Spotlight = filter overlay | focus = dim overlay | this phase | `applyTrainSpotlight` replaced |
| Per-file eslint complexity pins | `max-depth: 4` only | Phase 215 | stale "complexity 68" comments can be deleted |

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | ⏮ with no focused chip (D-04 state) re-focuses You | Pattern 3 | Minor UX; easy to flip |
| A2 | Keep the step overlay (quality highlight + blue next-move arrow) on known-line nodes past the root | Pattern 4 | Owner may want the sketch's barer board |
| A3 | `review_chips_selected` excludes the default You group even when re-tapped | Pattern 11 | Analysis semantics; costly once v2 rows exist (D-12 reversibility) |
| A4 | Reuse `board-tool line-delete` for the × instead of a new train target | Pattern 11 | Funnel naming preference |
| A5 | Strip expand uses `panel-open` / `train-verdict-strip`, first fork uses `action` / `train-sideline-fork` | Pattern 11 | Naming only, but never renamable later |
| A6 | Stockfish row expands to exactly 2 PVs regardless of the `sfLines` setting | Pattern 6 | Users who set 3 lines see 2 here |
| A7 | The claude-in-chrome tools are available to the UAT agent (per memory notes; not probed this session) | Environment | UAT falls back to owner |
| A8 | Desktop tour bubble stacks above the verdict bubble in the right column (D-10 only specifies the phone) | Pattern 9 | Layout tweak |

## Open Questions

1. **Should returning users see the new tour?** (affects plan scope; needs an owner decision)
   - What we know: the gate is `reveal_walkthrough_seen_at IS NULL`; `OnboardingStep = Literal["intro", "reveal_walkthrough", "sr_explained"]` [VERIFIED: app/schemas/train.py:676] and `export type OnboardingStep = 'intro' | 'reveal_walkthrough' | 'sr_explained';` [VERIFIED: hooks/useTrainOnboarding.ts]. The column was added by alembic `7d6bb75aae54`.
   - What's unclear: whether the owner wants existing users re-onboarded to a screen that replaces their bottom nav during the reveal and removes Solution. CONTEXT.md does not decide this.
   - Options: (a) accept: only users who never finished the old tour see it (zero backend change); (b) Alembic data migration `UPDATE train_settings SET reveal_walkthrough_seen_at = NULL` (re-shows once for everyone, loses the first-seen timestamps); (c) a new step `reveal_walkthrough_v2` plus column (keeps history; Literal on both sides, repository column map, migration).
   - Recommendation: ask the owner before or during planning (a `checkpoint:decision` is appropriate). If re-onboarding is wanted, (c) keeps history; (b) is the smallest change.

2. **Chip tap while on a free sideline of the SAME chip's line:** D-01 says "anywhere other than that chip's line" jumps to the root. Recommendation: treat a sideline hanging off the chip's own line as "on the line" (no jump), matching the sketch's `rootRole` walk (`case 'chip'` only calls `goto(0)` when `rootRole(S.cur) !== role`). The planner can lock this as a discretion call.

3. **Desktop strip:** locked as none on desktop, so `review_strip_expanded` is phone-only. Record that in the `ReviewTelemetry` docstring so analysis does not read a desktop `false` as "ignored".

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Node | frontend build/test | ✓ | v24.19.0 (engines `>=24.15.0`) | — |
| npm | scripts | ✓ | 11.17.0 | — |
| vitest | frontend tests | ✓ | 5.0.0 | — |
| uv | backend tests | ✓ | 0.10.9 | — |
| PostgreSQL dev DB (Docker) | `tests/routers/test_train.py` review-route tests | ✓ | container `flawchess-dev-db-1` healthy | — |
| Chrome + claude-in-chrome | 390x844 / 375x667 / desktop UAT (D-11) | assumed ✓ (A7) | — | owner runs UAT |
| Real phone | tap leg | ✗ (owner) | — | deferred to owner per D-11 |

**Missing dependencies with no fallback:** none.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | Vitest 5.0.0 + @testing-library/react 16 (jsdom 30); pytest via uv |
| Config file | `frontend/vite.config.ts` `test:` block (`testTimeout`, `hookTimeout`, `setupFiles: ['src/vitest.setup.ts']`); `pyproject.toml` |
| Quick run command | `cd frontend && npx vitest run src/hooks/__tests__/useTrainRevealTree.test.ts src/lib/__tests__/trainArrows.test.ts src/lib/__tests__/trainBotCopy.test.ts` |
| Full suite command | `cd frontend && npm run lint && npm run build && npm test -- --run && npm run knip`; `uv run pytest -n auto -x` |

### Phase Requirements → Test Map
| Req | Behavior | Test Type | Automated Command | File Exists? |
|-----|----------|-----------|-------------------|-------------|
| R4 / Pattern 1 | `graftLine` grafts with reuse, never moves `currentNodeId`, no-op on unknown parent | unit | `npx vitest run src/hooks/__tests__/useAnalysisBoard.test.ts` | ✅ (add cases) |
| R4 / D-03 | three lines seeded at ≤12 plies; late line grafts without moving the board; WR-02 empty played line seeds first move only | unit (hook) | `npx vitest run src/hooks/__tests__/useTrainRevealTree.test.ts` | ❌ Wave 0 |
| R3 / D-01, D-04 | chip tap jumps to root only off the chip's line; unmatched root move clears focus; matching root move focuses that chip | unit (hook) | same file | ❌ Wave 0 |
| R4 / D-13 | hand-played known move = board move, no fork; first free node = fork (`review_explored`) | unit (hook + telemetry) | same file + `useTrainPuzzleTelemetry.test.ts` | ✅/❌ |
| R4 | grading markers only on free nodes; D-06 root vetted shortcut kept; mid-line fork gets graded once parent eval is cached | unit | ported from `useTrainFreePlay.test.ts` | ✅ (port) |
| R2 / D-02 | chip groups merge You = Best / You = Game; pending/failed states | unit (pure) | `npx vitest run src/lib/__tests__/trainRevealLines.test.ts` | ❌ Wave 0 |
| R3 / Pattern 4 | focus overlay dims (not filters), also-fine dimmed, merged chip lights both arrows, badges by owner | unit (pure) | `npx vitest run src/lib/__tests__/trainArrows.test.ts` | ✅ (rewrite spotlight block) |
| R3 | `ChessBoard` honours `opacity` on arrows and markers | unit | `npx vitest run src/components/board/__tests__/` | ✅ (add case) |
| R1 / D-05, D-06 | clause vocabulary incl. "best move", no brackets in the strip | unit | `npx vitest run src/lib/__tests__/trainBotCopy.test.ts` | ✅ (update :359/:366) |
| R1 / D-07, D-08 | strip collapsed on mount, expands in D-07 order, Your-call content present, no Analyze inside | component | `npx vitest run src/components/train/__tests__/TrainVerdictStrip.test.tsx` | ❌ Wave 0 |
| R5 | bar publishes for the whole reveal (<sm) and renders in-flow (sm..lg); Next/Analyze/⏮ wired | component | `TrainSolveScreen.test.tsx` "mobileBoardControls publishing" block + `App.test.tsx` | ✅ (rewrite) |
| R5 | first view fits 390x844, no scroll | manual (browser UAT) | same-origin 390x844 iframe, assert `scrollHeight <= innerHeight` | manual-only (jsdom has no layout) |
| R6 | ← → Home navigate on desktop; Home = root | unit | `useBoardNavigationInput` test + hook test | ✅/❌ |
| R7 / D-09 | 6 steps, each ≤145 chars, merged-chip mention only when merged, Analyze only when `hasAnalyze` | unit | `trainBotCopy.test.ts` (budget test at :257-262) | ✅ (update) |
| R7 / D-10 | tour bubble above strip; ring targets; bar ring via payload; leave stamps on last step | component | `TrainSolveScreen.test.tsx` walkthrough block (:3226) | ✅ (rewrite) |
| R7 / D-11 | tour readable at 390x844, 375x667, desktop | manual (agent browser UAT) | — | manual-only |
| G-SOLV02 | forks never call `gradeMove`/`solvePuzzle` again | component | `TrainSolveScreen.test.tsx` | ✅ (keep, port selectors) |
| G-MARKS | herring and server-graded verdicts keep their marks on chips and board | component | `TrainSolveScreen.test.tsx` Phase 236 block (:3629) | ✅ (port) |
| G-RESTORE | cache writes `revealTree`; restore focuses the chip, rebuilds sidelines, lands on the saved node; old entries default | unit + page | `trainRevealCache.test.ts`, `Train.solveLoop.test.tsx`, `TrainSolveScreen.restoredGameArrow.test.tsx` | ✅ (extend) |
| G-TELEM / D-12 | v2 body shape; v1 still valid; cross-version keys rejected; parity constants | unit + pytest | `npx vitest run src/hooks/__tests__/useTrainPuzzleTelemetry.test.ts`; `uv run pytest tests/schemas/test_train_telemetry_schema.py tests/schemas/test_train_telemetry_parity.py tests/routers/test_train.py -k review` | ✅ (update) |
| D-14 | Umami fires exactly on strip expand, ⏮, ×, first fork; never on mount/restore | component | spy on `trackFeature` in TrainSolveScreen tests; `analytics.test.ts` slug test | ✅ (add) |

### Sampling Rate
- **Per task commit:** the touched test files (`npx vitest run <files>`), plus `npx tsc -b` via `npm run build` when shared types change.
- **Per wave merge:** `cd frontend && npm run lint && npm run build && npm test -- --run && npm run knip`; backend `uv run pytest tests/schemas tests/routers/test_train.py -x`.
- **Phase gate:** the full CLAUDE.md pre-merge gate (ruff format/check, ty, `check_function_size.py`, `uv run pytest -n auto -x`, frontend lint/build/test/knip) green, plus the agent-run browser UAT at 390x844, 375x667, 768x1024 and 1280x800.

### Wave 0 Gaps
- [ ] `src/hooks/__tests__/useTrainRevealTree.test.ts`: seeding, late graft, focus derivation, forward rule, fork detection, restore round trip
- [ ] `src/lib/__tests__/trainRevealLines.test.ts`: `buildChipGroups` (port the `buildLineBoxes` cases from TrainReveal.test.tsx)
- [ ] `src/components/train/__tests__/TrainVerdictStrip.test.tsx`
- [ ] Shared test helper `waitForReveal()` and a stable reveal sentinel to replace the 96 `train-verdict-guess` waits
- [ ] ChessBoard mock in TrainSolveScreen.test.tsx (:89-120): add `data-arrow-opacities` / `data-marker-opacities` so dimming is assertable
- [ ] Delete `TrainLineStepper.test.tsx` with the component; port `useTrainFreePlay.test.ts` cases into the new hook test

## Security Domain

`security_enforcement` is not set in `.planning/config.json` (treated as enabled).

### Applicable ASVS Categories
| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no (unchanged; review route uses `current_active_user`) | FastAPI-Users |
| V3 Session Management | no | — |
| V4 Access Control | yes (unchanged) | review route 404s foreign/missing rows (routers/train.py:207-247) |
| V5 Input Validation | yes | Pydantic `extra="forbid"`, `StrictBool`, clamped ints, version-shape validator; client cache shape check (`isCachedTrainReveal`) |
| V6 Cryptography | no | — |

### Known Threat Patterns
| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Tampered/oversized review telemetry | Tampering | strict types, caps via `_clamp_to`, `extra="forbid"`, new cross-version validator |
| Tampered `train_reveal_cache` (sessionStorage) | Tampering (self only) | shallow validation; malformed tree field dropped, never trusted for grading; paths replayed through chess.js (illegal moves stop the graft) |
| Answer leak before the solve lands (T-190-16) | Information disclosure | chips, lines, engine and arrows exist only after `verdict !== null`; keep every new fetch/engine behind the same gate |
| Free-text in Umami props | Information disclosure | enumerated literal targets only; never SAN/FEN in a target or `InfoPopover` testid |

## Project Constraints (from CLAUDE.md)

- Frontend only plus the D-12 schema bump; no unplanned features (GSD scope rule).
- No magic numbers: dim opacities, bar sizes, PV counts as named constants; opacity factors in `lib/theme.ts`.
- `max-depth` 4 (eslint) is the hard gate; aim for small functions, cognitive complexity ≤ 15 as soft guidance; refactor bloated code you touch (TrainReveal.tsx / TrainSolveScreen.tsx are in scope).
- `noUncheckedIndexedAccess`: narrow every index access.
- `data-testid` on every interactive element (chips, strip toggle, bar buttons, Stockfish-row toggle, sideline ×), kebab-case, component-prefixed; `aria-label` on icon-only buttons (⏮ ‹ › ⇅); semantic `<button>`.
- Minimum `text-sm` everywhere (chip labels, strip line, SF row).
- Buttons via `Button` variants: Next = `default`, Analyze = `brand-outline`; never hand-rolled colors.
- Apply changes to both phone and desktop renderers.
- Umami: register targets in `analytics.ts` first, fire from user handlers only, never rename existing targets; internal Analyze `Link` uses `trackFeature`, not `data-umami-event`.
- Backend: Pydantic v2, `Literal[...]` not bare `str`, ty clean, no Sentry capture for expected validation failures.
- `npm run build` before integrating shared-type changes; knip must stay clean.
- Pre-merge gate (CLAUDE.md) before squash-merge; CHANGELOG `[Unreleased]` bullet when the phase merges.
- Memory: run browser UAT yourself (iframe phone emulation; `getBoundingClientRect` measurements; drive moves via `[data-square] [data-piece]` pointer sequences); never `bin/reset_db.sh` in plans.

## Sources

### Primary (HIGH confidence, read this session)
- `frontend/src/components/train/TrainReveal.tsx` (full), `TrainSolveScreen.tsx` (135-2158), `TrainBotStepper.tsx`, `TrainLineStepper.tsx` (header/props)
- `frontend/src/hooks/useAnalysisBoard.ts` (full), `useTrainFreePlay.ts` (full), `useTrainWalkthrough.ts` (full), `useTrainPuzzleTelemetry.ts` (full), `useTrainOnboarding.ts`, `trainGradingSupport.ts` (80-165), `useStockfishEngine.ts` (options), `useBoardNavigationInput.ts` (header/keys)
- `frontend/src/lib/trainArrows.ts` (160-560), `trainBotCopy.ts` (205-620), `trainTelemetry.ts` (full), `trainRevealCache.ts` (full), `mobileBoardControls.ts` (full), `analytics.ts` (340-530), `trainScore.ts` (20-71)
- `frontend/src/components/board/ChessBoard.tsx` (arrow overlay), `boardMarkers.tsx` (SquareMarker), `HorizontalMoveList.tsx`, `components/analysis/VariationTree.tsx` (props, sibling blocks, MobileTree), `EngineLines.tsx` (props), `App.tsx` (MobileBottomBar, layout)
- `app/schemas/train.py` (185-440, 672-691), `app/routers/train.py` (review route), `tests/schemas/test_train_telemetry_parity.py`, `tests/schemas/test_train_telemetry_schema.py`
- `.planning/sketches/008-train-reveal-mobile-layout/index.html` (tree, chips, arrows, strip, desktop functions), README, MANIFEST §008, SEED-194, 237-CONTEXT.md, 237-DISCUSSION-LOG.md
- `frontend/eslint.config.js`, `frontend/package.json`, installed package versions

### Secondary / Tertiary
- None. No external documentation was needed; no web research performed.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH (no new packages; versions read from node_modules)
- Architecture: MEDIUM-HIGH (API gaps and seams verified in code; the recommended hook design is reasoned, not prototyped)
- Pitfalls: HIGH (each tied to a specific line read this session)

**Research date:** 2026-10-09
**Valid until:** 2026-11-08 (in-repo facts; re-check if Phase 236 follow-ups touch `TrainSolveScreen.tsx`)
