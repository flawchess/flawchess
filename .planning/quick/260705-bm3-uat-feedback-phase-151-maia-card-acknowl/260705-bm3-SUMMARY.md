---
quick_id: 260705-bm3
title: "UAT feedback phase 151 — Maia card, acknowledgements, tooltip, chart range + axis"
status: complete
date: 2026-07-05
---

# Quick Task 260705-bm3 — Summary

Applied the six phase-151 Maia UAT changes. Frontend-only.

## What changed

1. **ELO range → 600–2600** (`maiaEncoding.ts`). `MAIA_ELO_LADDER` now spans
   600–2600 step 100 (21 rungs), matching maiachess.com's presented range (user
   confirmed maiachess.com shows 600–2600). The slider and eval bar widen with it
   (both derive from the ladder). Doc comment flags that 600–1000 / 2100–2600 are
   extrapolation beyond the 151-01-validated 1100–2000 band.
2. **Adaptive y-axis** (`MovesByRatingChart.tsx`). New `computeYAxis` rounds the
   ceiling up to a nice step just above the peak shown probability (0 floor, capped
   at 100%) so curves fill the vertical space. X-axis spans 600–2600 automatically
   from the widened ladder data.
3. **Card wrap + header + tooltip** (`MaiaHumanPanel.tsx`). ELO selector + chart now
   sit in a charcoal `Card` whose `CardHeader` reads `<User> Human Move Probability
   <info>`, mirroring the engine card. The info tooltip: "Human-move predictions are
   based on [maia3](github.com/CSSLab/maia3). Check out [maiachess.com]()".
4. **Legal box removed**. `MaiaAttribution.tsx` + its test deleted; `showAttribution`
   prop and both call-site usages removed. The maia3 source link (AGPL offer-source)
   is preserved compactly in the tooltip.
5. **Card top aligns with board top** (`Analysis.tsx`). Desktop human column gets the
   same invisible player-bar spacer the engine column uses.
6. **Homepage acknowledgement** (`Home.tsx`). Added a "Maia Chess" `<li>` linking
   maiachess.com.

## Verification

- `npx tsc -b` — clean (prop signature change)
- Full frontend suite: **113 files / 1311 tests pass**
- `npm run lint` — 0 errors (3 pre-existing warnings in generated `coverage/`)
- `npm run knip` — clean (no dead exports after MaiaAttribution deletion)
- `npm run build` — succeeds
- Updated `maiaEncoding.test.ts` ladder assertion; replaced attribution tests in
  `MaiaHumanPanel.test.tsx` with header/tooltip assertions.

## Commits

- `9dda1179` widen ladder to 600–2600 (+ MaiaAttribution deletion)
- `f28fe32c` adaptive y-axis
- `ae442a1a` homepage acknowledgement
- card wrap + header tooltip + spacer + call sites (final code commit)

## Compliance note (for the user)

Removing the visible AGPL license box narrows on-page license disclosure to the
tooltip's maia3 source link. The formal AGPL-3.0 model notice should remain in the
README/LICENSE (LIC-02 precedent) — worth a quick confirm since this UAT drops the
in-app legal text.

## Not done (visual UAT)

Layout alignment and the tooltip look were verified via tests + build, not a live
browser drive — this task is itself UAT feedback, so final visual sign-off is the
user's (analysis page in game mode: card top vs board top; free-play tabs).
