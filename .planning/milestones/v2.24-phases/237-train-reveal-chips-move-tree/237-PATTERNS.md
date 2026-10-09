# Phase 237: Train Reveal Verdict Strip, Line Chips & One Move Tree - Pattern Map

**Mapped:** 2026-10-09
**Files analyzed:** 27 (new + modified + deleted)
**Analogs found:** 25 / 27

All paths below are git-tracked source under `frontend/src/` (unless `app/` or `tests/`). Line numbers verified 2026-10-09 against `main` (79a2c6bc7).

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `hooks/useAnalysisBoard.ts` (+`graftLine`) | hook | transform (tree state) | same file `playUciLine` :634-680 | exact |
| `hooks/useTrainRevealTree.ts` (NEW) | hook | event-driven (user nav + engine) | `hooks/useTrainFreePlay.ts` | exact |
| `hooks/useTrainFreePlay.ts` (DELETE/slim) | hook | — | absorbed into `useTrainRevealTree` | — |
| `lib/trainRevealLines.ts` (NEW, pure) | utility | transform | `TrainReveal.tsx` `buildLineBoxes` :287-353 | exact (lift) |
| `lib/trainArrows.ts` (focus overlay) | utility | transform | same file `applyTrainSpotlight` ~:500-540 | exact |
| `components/board/ChessBoard.tsx`, `components/board/boardMarkers.tsx` (+`opacity`) | component | render | `ArrowOverlay` ChessBoard.tsx:133-138,:233,:246; `SquareMarkerGroup` boardMarkers.tsx:288 | exact |
| `lib/theme.ts` (dim constants) | config | — | existing opacity constants in theme.ts | exact |
| `lib/trainBotCopy.ts` (`verdictClause`, `verdictClauseParts`, `walkthroughCopy`) | utility | transform | same file :405-419, :526-533 | exact |
| `lib/trainTelemetry.ts` (+`REVIEW_TELEMETRY_SCHEMA_VERSION`) | config/utility | batch | same file :14-41 | exact |
| `types/train.ts` (`ReviewTelemetry` v2) | model | — | same file :220 | exact |
| `hooks/useTrainPuzzleTelemetry.ts` (chips/strip/forked counters) | hook | event-driven | same file (card counters) | exact |
| `app/schemas/train.py` (`ReviewTelemetry v: Literal[1,2]` + validator) | model (Pydantic) | request-response | same file :380-400 | exact |
| `tests/schemas/test_train_telemetry_parity.py` | test | — | same file `_MIRRORED_CONSTANTS` :26-32 | exact |
| `tests/schemas/test_train_telemetry_schema.py` | test | — | same file :64, :89-104 | exact |
| `lib/trainRevealCache.ts` (+`revealTree`) | utility | file-I/O (sessionStorage) | same file `isCachedTrainReveal` :99-119 | exact |
| `lib/mobileBoardControls.ts` (+train payload fields) | store | pub-sub | same file :77-105 (`onResign` precedent) | exact |
| `App.tsx` `MobileBottomBar` (train branch) | component | pub-sub reader | App.tsx:487-505 `BotGameMobileBar` swap | exact |
| `lib/analytics.ts` (`train-sideline-fork`, `train-verdict-strip`; drop `train-explore-exit`) | config | — | `ACTION_TARGETS` :384-402 | exact |
| `hooks/useBoardNavigationInput.ts` (+optional `goHome`) | hook | event-driven | same file :140 | exact |
| `hooks/useTrainWalkthrough.ts` (re-pointed auto-advance) | hook | event-driven | same file :26-27, :94-103, :157-186 | exact |
| `components/train/TrainVerdictStrip.tsx` (NEW) | component | render | `TrainBotBubble.tsx` + `TrainScoreChip` (TrainReveal.tsx:418) | role-match |
| `components/train/TrainVerdictDetails.tsx` (NEW) | component | render | `renderVerdictBubbleBody` TrainSolveScreen.tsx:377-436 + Your-call card TrainReveal.tsx:1405-1458 | exact (extract) |
| `components/train/TrainLineChips.tsx` (NEW) | component | render | line-box header in `TrainReveal.tsx` (role mark + SAN + eval) | role-match |
| `components/train/TrainMoveTreeList.tsx` (NEW) | component | render | `components/analysis/VariationTree.tsx` (`variant` override :1085-1095) + `EngineLines compact` | exact |
| `components/train/TrainRevealActionBar.tsx` (NEW) | component | event-driven | `BotGameMobileBar` (App.tsx) + `BoardControls.tsx` | role-match |
| `components/train/TrainRevealGameFooter.tsx` (NEW) | component | render | extract TrainReveal.tsx:1525-1573 | exact (extract) |
| `components/train/TrainReveal.tsx`, `TrainSolveScreen.tsx`, `pages/Train.tsx` | component/page | composition | themselves | — |
| `components/train/TrainLineStepper.tsx` + test (DELETE) | — | — | — | — |
| Tests: `hooks/__tests__/useTrainRevealTree.test.ts`, `lib/__tests__/trainRevealLines.test.ts`, `components/train/__tests__/TrainVerdictStrip.test.tsx` (NEW) | test | — | `hooks/__tests__/useTrainFreePlay.test.ts`, `useAnalysisBoard.test.ts`, `TrainBotBubble.test.tsx` | exact |

## Pattern Assignments

### `hooks/useAnalysisBoard.ts` — add `graftLine(uciMoves, parentId)`

**Analog:** `playUciLine` in the same file, lines 634-680. Copy its body verbatim except: start from `parentId` arg (null = `prev.rootFen`), never write `currentNodeId`, return `prev` when `id === prev.nextId`.

```typescript
const playUciLine = useCallback((uciMoves: string[]): void => {
  unlockAudioOnce();
  if (uciMoves.length === 0) return;
  setState((prev) => {
    const newNodes = new Map(prev.nodes);
    let parentId: NodeId | null = prev.currentNodeId;
    const parentFen =
      parentId !== null ? (newNodes.get(parentId)?.fen ?? prev.rootFen) : prev.rootFen;
    const chess = new Chess(parentFen);
    let id = prev.nextId;
    ...
      const promotion = uci.length > 4 ? uci.slice(4, 5) : 'q';
      let move: ReturnType<typeof chess.move>;
      try { move = chess.move({ from, to, promotion }); } catch { break; }
      if (!move) break;
      // Reuse an existing child with the same from/to to avoid duplicate branches.
      let child: MoveNode | undefined;
      for (const node of newNodes.values()) {
        if (node.parentId === parentId && node.from === move.from && node.to === move.to) { child = node; break; }
      }
      if (!child) { child = buildNode(id, move.san, chess.fen(), move.from, move.to, parentId); newNodes.set(id, child); id++; }
    ...
    if (landingId === prev.currentNodeId) return prev; // nothing grafted — no-op
    return { ...prev, nodes: newNodes, currentNodeId: landingId, nextId: id };
```
Depth gate: extract the child-search loop into a module-level `findChild(nodes, parentId, from, to)` helper (also used by `walkLinePath`) to stay at max-depth 4. Target skeleton in RESEARCH.md "Code Examples" (lines 492-532). Do not call `unlockAudioOnce` (no sound on silent graft). Never use `clearAllSidelines` (deletes the other known lines).

Tests: add cases to `hooks/__tests__/useAnalysisBoard.test.ts` (graft reuses child, `currentNodeId` unchanged, unknown parent = no-op).

---

### `hooks/useTrainRevealTree.ts` (NEW, hook, event-driven)

**Analog:** `hooks/useTrainFreePlay.ts` (whole file; read once before writing). Carry over:
- Root seed: `loadMainLine([], puzzle.fen)` (useTrainFreePlay.ts:415, :446) — leave `mainLine` empty; semantics come from derived `linePaths`.
- Engine contract: `useStockfishEngine` options at :254-258; re-search at new MultiPV without restarting (useStockfishEngine.ts:66-70). New gate: `enabled = verdict landed && instantGrade?.status !== 'pending'` (TrainSolveScreen.tsx:1472 `showEvalBar` rule), `multiPv = isOffLine ? max(2, sfArrows) : 1`.
- Grading: `evalByFen` FIFO cache, root seed from `gradeResult` (:283-292), parent-eval lookup (:331-332), D-06 vetted root shortcut (:359-362), `qualityByNode`, `markerEntryForQuality`. Keep the Phase 211 D-06 header comment verbatim.
- Focus derivation (`rootFocus` + path) and forward rule: RESEARCH Pattern 3; use `goToNode`, never `goForward` (lowest-id rule, useAnalysisBoard.ts:344-360).
- Keyboard: call `useBoardNavigationInput` with a desktop board-wrapper ref (inert while ref null).
- All graft work through functional `setState` (Pitfall 2; `stateRef` syncs after render, useAnalysisBoard.ts:251-253).

Tests: port `hooks/__tests__/useTrainFreePlay.test.ts` cases into `hooks/__tests__/useTrainRevealTree.test.ts` (renderHook + mocked `useStockfishEngine` pattern in that file).

---

### `lib/trainRevealLines.ts` (NEW, pure utility)

**Analog:** `components/train/TrainReveal.tsx` `buildLineBoxes` (:287-353) plus constants :83, :97, :105. Lift verbatim, rename `buildChipGroups`.

```typescript
type RoleKey = 'your' | 'best' | 'game';                          // :83
const CANONICAL_ROLE_ORDER: readonly RoleKey[] = ['your', 'best', 'game']; // :97
const MAX_LINE_PLIES = 12;                                        // :105

function buildLineBoxes(
  puzzleFen: string,
  playedMoveUci: string | null,
  gradeResult: GradeResult | null,
  instantGrade: InstantGradeState | null,
  gameMoveUci: string | null,
  playedMoveQuality: TrainMoveQuality | null,
  gameMoveQuality: TrainMoveQuality | null,
  movePoints: number,
): LineBox[] {
  const uciByRole: Partial<Record<RoleKey, string>> = {};
  // Phase 236: on the instant path the verdict lands before the phone grade ...
  if ((gradeResult !== null || instantGrade !== null) && playedMoveUci !== null) {
```
Keep grouping `CANONICAL_ROLE_ORDER.filter((r) => uciByRole[r] === uci)`, `pending: 'loading' | 'failed' | null`, label `roles.map(short).join(' = ')`. Add `walkLinePath(nodes, uciMoves)` (RESEARCH :519-532). Port `buildLineBoxes` cases from `components/train/__tests__/TrainReveal.test.tsx` into `lib/__tests__/trainRevealLines.test.ts`.

---

### `lib/trainArrows.ts` — replace filter with dim (`buildChipFocusOverlay`)

**Analog:** `applyTrainSpotlight`, same file, end of function at :520-540. Keep `matchesActivePair` (square match) and `ownsMarkerSquare` (WR-02 owner match) verbatim; change only the return:

```typescript
  function ownsMarkerSquare(square: string): boolean {
    const ownerUci = overlay.markerOwners[square];
    return ownerUci !== undefined && activeUciSet.has(ownerUci);
  }
  return {
    ...overlay,
    arrows: overlay.arrows.filter(matchesActivePair),        // -> .map(a => ({...a, opacity: lit ? LIT : DIM, onTop: lit}))
    markers: overlay.markers.filter((marker) => ownsMarkerSquare(marker.square)), // -> .map(... opacity)
  };
```
Set `onTop` on lit arrows and clear it on a dimmed game arrow (game arrow built with `onTop: true`, :461-467). Keep `buildTrainStepArrows/Markers` and `buildTrainFreePlayArrows` for non-root nodes. Delete `applyTrainSpotlight`, `trainGlyphColor` when unused (knip). Rewrite spotlight block in `lib/__tests__/trainArrows.test.ts`.

---

### `components/board/ChessBoard.tsx` + `components/board/boardMarkers.tsx` — optional `opacity`

**Analog:** existing opacity computation, ChessBoard.tsx:133-138 (`const ARROW_OPACITY = 0.75;`, `const ARROW_LOW_EMPHASIS_OPACITY = 0.30;`), :246 `opacity={arrow.isHovered ? ARROW_HOVER_OPACITY : baseOpacity}`. Add `opacity?: number` to `BoardArrow` (ChessBoard.tsx:17) and `SquareMarker` (boardMarkers.tsx:37); use `arrow.opacity ?? baseOpacity`, and wrap `SquareMarkerGroup` output in `<g opacity={marker.opacity ?? 1}>` (:288). Dim factors (sketch: arrows 0.22/0.92, badges 0.32/1) go in `lib/theme.ts` as named constants.

---

### `lib/trainBotCopy.ts` — D-05/D-06 vocabulary + tour

**Analog:** same file :405-419 (current table):
```typescript
function verdictClause(correctGuess: boolean, moveQuality: TrainMoveTier): string {
  if (correctGuess && moveQuality === 'good') return 'Right call [+1], right move [+2].';
  if (correctGuess && moveQuality === 'inaccuracy') return 'Right call [+1], decent move [+1].';
  if (correctGuess) return 'Right call [+1], wrong move [+0].';
  if (moveQuality === 'good') return 'Wrong call [+0], but the right move [+2].';
  if (moveQuality === 'inaccuracy') return 'Wrong call [+0], decent move [+1].';
  return 'Wrong call [+0], wrong move [+0].';
}
```
Keep guard-clause style (no nesting), add `isBest: boolean` arg; move `verdictClauseParts` from TrainSolveScreen.tsx:346-361 into this file and drive both from one table (Pitfall 12). Points still passed in from `scorePuzzle` (never derived). Tour: `WalkthroughStep`/`WALKTHROUGH_STEP_COUNT` :526-527, `spotlightTarget` union :533, `STEPPER_COPY_MAX_CHARS = 145` :219; signature `walkthroughCopy(step, hasAnalyze, mergedChip)`. Update tests `lib/__tests__/trainBotCopy.test.ts` :257-262, :359, :366.

---

### `lib/trainTelemetry.ts` + `types/train.ts` + `hooks/useTrainPuzzleTelemetry.ts`

**Analog:** trainTelemetry.ts:14 `export const TELEMETRY_SCHEMA_VERSION = 1;`, :26 `export const TELEMETRY_CARDS_CAP = 10;`. Add `export const REVIEW_TELEMETRY_SCHEMA_VERSION = 2;` as a plain integer literal (the parity test regex `export\s+const\s+NAME\s*=\s*(\d+)\s*;` requires it). Do NOT change `TELEMETRY_SCHEMA_VERSION` (Pitfall 4). Remove `CardEngageKind`, `REVIEW_CARD_HOVER_MIN_MS` once unused. `types/train.ts:220` `v: 1` -> v2 shape with `review_chips_selected`, `review_chips_total`, `review_strip_expanded`.

### `app/schemas/train.py` — `ReviewTelemetry` v2

**Analog:** same class :380-400:
```python
    model_config = ConfigDict(extra="forbid")
    # Must equal TELEMETRY_SCHEMA_VERSION (a Literal cannot reference the constant).
    v: Literal[1]
    exit: Literal["next", "pagehide"]
    review_ms: TelemetryDurationMs | None = None
    ...
    review_cards_opened: TelemetryCardCount | None = None
    review_cards_total: TelemetryCardCount | None = None
    review_explored: StrictBool | None = None
```
Add `REVIEW_TELEMETRY_SCHEMA_VERSION: Final = 2` next to `TELEMETRY_SCHEMA_VERSION: Final = 1` (:195), `v: Literal[1, 2]`, three new optional fields, and the `model_validator(mode="after")` from RESEARCH :536-556 (ValueError -> plain 422, no Sentry). Docstring: `review_strip_expanded` is phone-only.

### `tests/schemas/test_train_telemetry_parity.py` / `test_train_telemetry_schema.py`

**Analog:** parity :26-32 — append `("REVIEW_TELEMETRY_SCHEMA_VERSION", REVIEW_TELEMETRY_SCHEMA_VERSION)` to `_MIRRORED_CONSTANTS`. Schema test :64 currently lists `{"v": 2, "exit": "next"}` as must-reject; move it to accepted and add cross-version reject cases. Keep the solve-telemetry `v: 2` rejection (:89-104 behaviour).

---

### `lib/trainRevealCache.ts` — optional `revealTree`

**Analog:** `isCachedTrainReveal` :99-119 (shallow structural check, "not a license to deep-validate"). Add `revealTree?: { rootFocus: RoleKey | null; currentPath: string[]; sidelinePaths: string[][] }`; validate loosely and drop the field (not the entry) when malformed. Persist UCI paths, never node ids (Pattern 10). Tests: `lib/__tests__/trainRevealCache.test.ts`.

---

### `lib/mobileBoardControls.ts` + `App.tsx` `MobileBottomBar`

**Analog:** `usePublishMobileBoardControls` :77-105, with `onResign` as the optional-field precedent:
```typescript
    // No default — undefined is the meaningful "not the bot bar" value.
    onResign,
  } = controls ?? {};
  const hasControls = controls != null;
  useEffect(() => {
    if (!hasControls) return;
    setPayload({ onBack, onForward, onReset, onFlip, canGoBack, canGoForward, canReset, onResign });
    return () => setPayload(null);
  }, [hasControls, onBack, onForward, onReset, onFlip, canGoBack, canGoForward, canReset, onResign]);
```
Add optional `onNext`, `analyzeTo`, `onAnalyzeClick`, `highlight` the same way (destructure without default, list each in deps, never `controls` itself). Reader: App.tsx:487-505 branch `boardControls.onResign != null ? <BotGameMobileBar .../> : <BoardControls .../>` — add a `boardControls.onNext != null ? <TrainRevealActionBar .../>` branch first. Publish for the whole reveal (`showResultRow && verdict !== null`), replacing TrainSolveScreen.tsx:968-991 `freePlay.isExploring ? {...} : null`.

### `components/train/TrainRevealActionBar.tsx` (NEW)

**Analog:** `BotGameMobileBar` (App.tsx import, four-action bar) and `components/board/BoardControls.tsx` (keep `board-btn-*` testids, `aria-label` on icon buttons, flip fires `board-tool flip` at BoardControls.tsx:218). Analyze stays a router `<Link>` with `onClick={handleAnalyzeFromReveal}` + `trackFeature` (no `data-umami-event`), `btn-train-analyze` / `btn-train-next`; `Button` variants `brand-outline` / `default`. Three hosts: phone bottom bar, `hidden sm:block lg:hidden` in-flow (precedent TrainReveal.tsx:596-598), desktop under board.

---

### `components/train/TrainVerdictDetails.tsx` / `TrainVerdictStrip.tsx` (NEW)

**Analogs:** extract `renderVerdictBubbleBody` (TrainSolveScreen.tsx:377-436) and the Your-call card body (TrainReveal.tsx:1405-1458) into `TrainVerdictDetails`, keeping testids `train-bot-verdict-line`, `train-bot-pill-guess`, `train-bot-pill-move`, `train-bot-look-closer`, `train-bot-return-tail`, `train-verdict-guess-prose`, `train-reveal-also-fine`, `train-reveal-motif`. Strip total pill reuses `TrainScoreChip` (TrainReveal.tsx:418):
```tsx
export function TrainScoreChip({ points, testid }: { points: number; testid: string }): ReactElement {
  return (
    <span className="shrink-0 rounded-full px-2 py-0.5 text-sm font-semibold text-white"
      style={{ backgroundColor: points > 0 ? TRAIN_VERDICT_CORRECT : TRAIN_VERDICT_INCORRECT }}
      data-testid={testid}>+{points}</span>
  );
}
```
Move `TrainScoreChip` into its own file or `TrainVerdictDetails.tsx` when TrainReveal.tsx is split. Strip = semantic `<button aria-expanded>` (`data-testid="train-verdict-strip"`), collapsed by default (D-08), fires `trackFeature('panel-open', 'train-verdict-strip')` only on collapsed->open in the click handler. Desktop host = `TrainBotBubble` (has `ring`). Test analog: `components/train/__tests__/TrainBotBubble.test.tsx`.

### `components/train/TrainLineChips.tsx` (NEW)

**Analog:** the line-box header rendering in TrainReveal.tsx (role mark + SAN + eval, `data-line-status` for Phase 236 pending/failed). Testids `train-chip-{primaryRole}` (never SAN), `<button>` per chip, `text-sm` minimum. SAN-only game move (TrainReveal.tsx:1494-1498) renders non-interactive.

### `components/train/TrainMoveTreeList.tsx` (NEW)

**Analog:** `components/analysis/VariationTree.tsx` :1085-1095 variant override:
```tsx
export function VariationTree(props: VariationTreeProps) {
  // `variant='vertical'` forces the paired vertical list at every width ...
  if (props.variant === 'vertical') {
    return (<div data-testid="analysis-variation-tree" aria-label="Move list" ...
```
Add `variant: 'wrap'` forcing `MobileTree` at every width (sidelines in parentheses, × with `btn-delete-line-{rootId}` firing `board-tool line-delete` at :689, `flawMarkerByNodeId` for grading markers). Pass a view: `mainLine = activeLinePath`, nodes filtered to the active line + free subtrees + free root forks (MobileTree renders `nearestMainIdx === -1` blocks before move 1, :743). Stockfish row = `EngineLines compact maxLines={expanded ? 2 : 1}` shown only when `isOffLine`.

---

### `components/train/TrainSolveScreen.tsx` (modify)

Key seams (from RESEARCH): drop handler :1356-1406 keep order `guess === null` -> nudge; post-verdict -> `if (verdict === null) return false; return tree.playMove(source, target);` (SOLV-02, keep the comment block); overlay switch :1609-1613 collapses to tree-driven overlay; `revealBestUci` :1507 is the `isBest` predicate; walkthrough `lastControl` :449-479 becomes `null` + bar `highlight`; eval-bar engine :1472-1483 merges into the reveal engine.

### `hooks/useTrainWalkthrough.ts`

**Analog:** same file; gate :94-103 (`reveal_walkthrough_seen_at !== null` -> null), auto-advance :26-27/:157-173 re-pointed to chip tap / tree step, `leave()` stamps on last step :182-186 (call it from the bar's Next/Analyze).

### `lib/analytics.ts`

**Analog:** `ACTION_TARGETS` :384-402. Add `'train-sideline-fork'` (action) and `'train-verdict-strip'` to the panel targets list; remove `'train-explore-exit'` (removal, not rename); keep `'train-solution'` for ⏮. Fire from user handlers only.

### `hooks/useBoardNavigationInput.ts`

**Analog:** same file :140 `if (e.key !== 'ArrowLeft' && e.key !== 'ArrowRight') return;` — add optional `goHome` handling `Home` before that guard; additive for Analysis/Openings.

## Shared Patterns

### Functional setState for tree mutations
**Source:** `hooks/useAnalysisBoard.ts:634-680` (`playUciLine`). **Apply to:** `graftLine`, seeding, restore replay. One `setState((prev) => ...)` per graft; chess.js `move()` in try/catch with `break`.

### Optional-field payload extension
**Source:** `lib/mobileBoardControls.ts:77-105` (`onResign`). **Apply to:** `MobileBoardControls`, `BoardArrow.opacity`, `SquareMarker.opacity`, `CachedTrainReveal.revealTree`, `useBoardNavigationInput` `goHome`: all additive, undefined = old behaviour.

### Mirrored telemetry constants
**Source:** `tests/schemas/test_train_telemetry_parity.py:26-44` + `lib/trainTelemetry.ts:14-31` + `app/schemas/train.py:195-203`. **Apply to:** `REVIEW_TELEMETRY_SCHEMA_VERSION` (plain integer literal both sides).

### Pydantic boundary
**Source:** `app/schemas/train.py:380-400` (`extra="forbid"`, `StrictBool`, clamped type aliases, `Literal`). Expected-invalid bodies -> 422, no `sentry_sdk.capture_exception`.

### Umami
**Source:** `lib/analytics.ts` target registries (:361, :384-402), `VariationTree.tsx:689`, `BoardControls.tsx:218`. Register first, fire from handlers, never rename, no SAN/FEN in targets.

### Testids / a11y / styling (frontend/CLAUDE.md)
Kebab-case component-prefixed `data-testid` on every interactive element; `aria-label` on icon-only buttons; `Button` variants; min `text-sm`; colors and opacity factors from `lib/theme.ts`; `noUncheckedIndexedAccess` narrowing; eslint `max-depth` 4.

## No Analog Found

| File | Role | Data Flow | Reason |
|---|---|---|---|
| Chip-focus derivation (`rootFocus` + path) inside `useTrainRevealTree` | hook logic | derived state | New logic; use RESEARCH Pattern 3 and sketch `case 'chip'` |
| Shared test helper `waitForReveal()` | test utility | — | No existing reveal sentinel helper; key on `train-reveal` testid (replaces 96 `train-verdict-guess` waits) |

## Metadata

**Analog search scope:** `frontend/src/{hooks,lib,components/train,components/board,components/analysis}`, `frontend/src/App.tsx`, `app/schemas/train.py`, `tests/schemas/`
**Files scanned:** ~20 (most line refs cross-checked against RESEARCH.md, which read them in full)
**Pattern extraction date:** 2026-10-09
