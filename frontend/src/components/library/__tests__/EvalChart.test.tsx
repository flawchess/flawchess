// @vitest-environment jsdom
/**
 * EvalChart gem/great dot layer tests.
 *
 * `bestMoveDotSpec` is tested directly as a pure function rather than by mounting
 * recharts' custom `dot` render prop and inspecting rendered <circle> attributes:
 * recharts 3 renders dots behind portal/zIndex layers that make jsdom pixel-position
 * assertions unreliable (see EndgameClockDiffOverTimeChart.test.tsx's own note on this).
 * Testing the pure spec function directly proves the color/tier binding deterministically.
 *
 * A light full-mount smoke test (with the established ResponsiveContainer/ResizeObserver
 * stub pattern) confirms the layer wires into the real chart without crashing.
 */

import { afterEach, beforeAll, describe, expect, it, vi } from 'vitest';
import { cleanup, render, screen } from '@testing-library/react';
import { cloneElement, isValidElement } from 'react';
import type { ReactElement } from 'react';
import { FACEPALM_HIGH_CUTOFF, FACEPALM_TYPE_LABEL, toFacepalmPct } from '@/lib/facepalm';
import {
  MAIA_ACCENT,
  GREAT_ACCENT,
  TAC_ALLOWED,
  TAC_MISSED,
} from '@/lib/theme';
import type { EvalPoint, FlawMarker, PhaseTransitions } from '@/types/library';

// Recharts' <ResponsiveContainer> measures its parent with ResizeObserver; in jsdom
// the parent has zero dimensions so the inner chart refuses to render. Stub it with a
// fixed-size wrapper (same pattern as EndgameClockDiffOverTimeChart.test.tsx).
vi.mock('recharts', async () => {
  const actual = await vi.importActual<typeof import('recharts')>('recharts');
  return {
    ...actual,
    ResponsiveContainer: ({ children }: { children: ReactElement }) => (
      <div style={{ width: 800, height: 200 }}>
        {isValidElement(children)
          ? cloneElement(children as ReactElement<{ width?: number; height?: number }>, {
              width: 800,
              height: 200,
            })
          : children}
      </div>
    ),
  };
});

import { EvalChart, FlawTooltipDetail, FlawTooltipVerdict } from '../EvalChart';
import { bestMoveDotSpec } from '@/lib/bestMoveDot';

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

function evalPoint(overrides: Partial<EvalPoint> = {}): EvalPoint {
  return {
    ply: 0,
    es: 0.5,
    eval_cp: 0,
    eval_mate: null,
    clock_seconds: null,
    move_seconds: null,
    best_move: null,
    best_move_tier: null,
    maia_prob: null,
    ...overrides,
  };
}

describe('bestMoveDotSpec (color/tier binding)', () => {
  it('renders a violet dot for a gem ply', () => {
    const spec = bestMoveDotSpec(evalPoint({ best_move_tier: 'gem' }));
    expect(spec).not.toBeNull();
    expect(spec?.color).toBe(MAIA_ACCENT);
  });

  it('renders a blue dot for a great ply', () => {
    const spec = bestMoveDotSpec(evalPoint({ best_move_tier: 'great' }));
    expect(spec).not.toBeNull();
    expect(spec?.color).toBe(GREAT_ACCENT);
  });

  it('renders nothing for a null-tier ply', () => {
    expect(bestMoveDotSpec(evalPoint({ best_move_tier: null }))).toBeNull();
  });

  // Regression: best/good are board/card-only tiers. Before the
  // isRareMoveTier gate they fell into the "not gem → great" branch and painted a
  // blue dot mislabeled "Great" on the eval chart.
  it('renders nothing for a best-tier ply (board/card-only, not the eval chart)', () => {
    expect(bestMoveDotSpec(evalPoint({ best_move_tier: 'best' }))).toBeNull();
  });

  it('renders nothing for a good-tier ply (board/card-only, not the eval chart)', () => {
    expect(bestMoveDotSpec(evalPoint({ best_move_tier: 'good' }))).toBeNull();
  });

  it('renders nothing when the ply has no eval, even with a tier', () => {
    expect(bestMoveDotSpec(evalPoint({ best_move_tier: 'gem', es: null }))).toBeNull();
  });

  describe('user-only scoping (best_move_tier is position-scoped)', () => {
    it('renders the dot for a White user on an even (user) ply', () => {
      const spec = bestMoveDotSpec(evalPoint({ ply: 2, best_move_tier: 'gem' }), null, 'white');
      expect(spec).not.toBeNull();
      expect(spec?.color).toBe(MAIA_ACCENT);
    });

    it('excludes the dot for a White user on an odd (opponent) ply', () => {
      expect(
        bestMoveDotSpec(evalPoint({ ply: 3, best_move_tier: 'gem' }), null, 'white'),
      ).toBeNull();
    });

    it('renders the dot for a Black user on an odd (user) ply', () => {
      const spec = bestMoveDotSpec(evalPoint({ ply: 3, best_move_tier: 'great' }), null, 'black');
      expect(spec).not.toBeNull();
      expect(spec?.color).toBe(GREAT_ACCENT);
    });

    it('excludes the dot for a Black user on an even (opponent) ply', () => {
      expect(
        bestMoveDotSpec(evalPoint({ ply: 2, best_move_tier: 'great' }), null, 'black'),
      ).toBeNull();
    });

    it('renders every tier when no userColor is provided (back-compat)', () => {
      expect(bestMoveDotSpec(evalPoint({ ply: 3, best_move_tier: 'gem' }))).not.toBeNull();
    });
  });

  it('emphasizes a highlighted ply with a larger radius at full opacity', () => {
    const base = bestMoveDotSpec(evalPoint({ ply: 5, best_move_tier: 'gem' }));
    const highlighted = bestMoveDotSpec(
      evalPoint({ ply: 5, best_move_tier: 'gem' }),
      new Set([5]),
    );
    expect(base).not.toBeNull();
    expect(highlighted).not.toBeNull();
    expect(highlighted!.radius).toBeGreaterThan(base!.radius);
    expect(highlighted!.opacity).toBe(1);
  });

  it('dims a non-matching ply while a highlight set is active', () => {
    const spec = bestMoveDotSpec(evalPoint({ ply: 5, best_move_tier: 'great' }), new Set([9]));
    expect(spec).not.toBeNull();
    expect(spec!.opacity).toBeLessThan(1);
  });

  it('treats an empty highlight set as a no-op — never dims everything', () => {
    const spec = bestMoveDotSpec(evalPoint({ ply: 5, best_move_tier: 'gem' }), new Set());
    expect(spec).not.toBeNull();
    expect(spec!.opacity).toBe(1);
  });
});

describe('EvalChart gem/great dot layer — mount smoke test', () => {
  const PHASE_TRANSITIONS: PhaseTransitions = { middlegame_ply: null, endgame_ply: null };
  const FLAW_MARKERS: FlawMarker[] = [];

  it('mounts without crashing when evalSeries mixes gem, great, flaw, and plain plies', () => {
    const evalSeries: EvalPoint[] = [
      evalPoint({ ply: 0, es: 0.5 }),
      evalPoint({ ply: 1, es: 0.6, best_move_tier: 'gem', maia_prob: 0.1 }),
      evalPoint({ ply: 2, es: 0.4, best_move_tier: 'great', maia_prob: 0.3 }),
      evalPoint({ ply: 3, es: 0.55 }),
    ];
    render(
      <EvalChart
        gameId={99}
        evalSeries={evalSeries}
        flawMarkers={FLAW_MARKERS}
        phaseTransitions={PHASE_TRANSITIONS}
        moves={['e4', 'e5', 'Nf3', 'Nc6']}
      />,
    );
    expect(screen.getByTestId('eval-chart-99')).toBeTruthy();
  });
});

/** jsdom normalizes color strings (oklch(0.50 ..) -> oklch(0.5 ..)); compare normalized forms. */
function normalized(color: string): string {
  const probe = document.createElement('div');
  probe.style.color = color;
  return probe.style.color;
}

describe('FlawTooltipVerdict (260-G1: one verdict line, colour on icons only)', () => {
  // Local test constant: facepalm scores are 0..1 on the wire, the cut is a percent (D-21).
  const PCT_SCALE = 100;
  const ABOVE_CUT = (FACEPALM_HIGH_CUTOFF + 1) / PCT_SCALE;
  const BELOW_CUT = (FACEPALM_HIGH_CUTOFF - 1) / PCT_SCALE;

  function verdictMarker(overrides: Partial<FlawMarker>): FlawMarker {
    return {
      ply: 10,
      severity: 'blunder',
      tags: [],
      is_user: true,
      move_san: 'Qxb2',
      allowed_tactic_motif: null,
      allowed_tactic_confidence: null,
      allowed_tactic_depth: null,
      missed_tactic_motif: null,
      missed_tactic_confidence: null,
      missed_tactic_depth: null,
      ...overrides,
    };
  }

  it('states a user facepalm blunder and its score on one neutral line with the ??? icon', () => {
    render(<FlawTooltipVerdict marker={verdictMarker({ facepalm_score: ABOVE_CUT })} />);
    const verdict = screen.getByTestId('eval-chart-tooltip-verdict');
    expect(verdict.querySelector('span')?.textContent).toBe(`You \u00b7 Facepalm ${toFacepalmPct(ABOVE_CUT)}%`);
    expect(verdict.getAttribute('style')).toBeNull();
    expect(verdict.className).toContain('text-foreground');
    // The ??? icon replaces the dot glyph: exactly one svg, and it carries the ??? text.
    const icons = verdict.querySelectorAll('svg');
    expect(icons).toHaveLength(1);
    expect(icons[0]?.textContent).toBe('???');
  });

  it('names an opponent facepalm blunder', () => {
    render(
      <FlawTooltipVerdict marker={verdictMarker({ is_user: false, facepalm_score: ABOVE_CUT })} />,
    );
    const verdict = screen.getByTestId('eval-chart-tooltip-verdict');
    expect(verdict.querySelector('span')?.textContent).toBe(
      `Opponent \u00b7 Facepalm ${toFacepalmPct(ABOVE_CUT)}%`,
    );
  });

  it('shows the ?? icon and the score for a blunder below the cut', () => {
    render(<FlawTooltipVerdict marker={verdictMarker({ facepalm_score: BELOW_CUT })} />);
    const verdict = screen.getByTestId('eval-chart-tooltip-verdict');
    expect(verdict.querySelector('span')?.textContent).toBe(`You \u00b7 Blunder ${toFacepalmPct(BELOW_CUT)}%`);
    const icons = verdict.querySelectorAll('svg');
    expect(icons).toHaveLength(1);
    expect(icons[0]?.textContent).toBe('??');
  });

  it('shows no percent for an unscored blunder', () => {
    render(<FlawTooltipVerdict marker={verdictMarker({ facepalm_score: null })} />);
    const verdict = screen.getByTestId('eval-chart-tooltip-verdict');
    expect(verdict.textContent).toBe('??You \u00b7 Blunder');
    expect(verdict.querySelector('svg')?.textContent).toBe('??');
  });

  it('keeps the dot glyph and no percent for an opponent mistake with a high score', () => {
    render(
      <FlawTooltipVerdict
        marker={verdictMarker({ severity: 'mistake', is_user: false, facepalm_score: ABOVE_CUT })}
      />,
    );
    const verdict = screen.getByTestId('eval-chart-tooltip-verdict');
    expect(verdict.textContent).toBe('Opponent \u00b7 Mistake');
    // The opponent dot glyph is a hollow square.
    expect(verdict.querySelector('rect')).not.toBeNull();
  });
});

describe('FlawTooltipDetail (260-G1)', () => {
  const PCT_SCALE = 100;
  const ABOVE_CUT = (FACEPALM_HIGH_CUTOFF + 1) / PCT_SCALE;

  function detailMarker(overrides: Partial<FlawMarker>): FlawMarker {
    return {
      ply: 10,
      severity: 'blunder',
      tags: [],
      is_user: true,
      move_san: 'Qxb2',
      allowed_tactic_motif: null,
      allowed_tactic_confidence: null,
      allowed_tactic_depth: null,
      missed_tactic_motif: null,
      missed_tactic_confidence: null,
      missed_tactic_depth: null,
      ...overrides,
    };
  }

  it.each(['allowed_loss', 'missed_win'] as const)(
    'names the %s type in words when the blunder has no tactic row',
    (type) => {
      render(
        <FlawTooltipDetail
          marker={detailMarker({ facepalm_score: ABOVE_CUT, facepalm_type: type })}
          tactics={[]}
          tags={[]}
        />,
      );
      expect(screen.getByTestId('eval-chart-tooltip-facepalm-type').textContent).toBe(
        FACEPALM_TYPE_LABEL[type].toLowerCase(),
      );
    },
  );

  it('drops the type line and renders a neutral tactic row with a coloured icon when a tactic exists', () => {
    render(
      <FlawTooltipDetail
        marker={detailMarker({ facepalm_score: ABOVE_CUT, facepalm_type: 'allowed_loss' })}
        tactics={[{ orientation: 'allowed', motif: 'fork', family: 'fork', depth: 1 }]}
        tags={[]}
      />,
    );
    expect(screen.queryByTestId('eval-chart-tooltip-facepalm-type')).toBeNull();
    const row = screen.getByText(/allowed: fork/);
    expect(row.textContent).toBe('allowed: fork');
    expect(row.getAttribute('style')).toBeNull();
    const icon = row.querySelector('svg') as SVGElement;
    expect(icon.style.color).toBe(normalized(TAC_ALLOWED));
  });

  it('colours the icon of a missed tactic row teal and leaves its text neutral', () => {
    render(
      <FlawTooltipDetail
        marker={detailMarker({ facepalm_score: ABOVE_CUT, facepalm_type: 'missed_win' })}
        tactics={[{ orientation: 'missed', motif: 'fork', family: 'fork', depth: null }]}
        tags={[]}
      />,
    );
    const row = screen.getByText(/missed: fork/);
    expect(row.getAttribute('style')).toBeNull();
    expect((row.querySelector('svg') as SVGElement).style.color).toBe(normalized(TAC_MISSED));
  });

  it('shows no type line for a mistake without tactics', () => {
    render(
      <FlawTooltipDetail
        marker={detailMarker({ severity: 'mistake', facepalm_score: ABOVE_CUT, facepalm_type: 'allowed_loss' })}
        tactics={[]}
        tags={[]}
      />,
    );
    expect(screen.queryByTestId('eval-chart-tooltip-facepalm-type')).toBeNull();
  });
});
