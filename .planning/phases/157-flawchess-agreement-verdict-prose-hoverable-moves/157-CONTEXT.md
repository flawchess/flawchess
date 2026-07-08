# Phase 157: FlawChess Agreement Verdict (prose + hoverable moves) - Context

**Gathered:** 2026-07-07
**Status:** Ready for planning

<domain>
## Phase Boundary

Add a one-line prose **agreement verdict** to the FlawChess Engine card on `/analysis`, below its ranked lines. The verdict narrates whether the engine's top **practical** move agrees or diverges from Stockfish's top **objective** move — citing both evals, with the named moves as interactive spans (hover lights a board arrow + opens an eval popover, click plays the move as a free move). It renders on both free analysis and game review (shared `Analysis.tsx`), turning the side-by-side score badges into a plain-language "engines are flawless, humans play FlawChess" read.

**In scope:** the verdict prose, its three-tier logic, the hoverable/click-to-play move spans, arrow isolation on hover, the popover, and confirming end-to-end parity on the game-review board (`?game_id&ply`).

**Out of scope (own phases / seeds):** any comparison anchored on the move the user *actually played* → **SEED-086**. New engine capabilities, new arrow layers (Phase 156 already ships amber FC + blue SF arrows), and the deferred-by-design items in REQUIREMENTS.md Future Requirements.

</domain>

<decisions>
## Implementation Decisions

### Data source & Stockfish-off behavior
- **D-01:** The verdict compares **FlawChess practical #1** (`flawChessEngine.rankedLines[0]`: `rootMove`, `practicalScore`, `objectiveEvalCp`) against **Stockfish objective #1** — the *true* Stockfish PV, `engine.pvLines[0]` (`moves[0]` + `evalCp`/`evalMate`). NOT the `engineTopLines[0]` memo, which silently degrades to a FlawChess row when Stockfish is off.
- **D-02:** The verdict renders **only when standalone Stockfish is on** (`engineEnabled === true`) **and** FlawChess has produced a snapshot. When `engineEnabled` is false there is no true objective #1, so no comparison is shown — avoids a misleading FlawChess-vs-itself read. (Both toggles default to `true`, so the common case is both engines running and the verdict well-defined.)
- **D-03:** When Stockfish is off, the fixed-height verdict slot shows a **muted prompt line**: `Turn on Stockfish to compare picks.` (mirrors `positionVerdict`'s help-text fallback; keeps the slot non-jumping).

### Three-tier logic (aligned / safe divergence / sharp divergence)
- **D-04:** **`aligned`** = FlawChess #1 `rootMove` and Stockfish #1 move are the **same UCI move**.
- **D-05:** On divergence (different moves), split by the **objective eval sacrificed** measured as a **win-probability drop from the mover's POV**: convert both objective evals to win% via the engine's existing lichess sigmoid, `drop = winpct(SF#1_objective) − winpct(FC#1_objective)`. `safe` = `0 < drop < BLUNDER_DROP` (0.15); `sharp (trap)` = `drop ≥ BLUNDER_DROP` (0.15). Reuses the app-wide flaw-threshold scale (`src/generated/flawThresholds.ts`) rather than a fresh cp constant — self-calibrating near 0.0 vs ±5.0. Give the threshold a **named constant** in the verdict module (no bare 0.15).
- **D-06:** By construction the FlawChess practical #1 can never be objectively better than Stockfish's objective max, so `drop` is always `≥ 0`. If **either objective eval hasn't arrived yet** mid-search (`objectiveEvalCp`/PV eval null), fall back to the loading/help line — never emit a bogus tier from a partial snapshot. The tier **refines live** with the search inside the fixed-height slot (no layout jump).

### Copy & tone (brand voice)
- **D-07:** **Brand voice** — Stockfish framed as objective/flawless, FlawChess as the human-playable pick. Use **neutral "for a human here"** phrasing (NOT "you"/"your opponent") so the line reads correctly regardless of side to move. Draft templates (exact wording finalized in implementation):
  - aligned: *"Both agree on `Nf3` — objectively +0.4, and the practical pick too."*
  - safe: *"Objectively `Qb3` (+0.6). But for a human here, FlawChess plays `Nf3` (+0.3) — barely any cost, far easier."*
  - sharp (trap): *"`Qb3` is objectively best (+2.1) but it's a trap for humans. FlawChess plays the safer `Nf3` (+0.4) instead."*
- **D-08:** No UI string reads a bare "best move" unqualified (REVIEW-02 / ARROW-04 principle). Move names are the interactive spans (backtick = `ProseMoveSpan` above).

### Hover / arrow / popover interaction
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

### Reviewed Todos (not folded)
- `2026-03-11-bitboard-storage-for-partial-position-queries.md` — DB-layer, unrelated to this frontend verdict (keyword false-positive on "position/game").
- `2026-05-18-wr01-pt33-invalid-tailwind-score-axis-label.md` — a different component's Y-axis label; not this card (keyword false-positive on "score/tsx").

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase spec & requirements
- `.planning/ROADMAP.md` → "### Phase 157: FlawChess Agreement Verdict" — goal, 4 success criteria, scope note.
- `.planning/REQUIREMENTS.md` — REVIEW-02 (reframed prose agreement verdict) and REVIEW-01 (game-review parity, absorbed into SC4).
- `.planning/seeds/SEED-086-game-review-played-vs-practical-comparison.md` — the explicitly-deferred played-vs-practical comparison; do NOT build it here.
- `.planning/phases/156-board-arrows-toggles-free-analysis/156-CONTEXT.md` — prior arrow-layer + toggle decisions this builds on.

### Reuse patterns (read before implementing)
- `frontend/src/components/analysis/MaiaMoveQualityBar.tsx` — `ProseMoveSpan`, `renderVerdictSentence`, `interleaveWithConjunction`, the lift-arrow + hover-intent popover + click-to-play plumbing to reuse verbatim.
- `frontend/src/lib/positionVerdict.ts` — the pure verdict-module template (`VerdictTier`, `VerdictMove`, named constants, `formatVerdictEval`, `joinMoveNames`).
- `frontend/src/generated/flawThresholds.ts` — `BLUNDER_DROP` (0.15), `MISTAKE_DROP`, `INACCURACY_DROP` (win% units) — the tier threshold scale (D-05).

### Data & wiring
- `frontend/src/lib/engine/types.ts` → `RankedLine` (`rootMove`, `practicalScore`, `objectiveEvalCp`, `modalPath`).
- `frontend/src/components/analysis/FlawChessEngineLines.tsx` — the card body the verdict renders beneath; `expectedScoreToWhitePovCp` / `sideToMoveFromFen` from `@/lib/liveFlaw` for practical→cp/win% conversion.
- `frontend/src/pages/Analysis.tsx` — `engineArrows` (amber FC + blue SF), `qualityHoverArrows` overlay + `hoveredQualityMoves` state, `engine.pvLines` (Stockfish PV), `flawChessEngine.rankedLines`, `engineEnabled`/`flawChessEnabled`, the FlawChess `CardBody` (~L1497), and the `onPlayMove` free-move handler pattern.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **`ProseMoveSpan` + `renderVerdictSentence`** (`MaiaMoveQualityBar.tsx`): interactive move spans with hover-intent popover, content-bridge, click-to-play, and a lift-arrow callback — the exact interaction contract for D-09/D-10/D-11.
- **`positionVerdict.ts`**: pure tier-classifier template (tiers + named constants + `VerdictMove` + `formatVerdictEval`) to mirror as `flawChessVerdict.ts`.
- **`qualityHoverArrows`** (`Analysis.tsx`): a hover-driven `BoardArrow[]` overlay derived from lifted moves that already takes precedence over `engineArrows` — the isolation mechanism for D-09.
- **`flawThresholds.ts`** (`BLUNDER_DROP`): the app-wide win%-drop scale for the tier split (D-05).
- **`FLAWCHESS_ENGINE_ARROW` / `BEST_MOVE_ARROW`** (theme): the amber/blue tier colors already used by the persistent engine-arrow layer.

### Established Patterns
- FlawChess card body (`FlawChessEngineLines`) is a deliberate `EngineLines` sibling — keep it body-only; the verdict is a separate sibling component in the same `CardBody`.
- No bare "best move" strings (ARROW-04); evals are white-POV pawn-scale; practical scores are root-STM 0–1 converted via the Plan 01 inverse sigmoid.
- Fixed-height slots below live-refining engine output to prevent layout jump (D-09 skeleton pattern in the card).

### Integration Points
- New verdict component consumes both `flawChessEngine.rankedLines[0]` and `engine.pvLines[0]`, plus `engineEnabled`, from `Analysis.tsx`.
- Its hover callback feeds the same lifted-move state that drives `qualityHoverArrows`; its click calls the existing free-move `onPlayMove`.
- Renders inside the FlawChess `CardBody` on both free analysis and game review (shared component ⇒ SC4 parity confirmation, not new game-review code).

</code_context>

<specifics>
## Specific Ideas

- Popover format is engine-labeled two lines (`FlawChess: … (practical)` / `Stockfish: … (objective)`), user-specified — NOT the terse `practically X · objectively Y` dot format from the Maia surface.
- Tagline framing ("engines are flawless, humans play FlawChess") should come through in the copy: Stockfish = the flawless/objective voice, FlawChess = the human-playable choice.

</specifics>

<deferred>
## Deferred Ideas

- **Played-move vs practical-best comparison (game review)** → already captured as **SEED-086**. Anchored on the move the user actually played; out of scope here (this phase compares the two engines, not the played move).

</deferred>

---

*Phase: 157-flawchess-agreement-verdict-prose-hoverable-moves*
*Context gathered: 2026-07-07*
