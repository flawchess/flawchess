---
sketch: 001
name: analyzed-game-card
question: "How do the analyzed-card additions (B/M/I severity counts + family-colored tag chips + the 'no engine analysis' state) sit on top of the existing GameCard, desktop + mobile?"
winner: "A"
tags: [card, library, games, flaws, mobile]
phase: 107
---

# Sketch 001: Analyzed Game Card

## Design Question
The Games subtab reuses the existing `GameCard` (charcoal-texture surface, WDL left-border,
mini result board, ■/□ names, opening line, metadata row). Phase 107 adds three things to it for
**analyzed** games: per-game **B/M/I severity counts**, a curated/deduped set of **family-colored
tag chips** (display-only in 107), and an explicit **"no engine analysis"** state for
chess.com / unanalyzed-lichess games. Where do these live so the card stays skimmable and the
flaw data never reads as part of the game metadata?

## How to View
open .planning/sketches/001-analyzed-game-card/index.html

Each variant renders desktop cards on the left and a phone-frame on the right, showing an
analyzed loss, an analyzed win, and a no-analysis card. Chips are clickable (toast shows the
future Flaws deep-link). Toolbar (bottom-right) constrains the page width.

## Variants
- **A: Inline flaw strip** — a dashed-divided, "Flaws"-labelled strip below the metadata holds the
  B/M/I counts then the tag chips. Flaw data gets its own zone; +1 row of height.
- **B: Right-rail count cluster** — desktop adds a right rail (echoing the endgame WDL-bar zone)
  with stacked, spelled-out counts; chips sit under the opening line. Mobile collapses the rail
  into the same inline strip as A.
- **C: Metadata-row badges** — counts append to the existing metadata wrap-row; chips form a second
  wrap-row beneath. Most compact, but counts compete with date/TC for attention.

## What to Look For
- Do the **severity counts** read instantly as "this game's mistakes," or blur into metadata?
- Is **color-by-family** (3 chip colors) skimmable, or do you want per-tag distinction?
- Does the **no-analysis** state read as "we lack evals" (not "clean game")?
- **Mobile**: do chips wrap acceptably, or cap the count and add a "+2" overflow?
- Vertical height cost vs. the existing card — A/B add a row; C stays tightest.
