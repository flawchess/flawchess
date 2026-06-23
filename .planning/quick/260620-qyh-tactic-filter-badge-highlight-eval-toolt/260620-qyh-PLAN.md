---
quick_id: 260620-qyh
status: planned
---

# Quick Task 260620-qyh: tactic UI fixes

Three small frontend fixes for the tactic-tag feature (Games + Flaws tabs).

## Task 1 — active-filter ring on tactic-motif chips

**Problem:** Flaw-tag chips (`TagChip`) show a colored active-filter ring when their
tag is in the active flaw filter (`ACTIVE_FILTER_RING_CLASS`). Tactic-motif chips
(`TacticMotifChip`) do not, so selecting a tactic family as a filter doesn't
highlight the matching badges on the game/flaw cards.

**Fix:** In `TacticMotifChip`, subscribe to `useFlawFilterStore`, resolve the chip's
family via `TACTIC_FAMILY_FOR_MOTIF[motif]`, and apply `ACTIVE_FILTER_RING_CLASS`
(ring color = family color) when the family is in `flawFilter.tacticFamilies` and the
orientation filter (`either` / chip orientation) matches. Mirrors `TagChip`'s D-05
ring. No call-site changes (both Games and Flaws cards get it for free).

- files: `frontend/src/components/library/TacticMotifChip.tsx`
- verify: select a tactic family filter; matching tactic chips on cards show the ring
- done: tactic chips ring identically to flaw-tag chips when filtered

## Task 2 — missed/allowed prefix in eval-chart tooltip

**Problem:** The eval-chart flaw tooltip lists only the `allowed_tactic_motif`, with
no orientation prefix — inconsistent with the chips ("missed: fork" / "allowed: pin").

**Fix:** In `EvalChart`, build a `tooltipTactics` list from the active marker's
`allowed_tactic_motif` + `missed_tactic_motif` (beta-gated, family-mapped) and render
each `<li>` as `"<orientation>: <label>"` with the family icon/color. Replaces the
single allowed-only line.

- files: `frontend/src/components/library/EvalChart.tsx`
- verify: hover/scrub to a flaw ply with tactics; tooltip lists prefixed motifs
- done: tooltip motif lines read "missed: …" / "allowed: …"

## Task 3 — show tooltip when opening a game on a flaw ply

**Problem:** Opening a game via a flaw card parks the eval slider on the flaw ply
(`initialPly`) but the tooltip is interaction-gated, so nothing is shown on open.

**Fix:** In `EvalChart`, add a mount effect: when `initialPly != null`, set
`sliderFocused` true (and focus the slider on fine pointers for blur-to-dismiss),
mirroring the existing `commandedPly` reveal. Games tab (no `initialPly`) is unaffected.

- files: `frontend/src/components/library/EvalChart.tsx`
- verify: open a game from a flaw card; the flaw tooltip is visible immediately
- done: tooltip shows on open, dismissable as usual

## Verification

- `cd frontend && npm run lint && npx tsc -b && npm test -- --run`
</content>
</invoke>
