---
quick_id: 261125-v4k
title: "Foldables: bot game bottom bar and two columns, Analysis landscape fit"
status: complete
date: 2026-11-25
commit: cd0d06f57
---

# Summary

Planned and executed inline (no planner/executor agents).

- Usable sizes derived from two device screenshots (inner landscape 933x617, cover 475x663) and reproduced in iframes: same cut-off strip, same 42px move list.
- Bot game: no page scroll at 933x617, 816x528, 704x845, 616x728, 475x663, 416x569, 375x647, 375x553. The side column sits in the board's grid row with absolute content: a long move list used to stretch the row and collapse the board to 240px (also on desktop).
- Analysis: `useBoardStageSize` takes a height budget when the footer is pinned, and its width budget from `<main>` because the board column is now only as wide as the board. Board 441 to 395px at 933x617.

# Verification

Lint, build, knip, full frontend suite (6924 tests). Landscape bar test mutation-checked. Not checked: a real iPhone PWA (safe-area insets), the Fold after the landscape changes.

# Follow-ups

`docs/mobile-foldable-layout.md` lists what is left; next is the Analysis board cap in portrait.
