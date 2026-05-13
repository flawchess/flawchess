---
status: partial
phase: 85-section-1-games-with-vs-without-endgame-cards
source: [85-VERIFICATION.md]
started: 2026-05-13T21:25:00Z
updated: 2026-05-13T21:25:00Z
---

## Current Test

[awaiting human testing]

## Tests

### 1. Visual UAT of the 3-card Endgame Overall Performance section
expected: |
  Under the "Endgame Overall Performance" h2 on /endgames:
  - A question line "Do you perform better or worse when games reach an endgame?" with no section h3 or info-icon above the cards.
  - Three cards side-by-side on lg+: LEFT "Games ending in Middlegame", CENTER "At Endgame Entry", RIGHT "Endgame results".
  - On mobile (< 1024px) the three cards stack vertically.
  - Cards 1 and 3 each show a WDL bar + "Score: NN%" row with a bullet anchored at 50%.
  - Card 2 shows TWO rows only (no WDL bar): "Endgame entry eval: ±X.Xp" with Cpu icon, and "Achievable score: NN%".
  - An "Endgame Score Gap" tile sits below Card 2 on desktop (column 2) and after Card 3 on mobile.
  - Score values in Cards 1 and 3 are tinted (green or red) only when score is clearly lopsided AND n >= 10 AND p < 0.05.
  - No "Games with vs without Endgame" section h3 anywhere on the page.
  - No legacy WDL table (`Endgame | Games | Win/Draw/Loss | Score | Score Gap` headers).
  - The "Where you start" and "What you do with it" tiles from the old EndgameStartVsEndSection are gone.
  - Hovering the info icon on Cards 1/3 score row shows the 0.50 natural anchor explanation.
result: [pending]

## Summary

total: 1
passed: 0
issues: 0
pending: 1
skipped: 0
blocked: 0

## Gaps
