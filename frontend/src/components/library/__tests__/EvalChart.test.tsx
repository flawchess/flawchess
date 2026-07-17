// @vitest-environment jsdom
/**
 * EvalChart gem/great dot layer tests (Phase 175 Plan 06).
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
import { MAIA_ACCENT, GREAT_ACCENT } from '@/lib/theme';
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

import { EvalChart } from '../EvalChart';
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
