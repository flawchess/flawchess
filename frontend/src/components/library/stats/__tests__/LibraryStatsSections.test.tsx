// @vitest-environment jsdom
/**
 * Phase 239 D-00a..D-00k, D-01..D-05: the Flaw Stats section of the Library Stats tab on
 * the real hooks with a mocked API client. The TC store is module-level state, so each test
 * loads a fresh copy of the component (the dynamic import lives in beforeEach, never in a
 * test body).
 */

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { DEFAULT_FILTERS } from '@/components/filters/FilterPanel';
import type { FlawStatsResponse } from '@/types/library';
import {
  BLITZ_ENTRY,
  BLITZ_TACTIC_ENTRY,
  RAPID_ENTRY,
  RAPID_TACTIC_ENTRY,
  SKETCH_RAPID_ENTRY,
  makeComparison,
  makeTacticComparison,
  makeTacticTcEntry,
  makeTcEntry,
  makeTrendPoint,
} from './flawStatsFixtures';

const mocks = vi.hoisted(() => ({
  getFlawComparison: vi.fn(),
  getFlawStats: vi.fn(),
  getTacticComparison: vi.fn(),
  trackFeature: vi.fn(),
}));

vi.mock('@/api/client', async (importOriginal) => ({
  ...(await importOriginal<typeof import('@/api/client')>()),
  libraryApi: {
    getFlawComparison: mocks.getFlawComparison,
    getFlawStats: mocks.getFlawStats,
    getTacticComparison: mocks.getTacticComparison,
  },
}));

vi.mock('@/lib/analytics', async (importOriginal) => ({
  ...(await importOriginal<typeof import('@/lib/analytics')>()),
  trackFeature: mocks.trackFeature,
}));

vi.mock('@/components/library/FlawTrendChart', () => ({
  FlawTrendChart: ({ trend, windowSize }: { trend: { date: string }[]; windowSize: number }) => (
    <div
      data-testid="trend-stub"
      data-dates={trend.map((p) => p.date).join(',')}
      data-window={windowSize}
    />
  ),
}));

vi.mock('@/components/library/EvalCoverageBadge', () => ({
  EvalCoverageBadge: () => <div data-testid="coverage-badge-stub" />,
}));

type SectionsModule = typeof import('../LibraryStatsSections');
let LibraryStatsSections: SectionsModule['LibraryStatsSections'];

const TREND_WINDOW = 25;
const STATS: FlawStatsResponse = {
  trend_by_tc: [
    { tc: 'blitz', points: [makeTrendPoint('2026-01-05')] },
    { tc: 'rapid', points: [makeTrendPoint('2026-02-02'), makeTrendPoint('2026-02-09')] },
  ],
  trend_window: TREND_WINDOW,
  analyzed_pct: 100,
  analyzed_n: 2841,
  total_n: 2841,
};

beforeEach(async () => {
  vi.resetModules();
  localStorage.clear();
  mocks.getFlawComparison.mockReset();
  mocks.getFlawStats.mockReset();
  mocks.getTacticComparison.mockReset();
  mocks.trackFeature.mockReset();
  mocks.getFlawComparison.mockResolvedValue(makeComparison([BLITZ_ENTRY, RAPID_ENTRY]));
  mocks.getFlawStats.mockResolvedValue(STATS);
  mocks.getTacticComparison.mockResolvedValue(
    makeTacticComparison([BLITZ_TACTIC_ENTRY, RAPID_TACTIC_ENTRY]),
  );
  ({ LibraryStatsSections } = await import('../LibraryStatsSections'));
});

afterEach(() => {
  cleanup();
  localStorage.clear();
});

function renderSections(): void {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(
    <QueryClientProvider client={client}>
      <LibraryStatsSections
        filters={DEFAULT_FILTERS}
        analyzedCount={2841}
        totalCount={2841}
        isGuest={false}
        isCoverageError={false}
      />
    </QueryClientProvider>,
  );
}

async function renderLoaded(): Promise<void> {
  renderSections();
  await screen.findByTestId('flaw-tiles');
}

function text(testId: string): string {
  return screen.getByTestId(testId).textContent ?? '';
}

describe('Flaw Stats section (default selection)', () => {
  it('shows the most populated TC with a switch of exactly the payload TCs', async () => {
    await renderLoaded();
    expect(screen.getByTestId('tc-switch-library-flaw-stats-blitz')).not.toBeNull();
    expect(screen.getByTestId('tc-switch-library-flaw-stats-rapid')).not.toBeNull();
    expect(screen.queryByTestId('tc-switch-library-flaw-stats-bullet')).toBeNull();
    expect(
      screen.getByTestId('tc-switch-library-flaw-stats-rapid').getAttribute('aria-pressed'),
    ).toBe('true');
    expect(text('flaw-stats-basis')).toBe('Your 1,841 analyzed rapid games in the current filters.');
  });

  it('renders the rapid tiles: rate, Opponents line, gap words and per-TC popover', async () => {
    await renderLoaded();
    expect(text('flaw-tile-blunder-rate')).toBe('5.22');
    expect(text('flaw-tile-blunder-opponents')).toBe('Opponents 5.83');
    expect(text('flaw-tile-blunder-bar-words')).toBe('0.61 fewer');
    expect(screen.getByTestId('gap-popover-blunder-tc-rapid')).not.toBeNull();
  });

  it('feeds the timeline the selected TC series and the window size', async () => {
    await renderLoaded();
    const trend = await screen.findByTestId('trend-stub');
    expect(trend.getAttribute('data-dates')).toBe('2026-02-02,2026-02-09');
    expect(trend.getAttribute('data-window')).toBe(String(TREND_WINDOW));
  });

  it('uses the Fredoka brand font on the three section titles (D-00j)', async () => {
    await renderLoaded();
    const headings = screen.getAllByRole('heading', { level: 2 });
    expect(headings.map((h) => h.textContent)).toEqual([
      'Flaw Stats',
      'You vs. your opponents',
      'Tactic motifs',
    ]);
    headings.forEach((h) => expect(h.className).toContain('font-brand'));
  });

});

describe('TC switch (D-02, D-05)', () => {
  it('re-renders the tiles for the clicked TC, tracks once, and makes no new request', async () => {
    await renderLoaded();
    expect(mocks.getFlawComparison).toHaveBeenCalledTimes(1);
    expect(mocks.getFlawStats).toHaveBeenCalledTimes(1);

    fireEvent.click(screen.getByTestId('tc-switch-library-flaw-stats-blitz'));

    await waitFor(() => expect(text('flaw-tile-blunder-rate')).toBe('5.46'));
    expect(text('flaw-tile-blunder-opponents')).toBe('Opponents 6.12');
    expect(text('flaw-stats-basis')).toBe('Your 1,000 analyzed blitz games in the current filters.');
    expect(screen.getByTestId('trend-stub').getAttribute('data-dates')).toBe('2026-01-05');
    expect(mocks.trackFeature).toHaveBeenCalledTimes(1);
    expect(mocks.trackFeature).toHaveBeenCalledWith('option-change', {
      target: 'library-stats-tc',
      value: 'blitz',
    });
    // The selected TC is a client-side pick: the query keys are unchanged, so no refetch.
    expect(mocks.getFlawComparison).toHaveBeenCalledTimes(1);
    expect(mocks.getFlawStats).toHaveBeenCalledTimes(1);
  });

  it('does not track a click on the already selected TC', async () => {
    await renderLoaded();
    fireEvent.click(screen.getByTestId('tc-switch-library-flaw-stats-rapid'));
    expect(mocks.trackFeature).not.toHaveBeenCalled();
  });

  it('remembers the choice under library_stats_tc', async () => {
    await renderLoaded();
    fireEvent.click(screen.getByTestId('tc-switch-library-flaw-stats-blitz'));
    expect(localStorage.getItem('library_stats_tc')).toBe('blitz');
  });

  it('restores a stored TC without tracking anything', async () => {
    localStorage.setItem('library_stats_tc', 'blitz');
    await renderLoaded();
    expect(text('flaw-tile-blunder-rate')).toBe('5.46');
    expect(mocks.trackFeature).not.toHaveBeenCalled();
  });

  it('ignores a stored TC the payload does not offer', async () => {
    localStorage.setItem('library_stats_tc', 'classical');
    await renderLoaded();
    expect(text('flaw-tile-blunder-rate')).toBe('5.22');
  });
});

describe('time controls below the gate (D-03)', () => {
  it('keeps the TC in the switch with the rate, Opponents line and the gate line', async () => {
    mocks.getFlawComparison.mockResolvedValue(
      makeComparison([
        makeTcEntry('bullet', {
          analyzedN: 12,
          blunder: { player_rate: 4.1, opp_rate: 4.6, delta: -0.5 },
        }),
        RAPID_ENTRY,
      ]),
    );
    await renderLoaded();
    fireEvent.click(screen.getByTestId('tc-switch-library-flaw-stats-bullet'));

    await waitFor(() => expect(text('flaw-tile-blunder-rate')).toBe('4.10'));
    expect(text('flaw-tile-blunder-opponents')).toBe('Opponents 4.60');
    expect(text('flaw-tile-blunder-gate')).toBe('Not enough analyzed games yet (12 of 20)');
    expect(text('flaw-tile-mistake-gate')).toBe('Not enough analyzed games yet (12 of 20)');
  });
});

describe('timeline for a TC without a series', () => {
  it('passes an empty series to the chart', async () => {
    mocks.getFlawStats.mockResolvedValue({
      ...STATS,
      trend_by_tc: [{ tc: 'blitz', points: [makeTrendPoint('2026-01-05')] }],
    });
    await renderLoaded();
    const trend = await screen.findByTestId('trend-stub');
    expect(trend.getAttribute('data-dates')).toBe('');
  });
});

describe('empty and failed states', () => {
  it('shows the empty copy and no switch when no TC has analyzed games', async () => {
    mocks.getFlawComparison.mockResolvedValue(makeComparison([]));
    mocks.getTacticComparison.mockResolvedValue(makeTacticComparison([]));
    renderSections();
    // Flaw Stats, You vs. your opponents and Tactic motifs each show the empty copy.
    await waitFor(() =>
      expect(screen.getAllByText('No analyzed games in the current filters yet.')).toHaveLength(3),
    );
    expect(screen.queryByTestId('tc-switch-library-flaw-stats')).toBeNull();
    expect(screen.queryByTestId('flaw-tiles')).toBeNull();
  });

  it('shows LoadError, not the empty copy, when the comparison query fails', async () => {
    mocks.getFlawComparison.mockRejectedValue(new Error('boom'));
    renderSections();
    expect(await screen.findByText(/Failed to load flaw statistics/)).not.toBeNull();
    expect(screen.queryByText('No analyzed games in the current filters yet.')).toBeNull();
    expect(screen.queryByTestId('tc-switch-library-flaw-stats')).toBeNull();
  });

  it('shows a timeline-only error while the tiles stay', async () => {
    mocks.getFlawStats.mockRejectedValue(new Error('boom'));
    await renderLoaded();
    expect(await screen.findByText(/Failed to load flaws timeline/)).not.toBeNull();
    expect(text('flaw-tile-blunder-rate')).toBe('5.22');
  });
});

describe('You vs. your opponents section', () => {
  beforeEach(() => {
    mocks.getFlawComparison.mockResolvedValue(makeComparison([BLITZ_ENTRY, SKETCH_RAPID_ENTRY]));
  });

  it('renders the four cards for the selected TC, between the other sections', async () => {
    await renderLoaded();
    const section = screen.getByTestId('vs-opponents-section');
    expect(section.querySelector('[data-testid="what-stands-out"]')).toBeNull();
    expect(section.querySelector('[data-testid="context-tag-cards"]')?.children).toHaveLength(4);
    const order = [
      screen.getByTestId('flaw-stats-section'),
      section,
      screen.getByTestId('tactic-motifs-section'),
    ];
    expect(order[0]!.compareDocumentPosition(order[1]!) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    expect(order[1]!.compareDocumentPosition(order[2]!) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
  });

  it('carries its own switch with the payload TCs, bound to the library-vs-opponents id', async () => {
    await renderLoaded();
    expect(screen.getByTestId('tc-switch-library-vs-opponents-blitz')).not.toBeNull();
    expect(
      screen.getByTestId('tc-switch-library-vs-opponents-rapid').getAttribute('aria-pressed'),
    ).toBe('true');
    expect(screen.queryByTestId('tc-switch-library-vs-opponents-bullet')).toBeNull();
  });

  it('a click in its switch also switches the Flaw Stats tiles, with no new request (D-02)', async () => {
    await renderLoaded();
    expect(text('flaw-tile-blunder-rate')).toBe('5.22');
    expect(mocks.getFlawComparison).toHaveBeenCalledTimes(1);

    fireEvent.click(screen.getByTestId('tc-switch-library-vs-opponents-blitz'));

    await waitFor(() => expect(text('flaw-tile-blunder-rate')).toBe('5.46'));
    expect(
      screen.getByTestId('tc-switch-library-flaw-stats-blitz').getAttribute('aria-pressed'),
    ).toBe('true');
    // The context-tag cards re-rendered for blitz.
    expect(screen.getByTestId('gap-popover-low-clock-tc-blitz')).not.toBeNull();
    expect(mocks.trackFeature).toHaveBeenCalledTimes(1);
    expect(mocks.trackFeature).toHaveBeenCalledWith('option-change', {
      target: 'library-stats-tc',
      value: 'blitz',
    });
    expect(mocks.getFlawComparison).toHaveBeenCalledTimes(1);
    expect(mocks.getFlawStats).toHaveBeenCalledTimes(1);
  });

  it('a click in the Flaw Stats switch also switches this section', async () => {
    await renderLoaded();
    fireEvent.click(screen.getByTestId('tc-switch-library-flaw-stats-blitz'));
    await waitFor(() =>
      expect(
        screen.getByTestId('tc-switch-library-vs-opponents-blitz').getAttribute('aria-pressed'),
      ).toBe('true'),
    );
    expect(screen.getByTestId('gap-popover-low-clock-tc-blitz')).not.toBeNull();
  });

  it('shows only the gate slot below the gate, with no cards (D-03)', async () => {
    mocks.getFlawComparison.mockResolvedValue(
      makeComparison([makeTcEntry('bullet', { analyzedN: 12 }), RAPID_ENTRY]),
    );
    await renderLoaded();
    fireEvent.click(screen.getByTestId('tc-switch-library-vs-opponents-bullet'));

    await waitFor(() =>
      expect(text('vs-opponents-gate')).toBe('Not enough analyzed games yet (12 of 20)'),
    );
    expect(screen.queryByTestId('context-tag-cards')).toBeNull();
    // The section heading, switch and intro stay.
    expect(screen.getByTestId('tc-switch-library-vs-opponents-bullet')).not.toBeNull();
  });

  it('shows the empty copy and no switch when no TC has analyzed games', async () => {
    mocks.getFlawComparison.mockResolvedValue(makeComparison([]));
    renderSections();
    await screen.findAllByText('No analyzed games in the current filters yet.');
    expect(within(screen.getByTestId('vs-opponents-section')).getByText('No analyzed games in the current filters yet.')).not.toBeNull();
    expect(screen.queryByTestId('tc-switch-library-vs-opponents-rapid')).toBeNull();
    expect(screen.queryByTestId('context-tag-cards')).toBeNull();
  });

  it('shows its own LoadError when the comparison query fails', async () => {
    mocks.getFlawComparison.mockRejectedValue(new Error('boom'));
    renderSections();
    expect(await screen.findByText(/Failed to load opponent comparison/)).not.toBeNull();
  });

  it('says flaws, blunders and mistakes, never events, across tiles and the cards (D-00d)', async () => {
    await renderLoaded();
    const rendered = [
      text('flaw-tiles'),
      text('context-tag-cards'),
      text('vs-opponents-section'),
    ].join('\n');
    expect(rendered).not.toMatch(/\bevents?\b/i);
    expect(rendered).toContain('flaws');
  });

  it('keeps the popover bodies free of events too (D-00d)', async () => {
    await renderLoaded();
    for (const id of [
      'gap-popover-blunder-tc-rapid',
      'gap-popover-hasty-tc-rapid',
      'gap-popover-unrushed-tc-rapid',
    ]) {
      // One popover is open at a time: open, read, then the next click closes it.
      fireEvent.click(screen.getByTestId(id));
      expect(text(`${id}-popover`)).not.toMatch(/\bevents?\b/i);
    }
  });
});

describe('Tactic motifs section (D-00h, D-02, D-03)', () => {
  it('renders the three tables for the selected TC', async () => {
    await renderLoaded();
    const section = screen.getByTestId('tactic-motifs-section');
    expect(await within(section).findByTestId('tactic-tables')).not.toBeNull();
    expect(within(section).getByTestId('tactic-group-piece_attacks')).not.toBeNull();
    expect(within(section).getByTestId('tactic-group-discoveries')).not.toBeNull();
    expect(within(section).getByTestId('tactic-group-advanced')).not.toBeNull();
    expect(text('tactic-row-fork-flaws')).toBe('218 of your flaws');
    expect(text('tactic-cell-fork-missed-bar-words')).toBe('2.2 more');
  });

  it('carries its own switch with the payload TCs, bound to the library-tactics id', async () => {
    await renderLoaded();
    expect(await screen.findByTestId('tc-switch-library-tactics-blitz')).not.toBeNull();
    expect(
      screen.getByTestId('tc-switch-library-tactics-rapid').getAttribute('aria-pressed'),
    ).toBe('true');
    expect(screen.queryByTestId('tc-switch-library-tactics-bullet')).toBeNull();
  });

  it('switches to the clicked TC with no new request and syncs the other sections (D-02)', async () => {
    await renderLoaded();
    await screen.findByTestId('tactic-tables');
    expect(mocks.getTacticComparison).toHaveBeenCalledTimes(1);

    fireEvent.click(screen.getByTestId('tc-switch-library-tactics-blitz'));

    await waitFor(() => expect(text('tactic-row-fork-flaws')).toBe('75 of your flaws'));
    expect(text('tactic-cell-fork-missed-bar-words')).toBe('1.8 more');
    expect(text('flaw-tile-blunder-rate')).toBe('5.46');
    expect(
      screen.getByTestId('tc-switch-library-vs-opponents-blitz').getAttribute('aria-pressed'),
    ).toBe('true');
    expect(mocks.trackFeature).toHaveBeenCalledTimes(1);
    expect(mocks.trackFeature).toHaveBeenCalledWith('option-change', {
      target: 'library-stats-tc',
      value: 'blitz',
    });
    // The selected TC is a client-side pick: the query key is unchanged, so no refetch.
    expect(mocks.getTacticComparison).toHaveBeenCalledTimes(1);
  });

  it('follows a click in another section switch', async () => {
    await renderLoaded();
    await screen.findByTestId('tactic-tables');
    fireEvent.click(screen.getByTestId('tc-switch-library-flaw-stats-blitz'));
    await waitFor(() => expect(text('tactic-row-fork-flaws')).toBe('75 of your flaws'));
  });

  it('shows only the gate slot below the gate, with no tables (D-03)', async () => {
    mocks.getTacticComparison.mockResolvedValue(
      makeTacticComparison([makeTacticTcEntry('bullet', 12), RAPID_TACTIC_ENTRY]),
    );
    mocks.getFlawComparison.mockResolvedValue(
      makeComparison([makeTcEntry('bullet', { analyzedN: 12 }), RAPID_ENTRY]),
    );
    await renderLoaded();
    await screen.findByTestId('tactic-tables');
    fireEvent.click(screen.getByTestId('tc-switch-library-tactics-bullet'));

    await waitFor(() =>
      expect(text('tactic-motifs-gate')).toBe('Not enough analyzed games yet (12 of 20)'),
    );
    expect(screen.queryByTestId('tactic-tables')).toBeNull();
    expect(screen.getByTestId('tc-switch-library-tactics-bullet')).not.toBeNull();
  });

  it('shows LoadError, not the empty copy, when the tactic query fails', async () => {
    mocks.getTacticComparison.mockRejectedValue(new Error('boom'));
    await renderLoaded();
    expect(await screen.findByText(/Failed to load tactic comparison/)).not.toBeNull();
    expect(screen.queryByTestId('tactic-tables')).toBeNull();
    expect(screen.queryByTestId('tc-switch-library-tactics-rapid')).toBeNull();
    // The other sections are unaffected.
    expect(text('flaw-tile-blunder-rate')).toBe('5.22');
  });

  it('does not mention the benchmark zone mapping or a top-N / More tactics list (D-00h, D-09)', async () => {
    await renderLoaded();
    await screen.findByTestId('tactic-tables');
    // Even in an open popover: the blitz/bullet-reads-rapid stopgap is deliberately silent.
    fireEvent.click(screen.getByTestId('gap-popover-tactic-fork-missed-tc-rapid'));
    const rendered = `${text('tactic-motifs-section')}\n${text('gap-popover-tactic-fork-missed-tc-rapid-popover')}`;
    expect(rendered).not.toMatch(/more tactics|stopgap|mapped|zone/i);
    expect(screen.queryByTestId('tactic-grid-more-tactics')).toBeNull();
  });
});
