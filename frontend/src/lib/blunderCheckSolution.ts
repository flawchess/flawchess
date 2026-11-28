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

import { isFacepalmBlunder } from '@/lib/facepalm';
import type { SoundEvent } from '@/lib/sounds';
import { buildTrainRevealOverlay } from '@/lib/trainArrows';
import type {
  TrainFineMove,
  TrainMoveQuality,
  TrainRevealOverlay,
} from '@/lib/trainArrows';
import { NO_GAME_MOVE_HEAD, gameBlunderParts } from '@/lib/gameBlunderSentence';
import type { GameBlunderPart, GameMoveHead } from '@/lib/gameBlunderSentence';
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
  /** The game's blunder is a facepalm blunder: "???" on the board and the Game chip. */
  facepalm?: boolean;
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
    game: {
      uci: solution.blunder_uci,
      quality: 'blunder',
      // The serve-time score snapshot; a solution cached before Phase 261 has no feedback at all.
      facepalm: isFacepalmBlunder(solution.feedback?.score),
    },
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

/** The quality (and facepalm flag) of a chip's first move: best, else the user's move, else the game's. */
function chipQuality(
  roles: readonly RoleKey[],
  model: SolutionLineModel,
): Pick<SolutionMove, 'quality' | 'facepalm'> {
  if (roles.includes('best')) return { quality: 'best' };
  if (roles.includes('your') && model.your !== null) return { quality: model.your.quality };
  return { quality: model.game.quality, facepalm: model.game.facepalm };
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
      ...chipQuality(roles, model),
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

/** The avatar feedback paragraph: its lines in order (never empty). */
export interface SolutionFeedback {
  lines: string[];
}

/** The verdict card's heading and its sentence, in reading order. */
export interface SolutionCopy {
  heading: string;
  parts: SolutionCopyPart[];
  /**
   * The second paragraph (Phase 261 D-03), the hard-to-catch line; null for false alarms,
   * herrings, pre-phase windows and a blunder that was not hard to catch.
   */
  feedback: SolutionFeedback | null;
  /**
   * The "Game move:" line below the divider (Phase 264 D-16), as parts; empty for false
   * alarms, herrings and a blunder with no visible tag and no type line.
   */
  gameMove: GameBlunderPart[];
  /** That line's subject: the blunder's SAN and its "??" / "???" glyph. */
  gameMoveHead: GameMoveHead;
}

/** The window's total: the sum of the verdict's point badges (the phone strip's pill). */
export function solutionCopyPoints(copy: SolutionCopy): number {
  return copy.parts.reduce((sum, part) => (typeof part === 'string' ? sum : sum + part.points), 0);
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

/** The fairness line for a subtle blunder (D-07), by whether the user called it. */
const HARD_TO_CATCH_COPY: Record<'caught' | 'missed', string> = {
  caught: 'Well spotted! This was one of the tough ones we mix in on purpose.',
  missed: 'This one was hard to catch. We mix in a few tough ones on purpose.',
};

/**
 * The feedback paragraph of a blunder solution: the hard-to-catch line. The type line moved to
 * the shared "Game move:" line below the divider (Phase 264 D-16).
 */
function feedbackCopy(solution: BlunderSolution): SolutionFeedback | null {
  // A solution cached in sessionStorage before the release has no `feedback` field at all.
  const feedback = solution.feedback ?? null;
  if (feedback === null) return null;
  // The score is no chip (Phase 261 UAT): it sits behind the line's badge and closes the
  // game-move line as its own sentence (264 D-23, D-25), not this paragraph.
  return feedback.hard_to_catch ? { lines: [HARD_TO_CATCH_COPY[solution.outcome]] } : null;
}

/** The "Game move:" line of a caught or missed blunder: its tags and the snapshotted type line. */
function gameMoveParts(solution: BlunderSolution): GameBlunderPart[] {
  return gameBlunderParts({
    // A solution cached in sessionStorage before the release has neither tag field.
    allowedTactic: solution.allowed_tactic ?? null,
    missedTactic: solution.missed_tactic ?? null,
    typeLine: solution.feedback?.type_line ?? null,
    // The serve-time snapshot, as the badge's popover: blunder check shows the score the window
    // was served with, the puzzle and analysis the live score (264 D-23, accepted drift).
    facepalmScore: solution.feedback?.score ?? null,
    // The hard-to-catch line above the divider already says it (same 50% cut): no band word.
    difficultySaid: solution.feedback?.hard_to_catch === true,
  });
}

/** How the user's call on the blunder went: right, wrong, or never made (the timer ran out). */
function callClause(solution: BlunderSolution): string {
  if (solution.outcome === 'caught') return 'Your call was right ';
  // Bug fix (Phase 264 review): a timeout also ends as "missed", and "Your call was wrong"
  // was false for it, since no call was made.
  return solution.timed_out === true ? 'Time ran out before your call ' : 'Your call was wrong ';
}

/**
 * The verdict of a caught or missed blunder: the user's call, then their better move with its
 * own quality. The blunder itself is no longer named here (owner, 2026-11-26, Phase 264): the
 * line below the divider starts with it ("Qe5 ???: loses material."), and next to that line
 * "Qe5 was a blunder. You missed it" read as if "it" were something other than the call. So
 * the clause says "Your call was right / wrong". A blunder is never said to "lose to" a reply:
 * many miss a chance or are positional.
 */
function blunderCopy(solution: BlunderSolution): SolutionCopy {
  const caught = solution.outcome === 'caught';
  const heading = caught ? 'Blunder caught' : 'Missed blunder';
  const bestSan = sanFromUci(solution.fen, solution.key_uci);
  const bestText = bestSan === null ? '' : ` Best was ${bestSan}.`;
  const parts: SolutionCopyPart[] = [
    callClause(solution),
    { name: 'call', points: solution.blunder_points },
  ];
  const better = betterMoveOverlay(solution);
  const betterSan = better === null ? null : sanFromUci(solution.fen, better.uci);
  if (better === null || betterSan === null || solution.better_move_points === null) {
    parts.push(`.${bestText}`);
  } else {
    parts.push(
      ` and you ${BETTER_MOVE_PHRASE[better.quality]}, ${betterSan} `,
      { name: 'move', points: solution.better_move_points },
      // The best move is not repeated when the user found it.
      better.quality === 'best' ? '.' : `.${bestText}`,
    );
  }
  return {
    heading,
    parts: [...parts, ...earlierCallsParts(solution.safe_points)],
    feedback: feedbackCopy(solution),
    gameMove: gameMoveParts(solution),
    gameMoveHead: {
      san: sanFromUci(solution.fen, solution.blunder_uci),
      quality: 'blunder',
      facepalmScore: solution.feedback?.score ?? null,
      facepalmType: solution.feedback?.facepalm_type ?? null,
      byOther: !solution.is_own,
    },
  };
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
    // D-05: a false alarm never reveals the blunder the user did not reach (249 D-10).
    feedback: null,
    gameMove: [],
    gameMoveHead: NO_GAME_MOVE_HEAD,
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
    feedback: null,
    gameMove: [],
    gameMoveHead: NO_GAME_MOVE_HEAD,
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
