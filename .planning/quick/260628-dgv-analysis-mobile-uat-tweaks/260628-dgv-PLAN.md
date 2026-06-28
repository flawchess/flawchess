---
quick_id: 260628-dgv
title: Analysis page mobile UAT tweaks
status: planned
date: 2026-06-28
---

# Quick 260628-dgv: Analysis page mobile view UAT tweaks

UAT feedback on the mobile `/analysis` takeover (3 items). User decisions captured
up front (AskUserQuestion):
- **Engine-line font:** allow `text-xs` for the two engine PV lines (deliberate
  exception to the CLAUDE.md `text-sm` floor, scoped to this dense surface).
- **Hide browser URL bar:** leave as-is — no reliable cross-browser JS way; PWA
  install is the only real path. No code change, documented.

## Task 1 — Remove the engine-lines vertical layout jump (loading → shown)

**Files:** `frontend/src/components/analysis/EngineLines.tsx`,
`frontend/src/pages/Analysis.tsx`

**Cause:** The mobile region shares `min-h-[60px]` between the loading skeleton and
the rendered PV rows, but rendered rows are taller (eval badge `py-0.5` + row `py-1`)
and `flex-wrap` lets chips wrap to extra visual rows — so height grows when lines
arrive.

**Action:** Add a `compact` prop to `EngineLines` + `EngineLinesSkeleton`:
- Eval badge + move chips + move-number labels use `text-xs` with zero vertical
  padding (`leading-4`) so each PV line is one deterministic ~16px row.
- Rows switch from `flex-wrap py-1` to `flex-nowrap overflow-x-auto py-0.5` so they
  never wrap vertically (horizontal scroll if too wide) — height is fixed.
- Shared compact min-height (`min-h-[44px]`) on the skeleton, the analyzing
  skeleton, and the rendered container so all three states are the same height →
  no jump.
- Desktop (non-compact) is unchanged (`text-sm`, wrap, current heights; its fixed
  `h-[88px]` card body never jumped anyway).
- Mobile usage in `Analysis.tsx` passes `compact` to the page-level loading
  skeleton and to `EngineLines`.

**Verify:** `npm run build` + `npm test`; visually the mobile engine region holds a
constant height through loading → analyzing → 2 lines.
**Done:** No vertical jump; engine lines are visibly smaller/denser on mobile.

## Task 2 — Board-controls footer styled like the main nav bar (no charcoal pill)

**Files:** `frontend/src/components/board/BoardControls.tsx`,
`frontend/src/pages/Analysis.tsx`

**Action:** Add a `flat` prop to `BoardControls` that drops the
`rounded-lg charcoal-texture` container styling. The mobile analysis footer (already
`border-t border-border bg-background`) passes `flat` so the buttons sit flat on the
bar like the bottom-nav items instead of inside a charcoal rounded pill. Desktop
analysis + Openings keep the charcoal pill (intentional chess.com pattern). The
shared `boardControls` element in `Analysis.tsx` becomes a small function taking
`flat` so mobile = flat, desktop = pill.

**Verify:** `npm run build` + `npm test`; desktop/Openings board controls unchanged.
**Done:** Mobile board controls render flat (no charcoal pill), reading as nav buttons.

## Task 3 — Browser nav/URL bar hiding (no-op, documented)

No code change. There is no reliable cross-browser JS API to force-hide the mobile
address bar; `h-[100dvh]` already fits the visible viewport so nothing scrolls to
trigger collapse. The supported path is installing the PWA (standalone, already
offered via the install banner). Recorded in SUMMARY.
