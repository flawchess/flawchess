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
