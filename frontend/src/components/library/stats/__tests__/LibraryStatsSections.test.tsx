// @vitest-environment jsdom
/**
 * Phase 239 D-00a..D-00k, D-01..D-05: the Flaw Stats section of the Library Stats tab on
 * the real hooks with a mocked API client. The TC store is module-level state, so each test
 * loads a fresh copy of the component (the dynamic import lives in beforeEach, never in a
 * test body).
 */

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { act, cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { DEFAULT_FILTERS } from '@/components/filters/FilterPanel';
import type { FlawComparisonResponse, FlawStatsResponse } from '@/types/library';
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
  CoverageSignupButton: () => <button data-testid="btn-coverage-signup" />,
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
  analyzed_n: 2841,
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

function renderSections(isGuest = false): void {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(
    <QueryClientProvider client={client}>
      <LibraryStatsSections filters={DEFAULT_FILTERS} isGuest={isGuest} />
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
    expect(screen.getByTestId('tc-switch-library-stats-blitz')).not.toBeNull();
    expect(screen.getByTestId('tc-switch-library-stats-rapid')).not.toBeNull();
    expect(screen.queryByTestId('tc-switch-library-stats-bullet')).toBeNull();
    expect(
      screen.getByTestId('tc-switch-library-stats-rapid').getAttribute('aria-pressed'),
    ).toBe('true');
    expect(text('flaw-stats-basis')).toBe('1,841 of 1,841 rapid games analyzed in the current filters.');
  });

  it('is the only TC switch on the page: no section carries its own', async () => {
    await renderLoaded();
    expect(screen.getAllByRole('group', { name: 'Time control' })).toHaveLength(1);
    expect(screen.queryByTestId('tc-switch-library-vs-opponents')).toBeNull();
    expect(screen.queryByTestId('tc-switch-library-tactics')).toBeNull();
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

describe('coverage basis line', () => {
  it('shows per-TC analyzed of total, pulsing the cpu icon while incomplete', async () => {
    mocks.getFlawComparison.mockResolvedValue(
      makeComparison([BLITZ_ENTRY, makeTcEntry('rapid', { analyzedN: 1768, totalN: 1790 })]),
    );
    await renderLoaded();
    expect(text('flaw-stats-basis')).toBe('1,768 of 1,790 rapid games analyzed in the current filters.');
    expect(screen.getByTestId('flaw-stats-coverage-info')).not.toBeNull();
    expect(screen.queryByTestId('btn-coverage-signup')).toBeNull();
  });

  it('offers guests the sign-up CTA only below the low-coverage threshold', async () => {
    mocks.getFlawComparison.mockResolvedValue(
      makeComparison([makeTcEntry('rapid', { analyzedN: 30, totalN: 300 })]),
    );
    renderSections(true);
    await screen.findByTestId('flaw-tiles');
    expect(screen.getByTestId('btn-coverage-signup')).not.toBeNull();
  });

  it('shows no CTA to a guest whose selected TC is mostly analyzed', async () => {
    renderSections(true);
    await screen.findByTestId('flaw-tiles');
    expect(screen.queryByTestId('btn-coverage-signup')).toBeNull();
  });
});

describe('TC switch (D-02, D-05)', () => {
  it('re-renders the tiles for the clicked TC, tracks once, and makes no new request', async () => {
    await renderLoaded();
    expect(mocks.getFlawComparison).toHaveBeenCalledTimes(1);
    expect(mocks.getFlawStats).toHaveBeenCalledTimes(1);

    fireEvent.click(screen.getByTestId('tc-switch-library-stats-blitz'));

    await waitFor(() => expect(text('flaw-tile-blunder-rate')).toBe('5.46'));
    expect(text('flaw-tile-blunder-opponents')).toBe('Opponents 6.12');
    expect(text('flaw-stats-basis')).toBe('1,000 of 1,000 blitz games analyzed in the current filters.');
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
    fireEvent.click(screen.getByTestId('tc-switch-library-stats-rapid'));
    expect(mocks.trackFeature).not.toHaveBeenCalled();
  });

  it('remembers the choice under library_stats_tc', async () => {
    await renderLoaded();
    fireEvent.click(screen.getByTestId('tc-switch-library-stats-blitz'));
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

  it('does not pin a tactic-based default while the flaw comparison is loading', async () => {
    // Tactics alone would default to blitz (their only TC); the flaw list defaults to rapid.
    let resolveFlaw: (value: FlawComparisonResponse) => void = () => {};
    mocks.getFlawComparison.mockReturnValue(
      new Promise<FlawComparisonResponse>((resolve) => {
        resolveFlaw = resolve;
      }),
    );
    mocks.getTacticComparison.mockResolvedValue(makeTacticComparison([BLITZ_TACTIC_ENTRY]));
    renderSections();
    // Let the tactic query settle while the flaw comparison is still pending.
    await act(() => new Promise((resolve) => setTimeout(resolve, 20)));
    await act(async () => resolveFlaw(makeComparison([BLITZ_ENTRY, RAPID_ENTRY])));
    await screen.findByTestId('flaw-tiles');
    expect(
      screen.getByTestId('tc-switch-library-stats-rapid').getAttribute('aria-pressed'),
    ).toBe('true');
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
    fireEvent.click(screen.getByTestId('tc-switch-library-stats-bullet'));

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
    expect(screen.queryByTestId('tc-switch-library-stats')).toBeNull();
    expect(screen.queryByTestId('flaw-tiles')).toBeNull();
  });

  it('shows LoadError, not the empty copy, when the comparison query fails', async () => {
    mocks.getFlawComparison.mockRejectedValue(new Error('boom'));
    renderSections();
    expect(await screen.findByText(/Failed to load flaw statistics/)).not.toBeNull();
    expect(screen.queryByText('No analyzed games in the current filters yet.')).toBeNull();
    expect(screen.queryByTestId('tc-switch-library-stats')).toBeNull();
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
    expect(section.querySelectorAll('[data-testid^="context-card-"][data-testid$="-axis"]')).toHaveLength(4);
    const order = [
      screen.getByTestId('flaw-stats-section'),
      section,
      screen.getByTestId('tactic-motifs-section'),
    ];
    expect(order[0]!.compareDocumentPosition(order[1]!) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    expect(order[1]!.compareDocumentPosition(order[2]!) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
  });

  it('renders the Clock by game phase heatmap between the Clock and Lost advantages cards', async () => {
    await renderLoaded();
    const section = screen.getByTestId('vs-opponents-section');
    const clock = within(section).getByTestId('context-card-clock');
    const lost = within(section).getByTestId('context-card-lost-advantages');
    const heatmap = within(section).getByTestId('tempo-phase-card');
    expect(clock.compareDocumentPosition(heatmap) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    expect(heatmap.compareDocumentPosition(lost) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    expect(heatmap.querySelectorAll('[data-testid^="tempo-phase-cell-"][data-testid$="-words"]')).toHaveLength(9);
  });

  it('follows the page switch, with no new request (D-02)', async () => {
    await renderLoaded();
    expect(screen.getByTestId('gap-popover-low-clock-tc-rapid')).not.toBeNull();
    fireEvent.click(screen.getByTestId('tc-switch-library-stats-blitz'));
    await waitFor(() => expect(screen.getByTestId('gap-popover-low-clock-tc-blitz')).not.toBeNull());
    expect(mocks.getFlawComparison).toHaveBeenCalledTimes(1);
  });

  it('shows only the gate slot below the gate, with no cards (D-03)', async () => {
    mocks.getFlawComparison.mockResolvedValue(
      makeComparison([makeTcEntry('bullet', { analyzedN: 12 }), RAPID_ENTRY]),
    );
    await renderLoaded();
    fireEvent.click(screen.getByTestId('tc-switch-library-stats-bullet'));

    await waitFor(() =>
      expect(text('vs-opponents-gate')).toBe('Not enough analyzed games yet (12 of 20)'),
    );
    expect(screen.queryByTestId('context-tag-cards')).toBeNull();
    expect(screen.queryByTestId('tempo-phase-card')).toBeNull();
  });

  it('shows the empty copy and no switch when no TC has analyzed games', async () => {
    mocks.getFlawComparison.mockResolvedValue(makeComparison([]));
    renderSections();
    await screen.findAllByText('No analyzed games in the current filters yet.');
    expect(within(screen.getByTestId('vs-opponents-section')).getByText('No analyzed games in the current filters yet.')).not.toBeNull();
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
  it('renders the one tactic card for the selected TC (D-17)', async () => {
    await renderLoaded();
    const section = screen.getByTestId('tactic-motifs-section');
    expect(await within(section).findByTestId('most-common-tactics')).not.toBeNull();
    expect(within(section).getAllByTestId('tactic-card')).toHaveLength(1);
    expect(text('tactic-cell-fork-missed-side')).toBe('Missed · 84');
    expect(text('tactic-cell-fork-missed-bar-words')).toBe('2.2 more');
  });

  it('switches to the page-switch TC with no new request (D-02)', async () => {
    await renderLoaded();
    await screen.findByTestId('most-common-tactics');
    expect(mocks.getTacticComparison).toHaveBeenCalledTimes(1);

    fireEvent.click(screen.getByTestId('tc-switch-library-stats-blitz'));

    await waitFor(() => expect(text('tactic-cell-fork-missed-side')).toBe('Missed · 30'));
    expect(text('tactic-cell-fork-missed-bar-words')).toBe('1.8 more');
    // The selected TC is a client-side pick: the query key is unchanged, so no refetch.
    expect(mocks.getTacticComparison).toHaveBeenCalledTimes(1);
  });

  it('says so, instead of showing another TC, when the tactic payload lacks the switch TC', async () => {
    mocks.getTacticComparison.mockResolvedValue(makeTacticComparison([RAPID_TACTIC_ENTRY]));
    await renderLoaded();
    await screen.findByTestId('most-common-tactics');
    fireEvent.click(screen.getByTestId('tc-switch-library-stats-blitz'));
    await waitFor(() =>
      expect(
        within(screen.getByTestId('tactic-motifs-section')).getByText(
          'No tactic data for this time control yet.',
        ),
      ).not.toBeNull(),
    );
    expect(screen.queryByTestId('most-common-tactics')).toBeNull();
  });

  it('shows only the gate slot below the gate, with no tactic card (D-03)', async () => {
    mocks.getTacticComparison.mockResolvedValue(
      makeTacticComparison([makeTacticTcEntry('bullet', 12), RAPID_TACTIC_ENTRY]),
    );
    mocks.getFlawComparison.mockResolvedValue(
      makeComparison([makeTcEntry('bullet', { analyzedN: 12 }), RAPID_ENTRY]),
    );
    await renderLoaded();
    await screen.findByTestId('most-common-tactics');
    fireEvent.click(screen.getByTestId('tc-switch-library-stats-bullet'));

    await waitFor(() =>
      expect(text('tactic-motifs-gate')).toBe('Not enough analyzed games yet (12 of 20)'),
    );
    expect(screen.queryByTestId('most-common-tactics')).toBeNull();
  });

  it('shows LoadError, not the empty copy, when the tactic query fails', async () => {
    mocks.getTacticComparison.mockRejectedValue(new Error('boom'));
    await renderLoaded();
    expect(await screen.findByText(/Failed to load tactic comparison/)).not.toBeNull();
    expect(screen.queryByTestId('most-common-tactics')).toBeNull();
    // The other sections are unaffected.
    expect(text('flaw-tile-blunder-rate')).toBe('5.22');
  });

  it('does not mention the benchmark zone mapping or a top-N / More tactics list (D-00h, D-09)', async () => {
    await renderLoaded();
    await screen.findByTestId('most-common-tactics');
    // Even in an open popover: the blitz/bullet-reads-rapid stopgap is deliberately silent.
    fireEvent.click(screen.getByTestId('gap-popover-tactic-fork-missed-tc-rapid'));
    const rendered = `${text('tactic-motifs-section')}\n${text('gap-popover-tactic-fork-missed-tc-rapid-popover')}`;
    expect(rendered).not.toMatch(/more tactics|stopgap|mapped|zone/i);
    expect(screen.queryByTestId('tactic-grid-more-tactics')).toBeNull();
  });
});
