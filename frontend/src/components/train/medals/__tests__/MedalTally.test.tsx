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

  it('renders one icon and count per non-zero type, with the aria-label', () => {
    render(<MedalTally medals={{ gold: 3, silver: 1, bronze: 0 }} board="points" testId="tally" />);
    const tally = screen.getByTestId('tally');
    expect(tally.getAttribute('role')).toBe('img');
    expect(tally.getAttribute('aria-label')).toBe('3 gold, 1 silver Points medals');
    // The count is the span after the icon (the SVG's own <text> is the place number).
    expect(screen.getByTestId('tally-gold').querySelector('span')?.textContent).toBe('3');
    // A single medal hides its count; only a zero-width baseline anchor remains.
    const silverCount = screen.getByTestId('tally-silver').querySelector('span');
    expect(silverCount?.textContent).not.toMatch(/\d/);
    expect(silverCount?.getAttribute('aria-hidden')).toBe('true');
    expect(screen.queryByTestId('tally-bronze')).toBeNull();
    expect(tally.querySelectorAll('svg')).toHaveLength(2);
  });

  it('shows the count from 2 up', () => {
    render(<MedalTally medals={{ gold: 2, silver: 0, bronze: 0 }} board="points" testId="tally" />);
    expect(screen.getByTestId('tally-gold').querySelector('span')?.textContent).toBe('2');
    expect(screen.getByTestId('tally').getAttribute('aria-label')).toBe('2 gold Points medals');
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
