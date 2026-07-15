import { describe, it, expect } from 'vitest';
import {
  buildAnalysisLineUrl,
  parseAnalysisLineParam,
  buildGameAnalysisUrl,
  buildAnalysisFenUrl,
  parseAnalysisFenParam,
  parseAnalysisOrientationParam,
} from './analysisUrl';

describe('buildAnalysisLineUrl', () => {
  it('returns the bare /analysis path for an empty move list', () => {
    expect(buildAnalysisLineUrl([])).toBe('/analysis');
  });

  it('encodes a SAN line as a comma-separated UCI ?line= param', () => {
    const result = buildAnalysisLineUrl(['e4', 'e5', 'Nf3', 'Nc6']);
    expect(result).toBe('/analysis?line=e2e4,e7e5,g1f3,b8c6');
  });

  it('emits URL-safe tokens (no query-breaking characters, unlike a raw FEN)', () => {
    const value = buildAnalysisLineUrl(['e4', 'e5', 'Nf3']).split('line=')[1];
    expect(value).toBeDefined();
    // Comma is a legal query separator; the tokens themselves carry no space,
    // '/', '?', '#', '&' or '=' that would need encodeURIComponent.
    expect(value!).not.toMatch(/[ /?#&=]/);
  });

  it('encodes castling as a king move (e1g1)', () => {
    const result = buildAnalysisLineUrl(['e4', 'e5', 'Nf3', 'Nc6', 'Bc4', 'Bc5', 'O-O']);
    expect(result.endsWith('e1g1')).toBe(true);
  });

  it('stops at the first illegal SAN', () => {
    const result = buildAnalysisLineUrl(['e4', 'totally-illegal', 'e5']);
    expect(result).toBe('/analysis?line=e2e4');
  });

  it('appends &orientation=black when an orientation arg is passed', () => {
    const result = buildAnalysisLineUrl(['e4', 'e5'], 'black');
    expect(result).toBe('/analysis?line=e2e4,e7e5&orientation=black');
  });

  it('emits an explicit &orientation=white (not elided)', () => {
    const result = buildAnalysisLineUrl(['e4'], 'white');
    expect(result).toBe('/analysis?line=e2e4&orientation=white');
  });

  it('survives an empty move list, becoming the only param', () => {
    const result = buildAnalysisLineUrl([], 'black');
    expect(result).toBe('/analysis?orientation=black');
  });
});

describe('parseAnalysisLineParam', () => {
  it('returns [] for null', () => {
    expect(parseAnalysisLineParam(null)).toEqual([]);
  });

  it('returns [] for an empty string', () => {
    expect(parseAnalysisLineParam('')).toEqual([]);
  });

  it('parses UCI tokens back to SAN', () => {
    expect(parseAnalysisLineParam('e2e4,e7e5,g1f3,b8c6')).toEqual(['e4', 'e5', 'Nf3', 'Nc6']);
  });

  it('round-trips with buildAnalysisLineUrl', () => {
    const sans = ['e4', 'c5', 'Nf3', 'd6', 'd4', 'cxd4'];
    const url = buildAnalysisLineUrl(sans);
    const lineParam = url.split('line=')[1] ?? null;
    expect(parseAnalysisLineParam(lineParam)).toEqual(sans);
  });

  it('handles a promotion token (b7a8q)', () => {
    // Legal line reaching a promotion (white a-pawn marches, captures on b7,
    // then promotes on a8 capturing the rook). Confirms the promotion suffix
    // parses through to a SAN promotion move.
    const sans = parseAnalysisLineParam('a2a4,b8c6,a4a5,c6b8,a5a6,b8c6,a6b7,c6b8,b7a8q');
    expect(sans[sans.length - 1]).toBe('bxa8=Q');
  });

  it('keeps the legal prefix and stops at the first illegal token', () => {
    expect(parseAnalysisLineParam('e2e4,e7e5,zzzz')).toEqual(['e4', 'e5']);
  });

  it('stops on a malformed (too-short) token', () => {
    expect(parseAnalysisLineParam('e2e4,e7')).toEqual(['e4']);
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

describe('buildAnalysisFenUrl', () => {
  it('starts with /analysis?fen=', () => {
    const result = buildAnalysisFenUrl('rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1');
    expect(result.startsWith('/analysis?fen=')).toBe(true);
  });

  it('encodeURIComponent-encodes a mid-game FEN (space -> %20, / -> %2F)', () => {
    const fen = '3r2k1/p5pp/1p1Np1q1/2pRP3/5P2/P3n1PP/1PP3Q1/3R3K w - - 1 28';
    const result = buildAnalysisFenUrl(fen);
    const value = result.split('fen=')[1];
    expect(value).toBeDefined();
    expect(value).not.toMatch(/[ /]/);
    expect(value).toContain('%20');
    expect(value).toContain('%2F');
  });
});

describe('parseAnalysisFenParam', () => {
  it('returns null for null', () => {
    expect(parseAnalysisFenParam(null)).toBeNull();
  });

  it('returns null for an empty string', () => {
    expect(parseAnalysisFenParam('')).toBeNull();
  });

  it('returns null for garbage input', () => {
    expect(parseAnalysisFenParam('not-a-fen')).toBeNull();
  });

  // Regression (CR-01): a stray `%` makes decodeURIComponent throw URIError.
  // The guard must catch it and return null, not crash the board render.
  it('returns null for a malformed percent-escape', () => {
    expect(parseAnalysisFenParam('50%')).toBeNull();
    expect(parseAnalysisFenParam('%')).toBeNull();
  });

  it('round-trips a mid-game full FEN with buildAnalysisFenUrl', () => {
    const fen = '3r2k1/p5pp/1p1Np1q1/2pRP3/5P2/P3n1PP/1PP3Q1/3R3K w - - 1 28';
    const url = buildAnalysisFenUrl(fen);
    const fenParam = new URLSearchParams(url.split('?')[1]).get('fen');
    expect(parseAnalysisFenParam(fenParam)).toBe(fen);
  });
});

describe('parseAnalysisOrientationParam', () => {
  it('returns "white" for "white"', () => {
    expect(parseAnalysisOrientationParam('white')).toBe('white');
  });

  it('returns "black" for "black"', () => {
    expect(parseAnalysisOrientationParam('black')).toBe('black');
  });

  it('returns null for null', () => {
    expect(parseAnalysisOrientationParam(null)).toBeNull();
  });

  it('returns null for an empty string', () => {
    expect(parseAnalysisOrientationParam('')).toBeNull();
  });

  it('returns null for garbage input', () => {
    expect(parseAnalysisOrientationParam('sideways')).toBeNull();
  });

  it('is a strict lowercase allowlist (mixed case rejected)', () => {
    expect(parseAnalysisOrientationParam('WHITE')).toBeNull();
  });

  it('never throws on a malformed percent-escape', () => {
    expect(parseAnalysisOrientationParam('%')).toBeNull();
  });

  it('round-trips with buildAnalysisLineUrl via URLSearchParams', () => {
    const url = buildAnalysisLineUrl(['e4', 'e5'], 'black');
    const orientationParam = new URLSearchParams(url.split('?')[1]).get('orientation');
    expect(parseAnalysisOrientationParam(orientationParam)).toBe('black');
  });
});
