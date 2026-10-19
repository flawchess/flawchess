// @vitest-environment jsdom
import { afterEach, describe, expect, it } from 'vitest';
import { cleanup, render, screen } from '@testing-library/react';
import { MedalTally } from '@/components/train/medals/MedalTally';

afterEach(cleanup);

describe('MedalTally', () => {
  it('renders nothing for all-zero medals', () => {
    const { container } = render(
      <MedalTally medals={{ gold: 0, silver: 0, bronze: 0 }} board="points" testId="tally" />,
    );
    expect(container.firstChild).toBeNull();
  });

  it('stacks up to five icons per non-zero type without a count, with the aria-label', () => {
    render(<MedalTally medals={{ gold: 5, silver: 1, bronze: 0 }} board="points" testId="tally" />);
    const tally = screen.getByTestId('tally');
    expect(tally.getAttribute('role')).toBe('img');
    expect(tally.getAttribute('aria-label')).toBe('5 gold, 1 silver Points medals');
    expect(screen.getByTestId('tally-gold').querySelectorAll('svg')).toHaveLength(5);
    expect(screen.getByTestId('tally-silver').querySelectorAll('svg')).toHaveLength(1);
    // No count while stacked; only a zero-width baseline anchor remains.
    expect(screen.queryByTestId('tally-gold-count')).toBeNull();
    expect(screen.queryByTestId('tally-silver-count')).toBeNull();
    expect(screen.getByTestId('tally-gold').querySelector('[aria-hidden="true"]:not(svg)')?.textContent).not.toMatch(
      /\d/,
    );
    // Stacked icons after the first overlap the previous one.
    const goldIcons = screen.getByTestId('tally-gold').querySelectorAll('svg');
    expect(goldIcons[0].getAttribute('class')).not.toContain('-ml-');
    expect(goldIcons[1].getAttribute('class')).toContain('-ml-2.5');
    expect(screen.queryByTestId('tally-bronze')).toBeNull();
  });

  it('collapses to one icon plus a count from 6 up', () => {
    render(<MedalTally medals={{ gold: 6, silver: 0, bronze: 0 }} board="points" testId="tally" />);
    expect(screen.getByTestId('tally-gold').querySelectorAll('svg')).toHaveLength(1);
    expect(screen.getByTestId('tally-gold-count').textContent).toBe('6');
    expect(screen.getByTestId('tally').getAttribute('aria-label')).toBe('6 gold Points medals');
  });

  it('orders the items gold, silver, bronze', () => {
    render(<MedalTally medals={{ gold: 1, silver: 2, bronze: 3 }} board="accuracy" testId="tally" />);
    const kinds = Array.from(screen.getByTestId('tally').children).map((el) => el.getAttribute('data-testid'));
    expect(kinds).toEqual(['tally-gold', 'tally-silver', 'tally-bronze']);
  });

  it('paints icons from the theme colours and uses no emoji', () => {
    render(<MedalTally medals={{ gold: 1, silver: 0, bronze: 0 }} board="points" testId="tally" />);
    const svg = screen.getByTestId('tally').querySelector('svg');
    const fills = Array.from(svg?.querySelectorAll('[fill]') ?? []).map((el) => el.getAttribute('fill'));
    expect(fills.length).toBeGreaterThan(0);
    expect(fills.every((fill) => fill?.startsWith('oklch'))).toBe(true);
    expect(screen.getByTestId('tally').textContent).not.toMatch(/[\u{1F947}-\u{1F949}]/u);
  });
});
