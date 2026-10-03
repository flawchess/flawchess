---
quick_id: 261003-ixu
status: complete
seed: SEED-182
commit: 75d660f46
date: 2026-10-03
---

# 261003-ixu: card border + lighter header band (SEED-182, sketch 007 S2)

Executed inline (no subagents; small mechanical CSS change).

## What changed
- `index.css`: new tokens `--card-edge` (white/8%), `--card-band` (white/3.5%), `--card-band-hover` (white/6%),
  exposed as Tailwind colors. `.charcoal-texture` now carries a real `1px solid var(--card-edge)` border
  (components layer, so utilities still win).
- `CardHeader` and `ACCORDION_TRIGGER_BAND` (its accordion sibling, also `bg-black/20` before): `bg-card-band`,
  separator `border-card-edge`. Plain insight header in `Endgames.tsx` likewise.
- In-card dividers on charcoal surfaces (`EndgameOverallPerformanceSection`, `EndgameTypeTcCard`,
  `EndgameTimePressureCard`, `EndgameMetricsByTcCard`) moved from `border/40` to `card-edge`.
- Call-site audit decisions:
  - `border-none` dropped from all charcoal accordion items (Endgames, insights, time pressure, metrics, type, tactic grid) so they get the edge.
  - `border border-border/20` dropped from `GameCard`, `LibraryGameCard`, `OpeningFindingCard`, `OpeningStatsCard`
    (they would otherwise have kept a 2% border, weaker than every other card). Widths unchanged for these.
  - `SidebarLayout` strip: dropped `border-r border-border`; the texture edge now draws it.
  - `Card accentColor` `border-l-4` spine and `.persona-accent-frame` keep winning (verified computed styles).
- Test selector updated in `EndgameTimePressureCard.test.tsx` (`bg-border/40` → `bg-card-edge`).

## Verification
- `npm run lint`, `npm run build`, `npm test -- --run` (4565 passed), `npm run knip`: green.
- Browser UAT (390px iframes, effective 353px viewport): Endgames, Openings Stats, Library, Analysis. Every
  `.charcoal-texture` computes a 1px white/8% border; library accent cards keep the 4px result spine; no
  horizontal page overflow; brand TabsList and header bands render correctly.
- Bots persona grid not exercised live (a resumable bot game blocked the grid; not discarded). Verified the
  `.persona-accent-frame` cascade with a synthetic element instead: accent border + glow win.

## Notes
- Pre-existing: on narrow screens the Opening Stats card footer ("231 Games") clips; border widths there are unchanged by this task.
