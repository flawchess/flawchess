// @vitest-environment jsdom
/**
 * Unit and render tests for the shared inactivityGapReferenceLines helper (SC-4).
 *
 * Pure cases (empty/single/short arrays) assert on the returned array length
 * directly without mounting. Render cases extract the label ReactElement from
 * the returned ReferenceLine elements and render it in a plain <svg>; this
 * approach was required after recharts 3 moved label rendering to React portals
 * (ZIndexLayer/zIndex-layer) which don't land in the jsdom query container.
 */
import type { ReactElement } from 'react';
import { describe, it, expect, beforeAll, afterEach, vi } from 'vitest';
import { render, screen, cleanup } from '@testing-library/react';
import { cloneElement, isValidElement } from 'react';

import { inactivityGapReferenceLines } from '../InactivityGapReferenceLines';

beforeAll(() => {
  // jsdom ships without window.matchMedia; stub it before any render.
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

// ---------------------------------------------------------------------------
// Pure / unit cases: no rendering needed
// ---------------------------------------------------------------------------

describe('inactivityGapReferenceLines — pure cases', () => {
  it('returns [] for empty dates', () => {
    expect(inactivityGapReferenceLines({ dates: [] }).length).toBe(0);
  });

  it('returns [] for a single date (no pair)', () => {
    expect(inactivityGapReferenceLines({ dates: ['2024-01-01'] }).length).toBe(0);
  });

  it('returns [] when all consecutive pairs are <= 90 days apart', () => {
    const dates = ['2024-01-01', '2024-01-08', '2024-02-01', '2024-02-15'];
    expect(inactivityGapReferenceLines({ dates }).length).toBe(0);
  });

  it('returns [] for a gap below the 90-day threshold (e.g. 60 days)', () => {
    const dates = ['2024-01-01', '2024-03-01']; // 60 days apart, under threshold
    expect(inactivityGapReferenceLines({ dates }).length).toBe(0);
  });

  it('returns one element for exactly one >90-day gap', () => {
    const dates = ['2024-01-01', '2024-05-01']; // 121 days apart
    expect(inactivityGapReferenceLines({ dates }).length).toBe(1);
  });

  it('returns two elements for two >90-day gaps', () => {
    const dates = ['2024-01-01', '2024-05-01', '2024-09-01']; // 121 + 123 days
    expect(inactivityGapReferenceLines({ dates }).length).toBe(2);
  });

  it('returned elements have stable React keys derived from gap.afterIndex', () => {
    const dates = ['2024-01-01', '2024-05-01']; // gap at afterIndex=0
    const elements = inactivityGapReferenceLines({ dates });
    expect(elements.length).toBe(1);
    // React key is set as a prop — accessible via element.key
    expect(elements[0]?.key).toBe('inactivity-gap-0');
  });
});

// ---------------------------------------------------------------------------
// Render cases: render the ReferenceLine label content directly
// ---------------------------------------------------------------------------
//
// recharts 3 uses React portals (ZIndexLayer) for ReferenceLine rendering —
// label content doesn't land in the query container in jsdom without a real
// browser layout engine. Instead, we extract the `label` ReactElement from the
// returned <ReferenceLine> props and render it directly in a plain <svg> to
// verify the label content independently of recharts' internal layout system.

/** Fixture with a >90-day gap between index 0 and 1 (121 days). */
const GAP_DATES = ['2024-01-01', '2024-05-01', '2024-05-08'];

/** Fixture where all consecutive pairs are 7 days apart — no gap. */
const NO_GAP_DATES = ['2024-01-01', '2024-01-08', '2024-01-15', '2024-01-22'];

/**
 * Extract the `label` ReactElement from the first ReferenceLine returned by
 * inactivityGapReferenceLines and render it with a mock viewBox. This bypasses
 * recharts' portal-based rendering (which requires a real layout engine) while
 * still testing the actual label component that recharts would render.
 */
function renderFirstGapLabel(dates: string[]) {
  const elements = inactivityGapReferenceLines({ dates });
  if (!elements.length) return null;
  const first = elements[0] as ReactElement<{ label?: ReactElement }>;
  const label = first?.props?.label;
  if (!label) return null;
  // Inject viewBox so the label receives coordinates (recharts would do this)
  const labelWithViewBox = isValidElement(label)
    ? cloneElement(label as ReactElement<{ viewBox?: { x: number; y: number } }>, {
        viewBox: { x: 100, y: 50 },
      })
    : label;
  return render(<svg>{labelWithViewBox}</svg>);
}

describe('inactivityGapReferenceLines — render cases (no yAxisId)', () => {
  it('renders data-testid="inactivity-gap-label" for a gap fixture', () => {
    const result = renderFirstGapLabel(GAP_DATES);
    expect(result).not.toBeNull();
    expect(result!.container.querySelector('[data-testid="inactivity-gap-label"]')).not.toBeNull();
  });

  it('renders data-testid="inactivity-gap-glyph" (Palmtree icon) for a gap fixture', () => {
    const result = renderFirstGapLabel(GAP_DATES);
    expect(result).not.toBeNull();
    expect(result!.container.querySelector('[data-testid="inactivity-gap-glyph"]')).not.toBeNull();
  });

  it('renders the compact gap label (e.g. "Nmo") for a gap fixture', () => {
    renderFirstGapLabel(GAP_DATES);
    // computeInactivityGaps labels gaps < 365 days as compact "Nmo"
    expect(screen.getByText(/^\d+mo$/)).toBeTruthy();
  });

  it('renders no gap label for a gap-free fixture', () => {
    const elements = inactivityGapReferenceLines({ dates: NO_GAP_DATES });
    // No ReferenceLine elements produced → no label content to render
    expect(elements.length).toBe(0);
  });
});

describe('inactivityGapReferenceLines — yAxisId forwarding', () => {
  it('yAxisId prop is forwarded to the returned ReferenceLine element', () => {
    const dates = ['2024-01-01', '2024-05-01'];
    const elements = inactivityGapReferenceLines({ dates, yAxisId: 'elo' });
    expect(elements.length).toBe(1);
    // The yAxisId prop should be present on the ReactElement props
    const props = elements[0]?.props as { yAxisId?: string } | undefined;
    expect(props?.yAxisId).toBe('elo');
  });

  it('yAxisId is absent from the ReferenceLine element when not provided', () => {
    const dates = ['2024-01-01', '2024-05-01'];
    const elements = inactivityGapReferenceLines({ dates });
    expect(elements.length).toBe(1);
    const props = elements[0]?.props as { yAxisId?: string } | undefined;
    expect(props?.yAxisId).toBeUndefined();
  });
});
