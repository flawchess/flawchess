---
quick_id: 261003-ixu
mode: quick
seed: SEED-182
files_modified:
  - frontend/src/index.css
  - frontend/src/components/ui/card.tsx
  - frontend/src/components/ui/accordion.tsx
  - frontend/src/pages/Endgames.tsx
  - frontend/src/components/charts/*.tsx (in-card separators, border-none drops)
  - frontend/src/components/insights/EndgameInsightsBlock.tsx
  - frontend/src/components/library/TacticComparisonGrid.tsx
---

# SEED-182: card border + lighter header band on every `.charcoal-texture` surface

Sketch 007 winner S2. Executed inline (small, mechanical CSS change).

## Task 1: tokens + `.charcoal-texture` border
- `index.css` `:root`: `--card-edge` (white/8%), `--card-band` (white/3.5%), `--card-band-hover`; expose as Tailwind colors.
- `.charcoal-texture` (components layer): real 1px `border` in `--card-edge` (not an inset shadow; children with a
  background would paint over it). Utilities layer still wins, so `border-l-4` accent spines and
  `.persona-accent-frame` keep their own borders.

## Task 2: header bands + in-card separators
- `CardHeader` and `ACCORDION_TRIGGER_BAND` (its accordion sibling): `bg-black/20` → `bg-card-band`, separators → `border-card-edge`.
- In-card dividers on charcoal surfaces (`divide-border/40`, Endgame TC/type/time-pressure dividers) → `card-edge`.
- Drop `border-none` on charcoal accordion items so they get the border (AccordionItem's `not-last:border-b` becomes harmless).

## Verify
- `npm run lint && npm run build && npm test -- --run`
- Browser UAT at 390px: Endgames, Openings Stats, Library, Bots, Analysis. Edges visible, no doubled borders on
  accent-spine/persona cards, no layout jumps (brand TabsList, BoardControls, persona grid).
