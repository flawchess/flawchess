---
type: quick
slug: tactic-explorer-desktop-horiz-move-list
status: complete
created: 2026-06-25
completed: 2026-06-25
---

# Summary: Desktop tactic-explorer horizontal move list

Brought the desktop `TacticLineExplorer` (opened from game cards and flaw cards) in line
with the mobile layout.

## What changed

- **Single-column desktop layout.** Replaced the two-column board / vertical `SanLadder`
  split with the same stacked layout mobile uses: header → board → `BoardControls` →
  horizontal `HorizontalMoveList`. Both surfaces now share one return branch (mobile keeps
  its own padding/scroll; the Dialog supplies `p-6`).
- **Board-sized modal.** Dialog narrowed `sm:max-w-4xl` → `sm:max-w-md` to fit the
  chessboard, keeping `max-h-[90vh]` so it grows taller to fit the move list below the
  controls. Board is `w-full aspect-square` on both surfaces.
- **3-line move list.** The horizontal list reuses the mobile 3-line height (`h-24`);
  `MOBILE_MOVE_LIST_HEIGHT` renamed to `MOVE_LIST_HEIGHT` since it's now shared.
- **No badge truncation on desktop.** Added a `noTruncate` prop to `TacticMotifChip` and
  pass `noTruncate={!isMobile}` from the explorer header, so `"allowed: hanging-piece"` is
  shown in full on desktop while mobile keeps the 16-char abbreviation.
- **Removed dead `SanLadder.tsx`** (its only consumer was the desktop ladder; knip would
  fail). Updated the stale comment reference in `moveNumberLabel.ts`.

## Tests

- Added an `Element.prototype.scrollIntoView` stub to the explorer test (jsdom gap; the
  desktop path now exercises `HorizontalMoveList`'s auto-scroll).

## Gate

Frontend green: `tsc -b` clean, lint 0 errors, knip clean, 1137 tests pass.
Backend untouched.

## Follow-up (same session)

- **Taller Game/Explore buttons.** The `Game` + `Explore` buttons on the game card
  (`LibraryGameCard`, mobile + desktop) and flaw card (`FlawCard`) dropped `size="sm"`
  (h-7) for the default Button size (h-8) so they match the import-page
  Games/Openings/Endgames quicklink buttons; their icons bumped `h-3.5` → `h-4` to match.
- **Mobile move-list height.** `MOVE_LIST_HEIGHT` `h-24` → `h-28 md:h-24`: the narrower
  mobile drawer wraps the 3-line content into a 4th row, so mobile gets extra height to
  avoid a scrollbar while the wider desktop modal keeps h-24.

- **Explore button into the Missed column (desktop game card).** On desktop the game
  card's Explore button moved from a row under all three tactic columns into the **Missed**
  column itself. Added an optional `footer` slot to `ChipColumn` + `TacticMotifGroup`;
  `chipsBlock` became `renderChipsBlock(missedFooter?)` so only the desktop instance injects
  the button (the shared mobile instance is unchanged, no duplicate `game-card-btn-explore`).
  The button gets a `mt-3` gap above it and spans the full Missed column width (`w-full`).
  Non-analyzed games (no Missed column) keep the standalone auto-width fallback button.

## Out of scope / notes

- Visual confirmation on a real desktop browser is a HUMAN-UAT step (not run here).
</content>
