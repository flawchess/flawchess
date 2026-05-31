/**
 * Phase 98 (D-09/D-10/D-11): Shared primary-TC heuristic utility.
 *
 * Computes which time control is the user's "primary" TC by selecting the TC
 * with the highest time-weighted game count. The NOMINAL_DURATION weights
 * neutralize bullet's volume advantage — a player with 500 blitz games and 600
 * bullet games is considered a blitz player (500×180=90 000 > 600×60=36 000).
 *
 * Placed in frontend/src/lib/ so the Endgame ELO Timeline can later consume it
 * without importing from charts/ (D-11 placement decision).
 */

export const NOMINAL_DURATION: Record<
  'bullet' | 'blitz' | 'rapid' | 'classical',
  number
> = {
  bullet: 60,
  blitz: 180,
  rapid: 600,
  classical: 900,
};

/**
 * Pick the user's primary time control from per-TC category data.
 *
 * Returns the TC whose summed `total` × `NOMINAL_DURATION[tc]` is highest
 * among TCs that pass the `minGames` floor. Returns null when no TC has
 * enough games.
 *
 * @param categoriesByTc - Map from TC string to an array of category stats.
 *   Each element must have a `total` number field.
 * @param minGames - Minimum total games for a TC to be eligible.
 */
export function computePrimaryTc(
  categoriesByTc: Record<string, { total: number }[]>,
  minGames: number,
): 'bullet' | 'blitz' | 'rapid' | 'classical' | null {
  const TC_ORDER = ['bullet', 'blitz', 'rapid', 'classical'] as const;
  let bestTc: (typeof TC_ORDER)[number] | null = null;
  let bestScore = -1;
  for (const tc of TC_ORDER) {
    const tcTotal = (categoriesByTc[tc] ?? []).reduce(
      (sum, c) => sum + c.total,
      0,
    );
    if (tcTotal < minGames) continue;
    const score = tcTotal * NOMINAL_DURATION[tc];
    if (score > bestScore) {
      bestScore = score;
      bestTc = tc;
    }
  }
  return bestTc;
}
