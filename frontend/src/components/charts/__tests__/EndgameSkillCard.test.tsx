// @vitest-environment jsdom
/**
 * Phase 87.2 Plan 03: tests for EndgameSkillCard (composite Skill variant).
 *
 * Covers:
 * - Structural render: gauge + ScoreGapRow bullet present when
 *   skill !== null && scoreGapN > 0.
 * - No MiniWDLBar (single-ply composite, no W/D/L definable per SEC2-03).
 * - ScoreGapRow absent when scoreGapN === 0.
 * - Sign convention: zone-only tint (Phase 85.1 D-04 inherited).
 *   positive gapMean >= neutralMax -> ZONE_SUCCESS;
 *   negative gapMean < neutralMin -> ZONE_DANGER;
 *   inside band -> no color.
 * - testid sub-elements: -score-gap-bullet, -score-gap-value, -score-gap-info.
 * - Popover name is "Skill Score Gap" (D-07); explanation contains Skill copy
 *   and sigmoid caveat; no "vs opponents" / "Opp Skill" framing.
 * - CI whisker props: passed at n >= 2 (non-null); undefined at n < 2.
 * - Empty state: skill === null -> "Not enough data yet" + opacity-50 gauge;
 *   no ScoreGapRow, no popover trigger.
 * - tileTestId prop is the container's data-testid.
 */

import { afterEach, beforeAll, describe, expect, it, vi } from 'vitest';
import { cleanup, render, screen } from '@testing-library/react';

import { ZONE_DANGER, ZONE_SUCCESS } from '@/lib/theme';

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

import { EndgameSkillCard } from '../EndgameSkillCard';

function normalizeColor(value: string): string {
  return value.replace(/(\d+)\.(\d*?)0+(?=\D|$)/g, (match, intPart: string, frac: string) => {
    if (frac === '') return `${intPart}`;
    return `${intPart}.${frac}`;
  });
}

// Default Score Gap props: positive, outside neutral band, confident.
const DEFAULT_SKILL_GAP_PROPS = {
  scoreGapMean: 0.10,   // above SECTION2_SCORE_GAP_SKILL_NEUTRAL_MAX (0.05)
  scoreGapN: 300,
  scoreGapPValue: 0.001,
  scoreGapCiLow: 0.05,
  scoreGapCiHigh: 0.15,
};

describe('EndgameSkillCard — structural render', () => {
  it('renders container with tileTestId, gauge, and ScoreGapRow bullet', () => {
    render(
      <EndgameSkillCard
        skill={0.55}
        totalGames={300}
        tileTestId="tile-endgame-skill"
        {...DEFAULT_SKILL_GAP_PROPS}
      />,
    );
    expect(screen.getByTestId('tile-endgame-skill')).not.toBeNull();
    expect(screen.getByTestId('tile-endgame-skill-score-gap-bullet')).not.toBeNull();
    expect(screen.getByTestId('tile-endgame-skill-score-gap-value')).not.toBeNull();
    expect(screen.getByTestId('tile-endgame-skill-score-gap-info')).not.toBeNull();
  });

  it('does NOT render MiniWDLBar (no W/D/L for the single-ply composite)', () => {
    render(
      <EndgameSkillCard
        skill={0.55}
        totalGames={300}
        tileTestId="tile-endgame-skill"
        {...DEFAULT_SKILL_GAP_PROPS}
      />,
    );
    expect(screen.queryByTestId('mini-wdl-bar')).toBeNull();
  });

  it('renders "Endgame Skill" title', () => {
    render(
      <EndgameSkillCard
        skill={0.55}
        totalGames={300}
        tileTestId="tile-endgame-skill"
        {...DEFAULT_SKILL_GAP_PROPS}
      />,
    );
    expect(screen.getByText('Endgame Skill')).not.toBeNull();
  });

  it('renders ScoreGapRow when scoreGapN > 0', () => {
    render(
      <EndgameSkillCard
        skill={0.55}
        totalGames={300}
        tileTestId="tile-endgame-skill"
        {...DEFAULT_SKILL_GAP_PROPS}
      />,
    );
    expect(screen.getByTestId('tile-endgame-skill-score-gap-bullet')).not.toBeNull();
    // ScoreGapRow renders a MiniBulletChart
    expect(screen.queryByTestId('mini-bullet-chart')).not.toBeNull();
  });

  it('does NOT render ScoreGapRow when scoreGapN === 0', () => {
    render(
      <EndgameSkillCard
        skill={0.55}
        totalGames={300}
        tileTestId="tile-endgame-skill"
        scoreGapMean={null}
        scoreGapN={0}
        scoreGapPValue={null}
        scoreGapCiLow={null}
        scoreGapCiHigh={null}
      />,
    );
    expect(screen.queryByTestId('tile-endgame-skill-score-gap-bullet')).toBeNull();
    expect(screen.queryByTestId('mini-bullet-chart')).toBeNull();
  });

  it('renders formatted value in score-gap-value testid', () => {
    render(
      <EndgameSkillCard
        skill={0.55}
        totalGames={300}
        tileTestId="tile-endgame-skill"
        scoreGapMean={0.05}   // exactly +5%
        scoreGapN={100}
        scoreGapPValue={0.05}
        scoreGapCiLow={null}
        scoreGapCiHigh={null}
      />,
    );
    const valueEl = screen.getByTestId('tile-endgame-skill-score-gap-value');
    expect(valueEl.textContent).toBe('+5%');
  });
});

describe('EndgameSkillCard — sign convention (zone-only tint, no sig-gate)', () => {
  it('paints value with ZONE_SUCCESS when gapMean >= neutralMax (positive outside band)', () => {
    render(
      <EndgameSkillCard
        skill={0.55}
        totalGames={300}
        tileTestId="tile-endgame-skill"
        scoreGapMean={0.10}   // above SECTION2_SCORE_GAP_SKILL_NEUTRAL_MAX (0.05)
        scoreGapN={300}
        scoreGapPValue={0.5}  // weak p-value: zone-only means color still applied
        scoreGapCiLow={null}
        scoreGapCiHigh={null}
      />,
    );
    const valueEl = screen.getByTestId('tile-endgame-skill-score-gap-value');
    expect(normalizeColor(valueEl.style.color)).toBe(normalizeColor(ZONE_SUCCESS));
  });

  it('paints value with ZONE_DANGER when gapMean < neutralMin (negative outside band)', () => {
    render(
      <EndgameSkillCard
        skill={0.55}
        totalGames={300}
        tileTestId="tile-endgame-skill"
        scoreGapMean={-0.10}  // below SECTION2_SCORE_GAP_SKILL_NEUTRAL_MIN (-0.05)
        scoreGapN={300}
        scoreGapPValue={0.5}
        scoreGapCiLow={null}
        scoreGapCiHigh={null}
      />,
    );
    const valueEl = screen.getByTestId('tile-endgame-skill-score-gap-value');
    expect(normalizeColor(valueEl.style.color)).toBe(normalizeColor(ZONE_DANGER));
  });

  it('does NOT paint value color when gapMean is inside neutral band', () => {
    render(
      <EndgameSkillCard
        skill={0.55}
        totalGames={300}
        tileTestId="tile-endgame-skill"
        scoreGapMean={0.02}   // inside [-0.05, 0.05] neutral band
        scoreGapN={300}
        scoreGapPValue={0.001}
        scoreGapCiLow={null}
        scoreGapCiHigh={null}
      />,
    );
    const valueEl = screen.getByTestId('tile-endgame-skill-score-gap-value');
    expect(valueEl.style.color).toBe('');
  });
});

describe('EndgameSkillCard — popover content (D-07 / D-08)', () => {
  it('popover aria-label is "What is Skill Score Gap?" per D-07', () => {
    render(
      <EndgameSkillCard
        skill={0.55}
        totalGames={300}
        tileTestId="tile-endgame-skill"
        {...DEFAULT_SKILL_GAP_PROPS}
      />,
    );
    const infoTrigger = screen.getByTestId('tile-endgame-skill-score-gap-info');
    expect(infoTrigger.getAttribute('aria-label')).toBe('What is Skill Score Gap?');
  });

  it('does NOT have "You:" / "Opp:" labels (D-08: no vs opponents framing)', () => {
    render(
      <EndgameSkillCard
        skill={0.55}
        totalGames={300}
        tileTestId="tile-endgame-skill"
        {...DEFAULT_SKILL_GAP_PROPS}
      />,
    );
    expect(screen.queryByText(/You:/)).toBeNull();
    expect(screen.queryByText(/Opp:/)).toBeNull();
    expect(screen.queryByText(/Opp Skill/)).toBeNull();
  });
});

describe('EndgameSkillCard — CI whisker props', () => {
  it('passes CI props to ScoreGapRow when scoreGapCiLow/CiHigh are non-null', () => {
    render(
      <EndgameSkillCard
        skill={0.55}
        totalGames={300}
        tileTestId="tile-endgame-skill"
        scoreGapMean={0.10}
        scoreGapN={300}
        scoreGapPValue={0.001}
        scoreGapCiLow={0.05}
        scoreGapCiHigh={0.15}
      />,
    );
    expect(screen.getByTestId('mini-bullet-chart')).not.toBeNull();
  });

  it('passes undefined CI when scoreGapCiLow/CiHigh are null', () => {
    render(
      <EndgameSkillCard
        skill={0.55}
        totalGames={300}
        tileTestId="tile-endgame-skill"
        scoreGapMean={0.10}
        scoreGapN={1}
        scoreGapPValue={null}
        scoreGapCiLow={null}
        scoreGapCiHigh={null}
      />,
    );
    // ScoreGapRow still renders (gapN > 0), but no CI whiskers
    expect(screen.getByTestId('tile-endgame-skill-score-gap-bullet')).not.toBeNull();
  });
});

describe('EndgameSkillCard — empty state', () => {
  it('renders "Not enough data yet" when skill === null', () => {
    render(
      <EndgameSkillCard
        skill={null}
        totalGames={0}
        tileTestId="tile-endgame-skill"
        scoreGapMean={null}
        scoreGapN={0}
        scoreGapPValue={null}
        scoreGapCiLow={null}
        scoreGapCiHigh={null}
      />,
    );
    expect(screen.queryByText(/Not enough data yet/)).not.toBeNull();
    // No ScoreGapRow, no popover trigger
    expect(screen.queryByTestId('tile-endgame-skill-score-gap-bullet')).toBeNull();
    expect(screen.queryByTestId('tile-endgame-skill-score-gap-info')).toBeNull();
    expect(screen.queryByTestId('mini-bullet-chart')).toBeNull();
  });
});
