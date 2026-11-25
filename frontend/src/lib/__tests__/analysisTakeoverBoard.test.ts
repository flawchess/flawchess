import { describe, expect, it } from 'vitest';

import { takeoverBoardBlockMaxWidth } from '@/lib/analysisTakeoverBoard';

/** Evaluates the CSS expression at a viewport size, without safe areas. Returns the board's
 *  width (the block less its 72px of eval bars, gaps and padding). */
function boardAt(width: number, height: number, css: string): number {
  const js = css
    .replaceAll(/env\([^)]*\)/g, '0')
    .replaceAll('92vw', String(0.92 * width))
    .replaceAll('100svh', String(height))
    .replaceAll('px', '')
    .replaceAll(/\b(min|max)\(/g, 'Math.$1(');
  return (new Function(`return ${js}`)() as number) - 72;
}

const GAME = { hasPlayerRows: true, hasExplainBar: true };
const FREE_PLAY = { hasPlayerRows: false, hasExplainBar: false };
const GAME_CHROME_PX = 248;

describe('takeoverBoardBlockMaxWidth', () => {
  it.each([
    ['cover screen', 475, 663],
    ['zoomed inner screen', 616, 728],
    ['inner screen', 704, 845],
    ['iPhone SE', 375, 647],
  ])('leaves the tabs at least 100px on the %s', (_name, width, height) => {
    const board = boardAt(width, height, takeoverBoardBlockMaxWidth(GAME));
    expect(height - GAME_CHROME_PX - board).toBeGreaterThanOrEqual(100);
  });

  it('keeps the width-driven size where the height allows it', () => {
    expect(boardAt(375, 647, takeoverBoardBlockMaxWidth(GAME))).toBeCloseTo(273);
    expect(boardAt(704, 845, takeoverBoardBlockMaxWidth(GAME))).toBe(460);
  });

  it('never goes below 256px', () => {
    expect(boardAt(416, 569, takeoverBoardBlockMaxWidth(GAME))).toBe(256);
    expect(boardAt(375, 553, takeoverBoardBlockMaxWidth(GAME))).toBe(256);
  });

  it('reserves nothing for the rows free play does not have', () => {
    const game = boardAt(475, 663, takeoverBoardBlockMaxWidth(GAME));
    const pasted = boardAt(475, 663, takeoverBoardBlockMaxWidth({ hasPlayerRows: true, hasExplainBar: false }));
    expect(game).toBe(315);
    expect(pasted).toBeCloseTo(365);
    expect(boardAt(616, 728, takeoverBoardBlockMaxWidth(FREE_PLAY))).toBe(460);
  });

  it('subtracts both safe areas', () => {
    const css = takeoverBoardBlockMaxWidth(GAME);
    expect(css).toContain('- env(safe-area-inset-top, 0px)');
    expect(css).toContain('- env(safe-area-inset-bottom, 0px)');
  });
});
