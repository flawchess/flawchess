// @vitest-environment jsdom
/**
 * Phase 238 validation row D-00d: the bucket card shows the ranked rate as an
 * uncolored big number, a bracketed WDL bar from the same games, and two
 * percentile rows; never a gauge.
 */

import { afterEach, describe, expect, it } from 'vitest';
import { cleanup, render } from '@testing-library/react';
import { MemoryRouter } from 'react-router';
import type { MaterialBucket, RankedBucketOut, RankedTcStats } from '@/types/endgames';
import { MetricsCard } from './MetricsCard';
import { buildRankedTc } from './rankedFixtures';

afterEach(cleanup);

// Bucket W/D/L agree with the ranked rates: 70/100 wins, (20 + 10/2)/50 score, (4 + 4)/40 saves.
const CONVERSION: RankedBucketOut = { bucket: 'conversion', games: 100, wins: 70, draws: 10, losses: 20 };
const PARITY: RankedBucketOut = { bucket: 'parity', games: 50, wins: 20, draws: 10, losses: 20 };
const RECOVERY: RankedBucketOut = { bucket: 'recovery', games: 40, wins: 4, draws: 4, losses: 32 };

function buildTc(overrides: Partial<RankedTcStats> = {}): RankedTcStats {
  return buildRankedTc(
    'rapid',
    { buckets: [CONVERSION, PARITY, RECOVERY], ...overrides },
    {
      conversion_rate: { value: 0.7, n: 100 },
      parity_rate: { value: 0.5, n: 50 },
      recovery_rate: { value: 0.2, n: 40 },
      score_gap_conv: { value: -0.04, n: 100 },
    },
  );
}

function renderCard(bucket: MaterialBucket, tcStats: RankedTcStats = buildTc()) {
  return render(
    <MemoryRouter>
      <MetricsCard tcStats={tcStats} bucket={bucket} />
    </MemoryRouter>,
  );
}

function byId(root: HTMLElement, testId: string): HTMLElement {
  const element = root.querySelector<HTMLElement>(`[data-testid="${testId}"]`);
  expect(element, `element ${testId} present`).not.toBeNull();
  return element as HTMLElement;
}

describe('MetricsCard', () => {
  it('conversion: shows the ranked rate and game count and brackets the win segment', () => {
    const { container } = renderCard('conversion');
    expect(byId(container, 'metrics-card-conversion-rate').textContent).toBe('70%');
    expect(byId(container, 'metrics-card-conversion-games').textContent).toBe('100 games');
    expect(byId(container, 'metrics-card-conversion-bracket-label').textContent).toBe('wins = 70%');
    expect(byId(container, 'metrics-card-conversion-bracket-span').style.width).toBe('70%');
    // The draw and loss segments (everything right of the wins) are dimmed.
    expect(byId(container, 'metrics-card-conversion-dim').style.left).toBe('70%');
  });

  it('recovery: brackets wins plus draws and dims only the losses', () => {
    const { container } = renderCard('recovery');
    expect(byId(container, 'metrics-card-recovery-bracket-label').textContent).toBe(
      'wins + draws = 20%',
    );
    // 4 wins + 4 draws of 40 games, the same 20% as the ranked rate.
    expect(byId(container, 'metrics-card-recovery-bracket-span').style.width).toBe('20%');
    expect(byId(container, 'metrics-card-recovery-dim').style.left).toBe('20%');
  });

  it('parity: brackets wins plus half the draws (the score) and dims the rest', () => {
    const { container } = renderCard('parity');
    expect(byId(container, 'metrics-card-parity-bracket-label').textContent).toBe(
      'wins + ½draws = 50%',
    );
    // 20 W / 10 D / 20 L of 50: 40% wins + half of the 20% draws.
    expect(byId(container, 'metrics-card-parity-bracket-span').style.width).toBe('50%');
    expect(byId(container, 'metrics-card-parity-dim').style.left).toBe('50%');
  });

  it('draws the WDL bar from the same bucket as the rate (D-00b)', () => {
    const { container } = renderCard('conversion');
    const bar = byId(container, 'metrics-card-conversion-bar');
    // Segment widths are the bucket's W/D/L shares (the 10% draw is too narrow for a label).
    const widths = Array.from(bar.querySelectorAll<HTMLElement>('[data-testid="mini-wdl-bar"] > div')).map(
      (segment) => segment.style.width,
    );
    expect(widths).toEqual(['70%', '10%', '20%']);
  });

  it('has no gauge and no color on the big number', () => {
    const { container } = renderCard('conversion');
    expect(container.querySelector('[data-testid*="gauge"]')).toBeNull();
    expect(byId(container, 'metrics-card-conversion-rate').getAttribute('style')).toBeNull();
  });

  it('shows the rate row then the matching score-gap row', () => {
    const { container } = renderCard('conversion');
    const rateRow = byId(container, 'metrics-card-conversion-rate-row');
    const gapRow = byId(container, 'metrics-card-conversion-gap-row');
    expect(rateRow.textContent).toContain('Conversion vs. peers');
    expect(gapRow.textContent).toContain('vs. expected');
    expect(byId(container, 'metrics-card-conversion-gap-row-value').textContent).toBe('-4%');
    // Rate row precedes the gap row in document order.
    expect(
      rateRow.compareDocumentPosition(gapRow) & Node.DOCUMENT_POSITION_FOLLOWING,
    ).toBeTruthy();
  });

  it('a pending rate renders the pending line instead of the big number and bar (D-11)', () => {
    const tcStats = buildRankedTc(
      'rapid',
      { buckets: [CONVERSION, PARITY, RECOVERY] },
      { conversion_rate: { status: 'pending', value: null, percentile: null } },
    );
    const { container } = renderCard('conversion', tcStats);
    expect(container.querySelector('[data-testid="metrics-card-conversion-rate"]')).toBeNull();
    expect(container.querySelector('[data-testid="metrics-card-conversion-bar"]')).toBeNull();
    expect(byId(container, 'metrics-card-conversion-rate-row').textContent).toContain(
      'Analyzing your games',
    );
  });

  it('omits the WDL bar for an empty bucket without crashing', () => {
    const { container } = renderCard('recovery', buildTc({ buckets: [] }));
    expect(container.querySelector('[data-testid="metrics-card-recovery-bar"]')).toBeNull();
    expect(byId(container, 'metrics-card-recovery-rate').textContent).toBe('20%');
  });
});
