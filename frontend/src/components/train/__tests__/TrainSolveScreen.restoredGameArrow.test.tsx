// @vitest-environment jsdom
/**
 * Regression: a RESTORED reveal (Analyze -> back) whose reveal query resolves
 * synchronously from the TanStack cache must still draw the thin white
 * played-in-game arrow.
 *
 * The bug: TrainReveal reports `played_in_game_move_uci` up via an effect,
 * and TrainSolveScreen's puzzle-reset effect used to null the same state.
 * With a warm cache both effects run in the SAME commit; React runs child
 * effects first, so the parent's null won, the UCI never changed again, and
 * the arrow was silently dropped while the "Played in game" legend card (which
 * reads the query directly) still rendered. Cold cache (fetch resolves after
 * the reset effect) never showed the bug, hence "sometimes".
 *
 * The harness mounts TrainSolveScreen only once the session is loaded, exactly
 * like Train.tsx's `restoredActive` gate — mounting earlier changes the reveal
 * query key (null sessionId) and hides the race.
 */
import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router';
import { useEffect } from 'react';
import type { ReactElement } from 'react';
import { TrainSolveScreen } from '@/components/train/TrainSolveScreen';
import { TooltipProvider } from '@/components/ui/tooltip';
import { NEXT_MOVE_ARROW } from '@/lib/theme';
import { useTrainSession } from '@/hooks/useTrainSession';
import { useTrainGradingEngine } from '@/hooks/useTrainGradingEngine';
import type { CachedTrainReveal } from '@/lib/trainRevealCache';
import type { PuzzleRevealResponse, TrainPuzzle } from '@/types/train';

// ─── jsdom shims (same precedent as TrainSolveScreen.test.tsx) ─────────────

class WorkerStub {
  postMessage(): void {}
  terminate(): void {}
  addEventListener(): void {}
  removeEventListener(): void {}
  onmessage = null;
  onerror = null;
}
(globalThis as unknown as { Worker: unknown }).Worker = WorkerStub;
class ResizeObserverStub {
  observe(): void {}
  unobserve(): void {}
  disconnect(): void {}
}
(globalThis as unknown as { ResizeObserver: typeof ResizeObserverStub }).ResizeObserver =
  ResizeObserverStub;
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: vi.fn().mockImplementation((query: string) => ({
    matches: true,
    media: query,
    onchange: null,
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    addListener: vi.fn(),
    removeListener: vi.fn(),
    dispatchEvent: vi.fn(),
  })),
});

// ─── Fixtures ───────────────────────────────────────────────────────────────

const START_FEN = 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1';
const SESSION_ID = 1;
const PUZZLE_POSITION = 1;
// The game move ('d2d4') is deliberately DISTINCT from the played/best move
// ('e2e4') so the white arrow is a standalone entry, not a coincidence-merge.
const REVEAL: PuzzleRevealResponse = {
  game_id: 100,
  ply: 20,
  fen: START_FEN,
  played_in_game_san: 'd4',
  played_in_game_move_uci: 'd2d4',
  puzzle_type: 'sharp',
  source: 'sr_item',
  has_tactic_lines: false,
};

vi.mock('@/api/client', async () => {
  const actual = await vi.importActual<typeof import('@/api/client')>('@/api/client');
  return {
    ...actual,
    trainApi: {
      ...actual.trainApi,
      composeOrResumeSession: vi.fn(async () => ({
        session_id: 1,
        session_date: '2026-07-25',
        expires_on: '2026-07-26',
        puzzle_count: 5,
        requested_count: 5,
        solved_count: 0,
        blob_pending_count: 0,
        puzzles: [],
        solved_results: [],
        is_warmup: false,
      })),
      solvePuzzle: vi.fn(),
      // Same payload as the pre-seeded cache entry below, so the cold-cache
      // control and the warm-cache regression differ ONLY in timing.
      revealPuzzle: vi.fn(async () => ({
        game_id: 100,
        ply: 20,
        fen: 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1',
        played_in_game_san: 'd4',
        played_in_game_move_uci: 'd2d4',
        puzzle_type: 'sharp',
        source: 'sr_item',
        has_tactic_lines: false,
      })),
    },
    libraryApi: {
      ...actual.libraryApi,
      getGame: vi.fn(async () => {
        throw new Error('not under test');
      }),
      getTacticLines: vi.fn(async () => {
        throw new Error('not under test');
      }),
    },
  };
});

vi.mock('@/components/board/ChessBoard', () => ({
  ChessBoard: ({ arrows }: { arrows?: { color: string }[] }) => (
    <div
      data-testid="chessboard"
      data-arrow-colors={(arrows ?? []).map((a) => a.color).join(',')}
    />
  ),
}));

// A restored puzzle never grades on mount; only the reveal-time game-move
// search runs. Module-level singleton so the hook's identity is stable.
vi.mock('@/hooks/useTrainGradingEngine', () => {
  const line = { moves: ['d2d4'], evalCp: 10, evalMate: null };
  const engine = {
    status: 'ready',
    gradeMove: vi.fn(),
    abortGrading: vi.fn(),
    startGrading: vi.fn(),
    startGameMoveSearch: vi.fn(async () => line),
    startRevealSearch: vi.fn(async () => line),
  };
  return { useTrainGradingEngine: () => engine };
});

const puzzle: TrainPuzzle = {
  position: PUZZLE_POSITION,
  game_id: 100,
  ply: 20,
  fen: START_FEN,
  side_to_move: 'white',
  last_move_uci: 'd7d5',
};

const restored = {
  sessionId: SESSION_ID,
  puzzle,
  verdict: {
    correct_guess: true,
    correct_move: true,
    move_quality: 'good',
    puzzle_type: 'sharp',
    item_status: 'active',
    streak: 1,
    due_date: '2026-07-28',
    session_complete: false,
  },
  guess: 'critical',
  playedMoveUci: 'e2e4',
  gradeResult: {
    moveTier: 'good',
    bestMoveUci: 'e2e4',
    esBefore: 0.5,
    esAfter: 0.5,
    bestLine: { moves: ['e2e4'], evalCp: 19, evalMate: null },
    playedLine: { moves: ['e2e4'], evalCp: 19, evalMate: null },
    lines: [],
  },
} as unknown as CachedTrainReveal;

function Harness(): ReactElement {
  const trainSession = useTrainSession();
  const gradingEngine = useTrainGradingEngine({ enabled: true });
  const { startSession } = trainSession;
  useEffect(() => {
    startSession();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
  // Mirrors Train.tsx's `restoredActive` gate: the restored screen mounts only
  // once the session is loaded, so the reveal query key is complete on the
  // very first render.
  if (trainSession.session === null) return <div data-testid="session-pending" />;
  return (
    <TrainSolveScreen
      puzzle={puzzle}
      trainSession={trainSession}
      gradingEngine={gradingEngine}
      restoredSolve={restored}
      onNext={() => {}}
    />
  );
}

async function renderRestored(opts: { warmCache: boolean }): Promise<() => string> {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  if (opts.warmCache) {
    queryClient.setQueryData(['train-reveal', SESSION_ID, PUZZLE_POSITION], REVEAL);
  }
  render(
    <MemoryRouter>
      <QueryClientProvider client={queryClient}>
        <TooltipProvider>
          <Harness />
        </TooltipProvider>
      </QueryClientProvider>
    </MemoryRouter>,
  );
  await waitFor(() => expect(screen.getByTestId('train-line-box-game-move')).not.toBeNull());
  return () => screen.getByTestId('chessboard').getAttribute('data-arrow-colors') ?? '';
}

describe('restored reveal: played-in-game arrow', () => {
  afterEach(() => cleanup());

  it('cold cache (control): the white game-move arrow is drawn once the reveal fetch lands', async () => {
    const arrowColors = await renderRestored({ warmCache: false });
    await waitFor(() => expect(arrowColors()).toContain(NEXT_MOVE_ARROW));
  });

  it('warm cache (regression): the white game-move arrow survives the puzzle-reset effect', async () => {
    const arrowColors = await renderRestored({ warmCache: true });
    await waitFor(() => expect(arrowColors()).toContain(NEXT_MOVE_ARROW));
  });
});
