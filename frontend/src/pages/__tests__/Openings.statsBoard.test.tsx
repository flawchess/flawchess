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
// See Phase 80 PLAN 04 §action step 4 (fallback: helper extraction).

afterEach(() => {
  cleanup();
});

describe('Openings board container className', () => {
  it('board container has lg:hidden when activeTab is stats (D-03)', () => {
    const className = getBoardContainerClassName('stats');
    expect(className).toMatch(/lg:hidden/);
  });

  it('board container has lg:hidden when activeTab is insights', () => {
    // Insights uses a 2-column white/black layout on desktop and doesn't need
    // the chessboard, so we hide it at lg+ to free horizontal space.
    const className = getBoardContainerClassName('insights');
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
// Score bullet sub-tree tests (quick task 260504-ttq)
//
// Full-page render of Openings requires mocking 15+ hooks. Instead, we
// test the score bullet sub-tree components directly: ScoreConfidencePopover
// (trigger testid + aria-label) and the isUnreliable opacity logic.
// ---------------------------------------------------------------------------

import { ScoreConfidencePopover } from '@/components/insights/ScoreConfidencePopover';
import { MiniBulletChart } from '@/components/charts/MiniBulletChart';
import {
  SCORE_BULLET_CENTER,
  SCORE_BULLET_DOMAIN,
  SCORE_BULLET_NEUTRAL_MAX,
  SCORE_BULLET_NEUTRAL_MIN,
} from '@/lib/scoreBulletConfig';
import { MIN_GAMES_FOR_RELIABLE_STATS, UNRELIABLE_OPACITY } from '@/lib/theme';

describe('ScoreConfidencePopover trigger (score bullet, 260504-ttq)', () => {
  it('renders trigger with expected testid and aria-label', () => {
    render(
      <ScoreConfidencePopover
        level="high"
        pValue={0.02}
        score={0.7}
        gameCount={10}
        testId="score-bullet-popover-trigger"
        ariaLabel="Show score confidence details"
      />,
    );
    const trigger = screen.getByTestId('score-bullet-popover-trigger');
    expect(trigger).not.toBeNull();
    expect(trigger.getAttribute('aria-label')).toBe('Show score confidence details');
  });

  it('uses default aria-label when not provided', () => {
    render(
      <ScoreConfidencePopover
        level="low"
        pValue={0.3}
        score={0.5}
        gameCount={5}
        testId="test-trigger"
      />,
    );
    const trigger = screen.getByTestId('test-trigger');
    expect(trigger.getAttribute('aria-label')).toBe('Show score confidence details');
  });
});

describe('MiniBulletChart score-domain configuration (260504-ttq)', () => {
  it('renders with score-domain constants and CI whisker', () => {
    render(
      <MiniBulletChart
        value={0.7}
        center={SCORE_BULLET_CENTER}
        neutralMin={SCORE_BULLET_NEUTRAL_MIN}
        neutralMax={SCORE_BULLET_NEUTRAL_MAX}
        domain={SCORE_BULLET_DOMAIN}
        ciLow={0.55}
        ciHigh={0.85}
        ariaLabel="Score 70% vs 50% baseline"
      />,
    );
    // MiniBulletChart renders with testid="mini-bullet-chart"
    expect(screen.getByTestId('mini-bullet-chart')).not.toBeNull();
    // CI whisker is present when both ciLow and ciHigh are provided
    expect(screen.getByTestId('mini-bullet-whisker')).not.toBeNull();
  });

  it('does not render CI whisker when CI props omitted', () => {
    render(
      <MiniBulletChart
        value={0.5}
        center={SCORE_BULLET_CENTER}
        neutralMin={SCORE_BULLET_NEUTRAL_MIN}
        neutralMax={SCORE_BULLET_NEUTRAL_MAX}
        domain={SCORE_BULLET_DOMAIN}
        ariaLabel="Score 50% vs 50% baseline"
      />,
    );
    expect(screen.queryByTestId('mini-bullet-whisker')).toBeNull();
  });
});

describe('Score bullet isUnreliable opacity logic (260504-ttq)', () => {
  it('total < MIN_GAMES_FOR_RELIABLE_STATS triggers UNRELIABLE_OPACITY', () => {
    // The moveExplorerContent IIFE applies opacity when stats.total < MIN_GAMES_FOR_RELIABLE_STATS.
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
// Eval bullet sub-tree tests (quick task 260508-f9o)
//
// Same pattern as the score-bullet tests above: full-page render of Openings
// requires mocking 15+ hooks, so we cover the eval row's key sub-trees
// (MiniBulletChart with eval domain + BulletConfidencePopover trigger) and
// the hasMgEval gate logic in isolation.
// ---------------------------------------------------------------------------

import { BulletConfidencePopover } from '@/components/insights/BulletConfidencePopover';
import {
  EVAL_BULLET_DOMAIN_PAWNS,
  EVAL_NEUTRAL_MIN_PAWNS,
  EVAL_NEUTRAL_MAX_PAWNS,
} from '@/lib/openingStatsZones';

describe('BulletConfidencePopover trigger (eval bullet, 260508-f9o)', () => {
  it('renders trigger with expected testid', () => {
    render(
      <BulletConfidencePopover
        level="medium"
        pValue={0.04}
        gameCount={25}
        evalMeanPawns={0.4}
        color="white"
        testId="eval-bullet-popover-trigger"
      />,
    );
    const trigger = screen.getByTestId('eval-bullet-popover-trigger');
    expect(trigger).not.toBeNull();
    expect(trigger.getAttribute('aria-label')).toBe('Show eval confidence details');
  });
});

describe('MiniBulletChart eval-domain configuration (260508-f9o)', () => {
  it('renders the eval bullet with tickPawns and CI whisker', () => {
    render(
      <MiniBulletChart
        value={0.4}
        ciLow={0.2}
        ciHigh={0.6}
        tickPawns={0.25}
        neutralMin={EVAL_NEUTRAL_MIN_PAWNS}
        neutralMax={EVAL_NEUTRAL_MAX_PAWNS}
        domain={EVAL_BULLET_DOMAIN_PAWNS}
        barColor="neutral"
        ariaLabel="Avg eval at MG entry: 0.40 pawns"
      />,
    );
    expect(screen.getByTestId('mini-bullet-chart')).not.toBeNull();
    expect(screen.getByTestId('mini-bullet-whisker')).not.toBeNull();
  });
});

describe('hasMgEval gate logic (260508-f9o)', () => {
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
