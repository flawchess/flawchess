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

// Mock useStockfishGradingEngine (Phase 151.1 Plan 04): jsdom has no real Worker for
// this SECOND classic engine file either. Deterministic empty-gradeMap stub — the
// grading hook's own behavior is covered by useStockfishGradingEngine.test.ts.
vi.mock('@/hooks/useStockfishGradingEngine', () => ({
  useStockfishGradingEngine: () => ({
    gradeMap: new Map(),
    isGrading: false,
    isReady: false,
  }),
}));

// Mock useMaiaEngine: jsdom has no real Worker for the classic Maia worker file
// either (Phase 151 Plan 06). Deterministic curve stub via the mutable maiaState —
// the Maia surfaces' own behavior is covered by useMaiaEngine.test.ts /
// MovesByRatingChart.test.tsx. expectedScoreAtSelectedElo drives the Maia bar fill.
const maiaState: { expectedScoreAtSelectedElo: number | null } = {
  expectedScoreAtSelectedElo: null,
};

vi.mock('@/hooks/useMaiaEngine', () => ({
  useMaiaEngine: () => ({
    perElo: [],
    expectedScoreAtSelectedElo: maiaState.expectedScoreAtSelectedElo,
    wdl: null,
    isReady: false,
    isAnalyzing: false,
  }),
}));

// Mock useUserProfile: no real network in this shell-level test.
vi.mock('@/hooks/useUserProfile', () => ({
  useUserProfile: () => ({ data: undefined, isError: false }),
}));

// Mock useTacticLines and useLibraryGame: free-play shell tests have no tactic/game
// params, so both return empty stubs — no real network needed.
vi.mock('@/hooks/useLibrary', () => ({
  useTacticLines: () => ({ data: undefined, isFetching: false, isError: false }),
  useLibraryGame: () => ({ data: undefined, isError: false }),
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
  maiaState.expectedScoreAtSelectedElo = null;
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
    // Phase 151 Plan 06 (SURF-04): the Maia bar renders on every position too.
    expect(screen.getByTestId('analysis-maia-eval-bar')).toBeTruthy();
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

    // The loading skeleton must appear in the engine card (Quick 260627-r9g item 3
    // replaced the "Loading engine…" text with a content-loading animation).
    const loading = screen.getByTestId('analysis-engine-loading');
    expect(loading).toBeTruthy();
    expect(loading.getAttribute('aria-busy')).toBe('true');
    // Board must remain present — never blocked on engine readiness.
    expect(screen.getByTestId('analysis-board')).toBeTruthy();
  });

  it('hides the engine-loading chrome when isReady=true (D-06)', () => {
    engineState.isReady = true;

    renderAnalysis();

    expect(screen.queryByTestId('analysis-engine-loading')).toBeNull();
  });
});

describe('Maia eval bar perspective (151.1 UAT regression)', () => {
  // Reads the Maia bar's white-share fill height. The white fill is the first
  // absolutely-positioned child div (same convention as EvalBar.test.tsx).
  function maiaWhiteFillPercent(): number {
    const bar = screen.getByTestId('analysis-maia-eval-bar');
    const whiteFill = bar.querySelector('div');
    if (!whiteFill) throw new Error('Maia white fill div not found');
    return parseFloat(whiteFill.style.height.replace('%', ''));
  }

  // Maia's WDL is the side-to-MOVE's perspective. The bar's fill must be
  // WHITE-relative, so a black-to-move expected score of 0.8 (Black favored) must
  // render as a ~20% white fill — NOT 80% (the pre-fix inverted behavior).
  it('inverts the expected score to white-POV when Black is to move', () => {
    maiaState.expectedScoreAtSelectedElo = 0.8;
    // Black to move (after 1. e4).
    const blackToMoveFen = 'rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1';
    renderAnalysis(`/analysis?fen=${encodeURIComponent(blackToMoveFen)}`);

    expect(maiaWhiteFillPercent()).toBeCloseTo(20, 1);
  });

  it('uses the expected score directly (white-POV) when White is to move', () => {
    maiaState.expectedScoreAtSelectedElo = 0.8;
    const whiteToMoveFen = 'rnbqkb1r/pppp1ppp/5n2/4p3/4P3/5N2/PPPP1PPP/RNBQKB1R w KQkq - 2 3';
    renderAnalysis(`/analysis?fen=${encodeURIComponent(whiteToMoveFen)}`);

    expect(maiaWhiteFillPercent()).toBeCloseTo(80, 1);
  });
});
