/**
 * Mock data for the Train prototype (/train-sketch).
 *
 * THROWAWAY: this is a clickable mockup to align on the spaced-repetition
 * blunder-training UX with a GM coach. No backend, no real engine — every
 * position carries hand-authored "acceptable moves" and mock expected scores.
 * Expected scores are user-POV win expectancy in [0, 1] (the same Lichess
 * sigmoid the real app uses via eval_utils.eval_cp_to_expected_score).
 */

export type PuzzleKind = 'blunder' | 'miss' | 'red_herring';

export interface AcceptableMove {
  /** SAN as chess.js produces it (check/mate glyphs are stripped before compare). */
  san: string;
  /** User-POV expected score after this move, [0, 1]. */
  expectedScore: number;
  label: string;
}

export interface Puzzle {
  id: string;
  kind: PuzzleKind;
  /** Position with the user to move — they must find a better move than they played. */
  fen: string;
  userColor: 'white' | 'black';
  // --- game context (what the card shows) ---
  opponent: string;
  opponentRating: number;
  timeControl: string;
  playedAgo: string;
  // --- what happened in the actual game ---
  playedSan: string;
  /** User-POV expected score just before the decision (the opportunity). */
  preExpectedScore: number;
  /** User-POV expected score after the move actually played. */
  playedExpectedScore: number;
  // --- grading (empty `acceptable` ⇒ red herring, any legal move is fine) ---
  acceptable: AcceptableMove[];
  bestSan: string | null;
  // --- narration ---
  prompt: string;
  revealSolved: string;
  revealMissed: string;
  // --- FSRS mock ---
  nextReviewSolved: string;
  nextReviewMissed: string;
}

export const PUZZLES: Puzzle[] = [
  {
    id: 'p1',
    kind: 'blunder',
    fen: 'r1bqkbnr/pppp1ppp/2n5/4p2Q/2B1P3/8/PPPP1PPP/RNB1K1NR b KQkq - 4 3',
    userColor: 'black',
    opponent: 'knightmare_92',
    opponentRating: 1480,
    timeControl: 'Blitz 5+0',
    playedAgo: '3 days ago',
    playedSan: 'Nf6',
    preExpectedScore: 0.46,
    playedExpectedScore: 0.02,
    acceptable: [
      { san: 'g6', expectedScore: 0.47, label: 'Best' },
      { san: 'Qe7', expectedScore: 0.42, label: 'Also fine' },
      { san: 'Qf6', expectedScore: 0.4, label: 'Also fine' },
    ],
    bestSan: 'g6',
    prompt: 'White just played Qh5, threatening mate on f7. You have a move that holds — find it.',
    revealSolved:
      'Right idea. g6 hits the queen and shuts the mate down; Qe7 also covers f7. In your game you played Nf6, ignoring the threat.',
    revealMissed:
      'Nf6 walks into 4.Qxf7#. The moves that survive all defend f7: g6 (best), or Qe7 / Qf6.',
    nextReviewSolved: 'Next review in 4 days',
    nextReviewMissed: 'Next review tomorrow',
  },
  {
    id: 'p2',
    kind: 'miss',
    fen: 'rnb1kbnr/pppp1ppp/6q1/4p3/2B1P3/5N2/PPPP1PPP/RNBQK2R w KQkq - 6 4',
    userColor: 'white',
    opponent: 'rook_rollins',
    opponentRating: 1532,
    timeControl: 'Rapid 10+0',
    playedAgo: '5 days ago',
    playedSan: 'd3',
    preExpectedScore: 0.58,
    playedExpectedScore: 0.55,
    acceptable: [
      { san: 'Bxf7+', expectedScore: 0.96, label: 'Best — wins the queen' },
      { san: 'Nxe5', expectedScore: 0.8, label: 'Also strong' },
    ],
    bestSan: 'Bxf7+',
    prompt: 'Your opponent just played Qg6, a blunder. You were already a shade better — punish it.',
    revealSolved:
      'Bxf7+! Kxf7 Nxe5+ forks king and queen and wins it. Nxe5 at once also nets a pawn and a fierce initiative. In your game you played the quiet d3 and let the moment pass.',
    revealMissed:
      'Qg6 hung the game to 4.Bxf7+! Kxf7 5.Nxe5+, forking king and queen. Nxe5 immediately is also clearly winning. You played d3 and the chance was gone.',
    nextReviewSolved: 'Next review in 4 days',
    nextReviewMissed: 'Next review tomorrow',
  },
  {
    id: 'p3',
    kind: 'red_herring',
    fen: 'rnbq1rk1/ppp1bppp/4pn2/3p4/2PP1B2/2N2N2/PP2PPPP/R2QKB1R w KQ - 2 6',
    userColor: 'white',
    opponent: 'quiet_quintus',
    opponentRating: 1605,
    timeControl: 'Classical 30+0',
    playedAgo: 'yesterday',
    playedSan: 'e3',
    preExpectedScore: 0.53,
    playedExpectedScore: 0.53,
    acceptable: [],
    bestSan: null,
    prompt: 'A calm Queen’s Gambit Declined. Is there a tactic here? Play the move you would choose.',
    revealSolved:
      'Correct call: there is no tactic and no single best move. Solid developing moves like e3, Rc1 or Qc2 are all fine. Not every position hides a winning shot, and seeing that is a skill too.',
    revealMissed: '',
    nextReviewSolved: 'Next review in 6 days',
    nextReviewMissed: 'Next review in 6 days',
  },
];

export type Verdict = 'solved' | 'missed' | 'herring_ok';

const stripGlyphs = (san: string): string => san.replace(/[+#!?]/g, '');

interface GradeResult {
  verdict: Verdict;
  move: AcceptableMove | null;
}

/** Grade a user's move (SAN) against a puzzle. Red herrings accept any legal move. */
export function gradeMove(puzzle: Puzzle, san: string): GradeResult {
  if (puzzle.kind === 'red_herring') {
    return { verdict: 'herring_ok', move: null };
  }
  const target = stripGlyphs(san);
  const hit = puzzle.acceptable.find((m) => stripGlyphs(m.san) === target);
  return hit ? { verdict: 'solved', move: hit } : { verdict: 'missed', move: null };
}

export const KIND_LABEL: Record<PuzzleKind, string> = {
  blunder: 'Your blunder',
  miss: 'Missed punishment',
  red_herring: 'Spot-check',
};
