/**
 * playStyle — pure constants and derivations for the Bots setup screen's
 * play-style control (Phase 171 D-01; reworked to preset-only, quick 260717-lr9).
 *
 * The control exposes THREE discrete presets, no slider:
 *   - Human (blend 0): raw Maia policy sample, no search (BOT-02).
 *   - Light (blend 0.05, the default): full MCTS search, softmax over
 *     `practicalScore` at high temperature — a little calculation on top of the
 *     human-like base.
 *   - Deep (blend 0.5): same search, lower temperature — calculates hard.
 *
 * Why preset-only (no continuous slider): the ELO selector and the blend can't
 * be disentangled into a predictable combined strength, and the engine is not
 * ELO-calibrated yet. So these are named by CALCULATION BEHAVIOR ("Light" /
 * "Deep"), never by rating — three distinct opponents to experiment with, not a
 * strength ladder. Dropping the slider also retires the old D-01 problem of
 * advertising a smooth continuum that the three-way regime dispatch in
 * `selectBotMove` never actually was.
 *
 * `blend <= 0` runs exactly one Maia policy call with no search; anything `> 0`
 * runs the full MCTS search and softmax-samples at `tau = TAU_MAX * (1 - blend)`.
 */

/** Human preset: raw Maia policy sample, no search. Also the valid-range floor. */
export const HUMAN_BLEND = 0;
/** Light preset: light MCTS search. The default preset. */
export const LIGHT_BLEND = 0.05;
/** Deep preset: heavier MCTS search (lower softmax temperature). */
export const DEEP_BLEND = 0.5;

/**
 * Valid-range ceiling for a stored blend, NOT a preset. No preset button emits
 * blend 1, but the accepted range must stay `[HUMAN_BLEND, BLEND_MAX]` = `[0, 1]`
 * so legacy stored blobs (the retired Engine preset persisted blend 1.0) still
 * VALIDATE rather than being treated as corruption — see the WR-01 bug note in
 * `botSetupSettings.ts`, where an out-of-range blend silently discards a
 * finished game. Downstream `selectBotMove` still treats blend >= 1 as the
 * deterministic-argmax regime.
 */
export const BLEND_MAX = 1;

/** Default preset on a fresh setup screen: Light. */
export const PLAY_STYLE_DEFAULT_BLEND = LIGHT_BLEND;

export type PlayStylePreset = 'human' | 'light' | 'deep';

/**
 * Which preset (if any) the current blend corresponds to exactly. `null` means
 * the blend is not one of the three presets — only reachable from a legacy
 * stored blob (e.g. an old 1.0); the UI then shows no active preset until the
 * user clicks one.
 */
export function deriveActivePlayStylePreset(blend: number): PlayStylePreset | null {
  if (blend === HUMAN_BLEND) return 'human';
  if (blend === LIGHT_BLEND) return 'light';
  if (blend === DEEP_BLEND) return 'deep';
  return null;
}

/**
 * Setup-screen play-style summary line. Behavior prose only — no blend number,
 * no "% search", no ELO/strength claim (the engine isn't calibrated yet). A
 * non-preset legacy blend falls back to a neutral line.
 */
export function formatPlayStyleSummary(blend: number): string {
  switch (deriveActivePlayStylePreset(blend)) {
    case 'human':
      return 'Human — instinct, no calculation';
    case 'light':
      return 'Light — calculates a little';
    case 'deep':
      return 'Deep — calculates hard';
    default:
      return 'Custom calculation depth';
  }
}
