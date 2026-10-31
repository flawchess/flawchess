// @vitest-environment jsdom
/** The out-of-the-opening popover: WHAT sentence with threshold, percentile statement, disclosures, per-TC list, 95% footer with p. */

import { afterEach, describe, expect, it } from 'vitest';
import { cleanup, fireEvent, render, screen, within } from '@testing-library/react';
import type { OpeningOutRateOut, OpeningOutSide, OpeningOutTcOut } from '@/types/openingOut';
import { OutOfOpeningPopover } from '../OutOfOpeningPopover';

afterEach(cleanup);

const TRIGGER_ID = 'out-of-opening-worse-rate';

function tc(overrides: Partial<OpeningOutTcOut> & Pick<OpeningOutTcOut, 'tc'>): OpeningOutTcOut {
  return {
    status: 'ranked',
    k: 330,
    n: 1491,
    rate: 0.22,
    floor_n: 1491,
    floor_required: 30,
    percentile_favorable: 58,
    ...overrides,
  };
}

function rankedRate(overrides: Partial<OpeningOutRateOut> = {}): OpeningOutRateOut {
  return {
    status: 'ranked',
    k: 330,
    n: 1491,
    rate: 0.22,
    floor_n: 1491,
    floor_required: 30,
    percentile_favorable: 58,
    ci_low: 0.201,
    ci_high: 0.243,
    p_value: 0.034,
    peer_p25: 0.15,
    peer_p50: 0.21,
    peer_p75: 0.28,
    significant: true,
    // Deliberately out of order: the popover must list bullet, blitz, rapid, classical.
    tcs: [
      tc({ tc: 'rapid', status: 'pending', percentile_favorable: null, rate: null, n: 0, k: 0 }),
      tc({
        tc: 'bullet',
        status: 'below_floor',
        percentile_favorable: null,
        rate: 0.3,
        n: 18,
        k: 5,
        floor_n: 18,
      }),
      tc({ tc: 'classical', status: 'unranked', percentile_favorable: null, n: 40, k: 9 }),
      tc({ tc: 'blitz' }),
    ],
    ...overrides,
  };
}

function openPopover(
  rate: OpeningOutRateOut,
  side: OpeningOutSide = 'worse',
  color: 'white' | 'black' = 'white',
  testId: string = TRIGGER_ID,
): HTMLElement {
  render(<OutOfOpeningPopover side={side} color={color} rate={rate} testId={testId} />);
  fireEvent.click(screen.getByTestId(testId));
  const popover = screen.queryByTestId(`${testId}-popover`);
  expect(popover, 'popover open').not.toBeNull();
  return popover as HTMLElement;
}

describe('OutOfOpeningPopover', () => {
  it('states the WHAT sentence in eval units and the percentile in words', () => {
    const popover = openPopover(rankedRate());
    const text = popover.textContent ?? '';
    expect(text).toContain('Came out worse:');
    expect(text).toContain(
      'with an eval of −0.75 or lower as White, 1.0 below a typical White opening position (+0.25).',
    );
    expect(text).toContain('Fewer bad openings than 58% of similarly rated peers.');
    expect(text).not.toMatch(/pawn/i);
  });

  it('states the colour-specific threshold for the other two side x colour cells', () => {
    let text = openPopover(rankedRate(), 'better', 'white').textContent ?? '';
    expect(text).toContain('with an eval of +1.25 or higher as White');
    cleanup();
    text = openPopover(rankedRate(), 'worse', 'black').textContent ?? '';
    expect(text).toContain('with an eval of −1.25 or lower as Black');
  });

  it('words the better side and the Black colour', () => {
    const popover = openPopover(rankedRate({ percentile_favorable: 71 }), 'better', 'black');
    const text = popover.textContent ?? '';
    expect(text).toContain('Came out better:');
    expect(text).toContain(
      'with an eval of +0.75 or higher as Black, 1.0 above a typical Black opening position (−0.25).',
    );
    expect(text).toContain('More good openings than 71% of similarly rated peers.');
  });

  it('adds the could-be-chance line only for an out-of-range, not significant percentile', () => {
    const chance = 'could be chance';
    let popover = openPopover(rankedRate({ percentile_favorable: 90, significant: false }));
    expect(popover.textContent).toContain(chance);
    cleanup();

    popover = openPopover(rankedRate({ percentile_favorable: 90, significant: true }));
    expect(popover.textContent).not.toContain(chance);
    cleanup();

    popover = openPopover(rankedRate({ percentile_favorable: 55, significant: false }));
    expect(popover.textContent).not.toContain(chance);
  });

  it('carries the peer, ranked-games and filter disclosures only', () => {
    const text = openPopover(rankedRate()).textContent ?? '';
    expect(text).toContain('benchmarked Lichess players at your rating, not FlawChess users');
    expect(text).toContain(
      'rated, opponents within ±100 Elo, your most recent 3,000 per time control from the last 36 months',
    );
    expect(text).toContain('Not affected by the page filters');
    // UAT: the rating-dependence and TC-averaging bullets were cut to shorten the popover.
    expect(text).not.toContain('depends strongly on rating');
    expect(text).not.toContain('averages the per-time-control percentiles');
  });

  it('lists every time control in fastest-to-slowest order with rate, percentile and games or status', () => {
    openPopover(rankedRate());
    const list = screen.getByTestId(`${TRIGGER_ID}-tcs`);
    const lines = within(list)
      .getAllByRole('listitem')
      .map((li) => li.textContent);
    expect(lines).toEqual([
      'Bullet: not enough games yet (18 of 30)',
      'Blitz: 22%, 58th percentile, 1,491 games',
      'Rapid: analyzing',
      'Classic: not ranked yet',
    ]);
  });

  it('footer shows k of n games, the 95% CI, the p-value vs the peer median and the peer range, never 99%', () => {
    openPopover(rankedRate());
    const footer = screen.getByTestId(`${TRIGGER_ID}-footer`).textContent ?? '';
    expect(footer).toBe(
      '330 of 1,491 games · 95% CI 20.1% to 24.3% · p = 0.034 vs peer median 21.0% · peers typically 15% to 28%',
    );
    expect(footer).not.toContain('99%');
  });

  it('a non-ranked card shows the status line, the TC list and a k-of-n footer only', () => {
    const popover = openPopover(
      rankedRate({
        status: 'below_floor',
        k: 5,
        n: 18,
        floor_n: 18,
        percentile_favorable: null,
        ci_low: null,
        ci_high: null,
        p_value: null,
        peer_p25: null,
        peer_p50: null,
        peer_p75: null,
        significant: false,
        tcs: [tc({ tc: 'bullet', status: 'below_floor', percentile_favorable: null, n: 18, k: 5, floor_n: 18 })],
      }),
    );
    const text = popover.textContent ?? '';
    expect(text).toContain('Not enough games to rank yet (18 of 30)');
    expect(text).not.toContain('similarly rated peers');
    expect(screen.getByTestId(`${TRIGGER_ID}-footer`).textContent).toBe('5 of 18 games');
    expect(screen.getByTestId(`${TRIGGER_ID}-tcs`)).not.toBeNull();
  });

  it('contains no chart', () => {
    const popover = openPopover(rankedRate());
    expect(popover.querySelector('canvas')).toBeNull();
    // The trigger icon lives outside the portal content; the body itself has no svg.
    expect(popover.querySelector('svg')).toBeNull();
  });
});
