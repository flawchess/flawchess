/**
 * Shared helpers + constants for the Endgame Metrics cards and the per-type cards.
 */

import type { EndgameClass, MaterialBucket } from '@/types/endgames';

// Presentation-layer affine that recenters the
// per-bucket Conv / Parity / Recov Score Gap bullets on a single visual zero
// without mutating the calibrated zone bands. Shift values are the midpoint
// of each metric's typical band (Conv: [-0.11, 0.00] → -0.055;
// Parity: [-0.04, +0.04] → 0; Recov: [+0.01, +0.11] → +0.06).
// Zone tinting reads the raw (unshifted) values; only the rendered value and
// neutral band shift.
export const SCORE_GAP_BUCKET_DISPLAY_SHIFT: Record<MaterialBucket, number> = {
  conversion: -0.055,
  parity: 0,
  recovery: 0.06,
} as const;

// One-sentence description per endgame class, shown in the TypeTable row's info
// popover. `pawnless` is omitted because
// HIDDEN_ENDGAME_CLASSES keeps it out of the table.
export const ENDGAME_TYPE_DESCRIPTIONS: Record<Exclude<EndgameClass, 'pawnless'>, string> = {
  rook: 'Endgames with rooks as the only non-king, non-pawn pieces. The most common Endgame Type besides Mixed.',
  minor_piece: 'Endgames with bishops and/or knights as the only non-king, non-pawn pieces.',
  pawn: 'King and pawn endgames only. No other pieces remain on the board.',
  queen: 'Endgames where queens are the only non-king, non-pawn pieces.',
  mixed: 'Endgames with pieces from two or more piece types: rooks, minor pieces (bishops/knights), and queens (e.g. queen + rook, rook + knight).',
};

// Hyphenated URL slug + testid suffix per endgame class. Powers
// the /endgames/games?type=... deep-link from each TypeTable row. All 6 entries are kept
// for completeness even though pawnless is filtered upstream by HIDDEN_ENDGAME_CLASSES.
export const ENDGAME_CLASS_TO_SLUG: Record<EndgameClass, string> = {
  rook: 'rook',
  minor_piece: 'minor-piece',
  pawn: 'pawn',
  queen: 'queen',
  mixed: 'mixed',
  pawnless: 'pawnless',
};

// Pawnless endgames are rare (~0.5% of positions in
// prod) and per-user sample sizes are usually too small to be meaningful. Hidden
// from the Endgames tab UI and from the TypeTable rows. Classification
// stays in the DB so the class can be re-enabled without a reimport.
export const HIDDEN_ENDGAME_CLASSES: ReadonlySet<EndgameClass> = new Set(['pawnless']);
