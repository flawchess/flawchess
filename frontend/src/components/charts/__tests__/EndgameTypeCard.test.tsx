// @vitest-environment jsdom
/**
 * Phase 87 Plan 02: tests for EndgameTypeCard (Conv + Recov per-class shell).
 *
 * Covers:
 * - Full render when all data present (gauges + WDL + Conv + Recov peer bullets
 *   + Games deep-link + title InfoPopover).
 * - Games-link onClick fires onCategorySelect with the endgame_class.
 * - WDL bar gated by SHOW_WDL_BAR_IN_TYPE_CARDS (mocked false → WDL row gone,
 *   Games deep-link still present in standalone row per D-07 fallback).
 * - Sparse opponent per metric (opp_conversion_games < 10) → that metric's
 *   peer bullet replaced with muted text; the other metric's bullet still
 *   renders (D-14).
 * - Empty class (total = 0) → empty-class shell with "Not enough data yet" +
 *   opacity-50 gauge row; no peer-bullet rows; no Games link (D-13).
 * - Sparse total class (total = 5 < MIN_GAMES_FOR_RELIABLE_STATS) → n=5 chip +
 *   UNRELIABLE_OPACITY on the body (D-15).
 * - Sig-gated diff color: confident + outside-neutral → inline color set;
 *   weak p-value → no inline color.
 */

import { afterEach, beforeAll, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';

import { TooltipProvider } from '@/components/ui/tooltip';
import { UNRELIABLE_OPACITY } from '@/lib/theme';
import type {
  ConversionRecoveryStats,
  EndgameCategoryStats,
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

import { EndgameTypeCard } from '../EndgameTypeCard';

const TILE_TESTID = 'type-card-rook';

function buildConversion(
  overrides?: Partial<ConversionRecoveryStats>,
): ConversionRecoveryStats {
  // Healthy default: 50 conversion games with 35 wins (70%), 50 recovery games
  // with 25 saves = 15 wins + 10 draws (50% save rate).
  // Opp from mirror: opp_conv = 1 − recovery_wins/recovery_games = 1 − 0.30 = 0.70
  // (but we set opp_conv to 0.50 to produce a meaningful +0.20 user Conv gap).
  return {
    conversion_pct: 70,
    conversion_games: 50,
    conversion_wins: 35,
    conversion_draws: 5,
    conversion_losses: 10,
    recovery_pct: 50,
    recovery_games: 50,
    recovery_saves: 25,
    recovery_wins: 15,
    recovery_draws: 10,
    opp_conversion_pct: 0.5,
    opp_recovery_pct: 0.4,
    opp_conversion_games: 50,
    opp_recovery_games: 50,
    conv_diff_p_value: 0.001,
    conv_diff_ci_low: 0.1,
    conv_diff_ci_high: 0.3,
    recov_diff_p_value: 0.001,
    recov_diff_ci_low: 0.05,
    recov_diff_ci_high: 0.15,
    ...overrides,
  };
}

function buildCategory(
  overrides?: Partial<EndgameCategoryStats> & {
    conversion?: Partial<ConversionRecoveryStats>;
  },
): EndgameCategoryStats {
  const { conversion: convOverrides, ...rest } = overrides ?? {};
  return {
    endgame_class: 'rook',
    label: 'Rook',
    wins: 50,
    draws: 20,
    losses: 30,
    total: 100,
    win_pct: 50,
    draw_pct: 20,
    loss_pct: 30,
    conversion: buildConversion(convOverrides),
    ...rest,
  };
}

interface RenderOptions {
  onCategorySelect?: (cls: EndgameCategoryStats['endgame_class']) => void;
  tileTestId?: string;
  sharePct?: number;
}

function renderCard(
  category: EndgameCategoryStats,
  opts: RenderOptions = {},
): ReturnType<typeof render> {
  const onCategorySelect = opts.onCategorySelect ?? vi.fn();
  const tileTestId = opts.tileTestId ?? TILE_TESTID;
  const sharePct = opts.sharePct ?? 45.5;
  return render(
    <MemoryRouter>
      <TooltipProvider>
        <EndgameTypeCard
          category={category}
          sharePct={sharePct}
          onCategorySelect={onCategorySelect}
          tileTestId={tileTestId}
        />
      </TooltipProvider>
    </MemoryRouter>,
  );
}

describe('EndgameTypeCard — Layout', () => {
  it('renders full layout when all data present', () => {
    renderCard(buildCategory());
    expect(screen.getByTestId(TILE_TESTID)).not.toBeNull();
    expect(screen.getByTestId(`${TILE_TESTID}-conv-gauge`)).not.toBeNull();
    expect(screen.getByTestId(`${TILE_TESTID}-recov-gauge`)).not.toBeNull();
    expect(screen.getByTestId(`${TILE_TESTID}-wdl`)).not.toBeNull();
    expect(screen.getByTestId(`${TILE_TESTID}-games-link`)).not.toBeNull();
    expect(screen.getByTestId(`${TILE_TESTID}-conv-you`)).not.toBeNull();
    expect(screen.getByTestId(`${TILE_TESTID}-conv-opp`)).not.toBeNull();
    expect(screen.getByTestId(`${TILE_TESTID}-conv-diff`)).not.toBeNull();
    expect(screen.getByTestId(`${TILE_TESTID}-conv-info`)).not.toBeNull();
    expect(screen.getByTestId(`${TILE_TESTID}-recov-you`)).not.toBeNull();
    expect(screen.getByTestId(`${TILE_TESTID}-recov-opp`)).not.toBeNull();
    expect(screen.getByTestId(`${TILE_TESTID}-recov-diff`)).not.toBeNull();
    expect(screen.getByTestId(`${TILE_TESTID}-recov-info`)).not.toBeNull();
    expect(screen.getByTestId(`${TILE_TESTID}-title-info`)).not.toBeNull();
  });

  it('Games deep-link points to /endgames/games?type=rook', () => {
    renderCard(buildCategory());
    const link = screen.getByRole('link', {
      name: /View Rook endgame games/i,
    });
    expect(link.getAttribute('href')).toBe('/endgames/games?type=rook');
  });

  it('fires onCategorySelect when Games link is clicked', () => {
    const onCategorySelect = vi.fn();
    renderCard(buildCategory(), { onCategorySelect });
    const link = screen.getByTestId(`${TILE_TESTID}-games-link`);
    fireEvent.click(link);
    expect(onCategorySelect).toHaveBeenCalledWith('rook');
  });
});

describe('EndgameTypeCard — Sparse states', () => {
  it('replaces Conv peer-bullet with muted placeholder when opp_conversion_games < 10', () => {
    renderCard(
      buildCategory({
        conversion: { opp_conversion_games: 5, opp_recovery_games: 100 },
      }),
    );
    expect(screen.queryByTestId(`${TILE_TESTID}-conv-diff`)).toBeNull();
    const muted = screen.getByTestId(`${TILE_TESTID}-conv-muted`);
    expect(muted.textContent).toMatch(/n\s*[<&lt;]\s*10.*baseline unavailable/i);
    // Recov bullet still renders.
    expect(screen.getByTestId(`${TILE_TESTID}-recov-diff`)).not.toBeNull();
  });

  it('renders empty-class shell when total === 0', () => {
    renderCard(
      buildCategory({
        wins: 0,
        draws: 0,
        losses: 0,
        total: 0,
        win_pct: 0,
        draw_pct: 0,
        loss_pct: 0,
        conversion: {
          conversion_pct: 0,
          conversion_games: 0,
          conversion_wins: 0,
          conversion_draws: 0,
          conversion_losses: 0,
          recovery_pct: 0,
          recovery_games: 0,
          recovery_saves: 0,
          recovery_wins: 0,
          recovery_draws: 0,
          opp_conversion_pct: null,
          opp_recovery_pct: null,
          opp_conversion_games: 0,
          opp_recovery_games: 0,
          conv_diff_p_value: null,
          conv_diff_ci_low: null,
          conv_diff_ci_high: null,
          recov_diff_p_value: null,
          recov_diff_ci_low: null,
          recov_diff_ci_high: null,
        },
      }),
    );
    expect(screen.getByTestId(TILE_TESTID)).not.toBeNull();
    const gaugeRow = screen.getByTestId(`${TILE_TESTID}-gauges`);
    expect(gaugeRow.className).toMatch(/opacity-50/);
    expect(screen.getByText(/Not enough data yet/i)).not.toBeNull();
    expect(screen.queryByTestId(`${TILE_TESTID}-wdl`)).toBeNull();
    expect(screen.queryByTestId(`${TILE_TESTID}-conv-diff`)).toBeNull();
    expect(screen.queryByTestId(`${TILE_TESTID}-recov-diff`)).toBeNull();
    expect(screen.queryByTestId(`${TILE_TESTID}-games-link`)).toBeNull();
  });

  it('shows n=total chip and unreliable opacity when total < MIN_GAMES_FOR_RELIABLE_STATS', () => {
    renderCard(
      buildCategory({
        wins: 3,
        draws: 1,
        losses: 1,
        total: 5,
        win_pct: 60,
        draw_pct: 20,
        loss_pct: 20,
      }),
    );
    const chip = screen.getByTestId(`${TILE_TESTID}-n-chip`);
    expect(chip.textContent).toBe('n=5');
    // The body wrapper inside the tile carries the inline opacity style.
    const tile = screen.getByTestId(TILE_TESTID);
    const body = tile.querySelector<HTMLElement>('.flex.flex-col.gap-4');
    expect(body).not.toBeNull();
    expect(body!.style.opacity).toBe(`${UNRELIABLE_OPACITY}`);
    // Peer-bullets + WDL + gauges still render.
    expect(screen.getByTestId(`${TILE_TESTID}-wdl`)).not.toBeNull();
    expect(screen.getByTestId(`${TILE_TESTID}-conv-diff`)).not.toBeNull();
    expect(screen.getByTestId(`${TILE_TESTID}-recov-diff`)).not.toBeNull();
  });
});

describe('EndgameTypeCard — Sig-gating', () => {
  it('applies inline color on Conv diff when confident + outside neutral band', () => {
    renderCard(
      buildCategory({
        conversion: {
          conversion_pct: 80,
          opp_conversion_pct: 0.4,
          opp_conversion_games: 100,
          conv_diff_p_value: 0.001,
          conv_diff_ci_low: 0.3,
          conv_diff_ci_high: 0.5,
        },
      }),
    );
    const diffSpan = screen.getByTestId(`${TILE_TESTID}-conv-diff`);
    expect(diffSpan.style.color).toBeTruthy();
  });

  it('does NOT apply inline color on Conv diff when p-value is weak', () => {
    renderCard(
      buildCategory({
        conversion: {
          conversion_pct: 80,
          opp_conversion_pct: 0.4,
          opp_conversion_games: 100,
          conv_diff_p_value: 0.5,
          conv_diff_ci_low: 0.0,
          conv_diff_ci_high: 0.6,
        },
      }),
    );
    const diffSpan = screen.getByTestId(`${TILE_TESTID}-conv-diff`);
    expect(diffSpan.style.color).toBe('');
  });
});

describe('EndgameTypeCard — WDL flag gating (mocked false)', () => {
  // Re-import EndgameTypeCard within a scoped vi.doMock so SHOW_WDL_BAR_IN_TYPE_CARDS
  // flips to false without affecting other describe blocks.
  it('hides WDL bar but keeps Games deep-link in a standalone row when SHOW_WDL_BAR_IN_TYPE_CARDS is false', async () => {
    vi.resetModules();
    vi.doMock('@/lib/endgameMetrics', async () => {
      const actual = await vi.importActual<
        typeof import('@/lib/endgameMetrics')
      >('@/lib/endgameMetrics');
      return { ...actual, SHOW_WDL_BAR_IN_TYPE_CARDS: false };
    });
    const { EndgameTypeCard: MockedCard } = await import(
      '../EndgameTypeCard'
    );
    const onCategorySelect = vi.fn();
    render(
      <MemoryRouter>
        <TooltipProvider>
          <MockedCard
            category={buildCategory()}
            sharePct={45.5}
            onCategorySelect={onCategorySelect}
            tileTestId={TILE_TESTID}
          />
        </TooltipProvider>
      </MemoryRouter>,
    );
    expect(screen.queryByTestId(`${TILE_TESTID}-wdl`)).toBeNull();
    expect(screen.getByTestId(`${TILE_TESTID}-games-link`)).not.toBeNull();
    vi.doUnmock('@/lib/endgameMetrics');
    vi.resetModules();
  });
});
