// @vitest-environment jsdom
/**
 * Tests for MostPlayedOpeningsTable Phase 80 columns:
 * - Desktop columns: MG eval text | MG bullet | MG conf | clock-diff
 * - Mobile MG-entry line (eval text + bullet + pill + clock-diff)
 * - InfoPopovers with D-10 tooltip wording
 */
import { describe, it, expect, vi, afterEach } from 'vitest';
import { render, cleanup } from '@testing-library/react';
import type { ReactNode } from 'react';
import type { OpeningWDL } from '@/types/stats';
import {
  MostPlayedOpeningsTable,
  MG_EVAL_HEADER_TOOLTIP,
} from '../MostPlayedOpeningsTable';
import { formatSignedEvalPawns } from '@/lib/clockFormat';

afterEach(() => {
  cleanup();
});

// Mock Tooltip so tests don't require TooltipProvider
vi.mock('@/components/ui/tooltip', () => ({
  Tooltip: ({ children }: { children: ReactNode }) => <>{children}</>,
  TooltipProvider: ({ children }: { children: ReactNode }) => <>{children}</>,
}));

// Mock MinimapPopover — not under test
vi.mock('@/components/stats/MinimapPopover', () => ({
  MinimapPopover: ({ children }: { children: ReactNode }) => <>{children}</>,
}));

// Mock ConfidencePill to simplify assertions
vi.mock('@/components/insights/ConfidencePill', () => ({
  ConfidencePill: ({ level, testId }: { level: string; testId?: string }) => (
    <span data-testid={testId}>{level}</span>
  ),
}));

// Mock MiniBulletChart so tests don't need canvas/SVG env
vi.mock('@/components/charts/MiniBulletChart', () => ({
  MiniBulletChart: ({ ariaLabel }: { ariaLabel?: string }) => (
    <div data-testid="mini-bullet-chart" aria-label={ariaLabel}>
      <div data-testid="mini-bullet-whisker" />
    </div>
  ),
}));

// Mock InfoPopover — renders children inline for easy text assertions
vi.mock('@/components/ui/info-popover', () => ({
  InfoPopover: ({
    children,
    testId,
  }: {
    children: ReactNode;
    testId?: string;
    ariaLabel?: string;
  }) => (
    <span data-testid={testId}>
      {children}
    </span>
  ),
}));

/** Build a fully-typed OpeningWDL row with sensible defaults. Override per test. */
function _makeRow(overrides: Partial<OpeningWDL> = {}): OpeningWDL {
  return {
    opening_eco: 'A00',
    opening_name: 'Test Opening',
    display_name: 'Test Opening',
    label: 'Test Opening (A00)',
    pgn: '1. e4 e5',
    fen: 'rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1',
    full_hash: '12345',
    wins: 10,
    draws: 5,
    losses: 5,
    total: 20,
    win_pct: 50,
    draw_pct: 25,
    loss_pct: 25,
    // MG fields — default to zero-data state
    eval_n: 0,
    eval_confidence: 'low',
    clock_diff_n: 0,
    ...overrides,
  };
}

const noop = () => {};
const TEST_PREFIX = 'most-played';

function renderTable(rows: OpeningWDL[]) {
  return render(
    <MostPlayedOpeningsTable
      openings={rows}
      color="white"
      testIdPrefix={TEST_PREFIX}
      onOpenGames={noop}
      showAll={true}
    />,
  );
}

describe('formatSignedEvalPawns', () => {
  it('positive value gets a leading +', () => {
    expect(formatSignedEvalPawns(2.13)).toBe('+2.1');
  });

  it('negative value keeps the minus sign', () => {
    expect(formatSignedEvalPawns(-0.47)).toBe('-0.5');
  });

  it('zero is rendered as +0.0', () => {
    expect(formatSignedEvalPawns(0)).toBe('+0.0');
  });
});

describe('MostPlayedOpeningsTable — Phase 80 desktop columns', () => {
  it('renders MG eval text cell with signed one-decimal value', () => {
    const row = _makeRow({
      avg_eval_pawns: 2.13,
      eval_n: 20,
      eval_confidence: 'high',
    });
    renderTable([row]);
    const rowKey = row.opening_eco;
    const cell = document.querySelector(`[data-testid="${TEST_PREFIX}-eval-text-${rowKey}"]`);
    expect(cell).not.toBeNull();
    expect(cell?.textContent).toBe('+2.1');
  });

  it('renders MG bullet chart cell when avg_eval_pawns provided', () => {
    const row = _makeRow({
      avg_eval_pawns: 0.3,
      eval_ci_low_pawns: 0.1,
      eval_ci_high_pawns: 0.5,
      eval_n: 20,
      eval_confidence: 'high',
    });
    renderTable([row]);
    const rowKey = row.opening_eco;
    const cellEl = document.querySelector(`[data-testid="${TEST_PREFIX}-bullet-${rowKey}"]`);
    expect(cellEl).not.toBeNull();
    expect(cellEl?.querySelector('[data-testid="mini-bullet-chart"]')).not.toBeNull();
  });

  it('renders MG confidence pill with eval_confidence level', () => {
    const row = _makeRow({
      avg_eval_pawns: 0.3,
      eval_n: 20,
      eval_confidence: 'high',
    });
    renderTable([row]);
    const rowKey = row.opening_eco;
    const el = document.querySelector(`[data-testid="${TEST_PREFIX}-confidence-${rowKey}"]`);
    expect(el).not.toBeNull();
    expect(el?.textContent).toBe('high');
  });

  it('renders clock-diff cell with formatted text', () => {
    const row = _makeRow({
      avg_clock_diff_pct: 8.2,
      avg_clock_diff_seconds: 24,
      clock_diff_n: 20,
    });
    renderTable([row]);
    const rowKey = row.opening_eco;
    const cell = document.querySelector(`[data-testid="${TEST_PREFIX}-clock-diff-${rowKey}"]`);
    expect(cell).not.toBeNull();
    expect(cell?.textContent).toContain('+8.2%');
    expect(cell?.textContent).toContain('+24s');
  });

  it('eval_n === 0 renders em-dash for both MG eval text and bullet chart', () => {
    const row = _makeRow({ eval_n: 0 });
    renderTable([row]);
    const rowKey = row.opening_eco;
    const text = document.querySelector(`[data-testid="${TEST_PREFIX}-eval-text-${rowKey}"]`);
    const bullet = document.querySelector(`[data-testid="${TEST_PREFIX}-bullet-${rowKey}"]`);
    expect(text?.textContent).toBe('—');
    expect(bullet?.textContent).toBe('—');
    expect(bullet?.querySelector('[data-testid="mini-bullet-chart"]')).toBeNull();
  });

  it('eval_confidence === low dims MG cells even with n >= 10', () => {
    const row = _makeRow({
      avg_eval_pawns: 0.1,
      eval_n: 15,
      eval_confidence: 'low',
    });
    renderTable([row]);
    const rowKey = row.opening_eco;
    const text = document.querySelector(`[data-testid="${TEST_PREFIX}-eval-text-${rowKey}"]`) as HTMLElement | null;
    const bullet = document.querySelector(`[data-testid="${TEST_PREFIX}-bullet-${rowKey}"]`) as HTMLElement | null;
    expect(text?.style.opacity).toBe('0.5');
    expect(bullet?.style.opacity).toBe('0.5');
  });
});

describe('MostPlayedOpeningsTable — mobile stacked lines (D-06)', () => {
  it('mobile MG-entry line is present with grid-cols class and MG entry label', () => {
    const row = _makeRow({
      eval_n: 15,
      eval_confidence: 'medium',
      avg_eval_pawns: 0.2,
    });
    renderTable([row]);
    const rowKey = row.opening_eco;
    const line = document.querySelector(`[data-testid="${TEST_PREFIX}-mobile-mg-line-${rowKey}"]`);
    expect(line).not.toBeNull();
    expect(line?.className).toMatch(/sm:hidden/);
    expect(line?.textContent).toContain('MG entry');
  });

  it('mobile MG line includes eval text', () => {
    const row = _makeRow({
      eval_n: 15,
      eval_confidence: 'medium',
      avg_eval_pawns: 1.4,
    });
    renderTable([row]);
    const rowKey = row.opening_eco;
    const cell = document.querySelector(`[data-testid="${TEST_PREFIX}-eval-text-mobile-${rowKey}"]`);
    expect(cell?.textContent).toBe('+1.4');
  });
});

describe('MostPlayedOpeningsTable — empty/null data fallbacks', () => {
  it('clock_diff_n === 0 renders em-dash for clock-diff cell', () => {
    const row = _makeRow({ clock_diff_n: 0 });
    renderTable([row]);
    const rowKey = row.opening_eco;
    const cell = document.querySelector(`[data-testid="${TEST_PREFIX}-clock-diff-${rowKey}"]`);
    expect(cell).not.toBeNull();
    expect(cell?.textContent).toBe('—');
  });
});

describe('MostPlayedOpeningsTable — D-10 column header tooltips', () => {
  it('MG eval column header tooltip contains "across analyzed games"', () => {
    const row = _makeRow();
    renderTable([row]);
    const popover = document.querySelector('[data-testid="opening-stats-mg-eval-info"]');
    expect(popover).not.toBeNull();
    expect(popover?.textContent).toContain('across analyzed games');
  });

  it('MG_EVAL_HEADER_TOOLTIP constant is exported and well-formed', () => {
    expect(MG_EVAL_HEADER_TOOLTIP).toContain('across analyzed games');
  });

  it('all column-header InfoPopovers are present in DOM', () => {
    const row = _makeRow();
    renderTable([row]);
    expect(document.querySelector('[data-testid="opening-stats-mg-eval-text-info"]')).not.toBeNull();
    expect(document.querySelector('[data-testid="opening-stats-mg-eval-info"]')).not.toBeNull();
    expect(document.querySelector('[data-testid="opening-stats-mg-confidence-info"]')).not.toBeNull();
    expect(document.querySelector('[data-testid="opening-stats-clock-diff-info"]')).not.toBeNull();
  });
});

describe('MostPlayedOpeningsTable — bookmarked openings reuse', () => {
  it('bookmarked-openings reuse gets all MG columns automatically', () => {
    const row = _makeRow({
      avg_eval_pawns: 0.3,
      eval_n: 20,
      eval_confidence: 'high',
      avg_clock_diff_pct: 5.0,
      avg_clock_diff_seconds: 12,
      clock_diff_n: 20,
    });
    render(
      <MostPlayedOpeningsTable
        openings={[row]}
        color="white"
        testIdPrefix="bookmarked"
        onOpenGames={noop}
        showAll={true}
      />,
    );
    const rowKey = row.opening_eco;
    expect(document.querySelector(`[data-testid="bookmarked-eval-text-${rowKey}"]`)).not.toBeNull();
    expect(document.querySelector(`[data-testid="bookmarked-bullet-${rowKey}"]`)).not.toBeNull();
    expect(document.querySelector(`[data-testid="bookmarked-confidence-${rowKey}"]`)).not.toBeNull();
    expect(document.querySelector(`[data-testid="bookmarked-clock-diff-${rowKey}"]`)).not.toBeNull();
  });
});
