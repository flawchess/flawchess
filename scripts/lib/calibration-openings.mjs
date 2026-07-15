#!/usr/bin/env node
/**
 * calibration-openings.mjs — curated opening-book FEN list (Phase 168, D-09).
 *
 * `blend = 1` bot play is deterministic argmax (Phase 166 D-06) — from a
 * single start position the harness would replay the identical game every
 * time, so every bot-vs-anchor matchup MUST draw from a fixed, diverse,
 * color-balanced set of opening start FENs (one per game, colors alternated,
 * reproducible under `--seed`). This is NOT sourced from the gem-elo
 * harness's Kaggle CSV (`temp/brilliants_no_stalemates.csv`) — that corpus is
 * tactical "brilliant move" positions (mid/endgame, wrong semantics for
 * opening theory).
 *
 * Every entry below is standard, well-known public opening theory (name +
 * ECO code + the resulting FEN after 2-6 half-moves), written from
 * confirmed chess facts — not copied from a licensed opening database (same
 * "confirmed facts, not copied source" discipline as
 * frontend/src/lib/maiaEncoding.ts's header comment). Every FEN was produced
 * by actually replaying the listed SAN moves through chess.js (so each is
 * guaranteed legal and reachable), spanning all four first-move families
 * (1.e4 / 1.d4 / 1.c4 / 1.Nf3) and a spread of open/semi-open/closed
 * structures (168-RESEARCH.md Open Question 1).
 *
 * `uci` is the move list from the STANDARD START to `fen` — required because
 * the app's /analysis deep-link (`?line=`, analysisUrl.ts) replays UCI moves
 * from the standard start only (`?fen=` wins over `?line=`; they never
 * compose), so a per-game analyze link must prefix the game's own moves with
 * the opening's. `assertOpeningBookUciPrefixes` (called once at harness
 * startup) replays every prefix and throws on any uci/fen drift.
 */

/** One curated opening: display name, ECO code, UCI moves from the standard start, and the resulting FEN. */
export const OPENING_BOOK = [
  {
    name: 'Italian Game',
    eco: 'C50',
    uci: ['e2e4', 'e7e5', 'g1f3', 'b8c6', 'f1c4', 'f8c5'],
    fen: 'r1bqk1nr/pppp1ppp/2n5/2b1p3/2B1P3/5N2/PPPP1PPP/RNBQK2R w KQkq - 4 4',
  },
  {
    name: 'Ruy Lopez',
    eco: 'C60',
    uci: ['e2e4', 'e7e5', 'g1f3', 'b8c6', 'f1b5'],
    fen: 'r1bqkbnr/pppp1ppp/2n5/1B2p3/4P3/5N2/PPPP1PPP/RNBQK2R b KQkq - 3 3',
  },
  {
    name: 'Ruy Lopez, Morphy Defense',
    eco: 'C70',
    uci: ['e2e4', 'e7e5', 'g1f3', 'b8c6', 'f1b5', 'a7a6', 'b5a4'],
    fen: 'r1bqkbnr/1ppp1ppp/p1n5/4p3/B3P3/5N2/PPPP1PPP/RNBQK2R b KQkq - 1 4',
  },
  {
    name: 'Scotch Game',
    eco: 'C45',
    uci: ['e2e4', 'e7e5', 'g1f3', 'b8c6', 'd2d4'],
    fen: 'r1bqkbnr/pppp1ppp/2n5/4p3/3PP3/5N2/PPP2PPP/RNBQKB1R b KQkq - 0 3',
  },
  {
    name: 'Petrov Defense',
    eco: 'C42',
    uci: ['e2e4', 'e7e5', 'g1f3', 'g8f6'],
    fen: 'rnbqkb1r/pppp1ppp/5n2/4p3/4P3/5N2/PPPP1PPP/RNBQKB1R w KQkq - 2 3',
  },
  {
    name: 'Four Knights Game',
    eco: 'C47',
    uci: ['e2e4', 'e7e5', 'g1f3', 'b8c6', 'b1c3', 'g8f6'],
    fen: 'r1bqkb1r/pppp1ppp/2n2n2/4p3/4P3/2N2N2/PPPP1PPP/R1BQKB1R w KQkq - 4 4',
  },
  {
    name: 'Vienna Game',
    eco: 'C25',
    uci: ['e2e4', 'e7e5', 'b1c3'],
    fen: 'rnbqkbnr/pppp1ppp/8/4p3/4P3/2N5/PPPP1PPP/R1BQKBNR b KQkq - 1 2',
  },
  {
    name: "King's Gambit",
    eco: 'C30',
    uci: ['e2e4', 'e7e5', 'f2f4'],
    fen: 'rnbqkbnr/pppp1ppp/8/4p3/4PP2/8/PPPP2PP/RNBQKBNR b KQkq - 0 2',
  },
  {
    name: 'Sicilian Defense, Open',
    eco: 'B50',
    uci: ['e2e4', 'c7c5', 'g1f3', 'd7d6'],
    fen: 'rnbqkbnr/pp2pppp/3p4/2p5/4P3/5N2/PPPP1PPP/RNBQKB1R w KQkq - 0 3',
  },
  {
    name: 'Sicilian Defense, Najdorf',
    eco: 'B90',
    uci: ['e2e4', 'c7c5', 'g1f3', 'd7d6', 'd2d4', 'c5d4', 'f3d4', 'g8f6', 'b1c3', 'a7a6'],
    fen: 'rnbqkb1r/1p2pppp/p2p1n2/8/3NP3/2N5/PPP2PPP/R1BQKB1R w KQkq - 0 6',
  },
  {
    name: 'Sicilian Defense, Dragon',
    eco: 'B70',
    uci: ['e2e4', 'c7c5', 'g1f3', 'd7d6', 'd2d4', 'c5d4', 'f3d4', 'g8f6', 'b1c3', 'g7g6'],
    fen: 'rnbqkb1r/pp2pp1p/3p1np1/8/3NP3/2N5/PPP2PPP/R1BQKB1R w KQkq - 0 6',
  },
  {
    name: 'French Defense',
    eco: 'C00',
    uci: ['e2e4', 'e7e6'],
    fen: 'rnbqkbnr/pppp1ppp/4p3/8/4P3/8/PPPP1PPP/RNBQKBNR w KQkq - 0 2',
  },
  {
    name: 'French Defense, Advance',
    eco: 'C02',
    uci: ['e2e4', 'e7e6', 'd2d4', 'd7d5', 'e4e5'],
    fen: 'rnbqkbnr/ppp2ppp/4p3/3pP3/3P4/8/PPP2PPP/RNBQKBNR b KQkq - 0 3',
  },
  {
    name: 'Caro-Kann Defense',
    eco: 'B10',
    uci: ['e2e4', 'c7c6'],
    fen: 'rnbqkbnr/pp1ppppp/2p5/8/4P3/8/PPPP1PPP/RNBQKBNR w KQkq - 0 2',
  },
  {
    name: 'Caro-Kann Defense, Advance',
    eco: 'B12',
    uci: ['e2e4', 'c7c6', 'd2d4', 'd7d5', 'e4e5'],
    fen: 'rnbqkbnr/pp2pppp/2p5/3pP3/3P4/8/PPP2PPP/RNBQKBNR b KQkq - 0 3',
  },
  {
    name: 'Scandinavian Defense',
    eco: 'B01',
    uci: ['e2e4', 'd7d5'],
    fen: 'rnbqkbnr/ppp1pppp/8/3p4/4P3/8/PPPP1PPP/RNBQKBNR w KQkq - 0 2',
  },
  {
    name: 'Pirc Defense',
    eco: 'B07',
    uci: ['e2e4', 'd7d6', 'd2d4', 'g8f6', 'b1c3', 'g7g6'],
    fen: 'rnbqkb1r/ppp1pp1p/3p1np1/8/3PP3/2N5/PPP2PPP/R1BQKBNR w KQkq - 0 4',
  },
  {
    name: 'Modern Defense',
    eco: 'B06',
    uci: ['e2e4', 'g7g6'],
    fen: 'rnbqkbnr/pppppp1p/6p1/8/4P3/8/PPPP1PPP/RNBQKBNR w KQkq - 0 2',
  },
  {
    name: 'Alekhine Defense',
    eco: 'B02',
    uci: ['e2e4', 'g8f6'],
    fen: 'rnbqkb1r/pppppppp/5n2/8/4P3/8/PPPP1PPP/RNBQKBNR w KQkq - 1 2',
  },
  {
    name: "Queen's Gambit Declined",
    eco: 'D30',
    uci: ['d2d4', 'd7d5', 'c2c4', 'e7e6'],
    fen: 'rnbqkbnr/ppp2ppp/4p3/3p4/2PP4/8/PP2PPPP/RNBQKBNR w KQkq - 0 3',
  },
  {
    name: "Queen's Gambit Accepted",
    eco: 'D20',
    uci: ['d2d4', 'd7d5', 'c2c4', 'd5c4'],
    fen: 'rnbqkbnr/ppp1pppp/8/8/2pP4/8/PP2PPPP/RNBQKBNR w KQkq - 0 3',
  },
  {
    name: 'Slav Defense',
    eco: 'D10',
    uci: ['d2d4', 'd7d5', 'c2c4', 'c7c6'],
    fen: 'rnbqkbnr/pp2pppp/2p5/3p4/2PP4/8/PP2PPPP/RNBQKBNR w KQkq - 0 3',
  },
  {
    name: "King's Indian Defense",
    eco: 'E60',
    uci: ['d2d4', 'g8f6', 'c2c4', 'g7g6', 'b1c3', 'f8g7'],
    fen: 'rnbqk2r/ppppppbp/5np1/8/2PP4/2N5/PP2PPPP/R1BQKBNR w KQkq - 2 4',
  },
  {
    name: 'Nimzo-Indian Defense',
    eco: 'E20',
    uci: ['d2d4', 'g8f6', 'c2c4', 'e7e6', 'b1c3', 'f8b4'],
    fen: 'rnbqk2r/pppp1ppp/4pn2/8/1bPP4/2N5/PP2PPPP/R1BQKBNR w KQkq - 2 4',
  },
  {
    name: 'Gruenfeld Defense',
    eco: 'D80',
    uci: ['d2d4', 'g8f6', 'c2c4', 'g7g6', 'b1c3', 'd7d5'],
    fen: 'rnbqkb1r/ppp1pp1p/5np1/3p4/2PP4/2N5/PP2PPPP/R1BQKBNR w KQkq - 0 4',
  },
  {
    name: "Queen's Indian Defense",
    eco: 'E12',
    uci: ['d2d4', 'g8f6', 'c2c4', 'e7e6', 'g1f3', 'b7b6'],
    fen: 'rnbqkb1r/p1pp1ppp/1p2pn2/8/2PP4/5N2/PP2PPPP/RNBQKB1R w KQkq - 0 4',
  },
  {
    name: 'Bogo-Indian Defense',
    eco: 'E11',
    uci: ['d2d4', 'g8f6', 'c2c4', 'e7e6', 'g1f3', 'f8b4'],
    fen: 'rnbqk2r/pppp1ppp/4pn2/8/1bPP4/5N2/PP2PPPP/RNBQKB1R w KQkq - 2 4',
  },
  {
    name: 'Dutch Defense',
    eco: 'A80',
    uci: ['d2d4', 'f7f5'],
    fen: 'rnbqkbnr/ppppp1pp/8/5p2/3P4/8/PPP1PPPP/RNBQKBNR w KQkq - 0 2',
  },
  {
    name: 'Benoni Defense',
    eco: 'A56',
    uci: ['d2d4', 'g8f6', 'c2c4', 'c7c5'],
    fen: 'rnbqkb1r/pp1ppppp/5n2/2p5/2PP4/8/PP2PPPP/RNBQKBNR w KQkq - 0 3',
  },
  {
    name: 'English Opening',
    eco: 'A10',
    uci: ['c2c4', 'c7c5'],
    fen: 'rnbqkbnr/pp1ppppp/8/2p5/2P5/8/PP1PPPPP/RNBQKBNR w KQkq - 0 2',
  },
  {
    name: 'English Opening, Reversed Sicilian',
    eco: 'A20',
    uci: ['c2c4', 'e7e5'],
    fen: 'rnbqkbnr/pppp1ppp/8/4p3/2P5/8/PP1PPPPP/RNBQKBNR w KQkq - 0 2',
  },
  {
    name: 'Reti Opening',
    eco: 'A04',
    uci: ['g1f3', 'd7d5', 'c2c4'],
    fen: 'rnbqkbnr/ppp1pppp/8/3p4/2P5/5N2/PP1PPPPP/RNBQKB1R b KQkq - 0 2',
  },
  {
    name: 'London System',
    eco: 'D02',
    uci: ['d2d4', 'd7d5', 'g1f3', 'g8f6', 'c1f4'],
    fen: 'rnbqkb1r/ppp1pppp/5n2/3p4/3P1B2/5N2/PPP1PPPP/RN1QKB1R b KQkq - 3 3',
  },
];

/**
 * Replays every entry's `uci` prefix from the standard start and throws if
 * any move is illegal or the resulting FEN differs from the committed `fen`
 * — fail-fast guard for the per-game `?line=` analyze links (a silent drift
 * would emit links that replay a DIFFERENT position than the game actually
 * started from). `Chess` is injected (the harness resolves the frontend-
 * vendored chess.js), matching `playGame`'s dependency style.
 */
export function assertOpeningBookUciPrefixes(Chess) {
  for (const opening of OPENING_BOOK) {
    const chess = new Chess();
    for (const uci of opening.uci) {
      try {
        chess.move({ from: uci.slice(0, 2), to: uci.slice(2, 4), promotion: uci.slice(4, 5) || undefined });
      } catch (err) {
        throw new Error(`OPENING_BOOK ${opening.name}: illegal uci ${uci}: ${err.message}`);
      }
    }
    if (chess.fen() !== opening.fen) {
      throw new Error(
        `OPENING_BOOK ${opening.name}: uci prefix replays to ${chess.fen()}, expected ${opening.fen}`,
      );
    }
  }
}
