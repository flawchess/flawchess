// @vitest-environment jsdom
/**
 * Phase 87 follow-up — tests for the redesigned EndgameTypeCard (single Score
 * bullet replacing the dual Conv/Recov peer-diff bullets).
 *
 * Covers:
 * - Full render when total >= MIN_GAMES_FOR_RELIABLE_STATS (gauges + WDL bar +
 *   Score bullet + Games deep-link + title InfoPopover).
 * - Games-link onClick fires onCategorySelect with the endgame_class and the
 *   href targets /endgames/games?type={slug}.
 * - Title InfoPopover content matches ENDGAME_TYPE_DESCRIPTIONS[class].
 * - Empty class (total = 0) → empty-class shell with "Not enough data yet" +
 *   opacity-50 gauge row; no WDL, no Score bullet, no Games link.
 * - Sparse class (0 < total < MIN_GAMES_FOR_RELIABLE_STATS) → n=total chip,
 *   UNRELIABLE_OPACITY on the body, Score row hidden, gauges + WDL still
 *   render.
 * - Score bullet sig-gating: confident + outside-neutral → inline color;
 *   weak p-value → no inline color.
 */

import { afterEach, beforeAll, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';

import { TooltipProvider } from '@/components/ui/tooltip';
import { ENDGAME_TYPE_DESCRIPTIONS } from '@/lib/endgameMetrics';
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
    wins: 60,
    draws: 20,
    losses: 20,
    total: 100,
    win_pct: 60,
    draw_pct: 20,
    loss_pct: 20,
    conversion: buildConversion(convOverrides),
    score_p_value: 0.001,
    // Phase 87.1: per-span Score Gap defaults. Tests override these.
    type_achievable_score_gap_mean: 0.08,
    type_achievable_score_gap_n: 80,
    type_achievable_score_gap_p_value: 0.0001,
    type_achievable_score_gap_ci_low: 0.04,
    type_achievable_score_gap_ci_high: 0.12,
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
  it('renders gauges, WDL bar, and Score bullet when total >= MIN_GAMES_FOR_RELIABLE_STATS', () => {
    renderCard(buildCategory());
    expect(screen.getByTestId(TILE_TESTID)).not.toBeNull();
    expect(screen.getByTestId(`${TILE_TESTID}-conv-gauge`)).not.toBeNull();
    expect(screen.getByTestId(`${TILE_TESTID}-recov-gauge`)).not.toBeNull();
    expect(screen.getByTestId(`${TILE_TESTID}-wdl`)).not.toBeNull();
    expect(screen.getByTestId(`${TILE_TESTID}-score-row`)).not.toBeNull();
    expect(screen.getByTestId(`${TILE_TESTID}-score-value`)).not.toBeNull();
    expect(screen.getByTestId(`${TILE_TESTID}-score-bullet`)).not.toBeNull();
    expect(screen.getByTestId(`${TILE_TESTID}-score-info`)).not.toBeNull();
    expect(screen.getByTestId(`${TILE_TESTID}-games-link`)).not.toBeNull();
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

  it('title InfoPopover content uses ENDGAME_TYPE_DESCRIPTIONS[class]', () => {
    renderCard(buildCategory());
    // The InfoPopover renders its content into a portal opened on click;
    // assert the underlying description string is the one from the map.
    expect(ENDGAME_TYPE_DESCRIPTIONS.rook.length).toBeGreaterThan(0);
    const titleInfo = screen.getByTestId(`${TILE_TESTID}-title-info`);
    // Click the trigger to open the popover and assert its body.
    fireEvent.click(titleInfo);
    expect(screen.getByText(ENDGAME_TYPE_DESCRIPTIONS.rook)).not.toBeNull();
  });
});

describe('EndgameTypeCard — Empty / sparse states', () => {
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
        score_p_value: null,
        type_achievable_score_gap_mean: null,
        type_achievable_score_gap_n: 0,
        type_achievable_score_gap_p_value: null,
        type_achievable_score_gap_ci_low: null,
        type_achievable_score_gap_ci_high: null,
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
        },
      }),
    );
    expect(screen.getByTestId(TILE_TESTID)).not.toBeNull();
    const gaugeRow = screen.getByTestId(`${TILE_TESTID}-gauges`);
    expect(gaugeRow.className).toMatch(/opacity-50/);
    expect(screen.getByText(/Not enough data yet/i)).not.toBeNull();
    expect(screen.queryByTestId(`${TILE_TESTID}-wdl`)).toBeNull();
    expect(screen.queryByTestId(`${TILE_TESTID}-score-row`)).toBeNull();
    expect(screen.queryByTestId(`${TILE_TESTID}-score-bullet`)).toBeNull();
    expect(screen.queryByTestId(`${TILE_TESTID}-games-link`)).toBeNull();
    // Phase 87.1: ScoreGapRow hidden when type_achievable_score_gap_n === 0.
    expect(screen.queryByTestId(`${TILE_TESTID}-asg-bullet`)).toBeNull();
  });

  it('shows n=total chip and UNRELIABLE_OPACITY when total < MIN_GAMES_FOR_RELIABLE_STATS, hides Score row', () => {
    renderCard(
      buildCategory({
        wins: 3,
        draws: 1,
        losses: 1,
        total: 5,
        win_pct: 60,
        draw_pct: 20,
        loss_pct: 20,
        score_p_value: null,
      }),
    );
    const chip = screen.getByTestId(`${TILE_TESTID}-n-chip`);
    expect(chip.textContent).toBe('n=5');
    // The body wrapper inside the tile carries the inline opacity style.
    const tile = screen.getByTestId(TILE_TESTID);
    const body = tile.querySelector<HTMLElement>('.flex.flex-col.gap-4');
    expect(body).not.toBeNull();
    expect(body!.style.opacity).toBe(`${UNRELIABLE_OPACITY}`);
    // Gauges + WDL still render; Score row hidden below the sample-size gate.
    expect(screen.getByTestId(`${TILE_TESTID}-wdl`)).not.toBeNull();
    expect(screen.queryByTestId(`${TILE_TESTID}-score-row`)).toBeNull();
    expect(screen.queryByTestId(`${TILE_TESTID}-score-bullet`)).toBeNull();
  });
});

describe('EndgameTypeCard — Score bullet sig-gating', () => {
  it('applies inline color on Score value when p < 0.05 and outside neutral band', () => {
    // 60W/20D/20L of 100 -> score = 0.70 (outside 0.45-0.55 neutral band).
    renderCard(
      buildCategory({
        wins: 60,
        draws: 20,
        losses: 20,
        total: 100,
        score_p_value: 0.0001,
      }),
    );
    const scoreSpan = screen.getByTestId(`${TILE_TESTID}-score-value`);
    expect(scoreSpan.style.color).toBeTruthy();
  });

  it('does NOT apply inline color when p_value is null (gated)', () => {
    renderCard(
      buildCategory({
        wins: 60,
        draws: 20,
        losses: 20,
        total: 100,
        score_p_value: null,
      }),
    );
    const scoreSpan = screen.getByTestId(`${TILE_TESTID}-score-value`);
    expect(scoreSpan.style.color).toBeFalsy();
  });

  it('does NOT apply inline color when score lands inside the neutral band', () => {
    // 50W/20D/30L of 100 -> score = 0.60? Need a score inside [0.45, 0.55]:
    // 25W/50D/25L -> score = 0.5 (neutral). p_value strong but neutral zone.
    renderCard(
      buildCategory({
        wins: 25,
        draws: 50,
        losses: 25,
        total: 100,
        win_pct: 25,
        draw_pct: 50,
        loss_pct: 25,
        score_p_value: 0.0001,
      }),
    );
    const scoreSpan = screen.getByTestId(`${TILE_TESTID}-score-value`);
    expect(scoreSpan.style.color).toBeFalsy();
  });
});

describe('EndgameTypeCard — Score Gap row (Phase 87.1)', () => {
  it('renders the ScoreGapRow row with testid sub-elements when n > 0', () => {
    renderCard(buildCategory());
    expect(screen.getByTestId(`${TILE_TESTID}-asg-bullet`)).not.toBeNull();
    expect(screen.getByTestId(`${TILE_TESTID}-asg-value`)).not.toBeNull();
    expect(screen.getByTestId(`${TILE_TESTID}-asg-info`)).not.toBeNull();
  });

  it('hides the ScoreGapRow row when type_achievable_score_gap_n === 0', () => {
    renderCard(
      buildCategory({
        type_achievable_score_gap_mean: null,
        type_achievable_score_gap_n: 0,
        type_achievable_score_gap_p_value: null,
        type_achievable_score_gap_ci_low: null,
        type_achievable_score_gap_ci_high: null,
      }),
    );
    expect(screen.queryByTestId(`${TILE_TESTID}-asg-bullet`)).toBeNull();
    expect(screen.queryByTestId(`${TILE_TESTID}-asg-value`)).toBeNull();
    expect(screen.queryByTestId(`${TILE_TESTID}-asg-info`)).toBeNull();
  });

  it('positions the ScoreGapRow as the last row in the card', () => {
    renderCard(buildCategory());
    const tile = screen.getByTestId(TILE_TESTID);
    const gauges = screen.getByTestId(`${TILE_TESTID}-gauges`);
    const asgBullet = screen.getByTestId(`${TILE_TESTID}-asg-bullet`);
    const wdl = screen.getByTestId(`${TILE_TESTID}-wdl`);
    const scoreRow = screen.getByTestId(`${TILE_TESTID}-score-row`);
    const body = tile.querySelector('.flex.flex-col.gap-4');
    expect(body).not.toBeNull();
    expect(gauges.parentElement).toBe(body);
    expect(asgBullet.parentElement).toBe(body);
    // DOM ordering: gauges -> wdl block -> score row -> asg row (Score Gap last).
    const children = Array.from(body!.children);
    const gaugesIdx = children.indexOf(gauges);
    const wdlWrapper = children.find((c) => c.contains(wdl)) as HTMLElement;
    const wdlIdx = children.indexOf(wdlWrapper);
    const scoreIdx = children.indexOf(scoreRow);
    const asgIdx = children.indexOf(asgBullet);
    expect(gaugesIdx).toBeGreaterThanOrEqual(0);
    expect(wdlIdx).toBeGreaterThan(gaugesIdx);
    expect(scoreIdx).toBeGreaterThan(wdlIdx);
    expect(asgIdx).toBeGreaterThan(scoreIdx);
  });

  it('tints positive out-of-band gap green (ZONE_SUCCESS)', async () => {
    const { ZONE_SUCCESS } = await import('@/lib/theme');
    renderCard(
      buildCategory({
        type_achievable_score_gap_mean: 0.08,
        type_achievable_score_gap_n: 80,
      }),
    );
    const valueSpan = screen.getByTestId(`${TILE_TESTID}-asg-value`);
    // jsdom normalizes oklch() numeric literals (e.g. 0.50 -> 0.5). Normalize
    // both sides by collapsing trailing zeros in decimal fractions before compare.
    const normalize = (s: string): string =>
      s.toLowerCase().replace(/(\d+\.\d*?)0+(?=\D|$)/g, '$1').replace(/(\d+)\.(?=\D)/g, '$1');
    expect(normalize(valueSpan.style.color)).toBe(normalize(ZONE_SUCCESS));
    expect(valueSpan.textContent).toBe('+8%');
  });

  it('tints negative out-of-band gap red (ZONE_DANGER)', async () => {
    const { ZONE_DANGER } = await import('@/lib/theme');
    renderCard(
      buildCategory({
        type_achievable_score_gap_mean: -0.09,
        type_achievable_score_gap_n: 80,
      }),
    );
    const valueSpan = screen.getByTestId(`${TILE_TESTID}-asg-value`);
    const normalize = (s: string): string =>
      s.toLowerCase().replace(/(\d+\.\d*?)0+(?=\D|$)/g, '$1').replace(/(\d+)\.(?=\D)/g, '$1');
    expect(normalize(valueSpan.style.color)).toBe(normalize(ZONE_DANGER));
    expect(valueSpan.textContent).toBe('-9%');
  });

  it('does not tint when gap is inside the neutral band', () => {
    renderCard(
      buildCategory({
        type_achievable_score_gap_mean: 0.02,
        type_achievable_score_gap_n: 80,
      }),
    );
    const valueSpan = screen.getByTestId(`${TILE_TESTID}-asg-value`);
    expect(valueSpan.style.color).toBeFalsy();
    expect(valueSpan.textContent).toBe('+2%');
  });

  it('popover explanation contains the sigmoid-bias caveat one-liner', () => {
    renderCard(buildCategory());
    const trigger = screen.getByTestId(`${TILE_TESTID}-asg-info`);
    fireEvent.mouseEnter(trigger);
    // The hover-open is delayed 100ms; open imperatively via click as a fallback.
    fireEvent.click(trigger);
    const matches = screen.queryAllByText(/Lichess expected-score formula under-weights/i);
    expect(matches.length).toBeGreaterThan(0);
  });
});

describe('EndgameTypeCard — WDL flag gating (mocked false)', () => {
  it('hides WDL bar but keeps Games deep-link in a standalone row when SHOW_WDL_BAR_IN_TYPE_CARDS is false', async () => {
    vi.resetModules();
    vi.doMock('@/lib/endgameMetrics', async () => {
      const actual = await vi.importActual<
        typeof import('@/lib/endgameMetrics')
      >('@/lib/endgameMetrics');
      return { ...actual, SHOW_WDL_BAR_IN_TYPE_CARDS: false };
    });
    const { EndgameTypeCard: MockedCard } = await import('../EndgameTypeCard');
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
