/**
 * trainScoreCelebration — the score screen's one-shot result sound and confetti,
 * shared by the real screen (on mount) and the admin demo (on Replay).
 */
import { fireWinConfetti, firePartialConfetti } from '@/lib/confetti';
import { playSound, type SoundEvent } from '@/lib/sounds';
import type { TrainRatingBand } from '@/lib/trainScore';

/** Result sound per band. `green` keeps WinChime, which is reserved for this
 * session verdict and bot-game wins — the per-puzzle reveal's full-score case
 * has its own `score-full` clip, so the session end does not sound like just
 * one more solved puzzle. The other two bands share the reveal's clips. */
const RATING_BAND_SOUND: Record<TrainRatingBand, SoundEvent> = {
  green: 'game-win',
  yellow: 'score-partial',
  red: 'game-loss',
};

/**
 * The sound is NOT motion-gated: reduced-motion users still get it (playSound
 * honors the shared mute preference on its own), they just lose the confetti.
 */
export function celebrateScore(band: TrainRatingBand | null, reducedMotion: boolean): void {
  if (band === null) return;
  playSound(RATING_BAND_SOUND[band]);
  if (reducedMotion) return;
  if (band === 'green') fireWinConfetti();
  else if (band === 'yellow') firePartialConfetti();
}
