# Sketch Manifest

## Design Direction
Mockups for **Phase 107 — the Library Games subtab frontend** (SEED-036). These ground the UI-SPEC
for two surfaces: the **analyzed game card** (existing `GameCard` + per-game B/M/I severity counts
+ curated family-colored tag chips + a "no engine analysis" state) and the **Flaw-Stats panel**
(per-severity rates, tag distribution, trend-over-time, explicit `% analyzed` + N denominator).
The aesthetic is **fixed by the existing app**, not invented: dark/charcoal surfaces, WDL
left-border cards on `charcoal-texture`, brand brown `#8B5E3C` / highlight `#F0DBB9`, Nunito Sans
body + Fredoka brand font, WDL palette. Tag chips are **color-by-family** (tempo / opportunity /
impact) — chips are display-only in 107 (the Flaws deep-link target ships later).

## Reference Points
- The real `frontend/src/components/results/GameCard.tsx` (mini board, ■/□ names, opening line, metadata row)
- Endgames stats-panel + WDL-bar layout (`frontend/src/components/charts/`)
- Tokens from `frontend/src/index.css` + `frontend/src/lib/theme.ts`

## Sketches

| # | Name | Design Question | Winner | Tags |
|---|------|----------------|--------|------|
| 001 | analyzed-game-card | Where do B/M/I counts + family tag chips + the no-analysis state sit on the existing card? | **A — Header + 3-col body** | card, library, games, flaws, mobile |
| 002 | flaw-stats-panel | How to arrange severity rates + tag distribution + trend + the analyzed denominator? | **A — Band → trend → tags** | panel, stats, library, charts, mobile |

## Decisions (winners)

**001 → Variant A (Header + 3-column body).**
- Player names sit in a **full-width card header** (platform link pinned right). On mobile the
  two names **stack on separate lines** (no "vs").
- **Desktop body = 3 columns**: board · game info (opening + metadata) · flaws (a dashed-divided
  right column). Flaw **counts use full labels on one line** — `[2 Blunders] [1 Mistake]
  [4 Inacc.]` — with the family-colored **tag chips** wrapping below. **No "Flaws" title.**
- **Mobile**: the flaws section stacks full-width under the board + info row; the metadata stacks
  vertically with the **game result as the last line**.
- **Tag-family colors** (clear of the severity red/orange/yellow): **tempo = violet**,
  opportunity = cyan, impact = magenta. Color = family; icon/label distinguishes members. Chips
  are **display-only in Phase 107** (Flaws deep-link target ships later).
- The **"no engine analysis"** state replaces the counts/chips for chess.com / unanalyzed games.

**002 → Variant A (Band → trend → tag distribution).**
- Top: a single row of **severity-rate cells** (blunders / mistakes / inaccuracies per game +
  result-changing %), with the **per-game / per-100-moves toggle** in the panel head and the
  **`% analyzed` + N denominator** pinned right.
- Middle: the full-width **trend chart** (blunders/game over time) — kept high because "am I
  blundering less?" is the headline insight.
- Bottom: the full **tag distribution** — tempo split (stacked violet bar), phase histogram,
  opportunity + impact rates.
- Order reads **how often → over time → of what kind**. Mobile reflows the band to stacked cells.
