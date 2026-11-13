/**
 * blunderCheckDrill: the pure state machine of the blunder-check drill (Phase 249).
 *
 * One window runs: loading -> lead-in replay -> prompt -> grading -> feedback ->
 * (move + reply -> next prompt) ... -> window ended. A caught blunder then asks for a
 * better move (better_move -> grading -> feedback); every ended window ends on its
 * solution screen (solution_loading -> solution). After the last window the session is
 * finished. The reducer is pure: no timers, no I/O. The component that hosts it
 * (BlunderCheckTab and the drill under it) schedules the ticks with the constants
 * below and feeds the server's responses back in as events. Points are always the
 * server's numbers (Pitfall 13), never derived here.
 */

import { Chess } from 'chess.js';
import { applyUciMoveFen } from '@/lib/engine/treeCommon';
import type { SoundEvent } from '@/lib/sounds';
import type {
  AnswerKind,
  AnsweredMove,
  AnswerResponse,
  BetterMoveResponse,
  BetterMoveTask,
  BetterMoveTier,
  BlunderCheckSessionResponse,
  Prompt,
  SessionResultResponse,
  WindowOutcome,
  WindowSolution,
  WindowStartResponse,
} from '@/types/blunderCheck';

/** Delay before the first lead-in ply is replayed after a window loads. */
export const LEAD_IN_START_DELAY_MS = 400;
/** Gap between two lead-in plies; the last gap hands over to the prompt. */
export const LEAD_IN_PLY_INTERVAL_MS = 700;
/** Gap between feedback end and the prompted move, and between that move and the reply. */
export const MOVE_REPLY_DELAY_MS = 600;
/** How long the graded answer's feedback stays up before the move and reply are played. */
export const FEEDBACK_DISPLAY_MS = 900;
/**
 * Mirrors the backend `PROMPT_ANIMATION_ALLOWANCE_S` (app/services/blunder_check_grading.py):
 * the server stamps `prompted_at` when it issues a prompt, so every client animation
 * between that stamp and the countdown start (a fresh window's start delay and lead-in
 * plies, or after an answer the feedback, the move and the reply) must fit inside this
 * budget, or the user loses real time (D-12, D-18).
 */
export const PROMPT_ANIMATION_BUDGET_MS = 3000;

/** The user-facing name of each window outcome (outcome panel and end screen). */
export const WINDOW_OUTCOME_LABELS: Record<WindowOutcome, string> = {
  cleared: 'Clear',
  caught: 'Caught',
  missed: 'Missed',
  false_alarm: 'False alarm',
};

const UNEXPECTED_RESPONSE_MESSAGE = 'Unexpected blunder-check response';

/**
 * The FEN after playing `ucis` from `startFen`. Throws on an illegal move: the server's
 * lines are legal, so an illegal one is a broken payload and must not draw a wrong board.
 */
export function applyUcis(startFen: string, ucis: readonly string[]): string {
  let fen = startFen;
  for (const uci of ucis) {
    const next = applyUciMoveFen(fen, uci);
    if (next === null) throw new Error('Illegal move in blunder-check line');
    fen = next;
  }
  return fen;
}

/** The session the drill is running, fixed once it is composed or resumed. */
export interface DrillSession {
  sessionId: number;
  windowCount: number;
}

/** What the board needs for the current window. */
export interface DrillWindow {
  position: number;
  startFen: string;
  orientation: 'white' | 'black';
  /** The replayed plies before the first judged move. */
  leadInUcis: readonly string[];
  /** Every UCI already played on the board, in order, starting from `startFen`. */
  shownUcis: readonly string[];
  windowPoints: number;
}

/** The points flash after a graded answer: a forfeit when points were taken away, else a gain. */
export interface FeedbackFlash {
  amount: number;
  variant: 'gain' | 'forfeit';
}

/** Fields every in-window phase carries. */
interface InWindow {
  session: DrillSession;
  sessionPoints: number;
  window: DrillWindow;
}

/** What every phase after the window's last answer carries (the better move, then the solution). */
interface WindowEnded extends InWindow {
  prompt: Prompt;
  graded: AnswerResponse;
  outcome: WindowOutcome;
}

export type DrillState =
  | { phase: 'idle' }
  | { phase: 'loading_window'; session: DrillSession; position: number; sessionPoints: number }
  | ({ phase: 'lead_in'; prompt: Prompt; timerMs: number } & InWindow)
  | ({ phase: 'prompt'; prompt: Prompt; timerMs: number } & InWindow)
  | ({ phase: 'grading'; prompt: Prompt } & InWindow)
  | ({ phase: 'feedback'; prompt: Prompt; graded: AnswerResponse } & InWindow)
  | ({
      phase: 'advancing';
      prompt: Prompt;
      graded: AnswerResponse;
      /** 0: the prompted move is next to be shown; 1: the opponent's reply is. */
      step: 0 | 1;
    } & InWindow)
  | ({ phase: 'better_move'; task: BetterMoveTask } & WindowEnded)
  | ({ phase: 'better_move_grading'; task: BetterMoveTask; playedUci: string } & WindowEnded)
  | ({
      phase: 'better_move_feedback';
      task: BetterMoveTask;
      playedUci: string;
      betterMove: BetterMoveResponse;
    } & WindowEnded)
  | ({ phase: 'solution_loading' } & WindowEnded)
  | ({ phase: 'solution'; solution: WindowSolution } & WindowEnded)
  | { phase: 'finishing'; session: DrillSession; position: number; sessionPoints: number }
  | { phase: 'session_end'; result: SessionResultResponse }
  | { phase: 'error'; message: string };

export type DrillEvent =
  | { type: 'SESSION_READY'; session: BlunderCheckSessionResponse }
  | { type: 'WINDOW_LOADED'; response: WindowStartResponse }
  | { type: 'LEAD_IN_TICK' }
  | { type: 'ANSWER_SUBMITTED'; answer: AnswerKind }
  | { type: 'ANSWER_GRADED'; response: AnswerResponse }
  | { type: 'FEEDBACK_DONE' }
  | { type: 'BETTER_MOVE_SUBMITTED'; playedUci: string }
  | { type: 'BETTER_MOVE_GRADED'; response: BetterMoveResponse }
  | { type: 'SOLUTION_LOADED'; solution: WindowSolution }
  | { type: 'ADVANCE_TICK' }
  | { type: 'NEXT_WINDOW' }
  | { type: 'SESSION_FINISHED'; result: SessionResultResponse }
  | { type: 'FAILED'; message: string }
  | { type: 'RESET' };

export const initialDrillState: DrillState = { phase: 'idle' };

/** A freshly composed or resumed session: load its current window, or finish it when none is left open. */
function sessionReady(response: BlunderCheckSessionResponse): DrillState {
  const session: DrillSession = {
    sessionId: response.session_id,
    windowCount: response.window_count,
  };
  if (response.current_position === null) {
    return {
      phase: 'finishing',
      session,
      position: response.window_count - 1,
      sessionPoints: response.session_points,
    };
  }
  return {
    phase: 'loading_window',
    session,
    position: response.current_position,
    sessionPoints: response.session_points,
  };
}

/** The moves and replies already played on the board, in order. */
function answeredUcis(answered: readonly AnsweredMove[]): string[] {
  return answered.flatMap((move) =>
    move.reply_uci === null ? [move.move_uci] : [move.move_uci, move.reply_uci],
  );
}

/**
 * A reload during the better-move step: back into it, on the board before the caught blunder.
 * Bug fix (Phase 249 review): the drill used to skip to the next sequence, so the better
 * move's points could never be earned. The catch's grade is rebuilt from its answered row.
 */
function betterMoveResumed(
  session: DrillSession,
  response: WindowStartResponse,
  task: BetterMoveTask,
): DrillState {
  const caught = response.answered[response.answered.length - 1];
  if (caught === undefined) return { phase: 'error', message: UNEXPECTED_RESPONSE_MESSAGE };
  const graded: AnswerResponse = {
    move_index: caught.move_index,
    result: caught.result,
    points_awarded: caught.points_awarded,
    points_forfeited: caught.points_forfeited,
    window_points: response.window_points,
    session_points: response.session_points,
    window_ended: true,
    outcome: 'caught',
    reply_uci: null,
    next_prompt: null,
    timer_remaining_ms: null,
    better_move: task,
  };
  return {
    phase: 'better_move',
    task,
    session,
    sessionPoints: response.session_points,
    window: {
      position: response.position,
      startFen: response.start_fen,
      orientation: response.orientation,
      leadInUcis: response.lead_in_ucis,
      // The caught blunder itself was never played on the board.
      shownUcis: [...response.lead_in_ucis, ...answeredUcis(response.answered.slice(0, -1))],
      windowPoints: response.window_points,
    },
    prompt: response.prompt,
    graded,
    outcome: 'caught',
  };
}

/**
 * The window just loaded. A resume goes straight to the prompt, a fresh window replays its
 * lead-in. A reload during grading (the server answered 409 stale_prompt, so its state wins)
 * also goes straight to the prompt: a replay would burn the user's real countdown time.
 */
function windowLoaded(state: DrillState, response: WindowStartResponse): DrillState {
  if (state.phase !== 'loading_window' && state.phase !== 'grading') return state;
  if (response.better_move !== null) {
    return betterMoveResumed(state.session, response, response.better_move);
  }
  const resumed = response.answered.length > 0 || state.phase === 'grading';
  const window: DrillWindow = {
    position: response.position,
    startFen: response.start_fen,
    orientation: response.orientation,
    leadInUcis: response.lead_in_ucis,
    shownUcis: resumed ? [...response.lead_in_ucis, ...answeredUcis(response.answered)] : [],
    windowPoints: response.window_points,
  };
  const common = {
    session: state.session,
    sessionPoints: response.session_points,
    window,
    prompt: response.prompt,
    // D-18: the server's remaining time, never topped up on a resume.
    timerMs: response.timer_remaining_ms,
  };
  return resumed ? { phase: 'prompt', ...common } : { phase: 'lead_in', ...common };
}

/** One lead-in step: show the next ply, or hand over to the prompt once all are shown. */
function leadInTick(state: DrillState): DrillState {
  if (state.phase !== 'lead_in') return state;
  const nextUci = state.window.leadInUcis[state.window.shownUcis.length];
  if (nextUci === undefined) return { ...state, phase: 'prompt' };
  return {
    ...state,
    window: { ...state.window, shownUcis: [...state.window.shownUcis, nextUci] },
  };
}

/** Accepted only while a prompt is open, so a late timeout after a click is ignored. */
function answerSubmitted(state: DrillState): DrillState {
  if (state.phase !== 'prompt') return state;
  const { session, sessionPoints, window, prompt } = state;
  return { phase: 'grading', session, sessionPoints, window, prompt };
}

/** The flash of a graded answer; the drill derives it for the feedback and the move + reply. */
export function flashFor(response: AnswerResponse): FeedbackFlash {
  if (response.points_forfeited > 0) {
    return { amount: response.points_forfeited, variant: 'forfeit' };
  }
  return { amount: response.points_awarded, variant: 'gain' };
}

function answerGraded(state: DrillState, response: AnswerResponse): DrillState {
  if (state.phase !== 'grading') return state;
  return {
    phase: 'feedback',
    session: state.session,
    // Always the server's totals (Pitfall 13): a forfeit visibly lowers them.
    sessionPoints: response.session_points,
    window: { ...state.window, windowPoints: response.window_points },
    prompt: state.prompt,
    graded: response,
  };
}

/**
 * The answer feedback is over. An open window plays the move and reply; an ended one goes to
 * the better-move step after a catch (the server hands out the task only then) or straight to
 * its solution (missed, cleared, false alarm).
 */
function answerFeedbackDone(state: Extract<DrillState, { phase: 'feedback' }>): DrillState {
  const { session, sessionPoints, window, prompt, graded } = state;
  if (!graded.window_ended) {
    return { phase: 'advancing', session, sessionPoints, window, prompt, graded, step: 0 };
  }
  if (graded.outcome === null) return { phase: 'error', message: UNEXPECTED_RESPONSE_MESSAGE };
  const ended: WindowEnded = {
    session,
    sessionPoints,
    window,
    prompt,
    graded,
    outcome: graded.outcome,
  };
  if (graded.better_move !== null) {
    return { phase: 'better_move', task: graded.better_move, ...ended };
  }
  return { phase: 'solution_loading', ...ended };
}

/** The better-move feedback is over: on to the solution. */
function betterMoveFeedbackDone(
  state: Extract<DrillState, { phase: 'better_move_feedback' }>,
): DrillState {
  const { session, sessionPoints, window, prompt, graded, outcome } = state;
  return { phase: 'solution_loading', session, sessionPoints, window, prompt, graded, outcome };
}

function feedbackDone(state: DrillState): DrillState {
  if (state.phase === 'feedback') return answerFeedbackDone(state);
  if (state.phase === 'better_move_feedback') return betterMoveFeedbackDone(state);
  return state;
}

/** The user played a legal move on the better-move board: it is graded next. */
function betterMoveSubmitted(state: DrillState, playedUci: string): DrillState {
  if (state.phase !== 'better_move') return state;
  return { ...state, phase: 'better_move_grading', playedUci };
}

/** The server's better-move grade: its totals replace the client's (Pitfall 13). */
function betterMoveGraded(state: DrillState, response: BetterMoveResponse): DrillState {
  if (state.phase !== 'better_move_grading') return state;
  return {
    ...state,
    phase: 'better_move_feedback',
    sessionPoints: response.session_points,
    window: { ...state.window, windowPoints: response.window_points },
    betterMove: response,
  };
}

function solutionLoaded(state: DrillState, solution: WindowSolution): DrillState {
  if (state.phase !== 'solution_loading') return state;
  const { session, sessionPoints, window, prompt, graded, outcome } = state;
  return { phase: 'solution', session, sessionPoints, window, prompt, graded, outcome, solution };
}

/** Plays the prompted move on the first tick and the opponent's reply on the second, then prompts again. */
function advanceTick(state: DrillState): DrillState {
  if (state.phase !== 'advancing') return state;
  const { window, graded } = state;
  if (state.step === 0) {
    const shownUcis = [...window.shownUcis, state.prompt.move_uci];
    return { ...state, step: 1, window: { ...window, shownUcis } };
  }
  if (graded.next_prompt === null) return { phase: 'error', message: UNEXPECTED_RESPONSE_MESSAGE };
  const shownUcis =
    graded.reply_uci === null ? window.shownUcis : [...window.shownUcis, graded.reply_uci];
  return {
    phase: 'prompt',
    session: state.session,
    sessionPoints: state.sessionPoints,
    window: { ...window, shownUcis },
    prompt: graded.next_prompt,
    // The server's countdown for the fresh prompt.
    timerMs: graded.timer_remaining_ms ?? 0,
  };
}

/** The next window, or finishing after the last one. */
function nextWindow(state: DrillState): DrillState {
  if (state.phase !== 'solution') return state;
  const { session, sessionPoints } = state;
  const position = state.window.position;
  if (position + 1 < session.windowCount) {
    return { phase: 'loading_window', session, position: position + 1, sessionPoints };
  }
  return { phase: 'finishing', session, position, sessionPoints };
}

function sessionFinished(state: DrillState, result: SessionResultResponse): DrillState {
  if (state.phase !== 'finishing') return state;
  return { phase: 'session_end', result };
}

/**
 * The largest the drill board column grows to on desktop (the personalized-puzzle board
 * size, so both Train drills share one layout); phones use the full width.
 */
export const BLUNDER_CHECK_BOARD_MAX_WIDTH_PX = 600;

/**
 * The gain badge's flight from the board to the pot badge in the progress row
 * (BlunderCheckPointsFlash): it pops in over the board, then flies and shrinks into the
 * header. The whole animation takes POINTS_FLIGHT_MS; the badge reaches the pot at
 * POINTS_FLIGHT_LAND_MS (the keyframes' landing stop), which is when the pot adds the
 * points up and the coin sound plays. Both stay under FEEDBACK_DISPLAY_MS: a window's last
 * answer swaps the screen when the feedback ends.
 */
export const POINTS_FLIGHT_MS = 850;
export const POINTS_FLIGHT_LAND_MS = 780;

/** Length of the coin clip (`pot-gain`, Coin.mp3). */
export const COIN_SOUND_MS = 500;
/**
 * A cleared herring's full-score sound waits for the last point's coin: the coin plays as
 * the badge lands, and the full-score sound follows once it has sounded.
 */
export const CLEARED_SOUND_DELAY_MS = POINTS_FLIGHT_LAND_MS + COIN_SOUND_MS;

/** Banking the pot plays this many coins, one every BANK_COIN_INTERVAL_MS, so they overlap. */
export const BANK_COIN_COUNT = 3;
export const BANK_COIN_INTERVAL_MS = 150;
/**
 * How long Next waits while the pot badge slides into the banked total, the total counts
 * up (BlunderCheckScore) and the coins sound, before the next window loads.
 */
export const BANK_HOLD_MS = 1200;

/**
 * What just happened to the pot, for the progress row's animation: points dropped in, the
 * pot was lost (a missed blunder or a timeout), or the pot was banked into the total (on
 * Next, see `bankingProgress`).
 */
export interface PotEvent {
  kind: 'gain' | 'bust' | 'bank';
  amount: number;
}

/** What the progress row above the board shows. */
export interface DrillProgress {
  position: number;
  windowCount: number;
  /** The points that can no longer be lost: the session's total without the open pot. */
  banked: number;
  /**
   * The window's points, apart from the total until Next banks them; null between windows.
   */
  pot: number | null;
  potEvent: PotEvent | null;
  /** The window is over and its solution is up (or loading): an empty pot is a lost one. */
  windowOver: boolean;
}

/** The pot event of a graded answer: a forfeit busts the pot, awarded points drop into it. */
function answerPotEvent(graded: AnswerResponse): PotEvent | null {
  if (graded.points_forfeited > 0) return { kind: 'bust', amount: graded.points_forfeited };
  if (graded.points_awarded > 0) return { kind: 'gain', amount: graded.points_awarded };
  return null;
}

/** The pot event of the phase on screen, or null when nothing just happened to the pot. */
function potEventOf(state: Extract<DrillState, { window: DrillWindow }>): PotEvent | null {
  switch (state.phase) {
    // Kept through the move + reply, so the pot's animation is not cut short.
    case 'feedback':
    case 'advancing':
      return answerPotEvent(state.graded);
    case 'better_move_feedback':
      return state.betterMove.points_awarded > 0
        ? { kind: 'gain', amount: state.betterMove.points_awarded }
        : null;
    default:
      return null;
  }
}

/**
 * The progress of the running session, or null on the start, error and end screens.
 *
 * The server's session total already counts the open window's points (a forfeit lowers it).
 * The row shows them apart instead: the pot is what a missed blunder would take away, the
 * banked total is safe. The pot stays on screen through the solution, so the user sees what
 * the window was worth, and is banked on Next (`bankingProgress`).
 */
export function drillProgress(state: DrillState): DrillProgress | null {
  switch (state.phase) {
    // The end screen (session_end) carries its own points and Score %.
    case 'idle':
    case 'error':
    case 'session_end':
      return null;
    case 'loading_window':
    case 'finishing':
      return {
        position: state.position,
        windowCount: state.session.windowCount,
        banked: state.sessionPoints,
        pot: null,
        potEvent: null,
        windowOver: false,
      };
    default:
      return {
        position: state.window.position,
        windowCount: state.session.windowCount,
        banked: state.sessionPoints - state.window.windowPoints,
        pot: state.window.windowPoints,
        potEvent: potEventOf(state),
        windowOver: state.phase === 'solution_loading' || state.phase === 'solution',
      };
  }
}

/** The progress row while Next banks the pot: the pot is handed over to the total. */
export function bankingProgress(progress: DrillProgress): DrillProgress {
  const pot = progress.pot ?? 0;
  return {
    ...progress,
    banked: progress.banked + pot,
    pot: null,
    potEvent: pot > 0 ? { kind: 'bank', amount: pot } : null,
  };
}

const UCI_SQUARE_LENGTH = 2;

/**
 * The sound of playing `uci` from `fen` (check wins over capture, else a plain move: the
 * bot game's taxonomy), or null for an illegal move.
 */
export function moveSoundFor(fen: string, uci: string): SoundEvent | null {
  const chess = new Chess(fen);
  try {
    const move = chess.move({
      from: uci.slice(0, UCI_SQUARE_LENGTH),
      to: uci.slice(UCI_SQUARE_LENGTH, UCI_SQUARE_LENGTH * 2),
      promotion: uci.slice(UCI_SQUARE_LENGTH * 2) || undefined,
    });
    if (chess.inCheck()) return 'check';
    return move.captured !== undefined ? 'capture' : 'move';
  } catch {
    return null;
  }
}

/**
 * The tier the server decides for a better move without the phone's engine (D-17): the key
 * move is always good, and the server's graded moves carry their own tier. Null means the
 * move is off-key and the browser engine grades it (the same residual as personalized puzzles).
 */
export function serverDecidedTier(task: BetterMoveTask, playedUci: string): BetterMoveTier | null {
  if (playedUci === task.key_uci) return 'good';
  const graded = task.server_graded_moves.find((move) => move.uci === playedUci);
  return graded === undefined ? null : graded.tier;
}

export function drillReducer(state: DrillState, event: DrillEvent): DrillState {
  switch (event.type) {
    case 'RESET':
      return initialDrillState;
    case 'FAILED':
      return { phase: 'error', message: event.message };
    case 'SESSION_READY':
      return state.phase === 'idle' ? sessionReady(event.session) : state;
    case 'WINDOW_LOADED':
      return windowLoaded(state, event.response);
    case 'LEAD_IN_TICK':
      return leadInTick(state);
    case 'ANSWER_SUBMITTED':
      return answerSubmitted(state);
    case 'ANSWER_GRADED':
      return answerGraded(state, event.response);
    case 'FEEDBACK_DONE':
      return feedbackDone(state);
    case 'BETTER_MOVE_SUBMITTED':
      return betterMoveSubmitted(state, event.playedUci);
    case 'BETTER_MOVE_GRADED':
      return betterMoveGraded(state, event.response);
    case 'SOLUTION_LOADED':
      return solutionLoaded(state, event.solution);
    case 'ADVANCE_TICK':
      return advanceTick(state);
    case 'NEXT_WINDOW':
      return nextWindow(state);
    case 'SESSION_FINISHED':
      return sessionFinished(state, event.result);
  }
}
