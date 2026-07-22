/**
 * selectBotMove — the pure, provider-agnostic bot move-selection orchestrator
 * (Phase 166). Given a position and (ELO, blend) settings, resolves to a
 * legal UCI move at the bot's configured strength. Both the play loop
 * (Phase 169) and the calibration harness (Phase 168) import and run this
 * function unchanged via the `@/` alias.
 *
 * D-07/BOT-03: `settings.elo` is the bot's ONLY strength input — the
 * signature intentionally has NO player-rating slot. `budget.elo` is always
 * built symmetrically as `{ w: elo, b: elo }` regardless of any other input,
 * so the bot can never adapt to the player by construction (a future call
 * site threading a second, player-derived ELO into this function would be a
 * regression, not a feature — see 166-RESEARCH.md Pitfall 3).
 *
 * Regime dispatch (D-01/D-03):
 *   - `blend <= 0` (full-human): exactly ONE `deps.policy()` call, sampling
 *     the raw Maia root policy. Never calls `deps.search`/`mctsSearch`
 *     (BOT-02).
 *   - `blend >= 1` (full-stockfish): runs `deps.search ?? mctsSearch` once,
 *     then returns the deterministic argmax over `RankedLine.practicalScore`
 *     (D-06 — ignoring `mctsSearch`'s own findability-weighted sort order).
 *   - `0 < blend < 1`: same search call, then softmax-samples over
 *     `practicalScore` at `tau = TAU_MAX * (1 - blend)` (D-04/D-05); a `tau`
 *     at or below `TAU_EPSILON` short-circuits to argmax to avoid a
 *     near-zero-tau numerical edge case (D-06).
 *
 * D-02 (locked, do not revisit): the analysis board's `applyPolicyTemperature`
 * transform is NEVER used here — its "flatten = more engine-like" polarity is
 * an artifact of the analysis *ranking* pipeline (where Stockfish grading
 * rescues the surfaced move); in this raw-sampling path there is no rescue,
 * so using it here would make the bot noisier/weaker, not more engine-like,
 * and would break Phase 168's calibration curve.
 *
 * D-09: this file holds ONLY the impure orchestration (one `policy()` or one
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

/** D-05: linear τ(b) = TAU_MAX * (1 - b) softmax-sharpness curve ceiling. */
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

/** The bot's own play settings — see the module header for the D-07/BOT-03 invariant. */
export interface BotSettings {
  /** The bot's own ELO (BOT-03) — never the player's rating. */
  elo: number;
  /**
   * b in [0,1]: 0 = full-human (raw Maia sample), 1 = full-stockfish (argmax
   * practicalScore). Out-of-domain values are clamped into [0,1]; a NaN
   * blend maps to 1 (deterministic argmax) — see the clamp in `selectBotMove`.
   */
  blend: number;
  /**
   * Caller-supplied search bounds (Phase 169 derives these from the clock);
   * `elo` is set here, not by the caller. `policyTemperature` is excluded by
   * type (WR-04) so the D-02 invariant is structural: a future call site
   * reusing the analysis board's budget helper (which sets it) is a compile
   * error, not a silent pass-through into the bot's search budget.
   */
  budget: Omit<SearchBudget, 'elo' | 'policyTemperature'>;
  /**
   * Optional style layer (Phase 182, STYLE-05) — a NEW field kept SEPARATE
   * from `budget` (deliberately not folded into the `Omit<>` above, so the
   * D-02/WR-04 `policyTemperature` exclusion stays structural). `undefined`
   * runs today's exact code path with no reweight/shaping call (D-03) — this
   * is both the calibration baseline and the Custom-mode default. When
   * present, it hooks two disjoint regime branches on disjoint data shapes
   * (Pitfall 5 — never merged into one call):
   *   - `blend<=0`: `applyStylePriorReweighting` runs between
   *     `deps.policy()` and `samplePolicy`.
   *   - the search branch: `applyStyleScoreShaping` runs between `search()`
   *     and `argmaxLine`/`sampleRankedLines`.
   */
  style?: BotStyleParams;
}

/** Injected providers + RNG (D-08/D-10) so this module stays provider-agnostic. */
export interface BotMoveDeps extends EngineProviders {
  /** [0,1) — the ONLY source of randomness `selectBotMove` uses (D-10). */
  rng: () => number;
  /** Defaults to `mctsSearch` (D-08) — injectable so tests/harness can stub the search. */
  search?: SearchRunner;
}

/** Never aborts — the D-07 default when the caller omits `signal`. */
const NEVER_ABORT_SIGNAL = new AbortController().signal;

/**
 * Resolves to a legal UCI move for `fen` at the bot's configured
 * `settings.elo`/`settings.blend` strength, using `deps` for policy/search
 * providers and randomness. See the module header for the full regime
 * dispatch and the D-02/D-07 invariants this function structurally enforces.
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
  // move selection (IN-03). Clamp to the domain; NaN (the one value
  // Math.min/Math.max cannot clamp) maps to 1, the deterministic argmax
  // regime — the least surprising strength for a corrupted setting.
  const blend = Number.isFinite(settings.blend) ? Math.min(1, Math.max(0, settings.blend)) : 1;

  if (blend <= 0) {
    // D-03/BOT-02: exactly ONE policy() call, no MCTS.
    const rawPolicy = await deps.policy(fen, settings.elo, side);
    // STYLE-03/D-03: undefined style leaves rawPolicy untouched — byte-
    // identical to the pre-style code path.
    const styledPolicy = settings.style
      ? applyStylePriorReweighting(rawPolicy, fen, settings.style)
      : rawPolicy;
    const sampled = samplePolicy(styledPolicy, deps.rng);
    return sampled ?? fallbackMove(fen, deps.rng);
  }

  const search = deps.search ?? mctsSearch;
  const budget: SearchBudget = {
    ...settings.budget,
    // D-07/BOT-03: symmetric ELO — the bot never adapts to the player.
    // policyTemperature is excluded from BotSettings.budget by type (D-02),
    // so the spread can never thread it into the search budget.
    elo: { w: settings.elo, b: settings.elo },
  };
  // No-op onSnapshot: selectBotMove never streams intermediate snapshots
  // (Pitfall 5 — mctsSearch's SearchRunner requires a real function, never
  // undefined).
  const snapshot = await search(fen, budget, deps, () => {}, signal);
  // STYLE-04/D-03: undefined style leaves snapshot.rankedLines untouched —
  // byte-identical to the pre-style code path.
  const lines: RankedLine[] = settings.style
    ? applyStyleScoreShaping(snapshot.rankedLines, settings.style)
    : snapshot.rankedLines;

  if (blend >= 1) {
    // D-06: deterministic argmax over practicalScore, UCI-ascending tie-break.
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
