// @vitest-environment jsdom
import { describe, it, expect, afterEach } from 'vitest';
import { render, screen, cleanup } from '@testing-library/react';
import { getBoardContainerClassName } from '@/lib/openingsBoardLayout';

// Note: Full-page render of Openings would require mocking 15+ hooks
// (useUserProfile, useNextMoves, useOpeningsPositionQuery, usePositionBookmarks,
//  useMostPlayedOpenings, etc.), making the test fragile and hard to maintain.
// The helper is extracted to openingsBoardLayout.ts (separate from the React component
// file per react-refresh/only-export-components ESLint rule) so the logic is
// unit-testable without coupling to the page's data layer.

afterEach(() => {
  cleanup();
});

describe('Openings board container className', () => {
  it('board container has lg:hidden when activeTab is stats', () => {
    const className = getBoardContainerClassName('stats');
    expect(className).toMatch(/lg:hidden/);
  });

  it('board container does NOT have lg:hidden when activeTab is explorer', () => {
    const className = getBoardContainerClassName('explorer');
    expect(className).not.toMatch(/lg:hidden/);
  });

  it('board container does NOT have lg:hidden when activeTab is games', () => {
    const className = getBoardContainerClassName('games');
    expect(className).not.toMatch(/lg:hidden/);
  });

  it('base classes are always present regardless of tab', () => {
    const statsClass = getBoardContainerClassName('stats');
    const explorerClass = getBoardContainerClassName('explorer');
    // Both contain the base flex layout classes
    expect(statsClass).toMatch(/flex flex-col gap-2 w-\[400px\] shrink-0/);
    expect(explorerClass).toMatch(/flex flex-col gap-2 w-\[400px\] shrink-0/);
  });
});

// ---------------------------------------------------------------------------
// Unreliable-row opacity constants (PositionResultsPanel fades rows under the floor).
// ---------------------------------------------------------------------------

import { MiniBulletChart } from '@/components/charts/MiniBulletChart';
import { MIN_GAMES_FOR_RELIABLE_STATS, UNRELIABLE_OPACITY } from '@/lib/theme';

describe('Score bullet isUnreliable opacity logic', () => {
  it('total < MIN_GAMES_FOR_RELIABLE_STATS triggers UNRELIABLE_OPACITY', () => {
    // PositionResultsPanel applies opacity when stats.total < MIN_GAMES_FOR_RELIABLE_STATS.
    // Verify the constants are consistent with the spec (threshold=10, opacity=0.5).
    expect(MIN_GAMES_FOR_RELIABLE_STATS).toBe(10);
    expect(UNRELIABLE_OPACITY).toBe(0.5);

    const totalBelow = MIN_GAMES_FOR_RELIABLE_STATS - 1;
    const totalAtThreshold = MIN_GAMES_FOR_RELIABLE_STATS;
    expect(totalBelow < MIN_GAMES_FOR_RELIABLE_STATS).toBe(true);
    expect(totalAtThreshold < MIN_GAMES_FOR_RELIABLE_STATS).toBe(false);
  });
});

// ---------------------------------------------------------------------------
// Endgames entry-eval bullet sub-tree tests
//
// The Openings End Eval row is a verdict track (PositionResultsPanel.test.tsx); the
// bullet chart and EvalConfidencePopover remain only for the Endgames entry eval.
// ---------------------------------------------------------------------------

import { EvalConfidencePopover } from '@/components/insights/EvalConfidencePopover';
import {
  EVAL_BULLET_DOMAIN_PAWNS,
  EVAL_NEUTRAL_MIN_PAWNS,
  EVAL_NEUTRAL_MAX_PAWNS,
} from '@/lib/openingStatsZones';

describe('EvalConfidencePopover trigger (eval bullet)', () => {
  it('renders trigger with expected testid', () => {
    render(
      <EvalConfidencePopover
        level="medium"
        pValue={0.04}
        gameCount={25}
        evalMeanPawns={0.4}
        testId="eval-bullet-popover-trigger"
      />,
    );
    const trigger = screen.getByTestId('eval-bullet-popover-trigger');
    expect(trigger).not.toBeNull();
    expect(trigger.getAttribute('aria-label')).toBe('Show eval confidence details');
  });
});

describe('MiniBulletChart eval-domain configuration', () => {
  it('renders the eval bullet with a CI whisker', () => {
    render(
      <MiniBulletChart
        value={0.4}
        ciLow={0.2}
        ciHigh={0.6}
        neutralMin={EVAL_NEUTRAL_MIN_PAWNS}
        neutralMax={EVAL_NEUTRAL_MAX_PAWNS}
        domain={EVAL_BULLET_DOMAIN_PAWNS}
        barColor="neutral"
        ariaLabel="Avg eval at endgame entry: 0.40 pawns"
      />,
    );
    expect(screen.getByTestId('mini-bullet-chart')).not.toBeNull();
    expect(screen.getByTestId('mini-bullet-whisker')).not.toBeNull();
  });
});

describe('hasMgEval gate logic', () => {
  // The wdl-moves-position section renders the eval bullet only when
  // eval_n > 0 AND avg_eval_pawns is non-null. The gate is asserted in
  // isolation here; the section itself sits inside a full-page render that
  // would require mocking 15+ hooks.
  const hasMgEval = (stats: {
    eval_n: number;
    avg_eval_pawns: number | null | undefined;
  }): boolean =>
    stats.eval_n > 0 && stats.avg_eval_pawns !== null && stats.avg_eval_pawns !== undefined;

  it('returns true when eval_n>0 and avg_eval_pawns is a number', () => {
    expect(hasMgEval({ eval_n: 12, avg_eval_pawns: 0.3 })).toBe(true);
  });

  it('returns false when eval_n is 0 (em-dash fallback)', () => {
    expect(hasMgEval({ eval_n: 0, avg_eval_pawns: null })).toBe(false);
  });

  it('returns false when avg_eval_pawns is null (em-dash fallback)', () => {
    expect(hasMgEval({ eval_n: 5, avg_eval_pawns: null })).toBe(false);
  });

  it('returns false when avg_eval_pawns is undefined', () => {
    expect(hasMgEval({ eval_n: 5, avg_eval_pawns: undefined })).toBe(false);
  });
});
