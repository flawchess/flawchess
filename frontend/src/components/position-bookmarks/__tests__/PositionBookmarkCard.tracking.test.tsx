// @vitest-environment jsdom
/**
 * Phase 229 (D-03, D-04, D-12): the bookmark card's chart toggle and load button
 * each report one id-free event; the persisted match-side change stays untracked
 * (DB-known). Real analytics module with a window.umami stub.
 */
import { DndContext } from '@dnd-kit/core';
import { SortableContext } from '@dnd-kit/sortable';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { PositionBookmarkCard } from '../PositionBookmarkCard';
import { TooltipProvider } from '@/components/ui/tooltip';
import type { PositionBookmarkResponse } from '@/types/position_bookmarks';

// The mini board is irrelevant here and heavy in jsdom.
vi.mock('../MiniBoard', () => ({ MiniBoard: () => null }));

const BOOKMARK_ID = 48213;

const BOOKMARK: PositionBookmarkResponse = {
  id: BOOKMARK_ID,
  label: 'Sicilian Najdorf',
  target_hash: '123456789',
  fen: 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1',
  moves: ['e4', 'c5'],
  color: 'white',
  match_side: 'both',
  is_flipped: false,
  sort_order: 0,
};

const track = vi.fn();

beforeEach(() => {
  track.mockClear();
  window.umami = { track, identify: vi.fn() };
  window.history.pushState({}, '', '/openings');
});

afterEach(() => {
  cleanup();
  delete window.umami;
});

function renderCard(chartEnabled: boolean) {
  const onChartEnabledChange = vi.fn();
  const onLoad = vi.fn();
  render(
    <QueryClientProvider client={new QueryClient()}>
      <TooltipProvider>
        <DndContext>
          <SortableContext items={[BOOKMARK_ID]}>
            <PositionBookmarkCard
              bookmark={BOOKMARK}
              onLoad={onLoad}
              chartEnabled={chartEnabled}
              onChartEnabledChange={onChartEnabledChange}
              onMatchSideChange={vi.fn()}
            />
          </SortableContext>
        </DndContext>
      </TooltipProvider>
    </QueryClientProvider>,
  );
  return { onChartEnabledChange, onLoad };
}

/** The card renders mobile and desktop layouts side by side; either copy works. */
function firstByTestId(testId: string): HTMLElement {
  const [first] = screen.getAllByTestId(testId);
  if (!first) throw new Error(`no element with testid ${testId}`);
  return first;
}

function expectNoBookmarkId(): void {
  for (const call of track.mock.calls) {
    expect(JSON.stringify(call)).not.toContain(String(BOOKMARK_ID));
  }
}

describe('PositionBookmarkCard tracking', () => {
  it('fires nothing on render', () => {
    renderCard(true);
    expect(track).not.toHaveBeenCalled();
  });

  it('reports the chart toggle as off when it was on, and calls the handler', () => {
    const { onChartEnabledChange } = renderCard(true);
    fireEvent.click(firstByTestId(`bookmark-chart-toggle-${BOOKMARK_ID}`));
    expect(onChartEnabledChange).toHaveBeenCalledWith(BOOKMARK_ID, false);
    expect(track).toHaveBeenCalledTimes(1);
    expect(track).toHaveBeenCalledWith('toggle', { page: 'openings', target: 'bookmark-chart', value: 'off' });
    expectNoBookmarkId();
  });

  it('reports the chart toggle as on when it was off', () => {
    renderCard(false);
    fireEvent.click(firstByTestId(`bookmark-chart-toggle-${BOOKMARK_ID}`));
    expect(track).toHaveBeenCalledWith('toggle', { page: 'openings', target: 'bookmark-chart', value: 'on' });
  });

  it('reports the load button as a fixed action without any identifier', () => {
    const { onLoad } = renderCard(true);
    fireEvent.click(firstByTestId(`bookmark-btn-load-${BOOKMARK_ID}`));
    expect(onLoad).toHaveBeenCalledWith(BOOKMARK);
    expect(track).toHaveBeenCalledTimes(1);
    expect(track).toHaveBeenCalledWith('action', { page: 'openings', target: 'bookmark-load' });
    expectNoBookmarkId();
  });

  it('does not track the persisted match-side change (DB-known)', () => {
    renderCard(true);
    fireEvent.click(firstByTestId(`bookmark-match-side-${BOOKMARK_ID}-mine`));
    expect(track).not.toHaveBeenCalled();
  });
});
