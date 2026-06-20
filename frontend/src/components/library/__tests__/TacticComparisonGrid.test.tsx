// @vitest-environment jsdom
/**
 * TacticComparisonGrid vitest suite (Phase 126 TACUI-02, extended Phase 129 TACUI-08).
 *
 * Tests:
 * (a) below_gate=true → CTA testid present, grid absent, shows "N of 20"
 * (b) below_gate=false with bullets → grid testid, family cards, bullet rows + popovers
 * (c) zero-event bullet renders "No events" placeholder, NOT a MiniBulletChart
 * (d) isError → error copy rendered
 * (e) isLoading → loading skeleton testid
 * (f) non-beta user → renders null (D-01 beta gate)
 * Phase 129 (TACUI-08 / D-13/D-14):
 * (g) each family card has both tactic-grid-missed-{family} and tactic-grid-allowed-{family} rows
 * (h) first 6 families render in the main grid; remaining families inside tactic-grid-more-tactics
 * (i) families render in server order (no client re-sort)
 * (j) ≤6 families → no More Tactics accordion renders
 * (k) no orientation toggle present on the grid (D-09)
 */

import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, render, screen } from '@testing-library/react';

// The grid self-fetches via useTacticComparison — mock the hook module.
vi.mock('@/hooks/useLibrary', () => ({
  useTacticComparison: vi.fn(),
}));

// Beta gate reads beta_enabled from useUserProfile — mock it so tests control the flag.
vi.mock('@/hooks/useUserProfile', () => ({
  useUserProfile: vi.fn(),
}));

import { TacticComparisonGrid } from '../TacticComparisonGrid';
import { useTacticComparison } from '@/hooks/useLibrary';
import { useUserProfile } from '@/hooks/useUserProfile';
import type { TacticComparisonResponse, TacticBullet } from '@/types/library';
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
  tacticFamilies: [],
  tacticOrientation: 'either',
  tacticDepthPreset: 'intermediate',
  tacticDepthMax: 6,
};

/** All 10 family keys in canonical TACTIC_COMPARISON_FAMILIES order (plan 129-05) */
const ALL_FAMILIES = [
  'fork', 'skewer', 'pin', 'x_ray', 'double_check', 'discovered_check',
  'discovered_attack', 'trapped_piece', 'hanging', 'mate',
];

/** First 6 families (main grid) for tests that need the top-6 set */
const FIRST_SIX_FAMILIES = ALL_FAMILIES.slice(0, 6);

function makeBullet(
  family: string,
  orientation: 'missed' | 'allowed',
  overrides: Partial<TacticBullet> = {},
): TacticBullet {
  return {
    family,
    orientation,
    you_rate: 1.2,
    opp_rate: 1.0,
    delta: 0.2,
    ci_low: 0.05,
    ci_high: 0.35,
    p_value: 0.02,
    you_events: 12,
    opp_events: 10,
    zone_lo: 0.0,
    zone_hi: 0.0,
    has_zone: false,
    ...overrides,
  };
}

/** Dual-orientation bullets for a list of families (missed then allowed per family). */
function makeDualBullets(families: string[]): TacticBullet[] {
  const bullets: TacticBullet[] = [];
  for (const family of families) {
    bullets.push(makeBullet(family, 'missed'));
    bullets.push(makeBullet(family, 'allowed'));
  }
  return bullets;
}

/** Dual-orientation bullets for all 10 families (drives overflow accordion in real taxonomy). */
function make10Bullets(): TacticBullet[] {
  return makeDualBullets(ALL_FAMILIES);
}

/** Dual-orientation bullets for the first 6 families (no overflow accordion). */
function make6Bullets(): TacticBullet[] {
  return makeDualBullets(FIRST_SIX_FAMILIES);
}

function makeResponse(overrides: Partial<TacticComparisonResponse> = {}): TacticComparisonResponse {
  return {
    bullets: make10Bullets(),
    analyzed_n: 25,
    analyzed_gate: 20,
    below_gate: false,
    ...overrides,
  };
}

// ── Test helper ───────────────────────────────────────────────────────────────

function renderGrid() {
  return render(
    <TacticComparisonGrid filters={DEFAULT_FILTERS} flawFilter={DEFAULT_FLAW_FILTER} />,
  );
}

/** Mock useUserProfile with a beta_enabled value (the beta gate's real source). */
function mockBeta(betaEnabled: boolean) {
  vi.mocked(useUserProfile).mockReturnValue({
    data: { beta_enabled: betaEnabled },
    isLoading: false,
  } as ReturnType<typeof useUserProfile>);
}

// ── Tests ─────────────────────────────────────────────────────────────────────

describe('TacticComparisonGrid — beta gate (D-01)', () => {
  it('non-beta user → renders null', () => {
    mockBeta(false);
    vi.mocked(useTacticComparison).mockReturnValue({
      isLoading: false,
      isError: false,
      data: makeResponse(),
    } as ReturnType<typeof useTacticComparison>);

    const { container } = renderGrid();

    // Nothing rendered for non-beta users
    expect(container.firstChild).toBeNull();
  });
});

describe('TacticComparisonGrid — below-gate CTA', () => {
  it('shows CTA testid when below_gate=true, not the grid', () => {
    mockBeta(true);
    vi.mocked(useTacticComparison).mockReturnValue({
      isLoading: false,
      isError: false,
      data: makeResponse({ below_gate: true, analyzed_n: 12, bullets: [] }),
    } as ReturnType<typeof useTacticComparison>);

    renderGrid();

    expect(screen.queryByTestId('tactic-comparison-gate-cta')).not.toBeNull();
    expect(screen.queryByTestId('tactic-comparison-grid')).toBeNull();
  });

  it('CTA text shows current analyzed_n and gate (e.g. "12 of 20")', () => {
    mockBeta(true);
    vi.mocked(useTacticComparison).mockReturnValue({
      isLoading: false,
      isError: false,
      data: makeResponse({ below_gate: true, analyzed_n: 12, analyzed_gate: 20, bullets: [] }),
    } as ReturnType<typeof useTacticComparison>);

    renderGrid();

    const cta = screen.getByTestId('tactic-comparison-gate-cta');
    expect(cta.textContent).toContain('12');
    expect(cta.textContent).toContain('20');
  });
});

describe('TacticComparisonGrid — full grid (below_gate=false)', () => {
  it('renders grid testid when below_gate=false', () => {
    mockBeta(true);
    vi.mocked(useTacticComparison).mockReturnValue({
      isLoading: false,
      isError: false,
      data: makeResponse(),
    } as ReturnType<typeof useTacticComparison>);

    renderGrid();

    expect(screen.queryByTestId('tactic-comparison-grid')).not.toBeNull();
    expect(screen.queryByTestId('tactic-comparison-gate-cta')).toBeNull();
  });

  it('renders exactly 6 family card testids in the main grid (top-6 of 10)', () => {
    mockBeta(true);
    vi.mocked(useTacticComparison).mockReturnValue({
      isLoading: false,
      isError: false,
      data: makeResponse(),
    } as ReturnType<typeof useTacticComparison>);

    const { container } = renderGrid();

    // Main grid contains exactly the first 6 families (overflow is in the accordion)
    const mainGridCards = container.querySelectorAll(
      '[data-testid="tactic-comparison-grid"] [data-testid^="tactic-family-card-"]',
    );
    expect(mainGridCards).toHaveLength(6);

    for (const family of FIRST_SIX_FAMILIES) {
      expect(
        container.querySelector(`[data-testid="tactic-comparison-grid"] [data-testid="tactic-family-card-${family}"]`),
        `expected family card for ${family} in main grid`,
      ).not.toBeNull();
    }
  });

  it('renders section heading "Tactic Motifs" and sub-heading', () => {
    mockBeta(true);
    vi.mocked(useTacticComparison).mockReturnValue({
      isLoading: false,
      isError: false,
      data: makeResponse(),
    } as ReturnType<typeof useTacticComparison>);

    renderGrid();

    expect(screen.getByText('Tactic Motifs')).not.toBeNull();
    expect(screen.getByText(/You vs. your opponents/i)).not.toBeNull();
  });
});

describe('TacticComparisonGrid — two-bullet cards (D-13 / TACUI-08)', () => {
  it('each main-grid family card has both tactic-grid-missed-{family} and tactic-grid-allowed-{family} rows', () => {
    mockBeta(true);
    vi.mocked(useTacticComparison).mockReturnValue({
      isLoading: false,
      isError: false,
      data: makeResponse(),
    } as ReturnType<typeof useTacticComparison>);

    renderGrid();

    // Check first 6 families (main grid). Overflow families are in the closed accordion
    // (hidden DOM) and need the accordion to be opened before their testids are accessible.
    for (const family of FIRST_SIX_FAMILIES) {
      expect(
        screen.queryByTestId(`tactic-grid-missed-${family}`),
        `expected missed row for family=${family}`,
      ).not.toBeNull();
      expect(
        screen.queryByTestId(`tactic-grid-allowed-${family}`),
        `expected allowed row for family=${family}`,
      ).not.toBeNull();
    }
  });

  it('missed row label says "Missed {FamilyName}" and allowed row says "Allowed {FamilyName}"', () => {
    mockBeta(true);
    vi.mocked(useTacticComparison).mockReturnValue({
      isLoading: false,
      isError: false,
      data: makeResponse({ bullets: makeDualBullets(['fork']) }),
    } as ReturnType<typeof useTacticComparison>);

    renderGrid();

    const missedRow = screen.getByTestId('tactic-grid-missed-fork');
    const allowedRow = screen.getByTestId('tactic-grid-allowed-fork');
    expect(missedRow.textContent).toMatch(/Missed Fork/i);
    expect(allowedRow.textContent).toMatch(/Allowed Fork/i);
  });

  it('every main-grid bullet row has a tactic-bullet-popover-{family} with aria-label (TACUI-02)', () => {
    mockBeta(true);
    vi.mocked(useTacticComparison).mockReturnValue({
      isLoading: false,
      isError: false,
      data: makeResponse(),
    } as ReturnType<typeof useTacticComparison>);

    renderGrid();

    // Check first 6 families (main grid). Overflow families are in the closed accordion.
    for (const family of FIRST_SIX_FAMILIES) {
      const popovers = screen.queryAllByTestId(`tactic-bullet-popover-${family}`);
      // Two popovers per family (one per orientation bullet)
      expect(popovers.length, `expected 2 popovers for family=${family}`).toBe(2);
      for (const popover of popovers) {
        expect(popover.getAttribute('aria-label')).toBeTruthy();
      }
    }
  });
});

describe('TacticComparisonGrid — More Tactics accordion (D-14 / TACUI-08)', () => {
  it('first 6 families render in the main grid; families 7-10 render inside tactic-grid-more-tactics (G-01)', () => {
    mockBeta(true);
    // Real 10-family taxonomy: first 6 in main grid, last 4 overflow into the accordion
    const bullets = make10Bullets();
    vi.mocked(useTacticComparison).mockReturnValue({
      isLoading: false,
      isError: false,
      data: makeResponse({ bullets }),
    } as ReturnType<typeof useTacticComparison>);

    const { container } = renderGrid();

    // Exactly 6 family cards in the main grid
    const mainGridCards = container.querySelectorAll(
      '[data-testid="tactic-comparison-grid"] > [data-testid^="tactic-family-card-"]',
    );
    expect(mainGridCards).toHaveLength(6);

    // More Tactics accordion is present with the 4 overflow families (G-01 closed)
    expect(screen.queryByTestId('tactic-grid-more-tactics')).not.toBeNull();

    // The overflow families (trapped_piece, hanging, mate + one more) should NOT appear
    // in the main grid — their cards should not be direct children of tactic-comparison-grid.
    const mainGrid = screen.getByTestId('tactic-comparison-grid');
    const overflowFamilies = ALL_FAMILIES.slice(6); // ['discovered_attack', 'trapped_piece', 'hanging', 'mate']
    for (const family of overflowFamilies) {
      expect(
        mainGrid.querySelector(`[data-testid="tactic-grid-missed-${family}"]`),
        `family=${family} should not appear in main grid`,
      ).toBeNull();
    }
    // The main grid has exactly 6 family cards.
    expect(mainGrid.querySelectorAll('[data-testid^="tactic-family-card-"]')).toHaveLength(6);
  });

  it('families render in server order — first family in response is first in grid (no client re-sort)', () => {
    mockBeta(true);
    // Server returns: fork first (by Missed you_rate desc), then skewer, pin, etc.
    const bullets = makeDualBullets(['fork', 'skewer', 'pin', 'x_ray', 'double_check', 'discovered_check']);
    vi.mocked(useTacticComparison).mockReturnValue({
      isLoading: false,
      isError: false,
      data: makeResponse({ bullets }),
    } as ReturnType<typeof useTacticComparison>);

    const { container } = renderGrid();

    const cards = container.querySelectorAll(
      '[data-testid="tactic-comparison-grid"] [data-testid^="tactic-family-card-"]',
    );
    expect(cards[0]?.getAttribute('data-testid')).toBe('tactic-family-card-fork');
    expect(cards[1]?.getAttribute('data-testid')).toBe('tactic-family-card-skewer');
  });

  it('≤6 families → no More Tactics accordion renders', () => {
    mockBeta(true);
    vi.mocked(useTacticComparison).mockReturnValue({
      isLoading: false,
      isError: false,
      data: makeResponse({ bullets: make6Bullets() }),
    } as ReturnType<typeof useTacticComparison>);

    renderGrid();

    expect(screen.queryByTestId('tactic-grid-more-tactics')).toBeNull();
  });

  it('no orientation toggle present on the grid (D-09)', () => {
    mockBeta(true);
    vi.mocked(useTacticComparison).mockReturnValue({
      isLoading: false,
      isError: false,
      data: makeResponse(),
    } as ReturnType<typeof useTacticComparison>);

    renderGrid();

    expect(screen.queryByTestId('filter-tactic-orientation')).toBeNull();
  });
});

describe('TacticComparisonGrid — zero-event bullet', () => {
  it('zero-event bullet renders "No events" placeholder, NOT a MiniBulletChart', () => {
    mockBeta(true);
    const bullets = makeDualBullets(['fork']);
    // Override the missed fork bullet to zero-event
    const forkMissedIdx = bullets.findIndex((b) => b.family === 'fork' && b.orientation === 'missed');
    if (forkMissedIdx !== -1) {
      bullets[forkMissedIdx] = makeBullet('fork', 'missed', {
        delta: null,
        ci_low: null,
        ci_high: null,
        you_rate: null,
        opp_rate: null,
        p_value: null,
        you_events: 0,
        opp_events: 0,
      });
    }

    vi.mocked(useTacticComparison).mockReturnValue({
      isLoading: false,
      isError: false,
      data: makeResponse({ bullets }),
    } as ReturnType<typeof useTacticComparison>);

    const { container } = renderGrid();

    const missedRow = container.querySelector('[data-testid="tactic-grid-missed-fork"]');
    expect(missedRow).not.toBeNull();

    // Should show the placeholder text
    expect(missedRow?.textContent).toContain('No events');

    // Should NOT contain a mini-bullet-chart inside this row
    expect(missedRow?.querySelector('[data-testid="mini-bullet-chart"]')).toBeNull();
  });
});

describe('TacticComparisonGrid — error state', () => {
  it('isError → renders error copy', () => {
    mockBeta(true);
    vi.mocked(useTacticComparison).mockReturnValue({
      isLoading: false,
      isError: true,
      data: undefined,
    } as ReturnType<typeof useTacticComparison>);

    renderGrid();

    // CLAUDE.md error copy — LoadError component text
    expect(screen.getByText(/Failed to load tactic comparison/i)).not.toBeNull();
    expect(screen.getByText(/Something went wrong/i)).not.toBeNull();
  });
});

describe('TacticComparisonGrid — loading state', () => {
  it('isLoading → renders loading skeleton testid', () => {
    mockBeta(true);
    vi.mocked(useTacticComparison).mockReturnValue({
      isLoading: true,
      isError: false,
      data: undefined,
    } as ReturnType<typeof useTacticComparison>);

    renderGrid();

    expect(screen.queryByTestId('tactic-comparison-loading')).not.toBeNull();
    expect(screen.queryByTestId('tactic-comparison-grid')).toBeNull();
  });
});
