---
created: 2026-05-15T00:00:00.000Z
title: Standardize Cpu icon usage on Endgame page (eval-derived metrics)
area: frontend
files:
  - frontend/src/components/charts/EndgameOverallEntryCard.tsx
  - frontend/src/components/charts/EndgameOverallPerformanceSection.tsx
  - frontend/src/components/charts/EndgameTypeCard.tsx
---

## Why

The Cpu icon is used inconsistently on the Endgame page. It currently
flags "Endgame Entry Eval" and the per-type "Score Gap" (added in
Phase 87.1) as eval-derived, but `Achievable Score`, `Achievable Score
Gap`, and `Endgame Score Gap` don't get the icon despite also being
computed from Stockfish eval (via the Lichess expected-score formula).

The original placement (after the value, like a unit symbol) only worked
for the raw eval in pawns. For metrics with an explicit unit (%, pp) a
trailing Cpu competes with the unit. Phase 87.1 already shifted to a
label-prefix placement for the per-type Score Gap — that's the pattern
to standardize on.

## Rule

**Cpu icon = "Stockfish eval is an input to this metric."**

- Placement: **before the row label**, sized `h-3.5 w-3.5`, `aria-hidden="true"`.
- Never on card titles (the per-row icons carry the signal).
- Never as a value suffix (that read as a unit symbol and doesn't generalize).

Apply to: Endgame Entry Eval, Achievable Score, Achievable Score Gap,
Endgame Score Gap, per-type Score Gap.
Do not apply to: Endgame Score, Conversion, Recovery, Parity (all
result-based).

## What

1. **`EndgameOverallEntryCard.tsx`**
   - Drop the Cpu icon from the card title `<h3>` "Eval at Endgame Entry".
   - Move the Cpu icon on the `Endgame Entry Eval` row from after the
     value to **before the label** (next to "Endgame Entry Eval:").
   - Add a Cpu prefix to the `Achievable Score` row label.

2. **`EndgameOverallPerformanceSection.tsx`**
   - Add a Cpu prefix to the `Achievable Score Gap` row label.
   - Add a Cpu prefix to the `Endgame Score Gap` row label.

3. **`EndgameTypeCard.tsx`**
   - No change. Per-type "Score Gap" already follows the rule.

4. Verify the same change is applied in any separate mobile markup
   (per CLAUDE.md: search for duplicated markup before considering the
   change complete). Endgame cards are responsive but mostly share a
   single tree — confirm rather than assume.

5. Update tests that snapshot/select on the Cpu icon placement if any
   break.

## Out of scope

- Card-title icons on other pages (Openings explorer, OpeningFindingCard,
  OpeningStatsCard). Same rule could apply later but is not required to
  ship this consistency fix.
- Adding a tooltip or legend that explains the Cpu icon's meaning to
  users. The popovers on each row already disclose the eval dependency
  in prose; a global legend is a separate UX decision.
