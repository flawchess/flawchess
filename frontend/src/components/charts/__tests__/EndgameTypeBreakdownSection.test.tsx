// @vitest-environment jsdom
/**
 * Phase 87 Plan 03 — integration tests for the EndgameTypeBreakdownSection
 * orchestrator. Verifies:
 * - 5 cards rendered when all 6 EndgameClass entries are present (pawnless
 *   filtered out via HIDDEN_ENDGAME_CLASSES).
 * - Locked sub-question copy above the grid.
 * - Locked Tailwind grid class string (D-06).
 * - Cards render in the backend-sorted order (total desc).
 * - Empty `categories` renders the section + sub-question with no cards.
 */

import { afterEach, beforeAll, describe, expect, it, vi } from 'vitest';
import { cleanup, render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';

// useEvalCoverage calls useQuery which requires a QueryClientProvider.
// Return safe defaults so the component renders without a provider.
vi.mock('@/hooks/useEvalCoverage', () => ({
  useEvalCoverage: () => ({ isPending: false, pendingCount: 0, pct: 100, totalCount: 0, isLoading: false }),
}));

import { TooltipProvider } from '@/components/ui/tooltip';
import type {
  ConversionRecoveryStats,
  EndgameCategoryStats,
  EndgameClass,
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

import { EndgameTypeBreakdownSection } from '../EndgameTypeBreakdownSection';

const CLASS_LABELS: Record<EndgameClass, string> = {
  rook: 'Rook',
  minor_piece: 'Minor Piece',
  pawn: 'Pawn',
  queen: 'Queen',
  mixed: 'Mixed',
  pawnless: 'Pawnless',
};

function buildConversion(
  overrides?: Partial<ConversionRecoveryStats>,
): ConversionRecoveryStats {
  return {
    conversion_pct: 65,
    conversion_games: 50,
    conversion_wins: 32,
    conversion_draws: 5,
    conversion_losses: 13,
    recovery_pct: 40,
    recovery_games: 50,
    recovery_saves: 20,
    recovery_wins: 10,
    recovery_draws: 10,
    opp_conversion_pct: 0.5,
    opp_recovery_pct: 0.4,
    opp_conversion_games: 50,
    opp_recovery_games: 50,
    conv_diff_p_value: 0.01,
    conv_diff_ci_low: 0.05,
    conv_diff_ci_high: 0.2,
    recov_diff_p_value: 0.01,
    recov_diff_ci_low: 0.02,
    recov_diff_ci_high: 0.18,
    ...overrides,
  };
}

function buildCategory(
  endgameClass: EndgameClass,
  overrides?: Partial<EndgameCategoryStats>,
): EndgameCategoryStats {
  return {
    endgame_class: endgameClass,
    label: CLASS_LABELS[endgameClass],
    wins: 50,
    draws: 20,
    losses: 30,
    total: 100,
    win_pct: 50,
    draw_pct: 20,
    loss_pct: 30,
    conversion: buildConversion(),
    ...overrides,
  };
}

function buildAllSixCategories(
  totalsByClass?: Partial<Record<EndgameClass, number>>,
): EndgameCategoryStats[] {
  const order: EndgameClass[] = [
    'rook',
    'minor_piece',
    'pawn',
    'queen',
    'mixed',
    'pawnless',
  ];
  return order.map((cls) => {
    const total = totalsByClass?.[cls] ?? 100;
    return buildCategory(cls, { total });
  });
}

function renderSection(
  categories: EndgameCategoryStats[],
  totalGames = 500,
): ReturnType<typeof render> {
  return render(
    <MemoryRouter>
      <TooltipProvider>
        <EndgameTypeBreakdownSection
          categories={categories}
          totalGames={totalGames}
          onCategorySelect={vi.fn()}
        />
      </TooltipProvider>
    </MemoryRouter>,
  );
}

// Match only top-level card containers (`type-card-{slug}` without any
// `-{sub-element}` suffix). Each card emits many sub-element testids like
// `type-card-rook-score-bullet`; the anchored regex below selects only the
// 5 card roots so card counts and ordering assertions are unambiguous.
const TOP_LEVEL_CARD_RE = /^type-card-(?:rook|minor-piece|pawn|queen|mixed|pawnless)$/;

describe('EndgameTypeBreakdownSection — Filtering', () => {
  it('renders 5 cards when all 6 EndgameClass entries are present (pawnless filtered)', () => {
    renderSection(buildAllSixCategories());

    const cards = screen.getAllByTestId(TOP_LEVEL_CARD_RE);
    expect(cards.length).toBe(5);

    expect(screen.getByTestId('type-card-rook')).not.toBeNull();
    expect(screen.getByTestId('type-card-minor-piece')).not.toBeNull();
    expect(screen.getByTestId('type-card-pawn')).not.toBeNull();
    expect(screen.getByTestId('type-card-queen')).not.toBeNull();
    expect(screen.getByTestId('type-card-mixed')).not.toBeNull();
    expect(screen.queryByTestId('type-card-pawnless')).toBeNull();
  });
});

describe('EndgameTypeBreakdownSection — Layout', () => {
  it('renders the locked sub-question copy', () => {
    renderSection(buildAllSixCategories());
    expect(
      screen.getByText(
        /Which Endgame Types did you convert or defend poorly/i,
      ),
    ).not.toBeNull();
  });

  it('renders the section container with locked testid', () => {
    renderSection(buildAllSixCategories());
    expect(screen.getByTestId('endgame-type-breakdown-section')).not.toBeNull();
  });

  it('renders a grid container carrying all locked Tailwind breakpoint classes', () => {
    renderSection(buildAllSixCategories());
    const section = screen.getByTestId('endgame-type-breakdown-section');
    const grid = section.querySelector<HTMLElement>('.grid');
    expect(grid).not.toBeNull();
    const className = grid!.className;
    expect(className).toMatch(/grid-cols-1/);
    expect(className).toMatch(/sm:grid-cols-2/);
    expect(className).toMatch(/lg:grid-cols-3/);
    expect(className).toMatch(/gap-4/);
  });
});

describe('EndgameTypeBreakdownSection — Ordering', () => {
  it('renders cards in the order delivered by the backend (preserves total-desc sort)', () => {
    // Backend returns categories sorted by total desc per _aggregate_endgame_stats.
    // The orchestrator preserves that order; pawnless is filtered out.
    const ordered: EndgameCategoryStats[] = [
      buildCategory('mixed', { total: 200 }),
      buildCategory('rook', { total: 100 }),
      buildCategory('minor_piece', { total: 50 }),
      buildCategory('pawn', { total: 20 }),
      buildCategory('queen', { total: 10 }),
      buildCategory('pawnless', { total: 5 }),
    ];
    renderSection(ordered);

    const cards = screen.getAllByTestId(TOP_LEVEL_CARD_RE);
    const testids = cards.map((c) => c.getAttribute('data-testid'));
    expect(testids).toEqual([
      'type-card-mixed',
      'type-card-rook',
      'type-card-minor-piece',
      'type-card-pawn',
      'type-card-queen',
    ]);
  });
});

describe('EndgameTypeBreakdownSection — Empty state', () => {
  it('renders section + sub-question with no cards when categories is empty', () => {
    renderSection([]);
    expect(screen.getByTestId('endgame-type-breakdown-section')).not.toBeNull();
    expect(
      screen.getByText(
        /Which Endgame Types did you convert or defend poorly/i,
      ),
    ).not.toBeNull();
    expect(screen.queryAllByTestId(TOP_LEVEL_CARD_RE).length).toBe(0);
  });
});
