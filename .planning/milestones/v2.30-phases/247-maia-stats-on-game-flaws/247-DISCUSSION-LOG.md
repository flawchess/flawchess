# Phase 247: Maia Stats on game_flaws - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-11-08
**Phase:** 247-maia-stats-on-game-flaws
**Areas discussed:** Re-analysis semantics, Benchmark DB, Straggler catch-up

---

## Re-analysis semantics

| Option | Description | Selected |
|--------|-------------|----------|
| Re-score all | Every flaw scored fresh on each Maia-loaded apply | ✓ |
| Score new plies only | Keep surviving values, score only new plies (best/second can go stale) | |

| Option | Description | Selected |
|--------|-------------|----------|
| Preserve + unstamp | Surviving plies keep values by omission, new plies NULL, game stamp cleared | ✓ |
| Preserve only | Same, but stamp untouched (permanent gaps) | |
| Scripts score Maia too | Reclassifier scripts load Maia | |

## Benchmark DB

| Option | Description | Selected |
|--------|-------------|----------|
| Script-ready, run later | `--db prod|benchmark`, run only on prod now | ✓ |
| Run both in this phase | Plus ~12 h benchmark run before close | |
| Prod only | Story phase adapts the script | |

## Straggler catch-up

| Option | Description | Selected |
|--------|-------------|----------|
| Re-runnable script | Idempotent `stamp IS NULL` selector, reminder from reclassifier scripts | ✓ |
| Automatic drain tier | tier-4b-style catch-up on the prod backend | |

| Option | Description | Selected |
|--------|-------------|----------|
| Done after full run | Deploy go-forward, full backfill, catch-up re-run, coverage verified | ✓ |
| Script verified on a slice | Full run as a follow-up | |

## Claude's Discretion

Edge-case rows (guests, missing rating, missing best/second move, PGN replay failures), stamp column name, backfill
internals, go-forward wiring.

## Deferred Ideas

Benchmark-DB backfill run (data-story phase); automatic catch-up tier (revisit if stragglers accumulate).
