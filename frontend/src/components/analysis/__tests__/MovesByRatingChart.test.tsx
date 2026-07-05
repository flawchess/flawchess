// @vitest-environment jsdom
/**
 * Phase 151.1 Plan 04 — MovesByRatingChart tests.
 *
 * Verifies the D-01/D-03/D-07 quality-coloring model: the chart renders exactly
 * the caller-selected `shownSans`, colors each line/label by its `qualityBySan`
 * bucket (ungraded → MOVE_QUALITY_PENDING, D-05), keeps stroke width decoupled
 * from color (played/best always emphasized regardless of quality color), and
 * the D-08 tooltip surfaces the quality word + white-POV eval alongside prob%.
 * Supersedes Phase 151 Plan 05's capMovesByPeak-based tests (that cap moved to
 * `selectCandidatesByMass` in Plan 02 and is computed upstream in Analysis.tsx).
 */

import { afterEach, beforeAll, describe, expect, it, vi } from 'vitest';
import { cleanup, render, screen } from '@testing-library/react';
import { cloneElement, isValidElement } from 'react';
import type { ReactElement } from 'react';

// Recharts' <ResponsiveContainer> measures its parent with ResizeObserver; in
// jsdom the parent has zero dimensions so the inner chart refuses to render.
// Stub it with a fixed-size wrapper (same pattern as
// EndgameClockDiffOverTimeChart.test.tsx / EndgameScoreOverTimeChart.test.tsx).
vi.mock('recharts', async () => {
  const actual = await vi.importActual<typeof import('recharts')>('recharts');
  return {
    ...actual,
    ResponsiveContainer: ({ children }: { children: ReactElement }) => (
      <div style={{ width: 800, height: 400 }}>
        {isValidElement(children)
          ? cloneElement(children as ReactElement<{ width?: number; height?: number }>, {
              width: 800,
              height: 400,
            })
          : children}
      </div>
    ),
  };
});

import { MovesByRatingChart, MovesByRatingTooltipContent } from '../MovesByRatingChart';
import type { MoveQualityEval } from '../MovesByRatingChart';
import type { MoveCurvePoint } from '@/hooks/useMaiaEngine';
import { MOVE_QUALITY_BLUNDER, MOVE_QUALITY_PENDING } from '@/lib/theme';

beforeAll(() => {
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
});

afterEach(() => {
  cleanup();
});

/**
 * Fixture with 6 candidate moves across 5 ELO rungs (mirrors spike 006's Ne4
 * example). `shownSans`/`qualityBySan` are supplied explicitly by the caller
 * (Analysis.tsx's selectCandidatesByMass + classifyMoveQuality) rather than
 * derived internally — this component no longer computes its own cap.
 */
function makePerElo(): MoveCurvePoint[] {
  const elos = [1100, 1300, 1500, 1700, 1900];
  const curves: Record<string, number[]> = {
    e4: [40, 45, 50, 48, 42],
    'O-O': [30, 38, 45, 40, 35],
    h3: [25, 30, 40, 35, 28],
    Qd2: [20, 25, 35, 30, 22],
    a3: [15, 20, 30, 25, 18],
    Ne4: [4, 6, 8, 5, 3],
  };
  return elos.map((elo, i) => ({
    elo,
    moveProbabilities: Object.fromEntries(
      Object.entries(curves).map(([san, vals]) => [san, (vals[i] ?? 0) / 100]),
    ),
  }));
}

const SHOWN_SANS = ['e4', 'O-O', 'h3', 'Qd2', 'a3', 'Ne4'];

function makeQualityBySan(): Map<string, MoveQualityEval> {
  return new Map<string, MoveQualityEval>([
    ['e4', { quality: 'good', evalCp: 30, evalMate: null }],
    ['O-O', { quality: 'best', evalCp: 45, evalMate: null }],
    ['h3', { quality: 'inaccuracy', evalCp: -10, evalMate: null }],
    ['Qd2', { quality: 'mistake', evalCp: -80, evalMate: null }],
    // Ne4 (played) is a blunder — verifies color/stroke decoupling: played stays
    // EMPHASIZED_STROKE_WIDTH even though colored red (D-01/D-07).
    ['Ne4', { quality: 'blunder', evalCp: -400, evalMate: null }],
    // a3 intentionally omitted — an ungraded SHOWN move must render PENDING (D-05).
  ]);
}

describe('MovesByRatingChart', () => {
  it('renders the container with data-testid="moves-by-rating-chart"', () => {
    render(
      <MovesByRatingChart
        perElo={makePerElo()}
        playedSan="Ne4"
        bestSan="O-O"
        selectedElo={1500}
        shownSans={SHOWN_SANS}
        engineTopLines={[]}
        qualityBySan={makeQualityBySan()}
      />,
    );
    expect(screen.getByTestId('moves-by-rating-chart')).toBeTruthy();
  });

  it('renders exactly one line per shownSans entry (no internal cap)', () => {
    const { container } = render(
      <MovesByRatingChart
        perElo={makePerElo()}
        playedSan="Ne4"
        bestSan="O-O"
        selectedElo={1500}
        shownSans={SHOWN_SANS}
        engineTopLines={[]}
        qualityBySan={makeQualityBySan()}
      />,
    );
    const lines = container.querySelectorAll('.recharts-line-curve');
    expect(lines.length).toBe(SHOWN_SANS.length);
  });

  it('colors a blunder-graded played move MOVE_QUALITY_BLUNDER while keeping the emphasized stroke width', () => {
    const { container } = render(
      <MovesByRatingChart
        perElo={makePerElo()}
        playedSan="Ne4"
        bestSan="O-O"
        selectedElo={1500}
        shownSans={SHOWN_SANS}
        engineTopLines={[]}
        qualityBySan={makeQualityBySan()}
      />,
    );
    const lines = container.querySelectorAll('.recharts-line-curve');
    const blunderLine = Array.from(lines).find(
      (el) => el.getAttribute('stroke') === MOVE_QUALITY_BLUNDER,
    );
    expect(blunderLine).toBeTruthy();
    // Played/best keep EMPHASIZED_STROKE_WIDTH (3) regardless of quality color.
    expect(blunderLine?.getAttribute('stroke-width')).toBe('3');
  });

  it('renders a non-emphasized shown move at OTHER_STROKE_WIDTH', () => {
    const { container } = render(
      <MovesByRatingChart
        perElo={makePerElo()}
        playedSan="Ne4"
        bestSan="O-O"
        selectedElo={1500}
        shownSans={SHOWN_SANS}
        engineTopLines={[]}
        qualityBySan={makeQualityBySan()}
      />,
    );
    const lines = container.querySelectorAll('.recharts-line-curve');
    const mutedLine = Array.from(lines).find((el) => el.getAttribute('stroke-width') === '1.5');
    expect(mutedLine).toBeTruthy();
  });

  it('renders an ungraded shown move (a3) with MOVE_QUALITY_PENDING', () => {
    const { container } = render(
      <MovesByRatingChart
        perElo={makePerElo()}
        playedSan="Ne4"
        bestSan="O-O"
        selectedElo={1500}
        shownSans={SHOWN_SANS}
        engineTopLines={[]}
        qualityBySan={makeQualityBySan()}
      />,
    );
    const lines = container.querySelectorAll('.recharts-line-curve');
    const pendingLine = Array.from(lines).find(
      (el) => el.getAttribute('stroke') === MOVE_QUALITY_PENDING,
    );
    expect(pendingLine).toBeTruthy();
  });

  it('renders the "you are here" reference line without a text label (151.1 UAT)', () => {
    render(
      <MovesByRatingChart
        perElo={makePerElo()}
        playedSan="Ne4"
        bestSan="O-O"
        selectedElo={1700}
        shownSans={SHOWN_SANS}
        engineTopLines={[]}
        qualityBySan={makeQualityBySan()}
      />,
    );
    // The "You: <elo>" label was removed; the dashed white marker line remains.
    expect(screen.queryByTestId('moves-by-rating-you-are-here-label')).toBeNull();
  });

  it('renders a fixed-height loading skeleton (still testid-bearing) when perElo is empty', () => {
    render(
      <MovesByRatingChart
        perElo={[]}
        playedSan={null}
        bestSan={null}
        selectedElo={1500}
        shownSans={[]}
        engineTopLines={[]}
        qualityBySan={new Map()}
      />,
    );
    const el = screen.getByTestId('moves-by-rating-chart');
    expect(el).toBeTruthy();
    // Pulsing placeholder keeps the card height constant until Maia is ready.
    expect(screen.getByTestId('moves-by-rating-chart-skeleton')).toBeTruthy();
    // The waiting text is kept (sr-only) for screen readers.
    expect(el.textContent).toMatch(/Waiting/i);
  });
});

describe('MovesByRatingTooltipContent (D-08)', () => {
  it('shows the quality word, white-POV eval, and prob% for a graded blunder row', () => {
    render(
      <MovesByRatingTooltipContent
        label={1500}
        rows={[{ san: 'Ne4', probability: 0.08, color: MOVE_QUALITY_BLUNDER }]}
        playedSan="Ne4"
        engineTopLines={[]}
        qualityBySan={makeQualityBySan()}
      />,
    );
    const row = screen.getByTestId('moves-by-rating-tooltip-row-Ne4');
    expect(row.textContent).toBe('Ne4 · played: Blunder · -4.0 · 8%');
  });

  it('shows a positive cp eval with a leading + sign and no redundant suffix for the best move', () => {
    render(
      <MovesByRatingTooltipContent
        label={1500}
        rows={[{ san: 'O-O', probability: 0.45, color: 'oklch(0.4 0.17 145)' }]}
        playedSan="Ne4"
        engineTopLines={[]}
        qualityBySan={makeQualityBySan()}
      />,
    );
    const row = screen.getByTestId('moves-by-rating-tooltip-row-O-O');
    // 151.1 UAT: the "Best" quality word already marks it best — no "· best" suffix.
    expect(row.textContent).toBe('O-O: Best · +0.5 · 45%');
  });

  it('renders "Pending" and an em dash for an ungraded shown move', () => {
    render(
      <MovesByRatingTooltipContent
        label={1500}
        rows={[{ san: 'a3', probability: 0.3 }]}
        playedSan="Ne4"
        engineTopLines={[]}
        qualityBySan={makeQualityBySan()}
      />,
    );
    const row = screen.getByTestId('moves-by-rating-tooltip-row-a3');
    expect(row.textContent).toBe('a3: Pending · — · 30%');
  });

  it('formats a mate score as "#N"', () => {
    const qualityBySan = new Map<string, MoveQualityEval>([
      ['Qh7', { quality: 'best', evalCp: null, evalMate: 3 }],
    ]);
    render(
      <MovesByRatingTooltipContent
        label={1500}
        rows={[{ san: 'Qh7', probability: 0.9 }]}
        playedSan={null}
        engineTopLines={[]}
        qualityBySan={qualityBySan}
      />,
    );
    const row = screen.getByTestId('moves-by-rating-tooltip-row-Qh7');
    expect(row.textContent).toBe('Qh7: Best · #3 · 90%');
  });

  it('renders the primary engine top-2 lines as a reference header (151.1 UAT)', () => {
    render(
      <MovesByRatingTooltipContent
        label={2400}
        rows={[{ san: 'Nf6', probability: 0.42 }]}
        playedSan={null}
        engineTopLines={[
          { san: 'Nf6', evalCp: 30, evalMate: null },
          { san: 'd5', evalCp: 25, evalMate: null },
        ]}
        qualityBySan={new Map([['Nf6', { quality: 'best', evalCp: 30, evalMate: null }]])}
      />,
    );
    const engine = screen.getByTestId('moves-by-rating-tooltip-engine');
    expect(engine.textContent).toBe('Engine: Nf6 +0.3 · d5 +0.3');
  });

  it('omits the engine reference header when no engine lines are available', () => {
    render(
      <MovesByRatingTooltipContent
        label={2400}
        rows={[{ san: 'Nf6', probability: 0.42 }]}
        playedSan={null}
        engineTopLines={[]}
        qualityBySan={new Map([['Nf6', { quality: 'best', evalCp: 30, evalMate: null }]])}
      />,
    );
    expect(screen.queryByTestId('moves-by-rating-tooltip-engine')).toBeNull();
  });
});
