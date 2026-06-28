import { describe, it, expect } from 'vitest';
import { buildAnalysisUrl, buildGameAnalysisUrl } from './analysisUrl';

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

describe('buildGameAnalysisUrl', () => {
  it('returns /analysis?game_id={id}&ply={ply}', () => {
    const result = buildGameAnalysisUrl(42, 10);
    expect(result).toBe('/analysis?game_id=42&ply=10');
  });

  it('starts with /analysis?game_id=', () => {
    expect(buildGameAnalysisUrl(1, 0).startsWith('/analysis?game_id=')).toBe(true);
  });

  it('keeps an explicit ply of 0 as a param', () => {
    expect(buildGameAnalysisUrl(7, 0)).toBe('/analysis?game_id=7&ply=0');
  });

  it('omits the ply param when ply is null (opens the game at ply 0)', () => {
    expect(buildGameAnalysisUrl(42, null)).toBe('/analysis?game_id=42');
  });

  it('omits the ply param when ply is undefined', () => {
    expect(buildGameAnalysisUrl(42)).toBe('/analysis?game_id=42');
  });
});
