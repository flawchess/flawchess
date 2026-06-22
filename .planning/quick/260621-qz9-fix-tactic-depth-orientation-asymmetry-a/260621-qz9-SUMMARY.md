---
quick_id: 260621-qz9
status: complete
date: 2026-06-21
commits:
  - 47b4b0a3  # backend filter offset
  - 9754b127  # frontend display + preset rename
---

# Quick Task 260621-qz9 — Summary

Fix the tactic-depth orientation asymmetry (Option A) and relabel the depth presets.

## Problem

`game_flaws.missed_tactic_depth` (player's own best line, from the `flaw_ply` PV)
and `allowed_tactic_depth` (opponent's refutation, from the `flaw_ply+1` PV) both
store the **raw 0-based detector loop index within their OWN principal variation**.

On the FlawCard / LibraryGameCard miniboards, BOTH depth badges are anchored on the
same pre-flaw decision board (`flaw.fen`). Because the opponent's refutation line
starts one ply *later* (after the blunder is played), an allowed tactic at raw depth
`d` actually sits one ply deeper from that shared decision board than a missed tactic
at the same raw `d`. So they were not comparable — an allowed depth-0 (1-ply look:
your move, then opponent punishes = 2 plies of calculation) displayed identically to
a missed depth-0 (your own immediate move = 1 ply).

## Decision (Option A — locked before execution)

Keep the DB columns as the raw detector index. **No migration, no backfill, no change
to the detector or `flaws_service` write path.** Apply a +1 decision-anchored offset
for the ALLOWED orientation **at read time only**, in two places.

## Changes

### Backend (commit 47b4b0a3)
- `app/repositories/library_repository.py`:
  - New constant `ALLOWED_DECISION_DEPTH_OFFSET = 1` (with a why-comment).
  - `_tactic_orientation_pairs` now returns 4-tuples `(motif_col, conf_col, depth_col,
    depth_offset)` — `0` for missed, `+1` for allowed.
  - `_depth_in_range` takes a `depth_offset` param and compares `depth_col + offset`
    against the bounds (bare column when offset is 0).
- `app/repositories/query_utils.py`: the parallel Games-tab EXISTS filter site threads
  the same per-orientation offset, so the Games and Flaws filters agree.
- Tests: updated the SQL-compile assertions in `tests/test_library_repository.py` and
  `tests/test_query_utils.py` (allowed column now compiles as `allowed_tactic_depth +
  <param> <=/>=`), and added a per-orientation test asserting allowed is offset and
  missed is bare.

### Frontend (commit 9754b127)
- `frontend/src/lib/tacticDepth.ts`:
  - New `ALLOWED_DECISION_DEPTH_OFFSET = 1`, `TacticDepthOrientation` type, and
    `toDisplayDepthForOrientation(depth, orientation)` (missed = raw+1, allowed = raw+2).
    Plain `toDisplayDepth` kept as the missed/neutral default (used by `formatDepthSummary`).
  - Presets renamed `beginner/intermediate/advanced` → `low/medium/high`; labels
    `Low/Medium/High`; `DEPTH_DEFAULT_PRESET = 'medium'`. Raw range bounds unchanged
    (they bound the stored column on both orientations via the offsetting filter).
- `FlawCard.tsx` + `LibraryGameCard.tsx`: depth badges now call the orientation-aware
  helper (allowed reads +1 vs missed). `LibraryGameCard` had the same latent bug.
- `TacticDepthFilter.tsx`: summary-active check `!== 'intermediate'` → `'medium'`; info
  copy updated to Low/Medium/High.
- `useFlawFilterStore.ts`: comment updated (Intermediate → Medium default).
- Tests: `tacticDepth.test.ts` updated for the rename + new orientation-helper cases.

## Verification (full pre-merge gate)

- `ruff format` (2 files), `ruff check --fix`: clean.
- `ty check app/ tests/`: 14 diagnostics, **all pre-existing** (identical count on a
  stashed baseline; in `count_filtered_and_analyzed` call sites I did not touch). Zero
  new errors. Pre-existing ty debt on this branch is out of scope for this task — flagged.
- `pytest -n auto -x`: **2836 passed**, 15 skipped.
- Frontend: `npm run lint` clean, `npm test --run` **1079 passed**, `npm run build`
  (tsc) clean (preset rename ripple is type-safe), `npm run knip` clean.

## Notes / follow-ups

- The "High" preset upper bound is raw 11; an allowed raw-11 tactic now *displays* 13
  while still being included by High. Internally consistent, but worth a glance during
  UAT to confirm the High label reads sensibly.
- Beta-gated tactic UI — no behavior change for non-beta users.
