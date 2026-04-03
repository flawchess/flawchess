import { describe, it, expect } from 'vitest';
import { Chess } from 'chess.js';
import { computeHashes, hashToString } from './zobrist';

/**
 * Known test vectors verified against the Python backend:
 *   uv run python -c "
 *     import chess, chess.polyglot
 *     from app.services.zobrist import _color_hash
 *     b = chess.Board()
 *     print('start white:', _color_hash(b, chess.WHITE))
 *     print('start black:', _color_hash(b, chess.BLACK))
 *     print('start full:', chess.polyglot.zobrist_hash(b))
 *   "
 */
describe('computeHashes', () => {
  // ── Starting position ─────────────────────────────────────────────────────
  it('returns correct whiteHash for the starting position', () => {
    const chess = new Chess();
    const { whiteHash } = computeHashes(chess);
    expect(whiteHash).toBe(5858837776588196015n);
  });

  it('returns correct blackHash for the starting position', () => {
    const chess = new Chess();
    const { blackHash } = computeHashes(chess);
    expect(blackHash).toBe(-3976252316203442281n);
  });

  it('returns correct fullHash for the starting position', () => {
    const chess = new Chess();
    const { fullHash } = computeHashes(chess);
    expect(fullHash).toBe(5060803636482931868n);
  });

  // ── After 1.e4 ───────────────────────────────────────────────────────────
  it('returns correct whiteHash after 1.e4 (pawn moved, white hash changes)', () => {
    const chess = new Chess();
    chess.move('e4');
    const { whiteHash } = computeHashes(chess);
    expect(whiteHash).toBe(-6532466553307562974n);
  });

  it('returns unchanged blackHash after 1.e4 (black has not moved)', () => {
    const chess = new Chess();
    chess.move('e4');
    const { blackHash } = computeHashes(chess);
    // Black pieces have not moved — blackHash must equal starting position blackHash
    expect(blackHash).toBe(-3976252316203442281n);
  });

  it('returns correct fullHash after 1.e4', () => {
    const chess = new Chess();
    chess.move('e4');
    const { fullHash } = computeHashes(chess);
    expect(fullHash).toBe(-9062197578030825066n);
  });

  // ── After 1.e4 e5 ────────────────────────────────────────────────────────
  it('returns unchanged whiteHash after 1.e4 e5 (white did not move on move 1)', () => {
    const chess = new Chess();
    chess.move('e4');
    chess.move('e5');
    const { whiteHash } = computeHashes(chess);
    // White pieces have not changed since 1.e4 — whiteHash stays the same
    expect(whiteHash).toBe(-6532466553307562974n);
  });

  it('returns correct blackHash after 1.e4 e5 (black pawn moved)', () => {
    const chess = new Chess();
    chess.move('e4');
    chess.move('e5');
    const { blackHash } = computeHashes(chess);
    expect(blackHash).toBe(1839718147647814041n);
  });

  it('returns correct fullHash after 1.e4 e5', () => {
    const chess = new Chess();
    chess.move('e4');
    chess.move('e5');
    const { fullHash } = computeHashes(chess);
    expect(fullHash).toBe(595762792459712928n);
  });

  // ── Invariant: color hashes are independent ────────────────────────────────
  it('whiteHash is independent of black piece positions', () => {
    // After 1.e4, only white moved; blackHash must match starting position value
    const start = new Chess();
    const afterE4 = new Chess();
    afterE4.move('e4');
    expect(computeHashes(afterE4).blackHash).toBe(computeHashes(start).blackHash);
  });

  it('blackHash is independent of white piece positions', () => {
    // After 1.e4 e5, only black moved on move 1; whiteHash must not have changed from after 1.e4
    const afterE4 = new Chess();
    afterE4.move('e4');
    const afterE4e5 = new Chess();
    afterE4e5.move('e4');
    afterE4e5.move('e5');
    expect(computeHashes(afterE4e5).whiteHash).toBe(computeHashes(afterE4).whiteHash);
  });
});

describe('hashToString', () => {
  it('converts a positive bigint to its decimal string representation', () => {
    expect(hashToString(5060803636482931868n)).toBe('5060803636482931868');
  });

  it('converts a negative bigint to its decimal string representation', () => {
    expect(hashToString(-9062197578030825066n)).toBe('-9062197578030825066');
  });

  it('converts zero to "0"', () => {
    expect(hashToString(0n)).toBe('0');
  });

  it('converts large positive bigint correctly', () => {
    expect(hashToString(5858837776588196015n)).toBe('5858837776588196015');
  });

  it('converts large negative bigint correctly', () => {
    expect(hashToString(-3976252316203442281n)).toBe('-3976252316203442281');
  });
});
