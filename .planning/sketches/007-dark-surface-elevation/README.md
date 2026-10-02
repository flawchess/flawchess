---
sketch: 007
name: dark-surface-elevation
question: "How should cards separate from the page in the dark theme so they stay distinguishable on a phone in sunlight?"
winner: "S2"
tags: [theme, dark-mode, surfaces, elevation, mobile, legibility]
---

# Sketch 007: Dark Surface Elevation

## Design Question
Today the page is `oklch(0.145)` ≈ `#0a0a0a` and cards are `--charcoal #161412` + 6% noise, with a
CardHeader band that is DARKER than the body (`bg-black/20`) and no border. Card/page fill contrast
is ≈1.08:1, so card edges vanish in sunlight. Containers stay as they are (owner decision); only
surface colors, outlines, header bands and shadows change.

## How to View
open .planning/sketches/007-dark-surface-elevation/index.html
(`?glare=25` presets the sun-glare veil)

## Variants
- **Current**: baseline for comparison.
- **A: Black page, glowing cards**: page stays `#0a0a0a`, card `#26221f`, 1px outline white/9%,
  header band white/3.5% (lighter than body), no shadow (a shadow can't show below near-black).
- **B: Charcoal page, raised cards**: page `#161412` (today's card tone), card `#2b2724`, outline
  white/7%, lighter header band, two-layer drop shadow.
- **S1 (round 2)**: Current surfaces + B's lighter header band + 1px card border in the in-card separator color (white/4%). Border too faint to see.
- **S2 (round 2) ★ WINNER**: same as S1 with the border AND in-card separator both at white/8%.
- **Tune**: sliders for page/card/raised levels, outline, shadow, header band, next to Current;
  shows the resulting values and the fill contrast.

## What to Look For
- Drag the **Sun glare veil** to 20–30%: do the card edges survive? The outline matters more than the fill.
- A and B have the same fill contrast (~1.25:1). The difference is how dark the page feels and whether the shadow reads.
- Third surface step: the "2862 of 2909 analyzed" chip, the accuracy pills, and the eval-chart well.
- Brown active tab pill and Filters button: does the brand brown still pop on a lighter page (B)?
- Game card green spine against the outline.

## Source context
Explore session 2026-10-02; baseline screenshots in `temp/theme-explore/` (gitignored).
Real tokens: `frontend/src/index.css` (`.dark`, `--charcoal`, `.charcoal-texture`),
`frontend/src/components/ui/card.tsx` (CardHeader band).

## Decision (2026-10-02)
**Winner: S2.** Keep today's page (`#0a0a0a`) and card (`#161412` + 6% noise) fills. Change only:
1. CardHeader band `bg-black/20` → `white/3.5%` (lighter than the body, so the card reads raised, not cut in).
2. A 1px card **border** at white/8% (= `border-border/80`, since `--border` is white/10%).
3. The in-card separator (CardHeader `border-b`, `divide-border/40`) raised to the same white/8% so border and separators match.

Implementation note: it must be a real `border`, not an inset `box-shadow`. Children with a background
(the header band) paint over an inset shadow and hide the edge (round-2 sketch bug).
`.charcoal-texture` is also used by non-Card surfaces (brand tabs, sidebar, persona cards, BoardControls),
so decide whether the border lives on `Card` only or on `.charcoal-texture`.
Rejected: A/B lifted surfaces. The owner prefers today's darkness, and the border carries sunlight legibility.
