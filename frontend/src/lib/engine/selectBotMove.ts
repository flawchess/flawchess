/**
 * selectBotMove — the pure, provider-agnostic bot move-selection orchestrator.
 * Given a position and (ELO, blend) settings, resolves to a
 * legal UCI move at the bot's configured strength. Both the play loop
 * and the calibration harness import and run this
 * function unchanged via the `@/` alias.
 *
 * `settings.elo` is the bot's ONLY strength input — the
 * signature intentionally has NO player-rating slot. `budget.elo` is always
 * built symmetrically as `{ w: elo, b: elo }` regardless of any other input,
 * so the bot can never adapt to the player by construction (a future call
 * site threading a second, player-derived ELO into this function would be a
 * regression, not a feature).
 *
 * Regime dispatch:
 *   - `blend <= 0` (full-human): exactly ONE `deps.policy()` call, sampling
 *     the raw Maia root policy. Never calls `deps.search`/`mctsSearch`.
 *   - `blend >= 1` (full-stockfish): runs `deps.search ?? mctsSearch` once,
 *     then returns the deterministic argmax over `RankedLine.practicalScore`
 *     (ignoring `mctsSearch`'s own findability-weighted sort order).
 *   - `0 < blend < 1`: same search call, then softmax-samples over
 *     `practicalScore` at `tau = TAU_MAX * (1 - blend)`; a `tau`
 *     at or below `TAU_EPSILON` short-circuits to argmax to avoid a
 *     near-zero-tau numerical edge case.
 *
 * Locked, do not revisit: the analysis board's `applyPolicyTemperature`
 * transform is NEVER used here — its "flatten = more engine-like" polarity is
 * an artifact of the analysis *ranking* pipeline (where Stockfish grading
 * rescues the surfaced move); in this raw-sampling path there is no rescue,
 * so using it here would make the bot noisier/weaker, not more engine-like,
 * and would break the bot's calibration curve.
 *
 * This file holds ONLY the impure orchestration (one `policy()` or one
 * `search()` call, plus regime branching) — every actual sampling/argmax/
 * fallback decision lives in `botSampling.ts`'s pure, sync, separately-
 * exported helpers. There is no try/catch here: degeneracy is signaled
 * solely by a helper returning `null`, handled uniformly at every
 * `?? fallbackMove(...)` call site below (never duplicated per-branch).
 */

import type { EngineProviders, SearchBudget, RankedLine } from './types';
import type { SearchRunner } from './guardrail';
import { mctsSearch } from './mctsSearch';
import { samplePolicy, sampleRankedLines, argmaxLine, fallbackMove } from './botSampling';
import { applyStylePriorReweighting, applyStyleScoreShaping, type BotStyleParams } from './botStyle';

/** Linear τ(b) = TAU_MAX * (1 - b) softmax-sharpness curve ceiling. */
export const TAU_MAX = 0.1;

/**
 * Argmax short-circuit threshold (Claude's discretion) — when `tau` computed
 * from `settings.blend` is at or below this value, skip the softmax path
 * entirely and go straight to `argmaxLine`. Safe even without this guard
 * (`sampleRankedLines` already uses max-subtraction stability), but this
 * avoids computing a needless near-zero-tau softmax at the `blend -> 1`
 * boundary.
 */
export const TAU_EPSILON = 1e-9;

/** The bot's own play settings — see the module header for the symmetric-ELO invariant. */
export interface BotSettings {
  /** The bot's own ELO — never the player's rating. */
  elo: number;
  /**
   * b in [0,1]: 0 = full-human (raw Maia sample), 1 = full-stockfish (argmax
   * practicalScore). Out-of-domain values are clamped into [0,1]; a NaN
   * blend maps to 1 (deterministic argmax) — see the clamp in `selectBotMove`.
   */
  blend: number;
  /**
   * Caller-supplied search bounds (derived from the clock);
   * `elo` is set here, not by the caller. `policyTemperature` is excluded by
   * type so the no-analysis-temperature invariant is structural: a future call site
   * reusing the analysis board's budget helper (which sets it) is a compile
   * error, not a silent pass-through into the bot's search budget.
   */
  budget: Omit<SearchBudget, 'elo' | 'policyTemperature'>;
  /**
   * Optional style layer — a NEW field kept SEPARATE
   * from `budget` (deliberately not folded into the `Omit<>` above, so the
   * `policyTemperature` exclusion stays structural). `undefined`
   * runs today's exact code path with no reweight/shaping call — this
   * is both the calibration baseline and the Custom-mode default. When
   * present, it hooks two disjoint regime branches on disjoint data shapes
   * (never merged into one call):
   *   - `blend<=0`: `applyStylePriorReweighting` runs between
   *     `deps.policy()` and `samplePolicy`.
   *   - the search branch: `applyStyleScoreShaping` runs between `search()`
   *     and `argmaxLine`/`sampleRankedLines`.
   */
  style?: BotStyleParams;
}

/** Injected providers + RNG so this module stays provider-agnostic. */
export interface BotMoveDeps extends EngineProviders {
  /** [0,1) — the ONLY source of randomness `selectBotMove` uses. */
  rng: () => number;
  /** Defaults to `mctsSearch` — injectable so tests/harness can stub the search. */
  search?: SearchRunner;
}

/** Never aborts — the default when the caller omits `signal`. */
const NEVER_ABORT_SIGNAL = new AbortController().signal;

/**
 * Resolves to a legal UCI move for `fen` at the bot's configured
 * `settings.elo`/`settings.blend` strength, using `deps` for policy/search
 * providers and randomness. See the module header for the full regime
 * dispatch and the invariants this function structurally enforces.
 */
export async function selectBotMove(
  fen: string,
  settings: BotSettings,
  deps: BotMoveDeps,
  signal: AbortSignal = NEVER_ABORT_SIGNAL,
): Promise<string> {
  const side = fen.split(' ')[1] === 'b' ? 'b' : 'w';

  // blend is documented [0,1] but settings are caller-trusted — a NaN blend
  // fails every regime check below (all NaN comparisons are false) and would
  // previously flow into sampleRankedLines with tau = NaN, silently degrading
  // move selection. Clamp to the domain; NaN (the one value
  // Math.min/Math.max cannot clamp) maps to 1, the deterministic argmax
  // regime — the least surprising strength for a corrupted setting.
  const blend = Number.isFinite(settings.blend) ? Math.min(1, Math.max(0, settings.blend)) : 1;

  if (blend <= 0) {
    // Exactly ONE policy() call, no MCTS.
    const rawPolicy = await deps.policy(fen, settings.elo, side);
    // Undefined style leaves rawPolicy untouched — byte-
    // identical to the unstyled code path.
    const styledPolicy = settings.style
      ? applyStylePriorReweighting(rawPolicy, fen, settings.style)
      : rawPolicy;
    const sampled = samplePolicy(styledPolicy, deps.rng);
    return sampled ?? fallbackMove(fen, deps.rng);
  }

  const search = deps.search ?? mctsSearch;
  const budget: SearchBudget = {
    ...settings.budget,
    // Symmetric ELO — the bot never adapts to the player.
    // policyTemperature is excluded from BotSettings.budget by type,
    // so the spread can never thread it into the search budget.
    elo: { w: settings.elo, b: settings.elo },
  };
  // No-op onSnapshot: selectBotMove never streams intermediate snapshots
  // (mctsSearch's SearchRunner requires a real function, never
  // undefined).
  const snapshot = await search(fen, budget, deps, () => {}, signal);
  // Undefined style leaves snapshot.rankedLines untouched —
  // byte-identical to the unstyled code path.
  const lines: RankedLine[] = settings.style
    ? applyStyleScoreShaping(snapshot.rankedLines, settings.style)
    : snapshot.rankedLines;

  if (blend >= 1) {
    // Deterministic argmax over practicalScore, UCI-ascending tie-break.
    const best = argmaxLine(lines);
    return best ?? fallbackMove(fen, deps.rng);
  }

  const tau = TAU_MAX * (1 - blend);
  if (tau <= TAU_EPSILON) {
    const best = argmaxLine(lines);
    return best ?? fallbackMove(fen, deps.rng);
  }
  const sampled = sampleRankedLines(lines, tau, deps.rng);
  return sampled ?? fallbackMove(fen, deps.rng);
}
