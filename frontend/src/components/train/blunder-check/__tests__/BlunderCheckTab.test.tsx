// @vitest-environment jsdom
/**
 * BlunderCheckTab: the start screen states (start, resume, empty supply, failures), the
 * error phase's way back, the double-click guard (T-249-29) and the no-analytics guard (D-19).
 */
import { readdirSync, readFileSync } from 'node:fs';
import { join } from 'node:path';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { AxiosError } from 'axios';
import type { AxiosResponse } from 'axios';
import { act } from '@testing-library/react';
import { MemoryRouter, useLocation } from 'react-router';
import { TooltipProvider } from '@/components/ui/tooltip';
import {
  BANK_COIN_COUNT,
  BANK_COIN_INTERVAL_MS,
  BANK_HOLD_MS,
  COIN_SOUND_MS,
  FEEDBACK_DISPLAY_MS,
  LEAD_IN_PLY_INTERVAL_MS,
  LEAD_IN_START_DELAY_MS,
  MOVE_REPLY_DELAY_MS,
  applyUcis,
} from '@/lib/blunderCheckDrill';
import { buildTrainPuzzleAnalysisUrl } from '@/lib/analysisUrl';
import type {
  AnswerRequest,
  AnswerResponse,
  BetterMoveRequest,
  BetterMoveResponse,
  BlunderCheckSessionResponse,
  BlunderSolution,
  SessionResultResponse,
  WindowSolution,
  WindowStartResponse,
} from '@/types/blunderCheck';

const SESSION: BlunderCheckSessionResponse = {
  session_id: 7,
  window_count: 6,
  current_position: 2,
  session_points: 5,
  windows: [],
};
const HTTP_CONFLICT = 409;
const HTTP_SERVER_ERROR = 500;
const LOAD_ERROR_COPY =
  'Failed to load blunder check. Something went wrong. Please try again in a moment.';

const getOpenSession = vi.fn(async (): Promise<BlunderCheckSessionResponse | null> => null);
const composeOrResumeSession = vi.fn(async (): Promise<BlunderCheckSessionResponse> => SESSION);
const startWindow = vi.fn<(sessionId: number, position: number) => Promise<WindowStartResponse>>();
const finishSession = vi.fn<(sessionId: number) => Promise<SessionResultResponse>>();
const answer = vi.fn<
  (sessionId: number, position: number, body: AnswerRequest) => Promise<AnswerResponse>
>();
const submitBetterMove = vi.fn<
  (sessionId: number, position: number, body: BetterMoveRequest) => Promise<BetterMoveResponse>
>();
const getSolution = vi.fn<(sessionId: number, position: number) => Promise<WindowSolution>>();

vi.mock('@/api/client', async () => {
  const actual = await vi.importActual<typeof import('@/api/client')>('@/api/client');
  return {
    ...actual,
    blunderCheckApi: {
      getOpenSession: () => getOpenSession(),
      composeOrResumeSession: () => composeOrResumeSession(),
      startWindow: (sessionId: number, position: number) => startWindow(sessionId, position),
      answer: (sessionId: number, position: number, body: AnswerRequest) =>
        answer(sessionId, position, body),
      submitBetterMove: (sessionId: number, position: number, body: BetterMoveRequest) =>
        submitBetterMove(sessionId, position, body),
      getSolution: (sessionId: number, position: number) => getSolution(sessionId, position),
      finishSession: (sessionId: number) => finishSession(sessionId),
    },
  };
});

// One grading engine for the whole tab, scripted by the tests (no Worker in jsdom).
const engine = vi.hoisted(() => ({
  isReady: true,
  hasError: false,
  startGrading: vi.fn(),
  abortGrading: vi.fn(),
  restartEngine: vi.fn(),
  gradeMove: vi.fn(),
  startGameMoveSearch: vi.fn(),
  recheckMove: vi.fn(),
}));
vi.mock('@/hooks/useTrainGradingEngine', () => ({
  useTrainGradingEngine: () => engine,
}));
// The solution's move tree runs its own reveal engine; a static one stands in (no Worker in jsdom).
vi.mock('@/hooks/useStockfishEngine', () => ({
  useStockfishEngine: (options: { fen: string | null; enabled: boolean }) => ({
    evalCp: null,
    evalMate: null,
    pvLines: [],
    depth: 0,
    isAnalyzing: false,
    isReady: true,
    currentFen: options.enabled ? options.fen : null,
  }),
}));

// The error phase has no UI trigger until the drill component dispatches FAILED, so the
// "Back to start" test starts the reducer from an error state.
const drillStart = vi.hoisted(() => ({ errored: false }));
vi.mock('@/lib/blunderCheckDrill', async () => {
  const actual = await vi.importActual<typeof import('@/lib/blunderCheckDrill')>(
    '@/lib/blunderCheckDrill',
  );
  return {
    ...actual,
    get initialDrillState() {
      return drillStart.errored ? { phase: 'error', message: 'boom' } : actual.initialDrillState;
    },
  };
});

// The badge counts up unless the user prefers reduced motion; the end screen test wants the
// final number straight away.
// A test that wants the animated path flips `reducedMotion.current` for itself.
const reducedMotion = vi.hoisted(() => ({ current: true }));
vi.mock('@/lib/confetti', async () => {
  const actual = await vi.importActual<typeof import('@/lib/confetti')>('@/lib/confetti');
  return { ...actual, prefersReducedMotion: () => reducedMotion.current };
});

// The reveal action bar renders under the board from `sm` up (phones publish it to the fixed
// bottom bar, which these tests do not mount); jsdom has no matchMedia.
vi.mock('@/hooks/useIsDesktop', () => ({ useIsDesktop: () => true, useIsSmUp: () => true }));

const playSound = vi.hoisted(() => vi.fn());
vi.mock('@/lib/sounds', async () => {
  const actual = await vi.importActual<typeof import('@/lib/sounds')>('@/lib/sounds');
  return { ...actual, playSound, unlockAudio: vi.fn() };
});

// A light board: the FEN and the drawn arrows are what the drill decides. The latest drop
// handler is kept so a test can play a move the way the real board reports it.
const boardDrop = vi.hoisted(() => ({
  current: null as null | ((from: string, to: string) => boolean),
}));
vi.mock('@/components/board/ChessBoard', () => ({
  ChessBoard: ({
    position,
    lastMove,
    arrows,
    flipped,
    onPieceDrop,
  }: {
    position: string;
    lastMove?: { from: string; to: string } | null;
    arrows?: { startSquare: string; endSquare: string }[];
    flipped?: boolean;
    onPieceDrop?: (from: string, to: string) => boolean;
  }) => {
    boardDrop.current = onPieceDrop ?? null;
    return (
      <div
        data-testid="board-mock"
        data-position={position}
        data-last-move={lastMove ? `${lastMove.from}${lastMove.to}` : ''}
        data-flipped={flipped ? 'true' : 'false'}
        data-arrows={(arrows ?? []).map((a) => `${a.startSquare}${a.endSquare}`).join(',')}
      />
    );
  },
}));

import { BlunderCheckTab } from '@/components/train/blunder-check/BlunderCheckTab';

/** Renders the router's current location so a test can assert where Analyze navigated. */
function LocationProbe() {
  const location = useLocation();
  return <div data-testid="location-probe">{`${location.pathname}${location.search}`}</div>;
}

function httpError(status: number, detail?: string): AxiosError {
  return new AxiosError('failed', 'ERR_BAD_REQUEST', undefined, undefined, {
    status,
    data: detail === undefined ? undefined : { detail },
  } as AxiosResponse);
}

function renderTab(onImmersiveChange: (immersive: boolean) => void = vi.fn()) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
      <TooltipProvider>
        <BlunderCheckTab onImmersiveChange={onImmersiveChange} />
        <LocationProbe />
      </TooltipProvider>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

/** The Start button once the open-session query has settled (it is disabled while loading). */
async function enabledStartButton(): Promise<HTMLButtonElement> {
  const button = (await screen.findByTestId('blunder-check-btn-start')) as HTMLButtonElement;
  await waitFor(() => expect(button.disabled).toBe(false));
  return button;
}

beforeEach(() => {
  drillStart.errored = false;
  getOpenSession.mockReset();
  getOpenSession.mockImplementation(async () => null);
  composeOrResumeSession.mockReset();
  composeOrResumeSession.mockImplementation(async () => SESSION);
  startWindow.mockReset();
  // Never resolves by default: a test that needs a window supplies its own response.
  startWindow.mockImplementation(() => new Promise(() => {}));
  answer.mockReset();
  submitBetterMove.mockReset();
  getSolution.mockReset();
  getSolution.mockImplementation(async () => BLUNDER_SOLUTION);
  engine.hasError = false;
  engine.startGrading.mockReset();
  engine.restartEngine.mockReset();
  engine.gradeMove.mockReset();
  engine.startGameMoveSearch.mockReset();
  engine.startGameMoveSearch.mockImplementation(async (_fen: string, uci: string) => ({
    moves: [uci],
    evalCp: 10,
    evalMate: null,
  }));
  boardDrop.current = null;
  playSound.mockReset();
  finishSession.mockReset();
});

afterEach(() => {
  cleanup();
  sessionStorage.clear();
});

describe('start screen', () => {
  it('shows the intro and a Start button when there is no open session', async () => {
    renderTab();

    const button = await enabledStartButton();
    expect(button.textContent).toBe('Start');
    expect(screen.getByText('Blunder check')).not.toBeNull();
    expect(
      screen.getByText('Check each move before it is played: Good move or blunder?'),
    ).not.toBeNull();
    expect(screen.queryByTestId('blunder-check-open-session')).toBeNull();
  });

  it('offers Resume and names the open window when a session is in progress', async () => {
    getOpenSession.mockImplementation(async () => SESSION);
    renderTab();

    await waitFor(() =>
      expect(screen.getByTestId('blunder-check-btn-start').textContent).toBe('Resume'),
    );
    expect(screen.getByTestId('blunder-check-open-session').textContent).toBe(
      'Session in progress: sequence 3 of 6',
    );
  });

  it('Resume goes through the compose call and shows the open window and its points', async () => {
    getOpenSession.mockImplementation(async () => SESSION);
    renderTab();

    await waitFor(() =>
      expect(screen.getByTestId('blunder-check-btn-start').textContent).toBe('Resume'),
    );
    fireEvent.click(screen.getByTestId('blunder-check-btn-start'));

    await waitFor(() =>
      expect(screen.getByTestId('blunder-check-window-counter').textContent).toBe('3 of 6'),
    );
    expect(screen.getByTestId('blunder-check-points').textContent).toBe('5 pts');
    expect(composeOrResumeSession).toHaveBeenCalledTimes(1);
  });

  it('a 409 from compose says there are no windows yet', async () => {
    composeOrResumeSession.mockImplementation(async () => {
      throw httpError(HTTP_CONFLICT);
    });
    renderTab();

    fireEvent.click(await enabledStartButton());

    await waitFor(() =>
      expect(screen.getByTestId('blunder-check-none-available').textContent).toBe(
        'No blunder-check sequences are available yet. Import and analyze more games, then try again.',
      ),
    );
    expect(screen.queryByTestId('blunder-check-compose-error')).toBeNull();
  });

  it('a non-409 compose failure shows the generic load error', async () => {
    composeOrResumeSession.mockImplementation(async () => {
      throw httpError(HTTP_SERVER_ERROR);
    });
    renderTab();

    fireEvent.click(await enabledStartButton());

    await waitFor(() =>
      expect(screen.getByTestId('blunder-check-compose-error').textContent).toBe(LOAD_ERROR_COPY),
    );
    expect(screen.queryByTestId('blunder-check-none-available')).toBeNull();
  });

  it('a failed open-session query shows the load error instead of the Start button', async () => {
    getOpenSession.mockImplementation(async () => {
      throw httpError(HTTP_SERVER_ERROR);
    });
    renderTab();

    await waitFor(() =>
      expect(screen.getByTestId('blunder-check-load-error').textContent).toBe(LOAD_ERROR_COPY),
    );
    expect(screen.queryByTestId('blunder-check-btn-start')).toBeNull();
  });
});

describe('double click (T-249-29)', () => {
  it('sends one compose request while the first is pending', async () => {
    composeOrResumeSession.mockImplementation(() => new Promise(() => {}));
    renderTab();

    const button = await enabledStartButton();
    fireEvent.click(button);
    fireEvent.click(button);

    await waitFor(() => expect(composeOrResumeSession).toHaveBeenCalledTimes(1));
    expect((screen.getByTestId('blunder-check-btn-start') as HTMLButtonElement).disabled).toBe(
      true,
    );
    expect(composeOrResumeSession).toHaveBeenCalledTimes(1);
  });
});

describe('error phase', () => {
  it('Back to start returns to the start screen', async () => {
    drillStart.errored = true;
    renderTab();

    expect(screen.getByTestId('blunder-check-error').textContent).toContain(LOAD_ERROR_COPY);
    fireEvent.click(screen.getByTestId('blunder-check-btn-reset'));

    await waitFor(() => expect(screen.getByTestId('blunder-check-start-screen')).not.toBeNull());
    expect(screen.queryByTestId('blunder-check-error')).toBeNull();
  });
});

describe('immersive reporting', () => {
  it('is not immersive on the start screen and clears on unmount', async () => {
    const onImmersiveChange = vi.fn();
    const { unmount } = renderTab(onImmersiveChange);

    await screen.findByTestId('blunder-check-btn-start');
    expect(onImmersiveChange).toHaveBeenLastCalledWith(false);
    expect(onImmersiveChange).not.toHaveBeenCalledWith(true);
    unmount();
    expect(onImmersiveChange).toHaveBeenLastCalledWith(false);
  });
});

// ─── The window loop (fake timers) ───────────────────────────────────────────

const START_FEN = 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1';
const LEAD_IN = ['e2e4', 'e7e5'];
const PROMPT_UCI = 'g1f3';
const REPLY_UCI = 'b8c6';
const NEXT_PROMPT_UCI = 'f1c4';
const FRESH_TIMER_MS = 10_000;
/** The first judged move, already answered correctly (a resumed window carries it). */
const ANSWERED_FIRST_MOVE: WindowStartResponse['answered'] = [
  {
    move_index: 1,
    move_uci: PROMPT_UCI,
    reply_uci: REPLY_UCI,
    result: 'correct_safe',
    points_awarded: 1,
    points_forfeited: 0,
  },
];
/** The position before the judged move: 1. e4 e5 played, white to move. */
const PRE_BLUNDER_FEN = 'rnbqkbnr/pppp1ppp/8/4p3/4P3/8/PPPP1PPP/RNBQKBNR w KQkq - 0 2';
const KEY_UCI = 'd2d4';
const ANALYSIS_GAME_ID = 55;
const ANALYSIS_PLY = 4;
/** What the server hands out after a caught blunder (plan 04's better_move). */
const BETTER_MOVE_TASK = { fen: PRE_BLUNDER_FEN, key_uci: KEY_UCI, server_graded_moves: [] };
const BLUNDER_SOLUTION: BlunderSolution = {
  kind: 'blunder',
  outcome: 'caught',
  is_own: true,
  window_case: 'allowed',
  game_id: ANALYSIS_GAME_ID,
  analysis_ply: ANALYSIS_PLY,
  fen: PRE_BLUNDER_FEN,
  blunder_uci: PROMPT_UCI,
  key_uci: KEY_UCI,
  better_move_uci: KEY_UCI,
  better_move_tier: 'good',
  server_graded_moves: [],
  game_info: null,
  window_points: 5,
  safe_points: 0,
  blunder_points: 3,
  better_move_points: 2,
};
const TWO_WINDOW_SESSION: BlunderCheckSessionResponse = {
  session_id: 7,
  window_count: 2,
  current_position: 0,
  session_points: 0,
  windows: [],
};

function windowStart(overrides: Partial<WindowStartResponse> = {}): WindowStartResponse {
  return {
    position: 0,
    start_fen: START_FEN,
    orientation: 'white',
    lead_in_ucis: LEAD_IN,
    answered: [],
    prompt: { move_index: 1, move_uci: PROMPT_UCI },
    timer_remaining_ms: FRESH_TIMER_MS,
    move_timer_seconds: 10,
    window_points: 0,
    session_points: 0,
    better_move: null,
    ...overrides,
  };
}

function gradedAnswer(overrides: Partial<AnswerResponse> = {}): AnswerResponse {
  return {
    move_index: 1,
    result: 'correct_safe',
    points_awarded: 1,
    points_forfeited: 0,
    window_points: 1,
    session_points: 1,
    window_ended: false,
    outcome: null,
    reply_uci: REPLY_UCI,
    next_prompt: { move_index: 2, move_uci: NEXT_PROMPT_UCI },
    timer_remaining_ms: FRESH_TIMER_MS,
    better_move: null,
    ...overrides,
  };
}

/** Moves fake time forward and lets the resulting promises and renders settle. */
async function advance(ms: number): Promise<void> {
  await act(async () => {
    await vi.advanceTimersByTimeAsync(ms);
  });
}

function boardFen(): string {
  return screen.getByTestId('board-mock').getAttribute('data-position') ?? '';
}

function boardArrows(): string {
  return screen.getByTestId('board-mock').getAttribute('data-arrows') ?? '';
}

function buttonDisabled(testId: string): boolean {
  return (screen.getByTestId(testId) as HTMLButtonElement).disabled;
}

/** Starts a session and plays the lead-in so the first prompt is open. */
async function reachFirstPrompt(): Promise<void> {
  renderTab();
  await advance(50);
  fireEvent.click(screen.getByTestId('blunder-check-btn-start'));
  await advance(50);
  // One advance per tick: each tick's timer is scheduled by an effect after a render, which
  // only happens when the act scope of the previous advance closes.
  await advance(LEAD_IN_START_DELAY_MS);
  for (let ply = 0; ply < LEAD_IN.length; ply += 1) {
    await advance(LEAD_IN_PLY_INTERVAL_MS);
  }
}

describe('window loop', () => {
  beforeEach(() => {
    vi.useFakeTimers();
    composeOrResumeSession.mockImplementation(async () => TWO_WINDOW_SESSION);
    startWindow.mockImplementation(async () => windowStart());
  });
  afterEach(() => {
    vi.useRealTimers();
  });

  it('replays the lead-in, then shows the arrow with the piece still on its source square', async () => {
    renderTab();
    await advance(50);
    fireEvent.click(screen.getByTestId('blunder-check-btn-start'));
    await advance(50);

    expect(startWindow).toHaveBeenCalledWith(7, 0);
    // Lead-in: nothing played yet, no arrow, no answering.
    expect(boardFen()).toBe(START_FEN);
    expect(boardArrows()).toBe('');
    expect(buttonDisabled('blunder-check-btn-safe')).toBe(true);

    await advance(LEAD_IN_START_DELAY_MS);
    expect(boardFen()).toBe(applyUcis(START_FEN, LEAD_IN.slice(0, 1)));
    await advance(LEAD_IN_PLY_INTERVAL_MS);
    expect(boardFen()).toBe(applyUcis(START_FEN, LEAD_IN));
    expect(boardArrows()).toBe('');

    // The hand-over tick opens the prompt: the judged move is only an arrow.
    await advance(LEAD_IN_PLY_INTERVAL_MS);
    expect(boardFen()).toBe(applyUcis(START_FEN, LEAD_IN));
    expect(boardArrows()).toBe('g1f3');
    expect(screen.getByText('Good move or blunder?')).not.toBeNull();
    expect(buttonDisabled('blunder-check-btn-safe')).toBe(false);
    expect(buttonDisabled('blunder-check-btn-blunder')).toBe(false);
  });

  it('plays a move sound for every lead-in ply, the prompted move and the reply, and the question sound for each arrow', async () => {
    answer.mockImplementation(async () => gradedAnswer());
    await reachFirstPrompt();
    const moveSounds = (): number =>
      playSound.mock.calls.filter(([event]) => event === 'move').length;
    const questionSounds = (): number =>
      playSound.mock.calls.filter(([event]) => event === 'question').length;
    // The lead-in plies, then the first prompt's arrow.
    expect(moveSounds()).toBe(LEAD_IN.length);
    expect(questionSounds()).toBe(1);

    fireEvent.click(screen.getByTestId('blunder-check-btn-safe'));
    await advance(50);
    await advance(FEEDBACK_DISPLAY_MS);
    await advance(MOVE_REPLY_DELAY_MS);
    await advance(MOVE_REPLY_DELAY_MS);
    // The prompted move and the reply, then the next prompt's arrow.
    expect(moveSounds()).toBe(LEAD_IN.length + 2);
    expect(questionSounds()).toBe(2);
  });

  it('a graded Good plays the move and then the reply, then shows the next arrow', async () => {
    answer.mockImplementation(async () => gradedAnswer());
    await reachFirstPrompt();

    fireEvent.click(screen.getByTestId('blunder-check-btn-safe'));
    await advance(0);

    expect(answer).toHaveBeenCalledTimes(1);
    const call = answer.mock.calls[0];
    expect(call?.[0]).toBe(7);
    expect(call?.[1]).toBe(0);
    expect(call?.[2]).toMatchObject({ move_index: 1, answer: 'safe' });
    expect(typeof call?.[2].client_elapsed_ms).toBe('number');
    // The server's point is shown straight away, over the board; it is still flying to the pot.
    expect(screen.getByTestId('blunder-check-points-flash').textContent).toBe('+1');
    expect(screen.getByTestId('blunder-check-pot-amount').textContent).toBe('+0');
    expect(screen.getByTestId('blunder-check-points').textContent).toBe('0 pts');
    // Feedback: the move is still not on the board.
    expect(boardFen()).toBe(applyUcis(START_FEN, LEAD_IN));

    await advance(FEEDBACK_DISPLAY_MS);
    await advance(MOVE_REPLY_DELAY_MS);
    expect(boardFen()).toBe(applyUcis(START_FEN, [...LEAD_IN, PROMPT_UCI]));
    expect(boardArrows()).toBe('');

    await advance(MOVE_REPLY_DELAY_MS);
    expect(boardFen()).toBe(applyUcis(START_FEN, [...LEAD_IN, PROMPT_UCI, REPLY_UCI]));
    expect(boardArrows()).toBe('f1c4');
    expect(buttonDisabled('blunder-check-btn-safe')).toBe(false);
  });

  it('a window-ending answer without a better-move task lands on the solution, and Next starts the next window', async () => {
    answer.mockImplementation(async () =>
      gradedAnswer({
        result: 'missed',
        points_awarded: 0,
        points_forfeited: 1,
        window_points: 0,
        session_points: 3,
        window_ended: true,
        outcome: 'missed',
        reply_uci: null,
        next_prompt: null,
        timer_remaining_ms: null,
      }),
    );
    getSolution.mockImplementation(async () => ({ ...BLUNDER_SOLUTION, outcome: 'missed' }));
    await reachFirstPrompt();

    fireEvent.click(screen.getByTestId('blunder-check-btn-safe'));
    await advance(0);
    await advance(FEEDBACK_DISPLAY_MS);
    await advance(50);

    // A missed blunder skips the better-move step.
    expect(screen.queryByTestId('blunder-check-better-move')).toBeNull();
    expect(getSolution).toHaveBeenCalledWith(7, 0);
    expect(screen.getByTestId('blunder-check-solution-heading').textContent).toBe('Missed blunder');
    expect(screen.queryByTestId('blunder-check-btn-safe')).toBeNull();
    // The lost pot stays up on the solution as a red +0.
    expect(screen.getByTestId('blunder-check-pot').getAttribute('data-pot-state')).toBe('lost');
    expect(screen.getByTestId('blunder-check-pot').textContent).toBe('+0');

    startWindow.mockImplementation(async () =>
      windowStart({ position: 1, session_points: 3 }),
    );
    fireEvent.click(screen.getByTestId('btn-train-next'));
    await advance(50);

    expect(startWindow).toHaveBeenLastCalledWith(7, 1);
    expect(screen.getByTestId('blunder-check-window-counter').textContent).toBe('2 of 2');
  });

  it('the countdown does not start during the lead-in or the move + reply animation', async () => {
    answer.mockImplementation(async () => gradedAnswer());
    renderTab();
    await advance(50);
    fireEvent.click(screen.getByTestId('blunder-check-btn-start'));
    await advance(50);
    await advance(LEAD_IN_START_DELAY_MS);
    expect(screen.getByTestId('blunder-check-timer').textContent).toBe('10s');
    await advance(LEAD_IN_PLY_INTERVAL_MS);
    expect(screen.getByTestId('blunder-check-timer').textContent).toBe('10s');
    await advance(LEAD_IN_PLY_INTERVAL_MS);
    // The prompt is open and the clock now runs.
    await advance(3_000);
    expect(screen.getByTestId('blunder-check-timer').textContent).toBe('7s');

    fireEvent.click(screen.getByTestId('blunder-check-btn-safe'));
    await advance(0);
    await advance(FEEDBACK_DISPLAY_MS);
    await advance(MOVE_REPLY_DELAY_MS);
    await advance(MOVE_REPLY_DELAY_MS);
    // The next prompt starts with the server's full countdown, not what was left before.
    expect(screen.getByTestId('blunder-check-timer').textContent).toBe('10s');
  });

  it('never says "your move" during the drill (D-09)', async () => {
    await reachFirstPrompt();
    expect(document.body.textContent?.toLowerCase()).not.toContain('your move');
  });
});

describe('timer, timeouts and points', () => {
  beforeEach(() => {
    vi.useFakeTimers();
    composeOrResumeSession.mockImplementation(async () => TWO_WINDOW_SESSION);
    startWindow.mockImplementation(async () => windowStart({ session_points: 5 }));
  });
  afterEach(() => {
    vi.useRealTimers();
  });

  it('plays the low-time sound once when 5 seconds remain', async () => {
    await reachFirstPrompt();

    await advance(FRESH_TIMER_MS - 6_000);
    expect(playSound).not.toHaveBeenCalledWith('low-time');
    await advance(1_500);
    await advance(2_000);
    expect(playSound.mock.calls.filter(([event]) => event === 'low-time')).toHaveLength(1);
  });

  it('a prompt left alone for 10 s posts a timeout once', async () => {
    answer.mockImplementation(async () =>
      gradedAnswer({ result: 'timeout_safe', points_awarded: 0, points_forfeited: 2 }),
    );
    await reachFirstPrompt();

    await advance(FRESH_TIMER_MS - 1_000);
    expect(answer).not.toHaveBeenCalled();
    await advance(1_000);
    expect(answer).toHaveBeenCalledTimes(1);
    expect(answer.mock.calls[0]?.[2]).toMatchObject({ move_index: 1, answer: 'timeout' });

    await advance(FRESH_TIMER_MS);
    expect(answer).toHaveBeenCalledTimes(1);
  });

  it('a forfeit shows the discarded points, busts the pot and plays the pot-bust sound', async () => {
    answer.mockImplementation(async () =>
      gradedAnswer({
        result: 'timeout_safe',
        points_awarded: 0,
        points_forfeited: 2,
        window_points: 0,
        session_points: 3,
      }),
    );
    await reachFirstPrompt();
    expect(screen.getByTestId('blunder-check-points').textContent).toBe('5 pts');

    await advance(FRESH_TIMER_MS);

    expect(screen.getByTestId('blunder-check-points-flash').textContent).toBe('-2');
    expect(screen.getByTestId('blunder-check-pot').getAttribute('data-pot-state')).toBe('bust');
    expect(screen.getByTestId('blunder-check-pot').textContent).toBe('-2');
    expect(screen.getByTestId('blunder-check-points').textContent).toBe('3 pts');
    expect(playSound).toHaveBeenCalledWith('pot-bust');
  });

  it('a correct Good shows +1, which lands in the pot with the coin sound', async () => {
    answer.mockImplementation(async () => gradedAnswer());
    await reachFirstPrompt();

    fireEvent.click(screen.getByTestId('blunder-check-btn-safe'));
    await advance(0);

    expect(screen.getByTestId('blunder-check-points-flash').textContent).toBe('+1');
    // In the air: the pot has not counted it and the coin has not dropped.
    expect(screen.getByTestId('blunder-check-pot-amount').textContent).toBe('+0');
    expect(playSound).not.toHaveBeenCalledWith('pot-gain');

    // These tests run with reduced motion (see the confetti mock): no flight, it lands next.
    await advance(1);

    // Landed: the pot adds it up and the coin drops.
    expect(screen.getByTestId('blunder-check-pot-amount').textContent).toBe('+1');
    expect(screen.getByTestId('blunder-check-points').textContent).toBe('0 pts');
    expect(playSound).toHaveBeenCalledWith('pot-gain');
  });

  it('the Good that clears a herring plays the full-score sound after its coin, an earlier Good does not', async () => {
    answer.mockImplementation(async () => gradedAnswer());
    await reachFirstPrompt();
    fireEvent.click(screen.getByTestId('blunder-check-btn-safe'));
    await advance(0);
    expect(playSound).not.toHaveBeenCalledWith('score-full');
    cleanup();
    playSound.mockClear();

    answer.mockImplementation(async () =>
      gradedAnswer({
        window_ended: true,
        outcome: 'cleared',
        next_prompt: null,
        timer_remaining_ms: null,
      }),
    );
    await reachFirstPrompt();
    fireEvent.click(screen.getByTestId('blunder-check-btn-safe'));
    await advance(1);
    // The last point's coin sounds first; the full-score sound waits for it to finish.
    expect(playSound).toHaveBeenCalledWith('pot-gain');
    expect(playSound).not.toHaveBeenCalledWith('score-full');
    await advance(COIN_SOUND_MS);
    expect(playSound).toHaveBeenCalledWith('score-full');
  });

  it('a piece moved while the question is open shakes the bubble with the nudge border', async () => {
    await reachFirstPrompt();
    const bubble = screen.getByTestId('train-bot-bubble');
    expect(bubble.getAttribute('data-nudge')).toBeNull();

    let accepted: boolean | undefined;
    await act(async () => {
      accepted = boardDrop.current?.('e2', 'e4');
    });

    // The board stays locked; the bubble points at the buttons.
    expect(accepted).toBe(false);
    expect(screen.getByTestId('train-bot-bubble').getAttribute('data-nudge')).toBe('true');
    expect(answer).not.toHaveBeenCalled();
  });

  it('a caught blunder shows +3 and plays the full-score sound, then the coin as it lands', async () => {
    answer.mockImplementation(async () =>
      gradedAnswer({
        result: 'caught',
        points_awarded: 3,
        window_points: 3,
        session_points: 8,
        window_ended: true,
        outcome: 'caught',
        reply_uci: null,
        next_prompt: null,
        timer_remaining_ms: null,
      }),
    );
    await reachFirstPrompt();

    fireEvent.click(screen.getByTestId('blunder-check-btn-blunder'));
    await advance(0);

    expect(screen.getByTestId('blunder-check-points-flash').textContent).toBe('+3');
    expect(playSound).toHaveBeenCalledWith('score-full');
    expect(playSound).not.toHaveBeenCalledWith('pot-gain');

    await advance(1);
    expect(playSound).toHaveBeenCalledWith('pot-gain');
  });

  it('a missed blunder that loses the pot plays the pot-bust sound', async () => {
    answer.mockImplementation(async () =>
      gradedAnswer({
        result: 'missed',
        points_awarded: 0,
        points_forfeited: 1,
        window_ended: true,
        outcome: 'missed',
        reply_uci: null,
        next_prompt: null,
        timer_remaining_ms: null,
      }),
    );
    await reachFirstPrompt();

    fireEvent.click(screen.getByTestId('blunder-check-btn-safe'));
    await advance(0);

    expect(playSound).toHaveBeenCalledWith('pot-bust');
  });

  it('D-18: a reload resumes on the prompt with the server remaining time, not a fresh 10 s', async () => {
    startWindow.mockImplementation(async () =>
      windowStart({
        answered: ANSWERED_FIRST_MOVE,
        prompt: { move_index: 2, move_uci: NEXT_PROMPT_UCI },
        timer_remaining_ms: 6_000,
      }),
    );
    answer.mockImplementation(async () =>
      gradedAnswer({ move_index: 2, result: 'timeout_safe', points_forfeited: 1 }),
    );
    renderTab();
    await advance(50);
    fireEvent.click(screen.getByTestId('blunder-check-btn-start'));
    await advance(50);

    // Straight to the prompt: the answered moves are on the board and the arrow is shown.
    expect(boardFen()).toBe(applyUcis(START_FEN, [...LEAD_IN, PROMPT_UCI, REPLY_UCI]));
    expect(boardArrows()).toBe('f1c4');
    expect(screen.getByTestId('blunder-check-timer').textContent).toBe('6s');

    await advance(5_000);
    expect(answer).not.toHaveBeenCalled();
    await advance(1_000);
    expect(answer).toHaveBeenCalledTimes(1);
    expect(answer.mock.calls[0]?.[2]).toMatchObject({ move_index: 2, answer: 'timeout' });
  });

  it('D-18: a prompt with no time left posts a timeout right after load', async () => {
    startWindow.mockImplementation(async () =>
      windowStart({
        answered: ANSWERED_FIRST_MOVE,
        prompt: { move_index: 2, move_uci: NEXT_PROMPT_UCI },
        timer_remaining_ms: 0,
      }),
    );
    answer.mockImplementation(async () =>
      gradedAnswer({ move_index: 2, result: 'timeout_safe', points_forfeited: 1 }),
    );
    renderTab();
    await advance(50);
    fireEvent.click(screen.getByTestId('blunder-check-btn-start'));
    await advance(50);
    await advance(0);

    expect(answer).toHaveBeenCalledTimes(1);
    expect(answer.mock.calls[0]?.[2]).toMatchObject({ move_index: 2, answer: 'timeout' });
  });

  it('a 409 stale_prompt re-fetches the window via start, and the server state wins', async () => {
    answer.mockImplementationOnce(async () => {
      throw httpError(HTTP_CONFLICT, 'stale_prompt');
    });
    await reachFirstPrompt();
    expect(startWindow).toHaveBeenCalledTimes(1);
    startWindow.mockImplementation(async () =>
      windowStart({
        answered: ANSWERED_FIRST_MOVE,
        prompt: { move_index: 2, move_uci: NEXT_PROMPT_UCI },
        timer_remaining_ms: 9_000,
        session_points: 6,
      }),
    );

    fireEvent.click(screen.getByTestId('blunder-check-btn-safe'));
    await advance(0);
    await advance(0);

    expect(startWindow).toHaveBeenCalledTimes(2);
    expect(startWindow).toHaveBeenLastCalledWith(7, 0);
    expect(boardFen()).toBe(applyUcis(START_FEN, [...LEAD_IN, PROMPT_UCI, REPLY_UCI]));
    expect(boardArrows()).toBe('f1c4');
    expect(screen.getByTestId('blunder-check-timer').textContent).toBe('9s');
    expect(screen.getByTestId('blunder-check-points').textContent).toBe('6 pts');
    expect(buttonDisabled('blunder-check-btn-safe')).toBe(false);
  });

  it('any other answer failure ends the drill in the error state', async () => {
    answer.mockImplementation(async () => {
      throw httpError(HTTP_SERVER_ERROR);
    });
    await reachFirstPrompt();

    fireEvent.click(screen.getByTestId('blunder-check-btn-safe'));
    await advance(0);

    expect(screen.getByTestId('blunder-check-error')).not.toBeNull();
  });
});

describe('better move and solution (D-12, D-14, D-17)', () => {
  const CAUGHT = (): AnswerResponse =>
    gradedAnswer({
      result: 'caught',
      points_awarded: 3,
      window_points: 3,
      session_points: 3,
      window_ended: true,
      outcome: 'caught',
      reply_uci: null,
      next_prompt: null,
      timer_remaining_ms: null,
      better_move: BETTER_MOVE_TASK,
    });
  const GRADED_GOOD: BetterMoveResponse = {
    tier: 'good',
    points_awarded: 2,
    window_points: 5,
    session_points: 5,
  };

  beforeEach(() => {
    vi.useFakeTimers();
    composeOrResumeSession.mockImplementation(async () => TWO_WINDOW_SESSION);
    startWindow.mockImplementation(async () => windowStart());
    answer.mockImplementation(async () => CAUGHT());
    submitBetterMove.mockImplementation(async () => GRADED_GOOD);
  });
  afterEach(() => {
    vi.useRealTimers();
  });

  /** Catches the blunder and waits out the feedback so the better-move board is up. */
  async function reachBetterMove(): Promise<void> {
    await reachFirstPrompt();
    fireEvent.click(screen.getByTestId('blunder-check-btn-blunder'));
    await advance(0);
    await advance(FEEDBACK_DISPLAY_MS);
  }

  /** Plays a move on the better-move board the way the board reports it. */
  async function playBoardMove(from: string, to: string): Promise<void> {
    await act(async () => {
      boardDrop.current?.(from, to);
    });
  }

  it('a caught blunder opens the pre-blunder board with the "Good call" prompt and starts the anchor search', async () => {
    await reachBetterMove();

    expect(screen.getByTestId('blunder-check-better-move-prompt').textContent).toBe(
      'Good call! +3 Now find a better move.',
    );
    expect(boardFen()).toBe(PRE_BLUNDER_FEN);
    // The move that led here keeps its squares lit (the caught blunder was never played).
    expect(screen.getByTestId('board-mock').getAttribute('data-last-move')).toBe('e7e5');
    expect(engine.startGrading).toHaveBeenCalledWith(PRE_BLUNDER_FEN, KEY_UCI);
    // The header still shows the server's points for the caught blunder, in the pot.
    expect(screen.getByTestId('blunder-check-pot-amount').textContent).toBe('+3');
    expect(screen.getByTestId('blunder-check-points').textContent).toBe('0 pts');
    // Its badge landed there during the feedback, with the coin.
    expect(playSound).toHaveBeenCalledWith('pot-gain');
  });

  it('the key move posts at once as good, shows +2 with the full-score sound, then the solution opens', async () => {
    await reachBetterMove();

    await playBoardMove('d2', 'd4');
    await advance(0);

    expect(engine.gradeMove).not.toHaveBeenCalled();
    expect(submitBetterMove).toHaveBeenCalledTimes(1);
    expect(submitBetterMove).toHaveBeenCalledWith(7, 0, { played_uci: KEY_UCI, client_tier: 'good' });
    expect(screen.getByTestId('blunder-check-points-flash').textContent).toBe('+2');
    expect(playSound).toHaveBeenCalledWith('score-full');
    // The server's totals replace the client's: the +2 lands in the pot, nothing is banked yet.
    await advance(1);
    expect(screen.getByTestId('blunder-check-pot-amount').textContent).toBe('+5');
    expect(screen.getByTestId('blunder-check-points').textContent).toBe('0 pts');

    await advance(FEEDBACK_DISPLAY_MS);
    await advance(50);

    expect(getSolution).toHaveBeenCalledWith(7, 0);
    expect(screen.getByTestId('blunder-check-solution-heading').textContent).toBe('Blunder caught');
    // The solution keeps the pot up, so the user sees what the window was worth.
    expect(screen.getByTestId('blunder-check-pot').getAttribute('data-pot-state')).toBe('open');
    expect(screen.getByTestId('blunder-check-pot-amount').textContent).toBe('+5');
    expect(screen.getByTestId('blunder-check-points').textContent).toBe('0 pts');
    expect(screen.getByTestId('btn-train-analyze')).not.toBeNull();

    // Next banks it: three overlapping coins, and the next window starts with it in the total.
    startWindow.mockImplementation(async () => windowStart({ position: 1, session_points: 5 }));
    playSound.mockClear();
    fireEvent.click(screen.getByTestId('btn-train-next'));
    await advance(BANK_COIN_COUNT * BANK_COIN_INTERVAL_MS);
    expect(playSound.mock.calls.filter(([event]) => event === 'pot-gain')).toHaveLength(
      BANK_COIN_COUNT,
    );
    expect(startWindow).toHaveBeenLastCalledWith(7, 1);
    expect(screen.getByTestId('blunder-check-points').textContent).toBe('5 pts');
  });

  it('with motion, Next holds the solution while the pot is banked, and a second click is ignored', async () => {
    reducedMotion.current = false;
    try {
      await reachBetterMove();
      await playBoardMove('d2', 'd4');
      await advance(FEEDBACK_DISPLAY_MS);
      await advance(50);
      expect(screen.getByTestId('blunder-check-pot-amount').textContent).toBe('+5');
      startWindow.mockImplementation(async () => windowStart({ position: 1, session_points: 5 }));
      const startsBefore = startWindow.mock.calls.length;

      playSound.mockClear();
      fireEvent.click(screen.getByTestId('btn-train-next'));
      fireEvent.click(screen.getByTestId('btn-train-next'));
      await advance(50);

      // The pot badge is handed over to the total; the solution is still up. The second
      // click started no second run of coins.
      expect(playSound.mock.calls.filter(([event]) => event === 'pot-gain')).toHaveLength(1);
      expect(screen.getByTestId('blunder-check-pot').getAttribute('data-pot-state')).toBe('bank');
      expect(screen.getByTestId('blunder-check-solution-heading')).not.toBeNull();
      expect(startWindow).toHaveBeenCalledTimes(startsBefore);

      await advance(BANK_HOLD_MS);
      await advance(50);
      expect(startWindow).toHaveBeenCalledTimes(startsBefore + 1);
      expect(startWindow).toHaveBeenLastCalledWith(7, 1);
      expect(screen.getByTestId('blunder-check-points').textContent).toBe('5 pts');
    } finally {
      reducedMotion.current = true;
    }
  });

  it('the caught solution also shows the Best and Game chips, with the engine lines searched', async () => {
    await reachBetterMove();
    await playBoardMove('d2', 'd4');
    await advance(FEEDBACK_DISPLAY_MS);
    await advance(50);

    // The better move was the key, so Your and Best share one chip next to the Game chip.
    expect(screen.getByTestId('train-chip-your').getAttribute('data-roles')).toBe('your best');
    expect(screen.getByTestId('train-chip-game-san').textContent).toBe('Nf3');
    expect(engine.startGameMoveSearch).toHaveBeenCalledWith(PRE_BLUNDER_FEN, KEY_UCI);
    expect(engine.startGameMoveSearch).toHaveBeenCalledWith(PRE_BLUNDER_FEN, PROMPT_UCI);
  });

  it('Analyze deep-links to the analysis board at the blunder position', async () => {
    await reachBetterMove();
    await playBoardMove('d2', 'd4');
    await advance(FEEDBACK_DISPLAY_MS);
    await advance(50);

    fireEvent.click(screen.getByTestId('btn-train-analyze'));
    await advance(0);

    expect(screen.getByTestId('location-probe').textContent).toBe(
      buildTrainPuzzleAnalysisUrl(ANALYSIS_GAME_ID, ANALYSIS_PLY),
    );
  });

  /** Reaches the caught solution, leaves through Analyze and unmounts the tab (the route change). */
  async function analyzeAndLeave(): Promise<void> {
    await reachBetterMove();
    await playBoardMove('d2', 'd4');
    await advance(FEEDBACK_DISPLAY_MS);
    await advance(50);
    fireEvent.click(screen.getByTestId('btn-train-analyze'));
    await advance(0);
    cleanup();
  }

  it('Analyze then Back lands on the same solution, not the start screen', async () => {
    await analyzeAndLeave();
    getOpenSession.mockImplementation(async () => TWO_WINDOW_SESSION);
    const onImmersiveChange = vi.fn();

    renderTab(onImmersiveChange);

    // Restored from the first paint: no start screen, no window or solution refetch.
    expect(screen.queryByTestId('blunder-check-start-screen')).toBeNull();
    expect(screen.getByTestId('blunder-check-solution-heading').textContent).toBe('Blunder caught');
    expect(onImmersiveChange).toHaveBeenLastCalledWith(true);
    await advance(50);
    expect(screen.getByTestId('blunder-check-solution-heading').textContent).toBe('Blunder caught');
    // The restored solution still holds its pot: Next banks it.
    expect(screen.getByTestId('blunder-check-pot-amount').textContent).toBe('+5');
    expect(screen.getByTestId('blunder-check-points').textContent).toBe('0 pts');
    expect(getSolution).toHaveBeenCalledTimes(1);

    // Next still continues the session from the restored solution.
    startWindow.mockImplementation(async () => windowStart({ position: 1, session_points: 5 }));
    fireEvent.click(screen.getByTestId('btn-train-next'));
    await advance(50);
    expect(startWindow).toHaveBeenLastCalledWith(7, 1);
  });

  it('a restored solution of another session falls back to the start screen', async () => {
    await analyzeAndLeave();
    getOpenSession.mockImplementation(async () => ({ ...TWO_WINDOW_SESSION, session_id: 8 }));

    renderTab();
    await advance(50);

    expect(screen.getByTestId('blunder-check-start-screen')).not.toBeNull();
    expect(sessionStorage.getItem('blunder_check_solution_cache')).toBeNull();
  });

  it('Next drops the cached solution, so a later visit starts on the start screen', async () => {
    await reachBetterMove();
    await playBoardMove('d2', 'd4');
    await advance(FEEDBACK_DISPLAY_MS);
    await advance(50);
    fireEvent.click(screen.getByTestId('btn-train-analyze'));
    await advance(0);
    expect(sessionStorage.getItem('blunder_check_solution_cache')).not.toBeNull();

    fireEvent.click(screen.getByTestId('btn-train-next'));
    await advance(50);

    expect(sessionStorage.getItem('blunder_check_solution_cache')).toBeNull();
  });

  it('Next on the solution starts the next window', async () => {
    await reachBetterMove();
    await playBoardMove('d2', 'd4');
    await advance(FEEDBACK_DISPLAY_MS);
    await advance(50);
    startWindow.mockImplementation(async () => windowStart({ position: 1, session_points: 5 }));

    fireEvent.click(screen.getByTestId('btn-train-next'));
    await advance(50);

    expect(startWindow).toHaveBeenLastCalledWith(7, 1);
    expect(screen.getByTestId('blunder-check-window-counter').textContent).toBe('2 of 2');
  });

  it('an off-key move the server did not grade is graded by the browser engine and posts the phone tier', async () => {
    engine.gradeMove.mockImplementation(async () => ({ moveTier: 'inaccuracy' }));
    submitBetterMove.mockImplementation(async () => ({
      tier: 'inaccuracy',
      points_awarded: 1,
      window_points: 4,
      session_points: 4,
    }));
    await reachBetterMove();

    await playBoardMove('g1', 'f3');
    await advance(0);

    expect(engine.gradeMove).toHaveBeenCalledWith(PRE_BLUNDER_FEN, 'g1f3');
    expect(submitBetterMove).toHaveBeenCalledWith(7, 0, {
      played_uci: 'g1f3',
      client_tier: 'inaccuracy',
    });
    expect(screen.getByTestId('blunder-check-points-flash').textContent).toBe('+1');
    expect(playSound).toHaveBeenCalledWith('score-partial');
  });

  it('a move the server graded itself posts its server tier without the engine', async () => {
    answer.mockImplementation(async () => ({
      ...CAUGHT(),
      better_move: {
        ...BETTER_MOVE_TASK,
        server_graded_moves: [{ uci: 'g1f3', tier: 'wrong' as const }],
      },
    }));
    submitBetterMove.mockImplementation(async () => ({
      tier: 'wrong',
      points_awarded: 0,
      window_points: 3,
      session_points: 3,
    }));
    await reachBetterMove();

    await playBoardMove('g1', 'f3');
    await advance(0);

    expect(engine.gradeMove).not.toHaveBeenCalled();
    expect(submitBetterMove).toHaveBeenCalledWith(7, 0, { played_uci: 'g1f3', client_tier: 'wrong' });
    expect(screen.getByTestId('blunder-check-points-flash').textContent).toBe('+0');
    expect(playSound).toHaveBeenCalledWith('game-loss');
  });

  it('an illegal drop is refused and posts nothing', async () => {
    await reachBetterMove();

    await playBoardMove('d2', 'd5');
    await advance(0);

    expect(submitBetterMove).not.toHaveBeenCalled();
    expect(screen.getByTestId('blunder-check-better-move-prompt')).not.toBeNull();
  });

  it('a grading failure shows the retry copy, and Retry re-grades the same move', async () => {
    engine.gradeMove.mockImplementationOnce(async () => {
      throw new Error('Grading timed out');
    });
    engine.gradeMove.mockImplementation(async () => ({ moveTier: 'good' }));
    await reachBetterMove();

    await playBoardMove('g1', 'f3');
    await advance(0);

    expect(screen.getByTestId('blunder-check-grade-error').textContent).toContain(
      "Couldn't check your move.",
    );
    expect(submitBetterMove).not.toHaveBeenCalled();

    fireEvent.click(screen.getByTestId('blunder-check-btn-retry-grade'));
    await advance(0);
    await advance(0);

    expect(engine.restartEngine).not.toHaveBeenCalled();
    expect(engine.gradeMove).toHaveBeenCalledTimes(2);
    expect(submitBetterMove).toHaveBeenCalledWith(7, 0, { played_uci: 'g1f3', client_tier: 'good' });
  });

  it('Retry restarts a dead engine first', async () => {
    engine.hasError = true;
    engine.gradeMove.mockImplementationOnce(async () => {
      throw new Error('Grading engine failed to load');
    });
    await reachBetterMove();
    await playBoardMove('g1', 'f3');
    await advance(0);

    fireEvent.click(screen.getByTestId('blunder-check-btn-retry-grade'));
    await advance(0);

    expect(engine.restartEngine).toHaveBeenCalledTimes(1);
  });

  it('a failed solution load keeps the screen with a Retry', async () => {
    getSolution.mockImplementationOnce(async () => {
      throw httpError(HTTP_SERVER_ERROR);
    });
    await reachBetterMove();
    await playBoardMove('d2', 'd4');
    await advance(FEEDBACK_DISPLAY_MS);
    await advance(50);

    expect(screen.getByTestId('blunder-check-solution-error').textContent).toContain(
      'Failed to load the solution.',
    );

    fireEvent.click(screen.getByTestId('blunder-check-btn-retry-solution'));
    await advance(50);

    expect(getSolution).toHaveBeenCalledTimes(2);
    expect(screen.getByTestId('blunder-check-solution-heading').textContent).toBe('Blunder caught');
  });
});

describe('session end screen (D-14)', () => {
  const RESULT: SessionResultResponse = {
    session_id: 7,
    session_points: 7,
    points_possible: 9,
    score_pct: 77,
    windows: [
      { position: 0, outcome: 'caught', points_scored: 4, points_possible: 4 },
      { position: 1, outcome: 'missed', points_scored: 3, points_possible: 5 },
    ],
  };

  beforeEach(() => {
    vi.useFakeTimers();
    composeOrResumeSession.mockImplementation(async () => TWO_WINDOW_SESSION);
    startWindow.mockImplementation(async (_sessionId, position) => windowStart({ position }));
    answer.mockImplementation(async () =>
      gradedAnswer({
        result: 'caught',
        points_awarded: 3,
        window_ended: true,
        outcome: 'caught',
        reply_uci: null,
        next_prompt: null,
        timer_remaining_ms: null,
      }),
    );
  });
  afterEach(() => {
    vi.useRealTimers();
  });

  /** Plays one window to its outcome panel and clicks Next. */
  async function finishWindowWithBlunderCall(): Promise<void> {
    await advance(LEAD_IN_START_DELAY_MS);
    for (let ply = 0; ply < LEAD_IN.length; ply += 1) {
      await advance(LEAD_IN_PLY_INTERVAL_MS);
    }
    fireEvent.click(screen.getByTestId('blunder-check-btn-blunder'));
    await advance(0);
    await advance(FEEDBACK_DISPLAY_MS);
    // The solution loads, then Next.
    await advance(50);
    fireEvent.click(screen.getByTestId('btn-train-next'));
    await advance(50);
  }

  /** Starts the session and plays both windows, leaving the tab at the finish call. */
  async function playTwoWindows(): Promise<void> {
    renderTab();
    await advance(50);
    fireEvent.click(screen.getByTestId('blunder-check-btn-start'));
    await advance(50);
    await finishWindowWithBlunderCall();
    await finishWindowWithBlunderCall();
  }

  it('shows the server points and Score % after the last window', async () => {
    finishSession.mockImplementation(async () => RESULT);
    await playTwoWindows();

    expect(finishSession).toHaveBeenCalledTimes(1);
    expect(finishSession).toHaveBeenCalledWith(7);
    expect(screen.getByTestId('blunder-check-end-screen')).not.toBeNull();
    expect(screen.getByTestId('train-score-percentage').textContent).toBe('77%');
    // The Train score screen's result sound for the band (confetti is off: reduced motion).
    expect(playSound).toHaveBeenCalledWith('game-win'); // 77% is the green band
    expect(screen.getByTestId('train-score-total').textContent).toBe('Points: 7/9');
    expect(screen.getByTestId('train-score-bubble').textContent).toContain('Strong session.');
    // No schedule, leaderboard or reminders for blunder check yet (Phase 251).
    expect(screen.queryByTestId('train-score-next-session')).toBeNull();
    // A summary by outcome, not one line per sequence; outcomes with no sequence are left out.
    expect(screen.getByTestId('blunder-check-end-sequences').textContent).toBe('Sequences: 2');
    expect(screen.getByTestId('blunder-check-end-blunders').textContent).toBe(
      'Caught: 1 · Missed: 1',
    );
    expect(screen.queryByTestId('blunder-check-end-clean')).toBeNull();
  });

  it('a failed finish shows the retry copy, and a successful retry shows the end screen', async () => {
    finishSession.mockImplementationOnce(async () => {
      throw httpError(HTTP_SERVER_ERROR);
    });
    finishSession.mockImplementation(async () => RESULT);
    await playTwoWindows();

    expect(screen.getByTestId('blunder-check-finish-error-copy').textContent).toBe(
      'Failed to finish the session. Something went wrong. Please try again in a moment.',
    );
    expect(screen.queryByTestId('blunder-check-end-screen')).toBeNull();

    fireEvent.click(screen.getByTestId('blunder-check-btn-retry'));
    await advance(50);

    expect(finishSession).toHaveBeenCalledTimes(2);
    expect(screen.getByTestId('blunder-check-end-screen')).not.toBeNull();
  });

  it('Done returns to the start screen and the page leaves immersive mode', async () => {
    finishSession.mockImplementation(async () => RESULT);
    const onImmersiveChange = vi.fn();
    renderTab(onImmersiveChange);
    await advance(50);
    fireEvent.click(screen.getByTestId('blunder-check-btn-start'));
    await advance(50);
    await finishWindowWithBlunderCall();
    await finishWindowWithBlunderCall();
    expect(screen.getByTestId('blunder-check-end-screen')).not.toBeNull();
    expect(onImmersiveChange).toHaveBeenLastCalledWith(false);

    fireEvent.click(screen.getByTestId('btn-train-done'));
    await advance(50);

    expect(screen.getByTestId('blunder-check-start-screen')).not.toBeNull();
    expect(screen.queryByTestId('blunder-check-end-screen')).toBeNull();
  });
});

describe('D-19: no Umami event for blunder check', () => {
  // process.cwd() is frontend/ under `npm test`; plain strings because jsdom's URL is not
  // accepted by node:fs.
  const SRC = join(process.cwd(), 'src');
  // Built from parts so this file does not contain the strings it forbids elsewhere.
  const ANALYTICS_IMPORT = ['@/lib', 'analytics'].join('/');
  const UMAMI_ATTRIBUTE = ['data-umami', 'event'].join('-');

  function sourceFiles(dir: string): string[] {
    return readdirSync(dir, { withFileTypes: true }).flatMap((entry) => {
      const child = join(dir, entry.name);
      return entry.isDirectory() ? sourceFiles(child) : [child];
    });
  }

  it('no blunder-check source imports the analytics module or sets an Umami attribute', () => {
    const files = [
      ...sourceFiles(join(SRC, 'components/train/blunder-check')),
      join(SRC, 'hooks/useBlunderCheckSession.ts'),
      join(SRC, 'hooks/useMoveTimer.ts'),
      join(SRC, 'lib/blunderCheckDrill.ts'),
    ];
    expect(files.length).toBeGreaterThan(3);
    for (const file of files) {
      const source = readFileSync(file, 'utf8');
      expect(source, file).not.toContain(ANALYTICS_IMPORT);
      expect(source, file).not.toContain(UMAMI_ATTRIBUTE);
    }
  });
});
