---
title: Calibration harness --resume flag (skip already-swept cells)
trigger_condition: Implement with /gsd-quick — small, self-contained change to scripts/calibration-harness.mjs
planted_date: 2026-07-12
source: Phase 168 follow-up (resumability gap surfaced while reviewing calibration-harness.mjs for a ~12h run)
---

# SEED-097: Calibration harness `--resume` flag

`scripts/calibration-harness.mjs` is **durable but not resumable**. Every run opens a NEW timestamped
file (`calibration-harness-${timestamp}.tsv`, ~line 737) and sweeps the full grid from `gameIndex = 0`
(~lines 759-800). There is no read-back, no skip-completed-cells, no `--resume`. So a killed 12h run,
re-invoked with the same command, **replays the entire grid from scratch into a fresh file** — the
WR-01 per-row durability only means completed rows aren't *lost*, not that the harness *continues*.

Add a `--resume <prior.tsv>` flag (or auto-detect the newest `calibration-harness-*.tsv` in `--out-dir`):
read the prior TSV, skip every `(bot_elo, bot_blend, anchor)` cell already present, and continue the
sweep with only the remaining cells — appending to the prior file (or a new file to be `cat`'d).

## Implementation landmines (get these right or resume silently corrupts the map)

1. **Fast-forward `gameIndex` through skipped cells — do NOT reset it.** Each game's opening, color, and
   RNG are derived from the GLOBAL running `gameIndex` (`deriveGameSeed(seed, idx)` ~line 96-98;
   `botIsWhite = idx % 2 === 0` ~line 697; `OPENING_BOOK[idx % len]` ~line 696), and `gameIndex`
   increments across ALL cells (threaded via `playCell`'s `nextGameIndex`). If resume skips a completed
   cell WITHOUT advancing `gameIndex` by that cell's `games-per-cell`, every remaining cell gets a
   different opening/color/seed than it would in an uninterrupted run → the resumed map is NOT the same
   experiment as a from-scratch run, and D-09 reproducibility is broken. Skipping a cell must still
   `gameIndex += gamesPerCell`.

2. **Load skipped cells' rows back into `cellRows` for the final `-summary.tsv`.** The advisory ELO
   summary (`emitEloSummary`, ~line 810-811) is computed at the end from the in-memory `cellRows`. On
   resume, `cellRows` would otherwise hold only the newly-played cells, so the summary would cover a
   partial grid. Parse the skipped rows from the prior TSV back into `cellRows` (they carry the full
   W/D/L needed) so the summary spans the whole grid.

3. **Cell identity key = `(bot_elo, bot_blend, anchor)`** — the first three TSV columns. `--games-per-cell`
   must match the prior run's for the skip to be sound; validate it against the prior TSV's rows (each
   row's `games` column) and throw (WR-02 discipline) if they disagree, rather than silently mixing
   grids.

4. **Guard against a changed grid/seed on resume.** The prior TSV rows carry `seed`, `max_nodes`,
   `max_plies`. If the resumed run's `--seed`/budget differ, refuse (throw) — resuming into a different
   experiment is a footgun, not a feature.

## Optional extension (only if cheap — otherwise leave for later)

Flip the durable write from per-CELL to per-GAME so a mid-cell crash loses one game, not a whole
matchup (~30 min for an expensive cell). Today `tsvWriter.writeRow` fires once per cell (~line 796),
after all `games-per-cell` games finish. This changes the artifact granularity (D-04 rows are per-cell
aggregates), so it needs a per-game checkpoint sidecar OR incremental cell-row rewriting — more than a
one-liner. Keep it OUT of the core `--resume` quick task unless it falls out naturally; cell-granularity
resume already removes the "restart from zero" pain.

## Scope

Small, self-contained, single file (`scripts/calibration-harness.mjs`) — a `/gsd-quick` task. No engine
or app changes. Verify by: run a small grid, kill it mid-sweep, `--resume` it, and confirm the final map
is byte-identical to an uninterrupted run of the same command (this is the whole correctness bar — it
directly exercises landmine #1). Reuses the existing `requireFlagValue`/`parsePositiveIntFlag` CLI
validation (WR-02) and the existing durable TSV writer.
