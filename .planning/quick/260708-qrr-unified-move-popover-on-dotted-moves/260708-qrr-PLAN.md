---
quick_id: 260708-qrr
description: unified move popover on dotted moves
status: in-progress
---

# Quick Task 260708-qrr: Unified move popover on dotted moves

## Goal

When hovering a dotted move span (`ProseSpan`) in either the FlawChess Engine card
(`FlawChessAgreementVerdict`) or the Maia card (`MaiaMoveQualityBar`), show the SAME
unified popover with up to three color-coded, icon-led lines:

- ♞ (ChessKnight) **FlawChess (practical): `<FC eval>`** — gold/amber (`FLAWCHESS_ENGINE_ACCENT`)
- 🖥 (Cpu) **Stockfish (objective): `<SF eval>`** — blue (`STOCKFISH_ACCENT`)
- 👤 (User) **Maia (human): `<Maia prob>`** — violet (`MAIA_ACCENT`)

Whole-line font color (icon + text). A line whose value is unavailable for that move is
omitted entirely.

## Tasks

### Task 1 — Shared `UnifiedMovePopover` body component
- **files:** `frontend/src/components/analysis/UnifiedMovePopover.tsx` (new)
- **action:** Render three optional lines from pre-formatted string props
  (`practicalEval`, `objectiveEval`, `maiaProbability`), each `null`/omitted → line hidden.
  Icons from lucide (`ChessKnight`, `Cpu`, `User`), colors from `theme.ts`. `currentColor`
  icons so the row `style.color` tints the whole line. Keep `text-xs` (info-tooltip exception).
- **verify:** component compiles; `npx tsc -b`.
- **done:** file exists, exports `UnifiedMovePopover`.

### Task 2 — Wire into both card consumers
- **files:** `FlawChessAgreementVerdict.tsx`, `MaiaMoveQualityBar.tsx`
- **action:**
  - FlawChess card: replace both `*PickPopoverBody` inline `<div>`s with `UnifiedMovePopover`.
    FlawChess pick → all three (Maia prob from `rawProbBySan[fcSan]`); Stockfish pick →
    objective always, practical only when `matchedLine`, Maia from `rawProbBySan[sfSan]`.
  - Maia card: replace `ProseMoveSpan`'s string body with `UnifiedMovePopover` — objective =
    `formatVerdictEval(...)`, Maia = `move.maiaPct%`. FlawChess practical is not available in
    this component's inputs, so that line is omitted (per the omit rule).
- **verify:** `npm run lint`, `npm test`, `npx tsc -b`.
- **done:** both popovers render the unified format.

### Task 3 — Update tests
- **files:** `__tests__/FlawChessAgreementVerdict.test.tsx`, `__tests__/MaiaMoveQualityBar.test.tsx`
- **action:** Update popover-text regexes to the new `FlawChess (practical):` / `Stockfish
  (objective):` / `Maia (human):` format; add a Maia-line assertion for the FlawChess card.
- **done:** `npm test` green.

## must_haves
- truths: unified popover shared by both cards; unavailable lines omitted; whole-line colors.
- artifacts: `UnifiedMovePopover.tsx`; edits to the two consumers + their tests.
- key_links: `FLAWCHESS_ENGINE_ACCENT`, `STOCKFISH_ACCENT`, `MAIA_ACCENT` in `theme.ts`;
  `ProseSpan` popover shell.
