// @vitest-environment jsdom
/**
 * HorizontalMoveList auto-scroll with a scroll tail: on the
 * two-row mobile Train list the live preview after the current move must not
 * sit below the fold.
 */
import { describe, it, expect, vi, afterEach, beforeEach } from 'vitest';
import { render, screen, cleanup } from '@testing-library/react';
import { HorizontalMoveList } from '../HorizontalMoveList';
import type { HorizontalMoveItem } from '../HorizontalMoveList';

const BOX_HEIGHT = 70;
const ROW_HEIGHT = 30;

/** Fake layout: each testid sits on a row; the box scroll offset shifts every row. */
function stubLayout(rowByTestId: Record<string, number>): void {
  vi.spyOn(Element.prototype, 'getBoundingClientRect').mockImplementation(function (this: Element) {
    const box = screen.getByTestId('list');
    const id = (this as HTMLElement).dataset.testid ?? '';
    const offset = this === box ? 0 : box.scrollTop;
    const row = id === 'list' ? 0 : (rowByTestId[id] ?? 0);
    const top = row * ROW_HEIGHT - offset;
    return { top, bottom: top + (id === 'list' ? BOX_HEIGHT : ROW_HEIGHT), left: 0, right: 0, width: 0, height: 0, x: 0, y: top, toJSON: () => ({}) };
  });
  Object.defineProperty(HTMLElement.prototype, 'clientHeight', { configurable: true, get: () => BOX_HEIGHT });
}

function items(withTail: boolean): HorizontalMoveItem[] {
  return [
    { key: 'a', ply: 0, san: 'e4', testId: 'm-a' },
    { key: 'b', ply: 1, san: 'e5', testId: 'm-b', isCurrent: true },
    { key: 'p0', ply: -1, san: 'Nf3', testId: 'p-0', dimmed: true },
    { key: 'p1', ply: -2, san: 'Nc6', testId: 'p-1', dimmed: true, scrollTail: withTail },
  ];
}

describe('HorizontalMoveList scroll tail', () => {
  beforeEach(() => {
    Element.prototype.scrollIntoView = vi.fn();
  });
  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
    delete (HTMLElement.prototype as { clientHeight?: number }).clientHeight;
  });

  it('scrolls the current move to the top row so the tail fits below it', () => {
    stubLayout({ 'm-a': 0, 'm-b': 1, 'p-0': 2, 'p-1': 3 });
    render(<HorizontalMoveList items={items(true)} onMoveClick={() => {}} testId="list" />);
    // current top 30 - pad 4 = 26; tail bottom 120 - 70 + 4 = 54 -> min is 26.
    expect(screen.getByTestId('list').scrollTop).toBe(26);
    expect(Element.prototype.scrollIntoView).not.toHaveBeenCalled();
  });

  it('falls back to a nearest scroll of the current move without a tail', () => {
    stubLayout({ 'm-a': 0, 'm-b': 1, 'p-0': 2, 'p-1': 3 });
    render(<HorizontalMoveList items={items(false)} onMoveClick={() => {}} testId="list" />);
    expect(screen.getByTestId('list').scrollTop).toBe(0);
    expect(Element.prototype.scrollIntoView).toHaveBeenCalled();
  });
});
