// @vitest-environment jsdom
/**
 * Quick task 260514-i3l: shared tooltip body for the 6 tooltips in the
 * "Endgame Overall Performance" section.
 *
 * Covers:
 *   - score-vocab headlines (strength / weakness / difference / inconclusive)
 *   - eval-vocab headlines (advantage / disadvantage / deviation / inconclusive)
 *   - percent and pawns value-line formats (signed for gap baseline=0, unsigned
 *     for score-vs-50% baseline=0.5; no baseline-distance for pawns)
 *   - pValue === null branch (no "p = ..." segment, no "null"/"NaN" leak)
 *   - lastPlayedAt branch (renders "Last played" line when provided)
 *   - D-10 forbidden-framing contract (no underperformance / fall short /
 *     below your potential) preserved from AchievableScorePopover.test.tsx
 */

import { afterEach, beforeAll, describe, expect, it, vi } from 'vitest';
import { cleanup, render } from '@testing-library/react';

import { MetricStatTooltip } from '../MetricStatTooltip';

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

// Score-vocab base: percent unit, baseline 0.5, neutral 0.45/0.55.
const scoreBase = {
  name: 'Endgame Score',
  explanation: 'Test explanation.',
  unit: 'percent' as const,
  vocabulary: 'score' as const,
  baseline: 0.5,
  baselineLabel: '50%',
  neutralLower: 0.45,
  neutralUpper: 0.55,
  gameCount: 50,
  pValue: 0.001,
  methodology: 'Methodology footer.',
};

// Eval-vocab base: pawns unit, baseline 0, neutral -0.75/+0.75 (endgame entry eval zones).
const evalBase = {
  name: 'Endgame Entry Eval',
  explanation: 'Test eval explanation.',
  unit: 'pawns' as const,
  vocabulary: 'eval' as const,
  baseline: 0,
  baselineLabel: '0 pawns',
  neutralLower: -0.75,
  neutralUpper: 0.75,
  gameCount: 40,
  pValue: 0.01,
  methodology: 'Methodology footer.',
};

// Achievable-Score explanation prop used by the D-10 contract test. Same prose
// the Task 2 call site will pass via MetricStatPopover. Inline copy is OK
// (the plan body explicitly allows it).
const ACHIEVABLE_SCORE_EXPLANATION =
  'What a 2300+ rated player would score from your endgame-entry positions against a peer of similar rating, via the Lichess expected-score formula. Compare against your Endgame Score.';

describe('MetricStatTooltip — score-vocab headlines', () => {
  it("renders 'Likely a real strength.' for high-confidence value above neutral", () => {
    const { container } = render(
      <MetricStatTooltip {...scoreBase} level="high" value={0.62} />,
    );
    expect(container.textContent).toMatch(/Likely a real strength\./);
  });

  it("renders 'Likely a real weakness.' for high-confidence value below neutral", () => {
    const { container } = render(
      <MetricStatTooltip {...scoreBase} level="high" value={0.4} />,
    );
    expect(container.textContent).toMatch(/Likely a real weakness\./);
  });

  it("renders 'Possibly a real difference from the 50% baseline.' for medium-confidence near baseline", () => {
    const { container } = render(
      <MetricStatTooltip {...scoreBase} level="medium" value={0.51} />,
    );
    expect(container.textContent).toMatch(
      /Possibly a real difference from the 50% baseline\./,
    );
  });

  it("renders 'Inconclusive.' for low confidence regardless of value", () => {
    const { container } = render(
      <MetricStatTooltip {...scoreBase} level="low" value={0.62} />,
    );
    expect(container.textContent).toMatch(/Inconclusive\./);
    expect(container.textContent).not.toMatch(/Likely a real /);
  });

  it("qualifies strength/weakness with 'relative' when relative=true", () => {
    const { container: weak } = render(
      <MetricStatTooltip {...scoreBase} level="high" value={0.4} relative />,
    );
    expect(weak.textContent).toMatch(/Likely a real relative weakness\./);
    cleanup();
    const { container: strong } = render(
      <MetricStatTooltip {...scoreBase} level="high" value={0.62} relative />,
    );
    expect(strong.textContent).toMatch(/Likely a real relative strength\./);
  });
});

describe('MetricStatTooltip — eval-vocab headlines', () => {
  it("renders 'Likely a real advantage.' for high-confidence positive eval", () => {
    const { container } = render(
      <MetricStatTooltip {...evalBase} level="high" value={1.2} />,
    );
    expect(container.textContent).toMatch(/Likely a real advantage\./);
  });

  it("renders 'Likely a real disadvantage.' for high-confidence negative eval", () => {
    const { container } = render(
      <MetricStatTooltip {...evalBase} level="high" value={-1.0} />,
    );
    expect(container.textContent).toMatch(/Likely a real disadvantage\./);
  });

  it("renders 'Possibly a real deviation from 0 pawns.' for medium-confidence near zero", () => {
    const { container } = render(
      <MetricStatTooltip {...evalBase} level="medium" value={0.1} />,
    );
    expect(container.textContent).toMatch(
      /Possibly a real deviation from 0 pawns\./,
    );
  });

  it("renders 'Inconclusive.' for low confidence eval regardless of value", () => {
    const { container } = render(
      <MetricStatTooltip {...evalBase} level="low" value={1.0} />,
    );
    expect(container.textContent).toMatch(/Inconclusive\./);
  });
});

describe('MetricStatTooltip — percent value line', () => {
  it('renders unsigned percent and signed baseline distance for baseline=0.5 (score-vs-50%)', () => {
    const { container } = render(
      <MetricStatTooltip {...scoreBase} level="high" value={0.62} />,
    );
    expect(container.textContent).toMatch(/62\.0%/);
    // No leading "+" for score-vs-50% (only signed when baseline === 0)
    expect(container.textContent).not.toMatch(/\+62\.0%/);
    expect(container.textContent).toMatch(/12\.0% above the 50% baseline/);
  });

  it('renders signed positive percent for gap metrics (baseline=0)', () => {
    const { container } = render(
      <MetricStatTooltip
        {...scoreBase}
        baseline={0}
        baselineLabel="0%"
        neutralLower={-0.1}
        neutralUpper={0.1}
        level="high"
        value={0.07}
      />,
    );
    expect(container.textContent).toMatch(/\+7\.0%/);
    expect(container.textContent).toMatch(/7\.0% above the 0% baseline/);
  });

  it('renders unsigned negative percent for gap metrics (baseline=0)', () => {
    const { container } = render(
      <MetricStatTooltip
        {...scoreBase}
        baseline={0}
        baselineLabel="0%"
        neutralLower={-0.1}
        neutralUpper={0.1}
        level="high"
        value={-0.05}
      />,
    );
    expect(container.textContent).toMatch(/-5\.0%/);
    expect(container.textContent).toMatch(/5\.0% below the 0% baseline/);
  });

  it('renders "at the X% baseline." when diff rounds to 0.0%', () => {
    const { container } = render(
      <MetricStatTooltip
        {...scoreBase}
        baseline={0}
        baselineLabel="0%"
        neutralLower={-0.1}
        neutralUpper={0.1}
        level="high"
        value={0}
      />,
    );
    expect(container.textContent).toMatch(/at the 0% baseline\./);
    expect(container.textContent).not.toMatch(/above the/);
    expect(container.textContent).not.toMatch(/below the/);
  });
});

describe('MetricStatTooltip — pawns value line', () => {
  it('renders signed positive pawns with no baseline-distance text', () => {
    const { container } = render(
      <MetricStatTooltip {...evalBase} level="medium" value={0.42} />,
    );
    expect(container.textContent).toMatch(/\+0\.42 pawns over 40 games\./);
    expect(container.textContent).not.toMatch(/above the/);
    expect(container.textContent).not.toMatch(/below the/);
  });

  it('renders signed negative pawns with no baseline-distance text', () => {
    const { container } = render(
      <MetricStatTooltip {...evalBase} level="high" value={-1.0} />,
    );
    expect(container.textContent).toMatch(/-1\.00 pawns over 40 games\./);
  });
});

describe('MetricStatTooltip — pValue null branch (WR-04)', () => {
  it('omits the "(p = ...)" segment when pValue is null', () => {
    const { container } = render(
      <MetricStatTooltip {...scoreBase} level="medium" value={0.51} pValue={null} />,
    );
    expect(container.textContent).toMatch(/Medium confidence/);
    expect(container.textContent).not.toMatch(/p = /);
    expect(container.textContent).not.toMatch(/null/i);
    expect(container.textContent).not.toMatch(/NaN/);
  });

  it('renders "(p = X.XXX)" when pValue is a number', () => {
    const { container } = render(
      <MetricStatTooltip {...scoreBase} level="high" value={0.62} pValue={0.001} />,
    );
    expect(container.textContent).toMatch(/p = 0\.001/);
  });
});

describe('MetricStatTooltip — lastPlayedAt branch', () => {
  it('renders "Last played" line when lastPlayedAt is provided', () => {
    const { container } = render(
      <MetricStatTooltip
        {...scoreBase}
        level="high"
        value={0.62}
        lastPlayedAt="2026-05-01T12:00:00Z"
      />,
    );
    expect(container.textContent).toMatch(/Last played/);
  });

  it('omits "Last played" line when lastPlayedAt is null', () => {
    const { container } = render(
      <MetricStatTooltip
        {...scoreBase}
        level="high"
        value={0.62}
        lastPlayedAt={null}
      />,
    );
    expect(container.textContent).not.toMatch(/Last played/);
  });

  it('omits "Last played" line when lastPlayedAt is undefined', () => {
    const { container } = render(
      <MetricStatTooltip {...scoreBase} level="high" value={0.62} />,
    );
    expect(container.textContent).not.toMatch(/Last played/);
  });
});

describe('MetricStatTooltip — name + explanation paragraph', () => {
  it('renders bold name followed by the explanation prose', () => {
    const { container } = render(
      <MetricStatTooltip
        {...scoreBase}
        name="Achievable Score"
        explanation="Custom explanation here."
        level="high"
        value={0.62}
      />,
    );
    expect(container.textContent).toMatch(/Achievable Score: Custom explanation here\./);
  });
});

describe('MetricStatTooltip — D-10 forbidden framing (Achievable Score)', () => {
  it('Achievable-Score body mentions Lichess and 2300+, never underperformance/fall short/below your potential', () => {
    const { container } = render(
      <MetricStatTooltip
        {...scoreBase}
        name="Achievable Score"
        explanation={ACHIEVABLE_SCORE_EXPLANATION}
        level="high"
        value={0.62}
      />,
    );
    expect(container.textContent).toMatch(/2300\+/);
    expect(container.textContent).toMatch(/Lichess/);
    expect(container.textContent).not.toMatch(/underperformance/i);
    expect(container.textContent).not.toMatch(/fall short/i);
    expect(container.textContent).not.toMatch(/below your potential/i);
  });
});
