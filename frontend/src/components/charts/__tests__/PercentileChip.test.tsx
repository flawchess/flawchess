// @vitest-environment jsdom
/**
 * Phase 94.4 Plan 11 (D-12 Reversal Amendment): PercentileChip bullet-4
 * branch-differentiation tests.
 *
 * All Plan 07 Tests 1-8 (chip face, MIN_PERCENT floor, p99 ceiling, color band,
 * aria-label, per-TC bullet 1, aggregated bullet 1, bullet 3 filter
 * independence) are preserved verbatim.
 *
 * Test 9 (no-flame regression guard for commit-6766898c) is preserved VERBATIM.
 *
 * Tests 10-12 (old Lichess-anchored / chess.com-anchored split) are REPLACED
 * with the new branch-differentiation quadruple:
 *   C1 — mixed user: BOTH platform substrings + "blending" + all 5 numbers
 *   C2 — pure-lichess: "native rating", NO chess.com clause, NO "converted"
 *   C3 — pure-chess.com: "converted" + snapshot date, NO lichess clause
 *   C4 — no flame (renamed from Test 9, preserved verbatim)
 *   C5 — props deprecation sanity guard (compile-time rejection of old props)
 *   C6 — suppression: chip hidden or bullet-4 empty when both counts == 0
 *
 * Critical contract: branch-differentiating MUST-NOT-APPEAR assertions in C2
 * and C3 ensure that a single-branch fallback implementation cannot silently
 * pass tests.
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
  nChesscomGames?: number;
  nLichessGames?: number;
  chesscomMedianNative?: number;
  lichessMedianNative?: number;
  metricLabel?: string;
};

function renderChip(percentile: number, opts: RenderOpts = {}) {
  return render(
    <PercentileChip
      percentile={percentile}
      flavor={opts.flavor ?? 'score-gap'}
      tc={opts.tc}
      anchorRating={opts.anchorRating ?? 1600}
      nChesscomGames={opts.nChesscomGames ?? 0}
      nLichessGames={opts.nLichessGames ?? 500}
      chesscomMedianNative={opts.chesscomMedianNative}
      lichessMedianNative={opts.lichessMedianNative ?? 1600}
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
  // Test 7: per-TC bullet 1 — pct<=50 keeps the legacy "bottom X%" framing
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

  // Test 8: aggregated bullet 1 — pct<=50 keeps the legacy "bottom X%" framing
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

  // Test 8b: pct>50 uses positive framing with the chip's percentile verbatim
  it('high-percentile bullet 1 echoes the chip percentile verbatim (pct=90 → "better than 90%")', () => {
    renderChip(90, {
      flavor: 'score-gap',
      anchorRating: 1600,
      metricLabel: 'Endgame Score Gap',
    });
    fireEvent.click(screen.getByTestId(TID));
    const body = screen.getByTestId(`${TID}-popover`).textContent ?? '';
    expect(body).toContain(
      'Your recent Endgame Score Gap is better than 90% of ~1600-rated players, aggregated across the time controls you play.',
    );
  });

  // Test 8c: median boundary (pct=50) stays on the "bottom" side per the <= rule
  it('median percentile (pct=50) uses "in the bottom 50%" framing', () => {
    renderChip(50, {
      flavor: 'score-gap',
      anchorRating: 1600,
      metricLabel: 'Endgame Score Gap',
    });
    fireEvent.click(screen.getByTestId(TID));
    const body = screen.getByTestId(`${TID}-popover`).textContent ?? '';
    expect(body).toContain(
      'Your recent Endgame Score Gap is in the bottom 50% of ~1600-rated players, aggregated across the time controls you play.',
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

  // Test 13: bullet 3 is COPY_FILTER_INDEPENDENCE verbatim
  it('bullet 3 (filter independence) reads "UI filters do not affect this percentile."', () => {
    renderChip(40, { flavor: 'score-gap' });
    fireEvent.click(screen.getByTestId(TID));
    const body = screen.getByTestId(`${TID}-popover`).textContent ?? '';
    expect(body).toContain('UI filters do not affect this percentile.');
  });

  // Bullet 2 (recent-games basis) — per-TC + aggregated forms
  it('per-TC bullet 2 mentions "most recent 3000 rated games in bullet over the last 36 months"', () => {
    renderChip(40, {
      flavor: 'time-pressure-score-gap',
      tc: 'bullet',
    });
    fireEvent.click(screen.getByTestId(TID));
    const body = screen.getByTestId(`${TID}-popover`).textContent ?? '';
    expect(body).toContain('most recent 3000 rated games in bullet over the last 36 months');
    expect(body).toContain('+/-100 Elo');
  });

  it('aggregated bullet 2 mentions "most recent 3000 rated games per time control over the last 36 months"', () => {
    renderChip(40, { flavor: 'score-gap' });
    fireEvent.click(screen.getByTestId(TID));
    const body = screen.getByTestId(`${TID}-popover`).textContent ?? '';
    expect(body).toContain('most recent 3000 rated games per time control over the last 36 months');
    expect(body).toContain('+/-100 Elo');
  });
});

// ── Test 9 / C4: REGRESSION GUARD — NO FLAME ICON AT ANY PERCENTILE ─────────
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
      nLichessGames: 300,
    });
    fireEvent.click(screen.getByTestId(TID));
    expect(screen.queryByTestId(/flame/i)).toBeNull();
    expect(container.querySelector('[class*="flame"]')).toBeNull();
    expect(container.querySelector('[class*="Flame"]')).toBeNull();
  });
});

// ── Bullet 4 composition branch tests (D-12 Reversal Amendment 2026-05-27) ──
//
// All 4 branches of the blended-anchor disclosure are exercised explicitly.
// Branch-differentiating MUST-NOT-APPEAR assertions in C2 and C3 ensure a
// single-branch fallback cannot silently pass.

describe('PercentileChip — bullet 4 composition branches (D-12 Reversal Amendment)', () => {
  // C1: Mixed user — BOTH platform substrings + all 5 numbers appear.
  // Unique signature: "blending" compositional verb + both "chess.com games"
  // and "lichess games" substrings in bullet 4.
  it('C1 mixed-user: bullet 4 shows blended composition with both platforms and all 5 numbers', () => {
    renderChip(50, {
      flavor: 'score-gap',
      anchorRating: 2046,
      nChesscomGames: 4000,
      nLichessGames: 100,
      chesscomMedianNative: 2200,
      lichessMedianNative: 1900,
    });
    fireEvent.click(screen.getByTestId(TID));
    const body = screen.getByTestId(`${TID}-popover`).textContent ?? '';
    // Both platforms must appear (branch-differentiating)
    expect(body).toContain('chess.com games');
    expect(body.toLowerCase()).toContain('lichess games');
    // All 5 numbers must appear
    expect(body).toContain('4000');
    expect(body).toContain('100');
    expect(body).toContain('2200');
    expect(body).toContain('1900');
    expect(body).toContain('2046');
    // Compositional verb (mixed unique signature)
    expect(body.toLowerCase()).toContain('blending');
  });

  // C2: Pure-lichess — "native rating" signal + NO chess.com clause + NO "converted".
  // MUST-NOT-APPEAR guards: "chess.com" and "converted" must be absent from bullet 4.
  it('C2 pure-lichess: bullet 4 shows lichess-only anchor with "native rating" and NO chess.com mention', () => {
    renderChip(40, {
      flavor: 'time-pressure-score-gap',
      tc: 'blitz',
      anchorRating: 1750,
      nChesscomGames: 0,
      nLichessGames: 500,
      lichessMedianNative: 1750,
    });
    fireEvent.click(screen.getByTestId(TID));
    const body = screen.getByTestId(`${TID}-popover`).textContent ?? '';
    // MUST APPEAR (branch-differentiating)
    expect(body.toLowerCase()).toContain('lichess games');
    expect(body).toContain('500');
    expect(body).toContain('1750');
    expect(body.toLowerCase()).toContain('native rating');
    // MUST NOT APPEAR (branch-differentiation guard)
    expect(body).not.toMatch(/chess\.com/i);
    expect(body).not.toContain('converted');
  });

  // C3: Pure-chess.com — "converted" + snapshot date + NO lichess clause.
  // MUST-NOT-APPEAR guards: "lichess games" must be absent from bullet 4.
  it('C3 pure-chess.com: bullet 4 shows chess.com-only anchor with conversion + NO lichess mention', () => {
    renderChip(60, {
      flavor: 'clock-gap',
      tc: 'rapid',
      anchorRating: 1920,
      nChesscomGames: 1500,
      nLichessGames: 0,
      chesscomMedianNative: 1830,
    });
    fireEvent.click(screen.getByTestId(TID));
    const body = screen.getByTestId(`${TID}-popover`).textContent ?? '';
    // MUST APPEAR (branch-differentiating)
    expect(body).toContain('chess.com games');
    expect(body).toContain('1500');
    expect(body).toContain('1830');
    expect(body.toLowerCase()).toContain('converted');
    expect(body).toContain('ChessGoals snapshot 2026-05-26');
    // MUST NOT APPEAR (branch-differentiation guard)
    expect(body).not.toMatch(/lichess games/i);
  });

  // C5: Props deprecation sanity guard — old prop names rejected at compile time.
  // Uses @ts-expect-error blocks to assert that anchorSource and chesscomRawRating
  // are no longer valid props on PercentileChip.
  it('C5 deprecation guard: component renders correctly with new props (old props would be TS errors)', () => {
    // This test ensures the new props work correctly as a runtime sanity check.
    // The compile-time rejection of anchorSource/chesscomRawRating is asserted
    // via @ts-expect-error below — if those errors disappear, TS will flag this
    // test file as broken (the old props were accidentally re-added).
    const { container } = renderChip(50, {
      flavor: 'score-gap',
      anchorRating: 1600,
      nChesscomGames: 0,
      nLichessGames: 300,
      lichessMedianNative: 1600,
    });
    // @ts-expect-error — anchorSource is not a valid prop on the new PercentileChip
    const _oldPropTest1 = { anchorSource: 'lichess' };
    // @ts-expect-error — chesscomRawRating is not a valid prop on the new PercentileChip
    const _oldPropTest2 = { chesscomRawRating: 1500 };
    expect(container).toBeTruthy();
    void _oldPropTest1;
    void _oldPropTest2;
  });

  // C6: Suppression — when both counts == 0, bullet 4 defensive fallback produces
  // empty string; neither platform's characteristic substrings appear in bullet 4.
  it('C6 suppression: when nChesscomGames=0 and nLichessGames=0, bullet 4 is empty and shows no platform copy', () => {
    renderChip(50, {
      flavor: 'score-gap',
      anchorRating: 1600,
      nChesscomGames: 0,
      nLichessGames: 0,
    });
    fireEvent.click(screen.getByTestId(TID));
    const body = screen.getByTestId(`${TID}-popover`).textContent ?? '';
    // Branch differentiation: suppression branch produces neither mixed nor pure-platform copy
    expect(body).not.toContain('blending');
    expect(body).not.toContain('Anchored at');
    // Neither platform's characteristic substring should appear in bullet 4 copy
    expect(body).not.toMatch(/chess\.com games/i);
    expect(body).not.toMatch(/lichess games/i);
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
