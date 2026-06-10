// @vitest-environment jsdom
/**
 * FlawCard vitest suite (Phase 112, SC-4, SC-5, SC-7, SC-8).
 *
 * Tests:
 * 1. CardHeader renders white + black usernames with ratings
 * 2. Ratings in parentheses; omitted (no empty parens) when null
 * 3. Move notation: ply=2 (white) → "2.Nxd4", ply=3 (black) → "2...c5"
 * 4. Board at size 132 with a flaw-move arrow when move_san is set
 * 5. data-testid on root article: flaw-card-{game_id}-{ply}
 * 6. Platform link testid and aria-label present
 * 7. "View game" button opens modal (flaw-game-modal appears in DOM)
 * 8. Modal shows LoadError on error state
 * 9. Modal shows LibraryGameCard on success state
 */

import { afterEach, beforeAll, beforeEach, describe, expect, it, vi } from 'vitest';
import type { ReactNode } from 'react';
import { cleanup, render, screen, fireEvent, waitFor } from '@testing-library/react';

// Stub Tooltip so tests don't need a TooltipProvider wrapper.
vi.mock('@/components/ui/tooltip', () => ({
  Tooltip: ({ children }: { children: ReactNode }) => children,
}));

// Mock useLibraryGame — controlled per test
vi.mock('@/hooks/useLibrary', async () => {
  const actual = await vi.importActual<typeof import('@/hooks/useLibrary')>('@/hooks/useLibrary');
  return {
    ...actual,
    useLibraryGame: vi.fn(),
  };
});

// Mock react-chessboard to avoid SVG/canvas rendering in test environment
vi.mock('react-chessboard', () => ({
  Chessboard: vi.fn(() => null),
}));

import { FlawCard } from '../FlawCard';
import type { FlawListItem, GameFlawCard } from '@/types/library';
import { useLibraryGame } from '@/hooks/useLibrary';

// ── jsdom stubs ───────────────────────────────────────────────────────────────

// Stub IntersectionObserver as a class (jsdom doesn't have it) — LazyMiniBoard uses it.
// Fire isIntersecting=true immediately so the board renders in tests.
class MockIntersectionObserver {
  private callback: (entries: { isIntersecting: boolean }[]) => void;
  observe = vi.fn().mockImplementation(() => {
    this.callback([{ isIntersecting: true }]);
  });
  unobserve = vi.fn();
  disconnect = vi.fn();
  constructor(callback: (entries: { isIntersecting: boolean }[]) => void) {
    this.callback = callback;
  }
}
vi.stubGlobal('IntersectionObserver', MockIntersectionObserver);

beforeAll(() => {

  // TagChip uses window.matchMedia (desktop: matches=false)
  Object.defineProperty(window, 'matchMedia', {
    writable: true,
    value: vi.fn().mockImplementation((query: string) => ({
      matches: false,
      media: query,
      onchange: null,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      addListener: vi.fn(),
      removeListener: vi.fn(),
      dispatchEvent: vi.fn(),
    })),
  });
});

// ── Mock dependencies ─────────────────────────────────────────────────────────

vi.mock('@/hooks/useFlawFilterStore', () => ({
  useFlawFilterStore: () => [{ severity: ['blunder', 'mistake'], tags: [] }, vi.fn()] as const,
}));

// ── Test data factory ─────────────────────────────────────────────────────────

function makeFlaw(overrides: Partial<FlawListItem> = {}): FlawListItem {
  return {
    game_id: 42,
    ply: 2,
    fen: 'rnbqkbnr/pp1ppppp/8/2p5/4P3/8/PPPP1PPP/RNBQKBNR',
    move_san: 'Nxd4',
    severity: 'blunder',
    tags: ['miss'],
    eval_cp_before: 470,
    eval_mate_before: null,
    eval_cp_after: -120,
    eval_mate_after: null,
    white_rating: 1850,
    black_rating: 1720,
    user_result: 'loss',
    played_at: '2026-01-15T10:00:00Z',
    time_control_bucket: 'rapid',
    time_control_str: '600+5',
    ply_count: 84,
    termination: 'resignation',
    platform: 'lichess',
    platform_url: 'https://lichess.org/abcd1234',
    white_username: 'Alice',
    black_username: 'Bob',
    user_color: 'white',
    ...overrides,
  };
}

// Default: modal closed → disabled hook returns no-op result
beforeEach(() => {
  vi.mocked(useLibraryGame).mockReturnValue({
    isLoading: false,
    isError: false,
    data: undefined,
  } as ReturnType<typeof useLibraryGame>);
});

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

// ── Tests ─────────────────────────────────────────────────────────────────────

describe('FlawCard', () => {
  describe('CardHeader — usernames and ratings (SC-4)', () => {
    it('renders white username in the header', () => {
      render(<FlawCard flaw={makeFlaw()} />);
      const article = screen.getByTestId('flaw-card-42-2');
      expect(article.textContent).toContain('Alice');
    });

    it('renders black username in the header', () => {
      render(<FlawCard flaw={makeFlaw()} />);
      const article = screen.getByTestId('flaw-card-42-2');
      expect(article.textContent).toContain('Bob');
    });

    it('renders white rating in parentheses when non-null', () => {
      render(<FlawCard flaw={makeFlaw()} />);
      const article = screen.getByTestId('flaw-card-42-2');
      expect(article.textContent).toContain('(1850)');
    });

    it('renders black rating in parentheses when non-null', () => {
      render(<FlawCard flaw={makeFlaw()} />);
      const article = screen.getByTestId('flaw-card-42-2');
      expect(article.textContent).toContain('(1720)');
    });

    it('omits parentheses when white_rating is null (no empty parens)', () => {
      render(<FlawCard flaw={makeFlaw({ white_rating: null })} />);
      const article = screen.getByTestId('flaw-card-42-2');
      // Should have Bob's rating but no "()" without a number
      expect(article.textContent).not.toMatch(/\(\s*\)/);
    });

    it('omits parentheses when black_rating is null', () => {
      render(<FlawCard flaw={makeFlaw({ black_rating: null })} />);
      const article = screen.getByTestId('flaw-card-42-2');
      expect(article.textContent).not.toMatch(/\(\s*\)/);
    });
  });

  describe('Move notation (SC-5)', () => {
    it('renders white move notation: ply=2 → "2.Nxd4"', () => {
      render(<FlawCard flaw={makeFlaw({ ply: 2, move_san: 'Nxd4' })} />);
      const article = screen.getByTestId('flaw-card-42-2');
      expect(article.textContent).toContain('2.Nxd4');
    });

    it('renders black move notation: ply=3 → "2...c5"', () => {
      render(<FlawCard flaw={makeFlaw({ ply: 3, move_san: 'c5', game_id: 43 })} />);
      const article = screen.getByTestId('flaw-card-43-3');
      expect(article.textContent).toContain('2...c5');
    });

    it('falls back to "Ply N" when move_san is null', () => {
      render(<FlawCard flaw={makeFlaw({ ply: 4, move_san: null })} />);
      const article = screen.getByTestId('flaw-card-42-4');
      expect(article.textContent).toContain('Ply 4');
    });
  });

  describe('Game-info block (Phase 112 follow-up — TC name + base[+inc] • # n Moves)', () => {
    it('renders time control name + base[+inc], move count, and termination', () => {
      render(<FlawCard flaw={makeFlaw()} />);
      const article = screen.getByTestId('flaw-card-42-2');
      // "rapid" bucket + formatTimeControl("600+5") → "10+5"
      expect(article.textContent).toContain('rapid');
      expect(article.textContent).toContain('10+5');
      // "Moves" label is desktop-only and joined with a non-breaking space.
      expect(article.textContent).toContain('42 Moves');
      expect(article.textContent).toContain('resignation');
    });

    it('omits the move-count segment when ply_count is null', () => {
      render(<FlawCard flaw={makeFlaw({ ply_count: null })} />);
      const article = screen.getByTestId('flaw-card-42-2');
      expect(article.textContent).not.toContain('Moves');
    });
  });

  describe('Miniboard (SC-3)', () => {
    it('renders a board at size 132', () => {
      render(<FlawCard flaw={makeFlaw()} />);
      // LazyMiniBoard renders a div with explicit width/height style=132px
      const boardContainers = document.querySelectorAll('[style*="width: 132px"]');
      expect(boardContainers.length).toBeGreaterThan(0);
    });
  });

  describe('data-testid (CLAUDE.md browser-automation rules)', () => {
    it('root article has data-testid="flaw-card-{game_id}-{ply}"', () => {
      render(<FlawCard flaw={makeFlaw()} />);
      expect(screen.getByTestId('flaw-card-42-2')).toBeDefined();
    });

    it('platform link has testid and aria-label', () => {
      render(<FlawCard flaw={makeFlaw()} />);
      const link = screen.getByTestId('flaw-card-platform-link-42-2');
      expect(link).toBeDefined();
      expect(link.getAttribute('aria-label')).toBe('Open at this move on platform');
    });
  });

  describe('"View game" button + modal (SC-7, SC-8)', () => {
    const MOCK_GAME: GameFlawCard = {
      game_id: 42,
      user_result: 'loss',
      played_at: '2026-01-15T10:00:00Z',
      time_control_bucket: 'rapid',
      platform: 'lichess',
      platform_url: 'https://lichess.org/abcd1234',
      white_username: 'Alice',
      black_username: 'Bob',
      white_rating: 1850,
      black_rating: 1720,
      opening_name: null,
      opening_eco: null,
      user_color: 'white',
      ply_count: 60,
      termination: 'checkmate',
      time_control_str: '10+5',
      result_fen: null,
      severity_counts: { inaccuracy: 0, mistake: 0, blunder: 1 },
      chips: [],
      analysis_state: 'analyzed',
      eval_series: null,
      flaw_markers: null,
      phase_transitions: null,
      moves: null,
    };

    it('"View game" button has correct testid and aria-label', () => {
      vi.mocked(useLibraryGame).mockReturnValue({
        isLoading: false,
        isError: false,
        data: undefined,
      } as ReturnType<typeof useLibraryGame>);

      render(<FlawCard flaw={makeFlaw()} />);
      const btn = screen.getByTestId('flaw-card-view-game-42-2');
      expect(btn).toBeDefined();
      expect(btn.getAttribute('aria-label')).toContain('Alice');
      expect(btn.getAttribute('aria-label')).toContain('Bob');
    });

    it('clicking "View game" button opens the modal (flaw-game-modal appears)', async () => {
      vi.mocked(useLibraryGame).mockReturnValue({
        isLoading: true,
        isError: false,
        data: undefined,
      } as ReturnType<typeof useLibraryGame>);

      render(<FlawCard flaw={makeFlaw()} />);
      const btn = screen.getByTestId('flaw-card-view-game-42-2');
      fireEvent.click(btn);

      await waitFor(() => {
        expect(screen.getByTestId('flaw-game-modal')).toBeDefined();
      });
    });

    it('modal shows LoadError when isError is true (CLAUDE.md isError pattern)', async () => {
      vi.mocked(useLibraryGame).mockReturnValue({
        isLoading: false,
        isError: true,
        data: undefined,
      } as ReturnType<typeof useLibraryGame>);

      render(<FlawCard flaw={makeFlaw()} />);
      fireEvent.click(screen.getByTestId('flaw-card-view-game-42-2'));

      await waitFor(() => {
        expect(screen.getByTestId('flaw-game-modal')).toBeDefined();
        // LoadError renders "Failed to load game"
        expect(screen.getByText(/Failed to load game/i)).toBeDefined();
      });
    });

    it('modal shows LibraryGameCard content on success', async () => {
      vi.mocked(useLibraryGame).mockReturnValue({
        isLoading: false,
        isError: false,
        data: MOCK_GAME,
      } as ReturnType<typeof useLibraryGame>);

      render(<FlawCard flaw={makeFlaw()} />);
      fireEvent.click(screen.getByTestId('flaw-card-view-game-42-2'));

      await waitFor(() => {
        expect(screen.getByTestId('flaw-game-modal')).toBeDefined();
      });
      // LibraryGameCard renders the white + black username
      expect(screen.getByTestId('flaw-game-modal').textContent).toContain('Alice');
    });
  });
});
