---
created: "2026-03-22T08:06:48.654Z"
title: Refactor button brand colors to CSS variables
area: ui
files:
  - frontend/src/lib/theme.ts
  - frontend/src/index.css:78-118
  - frontend/src/pages/Openings.tsx
---

## Problem

Button brand colors (`#8B5E3C` / `#6B4226`) are defined as a JS string constant (`PRIMARY_BUTTON_CLASS`) in `theme.ts` with hardcoded Tailwind arbitrary values. This works but is not idiomatic Tailwind — arbitrary value classes must be string literals (Tailwind scans statically), so the hex values can't be interpolated from constants.

Board square colors (`darkSquareStyle`/`lightSquareStyle`) are fine in `theme.ts` since they're inline style objects for react-chessboard, not Tailwind classes.

## Solution

Move button brand colors to CSS variables in `index.css` using the existing `@theme inline` pattern:

1. Add `--brand: oklch(...)` and `--brand-dark: oklch(...)` to `:root` (convert `#8B5E3C` and `#6B4226` to OKLCH to match existing convention)
2. Register in `@theme inline` block as `--color-brand` and `--color-brand-dark`
3. Use `bg-brand hover:bg-brand-dark text-white` directly in JSX
4. Remove `PRIMARY_BUTTON_CLASS` and `PRIMARY_BG`/`PRIMARY_BG_HOVER` from `theme.ts`
5. Optionally add `.dark` variants if dark mode brand colors should differ
