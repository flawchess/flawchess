// Curated troll-opening positions, keyed by user-side-only FEN piece-placement.
// Source: lichess.org/study/cEDAMVBB.pgn (hand-pruned to strict Bongcloud-tier per Phase 77 D-01).
// Regenerate with: npx tsx frontend/scripts/curate-troll-openings.ts
//   then hand-prune the candidate list before pasting into the Set literals below.
//
// Keys are derived via deriveUserSideKey(fen, side) in @/lib/trollOpenings — they are
// the FEN piece-placement field with opponent pieces stripped and empty squares
// re-canonicalized. Stable across opponent variations of the same user-side position.

export const WHITE_TROLL_KEYS: ReadonlySet<string> = new Set([
  // Bongcloud Attack — after 1.e4 e5 2.Ke2
  '8/8/8/8/4P3/8/PPPPKPPP/RNBQ1BNR',
  // Hammerschlag (Pork Chop / Fried Fox) — after 1.f3 e5 2.Kf2
  '8/8/8/8/8/5P2/PPPPPKPP/RNBQ1BNR',
  // Halloween Gambit — after 1.e4 e5 2.Nf3 Nc6 3.Nc3 Nf6 4.Nxe5
  '8/8/8/4N3/4P3/2N5/PPPP1PPP/R1BQKB1R',
  // Sodium Attack — after 1.Na3
  '8/8/8/8/8/N7/PPPPPPPP/R1BQKBNR',
  // Drunken Knight Opening — after 1.Nh3
  '8/8/8/8/8/7N/PPPPPPPP/RNBQKB1R',
  // Crab Opening — after 1.a4 e5 2.h4
  '8/8/8/8/P6P/8/1PPPPPP1/RNBQKBNR',
  // Double Duck Formation — after 1.f4 f5 2.d4 d5
  '8/8/8/8/3P1P2/8/PPP1P1PP/RNBQKBNR',
  // Creepy Crawly Formation — after 1.a3 e5 2.h3
  '8/8/8/8/8/P6P/1PPPPPP1/RNBQKBNR',
  // Reagan's Attack — after 1.h4
  '8/8/8/8/7P/8/PPPPPPP1/RNBQKBNR',
  // Napoleon Attack — after 1.e4 e5 2.Qf3
  '8/8/8/8/4P3/5Q2/PPPP1PPP/RNB1KBNR',
  // Grob Attack — after 1.g4 (manually added; not in cEDAMVBB study)
  '8/8/8/8/6P1/8/PPPPPP1P/RNBQKBNR',
  // Barnes Opening — after 1.f3 (manually added; not in cEDAMVBB study)
  '8/8/8/8/8/5P2/PPPPP1PP/RNBQKBNR',
]);

export const BLACK_TROLL_KEYS: ReadonlySet<string> = new Set([
  // Drunken Knight Variation — after 1.Nf3 f6 2.e4 Nh6
  'rnbqkb1r/ppppp1pp/5p1n/8/8/8/8/8',
  // Borg Defence (Reversed Grob) — after 1.e4 g5 (manually added; not in cEDAMVBB study)
  'rnbqkbnr/pppppp1p/8/6p1/8/8/8/8',
  // Fred Defence — after 1.e4 f5 (manually added; not in cEDAMVBB study)
  // Disabled because of false alarms for Dutch defense
  //'rnbqkbnr/ppppp1pp/8/5p2/8/8/8/8',
]);
