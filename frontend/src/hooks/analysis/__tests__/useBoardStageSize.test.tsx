// @vitest-environment jsdom
/**
 * The mid layout below lg has a footer pinned to the viewport: the board must leave room for
 * the rows around it (players, Explain bar) above that footer. jsdom has no layout, so the
 * boxes are stubbed with the sizes measured on a Galaxy Z Fold8 in landscape (933x617 between
 * the OS status bar and taskbar).
 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, render, screen } from '@testing-library/react';
import { useRef } from 'react';
import { useBoardStageSize } from '../useBoardStageSize';

const VIEWPORT_HEIGHT = 617;
const STAGE_TOP = 8;
/** `<main>` without its padding; the board column may take 60% of it less the 16px gap. */
const MAIN_WIDTH = 885;
const STAGE_WIDTH = 521;
const FOOTER_CLEARANCE = 76;
/** Group height minus board height: source caps, player rows, Explain bar slot, gaps. */
const CHROME = 138;
const BOARD_BOX = 441;

let stageWidth = STAGE_WIDTH;

function Probe({ isColumnBoardWide = true, hasPinnedFooter }: { isColumnBoardWide?: boolean; hasPinnedFooter: boolean }) {
  const containerRef = useRef<HTMLDivElement>(null);
  const { boardStageRef, boardWidth } = useBoardStageSize({
    layoutMode: 'mid',
    containerRef,
    isGameMode: true,
    isColumnBoardWide,
    hasPinnedFooter,
    gameData: undefined,
  });
  return (
    <main style={{ paddingBottom: FOOTER_CLEARANCE }}>
      <div ref={boardStageRef} data-box="stage">
        <div data-box="group">
          <div ref={containerRef} data-box="board" />
        </div>
      </div>
      <output data-testid="board-width">{boardWidth}</output>
    </main>
  );
}

beforeEach(() => {
  stageWidth = STAGE_WIDTH;
  vi.stubGlobal(
    'matchMedia',
    vi.fn(() => ({ matches: false })),
  );
  vi.stubGlobal(
    'ResizeObserver',
    class {
      observe() {}
      disconnect() {}
    },
  );
  const heights: Record<string, number> = { group: BOARD_BOX + CHROME, board: BOARD_BOX };
  vi.spyOn(Element.prototype, 'clientHeight', 'get').mockImplementation(function (this: Element) {
    if (this === document.documentElement) return VIEWPORT_HEIGHT;
    return heights[(this as HTMLElement).dataset.box ?? ''] ?? 0;
  });
  vi.spyOn(Element.prototype, 'clientWidth', 'get').mockImplementation(function (this: Element) {
    return this.tagName === 'MAIN' ? MAIN_WIDTH : stageWidth;
  });
  vi.spyOn(Element.prototype, 'getBoundingClientRect').mockReturnValue({ top: STAGE_TOP } as DOMRect);
});

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

function boardWidth(): number {
  return Number(screen.getByTestId('board-width').textContent);
}

describe('useBoardStageSize: mid layout with a pinned footer', () => {
  it('fits the board and the rows around it above the footer', () => {
    render(<Probe hasPinnedFooter />);
    expect(boardWidth()).toBe(VIEWPORT_HEIGHT - STAGE_TOP - CHROME - FOOTER_CLEARANCE);
  });

  it('is width-driven from lg', () => {
    render(<Probe isColumnBoardWide={false} hasPinnedFooter={false} />);
    expect(boardWidth()).toBe(BOARD_BOX);
  });

  it('is width-driven below lg with the footer in flow (a phone held sideways)', () => {
    stageWidth = 300;
    render(<Probe hasPinnedFooter={false} />);
    expect(Math.floor(boardWidth())).toBe(BOARD_BOX);
  });

  it('takes its width budget from the page, not from its own column', () => {
    // The column is only as wide as the board: a budget read from it would shrink the board
    // a bit more on every measurement.
    stageWidth = 300;
    render(<Probe hasPinnedFooter />);
    expect(boardWidth()).toBe(VIEWPORT_HEIGHT - STAGE_TOP - CHROME - FOOTER_CLEARANCE);
  });
});
