/**
 * Shared helpers + constants for Phase 86 Endgame Metrics cards and Phase 87
 * per-type cards. Lifted from `EndgameScoreGapSection.tsx` per Phase 86 D-08
 * so the new cards and the legacy section can share one source of truth
 * during the transition; legacy file keeps its private copies until deletion
 * in Plan 86-05.
 *
 * Note: the legacy composite-skill helper (lines 155-165 of the source) is
 * intentionally NOT lifted here. Per Phase 86 D-04, the composite Endgame
 * Skill rate is now produced server-side via the `skill` / `opp_skill` fields,
 * and the frontend helper is retired in Plan 04+.
 */

import type { EndgameClass, MaterialBucket } from '@/types/endgames';

// Phase 87.4 (D-03 / D-04): presentation-layer affine that recenters the
// per-bucket Conv / Parity / Recov Score Gap bullets on a single visual zero
// without mutating the calibrated zone bands. Shift values are the midpoint
// of each metric's typical band (Conv: [-0.11, 0.00] → -0.055;
// Parity: [-0.04, +0.04] → 0; Recov: [+0.01, +0.11] → +0.06).
// gapColor on EndgameMetricCard continues to read raw (unshifted) values so
// zone tinting is unaffected — only the rendered value + neutral band shift.
// See .planning/notes/endgame-skill-dropped-conversion-elo.md for rationale.
export const SCORE_GAP_BUCKET_DISPLAY_SHIFT: Record<MaterialBucket, number> = {
  conversion: -0.055,
  parity: 0,
  recovery: 0.06,
} as const;

// One-sentence description per endgame class, shown in the TypeTable row's info
// popover (restored in the 238 UAT). `pawnless` is omitted because
// HIDDEN_ENDGAME_CLASSES keeps it out of the table.
export const ENDGAME_TYPE_DESCRIPTIONS: Record<Exclude<EndgameClass, 'pawnless'>, string> = {
  rook: 'Endgames with rooks as the only non-king, non-pawn pieces. The most common Endgame Type besides Mixed.',
  minor_piece: 'Endgames with bishops and/or knights as the only non-king, non-pawn pieces.',
  pawn: 'King and pawn endgames only. No other pieces remain on the board.',
  queen: 'Endgames where queens are the only non-king, non-pawn pieces.',
  mixed: 'Endgames with pieces from two or more piece types: rooks, minor pieces (bishops/knights), and queens (e.g. queen + rook, rook + knight).',
};

// Phase 87 (D-16): Hyphenated URL slug + testid suffix per endgame class. Powers
// the /endgames/games?type=... deep-link from each TypeTable row. Lifted verbatim from
// EndgameWDLChart.tsx:21-28; all 6 entries kept for completeness even though
// pawnless is filtered upstream by HIDDEN_ENDGAME_CLASSES.
export const ENDGAME_CLASS_TO_SLUG: Record<EndgameClass, string> = {
  rook: 'rook',
  minor_piece: 'minor-piece',
  pawn: 'pawn',
  queen: 'queen',
  mixed: 'mixed',
  pawnless: 'pawnless',
};

// Phase 87 (Plan 03 D-03): Pawnless endgames are rare (~0.5% of positions in
// prod) and per-user sample sizes are usually too small to be meaningful. Hidden
// from the Endgames tab UI and from the TypeTable rows. Classification
// stays in the DB so the class can be re-enabled without a reimport. Lifted
// from Endgames.tsx:53 so the orchestrator and the page share one source of
// truth.
export const HIDDEN_ENDGAME_CLASSES: ReadonlySet<EndgameClass> = new Set(['pawnless']);
