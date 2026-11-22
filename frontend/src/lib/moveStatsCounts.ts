/**
 * Move Stats count derivation — pure,
 * client-side reduction of the 8-category × 2-side count table from data
 * already on the wire (`GameFlawCard.flaw_markers` + `.eval_series`). No new
 * backend aggregation, no new fetch.
 *
 * `MoveStatCategory` is its own 8-valued type — NOT `FlawSeverity` (which
 * stays 3-valued per the cross-stack backend contract, see
 * `lib/moveQuality.ts`'s explicit anti-pattern warning) and NOT the unrelated
 * frontend-only `MoveQuality` type (`lib/moveQuality.ts`), which shares most
 * of the same bucket *names* for a completely different live-engine-grading
 * concept. Do not import or merge with either.
 *
 * `flawMoveCategory` is the one place the display split lives: a blunder whose
 * facepalm score reaches the cut counts as "facepalm", every other blunder
 * stays "blunder" (disjoint, so Blunder + Facepalm equals the Lichess blunder
 * count). The move quality table, its cycle maps, the eval chart and the "???"
 * badge surfaces (game card, board badge, Explain bar) read it; surfaces that
 * carry the Lichess meaning (SeverityBadge, the Library Stats tiles, the Flaws
 * Timeline) keep `FlawSeverity` and must not import it.
 */

import { isFacepalmBlunder } from '@/lib/facepalm';
import { moverColorAtPly } from '@/lib/plyOwnership';
import type { EvalPoint, FlawMarker, FlawSeverity } from '@/types/library';

/**
 * A flaw marker's display category: the three severities with the blunder split
 * into Blunder ("??") and Facepalm ("???").
 */
export type FlawMoveCategory = FlawSeverity | 'facepalm';

/** The 4 positive best-move tiers (subset of `MoveStatCategory`). */
type MoveStatTier = 'gem' | 'great' | 'best' | 'good';

/** The 8 Move Stats categories: 4 positive best-move tiers + 3 severities + facepalm. */
export type MoveStatCategory = MoveStatTier | FlawMoveCategory;

/** Row order of the move quality table, Facepalm last after Blunder. */
export const MOVE_STAT_CATEGORY_ORDER: readonly MoveStatCategory[] = [
  'gem',
  'great',
  'best',
  'good',
  'inaccuracy',
  'mistake',
  'blunder',
  'facepalm',
] as const;

/** Literal board color — the absolute column identity (not user/opponent). */
export type MoveStatSide = 'white' | 'black';

/**
 * Classifies a flaw marker for display: 'facepalm' exactly when it is a blunder
 * whose facepalm score reaches the cut, else its severity. An unscored blunder
 * stays 'blunder'.
 */
export function flawMoveCategory(
  marker: Pick<FlawMarker, 'severity' | 'facepalm_score'>,
): FlawMoveCategory {
  if (marker.severity === 'blunder' && isFacepalmBlunder(marker.facepalm_score)) return 'facepalm';
  return marker.severity;
}

function emptySeverityCounts(): Record<FlawMoveCategory, number> {
  return { inaccuracy: 0, mistake: 0, blunder: 0, facepalm: 0 };
}

function emptyTierCounts(): Record<MoveStatTier, number> {
  return { gem: 0, great: 0, best: 0, good: 0 };
}

/**
 * Folds `flaw_markers` into per-side severity (I/M/B + Facepalm) counts, keyed by
 * `moverColorAtPly(m.ply)` — NOT `m.is_user` (this surface deliberately
 * surfaces both sides, reversing the user-scoped `isUserPly` convention used
 * elsewhere).
 *
 * Deliberately reads `flaw_markers` (not `game.severity_counts`) so this
 * table's I/M/B counts and the cycling machinery that walks the same
 * `flaw_markers` array share one source (`severity_counts`
 * is a separately-written flaw-count column with no test asserting it stays in
 * sync with `flaw_markers` for every game state).
 */
export function severityCountsBySide(
  markers: FlawMarker[],
): Record<MoveStatSide, Record<FlawMoveCategory, number>> {
  const out: Record<MoveStatSide, Record<FlawMoveCategory, number>> = {
    white: emptySeverityCounts(),
    black: emptySeverityCounts(),
  };
  for (const m of markers) {
    const side = moverColorAtPly(m.ply);
    out[side][flawMoveCategory(m)]++;
  }
  return out;
}

/**
 * Folds `eval_series` into per-side positive-tier (gem/great/best/good)
 * counts, keyed by `moverColorAtPly(p.ply)`. Points with a null
 * `best_move_tier` (no candidate row, or classified "neither") are skipped.
 * Both sides included unconditionally — opponent gems/greats/bests/
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
