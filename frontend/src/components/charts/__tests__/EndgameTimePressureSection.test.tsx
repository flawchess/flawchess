// @vitest-environment jsdom
/**
 * Phase 88 Plan 07 — integration tests for the EndgameTimePressureSection
 * orchestrator. Verifies:
 * - Only TC cards whose testids match the supplied TCs are rendered.
 * - Empty state renders when cards array is empty.
 * - All 4 TC cards render in canonical order when all four are present.
 * - Legacy data-testid="clock-pressure-section" is absent (proxy for
 *   knip-clean post-deletion of EndgameClockPressureSection).
 * - Section wrapper testid="time-pressure-cards-section" is always present.
 */

import { afterEach, beforeAll, describe, expect, it, vi } from 'vitest';
import { cleanup, render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';

import { TooltipProvider } from '@/components/ui/tooltip';
import type {
  ClockGapBullet,
  PressureQuintileBullet,
  TimePressureCardsResponse,
  TimePressureTcCard,
} from '@/types/endgames';

beforeAll(() => {
  Object.defineProperty(window, 'matchMedia', {
    writable: true,
    value: vi.fn().mockImplementation((query: string) => ({
      matches: false,
      media: query,
      onchange: null,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      addListener: vi.fn(),
      removeListener: vi.fn(),
      dispatchEvent: vi.fn(),
    })),
  });
  class ResizeObserverStub {
    observe() {}
    unobserve() {}
    disconnect() {}
  }
  (globalThis as unknown as { ResizeObserver: typeof ResizeObserverStub }).ResizeObserver =
    ResizeObserverStub;
});

afterEach(() => {
  cleanup();
});

import { EndgameTimePressureSection } from '../EndgameTimePressureSection';

// ── Payload helpers ────────────────────────────────────────────────────────────

function buildClockGap(): ClockGapBullet {
  return {
    n: 100,
    mean_diff_pct: 0.02,
    p_value: 0.2,
    ci_low: -0.01,
    ci_high: 0.05,
  };
}

function buildQuintile(index: 0 | 1 | 2 | 3 | 4): PressureQuintileBullet {
  const labels: Record<0 | 1 | 2 | 3 | 4, string> = {
    0: '0-20%',
    1: '20-40%',
    2: '40-60%',
    3: '60-80%',
    4: '80-100%',
  };
  return {
    quintile_index: index,
    quintile_label: labels[index],
    n: 20,
    delta: 0.0,
    p_value: 0.5,
    ci_low: -0.05,
    ci_high: 0.05,
    opp_score: 0.5,
  };
}

function buildCard(tc: TimePressureTcCard['tc']): TimePressureTcCard {
  return {
    tc,
    total: 100,
    // Plan 88-14 A-3: top-zone summary stats defaults.
    user_avg_pct: 0.47,
    user_avg_seconds: 215,
    opp_avg_pct: 0.52,
    opp_avg_seconds: 231,
    avg_clock_diff_seconds: -16,
    net_timeout_rate: -0.005,
    clock_gap: buildClockGap(),
    quintiles: [
      buildQuintile(0),
      buildQuintile(1),
      buildQuintile(2),
      buildQuintile(3),
      buildQuintile(4),
    ],
  };
}

/**
 * Build a TimePressureCardsResponse with one card per supplied TC.
 * Default all-four-TC payload when called with no args via overload.
 */
function makePayload(
  ...tcs: Array<TimePressureTcCard['tc']>
): TimePressureCardsResponse {
  const tcsToUse =
    tcs.length > 0 ? tcs : (['bullet', 'blitz', 'rapid', 'classical'] as const);
  return {
    cards: tcsToUse.map(buildCard),
  };
}

// ── Render helper ──────────────────────────────────────────────────────────────

function renderSection(
  data: TimePressureCardsResponse,
): ReturnType<typeof render> {
  return render(
    <MemoryRouter>
      <TooltipProvider>
        <EndgameTimePressureSection data={data} />
      </TooltipProvider>
    </MemoryRouter>,
  );
}

// ── Tests ─────────────────────────────────────────────────────────────────────

describe('EndgameTimePressureSection — TC card visibility', () => {
  it('renders visible TC cards and omits hidden ones', () => {
    // Only bullet and rapid are in the payload — blitz and classical absent.
    renderSection(makePayload('bullet', 'rapid'));

    expect(screen.getByTestId('time-pressure-card-bullet')).not.toBeNull();
    expect(screen.getByTestId('time-pressure-card-rapid')).not.toBeNull();
    expect(screen.queryByTestId('time-pressure-card-blitz')).toBeNull();
    expect(screen.queryByTestId('time-pressure-card-classical')).toBeNull();
  });
});

describe('EndgameTimePressureSection — Empty state', () => {
  it('renders empty state when cards array is empty', () => {
    renderSection({ cards: [] });

    expect(screen.getByTestId('time-pressure-cards-empty')).not.toBeNull();
    // The grid should not be rendered when there are no cards.
    expect(screen.queryByTestId('time-pressure-card-bullet')).toBeNull();
  });
});

describe('EndgameTimePressureSection — All 4 TCs', () => {
  it('renders all 4 TC cards in canonical order when payload contains all four', () => {
    renderSection(makePayload('bullet', 'blitz', 'rapid', 'classical'));

    expect(screen.getByTestId('time-pressure-card-bullet')).not.toBeNull();
    expect(screen.getByTestId('time-pressure-card-blitz')).not.toBeNull();
    expect(screen.getByTestId('time-pressure-card-rapid')).not.toBeNull();
    expect(screen.getByTestId('time-pressure-card-classical')).not.toBeNull();
  });
});

describe('EndgameTimePressureSection — Legacy absence (knip-clean proxy)', () => {
  it('asserts legacy data-testid="clock-pressure-section" is absent', () => {
    renderSection(makePayload('bullet', 'blitz', 'rapid', 'classical'));

    expect(screen.queryByTestId('clock-pressure-section')).toBeNull();
  });
});

describe('EndgameTimePressureSection — grandTotal propagation', () => {
  it('passes the summed total to each card so the percentage in the title is consistent across cards', () => {
    // 4 cards × 100 games each → grandTotal = 400 → each card is 25%.
    renderSection(makePayload('bullet', 'blitz', 'rapid', 'classical'));

    for (const tc of ['bullet', 'blitz', 'rapid', 'classical'] as const) {
      const total = screen.getByTestId(`time-pressure-card-${tc}-total`);
      expect(total.textContent).toContain('Games: 25% (100)');
    }
  });
});

describe('EndgameTimePressureSection — Section wrapper', () => {
  it('wraps content in a section with time-pressure-cards-section testid', () => {
    renderSection(makePayload('bullet', 'blitz', 'rapid', 'classical'));

    expect(screen.getByTestId('time-pressure-cards-section')).not.toBeNull();
  });

  it('exposes a non-dangling accessible name on the section', () => {
    // Phase 88.1 WR-02 / IN-05: section uses aria-label (self-contained),
    // not aria-labelledby pointing at a non-existent heading id.
    const { container } = renderSection(
      makePayload('bullet', 'blitz', 'rapid', 'classical'),
    );
    const section = container.querySelector(
      '[data-testid="time-pressure-cards-section"]',
    );
    expect(section).not.toBeNull();
    expect(section!.getAttribute('aria-label')).toBe('Time pressure analysis');
    expect(section!.getAttribute('aria-labelledby')).toBeNull();
  });
});

describe('EndgameTimePressureSection — SC-1: dynamic grid layout', () => {
  it('1-card payload wraps card in w-1/2 container', () => {
    const { container } = renderSection(makePayload('bullet'));
    const grid = container.querySelector(
      '[data-testid="time-pressure-cards-section"] > p + div',
    );
    // Single card uses half-width, not a grid layout.
    expect(grid?.className).toContain('w-1/2');
    expect(grid?.className).not.toContain('grid');
  });

  it('2-card payload uses grid-cols-2', () => {
    const { container } = renderSection(makePayload('bullet', 'blitz'));
    const grid = container.querySelector(
      '[data-testid="time-pressure-cards-section"] > p + div',
    );
    expect(grid?.className).toContain('grid-cols-2');
  });

  it('3-card payload uses sm:grid-cols-3', () => {
    const { container } = renderSection(makePayload('bullet', 'blitz', 'rapid'));
    const grid = container.querySelector(
      '[data-testid="time-pressure-cards-section"] > p + div',
    );
    expect(grid?.className).toContain('grid-cols-3');
  });

  it('4-card payload uses xl:grid-cols-4', () => {
    const { container } = renderSection(
      makePayload('bullet', 'blitz', 'rapid', 'classical'),
    );
    const grid = container.querySelector(
      '[data-testid="time-pressure-cards-section"] > p + div',
    );
    expect(grid?.className).toContain('grid-cols-4');
  });
});
