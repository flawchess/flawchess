---
quick_id: 260708-qrr
description: unified move popover on dotted moves
status: complete
date: 2026-07-08
---

# Quick Task 260708-qrr Summary

## What changed

Hovering a dotted move span (`ProseSpan`) in either analysis card now shows the
**same unified popover**: up to three color-coded, icon-led lines.

- ♞ (ChessKnight) **FlawChess (practical): `<eval>`** — gold/amber (`FLAWCHESS_ENGINE_ACCENT`)
- 🖥 (Cpu) **Stockfish (objective): `<eval>`** — blue (`STOCKFISH_ACCENT`)
- 👤 (User) **Maia (human): `<prob>`** — violet (`MAIA_ACCENT`)

Whole-line color (icon inherits via `currentColor`). A line whose value is
unavailable for the hovered move is omitted.

## Files

- **New:** `frontend/src/components/analysis/UnifiedMovePopover.tsx` — the shared
  popover body; three optional pre-formatted string props.
- `FlawChessAgreementVerdict.tsx` — both `*PickPopoverBody` bodies now render
  `UnifiedMovePopover`. Maia probability threaded in from the already-available
  `rawProbBySan` (`formatMaiaProbability` helper). FlawChess pick → all three
  lines; Stockfish pick → objective always, practical only when the SF move was
  also FlawChess-ranked, Maia when known.
- `MaiaMoveQualityBar.tsx` — `ProseMoveSpan`'s string body replaced with
  `UnifiedMovePopover` (objective + Maia %).
- Tests updated to the new `FlawChess (practical):` / `Stockfish (objective):` /
  `Maia (human):` format; added Maia-line present/omitted assertions.

## Scope note

The Maia card's inputs (`perElo`, `qualityBySan`) carry Maia probabilities and
Stockfish grading but **no FlawChess practical eval**, so its popover omits the
FlawChess line (per the explicit omit-when-unavailable rule). Surfacing FlawChess
practical there would require threading the FlawChess ranked lines into that
component and matching by SAN — out of scope for this task.

## Verification

- `npx tsc -b` — clean.
- `npm run lint` — 0 errors (3 warnings are in generated `coverage/`, pre-existing).
- `npm run knip` — clean.
- `npm test -- --run` — 1620/1620 pass (24 in the two touched component test files).

## Follow-up (HUMAN-UAT)

- Visually confirm in-app: hover a dotted move in each card, check the three
  colored lines and icons render, and lines omit correctly when an engine is off.
- Dark-mode legibility: the shared popover surface is `bg-foreground`, which
  inverts to near-white in dark mode. Blue/violet stay legible; the gold FlawChess
  line (`L≈0.78`) reads a bit low-contrast on white. Tune the gold or give the
  popover a fixed dark surface if it reads weak on real devices.
