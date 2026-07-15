import { Chess } from 'chess.js';
import { describe, expect, it } from 'vitest';

import type { BotGameOutcome } from '../botGameEnd';
import { annotateClock, finalizeBotPgn, formatClockHms, TERMINATION_CHECKMATE, toBackendTcStr } from '../botGamePgn';

describe('formatClockHms', () => {
  it('formats remaining time as lichess h:mm:ss', () => {
    expect(formatClockHms(4 * 60_000 + 57_000)).toBe('0:04:57');
    expect(formatClockHms(0)).toBe('0:00:00');
    expect(formatClockHms(3_661_000)).toBe('1:01:01'); // 1h 1m 1s
  });
});

describe('toBackendTcStr', () => {
  it('formats base+increment seconds, not a minutes display label', () => {
    expect(toBackendTcStr(300, 3)).toBe('300+3');
    expect(toBackendTcStr(180, 0)).toBe('180+0');
  });
});

describe('annotateClock + finalizeBotPgn', () => {
  it('embeds a [%clk] comment on both a white and a black ply, with the correct headers', () => {
    const chess = new Chess();
    const plies: [string, number][] = [
      ['e4', 297_000], // 0:04:57
      ['e5', 295_000], // 0:04:55
      ['Bc4', 293_000],
      ['Nc6', 291_000],
      ['Qh5', 289_000],
      ['Nf6', 287_000],
      ['Qxf7', 285_000], // checkmate
    ];
    for (const [san, remainingMs] of plies) {
      chess.move(san);
      annotateClock(chess, remainingMs);
    }
    expect(chess.isCheckmate()).toBe(true);

    const outcome: BotGameOutcome = { reason: 'checkmate', winner: 'white' };
    const pgn = finalizeBotPgn(chess, outcome, '300+3');

    expect(pgn).toContain('{[%clk 0:04:57]}'); // white's first ply
    expect(pgn).toContain('{[%clk 0:04:55]}'); // black's first ply
    expect(pgn).toContain('[Result "1-0"]');
    expect(pgn).toContain(`[Termination "${TERMINATION_CHECKMATE}"]`);
    expect(pgn).toContain('[TimeControl "300+3"]');
  });

  it('collapses every board-draw reason to the single backend "draw" Termination', () => {
    const chess = new Chess('k7/8/1Q6/8/8/8/8/7K b - - 0 1'); // stalemate
    const outcome: BotGameOutcome = { reason: 'draw', drawReason: 'stalemate' };
    const pgn = finalizeBotPgn(chess, outcome, '300+3');
    expect(pgn).toContain('[Termination "draw"]');
    expect(pgn).toContain('[Result "1/2-1/2"]');
  });
});
