---
quick_id: 260722-nlm
status: complete
date: 2026-07-22
commit: d1cddde2
---

# Quick Task 260722-nlm — Summary

Three Phase-184 follow-up fixes on the Bots surface. Frontend only.

## What changed

**1. Bot modal info icon** — `PersonaEloDisclosurePopover.tsx` traded lucide's
`Search` glyph for `HelpCircle`, matching `components/ui/info-popover.tsx`'s
default and the `TagChip`/`FlawCard` convention. Popover shell, testids, and
copy are untouched.

**2. Game-end dialog overflow** — `GameResultDialog.tsx`'s footer now carries
`sm:flex-col-reverse sm:justify-start`. The shared `DialogFooter` default
(`sm:flex-row sm:justify-end`) put "Analyze this game" + "New opponent" +
"Rematch &lt;Persona&gt;" on one line, which exceeds the dialog's `sm:max-w-sm`
(384px) and rendered the buttons outside the dialog border. Persona names are
variable-length, so a row layout can't be made safe — stacking at every
breakpoint is the fix, with the primary CTA on top and full-width buttons.
`GameResultStrip.tsx` (the mobile/dismissed surface with the same three
actions) got `flex-wrap` on its non-wrapping button row.

**3. Player rating above the roster** — `PersonaGrid` takes a new required
`playerRating: number | null` prop and renders "Your estimated blitz rating:
~NNNN" plus an `InfoPopover` disclosure above the style sections. `Bots.tsx`
feeds it `profile?.lichess_blitz_equivalent_rating ?? null` from the profile it
already fetches (no second `useUserProfile()` call). Guests / users with no
anchor see nothing — no placeholder copy.

## Verification

- Added a regression test asserting the dialog footer's resolved classes drop
  `sm:flex-row`/`sm:justify-end` and keep `sm:flex-col-reverse` — this proves
  the tailwind-merge override actually lands rather than assuming it.
- Added PersonaGrid coverage for both the shown and omitted rating-line
  branches; threaded `playerRating={null}` through the four pre-existing render
  calls.
- Full frontend gate green: `npx tsc -b`, `npx eslint src`, `npm run knip`,
  `npm test -- --run` (183 files, 2508 tests).
- Backend untouched — no pytest/ruff/ty run needed.

## Files

- `frontend/src/components/bots/PersonaEloDisclosurePopover.tsx`
- `frontend/src/components/bots/GameResultDialog.tsx`
- `frontend/src/components/bots/GameResultStrip.tsx`
- `frontend/src/components/bots/PersonaGrid.tsx`
- `frontend/src/pages/Bots.tsx`
- `frontend/src/components/bots/__tests__/GameResultDialog.test.tsx`
- `frontend/src/components/bots/__tests__/PersonaGrid.test.tsx`

## Notes

Not visually confirmed in a running browser — the layout fix is verified by the
class-resolution regression test, not a screenshot. Worth an eyeball on the next
`npm run dev`.
