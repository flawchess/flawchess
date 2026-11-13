/**
 * blunderCheckSolution: the pure chip model of the blunder-check solution screen (Phase 249, D-14).
 *
 * The screen shows up to three lines like a personalized puzzle's reveal: Your (the better move
 * the user found after a catch), Best (the server key) and Game (the move that was played: the
 * blunder, or the good move a false alarm flagged). Roles whose first move coincides merge into
 * one chip (labelled "Your = Best", for example), exactly as the Train reveal does. React-free so it unit-tests
 * without a DOM. Every line is a browser-engine search (`startGameMoveSearch`), never a stored
 * server line.
 */

import { Chess } from 'chess.js';
import type { Move } from 'chess.js';

import type { SoundEvent } from '@/lib/sounds';
import { buildTrainRevealOverlay } from '@/lib/trainArrows';
import type {
  TrainFineMove,
  TrainMoveQuality,
  TrainRevealOverlay,
} from '@/lib/trainArrows';
import { CANONICAL_ROLE_ORDER, ROLE_SHORT_LABELS, sanFromUci } from '@/lib/trainRevealLines';
import type { ChipGroup, GameMoveLineState, RoleKey } from '@/lib/trainRevealLines';
import type {
  BetterMoveTier,
  BlunderSolution,
  FalseAlarmSolution,
  HerringSolution,
  LinesSolution,
  WindowSolution,
} from '@/types/blunderCheck';

/** A graded better move as a chip quality: the same three tiers as a personalized puzzle's move. */
const BETTER_MOVE_QUALITY: Record<BetterMoveTier, TrainMoveQuality> = {
  good: 'good',
  inaccuracy: 'inaccuracy',
  wrong: 'mistake',
};

/** The most "also good" arrows the solution board draws next to the best move. */
export const BLUNDER_CHECK_ALT_MOVE_ARROWS = 3;

/**
 * The moves that were also good at the blunder position: the server's good-tier graded moves,
 * without the key (drawn as the best arrow) and the played blunder. Only the server's own
 * grades qualify, never a browser-engine reading.
 */
function alsoGoodMoves(solution: BlunderSolution): TrainFineMove[] {
  return solution.server_graded_moves
    .filter(
      (move) =>
        move.tier === 'good' && move.uci !== solution.key_uci && move.uci !== solution.blunder_uci,
    )
    .slice(0, BLUNDER_CHECK_ALT_MOVE_ARROWS)
    .map((move) => ({ uci: move.uci, quality: 'good' }));
}

/** A move the solution shows, with the quality it is shown with. */
interface SolutionMove {
  uci: string;
  quality: TrainMoveQuality;
}

/** The better move the user found, with its quality (the key itself is the best move). */
function betterMoveOverlay(solution: BlunderSolution): SolutionMove | null {
  if (solution.better_move_uci === null) return null;
  const quality =
    solution.better_move_uci === solution.key_uci
      ? 'best'
      : BETTER_MOVE_QUALITY[solution.better_move_tier ?? 'good'];
  return { uci: solution.better_move_uci, quality };
}

/** What the screen shows of a solution, whatever its kind. */
interface SolutionLineModel {
  bestUci: string | null;
  /** The better move the user found, absent unless a blunder was caught. */
  your: SolutionMove | null;
  /** The move that was played in the game. */
  game: SolutionMove;
  alsoGood: TrainFineMove[];
}

function lineModel(solution: LinesSolution): SolutionLineModel {
  if (solution.kind === 'false_alarm') {
    // The flagged move was good (the server's own grade), so it carries the good-move badge.
    return {
      bestUci: solution.key_uci,
      your: null,
      game: { uci: solution.flagged_uci, quality: 'good' },
      alsoGood: [],
    };
  }
  return {
    bestUci: solution.key_uci,
    your: betterMoveOverlay(solution),
    game: { uci: solution.blunder_uci, quality: 'blunder' },
    alsoGood: alsoGoodMoves(solution),
  };
}

/**
 * The solution board's overlay at the solution position, built like the personalized-puzzle
 * reveal: the best move, the user's better move, the played move and the moves that were
 * also good, each arrow with its move-quality badge. The caller dims everything but the lit
 * chip (`buildChipFocusOverlay`).
 */
export function buildSolutionOverlay(solution: LinesSolution): TrainRevealOverlay {
  const model = lineModel(solution);
  return buildTrainRevealOverlay(
    // The herring arrow budget is the widest; `alsoGoodMoves` applies the solution's own cap.
    'herring',
    model.alsoGood,
    model.bestUci,
    model.your,
    model.game,
    true,
  );
}

/** The first move of each role the solution shows (a role is absent when it has no move). */
function roleMoves(model: SolutionLineModel): Partial<Record<RoleKey, string>> {
  const moves: Partial<Record<RoleKey, string>> = { game: model.game.uci };
  if (model.bestUci !== null) moves.best = model.bestUci;
  if (model.your !== null) moves.your = model.your.uci;
  return moves;
}

/**
 * The distinct first moves whose lines the screen searches, in search order: the key, the
 * better move, then the played move. They run one after another on the shared engine.
 */
export function solutionLineUcis(solution: LinesSolution): string[] {
  const moves = roleMoves(lineModel(solution));
  const ordered = [moves.best, moves.your, moves.game];
  return ordered.filter(
    (uci, index): uci is string => uci !== undefined && ordered.indexOf(uci) === index,
  );
}

function chipQuality(roles: readonly RoleKey[], model: SolutionLineModel): TrainMoveQuality {
  if (roles.includes('best')) return 'best';
  if (roles.includes('your') && model.your !== null) return model.your.quality;
  return model.game.quality;
}

/** The chips row of a solution, in the canonical Your, Best, Game order. */
export function buildSolutionChips(
  solution: LinesSolution,
  lines: Readonly<Record<string, GameMoveLineState>>,
): ChipGroup[] {
  const model = lineModel(solution);
  const moves = roleMoves(model);
  const consumed = new Set<RoleKey>();
  const chips: ChipGroup[] = [];
  for (const role of CANONICAL_ROLE_ORDER) {
    const uci = moves[role];
    if (consumed.has(role) || uci === undefined) continue;
    const roles = CANONICAL_ROLE_ORDER.filter((candidate) => moves[candidate] === uci);
    roles.forEach((merged) => consumed.add(merged));
    const state = lines[uci];
    chips.push({
      key: roles[0] ?? role,
      roles,
      uci,
      san: sanFromUci(solution.fen, uci),
      label: roles.map((merged) => ROLE_SHORT_LABELS[merged]).join(' = '),
      line: state?.status === 'ready' ? state.line : null,
      pending: state?.status === 'ready' ? null : state?.status === 'error' ? 'failed' : 'loading',
      quality: chipQuality(roles, model),
    });
  }
  return chips;
}

/** A "+N" point badge inside the verdict sentence; `name` keys its test id. */
export interface SolutionPointsPart {
  name: 'call' | 'move' | 'earlier';
  points: number;
}

/** A piece of the verdict sentence: plain text or a point badge. */
export type SolutionCopyPart = string | SolutionPointsPart;

/** The verdict card's heading and its sentence, in reading order. */
export interface SolutionCopy {
  heading: string;
  parts: SolutionCopyPart[];
}

/** How the better move is named, by the quality the board and the Move chip show it with. */
const BETTER_MOVE_PHRASE: Record<TrainMoveQuality, string> = {
  best: 'found the best move',
  good: 'played a good move',
  inaccuracy: 'played an inaccuracy',
  mistake: 'played a mistake',
  blunder: 'played a blunder',
};

/** The points the "Good" calls before the window's last move kept, as a closing sentence. */
function earlierCallsParts(points: number): SolutionCopyPart[] {
  return points > 0 ? [' Your earlier calls earned ', { name: 'earlier', points }, '.'] : [];
}

/**
 * The verdict of a caught or missed blunder. The game move is named as the blunder and the
 * user's better move separately, with its own quality: without that, "X was a blunder" read
 * as a verdict on the better move the user had just played (Phase 249 UAT). A blunder is
 * never said to "lose to" a reply: many miss a chance or are positional.
 */
function blunderCopy(solution: BlunderSolution): SolutionCopy {
  const caught = solution.outcome === 'caught';
  const heading = caught ? 'Blunder caught' : 'Missed blunder';
  const playedSan = sanFromUci(solution.fen, solution.blunder_uci) ?? 'That move';
  const bestSan = sanFromUci(solution.fen, solution.key_uci);
  const bestText = bestSan === null ? '' : ` Best was ${bestSan}.`;
  const parts: SolutionCopyPart[] = [
    `${playedSan} was a blunder. You ${caught ? 'called' : 'missed'} it `,
    { name: 'call', points: solution.blunder_points },
  ];
  const better = betterMoveOverlay(solution);
  const betterSan = better === null ? null : sanFromUci(solution.fen, better.uci);
  if (better === null || betterSan === null || solution.better_move_points === null) {
    parts.push(`.${bestText}`);
  } else {
    parts.push(
      ` and ${BETTER_MOVE_PHRASE[better.quality]}, ${betterSan} `,
      { name: 'move', points: solution.better_move_points },
      // The best move is not repeated when the user found it.
      better.quality === 'best' ? '.' : `.${bestText}`,
    );
  }
  return { heading, parts: [...parts, ...earlierCallsParts(solution.safe_points)] };
}

/** A false alarm scores nothing for the call and keeps the "Good" calls before it. */
function falseAlarmCopy(solution: FalseAlarmSolution): SolutionCopy {
  const flaggedSan = sanFromUci(solution.fen, solution.flagged_uci) ?? 'That move';
  return {
    heading: 'False alarm',
    parts: [
      `${flaggedSan} was a good move, not a blunder `,
      { name: 'call', points: 0 },
      '.',
      ...earlierCallsParts(solution.window_points),
    ],
  };
}

function herringCopy(solution: HerringSolution): SolutionCopy {
  return {
    heading: 'All good',
    parts: [
      'Every move in this sequence was good. Your calls earned ',
      { name: 'call', points: solution.window_points },
      '.',
    ],
  };
}

/** The verdict card's copy of a solution, with the points each part of the window earned. */
export function solutionCopy(solution: WindowSolution): SolutionCopy {
  switch (solution.kind) {
    case 'blunder':
      return blunderCopy(solution);
    case 'false_alarm':
      return falseAlarmCopy(solution);
    case 'herring':
      return herringCopy(solution);
  }
}

/** One replayed ply of a cleared herring's sequence. */
export interface SequenceStep {
  san: string;
  /** Move-number label ("12." for White, "12..." for a Black move that opens the list), else null. */
  numberLabel: string | null;
  from: string;
  to: string;
  /** The position after the move. */
  fen: string;
  /** The move's sound: check wins over capture, else a plain move (the drill's taxonomy). */
  sound: SoundEvent;
}

/**
 * The plies of a cleared herring's sequence, replayed from `startFen`. Stops at the first
 * move that does not apply (a broken payload), so the list never shows a wrong board.
 */
export function buildSequenceSteps(startFen: string, ucis: readonly string[]): SequenceStep[] {
  const steps: SequenceStep[] = [];
  let chess: Chess;
  try {
    chess = new Chess(startFen);
  } catch {
    return steps;
  }
  for (const uci of ucis) {
    const moveNumber = chess.moveNumber();
    const isWhite = chess.turn() === 'w';
    let move: Move;
    try {
      move = chess.move({
        from: uci.slice(0, 2),
        to: uci.slice(2, 4),
        promotion: uci.length > 4 ? uci.slice(4, 5) : undefined,
      });
    } catch {
      break;
    }
    const quietSound: SoundEvent = move.captured !== undefined ? 'capture' : 'move';
    const blackLabel = steps.length === 0 ? `${moveNumber}...` : null;
    steps.push({
      san: move.san,
      numberLabel: isWhite ? `${moveNumber}.` : blackLabel,
      from: uci.slice(0, 2),
      to: uci.slice(2, 4),
      fen: chess.fen(),
      sound: chess.inCheck() ? 'check' : quietSound,
    });
  }
  return steps;
}
