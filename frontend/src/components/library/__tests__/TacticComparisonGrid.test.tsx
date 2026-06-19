// @vitest-environment jsdom
/**
 * TacticComparisonGrid vitest suite (Phase 126, TACUI-02).
 *
 * Tests:
 * (a) below_gate=true → CTA testid present, grid absent, shows "N of 20"
 * (b) below_gate=false with 6 bullets → grid testid, 6 family cards, 6 bullet rows + popovers
 * (c) zero-event bullet renders "No events" placeholder, NOT a MiniBulletChart
 * (d) isError → error copy rendered
 * (e) isLoading → loading skeleton testid
 * (f) non-beta user → renders null (D-01 beta gate)
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
};

/** All 6 family keys in canonical TACTIC_COMPARISON_FAMILIES order */
const ALL_FAMILIES = ['fork', 'pin_skewer', 'discovery', 'mate', 'hanging', 'combinations'];

function makeBullet(family: string, overrides: Partial<TacticBullet> = {}): TacticBullet {
  return {
    family,
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

function make6Bullets(overrides: Partial<TacticBullet> = {}): TacticBullet[] {
  return ALL_FAMILIES.map((family) => makeBullet(family, overrides));
}

function makeResponse(overrides: Partial<TacticComparisonResponse> = {}): TacticComparisonResponse {
  return {
    bullets: make6Bullets(),
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

  it('renders exactly 6 family card testids (one per API bullet)', () => {
    mockBeta(true);
    vi.mocked(useTacticComparison).mockReturnValue({
      isLoading: false,
      isError: false,
      data: makeResponse(),
    } as ReturnType<typeof useTacticComparison>);

    const { container } = renderGrid();

    const cards = container.querySelectorAll(
      '[data-testid="tactic-comparison-grid"] [data-testid^="tactic-family-card-"]',
    );
    expect(cards).toHaveLength(6);

    for (const family of ALL_FAMILIES) {
      expect(screen.queryByTestId(`tactic-family-card-${family}`)).not.toBeNull();
    }
  });

  it('every bullet row has a tactic-bullet-popover-{family} with aria-label (TACUI-02)', () => {
    mockBeta(true);
    vi.mocked(useTacticComparison).mockReturnValue({
      isLoading: false,
      isError: false,
      data: makeResponse(),
    } as ReturnType<typeof useTacticComparison>);

    renderGrid();

    for (const family of ALL_FAMILIES) {
      const popover = screen.queryByTestId(`tactic-bullet-popover-${family}`);
      expect(popover, `expected popover for family=${family}`).not.toBeNull();
      expect(popover?.getAttribute('aria-label')).toBeTruthy();
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

describe('TacticComparisonGrid — zero-event bullet', () => {
  it('zero-event bullet renders "No events" placeholder, NOT a MiniBulletChart', () => {
    mockBeta(true);
    const bullets = make6Bullets();
    // Override 'fork' to zero-event
    const forkIdx = bullets.findIndex((b) => b.family === 'fork');
    if (forkIdx !== -1) {
      bullets[forkIdx] = makeBullet('fork', {
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

    const forkRow = container.querySelector('[data-testid="tactic-bullet-row-fork"]');
    expect(forkRow).not.toBeNull();

    // Should show the placeholder text
    expect(forkRow?.textContent).toContain('No events');

    // Should NOT contain a mini-bullet-chart inside this row
    expect(forkRow?.querySelector('[data-testid="mini-bullet-chart"]')).toBeNull();
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
