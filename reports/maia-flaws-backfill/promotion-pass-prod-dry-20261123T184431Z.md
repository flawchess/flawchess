# Promotion pass (dry) on prod

**Generated:** 2026-11-23 19:17:38 UTC
**Stopped early:** False

## Counters

- Candidates: 163656
- Would change: 0
- Loss up / down: 0 / 0
- Missed up / down: 0 / 0
- NULL to value / value to NULL: 0 / 0
- Type missed win to allowed loss: 0
- Type allowed loss to missed win: 0
- Board failures (ply not reached or fen mismatch): 4
- Guard misses (row rewritten between read and write): 0
- Sample checked / mismatches: 2000 / 0
- Sample mismatches listed (game_id, ply): none
- Pages: 82
- Elapsed: 1987.5 s

## Rule

D-01: a promotion credits the promoting side with the promoted piece minus the pawn (queen 8, rook 4, bishop or knight 2), a promotion with capture adds the captured piece; per-depth caps unchanged (D-02).

## Filter

D-07: blunders (severity 2, both sides) of line-stamped games with a promotion token in the refutation line (pv at ply + 1), the best line (pv or best_move at the flaw ply) or the played move (move_san contains '='). Stored-NULL rows included.

## Comparison

A row changes only when the recomputed pair, rounded to a 4-byte float, differs from the stored REAL pair. The write is a guarded UPDATE on the values read.

Undo log: none (dry run)
