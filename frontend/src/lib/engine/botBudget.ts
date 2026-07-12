/**
 * botBudget — the shipped bot-play search-budget profile (Phase 168.5
 * D-05/D-07/D-09), the SINGLE definition shared by the app and the
 * calibration harness.
 *
 * Deliberately dependency-light (a types-only import — no React/Sentry/
 * Worker modules) so `scripts/calibration-harness.mjs` can import it
 * directly through its `@/` alias hook. One definition, zero hand-maintained
 * mirrors: a one-sided retune desyncing the shipped bot from the calibrated
 * one (T-168.5-04-01's failure mode) is structurally impossible.
 * `useFlawChessEngine.ts` re-exports these for app callers (Phase 169's
 * `useBotGame`).
 *
 * Locked 168.5-04 from measurement: a standalone probe (hand-built
 * SearchBudget carrying stopRule + pinned concurrency, run directly against
 * mctsSearch with the real Stockfish pool + Maia session) measured 8
 * positions spanning near-tie openings, a clear-winner tactical position,
 * and two genuinely contested/balanced middlegames. Result: median ~5.4s,
 * worst-case ~12.7s (both genuinely-contested positions ran to the full
 * maxNodes budget without ever satisfying the stop rule — the two-sided
 * rule correctly separates "settled" from "contested" positions) — within
 * the D-07/D-17 target band (median ~5s, worst-case ~15s, pass band 3-8s
 * median/p95<=20s). See 168.5-04-SUMMARY.md for the full measurement record.
 */

import type { BotStopRule } from './types';

/** Node-expansion budget for bot play (D-07: ~15s worst-case move target). Locked 168.5-04 from measurement. */
export const FLAWCHESS_BOT_MAX_NODES = 50;

/** Search-tree ply depth cap for bot play — unchanged from the analysis default (D-07, Claude's-discretion "keep"). Locked 168.5-04 from measurement. */
export const FLAWCHESS_BOT_MAX_PLIES = 8;

/** Pinned bot-play search concurrency (D-09) — the analysis board keeps device-adaptive `computePoolSize()`; bot play uses one fixed constant so app == harness determinism holds exactly. Locked 168.5-04 from measurement. */
export const FLAWCHESS_BOT_CONCURRENCY = 4;

/** Two-sided early-stop rule for bot play (D-05/D-06): clear-winner OR near-tie-flatness, gated by a shared min-nodes floor. Locked 168.5-04 from measurement. */
export const FLAWCHESS_BOT_STOP_RULE: BotStopRule = {
  marginThreshold: 0.05,
  epsilonThreshold: 0.02,
  stabilityWindow: 3,
  minNodes: 8,
};
