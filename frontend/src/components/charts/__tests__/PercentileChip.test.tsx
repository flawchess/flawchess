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
import type { PerTcBreakdownOut } from '@/types/endgames';

const TID = 'test-pctl-chip';

type RenderOpts = {
  flavor?: PercentileChipFlavor;
  tc?: 'bullet' | 'blitz' | 'rapid' | 'classical';
  anchorRating?: number;
  metricLabel?: string;
  perTcBreakdown?: PerTcBreakdownOut[];
  nGames?: number | null;
  value?: number | null;
};

function renderChip(percentile: number, opts: RenderOpts = {}) {
  // 260529-l1i: anchorRating is optional. Per-TC chips (tc set) pass it for
  // bullet 1; aggregated chips omit it. Only pass it when explicitly provided.
  return render(
    <PercentileChip
      percentile={percentile}
      flavor={opts.flavor ?? 'score-gap'}
      tc={opts.tc}
      {...(opts.anchorRating !== undefined ? { anchorRating: opts.anchorRating } : {})}
      metricLabel={opts.metricLabel ?? 'Endgame Score Gap'}
      testId={TID}
      perTcBreakdown={opts.perTcBreakdown}
      nGames={opts.nGames}
      value={opts.value}
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
  // Test 7: per-TC bullet 1 — pct<=50 keeps the legacy "bottom X%" framing.
  // 260529-fast: the chip's value is woven into the sentence (percent-formatted),
  // not shown as a separate "Your value:" line in bullet 2.
  it('per-TC popover bullet 1 reads "Your recent {metric} {value} is in the bottom 23% of ~1600-rated players in bullet."', () => {
    renderChip(23, {
      flavor: 'time-pressure-score-gap',
      tc: 'bullet',
      anchorRating: 1600,
      metricLabel: 'Time-Pressure Score Gap',
      value: 0.04,
    });
    fireEvent.click(screen.getByTestId(TID));
    const body = screen.getByTestId(`${TID}-popover`).textContent ?? '';
    expect(body).toContain(
      'Your recent Time-Pressure Score Gap +4% is in the bottom 23% of ~1600-rated players in bullet.',
    );
    // The value no longer appears as a separate "Your value:" line.
    expect(body).not.toContain('Your value');
  });

  // 260529-fast: per-TC bullet 1 omits the value when the caller did not thread
  // `value` (legacy fixtures), falling back to the metric-label-only sentence.
  it('per-TC popover bullet 1 omits the value when `value` is not provided', () => {
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

  // Test 8: aggregated bullet 1 — pct<=50 keeps the legacy "bottom X%" framing.
  // 260529-l1i: aggregated bullet 1 drops the "~{anchor}-rated" number and
  // reads "similarly-rated players".
  it('aggregated popover bullet 1 reads "Your recent {metric} is in the bottom 23% of similarly-rated players, aggregated across the time controls you play."', () => {
    renderChip(23, {
      flavor: 'score-gap',
      metricLabel: 'Endgame Score Gap',
    });
    fireEvent.click(screen.getByTestId(TID));
    const body = screen.getByTestId(`${TID}-popover`).textContent ?? '';
    expect(body).toContain(
      'Your recent Endgame Score Gap is in the bottom 23% of similarly-rated players, aggregated across the time controls you play.',
    );
  });

  // Test 8b: pct>50 uses positive framing with the chip's percentile verbatim
  it('high-percentile bullet 1 echoes the chip percentile verbatim (pct=90 → "better than 90%")', () => {
    renderChip(90, {
      flavor: 'score-gap',
      metricLabel: 'Endgame Score Gap',
    });
    fireEvent.click(screen.getByTestId(TID));
    const body = screen.getByTestId(`${TID}-popover`).textContent ?? '';
    expect(body).toContain(
      'Your recent Endgame Score Gap is better than 90% of similarly-rated players, aggregated across the time controls you play.',
    );
  });

  // Test 8c: median boundary (pct=50) stays on the "bottom" side per the <= rule
  it('median percentile (pct=50) uses "in the bottom 50%" framing', () => {
    renderChip(50, {
      flavor: 'score-gap',
      metricLabel: 'Endgame Score Gap',
    });
    fireEvent.click(screen.getByTestId(TID));
    const body = screen.getByTestId(`${TID}-popover`).textContent ?? '';
    expect(body).toContain(
      'Your recent Endgame Score Gap is in the bottom 50% of similarly-rated players, aggregated across the time controls you play.',
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

  // Quick task 260527-q0b: bullet 2 rewrite. The previous prose ("most recent
  // 3000 rated games") is now a fallback only — the real surface shows
  // concrete per-TC n_games + value + percentile (aggregated chips) or a
  // single-line n_games + value (per-TC chips).

  // Per-TC chip bullet 2 — concrete n_games framing. 260529-fast: the value
  // moved to bullet 1 (percent-formatted); bullet 2 no longer carries it.
  it('per-TC bullet 2 renders "Based on <n> of your recent <tc> games" with the value in bullet 1', () => {
    renderChip(40, {
      flavor: 'time-pressure-score-gap',
      tc: 'bullet',
      anchorRating: 1600,
      metricLabel: 'Time Pressure Score Gap',
      nGames: 137,
      value: 0.04,
    });
    fireEvent.click(screen.getByTestId(TID));
    const body = screen.getByTestId(`${TID}-popover`).textContent ?? '';
    expect(body).toContain('Based on 137 of your recent bullet games');
    expect(body).toContain('over the last 36 months');
    expect(body).toContain('+/-100 Elo');
    // Value is in bullet 1 as a percent, not a separate "Your value:" line.
    expect(body).toContain('Your recent Time Pressure Score Gap +4% is');
    expect(body).not.toContain('Your value');
  });

  // Per-TC clock-gap chip formats the value as signed integer percent in bullet 1.
  it('per-TC clock-gap bullet 1 renders the value as signed integer percent', () => {
    renderChip(60, {
      flavor: 'clock-gap',
      tc: 'blitz',
      anchorRating: 1600,
      metricLabel: 'Clock Gap',
      nGames: 320,
      value: 0.05,
    });
    fireEvent.click(screen.getByTestId(TID));
    const body = screen.getByTestId(`${TID}-popover`).textContent ?? '';
    expect(body).toContain('Based on 320 of your recent blitz games');
    expect(body).toContain('Your recent Clock Gap +5% is');
    expect(body).not.toContain('Your value');
  });

  // Per-TC net-flag-rate chip also formats the value as signed integer percent.
  it('per-TC net-flag-rate bullet 1 renders the value as signed integer percent', () => {
    renderChip(70, {
      flavor: 'net-flag-rate',
      tc: 'rapid',
      anchorRating: 1600,
      metricLabel: 'Net Flag Rate',
      nGames: 210,
      value: -0.02,
    });
    fireEvent.click(screen.getByTestId(TID));
    const body = screen.getByTestId(`${TID}-popover`).textContent ?? '';
    expect(body).toContain('Based on 210 of your recent rapid games');
    expect(body).toContain('Your recent Net Flag Rate -2% is');
    expect(body).not.toContain('Your value');
  });

  // Per-TC fallback when caller has not threaded the new fields (legacy fixture).
  it('per-TC bullet 2 falls back to the legacy single-line copy when nGames/value are missing', () => {
    renderChip(40, { flavor: 'time-pressure-score-gap', tc: 'bullet' });
    fireEvent.click(screen.getByTestId(TID));
    const body = screen.getByTestId(`${TID}-popover`).textContent ?? '';
    expect(body).toContain('most recent 3000 rated games in bullet over the last 36 months');
    expect(body).toContain('+/-100 Elo');
  });

  // Aggregated bullet 2 — concrete per-TC list. Covers all 4 branches at once:
  //   (a) above-floor with percentile → full line with value + n_games + percentile.
  //   (b) above-floor with null percentile → DROP the line entirely.
  //   (c) below-floor with games > 0 → "insufficient games".
  //   (d) zero-games entries → omitted upstream (covered by C6 suppression).
  it('aggregated bullet 2 renders a per-TC list with all 4 branch semantics', () => {
    renderChip(50, {
      flavor: 'score-gap',
      metricLabel: 'Endgame Score Gap',
      perTcBreakdown: [
        { tc: 'bullet', value: 0.05, n_games: 137, percentile: 62.3, anchor: 1600 },
        { tc: 'blitz', value: -0.02, n_games: 410, percentile: 38.0, anchor: 1580 },
        { tc: 'rapid', value: null, n_games: 12, percentile: null, anchor: 1620 },
        // classical above floor (value != null) but percentile null → DROPPED.
        { tc: 'classical', value: 0.1, n_games: 200, percentile: null, anchor: 1650 },
      ],
    });
    fireEvent.click(screen.getByTestId(TID));
    const body = screen.getByTestId(`${TID}-popover`).textContent ?? '';
    expect(body).toContain('weighted average of Endgame Score Gap percentiles');
    expect(body).toContain('3000 games per time control');
    expect(body).toContain('+/-100 Elo');
    // Branch (a): above-floor with percentile → two-line row (anchor + stats).
    // 260529-l1i: the TC label now lives on the anchor line; the stats line no
    // longer carries a "{tc}: " prefix.
    expect(body).toContain('bullet — anchored at ~1600 Lichess Elo');
    expect(body).toContain('+5% over 137 games');
    expect(body).toContain('62 percentile');
    expect(body).toContain('blitz — anchored at ~1580 Lichess Elo');
    expect(body).toContain('-2% over 410 games');
    expect(body).toContain('38 percentile');
    // Branch (c): below-floor → "insufficient games" line (no anchor line).
    expect(body).toContain('rapid: insufficient games');
    expect(body).not.toContain('rapid — anchored at');
    // Branch (b): null-percentile-above-floor → line DROPPED. Guard against a
    // single-branch fallback silently passing by asserting "classical" is
    // absent from the per-TC list entirely.
    expect(body).not.toMatch(/classical:/);
    expect(body).not.toContain('classical — anchored at');
  });

  // Per-flavor coverage of the new bullet-2 framing across the 5 aggregated +
  // 3 per-TC flavors. Each row asserts the framing-specific signature so an
  // implementation that drops a flavor would fail loudly.
  it.each([
    ['score-gap', 'Endgame Score Gap'],
    ['achievable', 'Achievable Score Gap'],
    ['parity', 'Parity Score Gap'],
    ['conversion', 'Conversion Score Gap'],
    ['recovery', 'Recovery Score Gap'],
  ] as Array<[PercentileChipFlavor, string]>)(
    'aggregated bullet 2 renders the per-TC list for flavor=%s',
    (flavor, label) => {
      renderChip(50, {
        flavor,
        metricLabel: label,
        perTcBreakdown: [
          { tc: 'blitz', value: 0.03, n_games: 200, percentile: 55.0, anchor: 1580 },
        ],
      });
      fireEvent.click(screen.getByTestId(TID));
      const body = screen.getByTestId(`${TID}-popover`).textContent ?? '';
      expect(body).toContain(`weighted average of ${label} percentiles`);
      // 260529-l1i: two-line row — anchor label line + stats line.
      expect(body).toContain('blitz — anchored at ~1580 Lichess Elo');
      expect(body).toContain('+3% over 200 games');
      expect(body).toContain('55 percentile');
    },
  );

  it.each([
    ['time-pressure-score-gap', 'Time Pressure Score Gap', 'bullet' as const],
    ['clock-gap', 'Clock Gap', 'blitz' as const],
    ['net-flag-rate', 'Net Flag Rate', 'rapid' as const],
  ] as Array<[PercentileChipFlavor, string, 'bullet' | 'blitz' | 'rapid' | 'classical']>)(
    'per-TC bullet 2 renders the simplified single-line framing for flavor=%s',
    (flavor, label, tc) => {
      renderChip(50, {
        flavor,
        tc,
        metricLabel: label,
        nGames: 150,
        value: 0.04,
      });
      fireEvent.click(screen.getByTestId(TID));
      const body = screen.getByTestId(`${TID}-popover`).textContent ?? '';
      expect(body).toContain(`Based on 150 of your recent ${tc} games`);
      expect(body).toContain('over the last 36 months');
    },
  );

  // Aggregated fallback: when caller passes no perTcBreakdown (legacy fixture)
  // bullet 2 keeps the old single-line copy so older callers don't break.
  it('aggregated bullet 2 falls back to the legacy single-line copy when perTcBreakdown is missing', () => {
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
    });
    fireEvent.click(screen.getByTestId(TID));
    expect(screen.queryByTestId(/flame/i)).toBeNull();
    expect(container.querySelector('[class*="flame"]')).toBeNull();
    expect(container.querySelector('[class*="Flame"]')).toBeNull();
  });
});

// ── 260529-l1i: bullet 4 removed; per-TC anchor rows added ──────────────────
//
// The standalone bullet-4 platform-blend anchor paragraph was removed. The
// rating-matching method now lives inline on each per-TC breakdown row of the
// aggregated chip tooltip ("anchored at ~X Lichess Elo"). These tests assert
// the removal and the new per-row anchor behavior.

describe('PercentileChip — per-TC anchor rows (260529-l1i)', () => {
  // No platform-blend prose anywhere, for any chip input.
  it('renders NO platform-blend prose (no "blending", "Anchored at", "converted") for any chip', () => {
    // Aggregated chip with per-TC anchors.
    renderChip(50, {
      flavor: 'score-gap',
      metricLabel: 'Endgame Score Gap',
      perTcBreakdown: [{ tc: 'blitz', value: 0.03, n_games: 200, percentile: 55.0, anchor: 1580 }],
    });
    fireEvent.click(screen.getByTestId(TID));
    const aggBody = screen.getByTestId(`${TID}-popover`).textContent ?? '';
    expect(aggBody).not.toContain('blending');
    expect(aggBody).not.toContain('Anchored at');
    expect(aggBody).not.toContain('converted');

    cleanup();

    // Per-TC chip.
    renderChip(60, {
      flavor: 'clock-gap',
      tc: 'rapid',
      anchorRating: 1920,
      nGames: 150,
      value: 0.04,
    });
    fireEvent.click(screen.getByTestId(TID));
    const perTcBody = screen.getByTestId(`${TID}-popover`).textContent ?? '';
    expect(perTcBody).not.toContain('blending');
    expect(perTcBody).not.toContain('Anchored at');
    expect(perTcBody).not.toContain('converted');
  });

  // Above-floor entry with anchor → two-line row with the locked anchor label.
  it('above-floor per-TC row renders "anchored at ~X Lichess Elo" + stats line + anchor data-testid', () => {
    renderChip(50, {
      flavor: 'score-gap',
      metricLabel: 'Endgame Score Gap',
      perTcBreakdown: [{ tc: 'blitz', value: 0.04, n_games: 410, percentile: 55.0, anchor: 1525 }],
    });
    fireEvent.click(screen.getByTestId(TID));
    const body = screen.getByTestId(`${TID}-popover`).textContent ?? '';
    expect(body).toContain('anchored at ~1525 Lichess Elo');
    expect(body).toContain('over');
    expect(body).toContain('percentile');
    // The per-row anchor data-testid must exist for the above-floor entry.
    expect(screen.getByTestId('percentile-chip-anchor-blitz')).toBeTruthy();
  });

  // Below-floor entry (value null) → single "insufficient games" line, no anchor.
  it('below-floor per-TC row shows "insufficient games" and NO anchor line', () => {
    renderChip(50, {
      flavor: 'score-gap',
      metricLabel: 'Endgame Score Gap',
      perTcBreakdown: [{ tc: 'rapid', value: null, n_games: 8, percentile: null, anchor: 1620 }],
    });
    fireEvent.click(screen.getByTestId(TID));
    const body = screen.getByTestId(`${TID}-popover`).textContent ?? '';
    expect(body).toContain('rapid: insufficient games');
    expect(screen.queryByTestId('percentile-chip-anchor-rapid')).toBeNull();
  });

  // Defensive: renderable entry with anchor === null → stats line renders,
  // anchor label line absent.
  it('renderable per-TC row with anchor=null renders the stats line and NO anchor line', () => {
    renderChip(50, {
      flavor: 'score-gap',
      metricLabel: 'Endgame Score Gap',
      perTcBreakdown: [{ tc: 'blitz', value: 0.02, n_games: 300, percentile: 48.0, anchor: null }],
    });
    fireEvent.click(screen.getByTestId(TID));
    const body = screen.getByTestId(`${TID}-popover`).textContent ?? '';
    expect(body).toContain('over 300 games');
    expect(body).not.toContain('anchored at');
    expect(screen.queryByTestId('percentile-chip-anchor-blitz')).toBeNull();
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
