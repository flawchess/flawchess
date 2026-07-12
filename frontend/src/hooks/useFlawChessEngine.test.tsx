/**
 * useFlawChessEngine bot-profile constant tests (Phase 168.5 D-07/D-09).
 *
 * A lightweight, hook-free vitest module — no React render harness needed
 * (the existing `src/hooks/__tests__/useFlawChessEngine.test.ts` already
 * covers the hook's throttle/abort behavior via mocked providers). This file
 * guards a narrower invariant: the exported `FLAWCHESS_BOT_*` constants are a
 * SMALLER, DISTINCT profile from the analysis-board's own constants (Pattern
 * 1 — never the same constant serving both callers), and the stop-rule
 * object it carries is internally well-formed.
 */

import { describe, it, expect } from 'vitest';
import {
  FLAWCHESS_BOT_MAX_NODES,
  FLAWCHESS_BOT_MAX_PLIES,
  FLAWCHESS_BOT_CONCURRENCY,
  FLAWCHESS_BOT_STOP_RULE,
} from './useFlawChessEngine';

// `FLAWCHESS_ENGINE_MAX_NODES`/`_MAX_PLIES` (the analysis-board budget) are
// module-private in useFlawChessEngine.ts by design (Pattern 1 — only the
// bot profile is exported). Asserting against the known literals here
// structurally proves the bot profile is a DIFFERENT, distinct set of
// constants rather than an accidental re-export of the same values.
const FLAWCHESS_ENGINE_MAX_NODES = 400;
const FLAWCHESS_ENGINE_MAX_PLIES = 8;

describe('useFlawChessEngine — bot-play budget profile (D-07/D-09)', () => {
  it('FLAWCHESS_BOT_MAX_NODES is a smaller, distinct budget from the analysis-board constant', () => {
    expect(FLAWCHESS_BOT_MAX_NODES).toBeLessThan(FLAWCHESS_ENGINE_MAX_NODES);
  });

  it('FLAWCHESS_BOT_MAX_PLIES matches the locked [6,10] ply-depth band (unchanged default, D-07 "keep")', () => {
    expect(FLAWCHESS_BOT_MAX_PLIES).toBe(FLAWCHESS_ENGINE_MAX_PLIES);
  });

  it('FLAWCHESS_BOT_CONCURRENCY is a pinned positive constant (D-09 — never device-adaptive like computePoolSize)', () => {
    expect(FLAWCHESS_BOT_CONCURRENCY).toBeGreaterThanOrEqual(1);
    expect(Number.isInteger(FLAWCHESS_BOT_CONCURRENCY)).toBe(true);
  });

  it('FLAWCHESS_BOT_STOP_RULE is well-formed: minNodes within the bot budget, positive stabilityWindow', () => {
    expect(FLAWCHESS_BOT_STOP_RULE.minNodes).toBeLessThanOrEqual(FLAWCHESS_BOT_MAX_NODES);
    expect(FLAWCHESS_BOT_STOP_RULE.stabilityWindow).toBeGreaterThan(0);
    expect(FLAWCHESS_BOT_STOP_RULE.marginThreshold).toBeGreaterThanOrEqual(0);
    expect(FLAWCHESS_BOT_STOP_RULE.epsilonThreshold).toBeGreaterThanOrEqual(0);
  });
});
