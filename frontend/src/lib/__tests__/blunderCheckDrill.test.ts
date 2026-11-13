import { describe, expect, it } from 'vitest';
import {
  FEEDBACK_DISPLAY_MS,
  LEAD_IN_PLY_INTERVAL_MS,
  LEAD_IN_START_DELAY_MS,
  MOVE_REPLY_DELAY_MS,
  PROMPT_ANIMATION_BUDGET_MS,
  applyUcis,
  bankingProgress,
  drillProgress,
  drillReducer,
  flashFor,
  initialDrillState,
  moveSoundFor,
} from '@/lib/blunderCheckDrill';
import type { DrillEvent, DrillState } from '@/lib/blunderCheckDrill';
import type {
  AnswerResponse,
  BetterMoveResponse,
  BlunderCheckSessionResponse,
  SessionResultResponse,
  WindowSolution,
  WindowStartResponse,
} from '@/types/blunderCheck';

const START_FEN = 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1';
const LEAD_IN = ['e2e4', 'e7e5', 'g1f3'];
/** Mirrors the backend `LEAD_IN_PLIES` (app/services/blunder_check_rules.py). */
const LEAD_IN_PLIES = 1;
const WINDOW_COUNT = 3;
const SESSION_ID = 7;
const FIRST_TIMER_MS = 10000;
const RESUMED_TIMER_MS = 8200;
const NEXT_TIMER_MS = 9100;

const SESSION: BlunderCheckSessionResponse = {
  session_id: SESSION_ID,
  window_count: WINDOW_COUNT,
  current_position: 0,
  session_points: 4,
  windows: [],
};

function windowStart(overrides: Partial<WindowStartResponse> = {}): WindowStartResponse {
  return {
    position: 0,
    start_fen: START_FEN,
    orientation: 'black',
    lead_in_ucis: LEAD_IN,
    answered: [],
    prompt: { move_index: 1, move_uci: 'b8c6' },
    timer_remaining_ms: FIRST_TIMER_MS,
    move_timer_seconds: 10,
    window_points: 0,
    session_points: 4,
    better_move: null,
    ...overrides,
  };
}

function graded(overrides: Partial<AnswerResponse> = {}): AnswerResponse {
  return {
    move_index: 1,
    result: 'correct_safe',
    points_awarded: 1,
    points_forfeited: 0,
    window_points: 1,
    session_points: 5,
    window_ended: false,
    outcome: null,
    reply_uci: 'f1b5',
    next_prompt: { move_index: 2, move_uci: 'a7a6' },
    timer_remaining_ms: NEXT_TIMER_MS,
    better_move: null,
    ...overrides,
  };
}

/** A solution payload for the reducer tests that only need some solution to be loaded. */
const FALSE_ALARM_SOLUTION: WindowSolution = {
  kind: 'false_alarm',
  outcome: 'false_alarm',
  flagged_uci: 'b8c6',
  fen: START_FEN,
  window_points: 0,
};

function run(events: DrillEvent[], from: DrillState = initialDrillState): DrillState {
  return events.reduce(drillReducer, from);
}

function loaded(response: WindowStartResponse = windowStart()): DrillState {
  return run([
    { type: 'SESSION_READY', session: SESSION },
    { type: 'WINDOW_LOADED', response },
  ]);
}

/** A window at its first prompt (lead-in fully replayed). */
function atPrompt(): DrillState {
  return run(
    [...LEAD_IN, 'prompt'].map((): DrillEvent => ({ type: 'LEAD_IN_TICK' })),
    loaded(),
  );
}

function asPhase<P extends DrillState['phase']>(
  state: DrillState,
  phase: P,
): Extract<DrillState, { phase: P }> {
  expect(state.phase).toBe(phase);
  return state as Extract<DrillState, { phase: P }>;
}

describe('session-level events', () => {
  it('SESSION_READY loads the current window with the server points', () => {
    const state = asPhase(
      drillReducer(initialDrillState, { type: 'SESSION_READY', session: SESSION }),
      'loading_window',
    );
    expect(state.session).toEqual({ sessionId: SESSION_ID, windowCount: WINDOW_COUNT });
    expect(state.position).toBe(0);
    expect(state.sessionPoints).toBe(4);
  });

  it('a session with no open window goes straight to finishing', () => {
    const state = drillReducer(initialDrillState, {
      type: 'SESSION_READY',
      session: { ...SESSION, current_position: null },
    });
    expect(state.phase).toBe('finishing');
  });

  it('FAILED goes to error and RESET returns to idle', () => {
    const failed = drillReducer(loaded(), { type: 'FAILED', message: 'boom' });
    expect(asPhase(failed, 'error').message).toBe('boom');
    expect(drillReducer(failed, { type: 'RESET' })).toBe(initialDrillState);
  });
});

describe('lead-in', () => {
  it('shows no ply on load, then one more per tick, then the prompt', () => {
    let state = asPhase(loaded(), 'lead_in');
    expect(state.window.shownUcis).toEqual([]);
    for (let shown = 1; shown <= LEAD_IN.length; shown++) {
      state = asPhase(drillReducer(state, { type: 'LEAD_IN_TICK' }), 'lead_in');
      expect(state.window.shownUcis).toEqual(LEAD_IN.slice(0, shown));
    }
    const prompt = asPhase(drillReducer(state, { type: 'LEAD_IN_TICK' }), 'prompt');
    expect(prompt.prompt).toEqual({ move_index: 1, move_uci: 'b8c6' });
    expect(prompt.timerMs).toBe(FIRST_TIMER_MS);
    expect(prompt.window.shownUcis).toEqual(LEAD_IN);
    expect(prompt.window.windowPoints).toBe(0);
    expect(prompt.sessionPoints).toBe(4);
  });

  it('a window with no lead-in plies goes to the prompt on the first tick', () => {
    const state = run([{ type: 'LEAD_IN_TICK' }], loaded(windowStart({ lead_in_ucis: [] })));
    expect(asPhase(state, 'prompt').window.shownUcis).toEqual([]);
  });
});

describe('resume (D-18)', () => {
  it('goes straight to the prompt with the answered moves applied and the server countdown', () => {
    const state = asPhase(
      loaded(
        windowStart({
          answered: [
            {
              move_index: 1,
              move_uci: 'b8c6',
              reply_uci: 'f1b5',
              result: 'correct_safe',
              points_awarded: 1,
              points_forfeited: 0,
            },
            {
              move_index: 2,
              move_uci: 'a7a6',
              reply_uci: null,
              result: 'correct_safe',
              points_awarded: 1,
              points_forfeited: 0,
            },
          ],
          prompt: { move_index: 3, move_uci: 'g8f6' },
          timer_remaining_ms: RESUMED_TIMER_MS,
          window_points: 2,
        }),
      ),
      'prompt',
    );
    expect(state.window.shownUcis).toEqual([...LEAD_IN, 'b8c6', 'f1b5', 'a7a6']);
    expect(state.timerMs).toBe(RESUMED_TIMER_MS);
    expect(state.prompt.move_index).toBe(3);
    expect(state.window.windowPoints).toBe(2);
  });

  it('returns to the better-move step when the caught blunder is still waiting for it', () => {
    const task = { fen: START_FEN, key_uci: 'd2d4', server_graded_moves: [] };
    const state = asPhase(
      loaded(
        windowStart({
          answered: [
            {
              move_index: 1,
              move_uci: 'b8c6',
              reply_uci: 'f1b5',
              result: 'correct_safe',
              points_awarded: 1,
              points_forfeited: 0,
            },
            {
              move_index: 2,
              move_uci: 'a7a6',
              reply_uci: null,
              result: 'caught',
              points_awarded: 3,
              points_forfeited: 0,
            },
          ],
          prompt: { move_index: 2, move_uci: 'a7a6' },
          timer_remaining_ms: 0,
          window_points: 4,
          session_points: 8,
          better_move: task,
        }),
      ),
      'better_move',
    );
    expect(state.task).toBe(task);
    // The board is the one before the caught blunder: it was never played.
    expect(state.window.shownUcis).toEqual([...LEAD_IN, 'b8c6', 'f1b5']);
    expect(state.outcome).toBe('caught');
    expect(state.graded.points_awarded).toBe(3);
    expect(state.sessionPoints).toBe(8);
    expect(state.window.windowPoints).toBe(4);
  });
});

describe('answering', () => {
  it('accepts an answer only in the prompt phase', () => {
    const prompt = atPrompt();
    const grading = asPhase(
      drillReducer(prompt, { type: 'ANSWER_SUBMITTED', answer: 'safe' }),
      'grading',
    );
    expect(grading.phase).toBe('grading');
  });

  it('ignores a late timeout after the click (a prompt is answered once)', () => {
    const grading = drillReducer(atPrompt(), { type: 'ANSWER_SUBMITTED', answer: 'safe' });
    expect(drillReducer(grading, { type: 'ANSWER_SUBMITTED', answer: 'timeout' })).toBe(grading);
    const feedback = drillReducer(grading, { type: 'ANSWER_GRADED', response: graded() });
    expect(drillReducer(feedback, { type: 'ANSWER_SUBMITTED', answer: 'timeout' })).toBe(feedback);
    const leadIn = loaded();
    expect(drillReducer(leadIn, { type: 'ANSWER_SUBMITTED', answer: 'safe' })).toBe(leadIn);
  });

  it('a graded answer shows feedback with the server points and a gain flash', () => {
    const feedback = asPhase(
      run(
        [
          { type: 'ANSWER_SUBMITTED', answer: 'safe' },
          { type: 'ANSWER_GRADED', response: graded() },
        ],
        atPrompt(),
      ),
      'feedback',
    );
    expect(flashFor(feedback.graded)).toEqual({ amount: 1, variant: 'gain' });
    expect(feedback.window.windowPoints).toBe(1);
    expect(feedback.sessionPoints).toBe(5);
  });

  it('the progress row keeps the open pot apart from the banked total', () => {
    // No pot before a window is open: the session total is all banked.
    expect(drillProgress(run([{ type: 'SESSION_READY', session: SESSION }]))).toMatchObject({
      banked: 4,
      pot: null,
      potEvent: null,
    });
    expect(drillProgress(atPrompt())).toMatchObject({ banked: 4, pot: 0, potEvent: null });

    // A safe call drops its point into the pot, not into the total.
    const feedback = run(
      [
        { type: 'ANSWER_SUBMITTED', answer: 'safe' },
        { type: 'ANSWER_GRADED', response: graded() },
      ],
      atPrompt(),
    );
    const gain = { banked: 4, pot: 1, potEvent: { kind: 'gain', amount: 1 } };
    expect(drillProgress(feedback)).toMatchObject(gain);
    // Kept through the move + reply, gone at the next prompt.
    const advancing = drillReducer(feedback, { type: 'FEEDBACK_DONE' });
    expect(drillProgress(advancing)).toMatchObject(gain);
    const nextPrompt = run([{ type: 'ADVANCE_TICK' }, { type: 'ADVANCE_TICK' }], advancing);
    expect(drillProgress(nextPrompt)).toMatchObject({ banked: 4, pot: 1, potEvent: null });
  });

  it('a lost pot busts without lowering the banked total', () => {
    const start = run(
      [
        { type: 'ANSWER_SUBMITTED', answer: 'safe' },
        { type: 'ANSWER_GRADED', response: graded({ window_points: 2, session_points: 6 }) },
        { type: 'FEEDBACK_DONE' },
        { type: 'ADVANCE_TICK' },
        { type: 'ADVANCE_TICK' },
      ],
      atPrompt(),
    );
    expect(drillProgress(start)).toMatchObject({ banked: 4, pot: 2 });
    const missed = run(
      [
        { type: 'ANSWER_SUBMITTED', answer: 'safe' },
        {
          type: 'ANSWER_GRADED',
          response: graded({
            result: 'missed',
            points_awarded: 0,
            points_forfeited: 2,
            window_points: 0,
            session_points: 4,
            window_ended: true,
            outcome: 'missed',
            reply_uci: null,
            next_prompt: null,
            timer_remaining_ms: null,
          }),
        },
      ],
      start,
    );
    expect(drillProgress(missed)).toMatchObject({
      banked: 4,
      pot: 0,
      potEvent: { kind: 'bust', amount: 2 },
      windowOver: false,
    });
    // The solution keeps the empty pot up as a lost one, with nothing to bank.
    const loading = drillProgress(drillReducer(missed, { type: 'FEEDBACK_DONE' }));
    expect(loading).toMatchObject({ banked: 4, pot: 0, potEvent: null, windowOver: true });
    expect(loading && bankingProgress(loading)).toMatchObject({ banked: 4, potEvent: null });
  });

  it('a forfeit flashes the forfeited amount and lowers the server session total', () => {
    const feedback = asPhase(
      run(
        [
          { type: 'ANSWER_SUBMITTED', answer: 'blunder' },
          {
            type: 'ANSWER_GRADED',
            response: graded({
              result: 'false_alarm',
              points_awarded: 0,
              points_forfeited: 2,
              window_points: 0,
              session_points: 2,
              window_ended: true,
              outcome: 'false_alarm',
              next_prompt: null,
              timer_remaining_ms: null,
            }),
          },
        ],
        atPrompt(),
      ),
      'feedback',
    );
    expect(flashFor(feedback.graded)).toEqual({ amount: 2, variant: 'forfeit' });
    expect(feedback.sessionPoints).toBe(2);
  });

  it('ignores a grade that arrives outside the grading phase', () => {
    const prompt = atPrompt();
    expect(drillReducer(prompt, { type: 'ANSWER_GRADED', response: graded() })).toBe(prompt);
  });
});

describe('after a correct answer: move, reply, next prompt', () => {
  const feedback = run(
    [
      { type: 'ANSWER_SUBMITTED', answer: 'safe' },
      { type: 'ANSWER_GRADED', response: graded() },
    ],
    atPrompt(),
  );

  it('plays the prompted move, then the reply, then prompts again with the server countdown', () => {
    const advancing = asPhase(drillReducer(feedback, { type: 'FEEDBACK_DONE' }), 'advancing');
    expect(advancing.window.shownUcis).toEqual(LEAD_IN);

    const moved = asPhase(drillReducer(advancing, { type: 'ADVANCE_TICK' }), 'advancing');
    expect(moved.window.shownUcis).toEqual([...LEAD_IN, 'b8c6']);

    const next = asPhase(drillReducer(moved, { type: 'ADVANCE_TICK' }), 'prompt');
    expect(next.window.shownUcis).toEqual([...LEAD_IN, 'b8c6', 'f1b5']);
    expect(next.prompt).toEqual({ move_index: 2, move_uci: 'a7a6' });
    expect(next.timerMs).toBe(NEXT_TIMER_MS);
  });

  it('a window that continues without an opponent reply still reaches the next prompt', () => {
    const noReply = run(
      [
        { type: 'ANSWER_SUBMITTED', answer: 'safe' },
        { type: 'ANSWER_GRADED', response: graded({ reply_uci: null }) },
        { type: 'FEEDBACK_DONE' },
        { type: 'ADVANCE_TICK' },
        { type: 'ADVANCE_TICK' },
      ],
      atPrompt(),
    );
    expect(asPhase(noReply, 'prompt').window.shownUcis).toEqual([...LEAD_IN, 'b8c6']);
  });
});

describe('window end and session end', () => {
  const ended = run(
    [
      { type: 'ANSWER_SUBMITTED', answer: 'blunder' },
      {
        type: 'ANSWER_GRADED',
        response: graded({
          result: 'caught',
          points_awarded: 3,
          window_points: 3,
          session_points: 7,
          window_ended: true,
          outcome: 'caught',
          next_prompt: null,
          timer_remaining_ms: null,
          reply_uci: null,
        }),
      },
    ],
    atPrompt(),
  );

  it('feedback then FEEDBACK_DONE goes to the solution load with the outcome', () => {
    asPhase(ended, 'feedback');
    const over = asPhase(drillReducer(ended, { type: 'FEEDBACK_DONE' }), 'solution_loading');
    expect(over.outcome).toBe('caught');
    expect(over.sessionPoints).toBe(7);
  });

  it('NEXT_WINDOW loads the next position', () => {
    const over = run(
      [{ type: 'FEEDBACK_DONE' }, { type: 'SOLUTION_LOADED', solution: FALSE_ALARM_SOLUTION }],
      ended,
    );
    const next = asPhase(drillReducer(over, { type: 'NEXT_WINDOW' }), 'loading_window');
    expect(next.position).toBe(1);
    expect(next.sessionPoints).toBe(7);
    expect(next.session.sessionId).toBe(SESSION_ID);
  });

  it('NEXT_WINDOW after the last window finishes the session, SESSION_FINISHED ends it', () => {
    const lastWindow = run([
      { type: 'SESSION_READY', session: { ...SESSION, current_position: WINDOW_COUNT - 1 } },
      { type: 'WINDOW_LOADED', response: windowStart({ position: WINDOW_COUNT - 1 }) },
      ...[...LEAD_IN, 'prompt'].map((): DrillEvent => ({ type: 'LEAD_IN_TICK' })),
      { type: 'ANSWER_SUBMITTED', answer: 'blunder' },
      {
        type: 'ANSWER_GRADED',
        response: graded({
          window_ended: true,
          outcome: 'caught',
          next_prompt: null,
          timer_remaining_ms: null,
        }),
      },
      { type: 'FEEDBACK_DONE' },
      { type: 'SOLUTION_LOADED', solution: FALSE_ALARM_SOLUTION },
    ]);
    asPhase(lastWindow, 'solution');
    const finishing = asPhase(drillReducer(lastWindow, { type: 'NEXT_WINDOW' }), 'finishing');
    const result: SessionResultResponse = {
      session_id: SESSION_ID,
      session_points: 9,
      points_possible: 20,
      score_pct: 45,
      windows: [],
    };
    const end = asPhase(drillReducer(finishing, { type: 'SESSION_FINISHED', result }), 'session_end');
    expect(end.result).toBe(result);
  });
});

describe('better move and solution (D-12, D-14, D-17)', () => {
  const TASK = { fen: START_FEN, key_uci: 'd2d4', server_graded_moves: [] };
  const BETTER_GRADED: BetterMoveResponse = {
    tier: 'good',
    points_awarded: 2,
    window_points: 5,
    session_points: 9,
  };
  const BLUNDER_SOLUTION: WindowSolution = {
    kind: 'blunder',
    outcome: 'caught',
    is_own: true,
    window_case: 'allowed',
    game_id: 3,
    analysis_ply: 6,
    fen: START_FEN,
    blunder_uci: 'g1f3',
    key_uci: 'd2d4',
    better_move_uci: 'd2d4',
    better_move_tier: 'good',
    server_graded_moves: [],
    game_info: null,
    window_points: 5,
    safe_points: 0,
    blunder_points: 3,
    better_move_points: 2,
  };

  /** A window answered "blunder" and graded, at the end of the answer feedback. */
  function answered(overrides: Partial<AnswerResponse>, position = 0): DrillState {
    return run(
      [
        { type: 'SESSION_READY', session: { ...SESSION, current_position: position } },
        { type: 'WINDOW_LOADED', response: windowStart({ position }) },
        ...[...LEAD_IN, 'prompt'].map((): DrillEvent => ({ type: 'LEAD_IN_TICK' })),
        { type: 'ANSWER_SUBMITTED', answer: 'blunder' },
        {
          type: 'ANSWER_GRADED',
          response: graded({
            window_ended: true,
            next_prompt: null,
            timer_remaining_ms: null,
            reply_uci: null,
            ...overrides,
          }),
        },
      ],
      initialDrillState,
    );
  }

  const CAUGHT: Partial<AnswerResponse> = {
    result: 'caught',
    outcome: 'caught',
    session_points: 7,
    better_move: TASK,
  };

  it('a caught blunder goes feedback -> better_move -> grading -> feedback -> solution_loading -> solution', () => {
    const feedback = asPhase(answered(CAUGHT), 'feedback');
    const ask = asPhase(drillReducer(feedback, { type: 'FEEDBACK_DONE' }), 'better_move');
    expect(ask.task).toBe(TASK);
    expect(ask.outcome).toBe('caught');
    expect(ask.sessionPoints).toBe(7);

    const grading = asPhase(
      drillReducer(ask, { type: 'BETTER_MOVE_SUBMITTED', playedUci: 'd2d4' }),
      'better_move_grading',
    );
    expect(grading.playedUci).toBe('d2d4');

    // The server's totals replace the client's.
    const gradedState = asPhase(
      drillReducer(grading, { type: 'BETTER_MOVE_GRADED', response: BETTER_GRADED }),
      'better_move_feedback',
    );
    expect(gradedState.sessionPoints).toBe(9);
    expect(gradedState.window.windowPoints).toBe(5);
    expect(gradedState.betterMove).toBe(BETTER_GRADED);
    // The catch and the better move are still in the pot ...
    expect(drillProgress(gradedState)).toMatchObject({
      banked: 4,
      pot: 5,
      potEvent: { kind: 'gain', amount: BETTER_GRADED.points_awarded },
    });

    const loading = asPhase(
      drillReducer(gradedState, { type: 'FEEDBACK_DONE' }),
      'solution_loading',
    );
    expect(loading.sessionPoints).toBe(9);
    expect(drillProgress(loading)).toMatchObject({ banked: 4, pot: 5, potEvent: null });

    const solution = asPhase(
      drillReducer(loading, { type: 'SOLUTION_LOADED', solution: BLUNDER_SOLUTION }),
      'solution',
    );
    expect(solution.solution).toBe(BLUNDER_SOLUTION);
    // ... stay there on the solution, which shows what the window was worth ...
    const shown = drillProgress(solution);
    expect(shown).toMatchObject({ banked: 4, pot: 5, potEvent: null, windowOver: true });
    // ... and are banked on Next.
    expect(shown && bankingProgress(shown)).toMatchObject({
      banked: 9,
      pot: null,
      potEvent: { kind: 'bank', amount: 5 },
    });

    const next = asPhase(drillReducer(solution, { type: 'NEXT_WINDOW' }), 'loading_window');
    expect(next.position).toBe(1);
    expect(next.sessionPoints).toBe(9);
  });

  it.each([
    ['missed', { result: 'missed', outcome: 'missed' }],
    ['cleared', { result: 'correct_safe', outcome: 'cleared' }],
    ['false alarm', { result: 'false_alarm', outcome: 'false_alarm' }],
  ] as const)('a %s window goes from feedback straight to solution_loading', (_name, overrides) => {
    const feedback = asPhase(answered(overrides), 'feedback');
    const loading = asPhase(drillReducer(feedback, { type: 'FEEDBACK_DONE' }), 'solution_loading');
    expect(loading.outcome).toBe(overrides.outcome);
  });

  it('the last window Next goes to finishing', () => {
    const lastPosition = WINDOW_COUNT - 1;
    const state = run(
      [
        { type: 'FEEDBACK_DONE' },
        { type: 'BETTER_MOVE_SUBMITTED', playedUci: 'd2d4' },
        { type: 'BETTER_MOVE_GRADED', response: BETTER_GRADED },
        { type: 'FEEDBACK_DONE' },
        { type: 'SOLUTION_LOADED', solution: BLUNDER_SOLUTION },
        { type: 'NEXT_WINDOW' },
      ],
      answered(CAUGHT, lastPosition),
    );
    const finishing = asPhase(state, 'finishing');
    expect(finishing.position).toBe(lastPosition);
    expect(finishing.sessionPoints).toBe(9);
  });

  it('events outside their phase are ignored', () => {
    const ask = asPhase(drillReducer(answered(CAUGHT), { type: 'FEEDBACK_DONE' }), 'better_move');
    // Grading result and solution cannot arrive before a move was played.
    expect(drillReducer(ask, { type: 'BETTER_MOVE_GRADED', response: BETTER_GRADED })).toBe(ask);
    expect(drillReducer(ask, { type: 'SOLUTION_LOADED', solution: BLUNDER_SOLUTION })).toBe(ask);
    // Next is only accepted on the solution screen.
    expect(drillReducer(ask, { type: 'NEXT_WINDOW' })).toBe(ask);
    // A second move cannot be submitted while the first is grading.
    const grading = drillReducer(ask, { type: 'BETTER_MOVE_SUBMITTED', playedUci: 'd2d4' });
    expect(drillReducer(grading, { type: 'BETTER_MOVE_SUBMITTED', playedUci: 'g1f3' })).toBe(
      grading,
    );
  });

  it('no path reaches the retired window_over outcome panel phase', () => {
    const phases = new Set<string>();
    const record = (state: DrillState): DrillState => {
      phases.add(state.phase);
      return state;
    };
    const events: DrillEvent[] = [
      { type: 'FEEDBACK_DONE' },
      { type: 'BETTER_MOVE_SUBMITTED', playedUci: 'd2d4' },
      { type: 'BETTER_MOVE_GRADED', response: BETTER_GRADED },
      { type: 'FEEDBACK_DONE' },
      { type: 'SOLUTION_LOADED', solution: BLUNDER_SOLUTION },
      { type: 'NEXT_WINDOW' },
    ];
    events.reduce((state, event) => record(drillReducer(state, event)), record(answered(CAUGHT)));
    expect(phases.has('window_over')).toBe(false);
    expect(phases.has('solution')).toBe(true);
  });
});

describe('applyUcis', () => {
  it('returns the FEN after playing the UCIs', () => {
    expect(applyUcis(START_FEN, ['e2e4', 'e7e5'])).toBe(
      'rnbqkbnr/pppp1ppp/8/4p3/4P3/8/PPPP1PPP/RNBQKBNR w KQkq - 0 2',
    );
  });

  it('returns the start FEN for no moves and handles a promotion', () => {
    expect(applyUcis(START_FEN, [])).toBe(START_FEN);
    expect(applyUcis('7k/4P3/8/8/8/8/8/K7 w - - 0 1', ['e7e8q'])).toBe(
      '4Q2k/8/8/8/8/8/8/K7 b - - 0 1',
    );
  });
});

describe('animation budget (D-12, D-18)', () => {
  it('the lead-in replay fits the server allowance before the first countdown', () => {
    // The start delay shows the first ply; every ply is then followed by one interval, the
    // last of which hands over to the prompt.
    expect(LEAD_IN_START_DELAY_MS + LEAD_IN_PLIES * LEAD_IN_PLY_INTERVAL_MS).toBeLessThan(
      PROMPT_ANIMATION_BUDGET_MS,
    );
  });

  it('feedback, then the move and the reply fit the allowance before the next countdown', () => {
    expect(FEEDBACK_DISPLAY_MS + 2 * MOVE_REPLY_DELAY_MS).toBeLessThan(PROMPT_ANIMATION_BUDGET_MS);
  });
});

describe('WINDOW_LOADED after a stale prompt (server state wins)', () => {
  it('from the grading phase it goes straight to the prompt with the server timer and points', () => {
    const grading = drillReducer(atPrompt(), { type: 'ANSWER_SUBMITTED', answer: 'safe' });
    expect(grading.phase).toBe('grading');

    const state = asPhase(
      drillReducer(grading, {
        type: 'WINDOW_LOADED',
        response: windowStart({
          answered: [
            {
              move_index: 1,
              move_uci: 'b8c6',
              reply_uci: 'f1b5',
              result: 'correct_safe',
              points_awarded: 1,
              points_forfeited: 0,
            },
          ],
          prompt: { move_index: 2, move_uci: 'a7a6' },
          timer_remaining_ms: RESUMED_TIMER_MS,
          session_points: 9,
        }),
      }),
      'prompt',
    );

    expect(state.timerMs).toBe(RESUMED_TIMER_MS);
    expect(state.prompt.move_index).toBe(2);
    expect(state.sessionPoints).toBe(9);
    expect(state.window.shownUcis).toEqual([...LEAD_IN, 'b8c6', 'f1b5']);
  });

  it('even with nothing answered yet it skips the lead-in replay', () => {
    const grading = drillReducer(atPrompt(), { type: 'ANSWER_SUBMITTED', answer: 'safe' });
    const state = drillReducer(grading, {
      type: 'WINDOW_LOADED',
      response: windowStart({ timer_remaining_ms: RESUMED_TIMER_MS }),
    });
    const prompt = asPhase(state, 'prompt');
    expect(prompt.window.shownUcis).toEqual(LEAD_IN);
  });
});

describe('moveSoundFor', () => {
  const AFTER_E4_D5 = 'rnbqkbnr/ppp1pppp/8/3p4/4P3/8/PPPP1PPP/RNBQKBNR w KQkq - 0 2';

  it('classifies a plain move, a capture and a check (check wins)', () => {
    expect(moveSoundFor(AFTER_E4_D5, 'g1f3')).toBe('move');
    expect(moveSoundFor(AFTER_E4_D5, 'e4d5')).toBe('capture');
    expect(moveSoundFor(AFTER_E4_D5, 'f1b5')).toBe('check');
  });

  it('is null for an illegal move', () => {
    expect(moveSoundFor(AFTER_E4_D5, 'e4e6')).toBeNull();
  });
});
