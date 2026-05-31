// @vitest-environment jsdom
/**
 * Phase 99 Plan 01 Wave 0 — EndgameMetricsByTcCard rate-chip test scaffold.
 *
 * Pins four chip behaviors required by Phase 99:
 *   1. RENDER (SC-1): rate chip renders when rate_percentile != null AND anchorRating provided.
 *   2. SUPPRESS-on-null-percentile (SC-1): no chip when rate_percentile == null.
 *   3. SUPPRESS-on-null-anchor (SC-1): no chip when anchorRating undefined, even if percentile set.
 *   4. TC-SCOPED TOOLTIP + metric noun (SC-4 / D-08): chip aria-label names the TC and rate noun.
 *   5. COEXISTENCE (D-01): gap chip AND rate chip both render when both percentile sources present.
 *
 * INTENDED RED (tests 1, 4, 5): the rate chip is not wired until Plan 04. The render
 * assertions fail until then. Tests 2 and 3 (suppression-on-null) may already pass
 * because null rate_percentile → the chip gate never fires → no chip in DOM.
 *
 * PerTcBucketStats fixture casts: the rate_percentile fields are added to the
 * backend schema in Plan 03 and the TS type in Plan 04. Until then, fixture objects
 * use `as PerTcBucketStats` to silence the unknown-field TS error. The cast is
 * intentional and documents the RED state.
 *
 * EndgameMetricsByTcCard is an AccordionItem; tests wrap it in an Accordion with
 * defaultValue equal to the card's TC so the content is open on mount.
 */

import { afterEach, describe, it, expect } from 'vitest';
import { render, screen, cleanup } from '@testing-library/react';

import { Accordion } from '@/components/ui/accordion';
import { EndgameMetricsByTcCard } from '@/components/charts/EndgameMetricsByTcCard';
import type { EndgameMetricsTcCard, PerTcBucketStats, RatingAnchorOut } from '@/types/endgames';

afterEach(() => {
  cleanup();
});

// ---------------------------------------------------------------------------
// Fixture builders
// ---------------------------------------------------------------------------

/** Minimal PerTcBucketStats for a bucket with enough games to render. */
function makeBlock(overrides: Partial<PerTcBucketStats> = {}): PerTcBucketStats {
  return {
    games: 40,
    win_pct: 60,
    draw_pct: 10,
    loss_pct: 30,
    rate: 0.6,
    score_gap_mean: 0.05,
    score_gap_n: 38,
    score_gap_p_value: 0.02,
    score_gap_ci_low: 0.01,
    score_gap_ci_high: 0.09,
    percentile: null,
    ...overrides,
  } as PerTcBucketStats;
}

/** Minimal EndgameMetricsTcCard for blitz with one bucket having percentile data. */
function makeCard(overrides: {
  conversionOverrides?: Partial<PerTcBucketStats>;
  parityOverrides?: Partial<PerTcBucketStats>;
  recoveryOverrides?: Partial<PerTcBucketStats>;
} = {}): EndgameMetricsTcCard {
  return {
    tc: 'blitz',
    total: 120,
    conversion: makeBlock(overrides.conversionOverrides),
    parity: makeBlock({ games: 40, win_pct: 30, draw_pct: 40, loss_pct: 30, rate: 0.5, ...overrides.parityOverrides }),
    recovery: makeBlock({ games: 40, win_pct: 20, draw_pct: 20, loss_pct: 60, rate: 0.4, ...overrides.recoveryOverrides }),
  };
}

/** RatingAnchorOut for blitz. */
const BLITZ_ANCHOR: RatingAnchorOut = {
  anchor_rating: 1450,
  n_games: 40,
  snapshot_date: '2026-05-01',
};

/** Render helper: wraps the card in an Accordion with defaultValue=tc so the
 *  AccordionContent is open on initial render (mirrors EndgameMetricsByTcSection). */
function renderCard(
  card: EndgameMetricsTcCard,
  ratingAnchor?: RatingAnchorOut,
): ReturnType<typeof render> {
  return render(
    <Accordion type="single" defaultValue={card.tc}>
      <EndgameMetricsByTcCard card={card} ratingAnchor={ratingAnchor} />
    </Accordion>,
  );
}

// ---------------------------------------------------------------------------
// Test 1 — RENDER: rate chip appears when rate_percentile != null + anchor provided.
//
// INTENDED RED until Plan 04 wires the chip in MetricBlock.
// ---------------------------------------------------------------------------

describe('EndgameMetricsByTcCard — rate chip RENDER', () => {
  it('renders rate-percentile-chip for conversion bucket when rate_percentile set and anchor provided', () => {
    const card = makeCard({
      conversionOverrides: {
        // rate_percentile field added by Plan 03/04; cast until TS type is widened
        ...({ rate_percentile: 72, rate_percentile_n_games: 35, rate_percentile_value: 0.62 } as Partial<PerTcBucketStats>),
      },
    });
    renderCard(card, BLITZ_ANCHOR);

    // The chip testId pattern is `metrics-tc-${tc}-${bucket}-rate-percentile-chip`
    // (Plan 99 PATTERNS.md §EndgameMetricsByTcCard.tsx — testId={`${testId}-rate-percentile-chip`})
    const chip = screen.queryByTestId('metrics-tc-blitz-conversion-rate-percentile-chip');
    expect(chip).not.toBeNull(); // RED until Plan 04 wires the chip
  });
});

// ---------------------------------------------------------------------------
// Test 2 — SUPPRESS-on-null-percentile: no chip when rate_percentile == null.
//
// This test may already pass (null → chip gate short-circuits → no render).
// ---------------------------------------------------------------------------

describe('EndgameMetricsByTcCard — rate chip SUPPRESS when rate_percentile null', () => {
  it('does NOT render rate-percentile-chip when rate_percentile is null', () => {
    const card = makeCard({
      conversionOverrides: {
        percentile: 65,  // gap chip data present — confirms the card renders
        ...({ rate_percentile: null } as Partial<PerTcBucketStats>),
      },
    });
    renderCard(card, BLITZ_ANCHOR);

    const chip = screen.queryByTestId('metrics-tc-blitz-conversion-rate-percentile-chip');
    expect(chip).toBeNull(); // chip must be absent when rate_percentile is null
  });
});

// ---------------------------------------------------------------------------
// Test 3 — SUPPRESS-on-null-anchor: no chip when anchorRating is undefined.
//
// This test may already pass for the same reason as Test 2.
// ---------------------------------------------------------------------------

describe('EndgameMetricsByTcCard — rate chip SUPPRESS when anchorRating absent', () => {
  it('does NOT render rate-percentile-chip when anchorRating is undefined', () => {
    const card = makeCard({
      conversionOverrides: {
        ...({ rate_percentile: 72, rate_percentile_n_games: 35, rate_percentile_value: 0.62 } as Partial<PerTcBucketStats>),
      },
    });
    // No ratingAnchor passed → anchorRating === undefined
    renderCard(card, undefined);

    const chip = screen.queryByTestId('metrics-tc-blitz-conversion-rate-percentile-chip');
    expect(chip).toBeNull(); // chip must be absent without an anchor (tooltip would be broken)
  });
});

// ---------------------------------------------------------------------------
// Test 4 — TC-SCOPED TOOLTIP + metric noun: chip aria-label names tc + rate noun.
//
// INTENDED RED until Plan 04 wires the chip.
// The aria-label pattern from PercentileChip.tsx:
//   `${metricLabel} percentile: p${ariaRounded}${tcFragment}, ${directionWord} of cohort`
//   e.g. "Conversion Rate percentile: p72 in blitz, top of cohort"
// ---------------------------------------------------------------------------

describe('EndgameMetricsByTcCard — rate chip TC-SCOPED tooltip', () => {
  it('conversion rate chip aria-label contains "Conversion Rate" and the tc "blitz"', () => {
    const card = makeCard({
      conversionOverrides: {
        ...({ rate_percentile: 72, rate_percentile_n_games: 35, rate_percentile_value: 0.62 } as Partial<PerTcBucketStats>),
      },
    });
    renderCard(card, BLITZ_ANCHOR);

    const chip = screen.queryByTestId('metrics-tc-blitz-conversion-rate-percentile-chip');
    expect(chip).not.toBeNull(); // RED until Plan 04
    if (chip !== null) {
      const ariaLabel = chip.getAttribute('aria-label') ?? '';
      expect(ariaLabel).toContain('Conversion Rate');
      expect(ariaLabel).toContain('blitz');
    }
  });

  it('parity rate chip aria-label contains "Parity Rate" and the tc "blitz"', () => {
    const card = makeCard({
      parityOverrides: {
        ...({ rate_percentile: 55, rate_percentile_n_games: 30, rate_percentile_value: 0.50 } as Partial<PerTcBucketStats>),
      },
    });
    renderCard(card, BLITZ_ANCHOR);

    const chip = screen.queryByTestId('metrics-tc-blitz-parity-rate-percentile-chip');
    expect(chip).not.toBeNull(); // RED until Plan 04
    if (chip !== null) {
      const ariaLabel = chip.getAttribute('aria-label') ?? '';
      expect(ariaLabel).toContain('Parity Rate');
      expect(ariaLabel).toContain('blitz');
    }
  });

  it('recovery rate chip aria-label contains "Recovery Rate" and the tc "blitz"', () => {
    const card = makeCard({
      recoveryOverrides: {
        ...({ rate_percentile: 40, rate_percentile_n_games: 28, rate_percentile_value: 0.38 } as Partial<PerTcBucketStats>),
      },
    });
    renderCard(card, BLITZ_ANCHOR);

    const chip = screen.queryByTestId('metrics-tc-blitz-recovery-rate-percentile-chip');
    expect(chip).not.toBeNull(); // RED until Plan 04
    if (chip !== null) {
      const ariaLabel = chip.getAttribute('aria-label') ?? '';
      expect(ariaLabel).toContain('Recovery Rate');
      expect(ariaLabel).toContain('blitz');
    }
  });
});

// ---------------------------------------------------------------------------
// Test 5 — COEXISTENCE (D-01): both gap chip and rate chip render for same block.
//
// INTENDED RED until Plan 04 wires the rate chip.
// The gap chip is `${testId}-percentile-chip`; the rate chip is `${testId}-rate-percentile-chip`.
// Both must be present simultaneously — the rate chip does NOT replace the gap chip.
// ---------------------------------------------------------------------------

describe('EndgameMetricsByTcCard — COEXISTENCE of gap chip and rate chip', () => {
  it('renders BOTH the gap percentile chip and the rate percentile chip on the same conversion block', () => {
    const card = makeCard({
      conversionOverrides: {
        percentile: 72,           // gap chip
        percentile_n_games: 50,
        percentile_value: 0.04,
        ...({ rate_percentile: 55, rate_percentile_n_games: 35, rate_percentile_value: 0.62 } as Partial<PerTcBucketStats>),
      },
    });
    renderCard(card, BLITZ_ANCHOR);

    // Gap chip (existing, wired since Phase 97)
    const gapChip = screen.queryByTestId('metrics-tc-blitz-conversion-percentile-chip');
    expect(gapChip).not.toBeNull(); // gap chip must still render (D-01 — not replaced)

    // Rate chip (new, wired in Plan 04)
    const rateChip = screen.queryByTestId('metrics-tc-blitz-conversion-rate-percentile-chip');
    expect(rateChip).not.toBeNull(); // RED until Plan 04 — but both must coexist once wired
  });
});
