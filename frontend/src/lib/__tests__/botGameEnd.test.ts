import { Chess } from 'chess.js';
import { describe, expect, it } from 'vitest';

import { detectEndCondition, resultCopy, type BotGameOutcome } from '../botGameEnd';

describe('detectEndCondition', () => {
  it('detects checkmate with black to move and derives white as the winner', () => {
    // Scholar's mate: 1.e4 e5 2.Bc4 Nc6 3.Qh5 Nf6 4.Qxf7# — black is mated.
    const chess = new Chess();
    for (const san of ['e4', 'e5', 'Bc4', 'Nc6', 'Qh5', 'Nf6', 'Qxf7']) chess.move(san);
    expect(chess.isCheckmate()).toBe(true);
    expect(detectEndCondition(chess)).toEqual({ reason: 'checkmate', winner: 'white' });
  });

  it('detects checkmate with white to move and derives black as the winner', () => {
    // Fool's mate: 1.f3 e5 2.g4 Qh4# — white is mated.
    const chess = new Chess();
    for (const san of ['f3', 'e5', 'g4', 'Qh4']) chess.move(san);
    expect(chess.isCheckmate()).toBe(true);
    expect(detectEndCondition(chess)).toEqual({ reason: 'checkmate', winner: 'black' });
  });

  it('detects stalemate', () => {
    const chess = new Chess('k7/8/1Q6/8/8/8/8/7K b - - 0 1');
    expect(detectEndCondition(chess)).toEqual({ reason: 'draw', drawReason: 'stalemate' });
  });

  it('detects threefold repetition', () => {
    const chess = new Chess();
    for (const san of ['Nf3', 'Nf6', 'Ng1', 'Ng8', 'Nf3', 'Nf6', 'Ng1', 'Ng8']) chess.move(san);
    expect(detectEndCondition(chess)).toEqual({ reason: 'draw', drawReason: 'threefold' });
  });

  it('detects the fifty-move rule', () => {
    const chess = new Chess('4k3/8/8/8/8/8/8/4K3 w - - 100 60');
    expect(detectEndCondition(chess)).toEqual({ reason: 'draw', drawReason: 'fifty-move' });
  });

  it('detects insufficient material', () => {
    const chess = new Chess('4k3/8/8/8/8/8/8/4K3 w - - 0 1');
    expect(detectEndCondition(chess)).toEqual({ reason: 'draw', drawReason: 'insufficient-material' });
  });

  it('returns null while the game continues', () => {
    const chess = new Chess();
    chess.move('e4');
    expect(detectEndCondition(chess)).toBeNull();
  });
});

describe('resultCopy', () => {
  it('shows the win/loss checkmate strings from the user POV', () => {
    const won: BotGameOutcome = { reason: 'checkmate', winner: 'white' };
    const lost: BotGameOutcome = { reason: 'checkmate', winner: 'black' };
    expect(resultCopy(won, 'white')).toBe('You won — checkmate');
    expect(resultCopy(lost, 'white')).toBe('You lost — checkmate');
  });

  it('shows the win/loss on-time strings from the user POV', () => {
    const won: BotGameOutcome = { reason: 'timeout', winner: 'black' };
    const lost: BotGameOutcome = { reason: 'timeout', winner: 'white' };
    expect(resultCopy(won, 'black')).toBe('You won on time');
    expect(resultCopy(lost, 'black')).toBe('You lost on time');
  });

  it('shows "You resigned" for a user resignation (bot never resigns, D-03)', () => {
    const resigned: BotGameOutcome = { reason: 'resignation', winner: 'black' };
    expect(resultCopy(resigned, 'white')).toBe('You resigned');
  });

  it('shows "You won — the bot resigned" only in the (D-03-unreachable) opposite case', () => {
    const opponentResigned: BotGameOutcome = { reason: 'resignation', winner: 'white' };
    expect(resultCopy(opponentResigned, 'white')).toBe('You won — the bot resigned');
  });

  it('maps each draw reason to its exact UI-SPEC copy', () => {
    expect(resultCopy({ reason: 'draw', drawReason: 'stalemate' }, 'white')).toBe('Draw — stalemate');
    expect(resultCopy({ reason: 'draw', drawReason: 'threefold' }, 'white')).toBe('Draw — repetition');
    expect(resultCopy({ reason: 'draw', drawReason: 'fifty-move' }, 'white')).toBe('Draw — 50-move rule');
    expect(resultCopy({ reason: 'draw', drawReason: 'insufficient-material' }, 'white')).toBe(
      'Draw — insufficient material',
    );
    expect(resultCopy({ reason: 'draw', drawReason: 'agreement' }, 'white')).toBe('Draw — by agreement');
  });
});

describe('resultCopy — persona-named bot-actor copy (Phase 183, D-06)', () => {
  const PERSONA_NAME = 'Riko the Raccoon';

  it('substitutes the persona name into the bot-actor checkmate-loss copy', () => {
    const lost: BotGameOutcome = { reason: 'checkmate', winner: 'black' };
    expect(resultCopy(lost, 'white', PERSONA_NAME)).toBe('Riko the Raccoon wins — checkmate');
  });

  it('substitutes the persona name into the bot-actor timeout-loss copy', () => {
    const lost: BotGameOutcome = { reason: 'timeout', winner: 'black' };
    expect(resultCopy(lost, 'white', PERSONA_NAME)).toBe('Riko the Raccoon wins on time');
  });

  it('substitutes the persona name into the (D-03-unreachable) bot-resigned win copy', () => {
    const opponentResigned: BotGameOutcome = { reason: 'resignation', winner: 'white' };
    expect(resultCopy(opponentResigned, 'white', PERSONA_NAME)).toBe(
      'You won — Riko the Raccoon resigned',
    );
  });

  it('leaves the user-actor copy (a user win, or the user resigning) UNCHANGED even with a persona name', () => {
    const won: BotGameOutcome = { reason: 'checkmate', winner: 'white' };
    expect(resultCopy(won, 'white', PERSONA_NAME)).toBe('You won — checkmate');

    const wonOnTime: BotGameOutcome = { reason: 'timeout', winner: 'white' };
    expect(resultCopy(wonOnTime, 'white', PERSONA_NAME)).toBe('You won on time');

    const userResigned: BotGameOutcome = { reason: 'resignation', winner: 'black' };
    expect(resultCopy(userResigned, 'white', PERSONA_NAME)).toBe('You resigned');
  });

  it('leaves every draw branch UNCHANGED even with a persona name (no actor)', () => {
    expect(resultCopy({ reason: 'draw', drawReason: 'stalemate' }, 'white', PERSONA_NAME)).toBe(
      'Draw — stalemate',
    );
    expect(resultCopy({ reason: 'draw', drawReason: 'agreement' }, 'white', PERSONA_NAME)).toBe(
      'Draw — by agreement',
    );
  });

  it('returns the exact pre-183 generic strings when personaName is omitted/null/undefined (Custom game)', () => {
    const lost: BotGameOutcome = { reason: 'checkmate', winner: 'black' };
    expect(resultCopy(lost, 'white')).toBe('You lost — checkmate');
    expect(resultCopy(lost, 'white', null)).toBe('You lost — checkmate');
    expect(resultCopy(lost, 'white', undefined)).toBe('You lost — checkmate');
  });
});
