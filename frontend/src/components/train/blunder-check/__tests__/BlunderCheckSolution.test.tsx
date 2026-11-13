// @vitest-environment jsdom
/**
 * BlunderCheckSolution: the solution screen of one ended window (Phase 249, D-14).
 * The Best / Game / Move line chips with sequential engine searches and line exploration
 * (task 2), then the own / foreign copy and footers and the false-alarm and herring views
 * (task 3). The board and the Stockfish worker are mocked.
 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { act, cleanup, fireEvent, render, screen, within } from '@testing-library/react';
import { MemoryRouter, useLocation } from 'react-router';
import { TooltipProvider } from '@/components/ui/tooltip';
import { buildTrainPuzzleAnalysisUrl } from '@/lib/analysisUrl';
import { playSound } from '@/lib/sounds';
import { applyUcis } from '@/lib/blunderCheckDrill';
import type { DrillProgress } from '@/lib/blunderCheckDrill';
import { pickPuzzleHost } from '@/lib/trainBotCopy';
import { formatDateWithYear } from '@/lib/utils';
import type { TrainEngineLine } from '@/hooks/useTrainGradingEngine';
import type { GameFlawCard } from '@/types/library';
import type {
  BlunderSolution,
  FalseAlarmSolution,
  GameInfo,
  HerringSolution,
  WindowSolution,
} from '@/types/blunderCheck';

// The reveal tree's own engine: a static, ready engine (jsdom has no Worker).
const enginePv = vi.hoisted(() => ({
  lines: [] as { multipv: number; depth: number; moves: string[]; evalCp: number; evalMate: null }[],
}));
vi.mock('@/hooks/useStockfishEngine', () => ({
  useStockfishEngine: (options: { fen: string | null; enabled: boolean }) => ({
    evalCp: null,
    evalMate: null,
    pvLines: enginePv.lines,
    depth: 0,
    isAnalyzing: false,
    isReady: true,
    currentFen: options.enabled ? options.fen : null,
  }),
}));

// The reveal action bar renders under the board from `sm` up (phones publish it to the fixed
// bottom bar, which these tests do not mount); jsdom has no matchMedia.
vi.mock('@/hooks/useIsDesktop', () => ({ useIsDesktop: () => true, useIsSmUp: () => true }));

vi.mock('@/lib/sounds', () => ({ playSound: vi.fn(), unlockAudio: vi.fn() }));

// The own-game footer's library card query, scripted per test.
const libraryGame = vi.hoisted(() => ({
  useLibraryGame: vi.fn(),
}));
vi.mock('@/hooks/useLibrary', () => ({ useLibraryGame: libraryGame.useLibraryGame }));

// jsdom has no scrollIntoView; the move list scrolls the active token into view.
if (typeof Element.prototype.scrollIntoView !== 'function') {
  Element.prototype.scrollIntoView = vi.fn();
}

vi.mock('@/components/board/ChessBoard', () => ({
  ChessBoard: ({
    position,
    arrows,
    squareMarkers,
    flipped,
  }: {
    position: string;
    arrows?: { startSquare: string; endSquare: string; opacity?: number }[];
    squareMarkers?: {
      square: string;
      best?: boolean;
      good?: boolean;
      severity?: string;
      opacity?: number;
    }[];
    flipped?: boolean;
  }) => {
    // An arrow or badge is lit unless the chip focus dimmed it (opacity below one half).
    const lit = (item: { opacity?: number }): boolean => (item.opacity ?? 1) >= 0.5;
    const uciOf = (a: { startSquare: string; endSquare: string }): string =>
      `${a.startSquare}${a.endSquare}`;
    const badgeOf = (m: { square: string; best?: boolean; good?: boolean; severity?: string }) =>
      `${m.square}:${m.best ? 'best' : m.good ? 'good' : (m.severity ?? '')}`;
    const drawn = arrows ?? [];
    const badges = squareMarkers ?? [];
    return (
      <div
        data-testid="board-mock"
        data-position={position}
        data-flipped={flipped ? 'true' : 'false'}
        data-arrows={[...new Set(drawn.map(uciOf))].join(',')}
        data-lit-arrows={[...new Set(drawn.filter(lit).map(uciOf))].join(',')}
        data-markers={badges.map(badgeOf).join(',')}
        data-lit-markers={badges.filter(lit).map(badgeOf).join(',')}
      />
    );
  },
}));

import { BlunderCheckSolution } from '@/components/train/blunder-check/BlunderCheckSolution';

/** 1. e4 e5 played, white to move: d4 is the key, Nf3 the played blunder. */
const FEN = 'rnbqkbnr/pppp1ppp/8/4p3/4P3/8/PPPP1PPP/RNBQKBNR w KQkq - 0 2';
const KEY = 'd2d4';
const BLUNDER = 'g1f3';
const OTHER_BETTER = 'b1c3';

function blunderSolution(overrides: Partial<BlunderSolution> = {}): BlunderSolution {
  return {
    kind: 'blunder',
    outcome: 'caught',
    is_own: true,
    window_case: 'allowed',
    game_id: 55,
    analysis_ply: 4,
    fen: FEN,
    blunder_uci: BLUNDER,
    key_uci: KEY,
    better_move_uci: OTHER_BETTER,
    better_move_tier: 'good',
    server_graded_moves: [],
    game_info: null,
    window_points: 5,
    safe_points: 0,
    blunder_points: 3,
    better_move_points: 2,
    ...overrides,
  };
}

function lineOf(first: string): TrainEngineLine {
  return { moves: [first], evalCp: 20, evalMate: null };
}

/** A search the test settles by hand, so the order of the searches is observable. */
interface Deferred {
  uci: string;
  resolve: (line: TrainEngineLine) => void;
}

function scriptedEngine() {
  const searches: Deferred[] = [];
  const startGameMoveSearch = vi.fn(
    (_fen: string, uci: string) =>
      new Promise<TrainEngineLine>((resolve) => {
        searches.push({ uci, resolve });
      }),
  );
  return { searches, startGameMoveSearch };
}

const PROGRESS: DrillProgress = {
  position: 0,
  windowCount: 6,
  banked: 0,
  pot: null,
  potEvent: null,
};
const PERSONA = pickPuzzleHost(true, () => 0);

function renderSolution(
  solution: WindowSolution,
  engine: ReturnType<typeof scriptedEngine>,
  props: { onNext?: () => void } = {},
) {
  return render(
    <MemoryRouter>
      <TooltipProvider>
      <BlunderCheckSolution
        solution={solution}
        orientation="white"
        progress={PROGRESS}
        persona={PERSONA}
        onNext={props.onNext ?? vi.fn()}
        engine={{ startGameMoveSearch: engine.startGameMoveSearch }}
        onAnalyze={vi.fn()}
        restoredTree={null}
      />
      <LocationProbe />
    </TooltipProvider>
      </MemoryRouter>,
  );
}

/** Renders the router's current location so a test can assert where Analyze navigated. */
function LocationProbe() {
  const location = useLocation();
  return <div data-testid="location-probe">{`${location.pathname}${location.search}`}</div>;
}

async function settle(): Promise<void> {
  await act(async () => {
    await Promise.resolve();
  });
}

function boardFen(): string {
  return screen.getByTestId('board-mock').getAttribute('data-position') ?? '';
}

beforeEach(() => {
  libraryGame.useLibraryGame.mockReset();
  libraryGame.useLibraryGame.mockReturnValue({ data: undefined, isError: false });
});

afterEach(() => {
  cleanup();
});

describe('line chips (D-14)', () => {
  let engine: ReturnType<typeof scriptedEngine>;
  beforeEach(() => {
    engine = scriptedEngine();
  });

  it('a caught blunder shows the Your, Best and Game chips with their moves', () => {
    renderSolution(blunderSolution(), engine);

    expect(screen.getByTestId('train-chip-your')).not.toBeNull();
    expect(screen.getByTestId('train-chip-best')).not.toBeNull();
    expect(screen.getByTestId('train-chip-game')).not.toBeNull();
    expect(screen.getByTestId('train-chip-your-san').textContent).toBe('Nc3');
    expect(screen.getByTestId('train-chip-best-san').textContent).toBe('d4');
    expect(screen.getByTestId('train-chip-game-san').textContent).toBe('Nf3');
  });

  it('a better move equal to the key shares one chip with Best', () => {
    renderSolution(blunderSolution({ better_move_uci: KEY }), engine);

    expect(screen.getByTestId('train-chip-your').getAttribute('data-roles')).toBe('your best');
    expect(screen.queryByTestId('train-chip-best')).toBeNull();
  });

  it('a missed blunder shows Best and Game chips and no Your chip', () => {
    renderSolution(blunderSolution({ outcome: 'missed', better_move_uci: null }), engine);

    expect(screen.getByTestId('train-chip-best')).not.toBeNull();
    expect(screen.getByTestId('train-chip-game')).not.toBeNull();
    expect(screen.queryByTestId('train-chip-your')).toBeNull();
  });

  it('runs the line searches one after another, never in parallel on the shared engine', async () => {
    renderSolution(blunderSolution(), engine);
    await settle();

    // Only the first search (the key) has started.
    expect(engine.startGameMoveSearch).toHaveBeenCalledTimes(1);
    expect(engine.startGameMoveSearch).toHaveBeenLastCalledWith(FEN, KEY);

    await act(async () => {
      engine.searches[0]?.resolve(lineOf(KEY));
    });
    expect(engine.startGameMoveSearch).toHaveBeenCalledTimes(2);
    expect(engine.startGameMoveSearch).toHaveBeenLastCalledWith(FEN, OTHER_BETTER);

    await act(async () => {
      engine.searches[1]?.resolve(lineOf(OTHER_BETTER));
    });
    expect(engine.startGameMoveSearch).toHaveBeenCalledTimes(3);
    expect(engine.startGameMoveSearch).toHaveBeenLastCalledWith(FEN, BLUNDER);
  });

  it('a failed search marks its chip failed and the next search still runs', async () => {
    const failing = vi
      .fn()
      .mockRejectedValueOnce(new Error('Reveal search timed out'))
      .mockImplementation(async (_fen: string, uci: string) => lineOf(uci));
    render(
      <MemoryRouter>
      <TooltipProvider>
        <BlunderCheckSolution
          solution={blunderSolution()}
          orientation="white"
          progress={PROGRESS}
          persona={PERSONA}
          onNext={vi.fn()}
          engine={{ startGameMoveSearch: failing }}
          onAnalyze={vi.fn()}
          restoredTree={null}
        />
      </TooltipProvider>
      </MemoryRouter>,
    );
    await settle();
    await settle();
    await settle();

    expect(failing).toHaveBeenCalledTimes(3);
    expect(screen.getByTestId('train-chip-best').getAttribute('data-line-status')).toBe('failed');
    expect(screen.getByTestId('train-chip-game').getAttribute('data-line-status')).toBeNull();
  });

  it('selecting a chip and a move in the list moves the board along that line', async () => {
    renderSolution(blunderSolution({ better_move_uci: KEY }), engine);
    await settle();
    expect(boardFen()).toBe(FEN);

    fireEvent.click(screen.getByTestId('train-chip-game'));
    const tokens = screen
      .getByTestId('train-move-tree')
      .querySelectorAll('[data-testid^="variation-node-"]');
    expect(tokens.length).toBeGreaterThan(0);
    fireEvent.click(tokens[0] as Element);

    expect(boardFen()).toBe(applyUcis(FEN, [BLUNDER]));
  });

  it('a stepped line draws the engine arrow and the move-quality badge, like the puzzle reveal', async () => {
    // Black's reply after the blunder, as the reveal engine's top line.
    const ENGINE_REPLY = 'b8c6';
    enginePv.lines = [{ multipv: 1, depth: 20, moves: [ENGINE_REPLY], evalCp: -300, evalMate: null }];
    try {
      renderSolution(blunderSolution(), engine);
      await settle();
      // The reveal engine only starts once every line search has landed.
      for (let i = 0; i < 3; i++) {
        const search = engine.searches[i];
        if (search === undefined) throw new Error('missing line search');
        await act(async () => search.resolve(lineOf(search.uci)));
      }
      fireEvent.click(screen.getByTestId('train-chip-game'));
      const tokens = screen
        .getByTestId('train-move-tree')
        .querySelectorAll('[data-testid^="variation-node-"]');
      fireEvent.click(tokens[0] as Element);

      const board = screen.getByTestId('board-mock');
      expect(board.getAttribute('data-position')).toBe(applyUcis(FEN, [BLUNDER]));
      expect(board.getAttribute('data-arrows')?.split(',')).toContain(ENGINE_REPLY);
      expect(board.getAttribute('data-markers')?.split(',')).toContain(
        `${BLUNDER.slice(2, 4)}:blunder`,
      );
    } finally {
      enginePv.lines = [];
    }
  });

  it('the lit chip draws its arrow at the blunder position', async () => {
    renderSolution(blunderSolution(), engine);
    await settle();

    // The Your chip is lit by default; the other arrows stay on the board, translucent.
    const board = screen.getByTestId('board-mock');
    expect(board.getAttribute('data-lit-arrows')).toBe(OTHER_BETTER);
    expect(board.getAttribute('data-arrows')?.split(',').sort()).toEqual(
      [OTHER_BETTER, KEY, BLUNDER].sort(),
    );
    fireEvent.click(screen.getByTestId('train-chip-game'));
    expect(screen.getByTestId('board-mock').getAttribute('data-lit-arrows')).toBe(BLUNDER);
  });

  it('every solution arrow carries its move-quality badge, only the lit chip opaque', async () => {
    renderSolution(blunderSolution(), engine);
    await settle();

    const board = screen.getByTestId('board-mock');
    expect(board.getAttribute('data-markers')?.split(',').sort()).toEqual(
      [
        `${OTHER_BETTER.slice(2, 4)}:good`,
        `${KEY.slice(2, 4)}:best`,
        `${BLUNDER.slice(2, 4)}:blunder`,
      ].sort(),
    );
    expect(board.getAttribute('data-lit-markers')).toBe(`${OTHER_BETTER.slice(2, 4)}:good`);
  });

  it('a missed blunder also draws the moves that were also good, translucent with a good badge', async () => {
    renderSolution(
      blunderSolution({
        outcome: 'missed',
        better_move_uci: null,
        better_move_tier: null,
        server_graded_moves: [
          { uci: KEY, tier: 'good' },
          { uci: OTHER_BETTER, tier: 'good' },
        ],
      }),
      engine,
    );
    await settle();

    const board = screen.getByTestId('board-mock');
    // Game is the lit chip: the user first inspects the blunder that was played.
    expect(board.getAttribute('data-lit-arrows')).toBe(BLUNDER);
    expect(board.getAttribute('data-arrows')?.split(',')).toContain(OTHER_BETTER);
    expect(board.getAttribute('data-markers')?.split(',')).toContain(
      `${OTHER_BETTER.slice(2, 4)}:good`,
    );
    expect(board.getAttribute('data-lit-markers')).toBe(`${BLUNDER.slice(2, 4)}:blunder`);
  });
});

describe('own copy and actions', () => {
  it('names the blunder and the best move in SAN, and never a reply it "loses to"', () => {
    renderSolution(blunderSolution(), scriptedEngine());

    expect(screen.getByTestId('blunder-check-solution-heading').textContent).toBe('Blunder caught');
    // The better move is named apart from the game's blunder, with its own quality, and
    // every scored part carries its point badge (Phase 249 UAT).
    expect(screen.getByTestId('blunder-check-solution-summary').textContent).toBe(
      'Nf3 was a blunder. You called it +3 and played a good move, Nc3 +2. Best was d4.',
    );
    expect(screen.getByTestId('blunder-check-pill-call').textContent).toBe('+3');
    expect(screen.getByTestId('blunder-check-pill-move').textContent).toBe('+2');
    expect(within(screen.getByTestId('blunder-check-solution')).getByTestId('board-mock')).not.toBeNull();
  });
});

// ─── Task 3: own vs foreign copy and footer, herring and false-alarm views ──────

const OWN_GAME = {
  user_color: 'white',
  white_username: 'me',
  black_username: 'rival',
  white_rating: 1500,
  black_rating: 1620,
  time_control_bucket: 'blitz',
  time_control_str: '180+2',
  played_at: '2026-03-04T12:00:00Z',
} as unknown as GameFlawCard;

const FOREIGN_INFO: GameInfo = {
  time_control_str: '600+0',
  time_control_bucket: 'rapid',
  played_at: '2026-02-10T09:30:00Z',
  mover_rating: 1650,
};

function herringSolution(overrides: Partial<HerringSolution> = {}): HerringSolution {
  return {
    kind: 'herring',
    outcome: 'cleared',
    is_own: true,
    game_id: 77,
    analysis_ply: 6,
    fen: FEN,
    sequence_ucis: [BLUNDER, 'b8c6'],
    game_info: null,
    window_points: 3,
    ...overrides,
  };
}

function falseAlarmSolution(overrides: Partial<FalseAlarmSolution> = {}): FalseAlarmSolution {
  return {
    kind: 'false_alarm',
    outcome: 'false_alarm',
    is_own: true,
    game_id: 77,
    analysis_ply: 6,
    flagged_uci: BLUNDER,
    fen: FEN,
    key_uci: KEY,
    game_info: null,
    window_points: 0,
    ...overrides,
  };
}

function renderedText(): string {
  return document.body.textContent?.toLowerCase() ?? '';
}

describe('own blunder solution (D-14)', () => {
  it('renders the library game footer with the opponent, rating and date', () => {
    libraryGame.useLibraryGame.mockReturnValue({ data: OWN_GAME, isError: false });
    renderSolution(blunderSolution(), scriptedEngine());

    expect(libraryGame.useLibraryGame).toHaveBeenCalledWith(55);
    expect(screen.getByTestId('blunder-check-game-footer').textContent).toBe(
      `Game: Blitz 3+2 · vs rival (1620) · ${formatDateWithYear('2026-03-04T12:00:00Z')}`,
    );
  });

  it('shows the load-error copy when the game card fails to load', () => {
    libraryGame.useLibraryGame.mockReturnValue({ data: undefined, isError: true });
    renderSolution(blunderSolution(), scriptedEngine());

    expect(screen.getByTestId('blunder-check-game-error').textContent).toBe(
      'Failed to load the game. Something went wrong. Please try again in a moment.',
    );
    expect(screen.queryByTestId('blunder-check-game-footer')).toBeNull();
  });
});

describe('foreign blunder solution (D-09)', () => {
  const foreign = () => blunderSolution({ is_own: false, game_info: FOREIGN_INFO });

  it('names the move without a mover, shows the neutral line from game_info and never loads the library card', () => {
    renderSolution(foreign(), scriptedEngine());

    expect(screen.getByTestId('blunder-check-solution-summary').textContent).toBe(
      'Nf3 was a blunder. You called it +3 and played a good move, Nc3 +2. Best was d4.',
    );
    expect(screen.getByTestId('blunder-check-game-footer').textContent).toBe(
      `Game: Rapid 10+0 · player rated 1650 · ${formatDateWithYear('2026-02-10T09:30:00Z')}`,
    );
    expect(libraryGame.useLibraryGame).not.toHaveBeenCalled();
  });

  it('never claims the move was the user\'s: no "You played" and no "your move" anywhere', () => {
    renderSolution(foreign(), scriptedEngine());

    expect(renderedText()).not.toContain('you played');
    expect(renderedText()).not.toContain('your move');
  });

  it('a foreign window whose game is gone shows no footer line at all', () => {
    renderSolution(blunderSolution({ is_own: false, game_info: null }), scriptedEngine());

    expect(screen.queryByTestId('blunder-check-game-footer')).toBeNull();
  });

  it('pure-miss windows use the same missed-blunder heading as the others (D-07)', () => {
    renderSolution(
      blunderSolution({ outcome: 'missed', window_case: 'pure_miss', better_move_uci: null }),
      scriptedEngine(),
    );

    expect(screen.getByTestId('blunder-check-solution-heading').textContent).toBe('Missed blunder');
  });
});

describe('herring solution', () => {
  it('shows "All good" with the own footer and Analyze at the analysis ply', () => {
    libraryGame.useLibraryGame.mockReturnValue({ data: OWN_GAME, isError: false });
    renderSolution(herringSolution(), scriptedEngine());

    expect(screen.getByTestId('blunder-check-solution-heading').textContent).toBe('All good');
    expect(screen.getByTestId('blunder-check-solution-summary').textContent).toBe(
      'Every move in this sequence was good. Your calls earned +3.',
    );
    expect(screen.getByTestId('blunder-check-game-footer')).not.toBeNull();

    fireEvent.click(screen.getByTestId('btn-train-analyze'));
    expect(screen.getByTestId('location-probe').textContent).toBe(
      buildTrainPuzzleAnalysisUrl(77, 6),
    );
  });

  it('steps through the sequence with the controls and the move list', () => {
    renderSolution(herringSolution(), scriptedEngine());
    const position = (): string | null =>
      screen.getByTestId('board-mock').getAttribute('data-position');
    const afterFirst = applyUcis(FEN, [BLUNDER]);
    const afterSecond = applyUcis(FEN, [BLUNDER, 'b8c6']);

    // The board rests at the window's start, with nothing to step back to.
    expect(position()).toBe(FEN);
    expect(screen.getByTestId('blunder-check-sequence-list').textContent).toContain('Nf3');
    expect(screen.queryByTestId('train-line-chips')).toBeNull();

    vi.mocked(playSound).mockClear();
    fireEvent.click(screen.getByTestId('board-btn-forward'));
    expect(position()).toBe(afterFirst);
    // Each step sounds like the move the board lands on.
    expect(vi.mocked(playSound).mock.calls).toEqual([['move']]);
    fireEvent.click(screen.getByTestId('blunder-check-sequence-move-2'));
    expect(position()).toBe(afterSecond);
    fireEvent.click(screen.getByTestId('board-btn-back'));
    expect(position()).toBe(afterFirst);
    fireEvent.click(screen.getByTestId('board-btn-reset'));
    expect(position()).toBe(FEN);
  });

  it('the desktop flip button turns the board around', () => {
    renderSolution(herringSolution(), scriptedEngine());
    const board = (): HTMLElement => screen.getByTestId('board-mock');
    const before = board().getAttribute('data-flipped');
    fireEvent.click(screen.getByTestId('board-btn-flip'));
    expect(board().getAttribute('data-flipped')).not.toBe(before);
  });

  it('a foreign herring shows the neutral line and never the library card', () => {
    renderSolution(herringSolution({ is_own: false, game_info: FOREIGN_INFO }), scriptedEngine());

    expect(screen.getByTestId('blunder-check-game-footer').textContent).toContain(
      'player rated 1650',
    );
    expect(libraryGame.useLibraryGame).not.toHaveBeenCalled();
    expect(renderedText()).not.toContain('your move');
  });
});

describe('false-alarm solution (Phase 249 UAT)', () => {
  it('names the good move and opens on its Game chip, next to the Best chip', async () => {
    libraryGame.useLibraryGame.mockReturnValue({ data: OWN_GAME, isError: false });
    renderSolution(falseAlarmSolution(), scriptedEngine());
    await settle();

    expect(screen.getByTestId('blunder-check-solution-heading').textContent).toBe('False alarm');
    expect(screen.getByTestId('blunder-check-solution-summary').textContent).toBe(
      'Nf3 was a good move, not a blunder +0.',
    );
    const board = screen.getByTestId('board-mock');
    // The flagged move is the lit arrow and carries the good-move badge.
    expect(board.getAttribute('data-lit-arrows')).toBe(BLUNDER);
    expect(board.getAttribute('data-lit-markers')).toBe(`${BLUNDER.slice(2, 4)}:good`);
    expect(board.getAttribute('data-arrows')?.split(',')).toContain(KEY);
    expect(screen.getByTestId('train-line-chips')).not.toBeNull();
    expect(screen.getByTestId('blunder-check-game-footer')).not.toBeNull();
  });

  it('Analyze opens the game at the flagged move', () => {
    renderSolution(falseAlarmSolution(), scriptedEngine());

    fireEvent.click(screen.getByTestId('btn-train-analyze'));
    expect(screen.getByTestId('location-probe').textContent).toBe(
      buildTrainPuzzleAnalysisUrl(77, 6),
    );
  });

  it('with no stored best move it still shows the flagged move as the only chip', async () => {
    renderSolution(falseAlarmSolution({ key_uci: null }), scriptedEngine());
    await settle();

    expect(screen.getByTestId('board-mock').getAttribute('data-arrows')).toBe(BLUNDER);
    expect(screen.getByTestId('train-line-chips')).not.toBeNull();
  });

  it('a false alarm whose game is gone has no Analyze', () => {
    renderSolution(falseAlarmSolution({ game_id: null }), scriptedEngine());

    expect(screen.queryByTestId('btn-train-analyze')).toBeNull();
  });
});

describe('a game that no longer exists', () => {
  it('hides Analyze and the footer on a blunder solution', () => {
    renderSolution(blunderSolution({ game_id: null }), scriptedEngine());

    expect(screen.queryByTestId('btn-train-analyze')).toBeNull();
    expect(screen.queryByTestId('blunder-check-game-footer')).toBeNull();
    expect(libraryGame.useLibraryGame).not.toHaveBeenCalled();
  });

  it('hides Analyze and the footer on a herring solution', () => {
    renderSolution(herringSolution({ game_id: null }), scriptedEngine());

    expect(screen.queryByTestId('btn-train-analyze')).toBeNull();
    expect(screen.queryByTestId('blunder-check-game-footer')).toBeNull();
  });
});
