import { describe, it, expect } from 'vitest';
import {
  buildAnalysisLineUrl,
  parseAnalysisLineParam,
  buildGameAnalysisUrl,
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
