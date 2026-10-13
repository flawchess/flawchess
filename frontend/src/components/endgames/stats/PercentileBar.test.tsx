// @vitest-environment jsdom
/** Phase 238 validation row D-00a: the percentile bar geometry, band colors and plain-text value. */

import { afterEach, describe, expect, it } from 'vitest';
import { cleanup, render, screen } from '@testing-library/react';
import { GAUGE_NEUTRAL, ZONE_DANGER, ZONE_SUCCESS } from '@/lib/theme';
import { PercentileBar } from './PercentileBar';

afterEach(cleanup);

/** jsdom normalizes color strings (oklch(0.50 ..) -> oklch(0.5 ..)); compare normalized forms. */
function normalized(color: string): string {
  const probe = document.createElement('div');
  probe.style.color = color;
  return probe.style.color;
}

function renderBar(percentile: number | null, significant = true) {
  return render(
    <PercentileBar
      status="ranked"
      percentile={percentile}
      floorN={120}
      floorRequired={30}
      significant={significant}
      testId="bar"
    />,
  );
}

describe('PercentileBar (D-00a)', () => {
  it('shades the 25-75 band', () => {
    renderBar(46);
    const band = screen.getByTestId('bar-band');
    expect(band.style.left).toBe('25%');
    expect(band.style.width).toBe('50%');
  });

  it('places the median tick at 50', () => {
    renderBar(46);
    expect(screen.getByTestId('bar-median').style.left).toBe('50%');
  });

  it.each([
    [24, ZONE_DANGER],
    [25, GAUGE_NEUTRAL],
    [75, GAUGE_NEUTRAL],
    [76, ZONE_SUCCESS],
  ])('colors the dot for percentile %i', (percentile, color) => {
    renderBar(percentile);
    expect(screen.getByTestId('bar-dot').style.backgroundColor).toBe(normalized(color));
    expect(screen.getByTestId('bar-number').style.color).toBe(normalized(color));
  });

  it.each([24, 76])(
    'keeps the dot and ordinal neutral at percentile %i when not significant (239 D-14)',
    (percentile) => {
      renderBar(percentile, false);
      expect(screen.getByTestId('bar-dot').style.backgroundColor).toBe(normalized(GAUGE_NEUTRAL));
      expect(screen.getByTestId('bar-number').style.color).toBe(normalized(GAUGE_NEUTRAL));
    },
  );

  it.each([
    [0.4, '1%'],
    [100, '99%'],
  ])('clamps the dot for percentile %f to %s', (percentile, left) => {
    renderBar(percentile);
    expect(screen.getByTestId('bar-dot').style.left).toBe(left);
  });

  it.each([
    [0, '1st'],
    [0.4, '1st'],
    [100, '99th'],
  ])('clamps the ordinal for percentile %f to %s, matching the dot', (percentile, label) => {
    renderBar(percentile);
    expect(screen.getByTestId('bar-number').textContent).toBe(label);
  });

  it.each([
    [24.6, '25th'],
    [75.4, '75th'],
  ])('colors percentile %f by its displayed ordinal %s (typical, not a tail)', (percentile, label) => {
    renderBar(percentile);
    expect(screen.getByTestId('bar-number').textContent).toBe(label);
    expect(screen.getByTestId('bar-dot').style.backgroundColor).toBe(normalized(GAUGE_NEUTRAL));
  });

  it('writes the percentile as an ordinal', () => {
    renderBar(46);
    expect(screen.getByTestId('bar-number').textContent).toBe('46th');
  });

  it('draws only plain elements: no svg icon of any kind', () => {
    const { container } = renderBar(90);
    expect(container.querySelector('svg')).toBeNull();
  });

  it('renders nothing for a ranked status without a percentile', () => {
    const { container } = renderBar(null);
    expect(container.firstChild).toBeNull();
  });
});
