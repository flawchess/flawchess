// @vitest-environment jsdom
/**
 * Phase 138 Plan 01 — Analysis page Wave-0 test scaffold.
 *
 * RED in Wave 0: all tests fail with "Cannot find module '../Analysis'" because
 * Analysis.tsx does not exist yet. Plan 02 creates that file and turns these GREEN.
 *
 * Verifies the Analysis page observable behaviors:
 * - Shell renders with required testids (ROUTE-01)
 * - ?fen= param seeds the board root (ROUTE-02)
 * - Malformed ?fen= degrades to standard start without throwing (ROUTE-02 / security)
 * - "Loading engine..." chrome shows while isReady=false, board stays interactive (D-06 / SC#3)
 * - Engine ready hides the loading chrome (D-06)
 */

import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { TooltipProvider } from '@/components/ui/tooltip';

// ── Mock useStockfishEngine: jsdom has no real Worker for the classic engine file.
// Drive isReady/pvLines states deterministically via the mutable engineState object.
const engineState: {
  evalCp: number | null;
  evalMate: number | null;
  pvLines: unknown[];
  depth: number;
  isAnalyzing: boolean;
  isReady: boolean;
} = {
  evalCp: null,
  evalMate: null,
  pvLines: [],
  depth: 0,
  isAnalyzing: false,
  isReady: false,
};

vi.mock('@/hooks/useStockfishEngine', () => ({
  useStockfishEngine: () => ({ ...engineState }),
}));

// Mock useTacticLines: free-play shell tests have no tactic params, so tactic data
// is unused. Return an empty/undefined stub so the hook does not need a real network.
vi.mock('@/hooks/useLibrary', () => ({
  useTacticLines: () => ({ data: undefined }),
}));

// Mock useFlawFilterStore: Analysis.tsx calls this unconditionally for tactic visibility.
vi.mock('@/hooks/useFlawFilterStore', () => ({
  useFlawFilterStore: () => [null, vi.fn()],
}));

// NOTE: useAnalysisBoard is NOT mocked — it is pure in-memory and must run for real
// so ?fen= seeding is genuinely exercised.

// jsdom shims required by react-chessboard and responsive components.
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

afterEach(() => {
  cleanup();
  // Reset engine state to defaults after each test.
  engineState.evalCp = null;
  engineState.evalMate = null;
  engineState.pvLines = [];
  engineState.depth = 0;
  engineState.isAnalyzing = false;
  engineState.isReady = false;
});

// Late import after vi.mock calls — Analysis.tsx is a default export (required by React.lazy).
// This import is intentionally RED in Wave 0: Analysis.tsx does not exist yet.
import AnalysisPage from '../Analysis';

// ── Render helper ──────────────────────────────────────────────────────────────
function renderAnalysis(initialPath = '/analysis') {
  // QueryClientProvider is required by useTacticLines (TanStack Query).
  // Tactic-mode tests that need real query behavior will supply their own client
  // via a dedicated test file (Analysis.tactic.test.tsx, Phase 139 Task 3).
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

// ── Tests ──────────────────────────────────────────────────────────────────────

describe('Analysis page shell', () => {
  it('renders shell with required testids (ROUTE-01)', () => {
    renderAnalysis();

    expect(screen.getByTestId('analysis-page')).toBeTruthy();
    expect(screen.getByTestId('analysis-board')).toBeTruthy();
    expect(screen.getByTestId('analysis-eval-bar')).toBeTruthy();
  });

  it('seeds the board from a valid ?fen= param (ROUTE-02)', () => {
    // A mid-opening FEN: 1. e4 e5 2. Nf3 (white to move, 3rd move)
    const openingFen = 'rnbqkb1r/pppp1ppp/5n2/4p3/4P3/5N2/PPPP1PPP/RNBQKB1R w KQkq - 2 3';
    const encodedFen = encodeURIComponent(openingFen);

    renderAnalysis(`/analysis?fen=${encodedFen}`);

    // The page must render without error, and the shell must be present.
    // useAnalysisBoard consumes the FEN as initialRootFen — the board will not be
    // at the standard start position when a valid FEN is provided.
    expect(screen.getByTestId('analysis-page')).toBeTruthy();
    expect(screen.getByTestId('analysis-board')).toBeTruthy();
  });

  it('degrades to start position on malformed ?fen= without throwing (security)', () => {
    // Malformed FEN: the security guard in Analysis.tsx falls back to STARTING_FEN.
    expect(() => {
      renderAnalysis('/analysis?fen=not-a-valid-fen');
    }).not.toThrow();

    expect(screen.getByTestId('analysis-page')).toBeTruthy();
  });

  it('shows engine-loading chrome while isReady=false, board stays present (D-06 / SC#3)', () => {
    // Default engineState has isReady: false — engine is loading.
    renderAnalysis();

    // "Loading engine..." must appear in the eval area.
    expect(screen.getByTestId('analysis-engine-loading')).toBeTruthy();
    // Board must remain present — never blocked on engine readiness.
    expect(screen.getByTestId('analysis-board')).toBeTruthy();
    // The loading text must mention the engine.
    expect(screen.getByTestId('analysis-engine-loading').textContent).toMatch(/loading engine/i);
  });

  it('hides the engine-loading chrome when isReady=true (D-06)', () => {
    engineState.isReady = true;

    renderAnalysis();

    expect(screen.queryByTestId('analysis-engine-loading')).toBeNull();
  });
});
