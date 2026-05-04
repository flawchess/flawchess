// @vitest-environment jsdom
/**
 * Tests for MostPlayedOpeningsTable Phase 80 columns:
 * - Desktop columns: Name | Games | WDL | (eval text) | Eval bullet w/ confidence popover
 * - InfoPopover with the merged "Eval" column tooltip
 */
import { describe, it, expect, vi, afterEach } from 'vitest';
import { render, cleanup } from '@testing-library/react';
import type { ReactNode } from 'react';
import type { OpeningWDL } from '@/types/stats';
import { MostPlayedOpeningsTable } from '../MostPlayedOpeningsTable';
import { buildMgEvalHeaderTooltip } from '@/lib/openingStatsZones';
import { formatSignedEvalPawns } from '@/lib/clockFormat';
import { ZONE_DANGER, ZONE_NEUTRAL, ZONE_SUCCESS } from '@/lib/theme';

afterEach(() => {
  cleanup();
});

vi.mock('@/components/ui/tooltip', () => ({
  Tooltip: ({ children }: { children: ReactNode }) => <>{children}</>,
  TooltipProvider: ({ children }: { children: ReactNode }) => <>{children}</>,
}));

vi.mock('@/components/stats/MinimapPopover', () => ({
  MinimapPopover: ({ children }: { children: ReactNode }) => <>{children}</>,
}));

vi.mock('@/components/charts/MiniBulletChart', () => ({
  MiniBulletChart: ({ ariaLabel }: { ariaLabel?: string }) => (
    <div data-testid="mini-bullet-chart" aria-label={ariaLabel}>
      <div data-testid="mini-bullet-whisker" />
    </div>
  ),
}));

vi.mock('@/components/ui/info-popover', () => ({
  InfoPopover: ({
    children,
    testId,
  }: {
    children: ReactNode;
    testId?: string;
    ariaLabel?: string;
  }) => <span data-testid={testId}>{children}</span>,
}));

// Mock BulletConfidencePopover as a self-contained info-icon trigger
// (no children — it now renders alongside the bullet, not wrapping it).
vi.mock('@/components/insights/BulletConfidencePopover', () => ({
  BulletConfidencePopover: ({
    testId,
    prefaceText,
  }: {
    testId?: string;
    prefaceText?: string;
  }) => (
    <button type="button" data-testid={testId} data-preface={prefaceText}>
      ?
    </button>
  ),
}));

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
    eval_n: 0,
    eval_confidence: 'low',
    ...overrides,
  };
}

const noop = () => {};
const TEST_PREFIX = 'most-played';

function renderTable(rows: OpeningWDL[], evalBaselinePawns: number = 0) {
  return render(
    <MostPlayedOpeningsTable
      openings={rows}
      color="white"
      testIdPrefix={TEST_PREFIX}
      onOpenGames={noop}
      evalBaselinePawns={evalBaselinePawns}
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

  it('renders MG bullet chart cell with confidence popover trigger alongside the bullet', () => {
    const row = _makeRow({
      avg_eval_pawns: 0.3,
      eval_ci_low_pawns: 0.1,
      eval_ci_high_pawns: 0.5,
      eval_n: 20,
      eval_confidence: 'high',
    });
    renderTable([row]);
    const rowKey = row.opening_eco;
    const cell = document.querySelector(`[data-testid="${TEST_PREFIX}-bullet-${rowKey}"]`);
    expect(cell).not.toBeNull();
    expect(cell?.querySelector('[data-testid="mini-bullet-chart"]')).not.toBeNull();
    const popover = cell?.querySelector(
      `[data-testid="${TEST_PREFIX}-bullet-popover-${rowKey}"]`,
    ) as HTMLElement | null;
    expect(popover).not.toBeNull();
    // Preface text (formerly the column-header tooltip) is now passed into the per-row popover.
    expect(popover?.dataset.preface).toContain('0 cp means engine-balanced');
  });

  it('eval_n === 0 renders em-dash for both MG eval text and bullet chart, no popover wrapper', () => {
    const row = _makeRow({ eval_n: 0 });
    renderTable([row]);
    const rowKey = row.opening_eco;
    const text = document.querySelector(`[data-testid="${TEST_PREFIX}-eval-text-${rowKey}"]`);
    const bullet = document.querySelector(`[data-testid="${TEST_PREFIX}-bullet-${rowKey}"]`);
    expect(text?.textContent).toBe('—');
    expect(bullet?.textContent).toBe('—');
    expect(bullet?.querySelector('[data-testid="mini-bullet-chart"]')).toBeNull();
    expect(
      bullet?.querySelector(`[data-testid="${TEST_PREFIX}-bullet-popover-${rowKey}"]`),
    ).toBeNull();
  });

  it('total games below MIN_GAMES_OPENING_ROW dims the whole row', () => {
    const row = _makeRow({
      total: 15,
      avg_eval_pawns: 0.1,
      eval_n: 15,
      eval_confidence: 'low',
    });
    renderTable([row]);
    const rowKey = row.opening_eco;
    const rowEl = document.querySelector(`[data-testid="${TEST_PREFIX}-row-${rowKey}"]`) as HTMLElement | null;
    expect(rowEl?.style.opacity).toBe('0.5');
  });

  it('confidence === low does NOT dim a row that has enough total games', () => {
    const row = _makeRow({
      total: 50,
      avg_eval_pawns: 0.1,
      eval_n: 15,
      eval_confidence: 'low',
    });
    renderTable([row]);
    const rowKey = row.opening_eco;
    const rowEl = document.querySelector(`[data-testid="${TEST_PREFIX}-row-${rowKey}"]`) as HTMLElement | null;
    expect(rowEl?.style.opacity).toBe('');
  });
});

describe('MostPlayedOpeningsTable — D-10 column header tooltip', () => {
  it('Eval column header has no separate info popover — content is merged into the per-row popover', () => {
    const row = _makeRow();
    renderTable([row]);
    expect(
      document.querySelector('[data-testid="opening-stats-mg-eval-info"]'),
    ).toBeNull();
  });

  it('buildMgEvalHeaderTooltip produces tooltip text anchored on 0 cp (260504-rvh)', () => {
    const text = buildMgEvalHeaderTooltip();
    expect(text).toContain('0 cp means engine-balanced');
    expect(text).toContain('typical MG-entry eval for your color');
  });

  it('buildMgEvalHeaderTooltip avoids em-dashes per CLAUDE.md user-facing copy rule', () => {
    const text = buildMgEvalHeaderTooltip();
    expect(text).not.toContain('—');
  });
});

describe('MostPlayedOpeningsTable — zero-anchored eval cell (260504-rvh)', () => {
  function readEvalCellColor(rowKey: string): string {
    const cell = document.querySelector(
      `[data-testid="${TEST_PREFIX}-eval-text-${rowKey}"]`,
    ) as HTMLElement | null;
    const span = cell?.querySelector('span.font-semibold') as HTMLElement | null;
    return span?.style.color ?? '';
  }

  // jsdom normalizes oklch component literals (e.g. "0.50" -> "0.5"), so compare
  // by stripping whitespace + zero-padding to make the assertion robust.
  function normalizeColor(c: string): string {
    return c.replace(/\s+/g, ' ').replace(/(\d)\.(\d+?)0+(\D|$)/g, '$1.$2$3').trim();
  }

  it('row within ±0.30 of zero is rendered with neutral color', () => {
    const row = _makeRow({
      avg_eval_pawns: 0.10,
      eval_n: 50,
      eval_confidence: 'medium',
    });
    renderTable([row], 0.315);
    expect(normalizeColor(readEvalCellColor(row.opening_eco))).toBe(
      normalizeColor(ZONE_NEUTRAL),
    );
  });

  it('row well above zero (>= +0.30) is rendered with success color regardless of color baseline', () => {
    const row = _makeRow({
      avg_eval_pawns: 0.65,
      eval_n: 50,
      eval_confidence: 'high',
    });
    renderTable([row], 0.315);
    expect(normalizeColor(readEvalCellColor(row.opening_eco))).toBe(
      normalizeColor(ZONE_SUCCESS),
    );
  });

  it('row well below zero (<= -0.30) is rendered with danger color regardless of color baseline', () => {
    const row = _makeRow({
      avg_eval_pawns: -0.50,
      eval_n: 50,
      eval_confidence: 'high',
    });
    renderTable([row], 0.315);
    expect(normalizeColor(readEvalCellColor(row.opening_eco))).toBe(
      normalizeColor(ZONE_DANGER),
    );
  });

  it('white engine baseline tick value (+0.315) reads as success (decoupled from H0)', () => {
    const row = _makeRow({
      avg_eval_pawns: 0.315,
      eval_n: 50,
      eval_confidence: 'high',
    });
    renderTable([row], 0.315);
    expect(normalizeColor(readEvalCellColor(row.opening_eco))).toBe(
      normalizeColor(ZONE_SUCCESS),
    );
  });
});

describe('MostPlayedOpeningsTable — bookmarked openings reuse', () => {
  it('bookmarked-openings reuse renders the same eval columns', () => {
    const row = _makeRow({
      avg_eval_pawns: 0.3,
      eval_n: 20,
      eval_confidence: 'high',
    });
    render(
      <MostPlayedOpeningsTable
        openings={[row]}
        color="white"
        testIdPrefix="bookmarked"
        onOpenGames={noop}
        evalBaselinePawns={0.315}
        showAll={true}
      />,
    );
    const rowKey = row.opening_eco;
    expect(document.querySelector(`[data-testid="bookmarked-eval-text-${rowKey}"]`)).not.toBeNull();
    expect(document.querySelector(`[data-testid="bookmarked-bullet-${rowKey}"]`)).not.toBeNull();
    expect(
      document.querySelector(`[data-testid="bookmarked-bullet-popover-${rowKey}"]`),
    ).not.toBeNull();
  });
});
