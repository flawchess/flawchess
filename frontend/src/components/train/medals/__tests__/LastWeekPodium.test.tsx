// @vitest-environment jsdom
import { afterEach, describe, expect, it } from 'vitest';
import { cleanup, render, screen } from '@testing-library/react';
import { LastWeekPodium } from '@/components/train/medals/LastWeekPodium';
import type { LeaderboardLastWeek } from '@/types/train';

afterEach(cleanup);

function lastWeek(podium: LeaderboardLastWeek['podium']): LeaderboardLastWeek {
  return { week_start: '2032-01-05', podium, viewer_final_rank: null };
}

describe('LastWeekPodium', () => {
  it('renders nothing when last_week is null', () => {
    const { container } = render(<LastWeekPodium lastWeek={null} />);
    expect(container.firstChild).toBeNull();
  });

  it('renders nothing for an empty podium', () => {
    const { container } = render(<LastWeekPodium lastWeek={lastWeek([])} />);
    expect(container.firstChild).toBeNull();
  });

  it('renders every tied entry in server order', () => {
    render(
      <LastWeekPodium
        lastWeek={lastWeek([
          { medal: 'gold', name: 'alice', is_viewer: false },
          { medal: 'silver', name: 'bob', is_viewer: false },
          { medal: 'silver', name: 'carol', is_viewer: false },
          { medal: 'bronze', name: 'dave', is_viewer: false },
        ])}
      />,
    );
    // The medal SVG draws its place number as <text>; leave it out of the name check.
    const names = [0, 1, 2, 3].map((i) => {
      const entry = screen.getByTestId(`train-leaderboard-podium-entry-${i}`).cloneNode(true) as HTMLElement;
      entry.querySelectorAll('svg').forEach((svg) => svg.remove());
      return entry.textContent;
    });
    expect(names).toEqual(['Goldalice', 'Silverbob', 'Silvercarol', 'Bronzedave']);
  });

  it('gives screen readers the medal label through sr-only text', () => {
    render(<LastWeekPodium lastWeek={lastWeek([{ medal: 'bronze', name: 'dave', is_viewer: false }])} />);
    const label = screen.getByText('Bronze');
    expect(label.className).toContain('sr-only');
  });

  it("highlights only the viewer's own entry", () => {
    render(
      <LastWeekPodium
        lastWeek={lastWeek([
          { medal: 'gold', name: 'alice', is_viewer: false },
          { medal: 'silver', name: 'me', is_viewer: true },
        ])}
      />,
    );
    const mine = screen.getByTestId('train-leaderboard-podium-entry-1');
    expect(mine.getAttribute('data-viewer')).toBe('true');
    expect(mine.getAttribute('aria-current')).toBe('true');
    expect(screen.getByText('me').className).toContain('font-semibold');
    const other = screen.getByTestId('train-leaderboard-podium-entry-0');
    expect(other.getAttribute('data-viewer')).toBeNull();
    expect(other.getAttribute('aria-current')).toBeNull();
    expect(screen.getByText('alice').className).not.toContain('font-semibold');
  });

  it('shows the "Last week:" lead-in', () => {
    render(<LastWeekPodium lastWeek={lastWeek([{ medal: 'gold', name: 'alice', is_viewer: false }])} />);
    expect(screen.getByTestId('train-leaderboard-podium').textContent).toContain('Last week:');
  });
});
