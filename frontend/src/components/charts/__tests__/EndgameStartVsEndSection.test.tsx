// @vitest-environment jsdom
/**
 * Phase 81 Plan 03: tests for EndgameStartVsEndSection.
 *
 * Covers:
 * - Layout: both tiles render when n >= 10 on both, section container has the
 *   data-testid, and DOM order is entry-eval first (D-17 — natural document
 *   order achieves mobile chronological stacking).
 * - Color zones (Tile 1, entry eval): sig + outside neutral band → ZONE_SUCCESS
 *   or ZONE_DANGER; sig + inside neutral band → no inline color; not sig → no
 *   inline color (D-09).
 * - Color zones (Tile 2, endgame score): scoreZoneColor gated on isConfident
 *   (D-10).
 * - Sparse handling: per-tile "Not enough data" placeholder when n < 10 (D-06);
 *   the placeholder replaces the value-row + chart pair on that tile only.
 * - Prop forwarding: MiniBulletChart receives D-15 constants on Tile 1 and
 *   D-16 / scoreBulletConfig constants on Tile 2 (mocked component to spy on
 *   props).
 * - Popover triggers carry stable kebab-case data-testids for browser-automation
 *   compatibility.
 */

import { afterEach, beforeAll, describe, expect, it, vi } from 'vitest';
import { cleanup, render, screen, within } from '@testing-library/react';

import { ZONE_DANGER, ZONE_SUCCESS } from '@/lib/theme';
import type {
  EndgamePerformanceResponse,
  EndgameWDLSummary,
} from '@/types/endgames';

// Spy on MiniBulletChart so we can assert prop forwarding without rendering
// recharts internals (no recharts in this section, but the spy keeps the
// assertions tight to the prop contract).
vi.mock('@/components/charts/MiniBulletChart', () => ({
  MiniBulletChart: vi.fn(
    (props: Record<string, unknown>) => (
      <div
        data-testid="mock-mini-bullet"
        data-domain={String(props.domain)}
        data-center={String(props.center)}
      />
    ),
  ),
}));

// jsdom ships without window.matchMedia / ResizeObserver. The popovers nested
// inside this section indirectly touch matchMedia via radix's portal. Stub
// both upfront so the render does not blow up under jsdom.
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
  vi.clearAllMocks();
});

import { MiniBulletChart } from '@/components/charts/MiniBulletChart';
import { EndgameStartVsEndSection } from '../EndgameStartVsEndSection';

// jsdom normalizes oklch trailing zeros ("0.50" → "0.5") when reading
// element.style.color back. Compare on a normalized form so the assertions
// are robust to jsdom's cosmetic rewrite without weakening the contract.
function normalizeColor(value: string): string {
  return value.replace(/(\d+)\.(\d*?)0+(?=\D|$)/g, (match, intPart: string, frac: string) => {
    if (frac === '') return `${intPart}`;
    return `${intPart}.${frac}`;
  });
}

// Helper: build a fully populated EndgameWDLSummary with sensible derived
// percentages. Tests override what they need.
function buildWdl(
  wins: number,
  draws: number,
  losses: number,
  total = wins + draws + losses,
): EndgameWDLSummary {
  const safeTotal = total === 0 ? 1 : total;
  return {
    wins,
    draws,
    losses,
    total,
    win_pct: (wins / safeTotal) * 100,
    draw_pct: (draws / safeTotal) * 100,
    loss_pct: (losses / safeTotal) * 100,
  };
}

function buildPerf(
  overrides?: Partial<EndgamePerformanceResponse>,
): EndgamePerformanceResponse {
  return {
    endgame_wdl: buildWdl(25, 10, 15),
    non_endgame_wdl: buildWdl(20, 8, 12),
    endgame_win_rate: 0.5,
    entry_eval_mean_pawns: 1.2,
    entry_eval_n: 50,
    entry_eval_p_value: 0.001,
    endgame_score_p_value: 0.001,
    entry_eval_ci_low_pawns: 0.4,
    entry_eval_ci_high_pawns: 2.0,
    // Phase 83: default to a neutral, in-band achievable score so existing
    // tests stay unaffected. Tests targeting the new bullet override these.
    entry_expected_score: 0.5,
    entry_expected_score_n: 50,
    entry_expected_score_p_value: 1.0,
    entry_expected_score_ci_low: 0.45,
    entry_expected_score_ci_high: 0.55,
    ...overrides,
  };
}

describe('EndgameStartVsEndSection', () => {
  it('renders the section container and both tiles when both n >= 10', () => {
    render(<EndgameStartVsEndSection data={buildPerf()} />);
    expect(screen.getByTestId('endgame-start-vs-end-section')).toBeTruthy();
    expect(screen.getByTestId('tile-entry-eval')).toBeTruthy();
    expect(screen.getByTestId('tile-endgame-score')).toBeTruthy();
  });

  it('renders entry-eval tile before endgame-score tile in DOM order (D-17)', () => {
    render(<EndgameStartVsEndSection data={buildPerf()} />);
    const tiles = document.querySelectorAll('[data-testid^="tile-"]');
    expect(tiles).toHaveLength(2);
    expect(tiles[0]?.getAttribute('data-testid')).toBe('tile-entry-eval');
    expect(tiles[1]?.getAttribute('data-testid')).toBe('tile-endgame-score');
  });

  it('Tile 1 value text is ZONE_SUCCESS when significant + above the neutral band', () => {
    render(
      <EndgameStartVsEndSection
        data={buildPerf({
          entry_eval_mean_pawns: 1.2,
          entry_eval_p_value: 0.001,
          entry_eval_n: 50,
        })}
      />,
    );
    const tile = screen.getByTestId('tile-entry-eval');
    const valueSpan = within(tile).getByTestId('entry-eval-value');
    expect(normalizeColor(valueSpan.style.color)).toBe(normalizeColor(ZONE_SUCCESS));
  });

  it('Tile 1 value text is ZONE_DANGER when significant + below the neutral band', () => {
    render(
      <EndgameStartVsEndSection
        data={buildPerf({
          entry_eval_mean_pawns: -1.2,
          entry_eval_p_value: 0.001,
          entry_eval_n: 50,
        })}
      />,
    );
    const tile = screen.getByTestId('tile-entry-eval');
    const valueSpan = within(tile).getByTestId('entry-eval-value');
    expect(normalizeColor(valueSpan.style.color)).toBe(normalizeColor(ZONE_DANGER));
  });

  it('Tile 1 value text is unstyled when not significant', () => {
    render(
      <EndgameStartVsEndSection
        data={buildPerf({
          entry_eval_mean_pawns: 1.2,
          entry_eval_p_value: 0.10,
          entry_eval_n: 50,
        })}
      />,
    );
    const tile = screen.getByTestId('tile-entry-eval');
    const valueSpan = within(tile).getByTestId('entry-eval-value');
    expect(valueSpan.style.color).toBe('');
  });

  it('Tile 1 value text is unstyled when significant but inside the neutral band (±0.5, Phase 82 D-09)', () => {
    render(
      <EndgameStartVsEndSection
        data={buildPerf({
          entry_eval_mean_pawns: 0.4,        // Clearly inside ±0.75 band → NEUTRAL
          entry_eval_p_value: 0.001,
          entry_eval_n: 50,
        })}
      />,
    );
    const tile = screen.getByTestId('tile-entry-eval');
    const valueSpan = within(tile).getByTestId('entry-eval-value');
    expect(valueSpan.style.color).toBe('');
  });

  it(
    'Tile 1 value text is ZONE_SUCCESS at the ±0.75 boundary when significant ' +
    '(Phase 82 D-12: boundary case for benchmark-IQR band)',
    () => {
      render(
        <EndgameStartVsEndSection
          data={buildPerf({
            entry_eval_mean_pawns: 0.75,        // ON the boundary → ZONE_SUCCESS
            entry_eval_p_value: 0.001,
            entry_eval_n: 50,
          })}
        />,
      );
      const valueSpan = within(screen.getByTestId('tile-entry-eval'))
        .getByTestId('entry-eval-value');
      expect(normalizeColor(valueSpan.style.color))
        .toBe(normalizeColor(ZONE_SUCCESS));
    },
  );

  it(
    'Tile 1 value text is unstyled for value 0.46 + p<0.001 ' +
    '(Phase 82 D-14: 0.46 sits inside the ±0.75 neutral band, ' +
    'so significance alone does not paint the tile; tile and LLM agree on neutral)',
    () => {
      render(
        <EndgameStartVsEndSection
          data={buildPerf({
            entry_eval_mean_pawns: 0.46,       // Inside ±0.75 band → NEUTRAL regardless of significance
            entry_eval_p_value: 0.001,
            entry_eval_n: 50,
          })}
        />,
      );
      const valueSpan = within(screen.getByTestId('tile-entry-eval'))
        .getByTestId('entry-eval-value');
      expect(valueSpan.style.color).toBe('');
    },
  );

  it(
    'Tile 1 value text is ZONE_DANGER for value -0.8 + p<0.05 ' +
    '(Phase 82 D-12: zone × sig negative case, ±0.75 band)',
    () => {
      render(
        <EndgameStartVsEndSection
          data={buildPerf({
            entry_eval_mean_pawns: -0.8,
            entry_eval_p_value: 0.01,
            entry_eval_n: 50,
          })}
        />,
      );
      const valueSpan = within(screen.getByTestId('tile-entry-eval'))
        .getByTestId('entry-eval-value');
      expect(normalizeColor(valueSpan.style.color))
        .toBe(normalizeColor(ZONE_DANGER));
    },
  );

  it('Tile 2 value text is ZONE_SUCCESS when score is high + p < 0.05', () => {
    render(
      <EndgameStartVsEndSection
        data={buildPerf({
          endgame_wdl: buildWdl(35, 10, 5),
          endgame_score_p_value: 0.001,
        })}
      />,
    );
    const tile = screen.getByTestId('tile-endgame-score');
    const valueSpan = within(tile).getByTestId('endgame-score-value');
    expect(normalizeColor(valueSpan.style.color)).toBe(normalizeColor(ZONE_SUCCESS));
  });

  it('Tile 2 value text is ZONE_DANGER when score is low + p < 0.05', () => {
    render(
      <EndgameStartVsEndSection
        data={buildPerf({
          endgame_wdl: buildWdl(10, 10, 30),
          endgame_score_p_value: 0.001,
        })}
      />,
    );
    const tile = screen.getByTestId('tile-endgame-score');
    const valueSpan = within(tile).getByTestId('endgame-score-value');
    expect(normalizeColor(valueSpan.style.color)).toBe(normalizeColor(ZONE_DANGER));
  });

  it('Tile 2 value text is unstyled when not significant', () => {
    render(
      <EndgameStartVsEndSection
        data={buildPerf({
          endgame_wdl: buildWdl(35, 10, 5),
          endgame_score_p_value: 0.20,
        })}
      />,
    );
    const tile = screen.getByTestId('tile-endgame-score');
    const valueSpan = within(tile).getByTestId('endgame-score-value');
    expect(valueSpan.style.color).toBe('');
  });

  it('Tile 1 renders the "Not enough data" placeholder when entry_eval_n < 10', () => {
    render(
      <EndgameStartVsEndSection
        data={buildPerf({ entry_eval_n: 5 })}
      />,
    );
    const tile = screen.getByTestId('tile-entry-eval');
    expect(within(tile).getByText(/Not enough data/i)).toBeTruthy();
    // Value-row + chart pair must be absent.
    expect(within(tile).queryByTestId('entry-eval-value')).toBeNull();
  });

  it('Tile 2 renders the "Not enough data" placeholder when endgame_wdl.total < 10', () => {
    render(
      <EndgameStartVsEndSection
        data={buildPerf({ endgame_wdl: buildWdl(2, 1, 2) })}
      />,
    );
    const tile = screen.getByTestId('tile-endgame-score');
    expect(within(tile).getByText(/Not enough data/i)).toBeTruthy();
    expect(within(tile).queryByTestId('endgame-score-value')).toBeNull();
  });

  it('passes Tile 1 D-15 constants to MiniBulletChart', () => {
    render(<EndgameStartVsEndSection data={buildPerf()} />);
    const calls = vi.mocked(MiniBulletChart).mock.calls;
    // Find the call that came from Tile 1: identified by center=0 and the
    // ±0.75 neutral band (benchmark IQR max(|p25|, |p75|) = 75 cp). Domain
    // ±3.75 makes the neutral band fill 20% of the axis to match the
    // Achievable-score chart's neutral-band proportion.
    const tile1Call = calls.find(
      ([props]) =>
        (props as { center?: number }).center === 0 &&
        (props as { neutralMin?: number }).neutralMin === -0.75,
    );
    expect(tile1Call).toBeDefined();
    expect(tile1Call?.[0]).toMatchObject({
      value: 1.2,
      center: 0,
      neutralMin: -0.75,
      neutralMax: 0.75,
      domain: 3.75,
      ciLow: 0.4,
      ciHigh: 2.0,
    });
  });

  it('passes Tile 2 score-bullet constants to MiniBulletChart (D-16)', () => {
    render(
      <EndgameStartVsEndSection
        data={buildPerf({
          // 25/10/15 → score = (25 + 5) / 50 = 0.6
          endgame_wdl: buildWdl(25, 10, 15),
        })}
      />,
    );
    const calls = vi.mocked(MiniBulletChart).mock.calls;
    // Phase 83: there are now two W+0.5D bullets (achievable + endgame score).
    // Disambiguate via Tile 2's distinct ±0.05 neutral band (vs achievable's
    // 0.45-0.55 band).
    const tile2Call = calls.find(
      ([props]) =>
        (props as { center?: number }).center === 0.5 &&
        (props as { neutralMin?: number }).neutralMin === -0.05,
    );
    expect(tile2Call).toBeDefined();
    expect(tile2Call?.[0]).toMatchObject({
      value: 0.6,
      center: 0.5,
      neutralMin: -0.05,
      neutralMax: 0.05,
      domain: 0.25,
    });
  });

  it('exposes stable kebab-case data-testids on the popover triggers', () => {
    render(<EndgameStartVsEndSection data={buildPerf()} />);
    expect(screen.getByTestId('entry-eval-popover-trigger')).toBeTruthy();
    expect(screen.getByTestId('endgame-score-popover-trigger')).toBeTruthy();
  });

  // ── Phase 83 Plan 03: 2x2 grid restructure (D-08..D-13) ────────────────────

  it('renders the achievable-score bullet inside tile-1 when entry_expected_score_n >= 10', () => {
    render(
      <EndgameStartVsEndSection
        data={buildPerf({
          entry_expected_score: 0.62,
          entry_expected_score_n: 50,
          entry_expected_score_p_value: 0.001,
          entry_expected_score_ci_low: 0.55,
          entry_expected_score_ci_high: 0.68,
        })}
      />,
    );
    const tile1 = screen.getByTestId('tile-entry-eval');
    expect(within(tile1).getByTestId('endgame-achievable-score')).toBeTruthy();
    expect(within(tile1).getByTestId('achievable-score-value')).toBeTruthy();
    expect(within(tile1).getByTestId('achievable-score-value').textContent).toMatch(/62/);
  });

  it(
    'renders "Not enough data yet" inside tile-1 row 2 when entry_expected_score_n < 10, ' +
      'independent of tile-1 row 1 entry-eval gate',
    () => {
      render(
        <EndgameStartVsEndSection
          data={buildPerf({
            // Row 1 (entry-eval) still has plenty of data
            entry_eval_n: 50,
            entry_eval_mean_pawns: 1.2,
            entry_eval_p_value: 0.001,
            // Row 2 (achievable score) is below the gate
            entry_expected_score_n: 5,
            entry_expected_score: 0.5,
          })}
        />,
      );
      const tile1 = screen.getByTestId('tile-entry-eval');
      // Row 1 still rendered
      expect(within(tile1).queryByTestId('entry-eval-value')).toBeTruthy();
      // Row 2 placeholder rendered, no value span
      expect(within(tile1).queryByTestId('achievable-score-value')).toBeNull();
      const placeholders = within(tile1).getAllByText(/Not enough data/i);
      expect(placeholders.length).toBeGreaterThanOrEqual(1);
    },
  );

  it('paints achievable-score value color when zone != neutral AND p < 0.05 (above band)', () => {
    render(
      <EndgameStartVsEndSection
        data={buildPerf({
          entry_expected_score: 0.62, // above 0.55 neutral max
          entry_expected_score_n: 50,
          entry_expected_score_p_value: 0.001,
        })}
      />,
    );
    const valueSpan = within(screen.getByTestId('tile-entry-eval')).getByTestId(
      'achievable-score-value',
    );
    expect(normalizeColor(valueSpan.style.color)).toBe(normalizeColor(ZONE_SUCCESS));
  });

  it('paints achievable-score value color when zone != neutral AND p < 0.05 (below band)', () => {
    render(
      <EndgameStartVsEndSection
        data={buildPerf({
          entry_expected_score: 0.40, // below 0.45 neutral min
          entry_expected_score_n: 50,
          entry_expected_score_p_value: 0.001,
        })}
      />,
    );
    const valueSpan = within(screen.getByTestId('tile-entry-eval')).getByTestId(
      'achievable-score-value',
    );
    expect(normalizeColor(valueSpan.style.color)).toBe(normalizeColor(ZONE_DANGER));
  });

  it(
    'does NOT paint achievable-score color when sig but inside neutral band ' +
      '(Phase 82 D-12 zone-AND-sig rule carried forward to D-11)',
    () => {
      render(
        <EndgameStartVsEndSection
          data={buildPerf({
            entry_expected_score: 0.52, // inside [0.45, 0.55] band
            entry_expected_score_n: 50,
            entry_expected_score_p_value: 0.001, // significant
          })}
        />,
      );
      const valueSpan = within(screen.getByTestId('tile-entry-eval')).getByTestId(
        'achievable-score-value',
      );
      expect(valueSpan.style.color).toBe('');
    },
  );

  it('renders MiniWDLBar at the top of tile-2 (D-13)', () => {
    render(<EndgameStartVsEndSection data={buildPerf()} />);
    const tile2 = screen.getByTestId('tile-endgame-score');
    expect(within(tile2).getByTestId('mini-wdl-bar')).toBeTruthy();
  });

  it('achievable-score popover trigger has data-testid="popover-trigger-achievable-score"', () => {
    render(<EndgameStartVsEndSection data={buildPerf()} />);
    expect(screen.getByTestId('popover-trigger-achievable-score')).toBeTruthy();
  });

  it('achievable-score popover body does NOT contain the word "underperformance" (D-10)', async () => {
    render(<EndgameStartVsEndSection data={buildPerf()} />);
    const trigger = screen.getByTestId('popover-trigger-achievable-score');
    // Open via click; the popover lives inside a radix Portal.
    trigger.click();
    // The portal renders synchronously after click; await a microtask so React
    // commits the open state.
    await Promise.resolve();
    expect(document.body.textContent ?? '').not.toMatch(/underperformance/i);
  });

  it('passes achievable-score W+0.5D constants to MiniBulletChart (D-12 axis parity)', () => {
    render(
      <EndgameStartVsEndSection
        data={buildPerf({
          entry_expected_score: 0.62,
          entry_expected_score_n: 50,
          entry_expected_score_ci_low: 0.55,
          entry_expected_score_ci_high: 0.68,
        })}
      />,
    );
    const calls = vi.mocked(MiniBulletChart).mock.calls;
    // The achievable bullet uses center=0.5 AND value=0.62 (distinct from
    // Tile 2 endgame score which is computed from endgame_wdl WDL counts).
    const achievableCall = calls.find(
      ([props]) =>
        (props as { center?: number }).center === 0.5 &&
        (props as { value?: number }).value === 0.62,
    );
    expect(achievableCall).toBeDefined();
    // MiniBulletChart's neutralMin/neutralMax are offsets from center; the
    // registry's [0.45, 0.55] absolute band must be passed as [-0.05, +0.05]
    // when center=0.5. Asserting the offset (not the absolute) is what catches
    // CR-01: passing absolute bounds collapses the neutral band to zero width
    // once the chart converts via `center + offset`. closeTo absorbs the float
    // artifact from 0.55 - 0.5 = 0.050000000000000044.
    expect(achievableCall?.[0]).toMatchObject({
      value: 0.62,
      center: 0.5,
      domain: 0.25,
    });
    const achievableProps = achievableCall?.[0] as {
      neutralMin: number;
      neutralMax: number;
    };
    expect(achievableProps.neutralMin).toBeCloseTo(-0.05, 6);
    expect(achievableProps.neutralMax).toBeCloseTo(0.05, 6);
  });
});
