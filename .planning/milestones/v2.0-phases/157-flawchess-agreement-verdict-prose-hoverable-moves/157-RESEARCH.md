# Phase 157: FlawChess Agreement Verdict (prose + hoverable moves) - Research

**Researched:** 2026-07-07
**Domain:** React/TypeScript frontend — pure verdict-classification module + interactive prose UI, reusing shipped Phase 151-156 patterns. No backend, no new dependencies.
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** The verdict compares **FlawChess practical #1** (`flawChessEngine.rankedLines[0]`: `rootMove`, `practicalScore`, `objectiveEvalCp`) against **Stockfish objective #1** — the *true* Stockfish PV, `engine.pvLines[0]` (`moves[0]` + `evalCp`/`evalMate`). NOT the `engineTopLines[0]` memo, which silently degrades to a FlawChess row when Stockfish is off.
- **D-02:** The verdict renders **only when standalone Stockfish is on** (`engineEnabled === true`) **and** FlawChess has produced a snapshot. When `engineEnabled` is false there is no true objective #1, so no comparison is shown — avoids a misleading FlawChess-vs-itself read. (Both toggles default to `true`, so the common case is both engines running and the verdict well-defined.)
- **D-03:** When Stockfish is off, the fixed-height verdict slot shows a **muted prompt line**: `Turn on Stockfish to compare picks.` (mirrors `positionVerdict`'s help-text fallback; keeps the slot non-jumping).
- **D-04:** **`aligned`** = FlawChess #1 `rootMove` and Stockfish #1 move are the **same UCI move**.
- **D-05:** On divergence (different moves), split by the **objective eval sacrificed** measured as a **win-probability drop from the mover's POV**: convert both objective evals to win% via the engine's existing lichess sigmoid, `drop = winpct(SF#1_objective) − winpct(FC#1_objective)`. `safe` = `0 < drop < BLUNDER_DROP` (0.15); `sharp (trap)` = `drop ≥ BLUNDER_DROP` (0.15). Reuses the app-wide flaw-threshold scale (`src/generated/flawThresholds.ts`) rather than a fresh cp constant — self-calibrating near 0.0 vs ±5.0. Give the threshold a **named constant** in the verdict module (no bare 0.15).
- **D-06:** By construction the FlawChess practical #1 can never be objectively better than Stockfish's objective max, so `drop` is always `≥ 0`. If **either objective eval hasn't arrived yet** mid-search (`objectiveEvalCp`/PV eval null), fall back to the loading/help line — never emit a bogus tier from a partial snapshot. The tier **refines live** with the search inside the fixed-height slot (no layout jump).
- **D-07:** **Brand voice** — Stockfish framed as objective/flawless, FlawChess as the human-playable pick. Use **neutral "for a human here"** phrasing (NOT "you"/"your opponent") so the line reads correctly regardless of side to move. Draft templates (exact wording finalized in implementation):
  - aligned: *"Both agree on `Nf3` — objectively +0.4, and the practical pick too."*
  - safe: *"Objectively `Qb3` (+0.6). But for a human here, FlawChess plays `Nf3` (+0.3) — barely any cost, far easier."*
  - sharp (trap): *"`Qb3` is objectively best (+2.1) but it's a trap for humans. FlawChess plays the safer `Nf3` (+0.4) instead."*
- **D-08:** No UI string reads a bare "best move" unqualified (REVIEW-02 / ARROW-04 principle). Move names are the interactive spans (`ProseMoveSpan` mechanics).
- **D-09:** Hovering a verdict move span **isolates** that pick's board arrow: show ONLY the hovered move's arrow in its tier color (**amber = FlawChess pick** `FLAWCHESS_ENGINE_ARROW`, **blue = Stockfish pick** `BEST_MOVE_ARROW`), overriding the default persistent two-arrow layer; on leave, both arrows return. Reuse the exact `qualityHoverArrows` lift-overlay plumbing (`onHoverMovesChange` → an overlay that wins over `engineArrows`), same as `MaiaMoveQualityBar`.
- **D-10:** Popover anchors to the hovered span (`ProseMoveSpan` mechanics: hover-intent delay, content-bridge, outside-click/Escape close). Content is **engine-labeled, two lines**:
  ```
  FlawChess: +0.3 (practical)
  Stockfish: +0.4 (objective)
  ```
  Per hovered move: FlawChess pick shows both (it's a ranked line with an objective eval). Stockfish pick always shows the Stockfish line, and a FlawChess line **only if** the engine also ranked that move (`rootMove` match in `rankedLines`) — otherwise **omit the FlawChess line** (no `—` placeholder, no invented number).
- **D-11:** Clicking a span plays that move as a **free move** on the board — reuse the existing `onPlayMove(san)` wiring (as `MaiaMoveQualityBar` does). "Hover shows, click plays" on desktop; "first tap shows, second tap plays" on touch — inherited from `ProseMoveSpan`.

### Claude's Discretion

- **Module + placement:** mirror `positionVerdict.ts` with a new **pure, worker-free `flawChessVerdict.ts`** (tier enum + named constants + a `VerdictMove`-like shape + a `formatVerdictEval`-style helper). Render the verdict as a **separate component** in the FlawChess `CardBody`, *below* `FlawChessEngineLines` — do NOT fold cross-engine Stockfish data into `FlawChessEngineLines` (it's documented as an `EngineLines` sibling, body-only). Planner may choose exact file/prop names.
- Exact prose wording, eval formatting reuse (`formatVerdictEval` M-notation vs the card's `formatScore`), and popover markup styling are left to implementation, consistent with the reused patterns.

### Deferred Ideas (OUT OF SCOPE)

- **Played-move vs practical-best comparison (game review)** → already captured as **SEED-086**. Anchored on the move the user actually played; out of scope here (this phase compares the two engines, not the played move).
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| REVIEW-02 | The FlawChess Engine card surfaces a prose agreement verdict — whether its top practical move agrees or diverges from Stockfish's top objective move, citing both evals, with the named moves hoverable (arrow + popover) and click-to-play. Reframed 2026-07-07 from "what you played vs practical best" (that game-review-only comparison is now SEED-086). | `flawChessVerdict.ts` mirror pattern (Pattern 1) + `ProseMoveSpan` mirror (Pattern 2) + existing arrow/hover plumbing (Pattern 3) fully cover D-01 through D-11; see Architecture Patterns and Code Examples |
| REVIEW-01 | The engine runs on the game-review board (whole game via `?game_id&ply`) as well as in free analysis (satisfied incidentally by the shared `Analysis.tsx`; Phase 157 confirms end-to-end parity there). | `flawChessCard` (Analysis.tsx L1476-1515) is defined once and rendered identically in both the mobile `humanTab` (L1532) and the desktop human column (L1712) — a single edit site satisfies both surfaces by construction; see System Architecture Diagram and Recommended Project Structure |

</phase_requirements>

## Summary

This phase is almost entirely a **reuse-and-mirror** exercise: two established patterns already ship on `/analysis` and need to be extended, not invented. `frontend/src/lib/positionVerdict.ts` is the exact template for the new pure classification module (`flawChessVerdict.ts`); `frontend/src/components/analysis/MaiaMoveQualityBar.tsx`'s `ProseMoveSpan` is the exact template for the hoverable/click-to-play move span. Both the data (`RankedLine`, `PvLine`) and the arrow/hover plumbing (`engineArrows`, `qualityHoverArrows`, `onHoverMovesChange` → `setHoveredQualityMoves`) already exist in `Analysis.tsx` and were built for exactly this purpose. The single insertion point — inside the FlawChess Engine's `CardBody`, directly below `FlawChessEngineLines` — is used identically by both desktop and mobile layouts because `Analysis.tsx` defines `flawChessCard` once (~L1476) and renders that same JSX in two places, so there is only one edit site for SC4 (game-review parity) to hold automatically.

The one genuine risk is that the two patterns aren't perfectly copy-paste compatible: `ProseMoveSpan` is a **module-private** function (not exported) and its popover body **hardcodes Maia-specific content** (`{move.maiaPct}% at this rating · ${evalText}`), which does not match D-10's required two-line "FlawChess: … (practical) / Stockfish: … (objective)" format. The planner must decide whether to extract-and-generalize the interaction *shell* (open/close state machine, hover-intent timer, content-bridge, click-vs-reveal logic) into a shared, content-agnostic component, or duplicate the ~60-line shell into the new file with different content. Reusing `interleaveWithConjunction`/`joinMoveNames` is **not needed** — unlike Maia's variable-length move lists, this phase's three tier templates each name exactly 1 or 2 fixed moves.

A second finding worth flagging: **ROADMAP.md's Phase 157 SC1 text contradicts CONTEXT.md's D-01.** SC1 says the verdict sources "the primary Stockfish PV, `engineTopLines[0]`, not the max-objective FlawChess row" — but `engineTopLines` (Analysis.tsx L682-700) is a memo that **silently degrades to FlawChess rows when Stockfish is off**, which is precisely what D-01 warns against and instructs the planner to avoid by using `engine.pvLines[0]` directly. CONTEXT.md is the later, deliberated, more specific source — follow **D-01** (`engine.pvLines[0]`), not the ROADMAP's looser SC1 wording. (Moot in practice for D-02's degradation case since the verdict never renders when Stockfish is off, but `engine.pvLines[0]` is architecturally the correct source either way.) Likewise, ROADMAP's SC2 popover format ("practically X · objectively Y") is superseded by CONTEXT.md D-10's engine-labeled two-line format — CONTEXT.md's own `<specifics>` section already flags this override explicitly.

**Primary recommendation:** Build `frontend/src/lib/flawChessVerdict.ts` as a pure module mirroring `positionVerdict.ts`'s shape (tier type, named constants from `flawThresholds.ts`, a `FlawChessVerdictMove`-like interface, an eval-formatter). Feed it SANs pre-converted by `Analysis.tsx`'s existing (currently module-private) `bestSanFromPv` helper — do not push chess.js/FEN logic into the pure module. Render a new sibling component below `FlawChessEngineLines` inside the existing `flawChessCard` JSX (~L1504-1511), wiring its hover callback to the *already-existing* `setHoveredQualityMoves` setter (same `HoveredQualityMove[] | null` shape `qualityHoverArrows` already consumes) and its click callback to the *already-existing* `playProseMove` (L513-520).

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Verdict tier classification (aligned/safe/sharp) | Browser / Client (pure lib module) | — | Pure function of already-fetched engine data (`RankedLine`, `PvLine`), no I/O — belongs in `frontend/src/lib/`, mirrors `positionVerdict.ts` |
| Prose rendering + interactive spans | Browser / Client (React component) | — | Presentational, consumes the pure module's output; lives in `frontend/src/components/analysis/` |
| Board arrow isolation on hover | Browser / Client (`Analysis.tsx` state + `ChessBoard`) | — | Already-shipped `qualityHoverArrows` overlay mechanism (Phase 151.1/155); the new component only *feeds* it via a callback, does not own arrow rendering |
| Popover eval display | Browser / Client (Radix Popover primitives) | — | No new UI primitive needed; `@/components/ui/popover` already used identically by `ProseMoveSpan` |
| Click-to-play | Browser / Client (`Analysis.tsx`'s `makeMove`/board-tree state) | — | Reuses existing `playProseMove` → `makeMove` wiring, no new mutation path |
| Engine data (FC ranked lines, SF PV) | Browser / Client (`useFlawChessEngine`, `useStockfishEngine` — client-side WASM/MCTS workers) | — | No backend involvement anywhere in this milestone (D-4 lock, v1.29); this phase adds zero new data sources |

No API/Backend/Database/CDN tier involvement — this is a 100% client-side presentational feature over data that already exists on the page.

## Standard Stack

No new libraries. Everything is already a dependency in `frontend/package.json` (React 19, Radix `Popover` primitives via `@/components/ui/popover`, `chess.js` for SAN/UCI conversion, Tailwind for styling). No `npm install` required.

### Package Legitimacy Audit

Not applicable — this phase installs no new packages. Skip the gate.

## Architecture Patterns

### System Architecture Diagram

```
                    ┌─────────────────────────────────────────┐
                    │             Analysis.tsx (page)          │
                    │                                           │
  useStockfishEngine│  engine.pvLines[0]  (Stockfish PV,       │
  (position FEN) ───┼─▶  {moves, evalCp, evalMate})            │
                    │           │                               │
                    │           ▼                               │
                    │   bestSanFromPv(position, uci)  (SAN)     │
                    │           │                               │
  useFlawChessEngine│  flawChessEngine.rankedLines[0]           │
  (position FEN) ───┼─▶ (RankedLine: rootMove, practicalScore,  │
                    │    objectiveEvalCp)                        │
                    │           │                               │
                    │           ▼                               │
                    │   bestSanFromPv(position, uci)  (SAN)     │
                    │           │                               │
                    │           ▼                               │
                    │  ┌──────────────────────────────┐         │
                    │  │  flawChessVerdict.ts (NEW,     │         │
                    │  │  pure lib module)               │         │
                    │  │   - evalToExpectedScore()        │        │
                    │  │     (existing, @/lib/liveFlaw)   │        │
                    │  │   - drop = winpct(SF) - winpct(FC)│       │
                    │  │   - tier: aligned/safe/sharp      │        │
                    │  │     via BLUNDER_DROP threshold    │        │
                    │  └──────────────┬───────────────────┘        │
                    │                 ▼                            │
                    │  ┌──────────────────────────────────┐        │
                    │  │  <FlawChessAgreementVerdict/>      │       │
                    │  │  (NEW component, renders inside    │       │
                    │  │  flawChessCard's CardBody, below   │       │
                    │  │  <FlawChessEngineLines/>)          │       │
                    │  │   - prose sentence (3 templates)   │       │
                    │  │   - 1-2 ProseMoveSpan-style spans   │      │
                    │  └──┬────────────────────────┬────────┘      │
                    │     │ onHoverMovesChange      │ onPlayMove    │
                    │     ▼                         ▼               │
                    │  setHoveredQualityMoves   playProseMove(san)  │
                    │  (existing state, L411)   (existing, L513)    │
                    │     │                         │               │
                    │     ▼                         ▼               │
                    │  qualityHoverArrows       makeMove(from,to)    │
                    │  (existing memo, L1049)   (existing board-tree│
                    │     │                      mutation)          │
                    │     ▼                                         │
                    │  boardArrows (wins over engineArrows,         │
                    │  L1139-1145) ──▶ <ChessBoard/>                │
                    └─────────────────────────────────────────┘
```

### Recommended Project Structure
```
frontend/src/
├── lib/
│   ├── flawChessVerdict.ts          # NEW — pure module, mirrors positionVerdict.ts
│   └── flawChessVerdict.test.ts     # NEW — co-located, mirrors positionVerdict.test.ts
├── components/analysis/
│   ├── FlawChessEngineLines.tsx     # UNCHANGED — verdict is a sibling, not folded in
│   ├── FlawChessAgreementVerdict.tsx # NEW — component name is planner's choice
│   └── __tests__/
│       └── FlawChessAgreementVerdict.test.tsx  # NEW
└── pages/
    └── Analysis.tsx                 # MODIFIED — one insertion inside flawChessCard (~L1504-1511),
                                      #   wiring onHoverMovesChange/onPlayMove to existing state/handlers
```

### Pattern 1: Pure verdict-classification module (mirror `positionVerdict.ts`)
**What:** A worker-free, side-effect-free module exporting a tier type, named threshold constants, a "verdict move" shape, and a formatter — consumed by a React component that only renders.
**When to use:** Any classification logic that must be independently unit-testable without mounting React (positionVerdict.test.ts has ~15+ pure tests with zero rendering).
**Example (mirror target, `frontend/src/lib/positionVerdict.ts:29-96`):**
```typescript
// Source: frontend/src/lib/positionVerdict.ts (existing, shipped)
export type VerdictTier = 'safe' | 'tricky' | 'difficult';

export interface VerdictMove {
  san: string;
  maiaPct: number;
  role: 'good' | 'bad' | 'escape';
  textColor: string;
  arrowColor: string;
  evalCp: number | null;
  evalMate: number | null;
}

export const SAFE_MAX_BAD_MASS = 0.2;   // named constant, no bare 0.2 in the classifier

export function formatVerdictEval(evalCp: number | null, evalMate: number | null): string {
  if (evalMate !== null) return evalMate > 0 ? `M${evalMate}` : `-M${Math.abs(evalMate)}`;
  if (evalCp !== null) {
    const pawns = evalCp / 100;
    return pawns >= 0 ? `+${pawns.toFixed(1)}` : pawns.toFixed(1);
  }
  return '—';
}
```
**Mirrored shape for `flawChessVerdict.ts` (new, not yet written):**
```typescript
// Proposed — mirrors positionVerdict.ts's shape, NOT its content (D-05 tiers differ from D-04/D-06 tiers)
export type FlawChessVerdictTier = 'aligned' | 'safe' | 'sharp';

export interface FlawChessVerdictMove {
  san: string;
  role: 'flawchess' | 'stockfish';   // NOT positionVerdict's 'good'|'bad'|'escape' — different semantics
  evalCp: number | null;             // white-POV cp (objectiveEvalCp for FC, evalCp for SF)
  evalMate: number | null;           // null for FC (RankedLine has no mate field), possibly set for SF
  textColor: string;                 // FLAWCHESS_ENGINE_ARROW or BEST_MOVE_ARROW
  arrowColor: string;                // same two constants — reused for both text and arrow (D-09)
}

export const SHARP_DROP_THRESHOLD = BLUNDER_DROP; // re-export/alias from '@/generated/flawThresholds' — a
                                                    // NAMED constant in THIS module per D-05, even though
                                                    // its value is imported, not redefined
```
Do not reuse `positionVerdict.ts`'s exported `VerdictMove`/`VerdictTier` types directly — the `role` semantics (`good`/`bad`/`escape`, keyed to Maia move quality) and `maiaPct` field don't map onto FlawChess-vs-Stockfish agreement. CONTEXT.md's own wording — "a `VerdictMove`-**like** shape" — confirms a new, analogous type is intended, not literal reuse.

### Pattern 2: Interactive move span (mirror `ProseMoveSpan`, `MaiaMoveQualityBar.tsx:145-207`)
**What:** A `Popover`/`PopoverAnchor`/`PopoverContent`-based button that opens on hover-intent (100ms delay) or immediate focus, stays open via a content-bridge (mouse re-entering the popover), and distinguishes "reveal" from "play" clicks by capturing whether the popover was already open at `pointerdown` time (a `ref`, not `state`, for synchronous read before the focus-driven re-render).
**When to use:** Any named-move prose span that needs both a passive hover preview and an active click-to-play action.
**Contract (exact, from `MaiaMoveQualityBar.tsx:145-207`):**
```typescript
// Source: frontend/src/components/analysis/MaiaMoveQualityBar.tsx:145-159
// NOT EXPORTED — module-private. Planner must extract or duplicate.
function ProseMoveSpan({
  move,          // typed as positionVerdict.ts's `VerdictMove` — Maia-specific field (maiaPct) baked in
  isOpen,        // boolean, parent-controlled (NOT internal state)
  onOpenDelayed, // () => void — used on onMouseEnter (100ms PROSE_POPOVER_OPEN_DELAY_MS timer)
  onOpenNow,     // () => void — used on onFocus and popover-content onMouseEnter (content-bridge)
  onClose,       // () => void — used on onMouseLeave, onBlur, popover-content onMouseLeave
  onPlay,        // (() => void) | undefined — called instead of onClose when already-open-at-press
}: { ... }): React.ReactElement {
  const wasOpenAtPress = useRef(false); // synchronous press-time snapshot, NOT React state
  return (
    <Popover open={isOpen} onOpenChange={(next) => (next ? undefined : onClose())}>
      <PopoverAnchor asChild>
        <button
          onMouseEnter={onOpenDelayed}
          onMouseLeave={onClose}
          onFocus={onOpenNow}
          onBlur={onClose}
          onPointerDown={() => { wasOpenAtPress.current = isOpen; }}
          onClick={() => {
            if (wasOpenAtPress.current) { onPlay ? onPlay() : onClose(); }
            else { onOpenNow(); }
          }}
        >{move.san}</button>
      </PopoverAnchor>
      <PopoverContent side="top" onMouseEnter={onOpenNow} onMouseLeave={onClose} ...>
        {/* HARDCODED Maia-specific content — this is the part that does NOT fit D-10 */}
        {`${move.maiaPct}% at this rating · ${evalText}`}
      </PopoverContent>
    </Popover>
  );
}
```
**Parent-side state ownership (`MaiaMoveQualityBar.tsx:272-386`):** the parent owns a single `activeProseSan: string | null` (which span is open), a `proseHoverTimer` ref for the delayed-open timeout, and three handler factories (`openProseNow`, `openProseDelayed`, `closeProse`). Only one span can be open at a time — opening one clears any hovered bar-segment state too (in this phase there's no bar-segment equivalent, so this simplifies).

**Extraction vs. duplication — planner decision required:**
- **Extract** the state-machine shell (the `Popover`/button/ref/handler wiring above) into a generic, content-parameterized component (e.g. accept `children: React.ReactNode` for the popover body and an `ariaLabel: string`), then have both `MaiaMoveQualityBar.tsx` and the new verdict component import it. Pro: single source of truth for the hover-intent/content-bridge/click-vs-play state machine (already covered by 3 passing tests in `MaiaMoveQualityBar.test.tsx:143-200`); con: touches a previously-stable, shipped file (`MaiaMoveQualityBar.tsx`), requiring its own tests to keep passing unchanged.
- **Duplicate** the ~60-line shell into the new component file with FlawChess-appropriate content and prop names. Pro: zero risk to the shipped Maia surface; con: two copies of the same interaction logic to keep in sync if either evolves.
- Given CLAUDE.md's "don't split just to fit a signature" guidance but also its general DRY preference, and given the shell logic is genuinely identical (not just superficially similar), **extraction is the recommended default** — but only extract the state-machine/button chrome, not the popover content (which is legitimately different data per surface).

### Pattern 3: Arrow-hover isolation via lifted state (existing plumbing, `Analysis.tsx`)
**What:** A callback prop (`onHoverMovesChange`) that a prose component calls with `HoveredQualityMove[] | null` (`{san: string; color: string}[]`); the page lifts this into `hoveredQualityMoves` state (L411), derives `qualityHoverArrows` from it (L1049-1067, replays each SAN via `new Chess(position).move(san)`, silently skipping illegal ones), and that memo **wins over** the persistent `engineArrows` layer in the `baseArrows` precedence chain (L1139-1142: `qualityHoverArrows ?? pvSidelineArrows ?? engineArrows`).
**When to use:** Exactly this phase's D-09 requirement — hovering isolates one pick's arrow, overriding the persistent two-arrow layer.
**Example:**
```typescript
// Source: frontend/src/pages/Analysis.tsx:1049-1067 (existing, unmodified)
const qualityHoverArrows = useMemo<BoardArrow[] | null>(() => {
  if (hoveredQualityMoves === null || hoveredQualityMoves.length === 0) return null;
  const arrows: BoardArrow[] = [];
  for (const { san, color } of hoveredQualityMoves) {
    try {
      const chess = new Chess(position);
      const move = chess.move(san);
      arrows.push({ startSquare: move.from, endSquare: move.to, color, width: QUALITY_HOVER_ARROW_WIDTH });
    } catch { /* illegal SAN for this position — skip */ }
  }
  return arrows.length > 0 ? arrows : null;
}, [hoveredQualityMoves, position]);
```
**Implication for the new component:** it must hand `onHoverMovesChange` **SAN strings legal at the current `position`**, not raw UCI. Both `flawChessEngine.rankedLines[0].rootMove` and `engine.pvLines[0].moves[0]` are UCI — they must be converted via `bestSanFromPv(position, uci)` (Analysis.tsx L240-254, module-private) before being handed to the verdict module/component. Since both `flawChessEngine` and `engine` are keyed on the same `position` FEN (L448-451, L535-539), this conversion is always valid at the moment of computation.

### Anti-Patterns to Avoid
- **Reading `engineTopLines[0]` for the objective comparison** — this memo (Analysis.tsx L682-700) degrades to a FlawChess row when `engineEnabled` is false, exactly the "FlawChess-vs-itself" false-agreement bug D-01/D-02 exist to prevent. Use `engine.pvLines[0]` directly.
- **Folding the verdict into `FlawChessEngineLines.tsx`** — that component's own docstring (L19-20) explicitly declares it a body-only sibling of `EngineLines.tsx`; adding cross-engine (Stockfish) awareness there breaks that documented boundary. Render the verdict as a separate sibling in the same `CardBody`.
- **Re-deriving the win% sigmoid** — `evalToExpectedScore` (`@/lib/liveFlaw.ts:53-68`) already does exactly this conversion (white-POV cp/mate → mover's expected score, `LICHESS_K` from the generated mirror). Do not hand-roll a second sigmoid.
- **Inventing a bare threshold** — `BLUNDER_DROP = 0.15` must be imported from `@/generated/flawThresholds`, not restated as a literal `0.15` in the new module (D-05 explicit requirement; also the generated-file drift-detection CI check would not catch a hand-copied literal).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| White-POV eval → mover win% | A new sigmoid | `evalToExpectedScore` (`@/lib/liveFlaw.ts:53-68`) | Already matches the backend's Python mirror exactly (`LICHESS_K`, mate mapping); a second implementation risks drift |
| Practical score (0-1) → display cp | A new inverse-sigmoid | `expectedScoreToWhitePovCp` (`@/lib/liveFlaw.ts:46-51`) | Already handles the es<=0/es>=1 mate-boundary special case without `ln(0)`/`ln(Infinity)` blowups |
| Eval string formatting | A third format function | `formatScore` (`EngineLines.tsx`, exported) or `formatVerdictEval` (`positionVerdict.ts`, exported) | Two precedents already exist; pick one (see Open Questions) rather than adding a third variant |
| UCI → SAN at a position | A new chess.js wrapper | `bestSanFromPv` (`Analysis.tsx:240-254`, module-private) | Already used identically for `bestSan`/`engineTopLines`; just needs export (or the caller keeps doing conversion before calling the new module) |
| Popover hover-intent/content-bridge mechanics | A new Radix wrapper | `ProseMoveSpan`'s shell (`MaiaMoveQualityBar.tsx:145-207`) | Exact same interaction contract (D-09/D-10/D-11 requirement) — extract or duplicate, don't reinvent |

**Key insight:** every primitive this phase needs (sigmoid, inverse-sigmoid, eval formatting, UCI→SAN, hover-intent popover, arrow-lift state) was built in Phases 151-156 for structurally identical problems. The engineering work here is composition and a few new named constants/templates, not new algorithms.

## Common Pitfalls

### Pitfall 1: Using `engineTopLines[0]` instead of `engine.pvLines[0]`
**What goes wrong:** When Stockfish is off but FlawChess is on, `engineTopLines` silently falls back to `flawChessEngine.rankedLines` (Analysis.tsx L692-698) — comparing FlawChess against itself produces a spurious "aligned" verdict for every position.
**Why it happens:** `engineTopLines` was designed as a generic "whatever's the best available reference" memo for the Maia chart tooltip (WR-04), a different consumer with different degradation-tolerance requirements.
**How to avoid:** Read `engine.pvLines[0]` directly (per D-01), and gate the whole verdict on `engineEnabled === true` (D-02) so there's never a need for a fallback.
**Warning signs:** A verdict claiming "Both agree" when Stockfish's toggle is visibly off.

### Pitfall 2: Feeding raw UCI to `onHoverMovesChange`
**What goes wrong:** `qualityHoverArrows` calls `new Chess(position).move(san)` expecting SAN; a raw UCI string like `e2e4` will usually throw inside the try/catch (chess.js's `.move()` accepts UCI-like objects but not bare 4-character strings as SAN) and the arrow silently fails to render — no crash, just a missing arrow, which is easy to miss in manual testing.
**Why it happens:** `RankedLine.rootMove` and `PvLine.moves[0]` are both UCI by contract (D-08 in `engine/types.ts`); the SAN conversion step is easy to forget since positionVerdict's `shownSans` were already SAN from Maia's contract.
**How to avoid:** Always convert via `bestSanFromPv(position, uci)` before constructing verdict-move objects or calling the hover callback.
**Warning signs:** Hovering a verdict move draws no board arrow, or draws the wrong one (a stale arrow from a previous hover that never cleared).

### Pitfall 3: Tier drift from partial snapshots (D-06)
**What goes wrong:** FlawChess's search is anytime (DISPLAY-01) — the first snapshot may have `rankedLines[0].objectiveEvalCp === null` (not yet graded). Computing a tier from a null eval either crashes or (worse) silently produces a bogus "sharp" or "aligned" verdict from a 0-treated-as-eval bug.
**Why it happens:** Live-refining data structures are easy to treat as "always complete" when developing against a fixture where the search has already converged.
**How to avoid:** D-06 requires falling back to the loading/help line whenever either `objectiveEvalCp` (FC) or `evalCp`/`evalMate` (SF, both null simultaneously would be malformed) hasn't arrived — mirror `positionVerdict.ts`'s `null`-return contract (its `computePositionVerdict` returns `null` when nothing is gradeable yet, and the caller falls back to static help text).
**Warning signs:** A verdict flashing briefly before "settling" into a different tier as the search progresses (should refine smoothly, not jump), or a console error about `null` arithmetic.

### Pitfall 4: `RankedLine` has no `evalMate` field
**What goes wrong:** Code that assumes symmetry between `RankedLine` and `PvLine` (both "the engine's line") and tries to read `flawChessEngine.rankedLines[0].evalMate` will hit a TypeScript error (the field doesn't exist) or, if loosely typed, `undefined`.
**Why it happens:** `RankedLine.objectiveEvalCp: number | null` (`engine/types.ts:53`) has no mate companion — FlawChess's search never surfaces a distinct mate distance, only a cp value (mate-adjacent positions are represented as very large/small cp via the same `MATE_CP_EQUIVALENT` convention used elsewhere). `PvLine` (Stockfish), by contrast, has both `evalCp: number | null` and `evalMate: number | null` (`uciParser.ts:20-23`).
**How to avoid:** When building the FC-side `FlawChessVerdictMove`, always pass `evalMate: null` explicitly; when formatting, `formatScore(objectiveEvalCp, null)` / `formatVerdictEval(objectiveEvalCp, null)` — both already handle this correctly (Analysis.tsx L682-700 and `FlawChessEngineLines.tsx:124` already do exactly this).
**Warning signs:** A TypeScript compile error, or (if bypassed with `as any`) a mate line rendering `NaN`/`undefined` for the FlawChess side.

## Code Examples

### Computing the win%-drop tier (D-05), using existing sigmoid
```typescript
// Proposed flawChessVerdict.ts internals — composes existing exports, invents nothing new
import { evalToExpectedScore, type MoverColor } from '@/lib/liveFlaw';
import { BLUNDER_DROP } from '@/generated/flawThresholds';

function computeDrop(
  fcEvalCp: number | null,
  sfEvalCp: number | null,
  sfEvalMate: number | null,
  mover: MoverColor,
): number | null {
  if (fcEvalCp === null || (sfEvalCp === null && sfEvalMate === null)) return null; // D-06 gate
  const fcWinPct = evalToExpectedScore(fcEvalCp, null, mover);       // FC has no mate field
  const sfWinPct = evalToExpectedScore(sfEvalCp, sfEvalMate, mover);
  return sfWinPct - fcWinPct; // D-06: always >= 0 by construction
}
```

### Existing hover-arrow lift (verbatim reuse point — no new code needed here, only a new caller)
```typescript
// Source: frontend/src/pages/Analysis.tsx:1539-1543 (existing MaiaHumanPanel wiring — the
// EXACT pattern the new verdict component's props should mirror)
<MaiaHumanPanel
  ...
  onHoverMovesChange={setHoveredQualityMoves}
  onPlayMove={playProseMove}
/>
```
The new component should accept the identically-named props (`onHoverMovesChange?: (moves: HoveredQualityMove[] | null) => void`, `onPlayMove?: (san: string) => void`) so its wiring at the call site (~L1504-1511, inside `flawChessCard`) is a one-line addition using state/handlers that already exist:
```typescript
<FlawChessEngineLines
  rankedLines={flawChessEngine.rankedLines}
  isSearching={flawChessEngine.isSearching}
  baseFen={position}
  startPly={currentPly}
  flipped={boardFlipped}
  onMoveClick={playUciLine}
/>
{/* NEW — sibling, not folded into FlawChessEngineLines */}
<FlawChessAgreementVerdict
  flawChessLine={flawChessEngine.rankedLines[0] ?? null}
  stockfishLine={engine.pvLines[0] ?? null}
  engineEnabled={engineEnabled}
  baseFen={position}
  onHoverMovesChange={setHoveredQualityMoves}
  onPlayMove={playProseMove}
/>
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|---------------|--------|
| Stockfish card fed the FlawChess engine's objective root eval (a "merged" handoff) | Two fully independent standalone searches (Stockfish WASM + FlawChess Engine's own pool), each with its own toggle | Phase 155 (D-04 reversal, per Analysis.tsx L440-447 comment) | The verdict compares two genuinely independent engine outputs — no shared/derived state to worry about desyncing |
| Old game-review default overlay (`gameOverlay.boardArrows`: best + light-blue 2nd-best) | `engineArrows`: top-1 per engine (FC amber + SF blue), `ARROW_COUNT = 1` | Phase 156 UAT | The verdict's "FC #1 vs SF #1" framing matches exactly what's already drawn on the board by default — no mismatch between what the verdict narrates and what the persistent arrows show |
| `MaiaMoveQualityBar`'s resting-state slot showed static help text | Live prose verdict (`positionVerdict.ts`) with hoverable spans | Quick 260705-m3z (2026-07-05) | This is the direct precedent/mirror target for the new module and component |

**Deprecated/outdated:** None — all referenced patterns are current, shipped code (no legacy paths to avoid in this domain).

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Extraction (not duplication) of `ProseMoveSpan`'s interaction shell is the recommended default | Pattern 2 | Low — this is explicitly framed as a planner decision in both CONTEXT.md and this research; either choice is viable, extraction is a recommendation, not a locked fact |
| A2 | `formatScore` (EngineLines.tsx, `#+3` notation) is visually more consistent than `formatVerdictEval` (positionVerdict.ts, `M3` notation) for this specific card | Open Questions | Low — cosmetic; CONTEXT.md explicitly defers this choice to implementation |

**If this table is empty:** N/A — both entries above are low-risk, discretion-flagged choices already acknowledged by CONTEXT.md, not load-bearing technical claims.

## Open Questions (RESOLVED)

> Both questions below were resolved during planning (Phase 157 PLAN.md): Plan 02 uses `formatScore` for cross-badge consistency (Q1), and keeps `flawChessVerdict.ts` pure with the UCI→SAN conversion done locally in the component/`Analysis.tsx` rather than exporting `bestSanFromPv` (Q2). The recommendations below stand.

1. **Eval formatting: `formatScore` vs `formatVerdictEval`?**
   - What we know: Both produce identical output for cp values (`+0.4`/`-0.3`); they differ only in mate notation (`#+3` vs `M3`) and null-fallback (`…` vs `—`). `formatScore` is already used one component-height above (in `FlawChessEngineLines`'s own badges) for the exact same `objectiveEvalCp`/`practicalScore` values.
   - What's unclear: Whether visual consistency with the immediately-adjacent `FlawChessEngineLines` badges (favoring `formatScore`) outweighs consistency with the *other* prose-verdict precedent (`positionVerdict.ts`'s `formatVerdictEval`, favoring the mirror pattern).
   - Recommendation: Use `formatScore` (already exported from `EngineLines.tsx`) for cross-badge consistency within the same card — CONTEXT.md explicitly leaves this open.

2. **Should `bestSanFromPv` be exported from `Analysis.tsx`, or should SAN conversion happen inside the new module/component?**
   - What we know: `bestSanFromPv` is currently module-private (`Analysis.tsx:240`); the pure-module design (mirroring `positionVerdict.ts`) argues for keeping chess.js/FEN logic OUT of `flawChessVerdict.ts` and doing the UCI→SAN conversion in `Analysis.tsx` before calling it (matching how `bestSan`/`engineTopLines` are already computed there).
   - What's unclear: Whether the new presentational component should also receive raw UCI + `baseFen` and do its own conversion (like `FlawChessEngineLines` does via `replayPvLine`), for prop-shape parity with that sibling.
   - Recommendation: Keep `flawChessVerdict.ts` pure (SAN + evals in, verdict out); have `Analysis.tsx` do the UCI→SAN conversion via the existing (possibly now-exported) `bestSanFromPv`, consistent with how `bestSan`/`engineTopLines` already work.

## Environment Availability

Skipped — no external tool/service/runtime dependencies. This phase touches only existing frontend source files; `npm run dev`/`npm test` are already verified working in this repo (per CLAUDE.md's documented commands).

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | Vitest 4.1.7 (`frontend/package.json`) |
| Config file | `frontend/vite.config.ts` (vitest config is co-located with the Vite config; no separate `vitest.config.ts` observed) |
| Quick run command | `cd frontend && npx vitest run src/lib/flawChessVerdict.test.ts` |
| Full suite command | `cd frontend && npm test` (= `vitest run`) |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| REVIEW-02 (D-04) | Same UCI move → `aligned` tier | unit | `npx vitest run src/lib/flawChessVerdict.test.ts` | ❌ Wave 0 |
| REVIEW-02 (D-05) | Divergence + drop < BLUNDER_DROP → `safe`; drop >= BLUNDER_DROP → `sharp` | unit | `npx vitest run src/lib/flawChessVerdict.test.ts` | ❌ Wave 0 |
| REVIEW-02 (D-06) | Null objective eval (either side) → `null` result, no bogus tier | unit | `npx vitest run src/lib/flawChessVerdict.test.ts` | ❌ Wave 0 |
| REVIEW-02 (D-02/D-03) | `engineEnabled === false` → muted prompt line, no comparison attempted | component | `npx vitest run src/components/analysis/__tests__/FlawChessAgreementVerdict.test.tsx` | ❌ Wave 0 |
| REVIEW-02 (D-09) | Hovering a span calls `onHoverMovesChange` with exactly one `{san, color}` in the pick's tier color | component | same file as above | ❌ Wave 0 |
| REVIEW-02 (D-10) | Popover content shows engine-labeled two lines; Stockfish-pick popover omits FlawChess line when the engine didn't also rank that move | component | same file as above | ❌ Wave 0 |
| REVIEW-02 (D-11) | Click (while popover already open) calls `onPlayMove(san)`; first click only reveals | component | same file as above (mirror `MaiaMoveQualityBar.test.tsx:163-200`'s `fireEvent.pointerDown` + `fireEvent.click` pattern) | ❌ Wave 0 |
| REVIEW-01/SC4 | Verdict renders identically on `?game_id&ply` (game review) and free analysis | manual/UAT | N/A — both surfaces share the single `flawChessCard` JSX (Analysis.tsx L1476-1515), so this is a parity *confirmation*, not new code | N/A |

### Sampling Rate
- **Per task commit:** `npx vitest run src/lib/flawChessVerdict.test.ts src/components/analysis/__tests__/FlawChessAgreementVerdict.test.tsx` (or whatever filenames the planner picks)
- **Per wave merge:** `cd frontend && npm run lint && npm test -- --run`
- **Phase gate:** Full suite green before `/gsd-verify-work`; also run `npx tsc -b` (or `npm run build`) per CLAUDE.md's "frontend has no separate typecheck in lint/test" gotcha (`noUncheckedIndexedAccess` errors on `rankedLines[0]`/`pvLines[0]` indexing won't surface via `npm run lint`/`npm test` alone).

### Wave 0 Gaps
- [ ] `frontend/src/lib/flawChessVerdict.test.ts` — covers tier classification (D-04/D-05/D-06), mirroring `positionVerdict.test.ts`'s fixture style (a `rung`-like helper or direct `RankedLine`/`PvLine` fixtures)
- [ ] `frontend/src/components/analysis/__tests__/FlawChessAgreementVerdict.test.tsx` — covers hover/click/popover mechanics, mirroring `MaiaMoveQualityBar.test.tsx`'s `fireEvent.focus`/`fireEvent.pointerDown`+`fireEvent.click` patterns (note: that file needs NO `matchMedia`/`ResizeObserver` stubs, unlike `FlawChessEngineLines.test.tsx` which needs them for its `Tooltip`+`MiniBoard` hover preview — the new component has no miniboard preview, so the simpler `MaiaMoveQualityBar.test.tsx` setup is the right template, not `FlawChessEngineLines.test.tsx`'s)
- [ ] No framework install needed — Vitest + Testing Library are already configured and used identically by both mirror-target test files.

## Security Domain

`security_enforcement` is not explicitly disabled in `.planning/config.json` (absent = enabled), but this phase has essentially no attack surface: no new user input, no new network calls, no new auth/session paths — it renders derived data from client-side engine workers that already run on the page.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | No | Not touched — no auth surface |
| V3 Session Management | No | Not touched |
| V4 Access Control | No | Not touched |
| V5 Input Validation | Marginal | Move SANs/UCIs originate from the trusted client-side engine outputs (not user text input); `bestSanFromPv`/`qualityHoverArrows` already wrap all chess.js parsing in try/catch (never throws on malformed input) |
| V6 Cryptography | No | Not touched |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| XSS via engine-derived strings rendered as prose | Tampering (low likelihood — data is client-computed, not server/user-supplied) | Already mitigated by construction: all strings are rendered as React children (auto-escaped), matching the existing "T-137-03 mitigated" convention noted in `FlawChessEngineLines.tsx`'s own docstring (L22-24) |

## Sources

### Primary (HIGH confidence — direct code reads, this session)
- `frontend/src/lib/positionVerdict.ts` (full file read) — the pure-module mirror target
- `frontend/src/components/analysis/MaiaMoveQualityBar.tsx` (full file read) — `ProseMoveSpan`/`renderVerdictSentence`/`interleaveWithConjunction` contracts
- `frontend/src/pages/Analysis.tsx` (targeted reads: L1-260, L440-720, L1030-1150, L1440-1560, L1700-1735) — `engineArrows`, `qualityHoverArrows`, `hoveredQualityMoves`, `engineTopLines` degradation, `flawChessCard`, `playProseMove`, `bestSanFromPv`
- `frontend/src/lib/engine/types.ts` (full file read) — `RankedLine`, `EngineSnapshot`
- `frontend/src/generated/flawThresholds.ts` (full file read) — `BLUNDER_DROP`/`MISTAKE_DROP`/`INACCURACY_DROP`/`LICHESS_K`/`MATE_CP_EQUIVALENT` values
- `frontend/src/lib/liveFlaw.ts` (full file read) — `evalToExpectedScore`, `expectedScoreToWhitePovCp`, `sideToMoveFromFen`
- `frontend/src/components/analysis/FlawChessEngineLines.tsx` (full file read) — score-pair badge precedent, body-only sibling boundary
- `frontend/src/lib/theme.ts` (targeted reads) — `FLAWCHESS_ENGINE_ARROW`, `BEST_MOVE_ARROW`, `FLAWCHESS_ENGINE_ACCENT`, `STOCKFISH_ACCENT`
- `frontend/src/hooks/uciParser.ts` — `PvLine` interface
- `frontend/src/hooks/useFlawChessEngine.ts` (return-shape grep) — `isSearching`/`isReady` fields
- `frontend/src/components/ui/popover.tsx` (export grep) — `Popover`/`PopoverAnchor`/`PopoverContent` availability
- `frontend/src/lib/positionVerdict.test.ts`, `frontend/src/components/analysis/__tests__/MaiaMoveQualityBar.test.tsx`, `frontend/src/components/analysis/__tests__/FlawChessEngineLines.test.tsx` — test-convention precedents
- `.planning/phases/157-flawchess-agreement-verdict-prose-hoverable-moves/157-CONTEXT.md` — locked decisions D-01 through D-11
- `.planning/REQUIREMENTS.md`, `.planning/ROADMAP.md` (Phase 157 section), `.planning/STATE.md` — requirement/roadmap cross-check (surfaced the SC1/D-01 mismatch)

### Secondary (MEDIUM confidence)
None used — every claim in this research was verified directly against the current working tree in this session; no external web sources were needed (this is a pure internal-reuse phase).

### Tertiary (LOW confidence)
None.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new dependencies; every symbol cited above was read directly from the repo this session
- Architecture: HIGH — the insertion point, data flow, and arrow/hover plumbing were traced line-by-line in `Analysis.tsx`
- Pitfalls: HIGH — each pitfall is grounded in a specific, quoted code behavior (the `engineTopLines` degradation, the SAN-vs-UCI mismatch, the missing `evalMate` field) observed directly in the source, not inferred

**Research date:** 2026-07-07
**Valid until:** Effectively indefinite for the cited symbols (all are Phase 151-156 locked/shipped contracts per `engine/types.ts`'s own "frozen for the rest of the v2.0 milestone" docstring) — re-verify only if a later phase in this milestone modifies `RankedLine`, `PvLine`, `flawThresholds.ts`, or `Analysis.tsx`'s arrow-precedence chain.
