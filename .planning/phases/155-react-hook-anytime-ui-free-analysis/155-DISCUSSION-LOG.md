# Phase 155: React Hook + Anytime UI (Free Analysis) - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-07-06
**Phase:** 155-React Hook + Anytime UI (Free Analysis)
**Areas discussed:** Surface placement, Activation/toggles, Eval bars, Branding, Score pair, Display detail

---

## Surface placement

| Option | Description | Selected |
|--------|-------------|----------|
| Own dedicated card/section | New FlawChessEngineLines card alongside the Stockfish card; keeps the two engines distinct | ✓ (refined) |
| Merge into the Stockfish engine card | Second section inside the existing engine card | |
| Replace the Stockfish lines | FlawChess Engine becomes the primary lines panel | |

**User's choice:** Own dedicated card, stacked **above** the "Maia — Human Move Probability" card in the **left** column (clarified against the actual layout screenshot — Maia card is left, board center, Stockfish card right).
**Notes:** User provided a screenshot of the current `/analysis` layout to pin the geometry.

---

## Activation / toggles

| Option | Description | Selected |
|--------|-------------|----------|
| Opt-in toggle, default OFF | Safest for the deferred SC4 mobile-memory UAT | |
| On by default, device-adaptive | ON desktop / OFF mobile | (held as fallback) |
| On by default everywhere | Always runs; pool lazy-spawns | ✓ |

**User's choice:** On by default everywhere. Additionally proposed a richer toggle model: a **toggle switch in each of the 3 cards** (Stockfish, Maia, FlawChess) to enable/disable each engine.
**Notes:** Accepted the risk of running before SC4; device-adaptive default kept as the post-UAT fallback. The existing Stockfish header on/off is upgraded to a switch for consistency.

---

## Eval bars (Phase 154 D-03 handoff)

| Option | Description | Selected |
|--------|-------------|----------|
| In-card headline, no 3rd bar | Practical score in the card, blue bar shows engine objective | (superseded) |
| Add a 3rd brown board bar | Three flanking bars | |
| Brown practical bar replaces Maia's | Brown takes the violet slot | (basis of chosen) |

**User's choice:** Shared left-slot precedence — the **FC** eval bar (brown, label "FC") takes the left slot over **Maia** (violet) when both engines are enabled; right slot stays **Stockfish** (blue "SF"), fed the engine's objective root eval while FC runs. No third bar. (This also resolved the D-03 "what does the bar do" question the user had initially skipped.)
**Notes:** User asked directly whether the engine needs its own bar and how it differs from Maia/Stockfish; the shared-slot design emerged from that exchange.

---

## Branding / color

| Option | Description | Selected |
|--------|-------------|----------|
| Brown accent, subtle gold on headline | Consistent card accent + gold headline, no card glow | ✓ |
| Full bronze/gold card glow | Homepage-style outer glow on the whole card | |
| Plain brown accent, no gold | Match blue/violet cards exactly | |

**User's choice:** Brown accent + subtle gold on the headline; no card-wide glow.
**Notes:** User flagged a full glow as probably "too much" and noted brown arrows won't be salient against the brown board squares → high-contrast arrow color punted to Phase 156.

---

## Score pair

| Option | Description | Selected |
|--------|-------------|----------|
| Both on pawn scale, your POV | Practical converted to pawns, signed from your side | (adjusted to white POV) |
| Objective in pawns, practical as % | Two different scales | |
| You decide during planning | Defer number format | |

**User's choice:** Both numbers on the **pawn scale**, but from **white's perspective** (like Stockfish) to avoid confusion. Color-code the badges/numbers: **blue** (Stockfish objective), **brown/gold** (practical).
**Notes:** User explicitly rejected a your-POV flip as confusing. Copy nuance captured in CONTEXT (numbers white-POV; "for you" describes the engine, not a POV flip).

---

## Display detail

| Decision | Options | Selected |
|----------|---------|----------|
| Line count | Top 2 / **Top 3** / Top 4 | Top 3 |
| Modal-path depth | **~5 plies + expand** / Full / Short (3) | ~5 plies + expand |
| Move-chip interaction | **Graft-to-tree** / Display only | Graft-to-tree (reuse `onMoveClick`) |

**User's choice:** Top 3 lines; ~5 plies of SAN with an expand chevron (mirrors Stockfish EngineLines); clickable graft-to-tree like the Stockfish PV chips.
**Notes:** All three taken as recommended.

---

## Claude's Discretion

- Grading-worker binding under the 3-toggle split (likely the Maia card toggle).
- Maia card toggle must not starve the engine's internal `maiaQueue` (separate instance).
- `useFlawChessEngine` hook shape: trigger/debounce, `SearchBudget` construction, abort-on-navigation, the "engine active" signal.
- ELO source for `budget.elo.{w,b}` (reuse `useMaiaEloDefault`/`selectedElo`).
- Exact bar cap labels and toggle-state persistence.

## Deferred Ideas

- Board arrows + high-contrast FlawChess arrow color — Phase 156.
- Game-review overlay integration — Phase 157.
- Device-adaptive default (on desktop / off mobile) — SC4 fallback only.
- Two low-relevance todos reviewed but not folded (bitboard storage; a chart-axis Tailwind nit).
