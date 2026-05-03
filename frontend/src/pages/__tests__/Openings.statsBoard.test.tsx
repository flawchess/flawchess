import { describe, it, expect } from 'vitest';
import { getBoardContainerClassName } from '@/lib/openingsBoardLayout';

// Note: Full-page render of Openings would require mocking 15+ hooks
// (useUserProfile, useNextMoves, useOpeningsPositionQuery, usePositionBookmarks,
//  useMostPlayedOpenings, etc.), making the test fragile and hard to maintain.
// The helper is extracted to openingsBoardLayout.ts (separate from the React component
// file per react-refresh/only-export-components ESLint rule) so the logic is
// unit-testable without coupling to the page's data layer.
// See Phase 80 PLAN 04 §action step 4 (fallback: helper extraction).

describe('Openings board container className (D-03)', () => {
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

  it('board container does NOT have lg:hidden when activeTab is insights', () => {
    const className = getBoardContainerClassName('insights');
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
