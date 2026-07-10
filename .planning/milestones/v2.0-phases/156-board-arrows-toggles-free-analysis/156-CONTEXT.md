# Phase 156: Board Arrows + Toggles (Free Analysis) - Context

**Gathered:** 2026-07-06
**Status:** Ready for planning

<domain>
## Phase Boundary

Render the two live engines' top moves as **distinct board arrows on the free-analysis
`/analysis` board** for the first time. Today the free-analysis board shows NO engine
arrows (only the translucent white on-main-line next-move arrow and move-quality hover
arrows); the Stockfish blue/grey arrows exist only in **game mode** via `useGameOverlay`.
This phase adds:

- A **FlawChess Engine** arrow (amber/gold) from `flawChessEngine.rankedLines[0].rootMove`.
- A **Stockfish** arrow (reuse the existing blue) from `engine.pvLines[0].moves[0]`.

Both refine live as their searches update. Arrow visibility binds to the **existing
Phase 155 card toggles** — no new toggle UI. Framed so disagreement reads as intentional
(ARROW-04), never "best move" unqualified.

**In scope:** free-analysis board only; the two engine arrows; the new FC amber theme
token; the nested concentric layering (FC > SF > white); binding arrow visibility to the
existing card enabled-state; applying the same to the mobile takeover board.

**Out of scope (later phases):** game-review overlay integration + the played-move arrow
+ game-review default visibility (Phase 157, REVIEW-01..02); a real engine-settings panel
with a configurable arrow count (future milestone, see REQUIREMENTS.md → Future
Requirements). Top-2 arrows (the roadmap's original count is overridden to top-1 — see D-03).

</domain>

<decisions>
## Implementation Decisions

### Toggling (ARROW-02) — already built
- **D-01 — Reuse the existing card switches; no new toggle UI.** The Phase 155 header
  switches `engineEnabled` (Stockfish card) and `flawChessEnabled` (FlawChess card) ARE
  the arrow toggles. Each engine's arrow renders iff its card is enabled — so the two
  layers are already independently toggleable (turning one card off never hides the
  other's arrow). This is what the phase note means by "we already built the toggles."
  No arrow-specific toggle control is added.

### Arrow count (ARROW-01) — override the roadmap
- **D-02 — Top-1 arrow per engine, not top-2.** The roadmap/success-criteria said "top-2";
  the user overrides to a **single** arrow per engine to reduce board clutter. FC arrow =
  `rankedLines[0].rootMove`; SF arrow = `engine.pvLines[0].moves[0]`.
- **D-03 — One `ARROW_COUNT = 1` constant; no settings plumbing now.** A future
  engine-settings panel will make the count configurable, but building that panel/prop
  threading is out of scope. Implement top-1 via a single named constant so the future
  change is a one-line edit. Do NOT thread a per-engine count prop through the component
  tree now (avoid premature settings infrastructure).

### Arrow colors (ARROW-01, ARROW-03)
- **D-04 — SF reuses blue; FC gets a NEW amber/gold token.** Stockfish's free-analysis
  arrow reuses the existing `BEST_MOVE_ARROW` blue (`rgba(37,99,235,0.8)`) so it matches
  the established SF-is-blue convention (incl. game mode). Add ONE new `theme.ts`
  constant for the FlawChess Engine board arrow: **amber/gold ~`oklch(0.78 0.15 85)`** —
  salient on the brown board squares (D-05 of Phase 155 flagged `FLAWCHESS_ENGINE_ACCENT`
  brown as NOT salient for arrows), reads as "human/practical", and is clearly distinct
  from the violet Maia accent and red/orange tactic arrows. Exact amber value is
  tunable at UAT; it belongs in `theme.ts` (never hard-coded in the component).
- **No dedicated Maia arrow layer (ARROW-03).** Maia's reply distribution stays reachable
  via the existing Moves-by-Rating chart hover. Unchanged here.

### Nested concentric layering + widths (agreement/overlap + emphasis)
- **D-05 — Three concentric arrows, largest at the bottom, smallest on top.** When layers
  point at the same move they do NOT collapse to one — they nest as concentric arrows so
  every active layer stays visible. Draw order (array order; later index = drawn on top):
  1. **FC amber — widest**, `width: 0.80` (drawn first, bottom)
  2. **SF blue — medium**, `width: 0.50` (standard engine width; drawn second)
  3. **White next-move / played-move — thinnest**, `width: 0.18` (existing
     `NEXT_MOVE_ARROW`, already `onTop`; drawn last, on top)

  Rationale: FC widest foregrounds the practical move (the product headline); the smaller
  arrows sit inside its halo. Disagreement → the arrows point different directions and
  read as two distinct colored arrows (satisfies ARROW-04).

- **D-06 — Engine arrows must BYPASS `dedupeArrowsByMove`.** `dedupeArrowsByMove`
  (`components/board/arrowGeometry.ts`) collapses two arrows sharing the same from→to,
  keeping only the last. For the concentric look, FC + SF on an **agreed** move must both
  survive. The white next-move arrow already escapes dedupe via its `-top` key suffix
  (`arrowMoveKey`); the FC and SF engine arrows need an equivalent escape (distinct
  render path or distinct keys). Planner: choose the mechanism, but the invariant is
  "FC and SF both render even when they agree."

### Framing (ARROW-04) — satisfied structurally
- **D-07 — Score pair is already always-visible; no new copy work beyond guarding strings.**
  The objective-vs-practical score pair lives in the FlawChess Engine card (Phase 155
  D-06) and is always visible whenever the FC card (hence the FC arrow) is on — so
  "disagreement is never a hover away" holds without new UI. Ensure no arrow-related
  string (tooltip, empty state, label) reads "best move" unqualified.

### Claude's Discretion
- Exact `dedupeArrowsByMove` bypass mechanism (D-06) — distinct keys vs a separate
  engine-arrow render path. Planner's call; invariant stated above.
- Exact amber `oklch` value (D-04) — tune at UAT for salience on the board squares.
- Where the two engine arrows slot into the `boardArrows` assembly in `Analysis.tsx`
  (~L1067–1075) relative to `qualityHoverArrows` and the game-mode overlays; note the
  free-analysis path currently yields `undefined` base arrows.
- Empty/pre-first-snapshot state: the FC arrow simply doesn't render until the first
  snapshot has a `rootMove` (mirror the card's skeleton timing); no placeholder arrow.
- Mobile takeover board: apply the same arrows there (CLAUDE.md "apply changes to mobile
  too").

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Prior phase decisions
- `.planning/phases/155-react-hook-anytime-ui-free-analysis/155-CONTEXT.md` — D-05 reserved
  the board-arrow color decision for this phase and flagged brown-as-not-salient; D-06 the
  always-visible score pair; D-02/D-03 the three card toggles this phase's arrows bind to.

### Frontend surfaces to edit / reuse
- `frontend/src/pages/Analysis.tsx` — `boardArrows` assembly (~L1067–1075), the
  `engineEnabled` / `flawChessEnabled` state (~L346–351), `flawChessEngine.rankedLines`
  and `engine.pvLines` sources, `<ChessBoard arrows={boardArrows}>` (~L1224).
- `frontend/src/hooks/useGameOverlay.ts` — the EXISTING Stockfish arrow pattern
  (`BEST_MOVE_ARROW` = pvLines[0], `SECOND_BEST_ARROW` = pvLines[1]); reuse, do not
  reimplement (ARROW-03 "reused, not reimplemented").
- `frontend/src/components/board/arrowGeometry.ts` — `dedupeArrowsByMove` / `arrowMoveKey`
  (the dedupe that D-06 must bypass for the engine layer).
- `frontend/src/components/board/ChessBoard.tsx` — `BoardArrow` interface (`width`,
  `onTop`, `color`).
- `frontend/src/lib/theme.ts` — `BEST_MOVE_ARROW` (reuse for SF), `FLAWCHESS_ENGINE_ACCENT`
  (brown, card only — NOT the arrow); add the new FC amber arrow token here.
- `frontend/src/lib/engine/types.ts` — `RankedLine.rootMove` / `objectiveEvalCp` /
  `practicalScore` (FC arrow source + score-pair values).

### Requirements
- `.planning/REQUIREMENTS.md` — ARROW-01..04 (note ARROW-01's "top-2" wording is
  overridden to top-1 per D-02; the requirement's INTENT — a live-refining practical-move
  arrow layer — is met).

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `useGameOverlay.ts` Stockfish arrow construction (`BEST_MOVE_ARROW`) — the SF arrow
  pattern to reuse for the free-analysis SF arrow.
- `dedupeArrowsByMove` / `arrowMoveKey` — same-move collapse the engine layer must
  bypass; the `-top` key-suffix trick (used by the white next-move arrow) is the model.
- Phase 155 card toggles `engineEnabled` / `flawChessEnabled` — the gating state.
- `BoardArrow.width` / `.onTop` — the existing mechanism for the concentric layering.

### Established Patterns
- Free-analysis `boardArrows` today = `qualityHoverArrows ?? undefined` (+ white
  next-move `onTop`). The two engine arrows extend this base for the non-game path.
- SF-is-blue, Maia-is-violet, tactics red/orange — new FC arrow must avoid all three;
  amber/gold is the open, salient slot.
- Theme colors with semantic meaning live in `theme.ts` only (never hard-coded).

### Integration Points
- `Analysis.tsx` `boardArrows` memo feeds `<ChessBoard arrows={...}>`; the engine arrows
  slot in there, gated by the two card-enabled booleans, in draw order [FC, SF, white].

</code_context>

<specifics>
## Specific Ideas

- Concentric nested arrows (user's exact framing): "Largest arrow is FC, second largest
  SF, third largest Move Played (white). Render order matters (smallest arrow on top):
  first FC (largest), second SF (medium), third move played (small)." Widths locked at
  **0.80 / 0.50 / 0.18**.
- FC amber board-arrow token target: ~`oklch(0.78 0.15 85)` (tunable).

</specifics>

<deferred>
## Deferred Ideas

- **Engine settings panel with a configurable arrow count** — build only the
  `ARROW_COUNT` constant now (D-03); the real settings UI is a future milestone
  (REQUIREMENTS.md → Future Requirements).
- **Game-review board arrows + played-move layer + game-review default visibility**
  (played-move ON, FC ON, SF OFF) — Phase 157 (REVIEW-01..02).

None else — discussion stayed within phase scope.

</deferred>

---

*Phase: 156-board-arrows-toggles-free-analysis*
*Context gathered: 2026-07-06*
