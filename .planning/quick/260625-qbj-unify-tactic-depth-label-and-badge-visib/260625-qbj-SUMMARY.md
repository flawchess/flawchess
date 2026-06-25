---
quick_id: 260625-qbj
title: Unify tactic depth-label + badge visibility behind one resolver
status: complete
date: 2026-06-25
---

# Quick Task 260625-qbj — Summary

## What changed

A depth number could render on the Tactic Line Explorer board for a tactic whose
badge was filtered out, because the badge and the depth label were derived by
**different** logic. Unified both behind one resolver so the divergence can't recur,
and fixed two latent instances of the same class.

### `frontend/src/lib/tacticComparisonMeta.ts`
- New `resolveVisibleTactic(orientation, motif, depth, filter?) => VisibleTactic | null`
  (`VisibleTactic = { motif, motifLabel, depthLabel: string | null }`). Single source of
  truth: the chip and the depth badge read from the same nullable object, so a depth can
  never render without its paired chip.
  - Always applies the family guard (family-less motifs → null; their chip self-nullifies).
  - When `filter` is supplied, applies `slotPassesFilter`, mirroring the backend
    `tactic_slot_visible` axis-for-axis: orientation scope, family narrowing, and the
    decision-anchored depth range (full-range short-circuit + `+1` allowed offset).
  - `depthLabel` set only when `depth != null` (chip can show without a board number).
- `tacticDepthBadge` reduced to a thin delegate over `resolveVisibleTactic` (no filter),
  so `LibraryGameCard`'s call sites are byte-for-byte equivalent.

### `frontend/src/components/library/TacticLineExplorer.tsx`
- Deleted the local `tacticOrientationPasses` (and its now-dead imports). `hasMissed` /
  `hasAllowed` and both root-arrow depth labels now derive from `missedVisible` /
  `allowedVisible` (the resolved objects), so the depth label is gated by the same
  decision as the badge. This also brought the explorer into exact agreement with the
  backend depth-range semantics (the allowed `+1` offset it previously omitted).

### `frontend/src/components/library/FlawCard.tsx`
- Replaced the inline depth-label derivation with `tacticDepthBadge(...)`, gaining the
  family guard — a family-less motif (promotion, self-interference) no longer paints a
  bare depth number with no chip.

### `frontend/src/lib/__tests__/resolveVisibleTactic.test.ts` (new)
- Pins the resolver to the backend predicate: family guard, depth-null (chip-yes /
  badge-no), `tacticDepthBadge` delegation, orientation scope, family narrowing,
  full-range skip, and the decision-anchored depth range with the `+1` allowed offset
  (the FE↔BE parity case).

### `frontend/src/components/library/__tests__/FlawCard.test.tsx`
- Fixed an unrealistic fixture (depth set with `missed_tactic_motif: null`) to include a
  motif — the detector always writes motif + depth together, and the depth badge is now
  family-guarded.

## Verification
- `npx tsc -b` clean, `npm run lint` 0 errors, `npm run knip` clean, `npm test -- --run`
  1150 passed (95 files).
- No display change on the server-filtered Games/Flaws surfaces (their slots are already
  nulled server-side); the explorer now matches them and the backend.

## Out of scope / follow-up
- The tactic-lines API still returns both raw lines un-nulled, forcing the explorer to
  re-filter client-side (the FE copy of `tactic_slot_visible`). Having the API null its
  own slots would delete the client predicate entirely — a larger, separate change.
