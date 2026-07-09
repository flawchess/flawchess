import { describe, expect, it } from 'vitest';
import { formatPlayerPovEval } from '@/lib/playerPovEval';

describe('formatPlayerPovEval — re-signs a white-POV eval to the mover frame', () => {
  it('white mover keeps a mate-for-white sign: +M4 -> "M4"', () => {
    expect(formatPlayerPovEval(null, 4, 'white')).toBe('M4');
  });

  it('black mover flips a mate-for-white eval: +M4 -> "-M4" (being mated)', () => {
    expect(formatPlayerPovEval(null, 4, 'black')).toBe('-M4');
  });

  it('black mover flips a positive white-POV cp eval: +250 -> "-2.5"', () => {
    expect(formatPlayerPovEval(250, null, 'black')).toBe('-2.5');
  });

  it('black mover flips a negative white-POV cp eval: -120 -> "+1.2"', () => {
    expect(formatPlayerPovEval(-120, null, 'black')).toBe('+1.2');
  });

  it('white mover keeps a positive white-POV cp eval unchanged: +120 -> "+1.2"', () => {
    expect(formatPlayerPovEval(120, null, 'white')).toBe('+1.2');
  });

  it('white mover keeps a negative white-POV cp eval unchanged: -250 -> "-2.5"', () => {
    expect(formatPlayerPovEval(-250, null, 'white')).toBe('-2.5');
  });

  it('black mover flips a mate-against-white eval to mate-for-black: -M2 -> "M2"', () => {
    expect(formatPlayerPovEval(null, -2, 'black')).toBe('M2');
  });

  it('null/null -> em dash, for either mover', () => {
    expect(formatPlayerPovEval(null, null, 'white')).toBe('—');
    expect(formatPlayerPovEval(null, null, 'black')).toBe('—');
  });
});
