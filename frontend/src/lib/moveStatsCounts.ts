/**
 * Move Stats count derivation (Phase 179 Plan 02, SEED-112 D-05) — pure,
 * client-side reduction of the 7-category × 2-side count table from data
 * already on the wire (`GameFlawCard.flaw_markers` + `.eval_series`). No new
 * backend aggregation, no new fetch.
 *
 * `MoveStatCategory` is its own 7-valued type — NOT `FlawSeverity` (which
 * stays 3-valued per the cross-stack backend contract, see
 * `lib/moveQuality.ts`'s explicit anti-pattern warning) and NOT the unrelated
 * frontend-only `MoveQuality` type (`lib/moveQuality.ts`), which shares the
 * same 7 bucket *names* for a completely different live-engine-grading
 * concept. Do not import or merge with either.
 */

import { moverColorAtPly } from '@/lib/plyOwnership';
import type { EvalPoint, FlawMarker, FlawSeverity } from '@/types/library';

/** The 7 Move Stats categories: 4 positive best-move tiers + 3 severities. */
export type MoveStatCategory = 'gem' | 'great' | 'best' | 'good' | 'inaccuracy' | 'mistake' | 'blunder';

/** Literal board color — the absolute column identity (not user/opponent). */
export type MoveStatSide = 'white' | 'black';

/** The 4 positive best-move tiers (subset of `MoveStatCategory`). */
type MoveStatTier = 'gem' | 'great' | 'best' | 'good';

function emptySeverityCounts(): Record<FlawSeverity, number> {
  return { inaccuracy: 0, mistake: 0, blunder: 0 };
}

function emptyTierCounts(): Record<MoveStatTier, number> {
  return { gem: 0, great: 0, best: 0, good: 0 };
}

/**
 * Folds `flaw_markers` into per-side severity (I/M/B) counts, keyed by
 * `moverColorAtPly(m.ply)` — NOT `m.is_user` (D-08: this surface deliberately
 * surfaces both sides, reversing the user-scoped `isUserPly` convention used
 * elsewhere).
 *
 * Deliberately reads `flaw_markers` (not `game.severity_counts`) so this
 * table's I/M/B counts and the cycling machinery that walks the same
 * `flaw_markers` array share one source (RESEARCH Pitfall 1: `severity_counts`
 * is a separately-written oracle column with no test asserting it stays in
 * sync with `flaw_markers` for every game state).
 */
export function severityCountsBySide(
  markers: FlawMarker[],
): Record<MoveStatSide, Record<FlawSeverity, number>> {
  const out: Record<MoveStatSide, Record<FlawSeverity, number>> = {
    white: emptySeverityCounts(),
    black: emptySeverityCounts(),
  };
  for (const m of markers) {
    const side = moverColorAtPly(m.ply);
    out[side][m.severity]++;
  }
  return out;
}

/**
 * Folds `eval_series` into per-side positive-tier (gem/great/best/good)
 * counts, keyed by `moverColorAtPly(p.ply)`. Points with a null
 * `best_move_tier` (no candidate row, or classified "neither") are skipped.
 * Both sides included unconditionally (D-08) — opponent gems/greats/bests/
 * goods appear here even though every other surface (eval-chart dots, board
 * markers) stays user-scoped via `isUserPly`.
 */
export function tierCountsBySide(
  points: EvalPoint[],
): Record<MoveStatSide, Record<MoveStatTier, number>> {
  const out: Record<MoveStatSide, Record<MoveStatTier, number>> = {
    white: emptyTierCounts(),
    black: emptyTierCounts(),
  };
  for (const p of points) {
    if (p.best_move_tier == null) continue;
    const side = moverColorAtPly(p.ply);
    out[side][p.best_move_tier]++;
  }
  return out;
}
