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
 *
 * D-19 (169, 2026-07-13 gap closure — READ BEFORE RETUNING ANY CONSTANT
 * HERE): the ELO mapping calibrated against this budget was measured with
 * the search ALWAYS running to completion of this exact node budget — the
 * calibration harness (`scripts/calibration-harness.mjs`) has no clock and
 * never cuts a search short (168.5 D-04b). Phase 169's per-move think
 * deadline (`computeThinkDeadlineMs` + `createDeadlineSearch`,
 * chessClock.ts/deadlineSearch.ts) can now abort a live game's search before
 * it reaches `FLAWCHESS_BOT_MAX_NODES` when the bot is low on its own clock.
 * A deadline-cut bot therefore plays MATERIALLY WEAKER than its advertised
 * ELO for that move — this is accepted and intended (humans get worse in
 * time trouble too), not a bug to "fix" by loosening the deadline or
 * shrinking these constants. Do not read calibration-harness numbers as
 * whole-game strength for a live, clocked bot game — they describe this
 * budget at FULL completion only.
 *
 * Phase 225 (SEED-170 item 1, D-01/D-02): the clear-winner stop compared a
 * boosted top root child (already visited, its value backed up through at
 * least one of its own children) against an unboosted, never-visited
 * runner-up — the runner-up's first expansion can raise its value by the
 * opponent's expected error, and the OLD unguarded rule could stop before
 * that boost ever had a chance to land. `rootGuardBoostAllowance` below
 * sizes a value-gap window around the top child within which an unvisited,
 * non-closed root child now blocks the clear-winner stop until it settles.
 * Deliberately left unguarded, per CONTEXT.md: the near-tie-flatness branch
 * (D-03 — stopping on a near-tie is low-stakes) and the wall-clock deadline
 * cut in `deadlineSearch.ts` (D-04 — guarding it could overrun the bot's own
 * clock and make it flag; a deadline-cut bot is already documented above as
 * intentionally weaker).
 */

import type { BotStopRule, DispatchMode } from './types';

/** Node-expansion budget for bot play (D-07: ~15s worst-case move target). Locked 168.5-04 from measurement. */
export const FLAWCHESS_BOT_MAX_NODES = 50;

/** Search-tree ply depth cap for bot play — unchanged from the analysis default (D-07, Claude's-discretion "keep"). Locked 168.5-04 from measurement. */
export const FLAWCHESS_BOT_MAX_PLIES = 8;

/** Pinned bot-play search concurrency (D-09) — the analysis board keeps device-adaptive `computePoolSize()`; bot play uses one fixed constant so app and harness run the same search shape (exactly reproducible in round mode; continuous dispatch, shipped in Phase 227, varies with timing). Locked 168.5-04 from measurement. */
export const FLAWCHESS_BOT_CONCURRENCY = 4;

/**
 * Phase 227 D-13: the dispatch loop `mctsSearch` runs for BOTH app callers
 * (`useBotGame`'s bot budget and `useFlawChessEngine`'s analysis budget) and
 * for every harness script (`scripts/lib/dispatch-mode.mjs`'s
 * `defaultDispatchMode()`). The single definition, same app == harness
 * pattern as the constants above (T-168.5-04-01): a one-sided flip is
 * structurally impossible. Flipped to `'continuous'` on the owner's ship
 * decision from the Phase 227 verdict
 * (`reports/continuous-dispatch-227/owner-decision.md`); rollback is
 * flipping it back to `'round'` (L-5).
 */
export const FLAWCHESS_DISPATCH_MODE: DispatchMode = 'continuous';

/** Two-sided early-stop rule for bot play (D-05/D-06): clear-winner OR near-tie-flatness, gated by a shared min-nodes floor. Locked 168.5-04 from measurement. */
export const FLAWCHESS_BOT_STOP_RULE: BotStopRule = {
  marginThreshold: 0.05,
  epsilonThreshold: 0.02,
  stabilityWindow: 3,
  minNodes: 8,
  // Phase 225 D-02: pooled p90 of root-child first-expansion value change
  // (post minus pre, at the expansion where that child's visits flip 0->1)
  // across the stop-rule harness's 16-position set at ELO 1300/1500/1900/
  // 2300, rounded up to 0.01 (METHOD measured, not the 0.10 fallback — see
  // reports/engine-search-fixes-225/d02-allowance.md for the full method,
  // per-ELO table, and caveats).
  rootGuardBoostAllowance: 0.04,
};
