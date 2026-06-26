import { describe, it, expect } from 'vitest';
import { buildAnalysisUrl } from './analysisUrl';

const STARTING_FEN = 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1';

describe('buildAnalysisUrl', () => {
  it('returns /analysis?fen= + encodeURIComponent(fen) for the starting position', () => {
    const result = buildAnalysisUrl(STARTING_FEN);
    expect(result).toBe(`/analysis?fen=${encodeURIComponent(STARTING_FEN)}`);
  });

  it('encodes spaces as %20 in the output', () => {
    const result = buildAnalysisUrl(STARTING_FEN);
    const afterFenParam = result.split('fen=')[1];
    expect(afterFenParam).toBeDefined();
    expect(afterFenParam).toContain('%20');
    expect(afterFenParam).not.toContain(' ');
  });

  it('encodes slashes as %2F in the output', () => {
    const result = buildAnalysisUrl(STARTING_FEN);
    const afterFenParam = result.split('fen=')[1];
    expect(afterFenParam).toBeDefined();
    expect(afterFenParam).toContain('%2F');
  });

  it('starts with /analysis?fen=', () => {
    const result = buildAnalysisUrl(STARTING_FEN);
    expect(result.startsWith('/analysis?fen=')).toBe(true);
  });
});
