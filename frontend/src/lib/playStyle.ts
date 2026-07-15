/**
 * playStyle — pure constants and derivations for the Bots setup screen's
 * play-style control (Phase 171 D-01, PLAY-02).
 *
 * The slider floor is 0.05, NOT 0 (SEED-100, D-01, cross-referenced in
 * selectBotMove.ts's own module header): `selectBotMove` is a three-way
 * REGIME DISPATCH, not a continuous mix. `blend <= 0` runs exactly one Maia
 * policy call with no search at all (BOT-02); anything `> 0` runs the full
 * MCTS search and softmax-samples over `practicalScore` at
 * `tau = TAU_MAX * (1 - blend)`. The 0 -> 0.05 step is therefore a ~+950 ELO
 * regime cliff at rung 1500 (harness measurement: ~980 -> ~1938), while the
 * remaining 95% of the axis (0.05 -> 1.00) is a gentle ramp. Putting 0 on the
 * slider's domain would advertise a smooth continuum that does not exist —
 * exactly the kind of dishonesty D-01 forbids. Reaching blend 0 is only
 * possible via the dedicated Human preset button, never by dragging.
 */

/** Full-human regime: raw Maia policy sample, no search (see module header). */
export const HUMAN_BLEND = 0;
/** Full-engine regime: deterministic argmax over practicalScore. */
export const ENGINE_BLEND = 1;

/** Slider domain floor — strictly greater than HUMAN_BLEND (0.05 > 0). This
 * is the constant-level pin of "the slider cannot reach 0" (D-01). */
export const PLAY_STYLE_MIN = 0.05;
export const PLAY_STYLE_MAX = 1;
export const PLAY_STYLE_STEP = 0.05;
export const PLAY_STYLE_DEFAULT_BLEND = 0.5;

/**
 * Which preset button (if any) the current blend corresponds to exactly.
 * `null` means neither preset is active — the slider is at a custom value.
 */
export function deriveActivePlayStylePreset(blend: number): 'human' | 'engine' | null {
  if (blend === HUMAN_BLEND) return 'human';
  if (blend === ENGINE_BLEND) return 'engine';
  return null;
}

/**
 * Setup-screen play-style summary line (UI-SPEC.md Copywriting Contract,
 * copied verbatim). Human gets a prose-only line (no numeric blend value —
 * 0 is not itself a meaningful "0% search" reading, it's a different regime
 * entirely); every other value gets the numeric-first form matching
 * `OpponentStrengthFilter`'s summary convention.
 */
export function formatPlayStyleSummary(blend: number): string {
  if (blend === HUMAN_BLEND) return 'Human — plays on instinct, no calculation';
  const percent = Math.round(blend * 100);
  return `${blend.toFixed(2)} — blends style with ${percent}% search`;
}
