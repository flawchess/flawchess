---
quick_id: 260722-nlm
description: Bot modal info popover, game-end dialog layout fix, show player blitz ELO above bot roster
date: 2026-07-22
mode: quick
---

# Quick Task 260722-nlm

Three Phase-184 follow-up UI fixes on the Bots surface. Frontend only, no backend
or schema changes.

## Task 1 — Bot modal: search icon → info icon

**Files:** `frontend/src/components/bots/PersonaEloDisclosurePopover.tsx`

The persona detail dialog's ELO disclosure popover trigger currently renders a
`Search` glyph (Phase 184 CAL-05), which reads as "search for something" rather
than "explanation available". Swap it for lucide's `HelpCircle` — the project's
standard info-popover trigger glyph (`components/ui/info-popover.tsx` defaults to
it; `TagChip`/`FlawCard` follow the same convention).

- `action`: replace the `Search` import + `<Search className="h-4 w-4" />` usage
  with `HelpCircle`. Nothing else about the popover shell changes (same testids,
  same hover/tap behavior, same copy).
- `verify`: `npm test -- --run PersonaEloDisclosurePopover PersonaDetailSurface`
- `done`: no `Search` import remains in the bots directory; both popover tests pass.

## Task 2 — Game-end dialog: stack the action buttons

**Files:** `frontend/src/components/bots/GameResultDialog.tsx`,
`frontend/src/components/bots/GameResultStrip.tsx`

`DialogFooter`'s default is `flex-col-reverse ... sm:flex-row sm:justify-end`. At
`sm:` and up the three actions (Analyze this game / New opponent / Rematch
&lt;Persona&gt;) exceed the dialog's `sm:max-w-sm` (384px) width and visibly bleed
outside the dialog's rounded border — see the reported screenshot. Persona names
are variable-length, so no amount of shortening makes a row layout safe.

- `action`: keep the column layout at every breakpoint —
  `<DialogFooter className="sm:flex-col-reverse sm:justify-start">`. `cn`'s
  tailwind-merge resolves `sm:flex-col-reverse` over the base `sm:flex-row` and
  `sm:justify-start` over `sm:justify-end`. `flex-col-reverse` puts the primary
  (Rematch, or New opponent for a Custom game) on top and Analyze at the bottom;
  buttons stretch full width.
- `action`: mobile parity (CLAUDE.md "apply changes to mobile too") — the
  dismissed-state `GameResultStrip` has the same three actions in a
  non-wrapping `flex items-center gap-2` row that overflows on narrow screens.
  Add `flex-wrap` to that inner row.
- `verify`: `npm test -- --run GameResultDialog GameResultStrip`
- `done`: footer renders one button per row at all widths; existing dialog/strip
  tests pass unchanged.

## Task 3 — Show the player's estimated blitz ELO above the bot roster

**Files:** `frontend/src/components/bots/PersonaGrid.tsx`,
`frontend/src/pages/Bots.tsx`,
`frontend/src/components/bots/__tests__/PersonaGrid.test.tsx`

Persona cards show `~ELO` labels, but the player has no on-screen reference for
what "similar strength" means. `profile.lichess_blitz_equivalent_rating` (Phase
171 D-07 — the blitz-bucket anchor, already fetched by `BotsPage`'s single
`useUserProfile()` call and already passed to `SetupScreen` as
`normalizedRating`) is exactly that reference.

- `action`: add a required `playerRating: number | null` prop to `PersonaGrid`.
  When non-null, render a header row above the style sections:
  "Your estimated blitz rating: ~NNNN" plus the shared `InfoPopover`
  (HelpCircle) disclosing that it is estimated from imported games on an
  approximate Lichess blitz scale. When null (guest, or no rated games) render
  nothing — no placeholder, no "unknown" copy.
- `action`: `Bots.tsx` passes
  `playerRating={profile?.lichess_blitz_equivalent_rating ?? null}` from the
  profile it already has. No second `useUserProfile()` call.
- `action`: pass `playerRating={null}` in the four existing `PersonaGrid` render
  calls in its test file; add coverage for the shown/hidden branches.
- `verify`: `npm test -- --run PersonaGrid Bots`, `npx tsc -b`
- `done`: rating line renders above the first style section for a user with an
  anchor, is absent for `null`, and `text-xs` never appears inside the grid
  container (the existing font-floor test still passes — the InfoPopover body is
  portaled out of the container and only mounts on hover).

## Gate

`npm run lint`, `npx tsc -b`, `npm test -- --run`. Backend untouched, so no
pytest/ruff/ty run is needed.
