// @vitest-environment jsdom
/**
 * Analysis tactic-mode regression tests (Phase 139, Plan 01, Task 3).
 *
 * Verifies the 4 Phase 135 behaviors preserved by TacticModeOverlay wired into Analysis.tsx:
 * - Behavior A: depth-0 tactic renders the overlay without crash (no empty-PV panic).
 * - Behavior B: allowed orientation anchors display depth one ply later (+1 allowed offset).
 * - Behavior C: move numbers use the real game ply (flaw_ply=42 → "22."), not "1.".
 * - Behavior D: clicking the orientation toggle re-seeds the move list; no stale mainline.
 *
 * useAnalysisBoard runs for real; useStockfishEngine + useTacticLines are mocked.
 * These tests are the deletion gate for Plan 03 (TacticLineExplorer removal).
 */

import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { TooltipProvider } from '@/components/ui/tooltip';
import AnalysisPage from '../Analysis';
import { useTacticLines } from '@/hooks/useLibrary';
import type { TacticLinesResponse } from '@/types/library';

// ── Mock useStockfishEngine (no real Worker in jsdom) ──────────────────────────

const engineState = {
  evalCp: null as number | null,
  evalMate: null as number | null,
  pvLines: [] as unknown[],
  depth: 0,
  isAnalyzing: false,
  isReady: true, // ready=true so engine-loading chrome is hidden in all tests
};

vi.mock('@/hooks/useStockfishEngine', () => ({
  useStockfishEngine: () => ({ ...engineState }),
}));

// ── Mock useTacticLines (controlled per test via vi.mocked) ────────────────────

vi.mock('@/hooks/useLibrary', async () => {
  const actual = await vi.importActual<typeof import('@/hooks/useLibrary')>('@/hooks/useLibrary');
  return { ...actual, useTacticLines: vi.fn() };
});

// ── Mock useFlawFilterStore — no filter restrictions so all tactics are visible ─

vi.mock('@/hooks/useFlawFilterStore', () => ({
  useFlawFilterStore: () =>
    [
      {
        severity: [],
        tags: [],
        tacticFamilies: [],
        tacticOrientation: 'either',
        tacticDepthMin: 0,
        tacticDepthMax: 11,
      },
      vi.fn(),
    ] as const,
}));

// ── jsdom shims required by react-chessboard + HorizontalMoveList ─────────────

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

class ResizeObserverStub {
  observe() {}
  unobserve() {}
  disconnect() {}
}
(globalThis as unknown as { ResizeObserver: typeof ResizeObserverStub }).ResizeObserver =
  ResizeObserverStub;

if (!('scrollTo' in window) || typeof window.scrollTo !== 'function') {
  window.scrollTo = vi.fn() as unknown as typeof window.scrollTo;
}

// HorizontalMoveList auto-scrolls the active move into view.
Element.prototype.scrollIntoView = vi.fn();

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
  engineState.evalCp = null;
  engineState.evalMate = null;
  engineState.pvLines = [];
  engineState.depth = 0;
  engineState.isAnalyzing = false;
  engineState.isReady = true;
});

// ─── Fixtures ─────────────────────────────────────────────────────────────────

// After 1.e4 (Black to move). Serves as position_fen for all fixtures.
// SAN moves in missed/allowed lists must be valid from this position.
const POSITION_FEN = 'rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1';

// flaw_ply=42 chosen per plan spec (game half-move 42, 0-based):
// moveLabel(42, 0) → realPly=42, fullMove=ceil(43/2)=22, 42%2===0=white → "22."
// (NOT "1." — verifies Behavior C real-game-ply numbering)
const FLAW_PLY = 42;
const TACTIC_URL = `/analysis?game_id=1&flaw_ply=${FLAW_PLY}&orientation=missed`;

/**
 * Depth-0 tactic (Behavior A): single missed line at immediate depth.
 * depth=0 → display depth = 0+1(display offset) = 1 (for missed orientation).
 * The "Punchline" label shows because displayDepth is 1 at root and 0 after one step.
 */
const DEPTH_0_RESPONSE: TacticLinesResponse = {
  missed_moves: ['Nf6'],
  missed_depth: 0,
  missed_tactic_ply_index: 0,
  missed_motif: 'fork',
  missed_eval_cp: 150,
  missed_eval_mate: null,
  allowed_moves: null,
  allowed_depth: null,
  allowed_tactic_ply_index: null,
  allowed_motif: null,
  allowed_eval_cp: null,
  allowed_eval_mate: null,
  position_fen: POSITION_FEN,
  flaw_move_san: 'e5',
  best_move_uci: 'g8f6',
  flaw_ply: FLAW_PLY,
  flaw_severity: 'blunder',
};

/**
 * Both lines (Behaviors B, C, D): missed + allowed, each with raw depth=0.
 *
 * Behavior B verification:
 *   toDisplayDepthForOrientation('missed', 0)  = 0+1 = 1
 *   toDisplayDepthForOrientation('allowed', 0) = 0+1+1 = 2   ← allowed +1 offset
 *
 * move sequences must be valid from POSITION_FEN (Black to move after 1.e4):
 *   missed:  1...Nf6, 2.Nc3  (fork scenario)
 *   allowed: 1...e5 (flaw move), 2.Qh5 (refutation — Scholar's Mate start)
 */
const BOTH_LINES_RESPONSE: TacticLinesResponse = {
  missed_moves: ['Nf6', 'Nc3'],
  missed_depth: 0,
  missed_tactic_ply_index: 0,
  missed_motif: 'fork',
  missed_eval_cp: 150,
  missed_eval_mate: null,
  allowed_moves: ['e5', 'Qh5'],
  allowed_depth: 0,
  allowed_tactic_ply_index: 1,
  allowed_motif: 'fork',
  allowed_eval_cp: -80,
  allowed_eval_mate: null,
  position_fen: POSITION_FEN,
  flaw_move_san: 'e5',
  best_move_uci: 'g8f6',
  flaw_ply: FLAW_PLY,
  flaw_severity: 'blunder',
};

// ─── Render helper ─────────────────────────────────────────────────────────────

/**
 * Render <AnalysisPage> with tactic-mode URL params inside required providers.
 * QueryClientProvider is required by useTacticLines (TanStack Query hook).
 */
function renderTacticAnalysis(initialPath = TACTIC_URL) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[initialPath]}>
        <TooltipProvider>
          <AnalysisPage />
        </TooltipProvider>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

// ─── Tests ────────────────────────────────────────────────────────────────────

describe('Analysis tactic mode — Phase 135 regression behaviors', () => {
  // ── Behavior A: depth-0 tactic renders without crash ──────────────────────────

  it('Behavior A: depth-0 tactic renders the overlay and move list without crashing', async () => {
    vi.mocked(useTacticLines).mockReturnValue({
      data: DEPTH_0_RESPONSE,
      isLoading: false,
      isError: false,
    } as ReturnType<typeof useTacticLines>);

    renderTacticAnalysis();

    // Overlay container must render — no empty-PV crash on depth=0 tactics.
    await waitFor(() => {
      expect(screen.getByTestId('tactic-mode-overlay')).toBeTruthy();
    });

    // The single PV move must render with a testid anchored to the real game ply.
    await waitFor(() => {
      expect(screen.getByTestId(`tactic-san-move-${FLAW_PLY}`)).toBeTruthy();
    });

    // The page shell must remain intact (board not crashed by depth-0 path).
    expect(screen.getByTestId('analysis-page')).toBeTruthy();
    expect(screen.getByTestId('analysis-board')).toBeTruthy();
  });

  // ── Behavior B: allowed orientation seeds the flaw lead-in (blunder glyph) ──
  // The +1 allowed depth anchoring (toDisplayDepthForOrientation) is unit-tested
  // in tacticDepth.test.ts; the on-screen depth counter was removed (UAT). Here
  // we assert the observable allowed-orientation behavior: the prepended flaw
  // move ('e5') leads the line and carries the blunder severity glyph.

  it('Behavior B: allowed orientation seeds the allowed PV with the flaw lead-in glyph', async () => {
    vi.mocked(useTacticLines).mockReturnValue({
      data: BOTH_LINES_RESPONSE,
      isLoading: false,
      isError: false,
    } as ReturnType<typeof useTacticLines>);

    // Open with allowed orientation so the flaw lead-in seeds immediately.
    renderTacticAnalysis(`/analysis?game_id=1&flaw_ply=${FLAW_PLY}&orientation=allowed`);

    await waitFor(() => {
      expect(screen.getByTestId('tactic-mode-overlay')).toBeTruthy();
    });

    // First move is the flaw lead-in 'e5' (allowed_moves[0]), not the missed 'Nf6'.
    await waitFor(() => {
      const firstMove = screen.getByTestId(`tactic-san-move-${FLAW_PLY}`);
      expect(firstMove.textContent).toContain('e5');
    });

    // The blunder severity glyph marks the allowed flaw lead-in.
    expect(screen.getByTestId('tactic-san-flaw-severity-blunder')).toBeTruthy();
  });

  // ── Behavior C: move numbers anchored to real game ply, not restarted at "1." ─

  it('Behavior C: move labels use real game ply (flaw_ply=42 → move 22, not move 1)', async () => {
    vi.mocked(useTacticLines).mockReturnValue({
      data: DEPTH_0_RESPONSE,
      isLoading: false,
      isError: false,
    } as ReturnType<typeof useTacticLines>);

    renderTacticAnalysis();

    await waitFor(() => {
      expect(screen.getByTestId(`tactic-san-move-${FLAW_PLY}`)).toBeTruthy();
    });

    // moveLabel(42, 0): realPly=42, fullMove=ceil(43/2)=22, white → "22."
    // The HorizontalMoveList renders numberLabel in a sibling <span> before the
    // move button, so we assert on the ladder container's full text content.
    const moveList = screen.getByTestId('tactic-san-ladder');
    expect(moveList.textContent).toContain('22.');
    expect(moveList.textContent).not.toContain('1.'); // restarted numbering would show "1."
  });

  // ── Behavior D: orientation toggle re-seeds the move list (no stale mainline) ─

  it('Behavior D: clicking the allowed toggle re-seeds the move list to the allowed PV', async () => {
    vi.mocked(useTacticLines).mockReturnValue({
      data: BOTH_LINES_RESPONSE,
      isLoading: false,
      isError: false,
    } as ReturnType<typeof useTacticLines>);

    renderTacticAnalysis();

    // Initial state: missed orientation → first PV item is 'Nf6' (missed_moves[0]).
    await waitFor(() => {
      const firstMove = screen.getByTestId(`tactic-san-move-${FLAW_PLY}`);
      expect(firstMove.textContent).toContain('Nf6');
    });

    // Click the Allowed chip to switch orientation.
    const allowedToggle = await screen.findByTestId('tactic-toggle-allowed');
    fireEvent.click(allowedToggle);

    // After toggle: allowed orientation → first item is 'e5' (the flaw lead-in in allowed_moves).
    // The re-seed effect fires (positionFen unchanged, resolvedOrientation changed) and
    // TacticModeOverlay picks activeMoves = data.allowed_moves = ['e5', 'Qh5'].
    await waitFor(() => {
      const firstMove = screen.getByTestId(`tactic-san-move-${FLAW_PLY}`);
      expect(firstMove.textContent).toContain('e5');
    });

    // The stale missed move 'Nf6' must not appear as the first move in the updated list.
    const firstMoveAfter = screen.getByTestId(`tactic-san-move-${FLAW_PLY}`);
    expect(firstMoveAfter.textContent).not.toContain('Nf6');
  });
});
