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
| 003 | train-bot-guess-bubble | Where does the bot avatar + speech bubble carrying the guess prompt sit on a phone? | **A — Chat row under board, buttons inside the bubble** | train, bots, onboarding, mobile, SEED-166 |
| 004 | train-bot-verdict-and-score | How does a bot deliver the per-puzzle verdict with its return date, and sum up the session ahead of the reminder ask? | **Synthesis — bot row under the board, pills + action buttons inside the bubble; score bubble above the badge** | train, bots, reveal, score-screen, SEED-166 |

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

**003 → Variant A (Chat row under board).** Sketched 2026-09-13 for SEED-166 (Train first-session
retention, bot-narrated). 56px avatar + name on the left, speech bubble with a left tail on the
right, the two guess buttons live INSIDE the bubble so the prompt and the action read as one
message from the bot. Board stays fully visible above (no overlay: the position must be readable
to decide). First session = 3-bubble stepper (Tank welcomes → Hilda defines the two buttons →
Hilda closes and the buttons appear), regular sessions = one bubble. A piece dropped before the
guess nudges the bubble and swaps the copy to "Decide first, then move". Refinement noted: the two
buttons wrap to two lines at 375px inside the bubble; stack full-width or shorten labels. Prose
is placeholder, to be settled in discuss-phase.

**004 → Synthesis (A + buttons in the bubble + inline pills).** Reveal: the outcome bot's chat row
sits DIRECTLY under the board (above every card). The bubble = verdict sentence with the guess
and move point pills inline ("Good call on the position [+1], wrong move [+0]. We'll try this
one again in the next session."), then Analyze / Next (and Solution once the board departs the
reveal) on their own row INSIDE the bubble. Stern bots (Tank, Diesel, Gus) front 0–1 points,
friendly bots (Pip, Bruno, Shelly) 2–3; herring/filler verdicts never promise a return. The sound
toggle is dropped from the reveal (future settings page). First session: a second bubble from
Hilda between the verdict and the cards explains the cards (tap to highlight the line, step
through it) and the buttons. Score screen: the bot bubble REPLACES the "Session complete"
heading, lists what returns and when, explains spaced repetition and the reminder's purpose;
badge, points, next-session line and Remind me / Done follow. Later sessions get a one-line
bubble. Prose is placeholder, to be settled in discuss-phase.
