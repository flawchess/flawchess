// @vitest-environment jsdom
/**
 * Phase 97 Plan 03 — Integration tests for the EndgameMetricsByTcSection
 * orchestrator. Verifies:
 *   - Renders one card per provided TC in bullet -> blitz -> rapid -> classical order.
 *   - Shows empty-state testid and text when cards array is empty.
 *   - Section wrapper testid="endgame-metrics-tc-section" is always present.
 *   - Empty-state testid="endgame-metrics-tc-section-empty" is present iff cards=[].
 *   - Cards absent from the payload do not render.
 */

import { afterEach, beforeAll, describe, expect, it, vi } from 'vitest';
import { cleanup, render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';

import { TooltipProvider } from '@/components/ui/tooltip';
import type {
  EndgameMetricsTcCard,
  EndgameMetricsCardsResponse,
  PerTcBucketStats,
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

import { EndgameMetricsByTcSection } from '../EndgameMetricsByTcSection';

// ── Payload helpers ────────────────────────────────────────────────────────────

function buildBucket(): PerTcBucketStats {
  return {
    games: 50,
    win_pct: 60,
    draw_pct: 20,
    loss_pct: 20,
    rate: 0.6,
    score_gap_mean: -0.08,
    score_gap_n: 40,
    score_gap_p_value: 0.04,
    score_gap_ci_low: -0.12,
    score_gap_ci_high: -0.04,
    percentile: 42,
  };
}

function buildCard(tc: EndgameMetricsTcCard['tc']): EndgameMetricsTcCard {
  return {
    tc,
    total: 150,
    conversion: buildBucket(),
    parity: buildBucket(),
    recovery: buildBucket(),
  };
}

function makePayload(
  ...tcs: Array<EndgameMetricsTcCard['tc']>
): EndgameMetricsCardsResponse {
  const tcsToUse =
    tcs.length > 0 ? tcs : (['bullet', 'blitz', 'rapid', 'classical'] as const);
  return {
    cards: tcsToUse.map(buildCard),
  };
}

// ── Render helper ──────────────────────────────────────────────────────────────

function renderSection(data: EndgameMetricsCardsResponse): ReturnType<typeof render> {
  return render(
    <MemoryRouter>
      <TooltipProvider>
        <EndgameMetricsByTcSection data={data} />
      </TooltipProvider>
    </MemoryRouter>,
  );
}

// ── Tests ─────────────────────────────────────────────────────────────────────

describe('EndgameMetricsByTcSection — section wrapper', () => {
  it('wraps content in a section with endgame-metrics-tc-section testid', () => {
    renderSection(makePayload('bullet', 'blitz'));
    expect(screen.getByTestId('endgame-metrics-tc-section')).not.toBeNull();
  });

  it('exposes a non-dangling accessible name on the section', () => {
    const { container } = renderSection(makePayload('bullet'));
    const section = container.querySelector('[data-testid="endgame-metrics-tc-section"]');
    expect(section).not.toBeNull();
    expect(section!.getAttribute('aria-label')).toBe('Endgame metrics by time control');
  });
});

describe('EndgameMetricsByTcSection — empty state', () => {
  it('renders empty state when cards array is empty', () => {
    renderSection({ cards: [] });
    expect(screen.getByTestId('endgame-metrics-tc-section-empty')).not.toBeNull();
    expect(screen.queryByTestId('metrics-tc-card-bullet')).toBeNull();
  });

  it('shows the correct empty-state text', () => {
    renderSection({ cards: [] });
    const emptyEl = screen.getByTestId('endgame-metrics-tc-section-empty');
    expect(emptyEl.textContent).toContain('No endgame data yet');
    expect(emptyEl.textContent).toContain('Import more games');
  });

  it('does NOT render empty state when cards are present', () => {
    renderSection(makePayload('bullet'));
    expect(screen.queryByTestId('endgame-metrics-tc-section-empty')).toBeNull();
  });
});

describe('EndgameMetricsByTcSection — TC card visibility', () => {
  it('renders visible TC cards and omits absent ones', () => {
    // Only bullet and rapid in the payload.
    renderSection(makePayload('bullet', 'rapid'));

    expect(screen.getByTestId('metrics-tc-card-bullet')).not.toBeNull();
    expect(screen.getByTestId('metrics-tc-card-rapid')).not.toBeNull();
    expect(screen.queryByTestId('metrics-tc-card-blitz')).toBeNull();
    expect(screen.queryByTestId('metrics-tc-card-classical')).toBeNull();
  });

  it('renders all 4 TC cards when payload contains all four', () => {
    renderSection(makePayload('bullet', 'blitz', 'rapid', 'classical'));

    expect(screen.getByTestId('metrics-tc-card-bullet')).not.toBeNull();
    expect(screen.getByTestId('metrics-tc-card-blitz')).not.toBeNull();
    expect(screen.getByTestId('metrics-tc-card-rapid')).not.toBeNull();
    expect(screen.getByTestId('metrics-tc-card-classical')).not.toBeNull();
  });
});

describe('EndgameMetricsByTcSection — card order', () => {
  it('renders cards in the order provided by the backend payload', () => {
    // Backend returns bullet -> blitz -> rapid -> classical order; section preserves it.
    const { container } = renderSection(
      makePayload('bullet', 'blitz', 'rapid', 'classical'),
    );

    // Gather all TC card testids in DOM order.
    const cards = container.querySelectorAll('[data-testid^="metrics-tc-card-"]');
    const tcs = Array.from(cards).map((el) =>
      el.getAttribute('data-testid')!.replace('metrics-tc-card-', ''),
    );

    expect(tcs).toEqual(['bullet', 'blitz', 'rapid', 'classical']);
  });
});
