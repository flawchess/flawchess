// @vitest-environment jsdom
import { render, screen, cleanup } from '@testing-library/react';
import { describe, it, expect, afterEach } from 'vitest';

// Vitest 4 does not auto-cleanup RTL mounts — rendered DOM from a previous
// test bleeds into the next one's screen queries if we don't explicitly unmount.
afterEach(() => {
  cleanup();
});
import { MiniBulletChart } from '../MiniBulletChart';
import { ZONE_DANGER, ZONE_NEUTRAL, ZONE_SUCCESS } from '@/lib/theme';

describe('MiniBulletChart — backward compatibility', () => {
  it('renders unchanged when ciLow and ciHigh are omitted', () => {
    render(<MiniBulletChart value={0.5} domain={1.0} />);
    expect(screen.queryByTestId('mini-bullet-whisker')).toBeNull();
  });
});

describe('MiniBulletChart — CI whisker', () => {
  it('renders whisker line when both ciLow and ciHigh provided', () => {
    render(<MiniBulletChart value={0.3} ciLow={0.1} ciHigh={0.5} domain={1.0} />);
    expect(screen.queryByTestId('mini-bullet-whisker')).not.toBeNull();
  });

  it('whisker has both end caps when CI fits within domain', () => {
    render(<MiniBulletChart value={0} ciLow={-0.2} ciHigh={0.2} domain={1.0} />);
    expect(screen.queryByTestId('mini-bullet-whisker-cap-low')).not.toBeNull();
    expect(screen.queryByTestId('mini-bullet-whisker-cap-high')).not.toBeNull();
  });

  it('left cap suppressed when ciLow < -domain', () => {
    render(<MiniBulletChart value={0} ciLow={-1.5} ciHigh={0.2} domain={1.0} />);
    expect(screen.queryByTestId('mini-bullet-whisker-cap-low')).toBeNull();
    expect(screen.queryByTestId('mini-bullet-whisker-cap-high')).not.toBeNull();
  });

  it('right cap suppressed when ciHigh > +domain', () => {
    render(<MiniBulletChart value={0} ciLow={-0.2} ciHigh={1.5} domain={1.0} />);
    expect(screen.queryByTestId('mini-bullet-whisker-cap-high')).toBeNull();
    expect(screen.queryByTestId('mini-bullet-whisker-cap-low')).not.toBeNull();
  });

  it('whisker positions clamp to domain edges when CI exceeds domain', () => {
    const { getByTestId } = render(
      <MiniBulletChart value={0} ciLow={-2.0} ciHigh={2.0} domain={1.0} />,
    );
    const whisker = getByTestId('mini-bullet-whisker');
    // toPct(-domain) = ((-1 + 1) / 2) = 0%, toPct(+domain) = 100%
    // width = 100 - 0 = 100%
    expect(whisker.style.left).toBe('0%');
    expect(whisker.style.width).toBe('100%');
  });

  it('whisker only renders if BOTH props provided — only ciLow', () => {
    // @ts-expect-error — intentional partial prop test
    render(<MiniBulletChart value={0} ciLow={0.1} domain={1.0} />);
    expect(screen.queryByTestId('mini-bullet-whisker')).toBeNull();
  });

  it('whisker only renders if BOTH props provided — only ciHigh', () => {
    // @ts-expect-error — intentional partial prop test
    render(<MiniBulletChart value={0} ciHigh={0.1} domain={1.0} />);
    expect(screen.queryByTestId('mini-bullet-whisker')).toBeNull();
  });

  it('does not affect existing aria-label or value bar', () => {
    render(
      <MiniBulletChart
        value={0.3}
        ciLow={0.1}
        ciHigh={0.5}
        domain={1.0}
        ariaLabel="Test label"
      />,
    );
    // aria-label must survive the whisker addition
    expect(screen.queryByRole('img', { name: 'Test label' })).not.toBeNull();
    // value bar (the chart container) still present
    expect(screen.queryByTestId('mini-bullet-chart')).not.toBeNull();
  });
});

describe('MiniBulletChart — tickPawns prop (260504-rvh)', () => {
  function leftPercent(el: HTMLElement | null): number | null {
    if (!el) return null;
    const m = (el.getAttribute('style') ?? '').match(/left:\s*([\d.]+)%/);
    return m && m[1] ? parseFloat(m[1]) : null;
  }

  it('omitted tickPawns -> tick not rendered', () => {
    render(<MiniBulletChart value={0} domain={1.5} />);
    expect(screen.queryByTestId('mini-bullet-tick')).toBeNull();
  });

  it('tickPawns=0.25 (white baseline) with domain=1.5 renders tick at the expected percentage', () => {
    render(<MiniBulletChart value={0} tickPawns={0.25} domain={1.5} />);
    const tick = screen.queryByTestId('mini-bullet-tick');
    expect(tick).not.toBeNull();
    // axisMin = -1.5, axisMax = 1.5; toPct(0.25) = ((0.25 + 1.5) / 3) * 100 ≈ 58.333%
    expect(leftPercent(tick)).toBeCloseTo(58.333, 2);
  });

  it('tickPawns=-0.25 (black baseline) renders tick at expected percentage', () => {
    render(<MiniBulletChart value={0} tickPawns={-0.25} domain={1.5} />);
    const tick = screen.queryByTestId('mini-bullet-tick');
    expect(tick).not.toBeNull();
    // toPct(-0.25) = ((-0.25 + 1.5) / 3) * 100 ≈ 41.667%
    expect(leftPercent(tick)).toBeCloseTo(41.667, 2);
  });

  it('tickPawns outside the axis (above axisMax) -> tick not rendered', () => {
    render(<MiniBulletChart value={0} tickPawns={2.0} domain={1.5} />);
    expect(screen.queryByTestId('mini-bullet-tick')).toBeNull();
  });

  it('tickPawns outside the axis (below axisMin) -> tick not rendered', () => {
    render(<MiniBulletChart value={0} tickPawns={-2.0} domain={1.5} />);
    expect(screen.queryByTestId('mini-bullet-tick')).toBeNull();
  });

  it('positive tickPawns (white opening) renders the dashed line in the theme default tone', () => {
    render(<MiniBulletChart value={0} tickPawns={0.25} domain={1.5} />);
    const tick = screen.queryByTestId('mini-bullet-tick');
    expect(tick).not.toBeNull();
    // jsdom 29 changed shorthand CSS serialization: getAttribute('style') no
    // longer includes 'currentcolor' for border-left shorthand. Check the
    // individual borderLeftColor style property instead.
    const borderColor = (tick as HTMLElement | null)?.style.borderLeftColor ?? '';
    expect(borderColor).toBe('currentcolor');
  });

  it('negative tickPawns (black opening) renders the dashed line in black', () => {
    render(<MiniBulletChart value={0} tickPawns={-0.25} domain={1.5} />);
    const tick = screen.queryByTestId('mini-bullet-tick');
    expect(tick).not.toBeNull();
    const borderColor = (tick as HTMLElement | null)?.style.borderLeftColor ?? '';
    expect(borderColor).not.toBe('currentcolor');
    // jsdom normalises #000 to rgb(0, 0, 0) in style properties
    expect(['#000000', '#000', 'rgb(0, 0, 0)']).toContain(borderColor);
  });
});

describe('MiniBulletChart — barColor prop (260507-t4r)', () => {
  /**
   * The `barColor` prop controls the fill color of the value bar.
   * 'zone' (default): fill uses the zone color (danger/neutral/success).
   * 'neutral': fill uses BULLET_BAR_NEUTRAL — a light grey, zone-agnostic.
   *
   * Zone band backgrounds and CI whiskers are unaffected by barColor.
   * Endgame consumers omit barColor and therefore keep the zone-colored bar.
   */

  function getValueBar(container: Element): HTMLElement | null {
    return container.querySelector('[data-testid="mini-bullet-value-bar"]') as HTMLElement | null;
  }

  it('Test 1a: no barColor prop — value bar uses zone color (danger zone)', () => {
    // value=0.2 with center=0.5, neutralMin=-0.05, neutralMax=0.05 falls into danger zone
    const { container } = render(
      <MiniBulletChart
        value={0.2}
        center={0.5}
        neutralMin={-0.05}
        neutralMax={0.05}
        domain={0.5}
      />,
    );
    const bar = getValueBar(container);
    expect(bar).not.toBeNull();
    // zone-colored: must NOT be the neutral grey
    // BULLET_BAR_NEUTRAL is 'oklch(0.85 0 0)' — a grey; zone colors have chroma
    expect(bar?.style.backgroundColor).not.toContain('oklch(0.85 0 0)');
  });

  it('Test 1b: no barColor prop — value bar uses zone color (neutral zone)', () => {
    const { container } = render(
      <MiniBulletChart
        value={0.5}
        center={0.5}
        neutralMin={-0.05}
        neutralMax={0.05}
        domain={0.5}
      />,
    );
    const bar = getValueBar(container);
    expect(bar).not.toBeNull();
    expect(bar?.style.backgroundColor).not.toContain('oklch(0.85 0 0)');
  });

  it('Test 1c: no barColor prop — value bar uses zone color (success zone)', () => {
    const { container } = render(
      <MiniBulletChart
        value={0.8}
        center={0.5}
        neutralMin={-0.05}
        neutralMax={0.05}
        domain={0.5}
      />,
    );
    const bar = getValueBar(container);
    expect(bar).not.toBeNull();
    expect(bar?.style.backgroundColor).not.toContain('oklch(0.85 0 0)');
  });

  it('Test 2a: barColor="neutral" — value bar uses BULLET_BAR_NEUTRAL in danger zone', () => {
    const { container } = render(
      <MiniBulletChart
        value={0.2}
        center={0.5}
        neutralMin={-0.05}
        neutralMax={0.05}
        domain={0.5}
        barColor="neutral"
      />,
    );
    const bar = getValueBar(container);
    expect(bar).not.toBeNull();
    // Must be the neutral grey (BULLET_BAR_NEUTRAL = 'oklch(0.85 0 0)')
    expect(bar?.style.backgroundColor).toContain('oklch(0.85 0 0)');
  });

  it('Test 2b: barColor="neutral" — value bar uses BULLET_BAR_NEUTRAL in neutral zone', () => {
    const { container } = render(
      <MiniBulletChart
        value={0.5}
        center={0.5}
        neutralMin={-0.05}
        neutralMax={0.05}
        domain={0.5}
        barColor="neutral"
      />,
    );
    const bar = getValueBar(container);
    expect(bar).not.toBeNull();
    expect(bar?.style.backgroundColor).toContain('oklch(0.85 0 0)');
  });

  it('Test 2c: barColor="neutral" — value bar uses BULLET_BAR_NEUTRAL in success zone', () => {
    const { container } = render(
      <MiniBulletChart
        value={0.8}
        center={0.5}
        neutralMin={-0.05}
        neutralMax={0.05}
        domain={0.5}
        barColor="neutral"
      />,
    );
    const bar = getValueBar(container);
    expect(bar).not.toBeNull();
    expect(bar?.style.backgroundColor).toContain('oklch(0.85 0 0)');
  });

  it('Test 3: barColor="zone" is functionally identical to omitting the prop', () => {
    // Both with zone color: value=0.7, center=0.5, neutralMax=0.55 -> success zone (ZONE_SUCCESS)
    // We verify barColor="zone" does NOT produce the neutral grey.
    const { container } = render(
      <MiniBulletChart value={0.7} center={0.5} neutralMin={-0.05} neutralMax={0.05} domain={0.5} barColor="zone" />,
    );
    const bar = getValueBar(container);
    expect(bar).not.toBeNull();
    // barColor="zone" must not produce the neutral grey; it must produce a zone color
    expect(bar?.style.backgroundColor).not.toContain('oklch(0.85 0 0)');
  });

  it('Test 4: barColor="neutral" does not affect zone band backgrounds', () => {
    // Zone bands are the three background divs — they always use zone colors
    // regardless of barColor. We verify the chart container itself still renders.
    const { container } = render(
      <MiniBulletChart
        value={0.5}
        center={0.5}
        neutralMin={-0.05}
        neutralMax={0.05}
        domain={0.5}
        barColor="neutral"
        ciLow={0.4}
        ciHigh={0.6}
      />,
    );
    // Whisker should still render
    const whisker = container.querySelector('[data-testid="mini-bullet-whisker"]');
    expect(whisker).not.toBeNull();
    // Chart root still renders
    const chart = container.querySelector('[data-testid="mini-bullet-chart"]');
    expect(chart).not.toBeNull();
  });

  it('Test 5: tickPawns reference line unaffected by barColor="neutral"', () => {
    const { container } = render(
      <MiniBulletChart
        value={0.5}
        center={0.5}
        neutralMin={-0.05}
        neutralMax={0.05}
        domain={0.5}
        tickPawns={0.45}
        barColor="neutral"
      />,
    );
    const tick = container.querySelector('[data-testid="mini-bullet-tick"]');
    expect(tick).not.toBeNull();
  });
});

describe('MiniBulletChart — center prop (260504-my2)', () => {
  function leftPercent(el: HTMLElement | null): number | null {
    if (!el) return null;
    const m = (el.getAttribute('style') ?? '').match(/left:\s*([\d.]+)%/);
    return m && m[1] ? parseFloat(m[1]) : null;
  }

  it('default center=0 places reference line at 50% (legacy zero-centered)', () => {
    const { container } = render(
      <MiniBulletChart value={0} domain={0.4} neutralMin={-0.10} neutralMax={0} />,
    );
    const refLine = container.querySelector(
      'div.absolute.top-0.bottom-0.w-px.bg-foreground\\/50',
    ) as HTMLElement | null;
    expect(leftPercent(refLine)).toBeCloseTo(50, 3);
  });

  it('with center=0.32 and value=0.32, marker bar sits at the reference-line position', () => {
    const { container } = render(
      <MiniBulletChart
        value={0.32}
        center={0.32}
        domain={1.5}
        neutralMin={-0.25}
        neutralMax={0.25}
      />,
    );
    // Reference line: vertical 1px stroke at centerPct.
    const refLine = container.querySelector(
      'div.absolute.top-0.bottom-0.w-px.bg-foreground\\/50',
    ) as HTMLElement | null;
    // Value bar: horizontal stroke; with value === center, width == 0 and left == centerPct.
    const valueBar = container.querySelector(
      'div.absolute.top-1\\/2',
    ) as HTMLElement | null;
    const refPct = leftPercent(refLine);
    const valuePct = leftPercent(valueBar);
    expect(refPct).not.toBeNull();
    expect(valuePct).not.toBeNull();
    expect(valuePct).toBeCloseTo(refPct as number, 3);
  });

  it('with non-zero center, reference line still sits at 50% (axis recenters)', () => {
    // Axis spans [center - domain, center + domain], so the reference line is
    // always at the visual middle regardless of center.
    const { container } = render(
      <MiniBulletChart
        value={0.315}
        center={0.315}
        domain={1.5}
        neutralMin={-0.25}
        neutralMax={0.25}
      />,
    );
    const refLine = container.querySelector(
      'div.absolute.top-0.bottom-0.w-px.bg-foreground\\/50',
    ) as HTMLElement | null;
    expect(leftPercent(refLine)).toBeCloseTo(50, 3);
  });
});

describe('MiniBulletChart — asymmetric neutral zone (260516-0ax)', () => {
  /**
   * Locks in that `neutralMin` and `neutralMax` are independent signed offsets
   * from `center`. Asymmetric tuples like (-0.11, 0.00) or (+0.01, +0.11) must
   * paint the colored band offset from the center tick — no symmetrization,
   * no averaging, no magnitude collapse along the path from props to render.
   *
   * Used by Section 2 ΔES Score Gap zones (per benchmarks-latest.md §3.4.4)
   * where Conversion sits below 0 and Recovery sits above 0.
   */

  // Width parsing helper — tolerates floating-point format drift across
  // platforms (e.g. '36.25%' vs '36.2500000000001%') while keeping the
  // expectations on the exact percentages computed in PLAN.md.
  function widthPct(el: Element | null): number | null {
    if (!el) return null;
    const s = (el as HTMLElement).style.width;
    if (!s) return null;
    const n = Number.parseFloat(s.replace('%', ''));
    return Number.isFinite(n) ? n : null;
  }

  // Browsers normalize numeric components in inline `style.backgroundColor`
  // (e.g. JSDOM rewrites '0.50' to '0.5'). Collapse all numbers to fixed
  // decimals on both sides so the comparison is invariant to that drift.
  function normalizeOklch(s: string | undefined): string {
    if (!s) return '';
    return s.replace(/[\d]+\.?[\d]*/g, (m) => Number.parseFloat(m).toString());
  }

  function zoneDivs(container: Element): readonly Element[] {
    const chart = container.querySelector('[data-testid="mini-bullet-chart"]');
    if (!chart) return [];
    // The zone band container is the first ".absolute.inset-0.flex" child of
    // the chart root (the three zone-color divs are its direct children).
    const zoneRow = chart.querySelector(':scope > div.absolute.inset-0.flex');
    if (!zoneRow) return [];
    return Array.from(zoneRow.children);
  }

  it('left-skewed band (-0.11, 0.00) — band sits entirely to the LEFT of center', () => {
    // axisMin=-0.40, axisMax=+0.40
    // toPct(-0.11) = ((-0.11 + 0.40) / 0.80) * 100 = 36.25%
    // toPct(0)     = ((0    + 0.40) / 0.80) * 100 = 50.00%
    // -> DANGER=36.25%, NEUTRAL=13.75%, SUCCESS=50%
    const { container } = render(
      <MiniBulletChart value={0} neutralMin={-0.11} neutralMax={0} center={0} domain={0.40} />,
    );
    const [danger, neutral, success] = zoneDivs(container);
    expect(widthPct(danger ?? null)).toBeCloseTo(36.25, 4);
    expect(widthPct(neutral ?? null)).toBeCloseTo(13.75, 4);
    expect(widthPct(success ?? null)).toBeCloseTo(50, 4);
  });

  it('right-skewed band (+0.01, +0.11) — band sits entirely to the RIGHT of center', () => {
    // toPct(0.01) = ((0.01 + 0.40) / 0.80) * 100 = 51.25%
    // toPct(0.11) = ((0.11 + 0.40) / 0.80) * 100 = 63.75%
    // -> DANGER=51.25%, NEUTRAL=12.5%, SUCCESS=36.25%
    const { container } = render(
      <MiniBulletChart value={0} neutralMin={0.01} neutralMax={0.11} center={0} domain={0.40} />,
    );
    const [danger, neutral, success] = zoneDivs(container);
    expect(widthPct(danger ?? null)).toBeCloseTo(51.25, 4);
    expect(widthPct(neutral ?? null)).toBeCloseTo(12.5, 4);
    expect(widthPct(success ?? null)).toBeCloseTo(36.25, 4);
  });

  it('symmetric band (-0.05, +0.05) — band centered on 0 (regression control)', () => {
    // toPct(-0.05) = ((-0.05 + 0.40) / 0.80) * 100 = 43.75%
    // toPct(+0.05) = ((+0.05 + 0.40) / 0.80) * 100 = 56.25%
    // -> DANGER=43.75%, NEUTRAL=12.5%, SUCCESS=43.75%
    const { container } = render(
      <MiniBulletChart value={0} neutralMin={-0.05} neutralMax={0.05} center={0} domain={0.40} />,
    );
    const [danger, neutral, success] = zoneDivs(container);
    expect(widthPct(danger ?? null)).toBeCloseTo(43.75, 4);
    expect(widthPct(neutral ?? null)).toBeCloseTo(12.5, 4);
    expect(widthPct(success ?? null)).toBeCloseTo(43.75, 4);
  });

  it('zone color follows asymmetric bounds (lo=-0.11, hi=0.00, center=0)', () => {
    // With (lo, hi) = (-0.11, 0.00) and center=0:
    //   absNeutralMin = -0.11, absNeutralMax = 0.00
    //   value < -0.11        -> DANGER
    //   -0.11 <= value < 0   -> NEUTRAL
    //   value >= 0           -> SUCCESS

    // value = -0.20 -> DANGER
    const { container: cDanger } = render(
      <MiniBulletChart value={-0.20} neutralMin={-0.11} neutralMax={0} center={0} domain={0.40} />,
    );
    const barDanger = cDanger.querySelector(
      '[data-testid="mini-bullet-value-bar"]',
    ) as HTMLElement | null;
    expect(barDanger).not.toBeNull();
    expect(normalizeOklch(barDanger?.style.backgroundColor)).toBe(normalizeOklch(ZONE_DANGER));

    cleanup();

    // value = -0.05 -> NEUTRAL (lies inside the off-center band)
    const { container: cNeutral } = render(
      <MiniBulletChart value={-0.05} neutralMin={-0.11} neutralMax={0} center={0} domain={0.40} />,
    );
    const barNeutral = cNeutral.querySelector(
      '[data-testid="mini-bullet-value-bar"]',
    ) as HTMLElement | null;
    expect(barNeutral).not.toBeNull();
    expect(normalizeOklch(barNeutral?.style.backgroundColor)).toBe(normalizeOklch(ZONE_NEUTRAL));

    cleanup();

    // value = +0.05 -> SUCCESS (above absNeutralMax = 0)
    const { container: cSuccess } = render(
      <MiniBulletChart value={0.05} neutralMin={-0.11} neutralMax={0} center={0} domain={0.40} />,
    );
    const barSuccess = cSuccess.querySelector(
      '[data-testid="mini-bullet-value-bar"]',
    ) as HTMLElement | null;
    expect(barSuccess).not.toBeNull();
    expect(normalizeOklch(barSuccess?.style.backgroundColor)).toBe(normalizeOklch(ZONE_SUCCESS));
  });
});
