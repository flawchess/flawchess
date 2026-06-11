// @vitest-environment jsdom
/**
 * FlawComparisonGrid vitest suite (Phase 115, FLAWUI-06).
 *
 * Tests:
 * (a) below_gate=true → CTA testid present, grid absent, shows "N of 20"
 * (b) below_gate=false with 15 bullets → grid testid, 6 family headers,
 *     15 flaw-bullet-row-{tag} rows, every row has a flaw-bullet-popover-{tag}
 *     with aria-label (FLAWUI-06)
 * (c) zero-event bullet renders "No events" placeholder, NOT a MiniBulletChart
 * (d) isError → error copy rendered
 */

import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, render, screen } from '@testing-library/react';

// The grid self-fetches via useLibraryFlawComparison — mock the hook module
// so tests don't require a QueryClientProvider or a real backend.
vi.mock('@/hooks/useLibrary', () => ({
  useLibraryFlawComparison: vi.fn(),
}));

import { FlawComparisonGrid } from '../FlawComparisonGrid';
import { useLibraryFlawComparison } from '@/hooks/useLibrary';
import type { FlawComparisonResponse, FlawBullet } from '@/types/library';
import type { FilterState } from '@/components/filters/FilterPanel';
import type { FlawFilterState } from '@/hooks/useFlawFilterStore';

afterEach(() => {
  cleanup();
});

// ── Test fixtures ─────────────────────────────────────────────────────────────

const DEFAULT_FILTERS: FilterState = {
  timeControls: null,
  platforms: null,
  rated: null,
  opponentType: 'human',
  opponentStrength: null,
  recency: null,
  playedAs: 'either',
};

const DEFAULT_FLAW_FILTER: FlawFilterState = {
  severity: ['blunder', 'mistake'],
  tags: [],
};

/** All 15 tags in family-registry order */
const ALL_TAGS = [
  'flaw_rate', 'blunder', 'mistake',
  'low_clock', 'hasty', 'unrushed',
  'opening', 'middlegame', 'endgame_phase',
  'miss', 'lucky',
  'reversed', 'squandered',
  'hasty_miss', 'low_clock_miss',
];

function makeBullet(tag: string, overrides: Partial<FlawBullet> = {}): FlawBullet {
  return {
    tag,
    delta: 0.1,
    ci_low: -0.05,
    ci_high: 0.25,
    player_rate: 1.2,
    opp_rate: 1.1,
    p_value: 0.04,
    player_events: 10,
    opp_events: 8,
    zone_lo: -0.1,
    zone_hi: 0.1,
    domain: 0.5,
    has_zone: true,
    ...overrides,
  };
}

function make15Bullets(overrides: Partial<FlawBullet> = {}): FlawBullet[] {
  return ALL_TAGS.map((tag) => makeBullet(tag, overrides));
}

function makeResponse(overrides: Partial<FlawComparisonResponse> = {}): FlawComparisonResponse {
  return {
    bullets: make15Bullets(),
    analyzed_n: 25,
    analyzed_gate: 20,
    below_gate: false,
    ...overrides,
  };
}

// ── Test helper ───────────────────────────────────────────────────────────────

function renderGrid() {
  return render(
    <FlawComparisonGrid
      filters={DEFAULT_FILTERS}
      flawFilter={DEFAULT_FLAW_FILTER}
    />,
  );
}

// ── Tests ─────────────────────────────────────────────────────────────────────

describe('FlawComparisonGrid — below-gate CTA (D-10)', () => {
  it('shows CTA testid when below_gate=true, not the grid', () => {
    vi.mocked(useLibraryFlawComparison).mockReturnValue({
      isLoading: false,
      isError: false,
      data: makeResponse({ below_gate: true, analyzed_n: 12, bullets: [] }),
    } as ReturnType<typeof useLibraryFlawComparison>);

    renderGrid();

    expect(screen.queryByTestId('flaw-comparison-gate-cta')).not.toBeNull();
    expect(screen.queryByTestId('flaw-comparison-grid')).toBeNull();
  });

  it('CTA text shows current analyzed_n and gate (e.g. "12 of 20")', () => {
    vi.mocked(useLibraryFlawComparison).mockReturnValue({
      isLoading: false,
      isError: false,
      data: makeResponse({ below_gate: true, analyzed_n: 12, analyzed_gate: 20, bullets: [] }),
    } as ReturnType<typeof useLibraryFlawComparison>);

    renderGrid();

    // The CTA must show both the current count and the gate
    const cta = screen.getByTestId('flaw-comparison-gate-cta');
    expect(cta.textContent).toContain('12');
    expect(cta.textContent).toContain('20');
  });
});

describe('FlawComparisonGrid — full grid (below_gate=false)', () => {
  it('renders grid testid when below_gate=false', () => {
    vi.mocked(useLibraryFlawComparison).mockReturnValue({
      isLoading: false,
      isError: false,
      data: makeResponse(),
    } as ReturnType<typeof useLibraryFlawComparison>);

    renderGrid();

    expect(screen.queryByTestId('flaw-comparison-grid')).not.toBeNull();
    expect(screen.queryByTestId('flaw-comparison-gate-cta')).toBeNull();
  });

  it('renders exactly 6 family card headers', () => {
    vi.mocked(useLibraryFlawComparison).mockReturnValue({
      isLoading: false,
      isError: false,
      data: makeResponse(),
    } as ReturnType<typeof useLibraryFlawComparison>);

    const { container } = renderGrid();

    // Each family is now a Card with a CardHeader carrying a flaw-family-header testid.
    const headers = container.querySelectorAll(
      '[data-testid="flaw-comparison-grid"] [data-testid^="flaw-family-header-"]',
    );
    expect(headers).toHaveLength(6);

    // Verify all 6 family names are present
    const headerTexts = Array.from(headers).map((h) => h.textContent?.trim());
    expect(headerTexts).toContain('Severity');
    expect(headerTexts).toContain('Tempo');
    expect(headerTexts).toContain('Phase');
    expect(headerTexts).toContain('Opportunity');
    expect(headerTexts).toContain('Impact');
    expect(headerTexts).toContain('Combos');
  });

  it('renders exactly 15 flaw-bullet-row-{tag} rows', () => {
    vi.mocked(useLibraryFlawComparison).mockReturnValue({
      isLoading: false,
      isError: false,
      data: makeResponse(),
    } as ReturnType<typeof useLibraryFlawComparison>);

    renderGrid();

    for (const tag of ALL_TAGS) {
      expect(screen.queryByTestId(`flaw-bullet-row-${tag}`)).not.toBeNull();
    }
  });

  it('every bullet row has a flaw-bullet-popover-{tag} with aria-label (FLAWUI-06)', () => {
    vi.mocked(useLibraryFlawComparison).mockReturnValue({
      isLoading: false,
      isError: false,
      data: makeResponse(),
    } as ReturnType<typeof useLibraryFlawComparison>);

    renderGrid();

    for (const tag of ALL_TAGS) {
      const popover = screen.queryByTestId(`flaw-bullet-popover-${tag}`);
      expect(popover, `expected popover for tag=${tag}`).not.toBeNull();
      // aria-label must be present on the trigger button
      expect(popover?.getAttribute('aria-label')).toBeTruthy();
    }
  });
});

describe('FlawComparisonGrid — zero-event bullet (D-11)', () => {
  it('zero-event bullet renders "No events" placeholder, NOT a MiniBulletChart', () => {
    const bullets = make15Bullets();
    // Override flaw_rate to zero-event
    const zeroIdx = bullets.findIndex((b) => b.tag === 'flaw_rate');
    if (zeroIdx !== -1) {
      bullets[zeroIdx] = makeBullet('flaw_rate', {
        delta: null,
        ci_low: null,
        ci_high: null,
        player_rate: null,
        opp_rate: null,
        p_value: null,
        player_events: 0,
        opp_events: 0,
      });
    }

    vi.mocked(useLibraryFlawComparison).mockReturnValue({
      isLoading: false,
      isError: false,
      data: makeResponse({ bullets }),
    } as ReturnType<typeof useLibraryFlawComparison>);

    const { container } = renderGrid();

    const flawRateRow = container.querySelector('[data-testid="flaw-bullet-row-flaw_rate"]');
    expect(flawRateRow).not.toBeNull();

    // Should show the placeholder text
    expect(flawRateRow?.textContent).toContain('No events');

    // Should NOT contain a mini-bullet-chart inside this row
    expect(flawRateRow?.querySelector('[data-testid="mini-bullet-chart"]')).toBeNull();
  });
});

describe('FlawComparisonGrid — error state (D-CLAUDE)', () => {
  it('isError → renders error copy', () => {
    vi.mocked(useLibraryFlawComparison).mockReturnValue({
      isLoading: false,
      isError: true,
      data: undefined,
    } as ReturnType<typeof useLibraryFlawComparison>);

    renderGrid();

    // CLAUDE.md error copy — LoadError component text
    expect(screen.getByText(/Failed to load comparison/i)).not.toBeNull();
    expect(screen.getByText(/Something went wrong/i)).not.toBeNull();
  });
});

describe('FlawComparisonGrid — loading state', () => {
  it('isLoading → renders loading skeleton testid', () => {
    vi.mocked(useLibraryFlawComparison).mockReturnValue({
      isLoading: true,
      isError: false,
      data: undefined,
    } as ReturnType<typeof useLibraryFlawComparison>);

    renderGrid();

    expect(screen.queryByTestId('flaw-comparison-loading')).not.toBeNull();
    expect(screen.queryByTestId('flaw-comparison-grid')).toBeNull();
  });
});
