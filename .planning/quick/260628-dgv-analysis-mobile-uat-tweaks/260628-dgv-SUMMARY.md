---
quick_id: 260628-dgv
title: Analysis page mobile UAT tweaks
status: complete
date: 2026-06-28
commit: c215a4ac
---

# Quick 260628-dgv — Summary

UAT round-7 follow-up on the mobile `/analysis` takeover. Three items; two
implemented, one is a documented no-op.

## Upfront decisions (AskUserQuestion)

- **Engine-line font:** allow `text-xs` for the two engine PV lines — a deliberate,
  user-approved exception to the CLAUDE.md `text-sm` floor, scoped to this dense
  engine surface only. Desktop engine lines stay `text-sm`.
- **Hide browser URL bar:** leave as-is — no reliable cross-browser JS way; PWA
  install (already offered) is the only real path.

## Item 1 — Engine-lines vertical jump (loading → shown) ✅

`EngineLines` + `EngineLinesSkeleton` gained a `compact` prop:
- `text-xs` eval badge / move chips / move-number labels with zero vertical padding
  (`leading-4`) → one ~16px row per PV line.
- Rows switch from `flex-wrap py-1` to `flex-nowrap overflow-x-auto py-0.5` so a long
  line scrolls horizontally instead of wrapping to a taller block — height is
  deterministic.
- Shared `min-h-[44px]` across the page-level loading skeleton, the in-component
  analyzing skeleton, and the rendered rows → the region is the same height in every
  state, so there is no jump when lines arrive.
- `Analysis.tsx` mobile passes `compact` to the loading skeleton and `EngineLines`.
- Desktop (non-compact) unchanged: `text-sm`, wrapping, `min-h-[60px]`; its fixed
  `h-[88px]` card body never jumped anyway.

## Item 2 — Board-controls footer styled like the main nav ✅

`BoardControls` gained a `flat` prop that drops the `rounded-lg charcoal-texture`
pill. The mobile analysis footer (already `border-t border-border bg-background`)
passes `flat` so the Reset/Back/Forward/Flip buttons sit flat on the bar, reading
like the bottom-nav items. The shared `boardControls` element in `Analysis.tsx`
became a small `(flat = false) =>` function: mobile footer calls `boardControls(true)`,
desktop right column calls `boardControls()`. Desktop analysis + both Openings
callers keep the charcoal pill (intentional chess.com pattern).

## Item 3 — Hide browser nav/URL bar ⊘ (no-op, documented)

No code change. There is no reliable cross-browser JS API to force-hide the mobile
address bar, and the takeover's `h-[100dvh]` already fits the visible viewport so
nothing scrolls to trigger the browser's scroll-to-collapse behavior. Making the
page artificially scrollable (the only "trick") is fragile, reappears on scroll-up,
and is broken on modern iOS Safari — not worth degrading the carefully-fitted
layout. The supported way to drop the browser chrome is installing the PWA
(standalone), already offered via the install banner.

## Verification

- `npx tsc -b` — clean
- `npm run lint` — 0 errors (only pre-existing warnings in generated `coverage/`)
- `npm run knip` — clean
- `npm test -- --run` — 103 files / 1214 tests pass

## Files changed

- `frontend/src/components/analysis/EngineLines.tsx` — `compact` prop + variants
- `frontend/src/components/board/BoardControls.tsx` — `flat` prop
- `frontend/src/pages/Analysis.tsx` — mobile passes `compact`; `boardControls(flat)`

## Follow-up notes

- Mobile board-control buttons keep their icon-only `sm` size; if you want them to
  fill the bar width like the labeled nav items (flex-1, larger tap targets), that's
  a small follow-up.
