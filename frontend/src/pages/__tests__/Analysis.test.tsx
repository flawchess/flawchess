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
 * - Phase 155: FlawChess Engine eval-bar precedence (DISPLAY-04) — see the dedicated
 *   describe block below.
 */

import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen } from '@testing-library/react';
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
// this SECOND classic engine file either. Deterministic gradeMap stub via the
// mutable gradingState — the grading hook's own behavior is covered by
// useStockfishGradingEngine.test.ts. Phase 158 Plan 03 (SEED-087 SC2): every
// call's options are captured into gradingCalls so tests can assert the
// shared run's (fen, enabled, candidateSans) across toggle combinations.
interface GradingMoveGrade {
  evalCp: number | null;
  evalMate: number | null;
  depth: number;
}
const gradingState: { gradeMap: Map<string, GradingMoveGrade> } = {
  gradeMap: new Map(),
};
const gradingCalls: { fen: string | null; candidateSans: string[]; enabled: boolean }[] = [];

vi.mock('@/hooks/useStockfishGradingEngine', () => ({
  useStockfishGradingEngine: (options: {
    fen: string | null;
    candidateSans: string[];
    enabled: boolean;
  }) => {
    gradingCalls.push(options);
    return {
      gradeMap: gradingState.gradeMap,
      isGrading: false,
      isReady: false,
    };
  },
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

// Mock useFlawChessEngine (Phase 155): jsdom has no real Worker for the pool this
// hook creates either. Deterministic stub via the mutable flawChessState — the
// hook's own throttle/abort behavior is covered by useFlawChessEngine.test.ts.
// isReady defaults to true so the FlawChess card's pre-ready skeleton doesn't mask
// the shell/eval-bar assertions below; individual tests override rankedLines to
// drive the eval-bar precedence.
const flawChessState: {
  rankedLines: {
    rootMove: string;
    practicalScore: number;
    objectiveEvalCp: number | null;
    objectiveEvalMate: number | null;
    modalPath: string[];
    modalStats: { objectiveEvalCp: number | null; objectiveEvalMate: number | null; maiaProb: number | null }[];
    visits: number;
  }[];
  isSearching: boolean;
  isReady: boolean;
} = {
  rankedLines: [],
  isSearching: false,
  isReady: true,
};

vi.mock('@/hooks/useFlawChessEngine', () => ({
  useFlawChessEngine: () => ({
    rankedLines: flawChessState.rankedLines,
    nodesEvaluated: 0,
    budgetExhausted: false,
    isSearching: flawChessState.isSearching,
    isReady: flawChessState.isReady,
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
  flawChessState.rankedLines = [];
  flawChessState.isSearching = false;
  flawChessState.isReady = true;
  gradingState.gradeMap = new Map();
  gradingCalls.length = 0;
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
    // Phase 155 D-04: the FlawChess Engine is on by default, so its bar takes
    // left-slot precedence over Maia (see the dedicated describe block below
    // for the Maia fallback case).
    expect(screen.getByTestId('analysis-flawchess-eval-bar')).toBeTruthy();
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
    // Default engineState has isReady: false — engine is loading. Phase 155 D-04:
    // the FlawChess Engine suppresses the standalone Stockfish search while it is
    // enabled (POOL-04 mutual exclusion, default ON), so the Stockfish card's own
    // loading skeleton only shows once FlawChess is toggled off.
    renderAnalysis();
    fireEvent.click(screen.getByTestId('btn-analysis-flawchess-toggle'));

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

  it('shows the standalone Stockfish top lines in the default state (both switches ON), not a merged placeholder (155 UAT un-merge)', () => {
    // Both engineEnabled and flawChessEnabled default to true — the state every
    // first-time visitor lands in. Post un-merge, the Stockfish search runs
    // independently of the FlawChess Engine, so the card shows its own top-2
    // lines (never a "merged" message).
    engineState.isReady = true;
    engineState.pvLines = [{ moves: ['e2e4'], evalCp: 30, evalMate: null, depth: 12 }];

    renderAnalysis();

    expect(screen.queryByTestId('analysis-engine-merged-message')).toBeNull();
    expect(screen.getByTestId('engine-line-0-move-0')).toBeTruthy();
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
  //
  // Phase 155 D-04: the FlawChess Engine takes left-slot precedence over Maia
  // by default, so these pre-155 tests toggle it off first to exercise the Maia
  // bar specifically (the FC-precedence describe block below covers the
  // FC-enabled path).
  it('inverts the expected score to white-POV when Black is to move', () => {
    maiaState.expectedScoreAtSelectedElo = 0.8;
    // Black to move (after 1. e4).
    const blackToMoveFen = 'rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1';
    renderAnalysis(`/analysis?fen=${encodeURIComponent(blackToMoveFen)}`);
    fireEvent.click(screen.getByTestId('btn-analysis-flawchess-toggle'));

    expect(maiaWhiteFillPercent()).toBeCloseTo(20, 1);
  });

  it('uses the expected score directly (white-POV) when White is to move', () => {
    maiaState.expectedScoreAtSelectedElo = 0.8;
    const whiteToMoveFen = 'rnbqkb1r/pppp1ppp/5n2/4p3/4P3/5N2/PPPP1PPP/RNBQKB1R w KQkq - 2 3';
    renderAnalysis(`/analysis?fen=${encodeURIComponent(whiteToMoveFen)}`);
    fireEvent.click(screen.getByTestId('btn-analysis-flawchess-toggle'));

    expect(maiaWhiteFillPercent()).toBeCloseTo(80, 1);
  });
});

describe('FlawChess Engine eval-bar precedence (Phase 155)', () => {
  it('shows the FlawChess eval bar in the left slot when the FlawChess Engine is enabled (DISPLAY-04)', () => {
    // FlawChess Engine is on by default (D-02) — its bar takes left-slot
    // precedence over Maia.
    renderAnalysis();

    expect(screen.getByTestId('analysis-flawchess-eval-bar')).toBeTruthy();
    expect(screen.queryByTestId('analysis-maia-eval-bar')).toBeNull();
  });

  it('falls back to the Maia eval bar in the left slot once the FlawChess Engine is toggled off (DISPLAY-04)', () => {
    renderAnalysis();

    fireEvent.click(screen.getByTestId('btn-analysis-flawchess-toggle'));

    expect(screen.getByTestId('analysis-maia-eval-bar')).toBeTruthy();
    expect(screen.queryByTestId('analysis-flawchess-eval-bar')).toBeNull();
  });

  it('renders the FlawChess card above the Maia panel by default (D-01)', () => {
    renderAnalysis();

    const flawChessCard = screen.getByTestId('analysis-flawchess-panel');
    const maiaPanel = screen.getByTestId('maia-human-panel');

    // DOCUMENT_POSITION_FOLLOWING: maiaPanel comes AFTER flawChessCard in the DOM.
    const maiaFollowsFlawChess =
      flawChessCard.compareDocumentPosition(maiaPanel) & Node.DOCUMENT_POSITION_FOLLOWING;
    expect(maiaFollowsFlawChess).toBeTruthy();
  });
});

describe('Grading run gating (Phase 158, SEED-087 SC2)', () => {
  it('runs the shared grading run whenever EITHER switch is on, and stops only when both are off', () => {
    renderAnalysis();

    // (maiaEnabled=true, flawChessEnabled=true) — the default state.
    let lastCall = gradingCalls[gradingCalls.length - 1];
    expect(lastCall?.enabled).toBe(true);
    expect(lastCall?.fen).not.toBeNull();

    // (maiaEnabled=false, flawChessEnabled=true) — OR gating keeps it enabled.
    fireEvent.click(screen.getByTestId('btn-analysis-maia-toggle'));
    lastCall = gradingCalls[gradingCalls.length - 1];
    expect(lastCall?.enabled).toBe(true);
    expect(lastCall?.fen).not.toBeNull();

    // (maiaEnabled=false, flawChessEnabled=false) — both off, the run is
    // disabled; fen/enabled stay paired on the SAME condition (RESEARCH
    // Pitfall 5 — the worker must never be alive-but-positionless).
    fireEvent.click(screen.getByTestId('btn-analysis-flawchess-toggle'));
    lastCall = gradingCalls[gradingCalls.length - 1];
    expect(lastCall?.enabled).toBe(false);
    expect(lastCall?.fen).toBeNull();

    // (maiaEnabled=true, flawChessEnabled=false) — OR gating re-enables it.
    fireEvent.click(screen.getByTestId('btn-analysis-maia-toggle'));
    lastCall = gradingCalls[gradingCalls.length - 1];
    expect(lastCall?.enabled).toBe(true);
    expect(lastCall?.fen).not.toBeNull();
  });
});

describe('Reconciled eval provenance (Phase 158, SEED-087)', () => {
  it('a move graded by both the free run and the grading run displays the free-run value (SC1 precedence)', () => {
    engineState.isReady = true;
    engineState.pvLines = [{ moves: ['e2e4'], evalCp: 310, evalMate: null, depth: 18 }];
    // objectiveEvalCp seeded at 80 (the grading run's own value) to prove
    // reconciliation OVERRIDES the raw RankedLine field, not merely echoes it.
    flawChessState.rankedLines = [
      {
        rootMove: 'e2e4',
        practicalScore: 0.6,
        objectiveEvalCp: 80,
        objectiveEvalMate: null,
        modalPath: ['e2e4'],
        modalStats: [{ objectiveEvalCp: 80, objectiveEvalMate: null, maiaProb: 0.5 }],
        visits: 5,
      },
    ];
    gradingState.gradeMap = new Map([['e4', { evalCp: 80, evalMate: null, depth: 10 }]]);

    renderAnalysis();

    // The FC card's badge aria-label carries "objectively <cp>" — it must read
    // the free-run's +3.1, never the grading run's +0.8.
    const badge = screen.getByLabelText(/Line 1: practically/);
    expect(badge.getAttribute('aria-label')).toContain('objectively +3.1');
    expect(badge.getAttribute('aria-label')).not.toContain('objectively +0.8');
  });

  it("the verdict's FC-pick and SF-best evals both resolve through evalLookup, so a stale/inflated raw RankedLine eval never leaks through (SC4)", () => {
    engineState.isReady = true;
    engineState.pvLines = [{ moves: ['g1f3'], evalCp: 130, evalMate: null, depth: 18 }];
    // A deliberately inflated raw objectiveEvalCp (999) simulates the "Qc7
    // +2.8 vs O-O +1.3" bug class this phase fixes — reconciliation must
    // replace it with the shared grading run's own value (40) before it ever
    // reaches the verdict, making a FC-pick-exceeds-SF-best reading impossible.
    flawChessState.rankedLines = [
      {
        rootMove: 'e2e4',
        practicalScore: 0.55,
        objectiveEvalCp: 999,
        objectiveEvalMate: null,
        modalPath: ['e2e4'],
        modalStats: [{ objectiveEvalCp: 999, objectiveEvalMate: null, maiaProb: 0.5 }],
        visits: 5,
      },
    ];
    gradingState.gradeMap = new Map([['e4', { evalCp: 40, evalMate: null, depth: 10 }]]);

    renderAnalysis();

    const sentence = screen.getByTestId('flawchess-verdict-sentence');
    expect(sentence.textContent).toContain('+1.3');
    expect(sentence.textContent).toContain('+0.4');
    expect(sentence.textContent).not.toContain('+10.0');
  });
});
