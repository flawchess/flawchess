// @vitest-environment jsdom
/**
 * Phase 238 validation rows D-00c (merged popover), D-09 (below-floor slot) and
 * D-11 (pending / not-ranked slots).
 */

import { afterEach, describe, expect, it } from 'vitest';
import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import type { CdfMetricId, RankedMetricOut, RatingAnchorOut } from '@/types/endgames';
import { buildMetric, buildRankedTc, MIXED_ANCHOR } from './rankedFixtures';
import { RankedMetricPopover } from './RankedMetricPopover';
import { RankedMetricRow } from './RankedMetricRow';

afterEach(cleanup);

const TRIGGER_ID = 'ranked-metric-score-gap-tc-rapid';

/**
 * Look an element up by testid with a one-line failure message (queryBy plus an
 * expectation, rather than getBy whose multi-line DOM dump breaks TAP reports).
 */
function byId(testId: string): HTMLElement {
  const element = screen.queryByTestId(testId);
  expect(element, `element ${testId} present`).not.toBeNull();
  return element as HTMLElement;
}

function openPopover(
  metric: RankedMetricOut,
  anchor: RatingAnchorOut | null = MIXED_ANCHOR,
): HTMLElement {
  const tcStats = buildRankedTc('rapid', { anchor });
  render(
    <RankedMetricPopover metric={metric} tcStats={tcStats} testId={TRIGGER_ID} />,
  );
  fireEvent.click(byId(TRIGGER_ID));
  return byId(`${TRIGGER_ID}-popover`);
}

describe('RankedMetricPopover body (D-00c)', () => {
  it('orders WHAT, percentile sentence, disclosures, separator, footer', () => {
    const popover = openPopover(buildMetric('score_gap', { value: 0.05, percentile: 46.4 }));
    const text = popover.textContent ?? '';
    const parts = [
      'Endgame Score Gap:',
      'Negative = you do worse once an endgame is reached.',
      'Better than 46% of ~1788-rated rapid players.',
      'Compared against benchmarked Lichess players at your rating.',
      'Based on 120 of your rapid games from the last 36 months, opponents within ±100 Elo.',
      'Anchored at ~1788 Elo, blending 657 chess.com games (median 1466, converted) with 741 lichess games (median 1765).',
      'n = 120',
    ];
    const indexes = parts.map((part) => text.indexOf(part));
    indexes.forEach((index, i) => expect(index, `missing: ${parts[i]}`).toBeGreaterThanOrEqual(0));
    expect([...indexes].sort((a, b) => a - b)).toEqual(indexes);
    // 238 UAT: the Stats tab has no filters, so the filter-independence line is gone.
    expect(text).not.toContain('Filters');
  });

  it('clamps the percentile sentence into 1..99', () => {
    const popover = openPopover(buildMetric('score_gap', { percentile: 99.8 }));
    expect(popover.textContent).toContain('Better than 99% of');
  });

  it('describes a lichess-only anchor', () => {
    const popover = openPopover(buildMetric('score_gap'), {
      anchor_rating: 1788,
      n_chesscom_games: 0,
      n_lichess_games: 741,
      chesscom_median_native: null,
      lichess_median_native: 1765,
    });
    expect(popover.textContent).toContain(
      'Anchored at ~1788 Elo from 741 lichess games (native rating).',
    );
  });

  it('describes a chess.com-only anchor', () => {
    const popover = openPopover(buildMetric('score_gap'), {
      anchor_rating: 1788,
      n_chesscom_games: 657,
      n_lichess_games: 0,
      chesscom_median_native: 1466,
      lichess_median_native: null,
    });
    expect(popover.textContent).toContain(
      'Anchored at ~1788 Elo from 657 chess.com games (median 1466, converted to Lichess-equivalent).',
    );
  });

  it('puts the statistics in a greyed footer below a separator', () => {
    const popover = openPopover(buildMetric('score_gap'));
    const footer = byId(`${TRIGGER_ID}-footer`);
    const separator = popover.querySelector('hr');
    expect(separator).not.toBeNull();
    expect(separator!.compareDocumentPosition(footer) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    expect(footer.className).toMatch(/text-background\/\d+/);
    // Stats jargon lives in the footer only, never in the prose part.
    const prose = (popover.textContent ?? '').replace(footer.textContent ?? '', '');
    expect(prose).not.toMatch(/99% CI|p =|p </);
  });

  it('writes a signed CI for gaps, a plain CI for rates, and the p-value', () => {
    openPopover(buildMetric('score_gap', { ci_low: 0.01, ci_high: 0.09, p_value: 0.032 }));
    const footer = byId(`${TRIGGER_ID}-footer`).textContent ?? '';
    expect(footer).toContain('n = 120');
    expect(footer).toContain('99% CI +1.0% to +9.0%');
    expect(footer).toContain('p = 0.032');
    cleanup();

    openPopover(buildMetric('conversion_rate' as CdfMetricId, { ci_low: 0.7, ci_high: 0.8, p_value: null }));
    const rateFooter = byId(`${TRIGGER_ID}-footer`).textContent ?? '';
    expect(rateFooter).toContain('99% CI 70.0% to 80.0%');
    expect(rateFooter).not.toContain('p =');
  });

  it('says an out-of-range percentile could be chance only when it is not significant (239 D-14)', () => {
    const chance = openPopover(buildMetric('score_gap', { percentile: 90, significant: false }));
    expect(chance.textContent).toContain('This could be chance');
    cleanup();
    const sure = openPopover(buildMetric('score_gap', { percentile: 90, significant: true }));
    expect(sure.textContent).not.toContain('could be chance');
    cleanup();
    const typical = openPopover(buildMetric('score_gap', { percentile: 46, significant: false }));
    expect(typical.textContent).not.toContain('could be chance');
  });

  it('omits the CI and p lines when they are null', () => {
    openPopover(buildMetric('score_gap', { ci_low: null, ci_high: null, p_value: null }));
    const footer = byId(`${TRIGGER_ID}-footer`).textContent ?? '';
    expect(footer).toBe('n = 120');
  });

  it('writes tiny p-values as p < 0.001', () => {
    openPopover(buildMetric('score_gap', { p_value: 0.0004 }));
    expect(byId(`${TRIGGER_ID}-footer`).textContent).toContain('p < 0.001');
  });
});

describe('RankedMetricPopover for unranked cells (D-09, D-11)', () => {
  it('below_floor keeps WHAT, explains the floor and skips the percentile statement', () => {
    const popover = openPopover(
      buildMetric('score_gap', {
        status: 'below_floor',
        percentile: null,
        n: 18,
        floor_n: 18,
        floor_required: 30,
      }),
    );
    const text = popover.textContent ?? '';
    expect(text).toContain('Endgame Score Gap:');
    expect(text).toContain('Not enough games to rank yet (18 of 30)');
    expect(text).not.toContain('Better than');
    expect(text).not.toContain('Compared against benchmarked');
    expect(byId(`${TRIGGER_ID}-footer`).textContent).toContain('n = 18');
  });

  it('pending and unranked explain themselves with the slot copy', () => {
    const pending = openPopover(buildMetric('score_gap', { status: 'pending', value: null, percentile: null }));
    expect(pending.textContent).toContain(
      'Analyzing your games, this fills in once evaluations finish',
    );
    cleanup();
    const unranked = openPopover(buildMetric('score_gap', { status: 'unranked', percentile: null }));
    expect(unranked.textContent).toContain('Not ranked yet');
    expect(unranked.textContent).not.toContain('Better than');
  });
});

describe('RankedMetricRow status slots (D-09, D-11)', () => {
  function renderRow(metric: RankedMetricOut) {
    const tcStats = buildRankedTc('rapid');
    return render(
      <RankedMetricRow metric={metric} tcStats={tcStats} testId="row" />,
    );
  }

  it('ranked: uncolored value and a dot', () => {
    renderRow(buildMetric('score_gap', { value: 0.05, percentile: 46 }));
    const value = byId('row-value');
    expect(value.textContent).toBe('+5%');
    expect(value.getAttribute('style') ?? '').not.toMatch(/color/);
    expect(value.className).not.toMatch(/text-(red|green|blue|amber)|zone/);
    expect(byId('row-bar-dot')).toBeTruthy();
  });

  it('below_floor: value stays, the slot reads the floor copy, no dot', () => {
    renderRow(
      buildMetric('score_gap', {
        status: 'below_floor',
        percentile: null,
        value: 0.05,
        floor_n: 18,
        floor_required: 30,
      }),
    );
    expect(byId('row-value').textContent).toBe('+5%');
    expect(byId('row-bar').textContent).toBe('Not enough games to rank yet (18 of 30)');
    expect(screen.queryByTestId('row-bar-dot')).toBeNull();
  });

  it('pending: value and bar are replaced by the analyzing line, no dot', () => {
    renderRow(buildMetric('score_gap', { status: 'pending', value: null, percentile: null }));
    expect(screen.queryByTestId('row-value')).toBeNull();
    expect(byId('row-bar').textContent).toBe(
      'Analyzing your games, this fills in once evaluations finish',
    );
    expect(screen.queryByTestId('row-bar-dot')).toBeNull();
  });

  it('unranked: value stays, slot reads "Not ranked yet", no dot', () => {
    renderRow(buildMetric('score_gap', { status: 'unranked', percentile: null, value: 0.05 }));
    expect(byId('row-value').textContent).toBe('+5%');
    expect(byId('row-bar').textContent).toBe('Not ranked yet');
    expect(screen.queryByTestId('row-bar-dot')).toBeNull();
  });

  it('never invents a drift or updating state', () => {
    const { container } = renderRow(buildMetric('score_gap'));
    expect(container.textContent?.toLowerCase()).not.toMatch(/updating|mismatch|drift/);
  });
});
