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
import { BEST_MOVE_ARROW } from '@/lib/theme';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { TooltipProvider } from '@/components/ui/tooltip';
import type { GameFlawCard } from '@/types/library';

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
  /** Retained grading PV (162 UAT card re-source) — optional, mirrors MoveGrade. */
  pv?: string[];
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
// `perElo` defaults to [] (no move-quality-bar/position-verdict rendering);
// Phase 162's mirror-image label test overrides it with a single rung so
// MaiaMoveQualityBar's totalMass > 0 gate lets computePositionVerdict run.
const maiaState: {
  expectedScoreAtSelectedElo: number | null;
  perElo: { elo: number; moveProbabilities: Record<string, number> }[];
} = {
  expectedScoreAtSelectedElo: null,
  perElo: [],
};

vi.mock('@/hooks/useMaiaEngine', () => ({
  useMaiaEngine: () => ({
    perElo: maiaState.perElo,
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
// params, so both default to empty stubs — no real network needed. Phase 161 D-04's
// tags-relocation test opts into game mode by setting libraryGameState.data before
// rendering with a `?game_id=` param.
const libraryGameState: { data: GameFlawCard | undefined } = { data: undefined };
vi.mock('@/hooks/useLibrary', () => ({
  useTacticLines: () => ({ data: undefined, isFetching: false, isError: false }),
  useLibraryGame: () => ({ data: libraryGameState.data, isError: false }),
}));

// Mock useFlawFilterStore: Analysis.tsx calls this unconditionally for tactic
// visibility, and (Phase 161 D-04 test) SeverityBadge — rendered inside
// AnalysisTagsPanel, now exercised for the first time in this file — also calls
// the hook directly and reads `flawFilter.severity` without a null guard. A
// realistic DEFAULT_FLAW_FILTER-shaped object (not null) is required for any
// game-mode render, not just the D-04 test (Rule 3 — the game-mode path was
// previously unexercised, so this null default worked by chance until now).
vi.mock('@/hooks/useFlawFilterStore', () => ({
  useFlawFilterStore: () => [
    { severity: [], tags: [], tacticFamilies: [], tacticOrientation: 'either', tacticDepthMin: 0, tacticDepthMax: 11 },
    vi.fn(),
  ],
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

// jsdom has no scrollIntoView implementation. Only reached in game mode (the D-04
// test below renders game_id=1 for the first time in this file), where
// HorizontalMoveList's active-move effect calls it unconditionally.
if (typeof Element.prototype.scrollIntoView !== 'function') {
  Element.prototype.scrollIntoView = vi.fn();
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
  maiaState.perElo = [];
  flawChessState.rankedLines = [];
  flawChessState.isSearching = false;
  flawChessState.isReady = true;
  gradingState.gradeMap = new Map();
  gradingCalls.length = 0;
  libraryGameState.data = undefined;
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

  it('excludes the free run\'s top-2 root SANs from the grading union while it is still analyzing, and includes them once it has committed (Phase 162 D-02/D-09)', () => {
    // Mid-search: pvLines empty (cleared on FEN change), isAnalyzing true —
    // freeRunCommitted must be false, so the free run contributes nothing.
    engineState.isReady = true;
    engineState.isAnalyzing = true;
    engineState.pvLines = [];

    renderAnalysis();

    let lastCall = gradingCalls[gradingCalls.length - 1];
    expect(lastCall?.candidateSans).not.toContain('Nf3');
    expect(lastCall?.candidateSans).not.toContain('e4');

    // Committed: pvLines populated AND isAnalyzing false — the free run's
    // top-2 root SANs (g1f3 -> Nf3, e2e4 -> e4) must now join the union.
    // Toggling an unrelated switch forces the re-render that re-reads the
    // mutable engineState (the mock is not itself reactive React state).
    engineState.isAnalyzing = false;
    engineState.pvLines = [
      { moves: ['g1f3'], evalCp: 30, evalMate: null, depth: 18 },
      { moves: ['e2e4'], evalCp: 25, evalMate: null, depth: 18 },
    ];

    fireEvent.click(screen.getByTestId('btn-analysis-maia-toggle'));

    lastCall = gradingCalls[gradingCalls.length - 1];
    expect(lastCall?.candidateSans).toContain('Nf3');
    expect(lastCall?.candidateSans).toContain('e4');
  });
});

describe('Reconciled eval provenance (Phase 158, SEED-087)', () => {
  it('a move graded by both the free run and the grading run displays the grading value (Phase 162 D-01 grading-first precedence)', () => {
    // Rule 1 fix: this test previously asserted free-run-first precedence
    // (Phase 158 SC1). 162-01 flipped buildEvalLookup to grading-first, so a
    // move graded by BOTH sources must now resolve to the grading (deeper,
    // depth-parity) value, not the free run's shallower placeholder.
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

    // The FC card's badge aria-label carries "objectively <cp>" — under
    // grading-first precedence it must read the grading run's +0.8, never
    // the free run's shallower +3.1.
    const badge = screen.getByLabelText(/Line 1: practically/);
    expect(badge.getAttribute('aria-label')).toContain('objectively +0.8');
    expect(badge.getAttribute('aria-label')).not.toContain('objectively +3.1');
  });

  it('mirror-image label case: a non-bestSan move with the strictly higher reconciled eval becomes the chart\'s Best, and the free-run bestSan is demoted (Phase 162 D-03)', () => {
    // Free run's own pick is e4 (bestSan) — the OLD pin this phase replaces.
    engineState.isReady = true;
    engineState.pvLines = [{ moves: ['e2e4'], evalCp: 20, evalMate: null, depth: 18 }];
    // The grading run grades BOTH e4 and Nf3, with Nf3 (NOT the free-run
    // bestSan) resolving to the strictly higher reconciled eval — the exact
    // mirror-image scenario this phase's reconciledBestUci pin fixes.
    gradingState.gradeMap = new Map([
      ['e4', { evalCp: 20, evalMate: null, depth: 10 }],
      ['Nf3', { evalCp: 300, evalMate: null, depth: 10 }],
    ]);
    // A single Maia rung with both SANs present (any elo — nearestByElo picks
    // this single rung regardless of the selected ELO default) so
    // MaiaMoveQualityBar's totalMass > 0 gate lets computePositionVerdict run
    // and shownSans (selectCandidatesByMass) includes both candidates.
    maiaState.perElo = [{ elo: 1500, moveProbabilities: { e4: 0.3, Nf3: 0.7 } }];

    renderAnalysis();

    // qualityBySan's designatedBestSan is now the reconciled argmax's SAN
    // (Nf3, cp 300) — NOT the free-run bestSan (e4, cp 20) — so the position
    // verdict's prose names Nf3 as the accurate/best move and demotes e4 to
    // "objectively looser" (a non-best label), never the reverse.
    const verdictEls = screen.getAllByTestId('maia-position-verdict');
    expect(verdictEls.length).toBeGreaterThan(0);
    const text = verdictEls[0]!.textContent ?? '';
    expect(text).toContain('Nf3');
    expect(text).toContain('accurate move');
    expect(text).toContain('e4');
    expect(text).toContain('objectively looser');
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
    // Rule 1 fix (Phase 162 D-13): the SF side is now the reconciled global
    // argmax (`reconciledBestUci`), not raw `engine.pvLines[0]` — so the free
    // run's own top pick (Nf3/g1f3) must ALSO be graded here (matching its own
    // eval, 130) for the verdict to still name it as the SF side. Without this
    // second entry, e4 (the only graded candidate) would win the reconciled
    // argmax instead, which is correct D-12 behavior but not what THIS test
    // (evalLookup resolution, not argmax selection) is proving.
    gradingState.gradeMap = new Map([
      ['e4', { evalCp: 40, evalMate: null, depth: 10 }],
      ['Nf3', { evalCp: 130, evalMate: null, depth: 10 }],
    ]);

    renderAnalysis();

    const sentence = screen.getByTestId('flawchess-verdict-sentence');
    expect(sentence.textContent).toContain('+1.3');
    expect(sentence.textContent).toContain('+0.4');
    expect(sentence.textContent).not.toContain('+10.0');
  });

  it("shows the grading (reconciled) value for the verdict's Stockfish side even when the SAME move is graded differently by the two sources (Phase 162 D-13 provenance)", () => {
    // RESEARCH Pitfall 1: `stockfishLine` used to be raw `engine.pvLines[0]`,
    // bypassing evalLookup entirely — a coverage gap even under the OLD
    // free-run-first precedence, since this call site never went through the
    // lookup at all. Both sources grade the SAME move (e4): the free run's
    // shallower +2.0, the grading run's deeper (and now authoritative) +0.8.
    engineState.isReady = true;
    engineState.pvLines = [{ moves: ['e2e4'], evalCp: 200, evalMate: null, depth: 18 }];
    flawChessState.rankedLines = [
      {
        rootMove: 'e2e4',
        practicalScore: 0.6,
        objectiveEvalCp: 200,
        objectiveEvalMate: null,
        modalPath: ['e2e4'],
        modalStats: [{ objectiveEvalCp: 200, objectiveEvalMate: null, maiaProb: 0.5 }],
        visits: 5,
      },
    ];
    gradingState.gradeMap = new Map([['e4', { evalCp: 80, evalMate: null, depth: 10 }]]);

    renderAnalysis();

    // Aligned tier (FC and SF both play e4) — the sentence cites ONE eval for
    // the shared pick. It must be the reconciled grading value (+0.8), never
    // the stale free-run value (+2.0) a raw engine.pvLines[0] read would show.
    const sentence = screen.getByTestId('flawchess-verdict-sentence');
    expect(sentence.textContent).toContain('+0.8');
    expect(sentence.textContent).not.toContain('+2.0');
  });

  it("the Stockfish card's line 1 IS the reconciled global argmax — with the grading run's own PV — even when the free run never searched that move (162 UAT card re-source, supersedes D-12's accepted edge case)", () => {
    // The UAT screenshot shape: the free run's own top pick (e4-analog for
    // Rad1) is outranked by a grading-union candidate (Nf3-analog for Bc1)
    // that never appears in engine.pvLines. Pre-fix the card kept showing the
    // free run's own 2 lines; now it lists the reconciled top-2 so the card,
    // arrow, chart crown, and verdict all name the same best move.
    engineState.isReady = true;
    engineState.depth = 18;
    engineState.pvLines = [{ moves: ['e2e4', 'e7e5'], evalCp: 20, evalMate: null, depth: 18 }];
    gradingState.gradeMap = new Map([
      ['e4', { evalCp: 20, evalMate: null, depth: 22, pv: ['e2e4', 'e7e5'] }],
      ['Nf3', { evalCp: 300, evalMate: null, depth: 22, pv: ['g1f3', 'b8c6'] }],
    ]);

    renderAnalysis();

    // Line 1's first chip renders the grading PV's root move (Nf3), not the
    // free run's e4; its badge carries the grading eval.
    expect(screen.getByTestId('engine-line-0-move-0').textContent).toBe('Nf3');
    expect(screen.getByLabelText('Line 1: +3.0')).toBeTruthy();
    // The grading PV's continuation renders too (retained pv, not a bare root).
    expect(screen.getByTestId('engine-line-0-move-1').textContent).toBe('Nc6');
    // The demoted free-run pick is line 2 with ITS reconciled eval.
    expect(screen.getByTestId('engine-line-1-move-0').textContent).toBe('e4');
    expect(screen.getByLabelText('Line 2: +0.2')).toBeTruthy();
    // Headline depth now describes line 1's own grade (162 UAT supersedes
    // D-05), not the free run's shallower search.
    expect(screen.getByTestId('analysis-engine-info').textContent).toContain('Depth 22');
  });

  it('the sf-0 board arrow follows the reconciled-argmax square, not the free run\'s own pick, when a Maia/FC-only candidate is the global argmax (D-12)', () => {
    // jsdom performs no real layout — clientWidth defaults to 0, which makes
    // ChessBoard's ArrowOverlay compute degenerate (NaN) zero-length SVG
    // paths. Stub a nonzero measured width so the overlay's geometry is real
    // and two different target squares produce two different `d` strings.
    const clientWidthSpy = vi.spyOn(Element.prototype, 'clientWidth', 'get').mockReturnValue(400);

    const captureSfArrowPath = (): string | null => {
      const overlay = document.querySelector('[data-testid="arrow-overlay"]');
      const sfPath = overlay?.querySelector(`path[fill="${BEST_MOVE_ARROW}"]`);
      return sfPath?.getAttribute('d') ?? null;
    };

    try {
      // Baseline: no grading data yet — reconciledBestUci is null, so the
      // arrow falls back to the free run's own top pick (e2e4).
      engineState.isReady = true;
      engineState.pvLines = [{ moves: ['e2e4'], evalCp: 20, evalMate: null, depth: 18 }];
      const { unmount } = renderAnalysis();
      const baselinePath = captureSfArrowPath();
      expect(baselinePath).not.toBeNull();
      unmount();

      // Grading lands: Nf3 (an FC/Maia-only candidate that never appears in
      // engine.pvLines) resolves to the strictly higher reconciled eval — the
      // exact D-12 scenario the arrow must follow, not the free run's e4.
      gradingState.gradeMap = new Map([
        ['e4', { evalCp: 20, evalMate: null, depth: 10 }],
        ['Nf3', { evalCp: 300, evalMate: null, depth: 10 }],
      ]);
      renderAnalysis();
      const reconciledPath = captureSfArrowPath();
      expect(reconciledPath).not.toBeNull();
      expect(reconciledPath).not.toBe(baselinePath);
    } finally {
      clientWidthSpy.mockRestore();
    }
  });
});

// Phase 161 (SEED-088), D-04 — structural-only coverage: jsdom performs no real CSS
// layout, so the 100dvh lock / breakpoint switching / board height-aware sizing are
// HUMAN-UAT only (161-RESEARCH.md Validation Architecture). What IS testable here is
// the JSX reorder itself: AnalysisTagsPanel must render in the RIGHT column, after
// the engine card and move list, not in its old home under the eval chart.
function buildGame(overrides: Partial<GameFlawCard> = {}): GameFlawCard {
  return {
    game_id: 1,
    user_result: 'win',
    played_at: null,
    time_control_bucket: null,
    platform: 'chess.com',
    platform_url: null,
    white_username: 'alice',
    black_username: 'bob',
    white_rating: null,
    black_rating: null,
    opening_name: null,
    opening_eco: null,
    user_color: 'white',
    ply_count: 1,
    termination: null,
    time_control_str: null,
    result_fen: null,
    severity_counts: { inaccuracy: 0, mistake: 0, blunder: 0 },
    chips: [],
    analysis_state: 'analyzed',
    // Non-null on all four — the exact evalChartReady gate Analysis.tsx checks
    // before mounting AnalysisTagsPanel/EvalChart.
    eval_series: [
      { ply: 0, es: 0.5, eval_cp: 20, eval_mate: null, clock_seconds: null, move_seconds: null, best_move: null },
      { ply: 1, es: 0.52, eval_cp: 25, eval_mate: null, clock_seconds: null, move_seconds: null, best_move: null },
    ],
    // AnalysisTagsPanel.tsx returns null when analysis_state !== 'analyzed' OR
    // flaw_markers is empty — at least one marker is required to actually mount it.
    flaw_markers: [
      {
        ply: 0,
        severity: 'inaccuracy',
        tags: [],
        is_user: true,
        move_san: 'e4',
        allowed_tactic_motif: null,
        allowed_tactic_confidence: null,
        allowed_tactic_depth: null,
        missed_tactic_motif: null,
        missed_tactic_confidence: null,
        missed_tactic_depth: null,
      },
    ],
    phase_transitions: { middlegame_ply: null, endgame_ply: null },
    moves: ['e4'],
    active_eval_status: null,
    ...overrides,
  };
}

describe('Analysis desktop layout (Phase 161, SEED-088)', () => {
  it('renders AnalysisTagsPanel in the right column, after the engine card and move list (D-04)', () => {
    libraryGameState.data = buildGame();

    renderAnalysis('/analysis?game_id=1');

    const engineCard = screen.getByTestId('analysis-engine-card');
    const tagsPanel = screen.getByTestId('analysis-tags-panel');

    // DOCUMENT_POSITION_FOLLOWING: tagsPanel comes AFTER the engine card in the DOM
    // (same compareDocumentPosition pattern as the D-01 FlawChess-card-order test
    // above) — proving the relocation out of the board column and into the right
    // column, appended after boardControls().
    const tagsFollowEngineCard =
      engineCard.compareDocumentPosition(tagsPanel) & Node.DOCUMENT_POSITION_FOLLOWING;
    expect(tagsFollowEngineCard).toBeTruthy();
  });

  it('carries the desk3col 3-column grid-cols class on the grid row (D-03)', () => {
    renderAnalysis();

    // Traverse from a stable desktop-tree anchor up to the grid row rather than
    // adding a new testid purely for this assertion — analysis-human-column's
    // parent IS the grid row per the current DOM structure.
    const humanColumn = screen.getByTestId('analysis-human-column');
    const gridRow = humanColumn.parentElement;
    expect(gridRow?.className).toContain('desk3col:grid-cols-[360px_1fr_360px]');
  });
});
