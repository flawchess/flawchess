// @vitest-environment jsdom
/**
 * PositionResultsPanel End Eval row: the Openings ('opening-end') context renders the
 * baseline-centred VerdictBar; the Endgames ('endgame-entry') context keeps the old
 * MiniBulletChart and EvalConfidencePopover untouched.
 */

import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { TooltipProvider } from '@/components/ui/tooltip';
import { GAUGE_NEUTRAL, ZONE_SUCCESS } from '@/lib/theme';
import type { WDLStats } from '@/types/api';
import { PositionResultsPanel } from '../PositionResultsPanel';

vi.mock('@/hooks/useReadiness', () => ({
  useReadiness: () => ({
    tier1: true,
    tier2: true,
    pendingCount: 0,
    totalCount: 0,
    isLoading: false,
  }),
}));

afterEach(cleanup);

/** jsdom normalizes color strings (oklch(0.50 ..) -> oklch(0.5 ..)); compare normalized forms. */
function normalized(color: string): string {
  const probe = document.createElement('div');
  probe.style.color = color;
  return probe.style.color;
}

function stats(overrides: Partial<WDLStats> = {}): WDLStats {
  return {
    wins: 18,
    draws: 6,
    losses: 16,
    total: 40,
    win_pct: 45,
    draw_pct: 15,
    loss_pct: 40,
    score: 0.525,
    confidence: 'low',
    p_value: 0.7,
    ci_low: 0.4,
    ci_high: 0.65,
    avg_eval_pawns: 0.85,
    eval_ci_low_pawns: 0.6,
    eval_ci_high_pawns: 1.1,
    eval_ci99_low_pawns: 0.5,
    eval_ci99_high_pawns: 1.2,
    eval_n: 38,
    eval_p_value: 0.001,
    eval_confidence: 'high',
    ...overrides,
  };
}

function renderPanel(
  s: WDLStats,
  props: Partial<Parameters<typeof PositionResultsPanel>[0]> = {},
): void {
  render(
    <TooltipProvider>
      <PositionResultsPanel
        stats={s}
        evalBaselinePawns={0.25}
        filterColor="white"
        label="Position"
        {...props}
      />
    </TooltipProvider>,
  );
}

describe('PositionResultsPanel End Eval row', () => {
  it('renders the verdict track, band, zero tick and a green dot for a confident, large-sample lead', () => {
    renderPanel(stats());
    expect(screen.getByTestId('eval-verdict-position-track')).toBeTruthy();
    expect(screen.getByTestId('eval-verdict-position-band')).toBeTruthy();
    expect(screen.getByTestId('eval-verdict-position-zero')).toBeTruthy();
    const dot = screen.getByTestId('eval-verdict-position-dot');
    expect(dot.style.backgroundColor).toBe(normalized(ZONE_SUCCESS));
    expect(screen.queryByTestId('eval-bullet-position')).toBeNull();
  });

  it('keeps the dot neutral below the 20-game floor even when outside the band and confident', () => {
    renderPanel(stats({ total: 15, eval_n: 15 }));
    const dot = screen.getByTestId('eval-verdict-position-dot');
    expect(dot.style.backgroundColor).toBe(normalized(GAUGE_NEUTRAL));
  });

  it('applies the 20-game floor to the eval sample, not the game count (WR-02)', () => {
    // 100 games but only 11 usable evals (mate/NULL excluded, outliers trimmed): no verdict colour.
    renderPanel(stats({ total: 100, eval_n: 11 }));
    const dot = screen.getByTestId('eval-verdict-position-dot');
    expect(dot.style.backgroundColor).toBe(normalized(GAUGE_NEUTRAL));
  });

  it('keeps the dot neutral when the eval is outside the band but not confident', () => {
    renderPanel(stats({ eval_confidence: 'medium' }));
    const dot = screen.getByTestId('eval-verdict-position-dot');
    expect(dot.style.backgroundColor).toBe(normalized(GAUGE_NEUTRAL));
  });

  it('centres the bar on the colour baseline: an average Black game sits on the centre', () => {
    renderPanel(stats({ avg_eval_pawns: -0.25, eval_confidence: 'low' }), {
      filterColor: 'black',
      evalBaselinePawns: -0.25,
    });
    expect(screen.getByTestId('eval-verdict-position-dot').style.left).toBe('50%');
  });

  it('endgame-entry still renders the old bullet chart and no verdict track', () => {
    renderPanel(stats(), { evalContext: 'endgame-entry' });
    expect(screen.getByTestId('eval-bullet-position')).toBeTruthy();
    expect(screen.queryByTestId('eval-verdict-position-track')).toBeNull();
    expect(screen.getByTestId('eval-bullet-popover-trigger')).toBeTruthy();
  });
});

describe('PositionResultsPanel End Eval popover', () => {
  function openEvalPopover(): HTMLElement {
    fireEvent.click(screen.getByTestId('eval-bullet-popover-trigger'));
    const popover = screen.queryByTestId('eval-bullet-popover-trigger-popover');
    expect(popover, 'popover open').not.toBeNull();
    return popover as HTMLElement;
  }

  it('opening-end popover carries the greyed 99% CI / p vs baseline / n footer and no "pawns"', () => {
    renderPanel(
      stats({
        avg_eval_pawns: 0.41,
        eval_ci99_low_pawns: 0.12,
        eval_ci99_high_pawns: 0.7,
        eval_p_value: 0.004,
        eval_n: 230,
        total: 230,
      }),
    );
    const popover = openEvalPopover();
    expect(screen.getByTestId('eval-bullet-popover-trigger-footer').textContent).toBe(
      '99% CI +0.12 to +0.70 · p = 0.004 vs +0.25 · n = 230',
    );
    expect(popover.textContent ?? '').not.toMatch(/pawns/i);
  });

  it('opening-end popover says "could be chance" for an out-of-band, non-confident eval', () => {
    renderPanel(stats({ eval_confidence: 'medium' }));
    expect(openEvalPopover().textContent ?? '').toMatch(/could be chance/);
  });

  it('endgame-entry popover is still the old EvalConfidencePopover (no verdict footer)', () => {
    renderPanel(stats(), { evalContext: 'endgame-entry' });
    fireEvent.click(screen.getByTestId('eval-bullet-popover-trigger'));
    expect(screen.queryByTestId('eval-bullet-popover-trigger-footer')).toBeNull();
  });
});
