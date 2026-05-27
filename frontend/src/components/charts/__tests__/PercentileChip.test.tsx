// @vitest-environment jsdom
/**
 * Phase 94.4 Plan 07: PercentileChip peer-relative rewrite tests.
 *
 * 13 assertions cover the new peer-relative chip:
 *   1. Chip face renders `SquarePercent` icon + bare integer (no "p" prefix,
 *      no "Top X%" / "Bottom X%").
 *   2. MIN_PERCENT=1 floor (no "0").
 *   3. p99 ceiling (no "100").
 *   4. Color band routing — red < 25 / neutral 25..75 / green > 75 (single-branch,
 *      all flavors `higher_is_better` per CONTEXT D-07a).
 *   5. aria-label preserves direction word ("bottom" < 50, "top" >= 50) per D-06b.
 *   6. Per-TC aria-label includes "in {tc}".
 *   7. Per-TC popover bullet 1 reads "Compared to other ~{anchor}-rated players in {tc}."
 *   8. Aggregated popover bullet 1 reads "Compared to other ~{anchor}-rated players,
 *      aggregated across the time controls you play."
 *   9. NO flame icon at any percentile (regression guard for commit-6766898c).
 *  10. Lichess-anchored bullet 4 reads "Anchored on your Lichess {tc} ({anchor})."
 *  11. chess.com-anchored bullet 4 with chesscomRawRating includes the
 *      "{raw} -> {anchor} Lichess-equivalent" conversion form.
 *  12. chess.com-anchored bullet 4 WITHOUT chesscomRawRating uses simpler form.
 *  13. Bullet 3 (filter independence) is COPY_FILTER_INDEPENDENCE verbatim.
 *
 * Critical regression test: Test 9 explicitly asserts NO flame icon renders at
 * every percentile in [1, 23, 50, 75, 90, 95, 99] — locks the commit-6766898c
 * flame removal per CONTEXT D-06.
 */

import { afterEach, beforeAll, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen } from '@testing-library/react';

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

import { PercentileChip, type PercentileChipFlavor } from '../PercentileChip';
import { GAUGE_NEUTRAL, ZONE_DANGER, ZONE_SUCCESS } from '@/lib/theme';

const TID = 'test-pctl-chip';

type RenderOpts = {
  flavor?: PercentileChipFlavor;
  tc?: 'bullet' | 'blitz' | 'rapid' | 'classical';
  anchorRating?: number;
  anchorSource?: 'lichess' | 'chesscom';
  chesscomRawRating?: number;
  metricLabel?: string;
};

function renderChip(percentile: number, opts: RenderOpts = {}) {
  return render(
    <PercentileChip
      percentile={percentile}
      flavor={opts.flavor ?? 'score-gap'}
      tc={opts.tc}
      anchorRating={opts.anchorRating ?? 1600}
      anchorSource={opts.anchorSource ?? 'lichess'}
      chesscomRawRating={opts.chesscomRawRating}
      metricLabel={opts.metricLabel ?? 'Endgame Score Gap'}
      testId={TID}
    />,
  );
}

// jsdom normalizes `oklch(0.50 ...)` to `oklch(0.5 ...)`, so we extract the
// numeric triplet and compare against the theme constant's parsed triplet.
function parseOklch(s: string): readonly [number, number, number] | null {
  const m = s.match(/oklch\(\s*([\d.]+)\s+([\d.]+)\s+([\d.]+)\s*\)/);
  if (!m) return null;
  return [Number(m[1]), Number(m[2]), Number(m[3])] as const;
}

describe('PercentileChip — chip face (Phase 94.4)', () => {
  // Test 1: icon + bare integer form
  it.each([
    [1, '1'],
    [10, '10'],
    [23, '23'],
    [50, '50'],
    [75, '75'],
    [90, '90'],
    [99, '99'],
  ])('renders icon + "%s" form for percentile=%d', (pct, expected) => {
    renderChip(pct);
    const chip = screen.getByTestId(TID);
    expect(chip.textContent ?? '').toBe(expected);
    // Icon must always be present — distinguishes percentile from raw percent.
    expect(chip.querySelector('svg')).not.toBeNull();
  });

  // Test 2: MIN_PERCENT=1 floor
  it.each([0, 0.4, -5])('floors at "1" for percentile=%d (no "0")', (pct) => {
    renderChip(pct);
    const txt = screen.getByTestId(TID).textContent ?? '';
    expect(txt).toBe('1');
  });

  // Test 3: p99 ceiling
  it.each([99.6, 100, 105])('clamps at "99" for percentile=%d (no "100")', (pct) => {
    renderChip(pct);
    const txt = screen.getByTestId(TID).textContent ?? '';
    expect(txt).toBe('99');
  });

  // Test 4: color band routing
  it('routes red (ZONE_DANGER) band for percentile=20', () => {
    renderChip(20);
    const chip = screen.getByTestId(TID);
    expect(parseOklch(chip.style.backgroundColor)).toEqual(parseOklch(ZONE_DANGER));
  });

  it('routes blue (GAUGE_NEUTRAL) band for percentile=50', () => {
    renderChip(50);
    const chip = screen.getByTestId(TID);
    expect(parseOklch(chip.style.backgroundColor)).toEqual(parseOklch(GAUGE_NEUTRAL));
  });

  it('routes green (ZONE_SUCCESS) band for percentile=80', () => {
    renderChip(80);
    const chip = screen.getByTestId(TID);
    expect(parseOklch(chip.style.backgroundColor)).toEqual(parseOklch(ZONE_SUCCESS));
  });

  // Test 5: aria-label direction word (D-06b)
  it('aria-label includes "bottom" for percentile=23', () => {
    renderChip(23);
    const aria = screen.getByTestId(TID).getAttribute('aria-label') ?? '';
    expect(aria.toLowerCase()).toContain('bottom');
  });

  it('aria-label includes "top" for percentile=70', () => {
    renderChip(70);
    const aria = screen.getByTestId(TID).getAttribute('aria-label') ?? '';
    expect(aria.toLowerCase()).toContain('top');
  });

  // Test 6: per-TC aria-label includes "in {tc}"
  it('per-TC chip with tc="bullet" includes "in bullet" in aria-label', () => {
    renderChip(23, { flavor: 'time-pressure-score-gap', tc: 'bullet' });
    const aria = screen.getByTestId(TID).getAttribute('aria-label') ?? '';
    expect(aria).toContain('in bullet');
  });
});

describe('PercentileChip — popover bullets (Phase 94.4)', () => {
  // Test 7: per-TC bullet 1 — direct percentile statement
  it('per-TC popover bullet 1 reads "Your recent {metric} is in the bottom 23% of ~1600-rated players in bullet."', () => {
    renderChip(23, {
      flavor: 'time-pressure-score-gap',
      tc: 'bullet',
      anchorRating: 1600,
      metricLabel: 'Time-Pressure Score Gap',
    });
    fireEvent.click(screen.getByTestId(TID));
    const body = screen.getByTestId(`${TID}-popover`).textContent ?? '';
    expect(body).toContain(
      'Your recent Time-Pressure Score Gap is in the bottom 23% of ~1600-rated players in bullet.',
    );
  });

  // Test 8: aggregated bullet 1 — direct percentile statement
  it('aggregated popover bullet 1 reads "Your recent {metric} is in the bottom 23% of ~1600-rated players, aggregated across the time controls you play."', () => {
    renderChip(23, {
      flavor: 'score-gap',
      anchorRating: 1600,
      metricLabel: 'Endgame Score Gap',
    });
    fireEvent.click(screen.getByTestId(TID));
    const body = screen.getByTestId(`${TID}-popover`).textContent ?? '';
    expect(body).toContain(
      'Your recent Endgame Score Gap is in the bottom 23% of ~1600-rated players, aggregated across the time controls you play.',
    );
  });

  // Test 8b: "top X%" form when percentile >= 50 (pct=90 → top 10%)
  it('high-percentile bullet 1 uses "top {100-pct}%" form (pct=90 → top 10%)', () => {
    renderChip(90, {
      flavor: 'score-gap',
      anchorRating: 1600,
      metricLabel: 'Endgame Score Gap',
    });
    fireEvent.click(screen.getByTestId(TID));
    const body = screen.getByTestId(`${TID}-popover`).textContent ?? '';
    expect(body).toContain(
      'Your recent Endgame Score Gap is in the top 10% of ~1600-rated players, aggregated across the time controls you play.',
    );
  });

  // Test 8c: "recent" is wrapped in <em> for emphasis
  it('bullet 1 wraps "recent" in an <em> element', () => {
    renderChip(40, { flavor: 'score-gap', anchorRating: 1600 });
    fireEvent.click(screen.getByTestId(TID));
    const popover = screen.getByTestId(`${TID}-popover`);
    const em = popover.querySelector('em');
    expect(em).not.toBeNull();
    expect(em?.textContent).toBe('recent');
  });

  // Test 10: Lichess-anchored bullet 4
  it('Lichess-anchored bullet 4 reads "Anchored on your Lichess bullet (1600)."', () => {
    renderChip(40, {
      flavor: 'time-pressure-score-gap',
      tc: 'bullet',
      anchorRating: 1600,
      anchorSource: 'lichess',
    });
    fireEvent.click(screen.getByTestId(TID));
    const body = screen.getByTestId(`${TID}-popover`).textContent ?? '';
    expect(body).toContain('Anchored on your Lichess bullet (1600).');
  });

  // Test 11: chess.com-anchored bullet 4 WITH chesscomRawRating
  it('chess.com-anchored bullet 4 with chesscomRawRating shows raw -> Lichess-equivalent conversion', () => {
    renderChip(40, {
      flavor: 'clock-gap',
      tc: 'blitz',
      anchorRating: 1920,
      anchorSource: 'chesscom',
      chesscomRawRating: 1830,
    });
    fireEvent.click(screen.getByTestId(TID));
    const body = screen.getByTestId(`${TID}-popover`).textContent ?? '';
    expect(body).toContain('Anchored on your chess.com blitz (1830 -> 1920 Lichess-equivalent).');
    expect(body).not.toContain('ChessGoals');
  });

  // Test 12: chess.com-anchored bullet 4 WITHOUT chesscomRawRating
  it('chess.com-anchored bullet 4 without chesscomRawRating uses simpler form', () => {
    renderChip(40, {
      flavor: 'clock-gap',
      tc: 'rapid',
      anchorRating: 1920,
      anchorSource: 'chesscom',
    });
    fireEvent.click(screen.getByTestId(TID));
    const body = screen.getByTestId(`${TID}-popover`).textContent ?? '';
    expect(body).toContain('Anchored on your chess.com rapid (1920).');
    expect(body).not.toContain('Lichess-equivalent');
  });

  // Test 13: bullet 3 is COPY_FILTER_INDEPENDENCE verbatim
  it('bullet 3 (filter independence) reads "UI filters do not affect this percentile."', () => {
    renderChip(40, { flavor: 'score-gap' });
    fireEvent.click(screen.getByTestId(TID));
    const body = screen.getByTestId(`${TID}-popover`).textContent ?? '';
    expect(body).toContain('UI filters do not affect this percentile.');
  });

  // Bullet 2 (recent-games basis) — per-TC + aggregated forms
  it('per-TC bullet 2 mentions "most recent 1000 rated games in bullet over the last 36 months"', () => {
    renderChip(40, {
      flavor: 'time-pressure-score-gap',
      tc: 'bullet',
    });
    fireEvent.click(screen.getByTestId(TID));
    const body = screen.getByTestId(`${TID}-popover`).textContent ?? '';
    expect(body).toContain('most recent 1000 rated games in bullet over the last 36 months');
    expect(body).toContain('+/-100 Elo');
  });

  it('aggregated bullet 2 mentions "most recent 1000 rated games per time control over the last 36 months"', () => {
    renderChip(40, { flavor: 'score-gap' });
    fireEvent.click(screen.getByTestId(TID));
    const body = screen.getByTestId(`${TID}-popover`).textContent ?? '';
    expect(body).toContain('most recent 1000 rated games per time control over the last 36 months');
    expect(body).toContain('+/-100 Elo');
  });
});

// ── Test 9: REGRESSION GUARD — NO FLAME ICON AT ANY PERCENTILE ──────────────
//
// Locks the commit-6766898c flame removal per CONTEXT D-06. The peer-relative
// pivot does NOT change this constraint — color band carries direction; tail
// emphasis is no longer expressed via icon.

describe('PercentileChip — NO flame icon (regression guard for commit-6766898c)', () => {
  it.each([1, 23, 50, 75, 90, 95, 99])(
    'renders NO flame icon at percentile=%d (commit-6766898c regression)',
    (pct) => {
      const { container } = renderChip(pct);
      expect(screen.queryByTestId(/flame/i)).toBeNull();
      // Check no <svg> child or DOM node has a flame-related class.
      expect(container.querySelector('[class*="flame"]')).toBeNull();
      expect(container.querySelector('[class*="Flame"]')).toBeNull();
      // No element should reference "flame" in its data-* attributes either.
      expect(container.querySelector('[data-icon*="flame" i]')).toBeNull();
    },
  );

  it('renders NO flame icon when popover is opened (any flavor, any percentile)', () => {
    const { container } = renderChip(95, {
      flavor: 'conversion',
      anchorRating: 1700,
      anchorSource: 'lichess',
    });
    fireEvent.click(screen.getByTestId(TID));
    expect(screen.queryByTestId(/flame/i)).toBeNull();
    expect(container.querySelector('[class*="flame"]')).toBeNull();
    expect(container.querySelector('[class*="Flame"]')).toBeNull();
  });
});

// ── Contract: data-testid + popover trigger ─────────────────────────────────

describe('PercentileChip — contract', () => {
  it('chip trigger has the supplied data-testid; popover Content has `${testId}-popover`', () => {
    renderChip(85);
    expect(screen.getByTestId(TID)).toBeTruthy();
    fireEvent.click(screen.getByTestId(TID));
    expect(screen.getByTestId(`${TID}-popover`)).toBeTruthy();
  });

  it('aria-label includes metricLabel and the rendered percentile token', () => {
    renderChip(73, { metricLabel: 'Endgame Score Gap' });
    const aria = screen.getByTestId(TID).getAttribute('aria-label') ?? '';
    expect(aria).toContain('Endgame Score Gap');
    expect(aria).toContain('p73');
  });
});
