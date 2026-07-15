---
quick_id: 260712-r4s
status: complete
date: 2026-07-12
commit: b13a1d98
---

# Quick Task 260712-r4s — Summary

## What changed

`scripts/calibration-harness.mjs` gained a `--resume <prior.tsv>` flag
(SEED-097). A killed sweep leaves a durable prior TSV whose completed
`(bot_elo, bot_blend, anchor)` cells form a grid-order prefix (one `writeRow`
per cell, WR-01). `--resume` re-invokes the same command, reads that file, skips
every already-swept cell, fast-forwards the global `gameIndex` through the
skipped cells, and **appends** the remaining cells to the same file — so the
finished map is byte-identical to an uninterrupted run. Resuming refuses
(throws) on any mismatch of `--games-per-cell`, `--seed`, the D-11 budget, or
the grid axes, and on a truncated/schema-mismatched prior file.

## Files

- `scripts/calibration-harness.mjs`
  - `parseArgs`: new `--resume` flag (absolute-resolved path; `resume: null`
    default; reuses `requireFlagValue`, WR-02).
  - `openMainTsvWriter(filePath, { append })`: append mode opens with
    `flags: 'a'` and skips the header (fresh runs unchanged).
  - New resume section: `cellKey`, `readPriorTsvLines` (refuses a missing
    trailing newline = truncated final row, and a schema-mismatched header),
    `parsePriorRow` (reconstructs the full W/D/L + color-split tally and the
    anchorSpec), `loadPriorSweep` (validates games-per-cell / seed / budget /
    grid membership + duplicate cells; returns `{ completedKeys, rowByKey }`).
  - `main()`: builds the current grid's cell-key set; loads the prior sweep on
    `--resume`; points the main TSV at the prior file in append mode; the grid
    loop skips completed cells (advances `gameIndex` by `gamesPerCell` and
    pushes the reloaded row to `cellRows` so the summary spans the whole grid);
    the summary path is derived from the main path; the throughput report is
    skipped when zero games were played (all cells already complete).
  - Usage docblock updated with the `--resume` semantics.

## Design decisions

- **Explicit `--resume <path>`, not newest-file auto-detect.** SEED-097 offered
  auto-detect as an alternative; explicit is safer (no silent wrong-file
  footgun) and matches the WR-02 refuse-rather-than-guess discipline.
- **Append to the prior file, don't re-serialize it.** The prior bytes are left
  untouched and new rows are appended, so the completed prefix stays exactly as
  originally written — byte-identity to a from-scratch run follows from
  identical inputs (same seed → same games → same score formatting), with no
  lossy parse→re-emit round-trip.
- **Refuse a truncated final line.** A prior file not ending in `\n` means the
  crash cut the last row mid-line; appending would splice two rows, so it throws
  rather than silently corrupt the map.
- **`stockfish_procs` intentionally NOT validated.** Pool size affects
  throughput, not game outcomes (grade/eval are deterministic regardless of
  which pool process serves them), so a resume may use a different
  `--stockfish-procs`. Matches SEED-097's stated scope (seed + budget + grid).

## Verification

Real-engine (Maia ONNX + Stockfish WASM) end-to-end test, `blend=0` minimal grid
(`--elo 1100 --blends 0 --anchors maia1100,maia1300 --games-per-cell 1 --seed 7`):

- Uninterrupted run → file A (2 cells).
- Truncated A to header + first cell (simulated mid-sweep kill) → file B, then
  `--resume B` with the same command.
- **Main TSV byte-identical** (`diff A B` clean) — landmine #1 verified (skipped
  cell 1 advanced `gameIndex` 0→1, so cell 2 replayed at the same index).
- **Advisory summary byte-identical** — landmine #2 verified (whole-grid).
- Guard throws confirmed: seed mismatch, games-per-cell mismatch, changed grid
  axis, missing file, and truncated final line each refuse with a clear message.

`node --check` clean. Not covered by any linter/CI gate (`scripts/*.mjs` has no
root eslint config and no CI reference); `playGame` untouched so the on-demand
`calibration-determinism.check.mjs` is unaffected.

Commit: `b13a1d98`
