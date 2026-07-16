---
status: pending
created: 2026-07-15
source: 172-REVIEW.md
phase_origin: 172
priority: medium
resolves_phase: 175
---

# Phase 172 deferred code-review findings

The 3 criticals + WR-02 from `172-REVIEW.md` were fixed at phase close. These
lower-severity findings were deliberately deferred. Full detail in
`.planning/phases/172-background-gem-sweep-on-analysis-seed-106/172-REVIEW.md`.

## Warnings

- **WR-04 — RESOLVED (quick 260715-als):** a book ply carrying an inaccuracy-severity
  motif rendered NO badge at all in the variation tree. Fixed: the `moveListMarkers`
  book fold now defers only to entries that actually draw a move-list glyph
  (`severity === 'blunder' || 'mistake' || gem`), so an inaccuracy-only book ply falls
  through to the book badge. Board surface was already correct (`!?`) and untouched.
  Page-level test in Analysis.test.tsx proves it RED→GREEN.

## Warnings (deferred)

- **WR-01:** the sweep's 1000ms grade permanently suppresses the live path's 4000ms
  re-grade of a mainline ply, so mainline gem detection is strictly less accurate than
  Phase 163. Fix: make the sweep verdict provisional (let the visited-ply live grade
  overwrite it), or raise SWEEP_GRADING_MOVETIME_MS to the live cap. `Analysis.tsx:1548`.
- **WR-03:** `sweepCandidates` recomputes on every move-tree mutation (depends on `nodes`
  Map identity) — full chess.js replay + scheduler churn on every free move. Derive the
  parent-FEN list from `mainLine` only. `Analysis.tsx:1567-1576`.
- **WR-05:** the sweep re-grades mainline plies the live path already resolved (its skip
  set is its own `gemByPly` only). Pass live-resolved plies in and union them.
- **WR-06:** `resolveCandidate` is called from `useGemSweep` effects without being in any
  dep array and no eslint-disable — a latent stale-closure trap if its body ever reads a
  prop/state. Now also applies to the two new watchdog/fast-fail effects added in the
  CR-03 fix. Wrap in `useCallback([])` and list it.

## Info (deferred)

- IN-01: `resolveMarkerIcon`'s `isBook` return field is never read (dead field).
- IN-02: `UseGemSweepState.isSweeping` — consider surfacing a "sweeping…" indicator or drop.
- IN-03: `SweepDispatch`'s `done` variant is indistinguishable from `idle` at its call site.
- IN-04: book fold synthesizes `ply: -1` when the real ply index is available.
