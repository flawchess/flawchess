---
status: complete
quick_id: 260715-als
description: Fix WR-04 — inaccuracy-severity book ply renders no variation-tree marker
date: 2026-07-15
commit: 6d9c12b8
---

# Quick Task 260715-als — WR-04 book marker fix

## What was broken

Deferred code-review finding WR-04 from `172-REVIEW.md`. In the `moveListMarkers`
memo (`frontend/src/pages/Analysis.tsx`), the book-marker fold suppressed the book
badge for any ply whose merged entry had a non-null `severity`:

```ts
if (existing?.severity != null || existing?.gem === true) return;
```

But the variation tree's `resolveMarkerIcon` only draws a glyph for `blunder`/`mistake`
severities — there is no move-list glyph for `inaccuracy` (unlike the board, which draws
`!?`). A book ply carrying an inaccuracy-severity flaw *with a tactic motif* (the condition
under which `flawMarkerByNodeId` creates a `severity: 'inaccuracy'` entry, Analysis.tsx:1289)
therefore rendered **nothing** in the move list: no severity glyph, and the book badge was
suppressed. The board and tree surfaces also disagreed (board showed `!?`, tree blank).

## The fix

Defer only to entries that actually draw a move-list icon:

```ts
if (
  existing?.severity === 'blunder' ||
  existing?.severity === 'mistake' ||
  existing?.gem === true
)
  return;
```

An inaccuracy-only book ply now falls through to the book badge. The board fold was already
correct and was left untouched.

## Proof (RED→GREEN)

Added a page-level test in `Analysis.test.tsx` ("Book marker on an inaccuracy-severity ply")
that renders `/analysis` for a game whose sole book ply (`opening_ply_count: 1`) carries an
inaccuracy + missed-motif flaw, and asserts the variation tree shows the "Opening theory"
BookIcon title. The test must be page-level because the render side (`resolveMarkerIcon`) was
already correct — the defect lived in the fold that never produced `book: true`.

- Reverting the guard to `severity != null` → **RED** (`AssertionError: expected [] to include 'Opening theory'` — the ply renders no marker).
- With the fix → **GREEN**.

An earlier draft used `opening_ply_count: 2`; that masked the bug because the second (clean)
book ply always rendered its own book badge. Narrowed to a single book ply so the assertion is
load-bearing.

## Gate

`npx tsc -b --noEmit` clean, eslint clean on changed files, `npm run knip` clean, full suite
**2228 passed** (up one from the new test).

## Files

- `frontend/src/pages/Analysis.tsx` — book-fold guard
- `frontend/src/pages/__tests__/Analysis.test.tsx` — RED→GREEN page-level test

## Tracking

WR-04 marked resolved in `172-REVIEW.md` frontmatter (resolved list) and in the deferred-findings
todo. WR-01, WR-03, WR-05, WR-06 and IN-01..04 remain deferred.
