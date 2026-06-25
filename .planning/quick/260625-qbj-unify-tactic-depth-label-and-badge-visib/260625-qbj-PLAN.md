---
quick_id: 260625-qbj
title: Unify tactic depth-label + badge visibility behind one resolver
status: in-progress
date: 2026-06-25
---

# Quick Task 260625-qbj

## Problem

On the tactic Explore board (`TacticLineExplorer`), a depth number can render on a
square whose tactic badge is filtered out. Root cause: the depth label and the badge
are derived by **different** logic. The badge is gated by `tacticOrientationPasses`
(the live flaw filter); the depth label is derived straight from the API response and
never re-checked. Two more instances of the same class exist:

- **FlawCard** builds depth labels with no family guard, but `TacticMotifChip` returns
  `null` for family-less motifs → a family-less motif (promotion, self-interference)
  paints a bare depth number with no chip.
- The frontend depth-range check omits the `+1` decision-anchored offset that the
  backend `tactic_slot_visible` applies to the *allowed* slot → latent FE↔BE drift.

## Goal

One shared client-side resolver is the single source of truth for "is this tactic
slot shown, and what is its depth badge". The chip and the depth number can never
diverge because both read from the same nullable object. Behavior on the
server-filtered Games/Flaws surfaces is unchanged (their slots are already nulled
server-side); the explorer is brought into exact agreement with the backend predicate.

## Tasks

### Task 1 — Shared resolver (Tier 2 core)
**Files:** `frontend/src/lib/tacticComparisonMeta.ts`

- Add `resolveVisibleTactic(orientation, motif, depth, filter?) => VisibleTactic | null`
  where `VisibleTactic = { motif, motifLabel, depthLabel: string | null }`.
  - Always applies the family guard (family-less → null; mirrors `tacticDepthBadge`).
  - When `filter` (a `FlawFilterState`, type-only import) is supplied, additionally
    mirror backend `tactic_slot_visible`: orientation scope, family narrowing, and the
    decision-anchored depth range (full-range short-circuit; `+1` offset on allowed).
  - `depthLabel` is set only when `depth != null`, so a chip with no depth still shows
    without a board number.
- Reduce `tacticDepthBadge` to a thin delegate:
  `resolveVisibleTactic(orientation, motif, depth)?.depthLabel ?? null` (keeps every
  existing `LibraryGameCard` call site byte-for-byte equivalent).

### Task 2 — Route the three surfaces through it (Tier 1 fix + Tier 2 migration)
**Files:** `frontend/src/components/library/TacticLineExplorer.tsx`,
`frontend/src/components/library/FlawCard.tsx`

- **TacticLineExplorer:** replace the local `tacticOrientationPasses` + the parallel
  `missedDepthLabel`/`allowedDepthLabel` derivations. Compute `missedVisible` /
  `allowedVisible` via `resolveVisibleTactic(..., flawFilter)`; derive `hasMissed` /
  `hasAllowed` and both depth labels from those objects (label gated by has*). Delete
  the now-dead `tacticOrientationPasses` and any imports it alone used.
- **FlawCard:** replace the inline depth-label derivation with `tacticDepthBadge(...)`
  (gains the family guard, fixing the family-less leak; no other change).

### Task 3 — Unit test pinning resolver = backend predicate
**Files:** `frontend/src/lib/__tests__/resolveVisibleTactic.test.ts` (new)

- Cover: family-less guard, depth-null (chip-yes / badge-no), no-filter path =
  `tacticDepthBadge`, orientation scope, family narrowing, full-range skip, and the
  decision-anchored depth range with the `+1` allowed offset (the FE↔BE parity case,
  e.g. allowed raw depth 5 with max 5 → hidden because `5+1 > 5`).

## Verification
- `npx tsc -b` (shared type change), `npm run lint`, `npm run knip`, `npm test -- --run`
  all green.
- Manual: game 681495 ply 22 under {blunders, depth 1-5, sacrifice} shows the missed
  sacrifice badge + depth and NO bare depth for the allowed trapped-piece.

## Out of scope
- Backend changes. Making the tactic-lines API null its own slots (would remove the
  client predicate entirely) is a larger change — left as a follow-up note.
