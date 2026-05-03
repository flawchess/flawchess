// @vitest-environment jsdom
/**
 * Tests for MostPlayedOpeningsTable Phase 80 additions:
 * - 5 new desktop columns: MG bullet | MG pill | clock-diff | EG bullet | EG pill
 * - 2 new mobile lines: MG triple (line 2) + EG pair (line 3)
 * - InfoPopovers with D-10 tooltip wording
 */
import { describe, it, expect, vi, afterEach } from 'vitest';
import { render, cleanup } from '@testing-library/react';
import type { ReactNode } from 'react';
import type { OpeningWDL } from '@/types/stats';
import { MostPlayedOpeningsTable } from '../MostPlayedOpeningsTable';
import {
  MG_EVAL_HEADER_TOOLTIP,
  EG_EVAL_HEADER_TOOLTIP,
} from '../MostPlayedOpeningsTable';

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
    // EG fields — default to zero-data state
    eval_endgame_n: 0,
    eval_endgame_confidence: 'low',
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

describe('MostPlayedOpeningsTable — Phase 80 desktop columns', () => {
  it('Test 1: renders MG bullet chart cell when avg_eval_pawns provided', () => {
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
    // MiniBulletChart mock renders with testid mini-bullet-chart
    expect(cellEl?.querySelector('[data-testid="mini-bullet-chart"]')).not.toBeNull();
  });

  it('Test 2: renders MG confidence pill with eval_confidence level', () => {
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

  it('Test 3: renders clock-diff cell with formatted text', () => {
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

  it('Test 4: renders EG bullet chart cell when avg_eval_endgame_entry_pawns provided', () => {
    const row = _makeRow({
      avg_eval_endgame_entry_pawns: 1.5,
      eval_endgame_ci_low_pawns: 1.0,
      eval_endgame_ci_high_pawns: 2.0,
      eval_endgame_n: 25,
      eval_endgame_confidence: 'medium',
    });
    renderTable([row]);
    const rowKey = row.opening_eco;
    const cellEl = document.querySelector(`[data-testid="${TEST_PREFIX}-eg-bullet-${rowKey}"]`);
    expect(cellEl).not.toBeNull();
    expect(cellEl?.querySelector('[data-testid="mini-bullet-chart"]')).not.toBeNull();
  });

  it('Test 5: renders EG confidence pill with eval_endgame_confidence level', () => {
    const row = _makeRow({
      avg_eval_endgame_entry_pawns: 1.5,
      eval_endgame_n: 25,
      eval_endgame_confidence: 'medium',
    });
    renderTable([row]);
    const rowKey = row.opening_eco;
    const el = document.querySelector(`[data-testid="${TEST_PREFIX}-eg-confidence-${rowKey}"]`);
    expect(el).not.toBeNull();
    expect(el?.textContent).toBe('medium');
  });

  it('Test 6: eval_n === 0 renders em-dash instead of MG bullet chart', () => {
    const row = _makeRow({ eval_n: 0 });
    renderTable([row]);
    const rowKey = row.opening_eco;
    const cell = document.querySelector(`[data-testid="${TEST_PREFIX}-bullet-${rowKey}"]`);
    expect(cell).not.toBeNull();
    expect(cell?.textContent).toBe('—');
    expect(cell?.querySelector('[data-testid="mini-bullet-chart"]')).toBeNull();
  });

  it('Test 7: eval_endgame_n === 0 renders em-dash instead of EG bullet chart', () => {
    const row = _makeRow({ eval_endgame_n: 0 });
    renderTable([row]);
    const rowKey = row.opening_eco;
    const cell = document.querySelector(`[data-testid="${TEST_PREFIX}-eg-bullet-${rowKey}"]`);
    expect(cell).not.toBeNull();
    expect(cell?.textContent).toBe('—');
    expect(cell?.querySelector('[data-testid="mini-bullet-chart"]')).toBeNull();
  });

  it('Test 8: MG and EG bullet cells dim independently based on their own gates', () => {
    const row = _makeRow({
      avg_eval_pawns: 0.3,
      eval_n: 20,
      eval_confidence: 'high',   // MG reliable
      avg_eval_endgame_entry_pawns: 0.5,
      eval_endgame_n: 5,
      eval_endgame_confidence: 'low',  // EG unreliable
    });
    renderTable([row]);
    const rowKey = row.opening_eco;
    const mgCell = document.querySelector(`[data-testid="${TEST_PREFIX}-bullet-${rowKey}"]`) as HTMLElement | null;
    const egCell = document.querySelector(`[data-testid="${TEST_PREFIX}-eg-bullet-${rowKey}"]`) as HTMLElement | null;
    // MG: reliable — should NOT be dimmed
    expect(mgCell?.style.opacity ?? '').toBe('');
    // EG: unreliable — should be dimmed (opacity = 0.5)
    expect(egCell?.style.opacity).toBe('0.5');
  });

  it('Test 9: eval_confidence === low dims the MG bullet cell even with n >= 10', () => {
    const row = _makeRow({
      avg_eval_pawns: 0.1,
      eval_n: 15,
      eval_confidence: 'low',
    });
    renderTable([row]);
    const rowKey = row.opening_eco;
    const mgCell = document.querySelector(`[data-testid="${TEST_PREFIX}-bullet-${rowKey}"]`) as HTMLElement | null;
    expect(mgCell?.style.opacity).toBe('0.5');
  });
});

describe('MostPlayedOpeningsTable — mobile stacked lines (D-06)', () => {
  it('Test 10: mobile MG-entry line is present with grid-cols class and MG entry label', () => {
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
    // Has the MG entry label
    expect(line?.textContent).toContain('MG entry');
  });

  it('Test 11: mobile EG-entry line is present with EG entry label', () => {
    const row = _makeRow({
      eval_endgame_n: 20,
      eval_endgame_confidence: 'high',
      avg_eval_endgame_entry_pawns: 1.2,
    });
    renderTable([row]);
    const rowKey = row.opening_eco;
    const line = document.querySelector(`[data-testid="${TEST_PREFIX}-mobile-eg-line-${rowKey}"]`);
    expect(line).not.toBeNull();
    expect(line?.className).toMatch(/sm:hidden/);
    expect(line?.textContent).toContain('EG entry');
  });
});

describe('MostPlayedOpeningsTable — empty/null data fallbacks', () => {
  it('Test 12: clock_diff_n === 0 renders em-dash for clock-diff cell', () => {
    const row = _makeRow({ clock_diff_n: 0 });
    renderTable([row]);
    const rowKey = row.opening_eco;
    const cell = document.querySelector(`[data-testid="${TEST_PREFIX}-clock-diff-${rowKey}"]`);
    expect(cell).not.toBeNull();
    expect(cell?.textContent).toBe('—');
  });
});

describe('MostPlayedOpeningsTable — D-10 column header tooltips', () => {
  it('Test 13: MG eval column header tooltip contains "across analyzed games"', () => {
    const row = _makeRow();
    renderTable([row]);
    // InfoPopover is mocked to render children inline with data-testid
    const popover = document.querySelector('[data-testid="opening-stats-mg-eval-info"]');
    expect(popover).not.toBeNull();
    expect(popover?.textContent).toContain('across analyzed games');
  });

  it('Test 14: EG eval column header tooltip does NOT contain "across analyzed games"', () => {
    const row = _makeRow();
    renderTable([row]);
    const popover = document.querySelector('[data-testid="opening-stats-eg-eval-info"]');
    expect(popover).not.toBeNull();
    expect(popover?.textContent).not.toContain('across analyzed games');
  });

  it('Test 15: tooltip strings are defined as named constants (both used in component)', () => {
    // These imports will fail if the constants are not exported from MostPlayedOpeningsTable
    expect(MG_EVAL_HEADER_TOOLTIP).toContain('across analyzed games');
    expect(EG_EVAL_HEADER_TOOLTIP).not.toContain('across analyzed games');
  });

  it('Test 16: all 5 InfoPopovers are present in DOM', () => {
    const row = _makeRow();
    renderTable([row]);
    expect(document.querySelector('[data-testid="opening-stats-mg-eval-info"]')).not.toBeNull();
    expect(document.querySelector('[data-testid="opening-stats-mg-confidence-info"]')).not.toBeNull();
    expect(document.querySelector('[data-testid="opening-stats-clock-diff-info"]')).not.toBeNull();
    expect(document.querySelector('[data-testid="opening-stats-eg-eval-info"]')).not.toBeNull();
    expect(document.querySelector('[data-testid="opening-stats-eg-confidence-info"]')).not.toBeNull();
  });
});

describe('MostPlayedOpeningsTable — calibrated constants', () => {
  it('Test 17: MG MiniBulletChart receives MG domain; EG receives EG domain', () => {
    const row = _makeRow({
      avg_eval_pawns: 0.5,
      eval_n: 15,
      eval_confidence: 'high',
      avg_eval_endgame_entry_pawns: 1.5,
      eval_endgame_n: 20,
      eval_endgame_confidence: 'medium',
    });
    renderTable([row]);
    const rowKey = row.opening_eco;
    const mgBullet = document.querySelector(`[data-testid="${TEST_PREFIX}-bullet-${rowKey}"] [data-testid="mini-bullet-chart"]`);
    const egBullet = document.querySelector(`[data-testid="${TEST_PREFIX}-eg-bullet-${rowKey}"] [data-testid="mini-bullet-chart"]`);
    // MG bullet ariaLabel should contain "MG entry"
    expect(mgBullet?.getAttribute('aria-label')).toContain('MG entry');
    // EG bullet ariaLabel should contain "EG entry"
    expect(egBullet?.getAttribute('aria-label')).toContain('EG entry');
  });

  it('Test 18: bookmarked-openings reuse gets new columns automatically', () => {
    const row = _makeRow({
      avg_eval_pawns: 0.3,
      eval_n: 20,
      eval_confidence: 'high',
      avg_eval_endgame_entry_pawns: 0.8,
      eval_endgame_n: 15,
      eval_endgame_confidence: 'medium',
      avg_clock_diff_pct: 5.0,
      avg_clock_diff_seconds: 12,
      clock_diff_n: 20,
    });
    // Use a different testIdPrefix to simulate bookmarked-openings reuse
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
    // All 5 new cells should be present
    expect(document.querySelector(`[data-testid="bookmarked-bullet-${rowKey}"]`)).not.toBeNull();
    expect(document.querySelector(`[data-testid="bookmarked-confidence-${rowKey}"]`)).not.toBeNull();
    expect(document.querySelector(`[data-testid="bookmarked-clock-diff-${rowKey}"]`)).not.toBeNull();
    expect(document.querySelector(`[data-testid="bookmarked-eg-bullet-${rowKey}"]`)).not.toBeNull();
    expect(document.querySelector(`[data-testid="bookmarked-eg-confidence-${rowKey}"]`)).not.toBeNull();
  });
});
