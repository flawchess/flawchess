// @vitest-environment jsdom
/**
 * FlawsTab vitest suite — tests the three key scenarios from Plan 108-07:
 *
 * 1. Deep-link (?tag=reversed) pre-populates the flaw filter control
 * 2. isError branch renders the mandatory error copy
 * 3. Flaw list renders rows from mocked useLibraryFlaws
 */

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, render, screen } from '@testing-library/react';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { TooltipProvider } from '@/components/ui/tooltip';
import type { Mock } from 'vitest';

// ── Mock heavy dependencies ───────────────────────────────────────────────────

// Stub LazyMiniBoard to avoid IntersectionObserver + react-chessboard in jsdom
vi.mock('@/components/board/LazyMiniBoard', () => ({
  LazyMiniBoard: ({ fen }: { fen: string }) => (
    <div data-testid="stub-mini-board" data-fen={fen} />
  ),
}));

// Stub SidebarLayout — render both the sidebar content (panels) and children
// so that FlawFilterControl (in the panel) is visible in the test DOM.
vi.mock('@/components/layout/SidebarLayout', () => ({
  SidebarLayout: ({
    children,
    panels,
  }: {
    children: React.ReactNode;
    panels: Array<{ content: React.ReactNode }>;
  }) => (
    <div data-testid="stub-sidebar-layout">
      {panels.map((p, i) => (
        // Render all panel contents so filter controls are accessible
        <div key={i} data-testid="stub-sidebar-panel">{p.content}</div>
      ))}
      {children}
    </div>
  ),
}));

// Stub TagChip to avoid Popover/portal issues in jsdom
vi.mock('@/components/library/TagChip', () => ({
  TagChip: ({ tag }: { tag: string }) => (
    <span data-testid={`stub-tag-chip-${tag}`}>{tag}</span>
  ),
}));

// Stub LibraryFilterPanel to avoid window.matchMedia (FilterPanel) in jsdom.
// The stub renders FlawFilterControl if the new flawFilter props are passed,
// so tests that check for flaw-filter-control or btn-clear-flaw-filter still work.
vi.mock('@/components/filters/LibraryFilterPanel', async () => {
  const { FlawFilterControl } = await vi.importActual<typeof import('@/components/filters/FlawFilterControl')>('@/components/filters/FlawFilterControl');
  return {
    LibraryFilterPanel: ({
      flawFilter,
      onFlawFilterChange,
      onClearFlawFilter,
    }: {
      flawFilter?: { severity: ('blunder' | 'mistake')[]; tags: string[] };
      onFlawFilterChange?: (next: { severity: ('blunder' | 'mistake')[]; tags: string[] }) => void;
      onClearFlawFilter?: () => void;
    }) => (
      <div data-testid="stub-library-filter-panel">
        {flawFilter && onFlawFilterChange && onClearFlawFilter && (
          <FlawFilterControl
            severity={flawFilter.severity}
            tags={flawFilter.tags as import('@/types/library').FlawTag[]}
            onSeverityChange={(severity) => onFlawFilterChange({ ...flawFilter, severity })}
            onTagChange={(tags) => onFlawFilterChange({ ...flawFilter, tags })}
            onClear={onClearFlawFilter}
          />
        )}
      </div>
    ),
  };
});

// Stub useUserProfile
vi.mock('@/hooks/useUserProfile', () => ({
  useUserProfile: () => ({
    data: { chess_com_game_count: 5, lichess_game_count: 10 },
  }),
}));

// ── Controlled useLibraryFlaws mock ───────────────────────────────────────────

type MockFlawsResult = {
  data?: {
    flaws: Array<{
      game_id: number;
      ply: number;
      fen: string;
      move_san: string | null;
      severity: 'mistake' | 'blunder';
      tags: string[];
      es_before: number;
      es_after: number;
      user_result: 'win' | 'draw' | 'loss';
      played_at: string | null;
      time_control_bucket: string | null;
      platform: string;
      platform_url: string | null;
      white_username: string | null;
      black_username: string | null;
      user_color: string;
    }>;
    matched_count: number;
    offset: number;
    limit: number;
  };
  isLoading: boolean;
  isError: boolean;
};

let mockFlawsResult: MockFlawsResult = {
  data: { flaws: [], matched_count: 0, offset: 0, limit: 20 },
  isLoading: false,
  isError: false,
};

vi.mock('@/hooks/useLibrary', () => ({
  useLibraryFlaws: () => mockFlawsResult,
  useLibraryGames: () => ({ data: undefined, isLoading: false, isError: false }),
  useLibraryFlawStats: () => ({ data: undefined, isLoading: false, isError: false }),
}));

// ── useFlawFilterStore mock — allows per-test state control ───────────────────

// We need a controllable store: the real store is module-level and persists
// between tests. Instead, mock the entire module with React state.
let mockStoreState = { severity: ['blunder', 'mistake'] as ('blunder' | 'mistake')[], tags: [] as string[] };
const mockSetFlawFilter = vi.fn((updater: typeof mockStoreState | ((prev: typeof mockStoreState) => typeof mockStoreState)) => {
  const next = typeof updater === 'function' ? updater(mockStoreState) : updater;
  mockStoreState = next;
});

vi.mock('@/hooks/useFlawFilterStore', async () => {
  const actual =
    await vi.importActual<typeof import('@/hooks/useFlawFilterStore')>('@/hooks/useFlawFilterStore');
  return {
    ...actual,
    useFlawFilterStore: () => [mockStoreState, mockSetFlawFilter] as const,
  };
});

// ── Import FlawsTab after mocks are in place ──────────────────────────────────

import { FlawsTab } from '../FlawsTab';

// ── Render helper ─────────────────────────────────────────────────────────────

function renderFlawsTab(initialPath = '/library/flaws') {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <TooltipProvider>
        <MemoryRouter initialEntries={[initialPath]}>
          <Routes>
            <Route path="/library/flaws" element={<FlawsTab />} />
            <Route path="/library/import" element={<div data-testid="stub-import" />} />
          </Routes>
        </MemoryRouter>
      </TooltipProvider>
    </QueryClientProvider>,
  );
}

// ── Setup / teardown ──────────────────────────────────────────────────────────

beforeEach(() => {
  mockStoreState = { severity: ['blunder', 'mistake'], tags: [] };
  vi.clearAllMocks();
  mockFlawsResult = {
    data: { flaws: [], matched_count: 0, offset: 0, limit: 20 },
    isLoading: false,
    isError: false,
  };
});

afterEach(() => {
  cleanup();
});

// ── Tests ─────────────────────────────────────────────────────────────────────

describe('FlawsTab', () => {
  describe('rendering', () => {
    it('renders the flaws tab content root', () => {
      renderFlawsTab();
      expect(screen.getByTestId('flaws-tab-content')).toBeTruthy();
    });

    it('renders the flaw-list section', () => {
      renderFlawsTab();
      // flaw-list appears in both desktop (via SidebarLayout children) and mobile stacked content
      const flawLists = screen.getAllByTestId('flaw-list');
      expect(flawLists.length).toBeGreaterThanOrEqual(1);
    });

    it('renders the FlawFilterControl in the sidebar panel', () => {
      renderFlawsTab();
      // FlawFilterControl rendered inside stub-sidebar-panel (desktop sidebar content)
      // plus in the mobile section (inline in mobile drawer position)
      const controls = screen.getAllByTestId('flaw-filter-control');
      expect(controls.length).toBeGreaterThanOrEqual(1);
    });
  });

  describe('isError branch', () => {
    it('renders the mandatory error message when useLibraryFlaws returns isError', () => {
      mockFlawsResult = { data: undefined, isLoading: false, isError: true };
      renderFlawsTab();
      // Appears in both desktop + mobile sections
      const errorMessages = screen.getAllByText(
        'Failed to load flaws. Something went wrong. Please try again in a moment.',
      );
      expect(errorMessages.length).toBeGreaterThanOrEqual(1);
    });

    it('does NOT render the flaw-list when isError', () => {
      mockFlawsResult = { data: undefined, isLoading: false, isError: true };
      renderFlawsTab();
      // flaw-list section is inside !flawsError check — should not be present
      expect(screen.queryAllByTestId('flaw-list').length).toBe(0);
    });
  });

  describe('flaw list rows', () => {
    it('renders miniboard rows from mocked useLibraryFlaws data', () => {
      mockFlawsResult = {
        data: {
          flaws: [
            {
              game_id: 1,
              ply: 24,
              fen: 'rnbqkb1r/pppp1ppp/4pn2/8/2PP4/8/PP2PPPP/RNBQKBNR',
              move_san: 'Nxd4',
              severity: 'blunder',
              tags: ['reversed'],
              es_before: 0.72,
              es_after: 0.28,
              user_result: 'loss',
              played_at: '2026-05-01T10:00:00Z',
              time_control_bucket: 'blitz',
              platform: 'lichess',
              platform_url: 'https://lichess.org/abcd1234',
              white_username: 'opponent',
              black_username: 'testuser',
              user_color: 'black',
            },
            {
              game_id: 2,
              ply: 32,
              fen: 'r1bqkb1r/pppp1ppp/2n2n2/4p3/2B1P3/5N2/PPPP1PPP/RNBQK2R',
              move_san: 'Nd4',
              severity: 'mistake',
              tags: ['miss'],
              es_before: 0.55,
              es_after: 0.45,
              user_result: 'draw',
              played_at: '2026-05-02T12:00:00Z',
              time_control_bucket: 'rapid',
              platform: 'chess.com',
              platform_url: null,
              white_username: 'testuser',
              black_username: 'opponent2',
              user_color: 'white',
            },
          ],
          matched_count: 2,
          offset: 0,
          limit: 20,
        },
        isLoading: false,
        isError: false,
      };

      renderFlawsTab();

      // Two miniboards in desktop section, two in mobile = 4 total (or 2 if mobile hidden in jsdom)
      const boards = screen.getAllByTestId('stub-mini-board');
      expect(boards.length).toBeGreaterThanOrEqual(2);

      // SeverityBadge elements per flaw (appears in both desktop + mobile)
      expect(screen.getAllByTestId('severity-blunder-1').length).toBeGreaterThanOrEqual(1);
      expect(screen.getAllByTestId('severity-mistake-2').length).toBeGreaterThanOrEqual(1);

      // Tag chips rendered for each flaw (in both desktop + mobile sections)
      expect(screen.getAllByTestId('stub-tag-chip-reversed').length).toBeGreaterThanOrEqual(1);
      expect(screen.getAllByTestId('stub-tag-chip-miss').length).toBeGreaterThanOrEqual(1);
    });

    it('deep-links the lichess flaw to the exact ply and chess.com to the plain game', () => {
      mockFlawsResult = {
        data: {
          flaws: [
            {
              game_id: 1,
              ply: 24,
              fen: 'rnbqkb1r/pppp1ppp/4pn2/8/2PP4/8/PP2PPPP/RNBQKBNR',
              move_san: 'Nxd4',
              severity: 'blunder',
              tags: ['reversed'],
              es_before: 0.72,
              es_after: 0.28,
              user_result: 'loss',
              played_at: '2026-05-01T10:00:00Z',
              time_control_bucket: 'blitz',
              platform: 'lichess',
              platform_url: 'https://lichess.org/abcd1234',
              white_username: 'opponent',
              black_username: 'testuser',
              user_color: 'black',
            },
            {
              game_id: 2,
              ply: 32,
              fen: 'r1bqkb1r/pppp1ppp/2n2n2/4p3/2B1P3/5N2/PPPP1PPP/RNBQK2R',
              move_san: 'Nd4',
              severity: 'mistake',
              tags: ['miss'],
              es_before: 0.55,
              es_after: 0.45,
              user_result: 'draw',
              played_at: '2026-05-02T12:00:00Z',
              time_control_bucket: 'rapid',
              platform: 'chess.com',
              platform_url: 'https://www.chess.com/game/live/999',
              white_username: 'testuser',
              black_username: 'opponent2',
              user_color: 'white',
            },
          ],
          matched_count: 2,
          offset: 0,
          limit: 20,
        },
        isLoading: false,
        isError: false,
      };

      renderFlawsTab();

      // Links land on the blunder (position AFTER the flawed move), so a flaw at
      // 0-indexed ply N maps to N + 1 half-moves.
      // Lichess flaw (game 1, ply 24, user played black) → black POV at #25.
      const lichessLinks = screen.getAllByTestId('flaw-card-link-1-24');
      expect(lichessLinks.length).toBeGreaterThanOrEqual(1);
      expect(lichessLinks[0]?.getAttribute('href')).toBe('https://lichess.org/abcd1234/black#25');

      // chess.com flaw (game 2, ply 32, user played white) → analysis board move=33.
      const chessComLinks = screen.getAllByTestId('flaw-card-link-2-32');
      expect(chessComLinks.length).toBeGreaterThanOrEqual(1);
      expect(chessComLinks[0]?.getAttribute('href')).toBe(
        'https://www.chess.com/analysis/game/live/999?tab=details-tab&move=33',
      );
    });

    it('renders matched count row', () => {
      mockFlawsResult = {
        data: { flaws: [], matched_count: 42, offset: 0, limit: 20 },
        isLoading: false,
        isError: false,
      };
      renderFlawsTab();
      const countEls = screen.getAllByText('42 flaws matched');
      expect(countEls.length).toBeGreaterThanOrEqual(1);
    });

    it('renders singular "flaw" for matched_count=1', () => {
      mockFlawsResult = {
        data: { flaws: [], matched_count: 1, offset: 0, limit: 20 },
        isLoading: false,
        isError: false,
      };
      renderFlawsTab();
      const countEls = screen.getAllByText('1 flaw matched');
      expect(countEls.length).toBeGreaterThanOrEqual(1);
    });
  });

  describe('empty states', () => {
    it('shows "No flaws matched" empty state when matched_count=0', () => {
      mockFlawsResult = {
        data: { flaws: [], matched_count: 0, offset: 0, limit: 20 },
        isLoading: false,
        isError: false,
      };
      renderFlawsTab();
      const headings = screen.getAllByText('No flaws matched');
      expect(headings.length).toBeGreaterThanOrEqual(1);
      const captions = screen.getAllByText('Try adjusting the flaw filter or game filters.');
      expect(captions.length).toBeGreaterThanOrEqual(1);
    });
  });

  describe('URL sync — deep-link pre-population', () => {
    it('initializes the store from URL params on mount when ?tag=reversed', () => {
      // The FlawsTab reads URL params on mount and calls setFlawFilter
      renderFlawsTab('/library/flaws?tag=reversed');

      // setFlawFilter should have been called with reversed tag
      expect(mockSetFlawFilter).toHaveBeenCalled();
      // Find the call that set the reversed tag
      const calls = (mockSetFlawFilter as Mock).mock.calls;
      const tagSetCall = calls.find((call) => {
        const arg = call[0];
        const resolved = typeof arg === 'function' ? arg(mockStoreState) : arg;
        return Array.isArray(resolved.tags) && resolved.tags.includes('reversed');
      });
      expect(tagSetCall).toBeTruthy();
    });

    it('renders the clear button when store state has tags (non-default)', () => {
      // Set store to have a tag pre-selected (simulating deep-link result)
      mockStoreState = { severity: ['blunder', 'mistake'], tags: ['miss'] };
      renderFlawsTab('/library/flaws');

      // Clear button should appear in at least one FlawFilterControl instance
      const clearBtns = screen.getAllByTestId('btn-clear-flaw-filter');
      expect(clearBtns.length).toBeGreaterThanOrEqual(1);
    });

    it('does NOT call setFlawFilter from URL when no tag/severity params present', () => {
      renderFlawsTab('/library/flaws');
      // Without URL params, the store should not be updated from URL
      expect(mockSetFlawFilter).not.toHaveBeenCalled();
    });
  });
});
