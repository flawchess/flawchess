/**
 * rootSplit.ts unit tests (Phase 226 D-18/L-2/L-3).
 *
 * Covers the pure partition/merge helpers that underlie the root grade
 * split: `partitionCandidates` (round-robin sharding) and `mergeShardGrades`
 * (order-preserving, no-fabrication merge). Edge cases (k > n, k <= 0, k ===
 * n, n === 1, empty input, missing/duplicate candidates) and mutation checks
 * land in Plan 226-10 Task 2.
 */

import { describe, it, expect } from 'vitest';
import { partitionCandidates, mergeShardGrades, ROOT_SPLIT_MAX_SHARDS } from '../rootSplit';
import type { MoveGrade } from '../types';

/** Ten candidates in a fixed, deliberately non-alphabetical order — matches the shape `truncateAndRenormalize` would produce (highest-probability first). */
const TEN_CANDIDATES = ['e2e4', 'd2d4', 'g1f3', 'c2c4', 'b1c3', 'e2e3', 'f2f4', 'a2a4', 'g2g3', 'h2h4'];

function makeGrade(evalCp: number): MoveGrade {
  return { evalCp, evalMate: null, depth: 14 };
}

describe('partitionCandidates', () => {
  it('splits 10 candidates into 4 round-robin shards that disjointly cover the input in i % k order', () => {
    const shards = partitionCandidates(TEN_CANDIDATES, 4);

    expect(shards).toHaveLength(4);
    // Round-robin: candidate i -> shard i % 4.
    expect(shards[0]).toEqual(['e2e4', 'b1c3', 'g2g3']); // indices 0, 4, 8
    expect(shards[1]).toEqual(['d2d4', 'e2e3', 'h2h4']); // indices 1, 5, 9
    expect(shards[2]).toEqual(['g1f3', 'f2f4']); // indices 2, 6
    expect(shards[3]).toEqual(['c2c4', 'a2a4']); // indices 3, 7

    // Disjoint cover: every shard's members are pairwise distinct across
    // shards, and their union (regardless of order) is exactly the input set.
    const seen = new Set<string>();
    for (const shard of shards) {
      for (const uci of shard) {
        expect(seen.has(uci)).toBe(false);
        seen.add(uci);
      }
    }
    expect(seen).toEqual(new Set(TEN_CANDIDATES));
  });

  it('clamps shardCount ABOVE candidateUcis.length down to n singleton shards', () => {
    const shards = partitionCandidates(['a', 'b', 'c'], 20);
    expect(shards).toEqual([['a'], ['b'], ['c']]);
  });

  it('clamps shardCount 0 up to one shard holding everything', () => {
    const shards = partitionCandidates(['a', 'b', 'c'], 0);
    expect(shards).toEqual([['a', 'b', 'c']]);
  });

  it('clamps a negative shardCount up to one shard holding everything', () => {
    const shards = partitionCandidates(['a', 'b', 'c'], -5);
    expect(shards).toEqual([['a', 'b', 'c']]);
  });

  it('k === n gives n singleton shards, one candidate each', () => {
    const shards = partitionCandidates(['a', 'b', 'c', 'd'], 4);
    expect(shards).toEqual([['a'], ['b'], ['c'], ['d']]);
  });

  it('a single candidate (n === 1) always returns one singleton shard regardless of shardCount', () => {
    expect(partitionCandidates(['a'], 4)).toEqual([['a']]);
    expect(partitionCandidates(['a'], 1)).toEqual([['a']]);
  });

  it('empty candidateUcis returns exactly one empty shard, regardless of shardCount', () => {
    expect(partitionCandidates([], 4)).toEqual([[]]);
    expect(partitionCandidates([], 0)).toEqual([[]]);
  });
});

describe('mergeShardGrades', () => {
  it('restores original candidate order across shards that each hold a disjoint subset', () => {
    const shards = partitionCandidates(TEN_CANDIDATES, 4);
    const grades = new Map<string, MoveGrade>(TEN_CANDIDATES.map((uci, i) => [uci, makeGrade(i * 10)]));
    const shardMaps = shards.map((shard) => new Map(shard.map((uci) => [uci, grades.get(uci)!])));

    const merged = mergeShardGrades(TEN_CANDIDATES, shardMaps);

    expect([...merged.keys()]).toEqual(TEN_CANDIDATES);
    for (const uci of TEN_CANDIDATES) {
      expect(merged.get(uci)).toEqual(grades.get(uci));
    }
  });

  it('a candidate missing from every shard is absent from the result — never fabricated (L-2)', () => {
    const shards = [new Map([['a', makeGrade(10)]]), new Map([['c', makeGrade(30)]])];

    const merged = mergeShardGrades(['a', 'b', 'c'], shards);

    expect(merged.has('b')).toBe(false);
    expect([...merged.keys()]).toEqual(['a', 'c']);
  });

  it('a candidate present in more than one shard takes the FIRST shard\'s grade', () => {
    const firstShardGrade = makeGrade(111);
    const secondShardGrade = makeGrade(999);
    const shards = [new Map([['a', firstShardGrade]]), new Map([['a', secondShardGrade]])];

    const merged = mergeShardGrades(['a'], shards);

    expect(merged.get('a')).toEqual(firstShardGrade);
  });
});

describe('ROOT_SPLIT_MAX_SHARDS', () => {
  it('is a positive integer (the desktop pool ceiling)', () => {
    expect(Number.isInteger(ROOT_SPLIT_MAX_SHARDS)).toBe(true);
    expect(ROOT_SPLIT_MAX_SHARDS).toBeGreaterThan(0);
  });
});
